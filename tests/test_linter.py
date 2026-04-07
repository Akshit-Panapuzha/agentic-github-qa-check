import json
import unittest.mock
from unittest.mock import MagicMock, patch

from qa.linter import SEVERITY_MAP, lint_file

SAMPLE_PYLINT_OUTPUT = json.dumps([
    {
        "type": "error",
        "line": 5,
        "symbol": "undefined-variable",
        "message": "Undefined variable 'foo'",
        "message-id": "E0602",
        "column": 0, "module": "tmp", "obj": "", "path": "/tmp/qa_lint_x.py",
    },
    {
        "type": "convention",
        "line": 2,
        "symbol": "line-too-long",
        "message": "Line too long (130/120)",
        "message-id": "C0301",
        "column": 0, "module": "tmp", "obj": "", "path": "/tmp/qa_lint_x.py",
    },
])


def test_severity_map_covers_all_pylint_types():
    for t in ["fatal", "error", "warning", "convention", "refactor"]:
        assert t in SEVERITY_MAP


def test_lint_file_parses_findings_and_maps_severity():
    with patch("qa.linter.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout=SAMPLE_PYLINT_OUTPUT, returncode=1)
        findings = lint_file("app/models.py", "x = foo\n")

    assert len(findings) == 2
    error_f = next(f for f in findings if "E0602" in f.title)
    conv_f = next(f for f in findings if "C0301" in f.title)
    assert error_f.severity == "critical"
    assert error_f.filename == "app/models.py"
    assert error_f.line_number == 5
    assert conv_f.severity == "low"


def test_lint_file_returns_empty_on_invalid_json():
    with patch("qa.linter.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="not valid json", returncode=1)
        findings = lint_file("app/models.py", "x = 1\n")
    assert findings == []


def test_lint_file_returns_empty_on_subprocess_error():
    with patch("qa.linter.subprocess.run") as mock_run:
        mock_run.side_effect = FileNotFoundError("pylint not found")
        findings = lint_file("app/models.py", "x = 1\n")
    assert findings == []


# --- JS/TS ---

SAMPLE_ESLINT_OUTPUT = json.dumps([{
    "filePath": "/tmp/qa_lint_xxx.js",
    "messages": [
        {
            "ruleId": "no-unused-vars",
            "severity": 2,
            "message": "'foo' is defined but never used.",
            "line": 3,
            "column": 7,
        },
        {
            "ruleId": "no-console",
            "severity": 1,
            "message": "Unexpected console statement.",
            "line": 7,
            "column": 1,
        },
    ],
}])


def test_lint_file_js_maps_eslint_severity():
    with patch("qa.linter.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout=SAMPLE_ESLINT_OUTPUT, returncode=1)
        findings = lint_file("src/app.js", "const foo = 1;\nconsole.log('hi');\n")

    assert len(findings) == 2
    err_f = next(f for f in findings if "no-unused-vars" in f.title)
    warn_f = next(f for f in findings if "no-console" in f.title)
    assert err_f.severity == "critical"
    assert err_f.line_number == 3
    assert err_f.filename == "src/app.js"
    assert warn_f.severity == "medium"


def test_lint_file_ts_routes_to_eslint():
    with patch("qa.linter.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            stdout=json.dumps([{"filePath": "/tmp/x.ts", "messages": []}]),
            returncode=0,
        )
        findings = lint_file("src/app.ts", "const x: number = 1;\n")

    cmd = mock_run.call_args[0][0]
    assert "eslint" in cmd[0]
    assert findings == []


def test_lint_file_js_returns_empty_on_subprocess_error():
    with patch("qa.linter.subprocess.run") as mock_run:
        mock_run.side_effect = FileNotFoundError("eslint not found")
        findings = lint_file("src/app.js", "const x = 1;\n")
    assert findings == []
