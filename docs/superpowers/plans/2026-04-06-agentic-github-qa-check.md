# agentic-github-qa-check Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Docker-based GitHub Action that runs pylint on changed Python files in a PR and posts inline review comments plus a collapsible summary.

**Architecture:** Three-stage pipeline — Orchestrator fetches PR diff and file contents via PyGithub; Linter runs pylint per file and maps results to Finding objects; GitHub Client validates line positions against the diff hunk, posts a batched PR review (inline comments for critical/medium), and posts a separate issue comment (summary + collapsible `<details>` block for low findings).

**Tech Stack:** Python 3.11, pylint, PyGithub, PyYAML, pytest, pytest-mock, Docker, GitHub Actions

---

## File map

| File | Responsibility |
|------|---------------|
| `qa/models.py` | `Finding` dataclass |
| `qa/config.py` | Load `.qa.yaml` with defaults |
| `qa/linter.py` | Run pylint, parse JSON output, return `List[Finding]` |
| `qa/orchestrator.py` | Fetch PR files, filter, route to linter |
| `qa/github_client.py` | Diff position mapping, build summary, post review + issue comment |
| `qa/main.py` | Entry point: read env vars, wire pipeline, exit 0/1 |
| `action.yml` | GitHub Action definition |
| `Dockerfile` | Docker image definition |
| `default.pylintrc` | Bundled pylint config |
| `requirements.txt` | Runtime deps (PyGithub, PyYAML) |
| `tests/test_models.py` | Tests for Finding |
| `tests/test_config.py` | Tests for config loader |
| `tests/test_linter.py` | Tests for lint runner (mocked subprocess) |
| `tests/test_orchestrator.py` | Tests for orchestrator (mocked PyGithub) |
| `tests/test_github_client.py` | Tests for diff utils, summary builder, review poster |
| `tests/test_main.py` | Tests for entry point (mocked orchestrator + client) |

---

### Task 1: Project scaffold

**Files:**
- Create: `requirements.txt`
- Create: `requirements-dev.txt`
- Create: `qa/__init__.py`
- Create: `tests/__init__.py`
- Create: `pytest.ini`

- [ ] **Step 1: Create requirements.txt**

```
PyGithub
PyYAML
```

- [ ] **Step 2: Create requirements-dev.txt**

```
pytest
pytest-mock
```

- [ ] **Step 3: Create qa/__init__.py**

Empty file.

- [ ] **Step 4: Create tests/__init__.py**

Empty file.

- [ ] **Step 5: Create pytest.ini**

```ini
[pytest]
testpaths = tests
```

- [ ] **Step 6: Install dependencies**

Run: `pip install -r requirements.txt -r requirements-dev.txt`
Expected: installs PyGithub, PyYAML, pytest, pytest-mock

- [ ] **Step 7: Verify pytest runs**

Run: `pytest`
Expected: "no tests ran" or "collected 0 items"

- [ ] **Step 8: Commit**

```bash
git add requirements.txt requirements-dev.txt qa/__init__.py tests/__init__.py pytest.ini
git commit -m "chore: project scaffold"
```

---

### Task 2: Finding model

**Files:**
- Create: `qa/models.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_models.py`:
```python
from qa.models import Finding


def test_finding_stores_all_fields():
    f = Finding(
        filename="app/models.py",
        line_number=10,
        severity="critical",
        title="[E0602] undefined-variable",
        explanation="Undefined variable 'foo'",
        suggestion="",
    )
    assert f.filename == "app/models.py"
    assert f.line_number == 10
    assert f.severity == "critical"
    assert f.title == "[E0602] undefined-variable"
    assert f.explanation == "Undefined variable 'foo'"
    assert f.suggestion == ""


def test_finding_equality():
    f1 = Finding("a.py", 1, "medium", "title", "exp", "sug")
    f2 = Finding("a.py", 1, "medium", "title", "exp", "sug")
    assert f1 == f2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_models.py -v`
Expected: FAIL — `ImportError: cannot import name 'Finding'`

- [ ] **Step 3: Implement qa/models.py**

```python
from dataclasses import dataclass


@dataclass
class Finding:
    filename: str
    line_number: int
    severity: str  # "critical" | "medium" | "low"
    title: str
    explanation: str
    suggestion: str
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_models.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add qa/models.py tests/test_models.py
git commit -m "feat: add Finding dataclass"
```

---

### Task 3: Config loader

