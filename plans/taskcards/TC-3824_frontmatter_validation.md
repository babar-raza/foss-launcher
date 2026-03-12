---
id: TC-3824
title: "Frontmatter validation hardening: FrontmatterError + robots at plan time"
status: In-Progress
priority: Critical
owner: agent
updated: "2026-03-08"
tags: [frontmatter, ir-renderer, planner, generate-worker, engineering-fix]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-3824_frontmatter_validation.md
  - src/launcher/util/errors.py
  - src/launcher/shared/ir_renderer.py
  - src/launcher/workers/planner/plan.py
  - src/launcher/workers/generate/worker.py
  - tests/unit/shared/test_ir_renderer.py
  - tests/unit/workers/test_plan_slug_integration.py
evidence_required:
  - reports/TC-3824/evidence.md
---

# Taskcard TC-3824 — Frontmatter validation hardening: FrontmatterError + robots at plan time

## Objective

Close two structural defects in frontmatter handling: (1) `ir_renderer.render_page()` silently
emits empty or YAML-invalid frontmatter; (2) the planner never sets `robots`, leaving every page
without a robots directive until the optional SEO phase. Adds a `FrontmatterError` type so
failures are scoped to the page level (not run level) with full observability via events.ndjson.

## Required spec references

- `specs/02_content_model.md` (Section: Frontmatter required fields)
- `specs/08_quality_gates.md` (Section: frontmatter gate — required/recommended fields)

## Scope

### In scope
- New `FrontmatterError` exception class in `errors.py`
- Frontmatter validation (None rejection, required-key check, YAML round-trip) in `ir_renderer.render_page()`
- Adding `robots` to planner's `_build_frontmatter()` output
- Canonical URL fallback in generate worker Phase 1.5
- FrontmatterError catch in generate worker Phase 3, emitting `issue_opened` event

### Out of scope
- Changing SEO phase logic (TC-3827)
- Fixing missing SEO fields (seoTitle, keywords) — those are TC-3827
- Adding new required frontmatter fields beyond what's already defined

## Inputs

- `src/launcher/shared/ir_renderer.py` — render_page function
- `src/launcher/workers/planner/plan.py` — _build_frontmatter function
- `src/launcher/workers/generate/worker.py` — Phase 1.5 SEO loop and Phase 3 render loop
- `src/launcher/util/errors.py` — base error hierarchy

## Outputs

- `FrontmatterError` available from `launcher.util.errors`
- `render_page()` raises `FrontmatterError` on invalid FM instead of emitting `---\n---`
- Every planned page has `robots` set to a valid robots directive string
- Every rendered page with a `url` gets a `canonical` field via deterministic fallback
- Phase 3 `issue_opened` events in events.ndjson for any pages with invalid frontmatter

## Allowed paths

- plans/taskcards/TC-3824_frontmatter_validation.md
- src/launcher/util/errors.py
- src/launcher/shared/ir_renderer.py
- src/launcher/workers/planner/plan.py
- src/launcher/workers/generate/worker.py
- tests/unit/shared/test_ir_renderer.py
- tests/unit/workers/test_plan_slug_integration.py

### Allowed paths rationale
- `errors.py`: new exception class
- `ir_renderer.py`: validation logic
- `plan.py`: robots field added to _build_frontmatter
- `worker.py`: canonical fallback + FrontmatterError catch
- test files: coverage for the above

## Implementation steps

### Step 1: Add FrontmatterError to errors.py

Add after `ValidationError`:
```python
class FrontmatterError(LaunchError):
    """Raised when page frontmatter is missing required fields, contains None values,
    or fails YAML round-trip verification. Scoped to a single page; callers should
    catch and emit an issue_opened event rather than aborting the run."""
    def __init__(
        self,
        message: str,
        *,
        page_id: str = "",
        missing_keys: list[str] | None = None,
        invalid_keys: list[str] | None = None,
        detail: str = "",
    ) -> None:
        super().__init__(message)
        self.page_id = page_id
        self.missing_keys: list[str] = missing_keys or []
        self.invalid_keys: list[str] = invalid_keys or []
        self.detail = detail
```

### Step 2: Add validation to ir_renderer.render_page()

Required keys: `{"title", "slug", "type", "url", "weight", "family", "platform", "page_role"}`.
Three checks before yaml.dump:
1. Null rejection: collect keys with `v is None` → raise FrontmatterError(invalid_keys=...)
2. Missing keys: `_REQUIRED_FM_KEYS - fm.keys()` → raise FrontmatterError(missing_keys=...)
3. After yaml.dump, yaml.safe_load round-trip: verify key count matches original

Remove the `else: parts.append("---\n---")` branch entirely.

### Step 3: Add robots to plan.py _build_frontmatter()

