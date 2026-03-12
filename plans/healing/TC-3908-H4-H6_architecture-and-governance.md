# TC-3908 Healing: Architecture and Governance

Gaps addressed: EX-04, EX-05, EX-06
Taskcards: TC-3908-H4, TC-3908-H5, TC-3908-H6

---

## TC-3908-H4 — Split `_snippets.py` into `_snippets.py` + `_narratives.py`

**Status**: Done
**Gap linkage**: EX-04
**Depends on**: TC-3908-H1 (if H1 modifies `_snippets.py`, this split must happen after)
**Role**: Senior engineer. Drop-in, production-ready.

### Context

`_snippets.py` is 825 lines — 37.5% over the 600-line architectural limit set in TC-3908.
The three ported narrative extraction functions (`_extract_tutorial_narratives`,
`_extract_use_case_narratives`, `_decompose_code_block_into_steps`) are 248 lines of
cohesive, self-contained functionality that belongs in its own module.

Moving them to `_narratives.py` restores `_snippets.py` to ~577 lines (within limit)
and gives the narrative logic its own namespace, making it easy to test, evolve,
and document independently.

### Scope

**Fix**: Extract the three narrative functions (and their helpers/constants) from
`_snippets.py` into a new `_narratives.py` submodule. Update `_snippets.py` to import
from `_narratives.py`. Update `__init__.py` re-exports.

**Allowed paths**:
- `src/launcher/workers/understand/extract/_snippets.py`
- `src/launcher/workers/understand/extract/_narratives.py` (new file)
- `src/launcher/workers/understand/extract/__init__.py`

**Forbidden**: any other file or path.

### Acceptance checks

**CLI — line count gate**:
```bash
wc -l src/launcher/workers/understand/extract/_snippets.py
# Must be ≤ 600

wc -l src/launcher/workers/understand/extract/_narratives.py
# Must be ≤ 350
```

**CLI — import smoke test**:
```bash
python -c "
from launcher.workers.understand.extract._narratives import (
    _extract_tutorial_narratives,
    _extract_use_case_narratives,
    _decompose_code_block_into_steps,
)
print('OK')
"
```

**CLI — package still exports everything**:
```bash
python -c "
from launcher.workers.understand.extract import (
    _extract_tutorial_narratives,
    _extract_use_case_narratives,
    _decompose_code_block_into_steps,
    _extract_snippets,
    _build_doc_contexts,
)
print('ALL EXPORTS OK')
"
```

