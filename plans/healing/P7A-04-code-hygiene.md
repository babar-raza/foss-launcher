# P7A-04 — Code Hygiene: Import Consistency + Stale Docstring

## Status: Done

## Gap Linkage: G-04, G-05

Two minor code hygiene issues:

1. **G-04**: `PAGE_ROLE_SKELETONS` is imported lazily (inside method) in `planner/worker.py`
   but at top-level in `frontmatter.py`. Inconsistent pattern.
2. **G-05**: Test class docstring in `test_ir_renderer.py` says "for non-code blocks"
   but the tests now cover all block types including code blocks.

## Role

Senior engineer. Minimal cleanup, no behavioral changes.

## Scope

### Fix

**Import consistency** — Move the lazy import in `planner/worker.py` `self_review()`
to a top-level import:

```python
# At top of file, add:
from launcher.shared.page_skeletons import PAGE_ROLE_SKELETONS

# In self_review(), replace:
#     from launcher.shared.page_skeletons import PAGE_ROLE_SKELETONS
#     valid_roles = set(PAGE_ROLE_SKELETONS.keys())
# With:
        valid_roles = set(PAGE_ROLE_SKELETONS.keys())
```

This is safe because `page_skeletons` has no imports from the planner package
(dependency is one-way: planner → shared). The module already imports from
`launcher.shared.page_skeletons` via `resolve_skeleton` in `plan.py`.

**Stale docstring** — In `tests/unit/test_ir_renderer.py` line 9:

```python
# Old:
"""Verify claim citations are stripped at render time for non-code blocks."""
# New:
"""Verify claim citations are stripped at render time for all block types."""
```

### Allowed paths

- `src/launcher/workers/planner/worker.py`
- `tests/unit/test_ir_renderer.py`

### Forbidden

Any path not listed above.

## Acceptance Checks

- CLI: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --ignore=tests/test_planner_per_module.py` — all pass
- Tests: no new tests needed (behavioral no-op)
- Config respected end-to-end: N/A
- No mock data in production paths: N/A

## Deliverables

- Modified `src/launcher/workers/planner/worker.py` — import moved to top level
- Modified `tests/unit/test_ir_renderer.py` — docstring corrected

## Hard Rules

- No behavioral changes
- No new dependencies
- Verify no circular import introduced

## Review Dimensions — What 5/5 Means

| Dimension | 5/5 Criteria |
|-----------|-------------|
| Consistency | Same import pattern used in both frontmatter.py and planner/worker.py |
| Minimality | 2 lines changed total |
| Correctness | Docstring matches actual test coverage |

## Now (Runbook)

```bash
# 1. Edit planner/worker.py: move import to top, remove from self_review body
# 2. Edit test_ir_renderer.py: fix docstring

# 3. Verify no circular import
.venv/Scripts/python.exe -c "from launcher.workers.planner.worker import PlannerWorker; print('OK')"

# 4. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --ignore=tests/test_planner_per_module.py
```
