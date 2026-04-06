# agentic-github-qa-check — Design Document

**Status:** Approved
**Last updated:** April 2026

---

## Overview

`agentic-github-qa-check` is a Docker-based GitHub Action that runs static linting on pull requests and posts inline comments at the exact lines where issues are found. It fails the Actions run when any lint issues are detected, giving a clear red/green signal on every PR.

The initial version supports **Python only** (via pylint), with the architecture designed to add JavaScript (ESLint) and C# (dotnet-format) in future versions without structural changes.

There is no LLM involved — this is pure static analysis. No OpenAI key required.

---

## Goals

- Run pylint on every changed `.py` file in a PR
- Post inline GitHub PR review comments at the flagged line numbers
- Fail the Actions run (exit code 1) if any lint issues are found
- Require zero configuration in the consuming repo — sensible defaults built in
- Be consumable by any repo with a single workflow file and no secrets beyond `GITHUB_TOKEN`

### Non-goals

- LLM-based analysis
- Auto-fixing code
- Running on non-PR events (push to main, scheduled runs)
- Supporting JS or C# in v1

---

## Architecture

```
GitHub PR event
      │
      ▼
┌─────────────────────────┐
│  Orchestrator           │  Fetches diff, identifies changed .py files
└──────────┬──────────────┘
           │ (per file)
           ▼
┌─────────────────────────┐
│  Lint Runner            │  Runs pylint, parses JSON output into findings
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│  GitHub Client          │  Validates line numbers against diff, posts review
└──────────┬──────────────┘
           │
           ▼
    Inline PR review comments (critical/medium)
  + Separate issue comment with <details> summary (low)
  + exit code 1 if any findings
```

### Components

**Orchestrator** (`orchestrator.py`)
Fetches the PR diff via PyGithub. For each changed file, checks if it matches a supported language (`.py` in v1). Skips files matching `ignore_paths`. Passes each file's content and patch to the lint runner.

**Lint Runner** (`linter.py`)
Writes the file content to a temp path, runs `pylint --output-format=json`, parses the JSON output. Maps pylint message types to severities. Returns a list of `Finding` objects.

**GitHub Client** (`github_client.py`)
Validates each finding's line number against the actual diff hunk (only lines in the diff can receive inline comments). Snaps to the nearest diff line when the linter reports a line outside the hunk.

Posts two things:
1. A PR review (`POST /pulls/{n}/reviews`) with inline comments for `critical` and `medium` findings
2. A separate issue comment (`POST /issues/{n}/comments`) with a `<details>` HTML block listing all `low` findings (collapsible in GitHub's markdown), plus a brief summary of total findings

**Models** (`models.py`)
`Finding` dataclass:
```python
@dataclass
class Finding:
    filename: str
    line_number: int
    severity: str      # "critical" | "high" | "medium" | "low"
    title: str
    explanation: str
    suggestion: str
```

**Config** (`config.py`)
Loads `.qa.yaml` from the consuming repo root if present. Falls back to built-in defaults. Env var `QA_MODE` takes precedence.

**Main** (`main.py`)
Entry point. Reads env vars, runs the pipeline, posts the review and summary comment, exits with code 1 if any findings, 0 if clean.

---

## Pylint configuration

A default `pylintrc` is bundled inside the Docker image. It:
- Enables all error and warning checks
- Disables noisy convention checks (`C0114` missing module docstring, `C0115` missing class docstring, `C0116` missing function docstring)
- Sets `max-line-length = 120`
- Sets `max-args = 7`

Consuming repos can override by placing a `.pylintrc` or `pyproject.toml` `[tool.pylint]` section at their repo root — the runner detects and uses it automatically.

---

## Severity mapping

| Pylint type | Code prefix | Mapped severity |
|-------------|-------------|-----------------|
| Fatal       | F           | critical        |
| Error       | E           | critical        |
| Warning     | W           | medium          |
| Convention  | C           | low             |
| Refactor    | R           | low             |

`critical` and `medium` findings are posted as inline review comments. `low` findings appear in a collapsible `<details>` block in a separate PR issue comment.

---

## GitHub review posting

Two API calls per run (when findings exist):

1. **`POST /repos/{owner}/{repo}/pulls/{pr}/reviews`** — creates a review with `COMMENT` event containing all `critical`/`medium` inline comments
2. **`POST /repos/{owner}/{repo}/issues/{pr}/comments`** — creates a summary comment with:
   - Total finding counts by severity
   - `<details><summary>Low severity findings</summary>...</details>` block listing `low` findings

If no `low` findings exist, the `<details>` block is omitted. If no `critical`/`medium` findings exist, the review call is skipped.

---

## GitHub Action packaging

**`action.yml`**
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

**`Dockerfile`**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir pylint PyGithub

COPY qa/ ./qa/
COPY default.pylintrc .

ENV PYTHONPATH=/app

ENTRYPOINT ["python", "-m", "qa.main"]
```

---

## Consuming repo workflow

Repos add `.github/workflows/qa.yml`:

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

---

## Optional configuration (`.qa.yaml`)

```yaml
qa:
  severity_filter:        # which severities trigger inline comments
    - critical
    - medium
  max_comments_per_pr: 20
  ignore_paths:
    - "migrations/*"
    - "tests/*"
  languages:              # for future use; v1 only supports python
    - python
```

All fields are optional. Defaults shown above apply when the file is absent.

---

## Pass/fail behaviour

| Situation | Exit code | Actions result |
|-----------|-----------|----------------|
| No `.py` files changed | 0 | Pass |
| `.py` files changed, no findings | 0 | Pass |
| Any findings found | 1 | Fail |

---

## Project structure

```
agentic-github-qa-check/
├── action.yml
├── Dockerfile
├── default.pylintrc
├── requirements.txt         # PyGithub only (pylint installed separately)
├── qa/
│   ├── __init__.py
│   ├── main.py              # entry point
│   ├── orchestrator.py      # fetches diff, routes files to linter
│   ├── linter.py            # runs pylint, parses output, returns findings
│   ├── github_client.py     # posts review + summary issue comment
│   ├── models.py            # Finding dataclass
│   └── config.py            # loads .qa.yaml with defaults
└── README.md
```

---

## Error handling

| Scenario | Behaviour |
|----------|-----------|
| Pylint not installed / crashes | Log error, skip file, note in summary |
| File not decodable (binary) | Skip silently |
| Line number outside diff hunk | Snap to nearest diff line |
| GitHub API 422 on inline comment | Skip that comment, still post summary |
| No `.py` files in PR | Post "No Python files changed" summary comment, exit 0 |
| `.qa.yaml` invalid | Fall back to defaults, log warning |

---

## Future language support

Adding JavaScript or C# requires:
1. Install the tool in `Dockerfile` (`npm install -g eslint` / `dotnet tool install dotnet-format`)
2. Add a runner class in `linter.py` for the new language
3. Add file extension detection in `orchestrator.py`
4. Add a default config for the new linter bundled in the image

No structural changes needed.
