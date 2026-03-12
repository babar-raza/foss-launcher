---
id: TC-3862
title: "worker.py call-site: pass product_name to check_seo, canonical_import to check_code; fix code.py import logic"
status: Done
priority: High
owner: agent
updated: "2026-03-08"
tags: [evaluate, worker, seo, code, call-site]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-3862_worker_callsite_seo_code_canonical.md
  - src/launcher/workers/evaluate/worker.py
  - src/launcher/workers/evaluate/checks/code.py
evidence_required:
  - reports/TC-3862/evidence.md
---

# Taskcard TC-3862 — worker.py call-site: pass product_name to check_seo, canonical_import to check_code; fix code.py import logic

## Objective

`_run_deterministic_checks()` silently drops `product_name` when calling `check_seo` and
lacks `canonical_import` entirely, disabling two sub-checks. Additionally, `code.py`'s
import allowlist logic is inverted: when no allowlist is provided, non-canonical imports
silently pass instead of being flagged.

## Required spec references

- `src/launcher/workers/evaluate/worker.py` (call-site)
- `src/launcher/workers/evaluate/checks/code.py` (import allowlist logic)

## Scope

### In scope
- Add `canonical_import: str = ""` to `_run_deterministic_checks()` signature
- Thread `canonical_import` from `context.config` into `run()` call
- Pass `product_name=product_name` to `check_seo` call
- Pass `canonical_import=canonical_import` to `check_code` call
- Fix inverted import allowlist logic in `code.py`

### Out of scope
- Changes to `check_seo()` internals beyond receiving `product_name`
- Changes to `check_code()` beyond fixing the allowlist logic
- Any other worker.py changes

## Inputs

- `src/launcher/workers/evaluate/worker.py`
- `src/launcher/workers/evaluate/checks/code.py`

## Outputs

- Modified `worker.py` with correct call-site parameter passing
- Modified `code.py` with corrected allowlist logic

## Allowed paths

- plans/taskcards/TC-3862_worker_callsite_seo_code_canonical.md
- src/launcher/workers/evaluate/worker.py
- src/launcher/workers/evaluate/checks/code.py

### Allowed paths rationale
Only the call-site in worker.py and the logic bug in code.py are modified.

## Implementation steps

### Step 1: Add canonical_import to _run_deterministic_checks() signature

Change:
```python
def _run_deterministic_checks(
    content: str, slug: str, *, page_role: str = "", product_name: str = "",
) -> list[Finding]:
```
To:
```python
def _run_deterministic_checks(
    content: str, slug: str, *, page_role: str = "", product_name: str = "", canonical_import: str = "",
) -> list[Finding]:
```

### Step 2: Pass product_name to check_seo and canonical_import to check_code

Change `check_seo(content, slug)` → `check_seo(content, slug, product_name=product_name)`
Change `check_code(content, slug)` → `check_code(content, slug, canonical_import=canonical_import)`

### Step 3: Thread canonical_import from context.config in the run() call site

Change:
```python
findings = _run_deterministic_checks(
    content, gen_page.slug, page_role=gen_page.page_role, product_name=product_name,
)
```
To:
```python
findings = _run_deterministic_checks(
    content, gen_page.slug,
    page_role=gen_page.page_role,
    product_name=product_name,
    canonical_import=context.config.canonical_import or "",
)
```

### Step 4: Fix inverted import allowlist logic in code.py

Current (inverted — non-canonical imports pass silently when no allowlist):
```python
if canonical_import not in stripped and import_allowlist:
    if not any(allowed in stripped for allowed in import_allowlist):
        findings.append(...)
```
Correct (flag if canonical missing AND (no allowlist OR not in allowlist)):
```python
if canonical_import not in stripped:
    if not import_allowlist or not any(allowed in stripped for allowed in import_allowlist):
        findings.append(...)
```

## Failure modes

### Failure mode 1: canonical_import not in context.config

**Detection**: `AttributeError: 'RunConfig' object has no attribute 'canonical_import'`
**Resolution**: Use `getattr(context.config, "canonical_import", "") or ""` as fallback
**Gate**: Test with config missing canonical_import → no crash, empty string used

### Failure mode 2: check_seo product_name sub-checks now fire unexpectedly

**Detection**: Existing tests for check_seo fail due to product_name now being passed
**Resolution**: Tests should already cover product_name; if not, confirm behavior is correct
**Gate**: `pytest tests/ -k check_seo`

### Failure mode 3: code.py logic change causes over-flagging

**Detection**: Pages with valid alternative imports get flagged
**Resolution**: Verify import_allowlist is populated correctly in config; the fix is correct
**Gate**: Test page with allowlist entry that matches → no finding; page with no match → finding

## Task-specific review checklist

1. [ ] `_run_deterministic_checks` signature has `canonical_import: str = ""`
2. [ ] `check_seo` called with `product_name=product_name`
3. [ ] `check_code` called with `canonical_import=canonical_import`
4. [ ] `run()` passes `context.config.canonical_import or ""` to the deterministic checks call
5. [ ] `code.py` allowlist logic: flag when canonical absent AND (no allowlist OR no match)
6. [ ] No other call sites of `_run_deterministic_checks` broken
7. [ ] Docstrings updated for all new/changed public functions
8. [ ] Spec file updated if worker behavior changed (or confirmed no spec drift)
9. [ ] Schema `"description"` fields present for all new/changed properties

## Deliverables

1. `src/launcher/workers/evaluate/worker.py` — modified call-sites
2. `src/launcher/workers/evaluate/checks/code.py` — fixed allowlist logic

## Acceptance checks

1. [x] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x` — all pass
2. [x] Page with wrong import + no allowlist → finding emitted
3. [x] Page with import in allowlist → no finding

## Self-review

### Verification results
- [x] Tests: 2863/2863 PASS
- [x] Evidence captured: reports/TC-3862/evidence.md

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -v
```

## Integration boundary proven

**Upstream**: `run()` in `worker.py` provides `context.config.canonical_import`
**Downstream**: `check_code()` and `check_seo()` receive their required parameters
**Contract**: Non-canonical imports flagged; product name in title validated