**Tests**:
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=short 2>&1 | tail -5
# Must match or exceed current passing count
```

**Static analysis**:
```bash
python -m py_compile src/launcher/workers/understand/extract/_snippets.py
python -m py_compile src/launcher/workers/understand/extract/_narratives.py
echo "py_compile OK"
```

**Config respected**: N/A
**No mock data**: N/A — pure refactor, no data flow changes.

### Deliverables

1. **`src/launcher/workers/understand/extract/_narratives.py`** — new file containing:
   - Module docstring explaining narrative extraction purpose
   - All imports needed by the three functions (re, logging, Any, etc.)
   - `_is_prose_like()` helper (if currently only used by narrative functions)
   - `_MAX_CLAIM_TEXT_LENGTH_EXTRACT` constant (or import from `_snippets.py`)
   - `_decompose_code_block_into_steps()`
   - `_extract_use_case_narratives()`
   - `_extract_tutorial_narratives()`
   File must be ≤350 lines.

2. **`src/launcher/workers/understand/extract/_snippets.py`** — full file with the three
   functions removed and replaced with:
   ```python
   from launcher.workers.understand.extract._narratives import (  # noqa: F401
       _extract_tutorial_narratives,
       _extract_use_case_narratives,
       _decompose_code_block_into_steps,
   )
   ```
   File must be ≤600 lines after extraction.

3. **`src/launcher/workers/understand/extract/__init__.py`** — updated to import the
   three narrative functions from `_narratives` instead of `_snippets`. All other
   existing re-exports unchanged.

### Hard rules

- Zero behavior changes — pure structural refactor
- `_build_doc_contexts()` in `_snippets.py` must still call `_extract_tutorial_narratives`
  and `_extract_use_case_narratives` (they're re-imported via the from-import above)
- `__init__.py` must continue to re-export all three functions at the package level
  (existing tests import them from `launcher.workers.understand.extract`)
- No circular imports: `_narratives.py` must NOT import from `_snippets.py`
- `_narratives.py` may import from `_filters.py` or `_linking.py` if needed, not from `_snippets.py`

### Review dimensions (what 5/5 means for this taskcard)

| Dimension | 5/5 means |
|-----------|-----------|
| Minimality | Only 3 files touched; zero behavior changes; git diff shows pure moves |
| Correctness | All tests pass; smoke imports resolve; py_compile clean |
| Maintainability | `_snippets.py` ≤ 600 lines; `_narratives.py` ≤ 350 lines; each has a module docstring |
| Architecture | No circular imports; `_narratives.py` depends only on stdlib + `_filters.py` |
| Consistency | `__init__.py` exports remain identical to before the split |

### Runbook

```bash
# 1. Read _snippets.py lines 1-165 (imports, constants, helpers before _decompose)
#    and 166-353 (three narrative functions)
# 2. Identify which imports/constants are needed ONLY by narrative functions
# 3. Create _narratives.py with module docstring + those imports + 3 functions
# 4. In _snippets.py: delete the 3 function bodies, add the 3-line from-import block
# 5. In __init__.py: change the 3 narrative function re-exports to come from _narratives
# 6. Verify line counts:
wc -l src/launcher/workers/understand/extract/_snippets.py
wc -l src/launcher/workers/understand/extract/_narratives.py
# 7. Smoke test:
python -c "from launcher.workers.understand.extract import _extract_tutorial_narratives, run_extract; print('OK')"
# 8. Full test suite:
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=no 2>&1 | tail -3
```

---

## TC-3908-H5 — Relocate `classify_claim_visibility` to fix inverted dependency direction

**Status**: Done
**Gap linkage**: EX-05
**Depends on**: nothing
**Role**: Senior engineer. Drop-in, production-ready.

### Context

`src/launcher/shared/extract_claims.py` (compat shim) imports from
`src/launcher/workers/understand/extract/_filters.py`. This reverses the
correct dependency direction: `shared/` modules must not depend on `workers/` modules.
`shared/` is for cross-worker utilities; workers depend on shared, not the reverse.

`classify_claim_visibility` is not worker-specific — it classifies claim text by
visibility (public/internal). Its natural home is `src/launcher/shared/classify_claims.py`
alongside `classify_claim`, which already handles related classification logic.

The fix: move `classify_claim_visibility` to `shared/classify_claims.py`, update the
compat shim to import from there, and remove it from `_filters.py`.

### Scope

**Fix**: Move `classify_claim_visibility` (and its 4 supporting constants:
`_INTERNAL_VISIBILITY_TERMS`, `_INTERNAL_VISIBILITY_PATTERN`, `_PRIVATE_MODULE_RE`,
`_PRIVATE_IMPL_RE`) from `_filters.py` to `shared/classify_claims.py`.

**Allowed paths**:
- `src/launcher/shared/classify_claims.py`
- `src/launcher/shared/extract_claims.py`
- `src/launcher/workers/understand/extract/_filters.py`
- `src/launcher/workers/understand/extract/__init__.py`

**Forbidden**: any other file or path.

### Acceptance checks

**CLI — import from new canonical location**:
```bash
python -c "
from launcher.shared.classify_claims import classify_claim_visibility
result = classify_claim_visibility('uses wire protocol internally', 'feature')
assert result == 'internal', f'Expected internal, got {result}'
print('CANONICAL IMPORT OK')
"
```

**CLI — compat shim still works**:
```bash
python -c "
from launcher.shared.extract_claims import classify_claim_visibility
result = classify_claim_visibility('opcode processing', 'feature')
assert result == 'internal'
print('COMPAT SHIM OK')
"
```

**CLI — no inverted dependency**:
```bash
grep -r "workers.understand.extract" src/launcher/shared/
# Must return ZERO matches (no shared module may import from workers)
```

**CLI — __init__.py re-export still works**:
```bash
python -c "
from launcher.workers.understand.extract import classify_claim_visibility
result = classify_claim_visibility('The library supports XLSX', 'feature')
assert result == 'public'
print('PACKAGE EXPORT OK')
"
```

**Tests**:
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/shared/test_claim_visibility_spec_leakage.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=no 2>&1 | tail -3
```

**Config respected**: N/A
**No mock data**: All tests use real classification logic.

### Deliverables

1. **`src/launcher/shared/classify_claims.py`** — full file with `classify_claim_visibility`
   and its 4 supporting constants added after the existing `classify_claim` function.
   Add a section header comment:
   ```python
   # ---------------------------------------------------------------------------
   # Claim visibility classification (ported from TC-3908, relocated from TC-3908-H5)
   # ---------------------------------------------------------------------------
   ```