**Files:**
- Create: `qa/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_config.py`:
```python
import os
import tempfile
import textwrap

from qa.config import Config, load_config


def test_default_config_when_no_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        cfg = load_config(tmpdir)
    assert cfg.severity_filter == ["critical", "medium"]
    assert cfg.max_comments_per_pr == 20
    assert cfg.ignore_paths == []
    assert cfg.languages == ["python"]


def test_loads_qa_yaml_overrides():
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, ".qa.yaml"), "w") as f:
            f.write(textwrap.dedent("""\
                qa:
                  max_comments_per_pr: 5
                  ignore_paths:
                    - "migrations/*"
            """))
        cfg = load_config(tmpdir)
    assert cfg.max_comments_per_pr == 5
    assert cfg.ignore_paths == ["migrations/*"]
    assert cfg.severity_filter == ["critical", "medium"]  # unchanged default


def test_invalid_yaml_falls_back_to_defaults():
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, ".qa.yaml"), "w") as f:
            f.write("{ invalid yaml :")
        cfg = load_config(tmpdir)
    assert cfg.severity_filter == ["critical", "medium"]
    assert cfg.max_comments_per_pr == 20
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_config.py -v`
Expected: FAIL — `ImportError: cannot import name 'load_config'`

- [ ] **Step 3: Implement qa/config.py**

```python
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

import yaml


@dataclass
class Config:
    severity_filter: List[str] = field(default_factory=lambda: ["critical", "medium"])
    max_comments_per_pr: int = 20
    ignore_paths: List[str] = field(default_factory=list)
    languages: List[str] = field(default_factory=lambda: ["python"])


def load_config(repo_root: str = ".") -> Config:
    qa_yaml = Path(repo_root) / ".qa.yaml"
    if not qa_yaml.exists():
        return Config()
    try:
        with open(qa_yaml) as f:
            data = yaml.safe_load(f)
        qa = (data or {}).get("qa", {}) or {}
        config = Config()
        if "severity_filter" in qa:
            config.severity_filter = qa["severity_filter"]
        if "max_comments_per_pr" in qa:
            config.max_comments_per_pr = qa["max_comments_per_pr"]
        if "ignore_paths" in qa:
            config.ignore_paths = qa["ignore_paths"]
        if "languages" in qa:
            config.languages = qa["languages"]
        return config
    except Exception:
        return Config()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_config.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add qa/config.py tests/test_config.py
git commit -m "feat: add config loader"
```

---

### Task 4: Lint runner

**Files:**
- Create: `qa/linter.py`
- Create: `tests/test_linter.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_linter.py`:
```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_linter.py -v`
Expected: FAIL — `ImportError: cannot import name 'lint_file'`

- [ ] **Step 3: Implement qa/linter.py**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_linter.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add qa/linter.py tests/test_linter.py
git commit -m "feat: add pylint runner"
```

---

### Task 5: Orchestrator

**Files:**
- Create: `qa/orchestrator.py`
- Create: `tests/test_orchestrator.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_orchestrator.py`:
```python
from unittest.mock import MagicMock, patch

from qa.config import Config
from qa.models import Finding
from qa.orchestrator import is_ignored, run


def test_is_ignored_matches_wildcard():
    assert is_ignored("migrations/0001_initial.py", ["migrations/*"]) is True


def test_is_ignored_no_match():
    assert is_ignored("app/models.py", ["migrations/*"]) is False


def test_is_ignored_empty_patterns():
    assert is_ignored("anything.py", []) is False


def _make_mock_repo(files, file_contents):
    mock_pr = MagicMock()
    mock_pr.get_files.return_value = files
    mock_repo = MagicMock()
    mock_repo.get_pull.return_value = mock_pr
    mock_repo.get_contents.side_effect = lambda path, ref: file_contents[path]
    return mock_repo


def test_run_returns_findings_for_py_files():
    mock_file = MagicMock()
    mock_file.filename = "app/models.py"
    mock_file.patch = "@@ -1,1 +1,2 @@\n line1\n+new line\n"

    mock_content = MagicMock()
    mock_content.decoded_content = b"x = foo\n"

    mock_repo = _make_mock_repo([mock_file], {"app/models.py": mock_content})
    expected = Finding("app/models.py", 1, "critical", "[E0602] err", "bad", "")

    with patch("qa.orchestrator.Github") as MockGithub, \
         patch("qa.orchestrator.lint_file", return_value=[expected]):
        MockGithub.return_value.get_repo.return_value = mock_repo
        findings = run("token", "owner/repo", 42, "def456", Config())

    assert findings == [expected]


