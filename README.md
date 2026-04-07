# agentic-github-qa-check

A Docker-based GitHub Action that lints changed files in a PR and posts inline review comments. Fails the Actions run when any lint issues are found.

Supports Python, JavaScript, TypeScript, and C#.

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
        uses: Akshit-Panapuzha/agentic-github-qa-check@v2
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
          pr-number: ${{ github.event.pull_request.number }}
          repo: ${{ github.repository }}
          base-sha: ${{ github.event.pull_request.base.sha }}
          head-sha: ${{ github.event.pull_request.head.sha }}
```

No additional secrets required beyond the built-in `GITHUB_TOKEN`.

## Supported languages

| Language | Extensions | Tool |
|----------|------------|------|
| Python | `.py` | pylint |
| JavaScript | `.js` `.jsx` `.mjs` `.cjs` | ESLint |
| TypeScript | `.ts` `.tsx` | ESLint + @typescript-eslint |
| C# | `.cs` | dotnet-format |

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

| Tool | Output | Severity | Behaviour |
|------|--------|----------|-----------|
| pylint | Fatal / Error | critical | Inline PR review comment |
| pylint | Warning | medium | Inline PR review comment |
| pylint | Convention / Refactor | low | Collapsible summary comment |
| ESLint | error (severity 2) | critical | Inline PR review comment |
| ESLint | warning (severity 1) | medium | Inline PR review comment |
| dotnet-format | formatting issue | low | Collapsible summary comment |

## Pass/fail

Exits 1 (fail) if any findings, 0 if clean.