2. **`src/launcher/shared/extract_claims.py`** — update the compat shim import from:
   ```python
   from launcher.workers.understand.extract._filters import classify_claim_visibility
   ```
   to:
   ```python
   from launcher.shared.classify_claims import classify_claim_visibility
   ```
   Update the module docstring to reflect the new canonical location.

3. **`src/launcher/workers/understand/extract/_filters.py`** — remove the 4 constants
   (`_INTERNAL_VISIBILITY_TERMS`, `_INTERNAL_VISIBILITY_PATTERN`, `_PRIVATE_MODULE_RE`,
   `_PRIVATE_IMPL_RE`) and `classify_claim_visibility` function. File must be ≤ 100 lines
   after removal.

4. **`src/launcher/workers/understand/extract/__init__.py`** — update the
   `classify_claim_visibility` re-export to come from `launcher.shared.classify_claims`
   instead of `launcher.workers.understand.extract._filters`.

### Hard rules

- Behavior of `classify_claim_visibility` must be **bit-for-bit identical** — do NOT
  add terms, remove terms, or change the matching logic during the move
- After this change: `grep -r "workers.understand.extract" src/launcher/shared/` → zero results
- The compat shim `shared/extract_claims.py` must keep re-exporting `classify_claim_visibility`
  (test `tests/unit/shared/test_claim_visibility_spec_leakage.py` imports from there)
- `_filters.py` re-exports via `__init__.py` must still work for any test importing
  `from launcher.workers.understand.extract import classify_claim_visibility`
- No new dependencies introduced

### Review dimensions (what 5/5 means for this taskcard)

| Dimension | 5/5 means |
|-----------|-----------|
| Architecture fit | `shared/` depends only on stdlib and `models/`; no worker imports |
| Correctness | All existing `test_claim_visibility_spec_leakage.py` tests pass unchanged |
| Minimality | Exactly 4 files changed; function body moved verbatim (zero logic changes) |
| Consistency | `classify_claim_visibility` sits beside `classify_claim` in `classify_claims.py` |
| Dependency graph | `shared/ ← workers/understand/extract/` direction restored; `_filters.py` ← `shared/` if needed |

### Runbook

```bash
# 1. Read src/launcher/shared/classify_claims.py (existing file)
# 2. Append the 4 constants and classify_claim_visibility function verbatim
# 3. Read src/launcher/shared/extract_claims.py (12-line shim)
# 4. Update the import line: change _filters to shared.classify_claims
# 5. Read _filters.py — remove the 4 constants + function (lines ~70-107)
# 6. Read __init__.py — update the classify_claim_visibility re-export source
# 7. Verify no inverted dep:
grep -r "workers.understand.extract" src/launcher/shared/
# Must be empty
# 8. Smoke tests:
python -c "from launcher.shared.classify_claims import classify_claim_visibility; print('OK')"
python -c "from launcher.shared.extract_claims import classify_claim_visibility; print('COMPAT OK')"
python -c "from launcher.workers.understand.extract import classify_claim_visibility; print('PKG OK')"
# 9. Full test suite:
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=no 2>&1 | tail -3
```

---

## TC-3908-H6 — Complete TC-3908 governance trail

**Status**: Done
**Gap linkage**: EX-06
**Depends on**: nothing
**Role**: Senior engineer. Drop-in, production-ready.

### Context

TC-3908 is marked Done but two governance gaps remain:

1. **Missing deliverables**: `reports/agents/B/TC-3908/plan.md` and
   `reports/agents/B/TC-3908/changes.md` were in the taskcard's allowed_paths
   and stated deliverables, but were never created.

2. **AG-002 violations without formal cover**:
   - `_filters.py` was created during TC-3908 but was NOT in the original
     allowed_paths (it was a necessary addition discovered during implementation).
   - `src/launcher/deploy/promoter.py` was modified (added `_grade_ge` alias)
     but is also not in TC-3908's allowed_paths.

Both modifications were correct and necessary, but the governance trail is incomplete.
A healing taskcard that creates the missing documents closes the audit gap.

### Scope

**Fix**: Create missing report files and document the AG-002 deviations formally.

**Allowed paths**:
- `reports/agents/B/TC-3908/plan.md`
- `reports/agents/B/TC-3908/changes.md`

**Forbidden**: any code file. No source changes in this taskcard.

### Acceptance checks

**CLI — files exist**:
```bash
ls reports/agents/B/TC-3908/
# Must list: changes.md  commands.sh  evidence.md  plan.md  self_review.md
```

**CLI — content sanity**:
```bash
grep "allowed_paths" reports/agents/B/TC-3908/plan.md
# Must find the allowed_paths section

grep "_grade_ge" reports/agents/B/TC-3908/changes.md
# Must document the promoter.py fix

grep "_filters.py" reports/agents/B/TC-3908/changes.md
# Must document the unplanned _filters.py addition
```