def test_run_skips_non_py_files():
    mock_file = MagicMock()
    mock_file.filename = "README.md"
    mock_file.patch = "@@ -1 +1 @@\n+# Title\n"

    mock_repo = _make_mock_repo([mock_file], {})

    with patch("qa.orchestrator.Github") as MockGithub, \
         patch("qa.orchestrator.lint_file") as mock_lint:
        MockGithub.return_value.get_repo.return_value = mock_repo
        findings = run("token", "owner/repo", 42, "def456", Config())

    mock_lint.assert_not_called()
    assert findings == []


def test_run_skips_ignored_paths():
    mock_file = MagicMock()
    mock_file.filename = "migrations/0001.py"
    mock_file.patch = "@@ -1 +1 @@\n+x = 1\n"

    mock_repo = _make_mock_repo([mock_file], {})

    with patch("qa.orchestrator.Github") as MockGithub, \
         patch("qa.orchestrator.lint_file") as mock_lint:
        MockGithub.return_value.get_repo.return_value = mock_repo
        findings = run("token", "owner/repo", 42, "def456", Config(ignore_paths=["migrations/*"]))

    mock_lint.assert_not_called()
    assert findings == []


def test_run_skips_files_with_no_patch():
    mock_file = MagicMock()
    mock_file.filename = "app/models.py"
    mock_file.patch = None

    mock_repo = _make_mock_repo([mock_file], {})

    with patch("qa.orchestrator.Github") as MockGithub, \
         patch("qa.orchestrator.lint_file") as mock_lint:
        MockGithub.return_value.get_repo.return_value = mock_repo
        findings = run("token", "owner/repo", 42, "def456", Config())

    mock_lint.assert_not_called()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_orchestrator.py -v`
Expected: FAIL — `ImportError: cannot import name 'is_ignored'`

- [ ] **Step 3: Implement qa/orchestrator.py**

```python
import fnmatch
from typing import List

from github import Github

from qa.config import Config
from qa.linter import lint_file
from qa.models import Finding


def is_ignored(filename: str, ignore_paths: List[str]) -> bool:
    return any(fnmatch.fnmatch(filename, pattern) for pattern in ignore_paths)


def run(
    github_token: str,
    repo_name: str,
    pr_number: int,
    head_sha: str,
    config: Config,
    pylintrc: str = None,
) -> List[Finding]:
    g = Github(github_token)
    repo = g.get_repo(repo_name)
    pr = repo.get_pull(pr_number)

    all_findings: List[Finding] = []

    for f in pr.get_files():
        if not f.filename.endswith(".py"):
            continue
        if is_ignored(f.filename, config.ignore_paths):
            continue
        if not f.patch:
            continue
        try:
            content = repo.get_contents(f.filename, ref=head_sha).decoded_content.decode("utf-8")
        except Exception:
            continue
        all_findings.extend(lint_file(f.filename, content, pylintrc))

    return all_findings
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_orchestrator.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add qa/orchestrator.py tests/test_orchestrator.py
git commit -m "feat: add orchestrator"
```

---

### Task 6: GitHub Client

**Files:**
- Create: `qa/github_client.py`
- Create: `tests/test_github_client.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_github_client.py`:
```python
from unittest.mock import MagicMock, patch

from qa.config import Config
from qa.github_client import build_summary, parse_diff_positions, post_review, snap_to_diff
from qa.models import Finding


# --- parse_diff_positions ---

def test_parse_diff_positions_maps_lines_to_diff_positions():
    diff_str = "@@ -1,2 +1,3 @@\n line1\n+added\n line2"
    positions = parse_diff_positions(diff_str)
    # @@ = diff pos 1
    # " line1" = new file line 1, diff pos 2
    # "+added" = new file line 2, diff pos 3
    # " line2" = new file line 3, diff pos 4
    assert positions[1] == 2
    assert positions[2] == 3
    assert positions[3] == 4


def test_parse_diff_positions_removed_lines_not_in_map():
    diff_str = "@@ -1,2 +1,1 @@\n context\n-removed"
    positions = parse_diff_positions(diff_str)
    assert 1 in positions
    assert 2 not in positions


def test_parse_diff_positions_empty_returns_empty():
    assert parse_diff_positions("") == {}


# --- snap_to_diff ---

def test_snap_to_diff_exact_match():
    positions = {1: 2, 2: 3, 3: 4}
    assert snap_to_diff(2, positions) == 3


