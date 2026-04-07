# Multi-Language Support (v2) — Design Document

**Status:** Approved
**Last updated:** April 2026

---

## Overview

v2 adds JavaScript, TypeScript, and C# linting to the existing Python-only action. The architecture follows the extension path outlined in the v1 spec: new runners in `linter.py`, new extension detection in `orchestrator.py`, new tools in the `Dockerfile`. No structural changes.

**Tools:**
- JS/TypeScript: ESLint with bundled `default.eslintrc.json`
- C#: `dotnet-format --verify-no-changes` (formatting only)
- Python: pylint (unchanged)

---

## Changes

### `qa/linter.py`

`lint_file()` becomes the dispatch function. It routes internally by file extension to private runners. The orchestrator call site is unchanged.

```
lint_file(filename, content, pylintrc=None)
  ├── .py          → _lint_python()   (existing logic, extracted)
  ├── .js .jsx .ts .tsx .mjs .cjs → _lint_js_ts()
  └── .cs          → _lint_cs()
```

**`_lint_python()`** — existing pylint logic moved as-is.

**`_lint_js_ts()`** — writes content to a temp file preserving the original extension (so ESLint's TypeScript parser activates on `.ts`/`.tsx`). Runs:
```
eslint --format json --no-eslintrc -c /app/default.eslintrc.json <tmpfile>
```
Parses JSON output: `messages[].severity` and `messages[].line`.

**`_lint_cs()`** — writes content to a temp `.cs` file in a temp directory alongside a minimal `.csproj`. Runs:
```
dotnet format <tmpdir> --verify-no-changes --report <report.json>
```
Parses the JSON report: `[].FileChanges[].LineNumber` and `FormatDescription`.

### `qa/orchestrator.py`

Replace the `.py`-only extension check with:

```python
SUPPORTED_EXTENSIONS = {".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".cs"}
```

### `Dockerfile`

Add to the existing `python:3.11-slim` image:
- Node.js 20 (via NodeSource)
- `npm install -g eslint @typescript-eslint/parser @typescript-eslint/eslint-plugin`
- .NET SDK 8 (via Microsoft package feed)
- `dotnet-format` is built into the .NET 6+ SDK — no extra install needed

### New file: `default.eslintrc.json`

```json
{
  "env": { "browser": true, "es2021": true, "node": true },
  "extends": ["eslint:recommended"],
  "overrides": [
    {
      "files": ["*.ts", "*.tsx"],
      "parser": "@typescript-eslint/parser",
      "plugins": ["@typescript-eslint"],
      "extends": ["eslint:recommended", "plugin:@typescript-eslint/recommended"]
    }
  ],
  "parserOptions": { "ecmaVersion": "latest", "sourceType": "module" }
}
```

---

## Severity mapping

| Tool | Output | Severity |
|------|--------|----------|
| pylint Fatal/Error | F/E | critical |
| pylint Warning | W | medium |
| pylint Convention/Refactor | C/R | low |
| ESLint | severity 2 (error) | critical |
| ESLint | severity 1 (warning) | medium |
| dotnet-format | any formatting issue | low |

---

## Error handling

| Scenario | Behaviour |
|----------|-----------|
| ESLint not installed / crashes | Log error, skip file, note in summary |
| `dotnet` not installed / crashes | Log error, skip file, note in summary |
| dotnet-format report missing/empty | Skip file silently |
| `.cs` file has no basename | Skip file |
| ESLint JSON parse error | Return empty findings |

---

## Versioning

- Tag `v2` after merging to main
- `v1` tag stays pointing at the Python-only commit — existing consumers unaffected
- `action.yml` inputs are unchanged — v2 is a drop-in upgrade

---

## dotnet-format temp project

dotnet-format requires a project file. For each `.cs` file:

1. Create temp directory
2. Write `<basename>.cs` into it
3. Write minimal `project.csproj`:
   ```xml
   <Project Sdk="Microsoft.NET.Sdk">
     <PropertyGroup>
       <TargetFramework>net8.0</TargetFramework>
     </PropertyGroup>
   </Project>
   ```
4. Run `dotnet format <tmpdir> --verify-no-changes --report <report.json>`
5. Parse report, clean up temp directory in `finally`

---

## Files changed

| File | Change |
|------|--------|
| `qa/linter.py` | Add dispatch + two new private runners |
| `qa/orchestrator.py` | Replace `.py` check with `SUPPORTED_EXTENSIONS` set |
| `Dockerfile` | Add Node.js 20, ESLint + TS plugins, .NET SDK 8 |
| `default.eslintrc.json` | New — bundled ESLint config |
| `tests/test_linter.py` | Add tests for JS/TS and C# runners |
| `tests/test_orchestrator.py` | Add tests for new extension filtering |
