import json
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