def test_snap_to_diff_snaps_to_nearest():
    positions = {1: 2, 5: 6}
    result = snap_to_diff(3, positions)
    assert result in (2, 6)  # line 3 is equidistant from lines 1 and 5


def test_snap_to_diff_empty_positions_returns_none():
    assert snap_to_diff(5, {}) is None


# --- build_summary ---

def test_build_summary_includes_counts_and_details_block():
    findings = [
        Finding("a.py", 1, "critical", "[E0602] undefined-variable", "Undefined 'x'", ""),
        Finding("a.py", 2, "medium", "[W0611] unused-import", "Unused import os", ""),
        Finding("a.py", 3, "low", "[C0301] line-too-long", "Line too long", ""),
    ]
    summary = build_summary(findings)
    assert "critical" in summary.lower()
    assert "medium" in summary.lower()
    assert "<details>" in summary
    assert "C0301" in summary


def test_build_summary_omits_details_block_when_no_low_findings():
    findings = [Finding("a.py", 1, "critical", "[E0602] err", "bad", "")]
    summary = build_summary(findings)
    assert "<details>" not in summary


def test_build_summary_clean_message_when_no_findings():
    summary = build_summary([])
    assert summary
    assert "<details>" not in summary


# --- post_review ---

def _make_mock_repo(patch_str="@@ -1,3 +1,3 @@\n line1\n line2\n line3"):
    mock_file = MagicMock()
    mock_file.filename = "a.py"
    mock_file.patch = patch_str
    mock_pr = MagicMock()
    mock_pr.get_files.return_value = [mock_file]
    mock_repo = MagicMock()
    mock_repo.get_pull.return_value = mock_pr
    return mock_repo, mock_pr


def test_post_review_creates_inline_review_for_critical_and_medium():
    mock_repo, mock_pr = _make_mock_repo()
    findings = [
        Finding("a.py", 1, "critical", "[E0602] err", "bad", ""),
        Finding("a.py", 2, "medium", "[W0611] warn", "meh", ""),
        Finding("a.py", 3, "low", "[C0301] low", "style", ""),
    ]
    post_review(mock_repo, 1, findings, Config())
    mock_pr.create_review.assert_called_once()
    comments = mock_pr.create_review.call_args.kwargs["comments"]
    assert len(comments) == 2
    mock_pr.create_issue_comment.assert_called_once()


def test_post_review_skips_create_review_when_only_low_findings():
    mock_repo, mock_pr = _make_mock_repo()
    findings = [Finding("a.py", 1, "low", "[C0301] low", "style", "")]
    post_review(mock_repo, 1, findings, Config())
    mock_pr.create_review.assert_not_called()
    mock_pr.create_issue_comment.assert_called_once()


def test_post_review_respects_max_comments_per_pr():
    mock_repo, mock_pr = _make_mock_repo(
        "@@ -1,5 +1,5 @@\n line1\n line2\n line3\n line4\n line5"
    )
    findings = [Finding("a.py", i, "critical", f"[E{i:04d}] err", "bad", "") for i in range(1, 6)]
    post_review(mock_repo, 1, findings, Config(max_comments_per_pr=2))
    comments = mock_pr.create_review.call_args.kwargs["comments"]
    assert len(comments) == 2


def test_post_review_handles_422_gracefully():
    from github import GithubException
    mock_repo, mock_pr = _make_mock_repo()
    mock_pr.create_review.side_effect = GithubException(422, "Validation Failed", None)
    findings = [Finding("a.py", 1, "critical", "[E0602] err", "bad", "")]
    post_review(mock_repo, 1, findings, Config())  # must not raise
    mock_pr.create_issue_comment.assert_called_once()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_github_client.py -v`
Expected: FAIL — `ImportError: cannot import name 'parse_diff_positions'`

- [ ] **Step 3: Implement qa/github_client.py**

```python
import re
from typing import Dict, List, Optional

from github import GithubException

from qa.config import Config
from qa.models import Finding


def parse_diff_positions(patch: str) -> Dict[int, int]:
    """Map new-file line numbers to 1-indexed diff positions."""
    positions: Dict[int, int] = {}
    diff_pos = 0
    current_new_line = 0

    for line in patch.split("\n"):
        if line.startswith("@@"):
            diff_pos += 1
            match = re.search(r"\+(\d+)", line)
            if match:
                current_new_line = int(match.group(1)) - 1
        elif line.startswith("+"):
            diff_pos += 1
            current_new_line += 1
            positions[current_new_line] = diff_pos
        elif line.startswith("-"):
            diff_pos += 1
        elif line.startswith("\\"):
            pass  # "\ No newline at end of file"
        else:
            diff_pos += 1
            current_new_line += 1
            positions[current_new_line] = diff_pos

    return positions


