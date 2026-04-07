import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import List

from qa.models import Finding

SEVERITY_MAP = {
    "fatal": "critical",
    "error": "critical",
    "warning": "medium",
    "convention": "low",
    "refactor": "low",
}

ESLINT_SEVERITY_MAP = {2: "critical", 1: "medium"}

JS_TS_EXTENSIONS = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}
CS_EXTENSIONS = {".cs"}


def lint_file(filename: str, content: str, pylintrc: str = None) -> List[Finding]:
    ext = Path(filename).suffix.lower()
    if ext in JS_TS_EXTENSIONS:
        return _lint_js_ts(filename, content)
    if ext in CS_EXTENSIONS:
        return _lint_cs(filename, content)
    return _lint_python(filename, content, pylintrc)


def _lint_python(filename: str, content: str, pylintrc: str = None) -> List[Finding]:
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, prefix="qa_lint_"
    ) as f:
        f.write(content)
        tmp_path = f.name
    try:
        cmd = ["pylint", "--output-format=json", tmp_path]
        if pylintrc:
            cmd.extend(["--rcfile", pylintrc])
        result = subprocess.run(cmd, capture_output=True, text=True)
        messages = json.loads(result.stdout)
        return [
            Finding(
                filename=filename,
                line_number=msg.get("line", 1),
                severity=SEVERITY_MAP.get(msg.get("type", "").lower(), "low"),
                title=f"[{msg.get('message-id', '')}] {msg.get('symbol', '')}",
                explanation=msg.get("message", ""),
                suggestion="",
            )
            for msg in messages
        ]
    except (json.JSONDecodeError, ValueError):
        return []
    except Exception as e:
        print(f"Linter error for {filename}: {e}")
        return []
    finally:
        os.unlink(tmp_path)


def _lint_js_ts(filename: str, content: str) -> List[Finding]:
    ext = Path(filename).suffix.lower()
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=ext, delete=False, prefix="qa_lint_"
    ) as f:
        f.write(content)
        tmp_path = f.name
    try:
        result = subprocess.run(
            [
                "eslint",
                "--format", "json",
                "--no-eslintrc",
                "-c", "/app/default.eslintrc.json",
                tmp_path,
            ],
            capture_output=True,
            text=True,
        )
        output = json.loads(result.stdout)
        findings = []
        for file_result in output:
            for msg in file_result.get("messages", []):
                findings.append(Finding(
                    filename=filename,
                    line_number=msg.get("line", 1),
                    severity=ESLINT_SEVERITY_MAP.get(msg.get("severity"), "medium"),
                    title=f"[{msg.get('ruleId', '')}]",
                    explanation=msg.get("message", ""),
                    suggestion="",
                ))
        return findings
    except (json.JSONDecodeError, ValueError):
        return []
    except Exception as e:
        print(f"Linter error for {filename}: {e}")
        return []
    finally:
        os.unlink(tmp_path)


def _lint_cs(filename: str, content: str) -> List[Finding]:
    tmpdir = tempfile.mkdtemp(prefix="qa_cs_")
    try:
        basename = Path(filename).name
        cs_path = os.path.join(tmpdir, basename)
        report_path = os.path.join(tmpdir, "report.json")

        with open(cs_path, "w") as f:
            f.write(content)

        with open(os.path.join(tmpdir, "project.csproj"), "w") as f:
            f.write(
                "<Project Sdk=\"Microsoft.NET.Sdk\">\n"
                "  <PropertyGroup>\n"
                "    <TargetFramework>net8.0</TargetFramework>\n"
                "  </PropertyGroup>\n"
                "</Project>\n"
            )

        subprocess.run(
            ["dotnet", "format", tmpdir, "--verify-no-changes", "--report", report_path],
            capture_output=True,
            text=True,
        )

        if not os.path.exists(report_path):
            return []

        with open(report_path) as f:
            report = json.load(f)

        findings = []
        for file_entry in report:
            for change in file_entry.get("FileChanges", []):
                findings.append(Finding(
                    filename=filename,
                    line_number=change.get("LineNumber", 1),
                    severity="low",
                    title=f"[{change.get('DiagnosticId', 'dotnet-format')}] formatting",
                    explanation=change.get("FormatDescription", "File needs formatting"),
                    suggestion="Run `dotnet format` to fix.",
                ))
        return findings
    except Exception as e:
        print(f"Linter error for {filename}: {e}")
        return []
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
