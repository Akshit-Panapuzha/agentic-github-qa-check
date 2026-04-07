import json
import os
import subprocess
import tempfile
from typing import List

from qa.models import Finding

SEVERITY_MAP = {
    "fatal": "critical",
    "error": "critical",
    "warning": "medium",
    "convention": "low",
    "refactor": "low",
}


def lint_file(filename: str, content: str, pylintrc: str = None) -> List[Finding]:
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
