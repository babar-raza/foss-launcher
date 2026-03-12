---
id: TC-4072
title: "Strengthen IntakeWorker self_review and repo_signals manifest detection"
status: Done
priority: High
owner: agent
updated: "2026-03-11"
tags: [phase1, intake, self-review, multi-language]
depends_on: [TC-4070]
allowed_paths:
  - plans/taskcards/TC-4072_intake_self_review_hardening.md
  - src/launcher/workers/intake/worker.py
  - tests/unit/workers/test_intake.py
evidence_required:
  - reports/TC-4072/evidence.md
---

# Taskcard TC-4072 — Strengthen IntakeWorker self_review

## Objective

Add two self_review findings to detect (1) Python-shaped canonical_import on non-Python platforms
and (2) missing runtime_import for Python; and enrich `_build_repo_signals()` with manifest file
detection so the acquisition artifact shows what was found in the cloned repo.

## Required spec references

- `specs/worker_understand.md` (self_review contract)
- `configs/families.yaml` (platform import templates)

## Scope

### In scope
- `IntakeWorker.self_review()`: add Python-shaped import check for non-Python
- `IntakeWorker.self_review()`: add runtime_import empty check for Python (medium severity)
- `_build_repo_signals()`: detect manifest files (package.json, pyproject.toml, etc.)
- Add `detected_manifest_files: list[str]` and `inferred_language: str` to artifact

### Out of scope
- Changing identity derivation (TC-4070)
- Scout separation (Phase 2)

## Implementation steps

### Step 1: Strengthen self_review()
After existing checks, add:
```python
# Check for Python-shaped canonical_import on non-Python platforms
if output.platform not in ("python",) and output.canonical_import.endswith("_foss"):
    findings.append({
        "category": "identity",
        "severity": "high",
        "message": (
            f"canonical_import '{output.canonical_import}' appears Python-shaped "
            f"(ends with '_foss') for non-Python platform '{output.platform}'. "
            "families.yaml may be missing a platform entry for this platform."
        ),
    })

# Check for empty runtime_import on Python
if output.platform == "python" and not output.runtime_import:
    findings.append({
        "category": "identity",
        "severity": "medium",
        "message": (
            "runtime_import is empty for Python platform. "
            "families.yaml python.runtime_import_tpl should provide this."
        ),
    })
```

### Step 2: Enrich _build_repo_signals()
After enumerating `children`, scan for manifest files:
```python
MANIFEST_MAP = {
    "package.json": "node/typescript",
    "pyproject.toml": "python",
    "setup.py": "python",
    "setup.cfg": "python",
    "go.mod": "go",
    "Cargo.toml": "rust",
    "pom.xml": "java",
    "build.gradle": "java",
    "Gemfile": "ruby",
    "composer.json": "php",
}
detected_manifest_files = []
inferred_language = ""
for c in children:
    if c.is_file():
        name = c.name.lower()
        if name in MANIFEST_MAP:
            detected_manifest_files.append(c.name)
            if not inferred_language:
                inferred_language = MANIFEST_MAP[name]
        # *.csproj detection
        if c.suffix.lower() == ".csproj":
            detected_manifest_files.append(c.name)
            if not inferred_language:
                inferred_language = "dotnet"
        # *.gemspec detection
        if c.suffix.lower() == ".gemspec":
            detected_manifest_files.append(c.name)
            if not inferred_language:
                inferred_language = "ruby"
```
Add `detected_manifest_files` and `inferred_language` to the return dict.

## Failure modes

1. If `platform` field in IntakeBundle is not exactly `"python"`, the platform check may miss
   case-variant strings — mitigation: use `output.platform.lower() == "python"` in check
2. `_build_repo_signals` may raise on unusual file permissions — already wrapped in `except OSError`
3. Multiple manifest files from the same language — `detected_manifest_files` is a list, `inferred_language` takes first match

## Task-specific review checklist

- [ ] self_review returns `passed=False` for platform="typescript", canonical_import="cells_foss"
- [ ] self_review returns `passed=True` for platform="typescript", canonical_import="@aspose/cells"
- [ ] self_review returns `passed=True` with medium finding for platform="python", runtime_import=""
- [ ] `_build_repo_signals` with package.json → `inferred_language="node/typescript"`, `detected_manifest_files=["package.json"]`
- [ ] `_build_repo_signals` with pyproject.toml → `inferred_language="python"`
- [ ] OSError in manifest scan does not crash (already guarded by outer try/except OSError)

## Deliverables

- Updated `src/launcher/workers/intake/worker.py`
- Updated `tests/unit/workers/test_intake.py`

## Acceptance checks

- [x] `pytest tests/unit/workers/test_intake.py -v` all pass (78 passed, verified 2026-03-11)
- [x] self_review fails hard (passed=False) for Python-shaped import on TypeScript platform (line 216 in worker.py)

## E2E verification

`pytest tests/unit/workers/test_intake.py -x`

## Integration boundary proven

intake_bundle.json produced for any platform now shows `detected_manifest_files` and
`inferred_language`, giving reviewers immediate structural insight without reading source code.
