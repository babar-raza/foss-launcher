---
id: TC-3906-H3
title: "Make grade_ge public; fix private-symbol import in phase_promoter"
status: Done
priority: P1 / High
owner: unassigned
updated: "2026-03-09"
tags: [snapshot, code-quality, coupling]
depends_on: []
allowed_paths:
  - plans/healing/TC-3906-H3-grade-ge-extraction.md
  - src/launcher/deploy/promoter.py
  - src/launcher/deploy/phase_promoter.py
---

# TC-3906-H3 — Make `grade_ge` public; remove private-symbol import

## Status: Not Started

## Gap linkage

- **G-3906-03**: `phase_promoter.py` imports `_grade_ge` and `GRADE_RANK` from `promoter.py`
  using `from .promoter import GRADE_RANK, _grade_ge`. The leading underscore on `_grade_ge`
  signals it is a module-private implementation detail. Importing another module's private
  symbol is a coupling anti-pattern that breaks silently when `promoter.py` is refactored.

## Role

Senior engineer. Drop-in, production-ready.

## Scope

### Fix:

**`src/launcher/deploy/promoter.py`** — Rename `_grade_ge` → `grade_ge` (remove underscore).
Update the single internal call site (`if not _grade_ge(grade, min_grade)` on line ~166 and
`if not _grade_ge(grade, existing.grade)` on line ~207) to use `grade_ge`.

`GRADE_RANK` is already public (no underscore) — no change needed there.

**`src/launcher/deploy/phase_promoter.py`** — Update import:

```python
# BEFORE:
from .promoter import GRADE_RANK, _grade_ge

# AFTER:
from .promoter import GRADE_RANK, grade_ge
```

Update the two call sites inside `promote_phase_snapshots()`:

```python
# BEFORE:
if not _grade_ge(grade, min_grade): ...
if not _grade_ge(grade, existing.grade): ...

# AFTER:
if not grade_ge(grade, min_grade): ...
if not grade_ge(grade, existing.grade): ...
```

No other files are affected. `grade_ge` is not exported from `__init__.py` and not used
outside `promoter.py` + `phase_promoter.py` currently.

### Allowed paths:
- `plans/healing/TC-3906-H3-grade-ge-extraction.md`
- `src/launcher/deploy/promoter.py`
- `src/launcher/deploy/phase_promoter.py`

### Forbidden: any other file/path

## Acceptance checks

### CLI:
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=no | tail -3
```
Passes with ≥ 3183 tests.

```bash
python -c "from launcher.deploy.promoter import grade_ge, GRADE_RANK; print('OK')"
python -c "from launcher.deploy.phase_promoter import promote_phase_snapshots; print('OK')"
```
Both print `OK` without ImportError.

### UI/Web/API:
N/A.

### Tests:
No new tests needed for this rename alone. TC-3906-H2 tests will exercise `grade_ge`
via `promote_phase_snapshots`. Confirm existing tests still pass after rename.

### Config respected end-to-end:
Grade-filtering behaviour is unchanged — only the symbol name changes.

### No mock data in production paths:
N/A for a rename.

## Deliverables

1. **`src/launcher/deploy/promoter.py`** — Full file replacement. Rename `_grade_ge` →
   `grade_ge` at definition and both call sites. No other changes.
2. **`src/launcher/deploy/phase_promoter.py`** — Full file replacement. Update import and
   two call sites. No other changes.

Full file replacements — no stubs, no TODOs.

## Hard rules

- Public signature of `promote_run()` and `promote_phase_snapshots()` unchanged.
- `grade_ge` docstring: "True if candidate grade is equal or better than incumbent."
- No new deps.
- `GRADE_RANK` stays as-is (already public).

## Review dimensions

| Dimension | 5/5 target for this TC |
|-----------|------------------------|
| Maintainability | No module imports a private symbol from another module |
| Minimality | ≤5 lines changed across both files |
| Correctness | Grade filtering behaviour identical before and after |
| Integration fit | `grade_ge` importable by any future module in `launcher.deploy.*` |

## Now (runbook)

```bash
# 1. Find all occurrences of _grade_ge
grep -rn "_grade_ge" src/launcher/

# 2. Rename in promoter.py (definition + 2 call sites)

# 3. Update import + 2 call sites in phase_promoter.py

# 4. Smoke-test imports
python -c "from launcher.deploy.promoter import grade_ge; print(grade_ge)"
python -c "from launcher.deploy.phase_promoter import promote_phase_snapshots; print('OK')"

# 5. Full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=no | tail -3
```
