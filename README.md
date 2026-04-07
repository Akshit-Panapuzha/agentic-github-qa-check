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