def snap_to_diff(line_number: int, positions: Dict[int, int]) -> Optional[int]:
    """Return the diff position for the nearest file line. None if positions is empty."""
    if not positions:
        return None
    if line_number in positions:
        return positions[line_number]
    nearest = min(positions.keys(), key=lambda x: abs(x - line_number))
    return positions[nearest]


def build_summary(findings: List[Finding]) -> str:
    if not findings:
        return "**QA Lint Check passed.** No issues found."

    counts: Dict[str, int] = {}
    for f in findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1

    total = sum(counts.values())
    parts = [f"{v} {k}" for k, v in counts.items() if v > 0]
    lines = [f"**QA Lint Check found {total} issue(s):** {', '.join(parts)}."]

    low_findings = [f for f in findings if f.severity == "low"]
    if low_findings:
        lines += [
            "",
            "<details>",
            f"<summary>Low severity findings ({len(low_findings)})</summary>",
            "",
        ]
        for f in low_findings:
            lines.append(f"**{f.filename}:{f.line_number}** — {f.title}")
            lines.append(f"_{f.explanation}_")
            lines.append("")
        lines.append("</details>")

    return "\n".join(lines)


def post_review(repo, pr_number: int, findings: List[Finding], config: Config) -> None:
    pr = repo.get_pull(pr_number)
    file_patches = {f.filename: f.patch for f in pr.get_files() if f.patch}

    inline_findings = [
        f for f in findings if f.severity in config.severity_filter
    ][: config.max_comments_per_pr]

    if inline_findings:
        comments = []
        for finding in inline_findings:
            positions = parse_diff_positions(file_patches.get(finding.filename, ""))
            position = snap_to_diff(finding.line_number, positions)
            if position is None:
                continue
            body = f"**[{finding.severity.upper()}] {finding.title}**\n\n{finding.explanation}"
            comments.append({"path": finding.filename, "position": position, "body": body})

        if comments:
            try:
                pr.create_review(body="", event="COMMENT", comments=comments)
            except GithubException as e:
                print(f"Warning: could not post inline review (HTTP {e.status}): {e.data}")

    pr.create_issue_comment(build_summary(findings))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_github_client.py -v`
Expected: 13 passed

- [ ] **Step 5: Commit**

```bash
git add qa/github_client.py tests/test_github_client.py
git commit -m "feat: add GitHub client"
```

---

### Task 7: Main entry point

**Files:**
- Create: `qa/main.py`
- Create: `tests/test_main.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_main.py`:
```python
import pytest
from unittest.mock import patch

from qa.main import main
from qa.models import Finding


def test_main_exits_1_when_findings(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "token123")
    monkeypatch.setenv("PR_NUMBER", "42")
    monkeypatch.setenv("REPO", "owner/repo")
    monkeypatch.setenv("BASE_SHA", "abc")
    monkeypatch.setenv("HEAD_SHA", "def")

    mock_finding = Finding("a.py", 1, "critical", "[E0602] err", "bad code", "")

    with patch("qa.main.orchestrator.run", return_value=[mock_finding]), \
         patch("qa.main.Github"), \
         patch("qa.main.github_client.post_review"):
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 1


def test_main_exits_0_when_no_findings(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "token123")
    monkeypatch.setenv("PR_NUMBER", "42")
    monkeypatch.setenv("REPO", "owner/repo")
    monkeypatch.setenv("BASE_SHA", "abc")
    monkeypatch.setenv("HEAD_SHA", "def")

    with patch("qa.main.orchestrator.run", return_value=[]), \
         patch("qa.main.Github"), \
         patch("qa.main.github_client.post_review"):
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0


def test_main_passes_correct_args_to_orchestrator(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "mytoken")
    monkeypatch.setenv("PR_NUMBER", "7")
    monkeypatch.setenv("REPO", "acme/myrepo")
    monkeypatch.setenv("BASE_SHA", "base123")
    monkeypatch.setenv("HEAD_SHA", "head456")

    with patch("qa.main.orchestrator.run", return_value=[]) as mock_run, \
         patch("qa.main.Github"), \
         patch("qa.main.github_client.post_review"):
        try:
            main()
        except SystemExit:
            pass

    args = mock_run.call_args.args
    assert args[0] == "mytoken"
    assert args[1] == "acme/myrepo"
    assert args[2] == 7
    assert args[3] == "head456"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_main.py -v`
Expected: FAIL — `ImportError: cannot import name 'main'`

- [ ] **Step 3: Implement qa/main.py**

```python
import os
import sys