Inline the same logic as `seo_metadata._robots_directive`:
```python
robots = "noindex, follow" if slug == "_index" or page.page_role == "toc" else "index, follow"
```
Add `"robots": robots` to the `fm` dict.

### Step 4: Add canonical fallback in generate worker Phase 1.5

After the SEO optimization for-loop (before Phase 2), add a deterministic canonical fill:
for each page_ir that still lacks a `canonical` or has an empty `canonical`, call
`_generate_canonical(url, page_ir.page_role, subdomain_map=subdomain_map)` and set it.

### Step 5: Add FrontmatterError catch in generate worker Phase 3

Wrap `render_page(linked_ir)` in try/except FrontmatterError. On catch:
- Log error with page_id
- Emit `context.emit_event("issue_opened", {...}, worker=self.name)`
- Increment `frontmatter_failures` counter
- `continue` (skip file writes for this page)

Initialize `frontmatter_failures = 0` before Phase 3. Include it in manifest stats.

### Step 6: Write tests

`tests/unit/shared/test_ir_renderer.py`:
- None value → FrontmatterError with invalid_keys
- Missing required key → FrontmatterError with missing_keys
- Non-serializable value (custom class) → FrontmatterError
- Valid FM → correct markdown output (regression)

`tests/unit/workers/test_plan_slug_integration.py`:
- After _build_frontmatter: `robots` field present and is a non-empty string
- `robots` = `"noindex, follow"` for slug `_index` or page_role `toc`
- `robots` = `"index, follow"` for regular content page role

## Failure modes

### Failure mode 1: render_page called with empty frontmatter from a third path

**Detection**: `FrontmatterError: missing required keys` in test or pilot run
**Resolution**: Trace which worker produces the empty-FM PageIR; add robots/required fields there
**Gate**: frontmatter check gate

### Failure mode 2: robots field breaks existing tests expecting exact FM dict keys

**Detection**: `AssertionError` in existing plan slug integration tests
**Resolution**: Update assertions to accept additional keys OR check field-by-field instead of
  comparing full dicts
**Gate**: pytest -x

### Failure mode 3: circular import errors.py ↔ ir_renderer.py ↔ worker

**Detection**: `ImportError` at test time
**Resolution**: `FrontmatterError` lives in `util/errors.py` which is a leaf module with no
  launcher imports — no circular import possible
**Gate**: pytest -x --import-mode=importlib

## Task-specific review checklist

1. [ ] `FrontmatterError` has `page_id`, `missing_keys`, `invalid_keys`, `detail` fields
2. [ ] `render_page()` rejects None values with `invalid_keys` populated
3. [ ] `render_page()` rejects missing required keys with `missing_keys` populated
4. [ ] `render_page()` performs YAML round-trip verification after yaml.dump
5. [ ] `_build_frontmatter()` sets `robots` as a non-empty string for every page
6. [ ] Generate worker Phase 3 catches FrontmatterError per-page, emits issue_opened, continues
7. [ ] Generate worker Phase 1.5 fills `canonical` if missing after SEO phase
8. [ ] No `None` values in any frontmatter dict can reach yaml.dump
9. [ ] All new tests pass with PYTHONHASHSEED=0
10. [ ] No existing tests broken

## Deliverables

1. Modified `src/launcher/util/errors.py` with FrontmatterError
2. Modified `src/launcher/shared/ir_renderer.py` with validation
3. Modified `src/launcher/workers/planner/plan.py` with robots field
4. Modified `src/launcher/workers/generate/worker.py` with canonical fallback + catch
5. New `tests/unit/shared/test_ir_renderer.py`
6. Updated `tests/unit/workers/test_plan_slug_integration.py`

## Acceptance checks

1. [ ] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/shared/test_ir_renderer.py tests/unit/workers/test_plan_slug_integration.py -v` — all pass
2. [ ] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q` — 0 failures
3. [ ] `grep -r "FrontmatterError" src/launcher/` shows usage in ir_renderer + worker
4. [ ] `render_page(PageIR(frontmatter={}))` raises FrontmatterError

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: frontmatter gate PASS
- [ ] Evidence captured: reports/TC-3824/evidence.md

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/shared/test_ir_renderer.py tests/unit/workers/test_plan_slug_integration.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

**Expected results**:
- All tests pass
- No `---\n---` empty frontmatter in any rendered page

## Integration boundary proven

**Upstream**: `_build_frontmatter()` in plan.py (produces PlannedPage.frontmatter)
**Downstream**: `render_page()` in ir_renderer (consumes PageIR.frontmatter → markdown string)
**Contract**: frontmatter dict must contain all 8 required keys with non-None string/int values;
  `render_page()` raises `FrontmatterError` if contract is violated