**Config respected**: N/A
**No mock data**: N/A — documentation only.

### Deliverables

1. **`reports/agents/B/TC-3908/plan.md`** — agent implementation plan with:
   - Original scope and the discovered need for `_filters.py`
   - Dependency graph (leaf → orchestrator order used)
   - Decision log: why `_filters.py` was added (circular import avoidance)
   - Decision log: why `promoter.py` was modified (`_grade_ge` was a pre-existing bug
     exposed by pycache invalidation, fixed as a prerequisite to green tests)
   - Reference to healing plan: `plans/healing/TC-3908-H5_dep-direction.md` (classify_claim_visibility relocation)

2. **`reports/agents/B/TC-3908/changes.md`** — file-by-file change log:

   | File | Action | Lines | AG-002 status |
   |------|--------|-------|---------------|
   | `src/launcher/workers/understand/extract/__init__.py` | Created | ~95 | Covered by TC-3908 |
   | `src/launcher/workers/understand/extract/_api_surface.py` | Created | ~502 | Covered by TC-3908 |
   | `src/launcher/workers/understand/extract/_deterministic.py` | Created | ~325 | Covered by TC-3908 |
   | `src/launcher/workers/understand/extract/_entry.py` | Created | ~216 | Covered by TC-3908 |
   | `src/launcher/workers/understand/extract/_filters.py` | Created (unplanned) | ~140 | **AG-002 gap** — justified by circular import prevention; documented here |
   | `src/launcher/workers/understand/extract/_linking.py` | Created | ~49 | Covered by TC-3908 |
   | `src/launcher/workers/understand/extract/_llm.py` | Created | ~199 | Covered by TC-3908 |
   | `src/launcher/workers/understand/extract/_snippets.py` | Created | 825 | Covered by TC-3908 |
   | `src/launcher/workers/understand/extract/_validation.py` | Created | ~223 | Covered by TC-3908 |
   | `src/launcher/shared/extract_claims.py` | Replaced with 12-line compat shim | 12 | Covered by TC-3908 (file in allowed_paths) |
   | `src/launcher/deploy/promoter.py` | Added `_grade_ge = grade_ge` alias | +1 line | **AG-002 gap** — pre-existing bug revealed by pycache invalidation; fix was prerequisite to green tests |
   | `src/launcher/workers/understand/extract.py` | Deleted | -2023 | Covered by TC-3908 |
   | `src/launcher/workers/understand/extract/_impl.py` | Created then deleted | 0 net | Transitional; covered by TC-3908 |

   Include a section: "Healing taskcards raised for remaining gaps":
   - TC-3908-H1: Wire `_decompose_code_block_into_steps` into pipeline
   - TC-3908-H2: Fix `_extract_error_messages` return type
   - TC-3908-H3: Add unit tests for ported functions
   - TC-3908-H4: Split `_snippets.py` (825 → ≤600 lines)
   - TC-3908-H5: Relocate `classify_claim_visibility` to `shared/classify_claims.py`
   - TC-3908-H6: This taskcard (governance trail completion)

### Hard rules

- No code changes in this taskcard — documentation only
- `changes.md` must be accurate — verify line counts against actual files before writing
- The AG-002 deviations must be documented honestly, not glossed over
- Both files must be in Markdown, render correctly in GitHub

### Review dimensions (what 5/5 means for this taskcard)

| Dimension | 5/5 means |
|-----------|-----------|
| Thoroughness | All 13 changed files documented; all 2 AG-002 deviations acknowledged |
| Correctness | Line counts match `wc -l` output on actual files |
| Governance | AG-002 deviations documented with rationale; healing taskcards referenced |
| Minimality | Only 2 files created; no code touched |
| Consistency | Matches evidence.md and self_review.md already written |

### Runbook

```bash
# 1. Count lines for each file:
for f in src/launcher/workers/understand/extract/*.py src/launcher/shared/extract_claims.py; do
    echo "$f: $(wc -l < $f)"
done

# 2. Write reports/agents/B/TC-3908/plan.md
#    - Include dependency graph, decision log for _filters.py and promoter.py

# 3. Write reports/agents/B/TC-3908/changes.md
#    - Use verified line counts from step 1
#    - Include the healing taskcards table

# 4. Verify all 5 files exist in reports/agents/B/TC-3908/:
ls reports/agents/B/TC-3908/
# Expected: changes.md  commands.sh  evidence.md  plan.md  self_review.md
```