from github import Github

from qa import github_client, orchestrator
from qa.config import load_config


def main() -> None:
    token = os.environ["GITHUB_TOKEN"]
    pr_number = int(os.environ["PR_NUMBER"])
    repo_name = os.environ["REPO"]
    head_sha = os.environ["HEAD_SHA"]

    config = load_config(".")
    findings = orchestrator.run(token, repo_name, pr_number, head_sha, config)

    g = Github(token)
    repo = g.get_repo(repo_name)
    github_client.post_review(repo, pr_number, findings, config)

    sys.exit(1 if findings else 0)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the full test suite**

Run: `pytest -v`
Expected: 32 passed (2 + 3 + 4 + 5 + 13 + 3 across all test files)

- [ ] **Step 5: Commit**

```bash
git add qa/main.py tests/test_main.py
git commit -m "feat: add main entry point"
```

---

### Task 8: Action packaging

**Files:**
- Create: `default.pylintrc`
- Create: `Dockerfile`
- Create: `action.yml`

- [ ] **Step 1: Create default.pylintrc**

```ini
[MESSAGES CONTROL]
disable=C0114,C0115,C0116

[FORMAT]
max-line-length=120

[DESIGN]
max-args=7
```

- [ ] **Step 2: Create Dockerfile**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir pylint PyGithub PyYAML

COPY qa/ ./qa/
COPY default.pylintrc .

ENV PYTHONPATH=/app

ENTRYPOINT ["python", "-m", "qa.main"]
```

- [ ] **Step 3: Create action.yml**

```yaml
name: 'AI QA Linter'
description: 'Runs pylint on changed Python files and posts inline PR comments.'
branding:
  icon: 'check-circle'
  color: 'green'
inputs:
  github-token:
    description: 'GitHub token'
    required: true
  pr-number:
    description: 'PR number'
    required: true
  repo:
    description: 'Repository name (owner/repo)'
    required: true
  base-sha:
    description: 'Base branch SHA'
    required: true
  head-sha:
    description: 'Head branch SHA'
    required: true
runs:
  using: 'docker'
  image: 'Dockerfile'
  env:
    GITHUB_TOKEN: ${{ inputs.github-token }}
    PR_NUMBER: ${{ inputs.pr-number }}
    REPO: ${{ inputs.repo }}
    BASE_SHA: ${{ inputs.base-sha }}
    HEAD_SHA: ${{ inputs.head-sha }}
```

- [ ] **Step 4: Commit**

```bash
git add default.pylintrc Dockerfile action.yml
git commit -m "chore: add Docker and GitHub Action packaging"
```

---

### Task 9: README

**Files:**
- Create: `README.md`

- [ ] **Step 1: Create README.md**

````markdown
# agentic-github-qa-check

A Docker-based GitHub Action that runs pylint on changed Python files in a PR and posts inline review comments. Fails the Actions run when any lint issues are found.

## Usage

Add `.github/workflows/qa.yml` to your repository:

```yaml
name: QA Lint Check

on:
  pull_request:
    types: [opened, synchronize, reopened]

permissions:
  contents: read
  pull-requests: write

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - name: Run QA Linter
        uses: Akshit-Panapuzha/agentic-github-qa-check@v1
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
          pr-number: ${{ github.event.pull_request.number }}
          repo: ${{ github.repository }}
          base-sha: ${{ github.event.pull_request.base.sha }}
          head-sha: ${{ github.event.pull_request.head.sha }}
```

No additional secrets required beyond the built-in `GITHUB_TOKEN`.

## Configuration

Optionally add `.qa.yaml` to your repo root:

```yaml
qa:
  severity_filter:
    - critical
    - medium
  max_comments_per_pr: 20
  ignore_paths:
    - "migrations/*"
    - "tests/*"
```

All fields are optional. Shown values are the defaults.

## Severity levels

| Pylint type | Severity | Behaviour |
|-------------|----------|-----------|
| Fatal / Error | critical | Inline PR review comment |
| Warning | medium | Inline PR review comment |
| Convention / Refactor | low | Collapsible summary comment |

## Pass/fail

Exits 1 (fail) if any findings, 0 if clean.
````

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README"
```
