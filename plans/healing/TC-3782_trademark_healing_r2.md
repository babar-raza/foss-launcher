# TC-3782 Trademark Healing Round 2

## Context

Self-review of the TH-01..TH-05 healing sprint (which itself healed TC-3782)
identified residual gaps. Empirical verification confirmed that double-encoded
HTML entities (`&amp;reg;`) bypass `_strip_html_entities()` and produce the
exact same `excelreg` artifact that TC-3782 was designed to fix.

The validation gate (`_ENTITY_ARTIFACT_RE`) catches these at evaluation time,
but the root-cause fix in `_strip_html_entities()` does not prevent them.
This violates Rule 6 (root-cause re-generation, not post-hoc patching).

**Parent**: TC-3782 (Done) > TH-01..TH-05 (Done)
**Source**: Self-review of TH-01..TH-05 execution, dated 2026-03-07
**Evidence**: `.venv/Scripts/python.exe -c "from launcher.shared.slug_engine import derive_semantic_slug; print(derive_semantic_slug('Excel&amp;reg; files'))"` → `excelampreg-files` (BUG)

---

## Gap Table

| Gap ID | Description | Severity | Confirmed | Taskcard |
|--------|-------------|----------|-----------|----------|
| R2-G01 | Double-encoded HTML entities (`&amp;reg;`) bypass single `html.unescape()` pass — `excelreg` still leaks into slug | High | YES: `derive_semantic_slug('Excel&amp;reg; files')` → `excelampreg-files` | R2-01 |
| R2-G02 | Trademark symbol regex `[®™©]` inline in `_strip_html_entities()` not compiled at module level — inconsistent with TH-03 principle | Low | YES: code inspection confirms inline `re.sub` | R2-02 |
| R2-G03 | Missing test coverage: double-encoded entities, case-insensitive malformed entities, mixed entity strings | Medium | YES: no tests for these confirmed-working paths | R2-03 |
| R2-G04 | Pilot E2E verification not executed — protocol Step 7 requires it | Medium | YES: no pilot run in TH-01..TH-05 sprint | R2-04 |

---

## Taskcards

---

### R2-01 — Fix Double-Encoded HTML Entity Bypass

**Status**: Done
**Gap linkage**: R2-G01
**Role**: Senior engineer. Drop-in, production-ready.

#### Scope

**Fix**: Replace single `html.unescape()` call in `_strip_html_entities()` with a convergence loop that decodes until stable. This handles `&amp;reg;` → `&reg;` → `®` → stripped in successive passes.

```python
# In _strip_html_entities(), replace:
#   text = html.unescape(text)
# With:
prev = None
while prev != text:
    prev = text
    text = html.unescape(text)
```

Safety: The loop terminates because `html.unescape` is idempotent on fully-decoded text. Maximum iterations in practice: 2-3 (double/triple encoding). Add a safety cap of 5 iterations to prevent pathological input.

**Allowed paths**:
- `src/launcher/shared/slug_engine.py`
- `tests/unit/shared/test_slug_engine.py`

**Forbidden**: any other file/path.

#### Acceptance checks

- **CLI**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/shared/test_slug_engine.py -v` — all pass
- **Tests**:
  - New: `test_semantic_slug_strips_double_encoded_entity` — `"Excel&amp;reg; files"` → no `reg` or `amp` artifacts
  - New: `test_semantic_slug_strips_triple_encoded_entity` — `"Excel&amp;amp;reg; files"` → clean
  - New: `test_strip_html_entities_convergence_cap` — verify loop terminates on pathological input (e.g., 10 levels of encoding)
  - Existing: all 68 slug engine tests still pass
- **Config respected end-to-end**: No config changes
- **No mock data in production paths**: Pure string transformation
- **Full suite**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest --tb=short -q` — 0 failures

#### Deliverables

- Modified `src/launcher/shared/slug_engine.py` — convergence loop in `_strip_html_entities()`
- Updated `tests/unit/shared/test_slug_engine.py` — 3 new tests

#### Hard rules

- Keep `_strip_html_entities` signature unchanged
- Loop MUST have a safety cap (max 5 iterations) with a `logger.warning` if cap is hit
- Deterministic: `html.unescape` is pure and deterministic
- No new dependencies
- Update `_strip_html_entities` docstring to mention multi-pass decoding

#### Review dimensions — what 5/5 means

| Dimension | 5/5 definition |
|-----------|----------------|
| Correctness | `derive_semantic_slug("Excel&amp;reg; files")` produces slug without `reg` or `amp` artifacts |
| Robustness | Triple-encoded entities handled; pathological input terminates safely |
| Testability | Double, triple, and cap-hit paths all tested |
| Safety | Loop bounded by cap; warning logged on cap hit |
| Performance | Max 5 iterations × O(n) string scan = negligible for slug-length strings |
| Observability | Warning logged when convergence cap hit |
| Minimality | ~5 lines changed in `_strip_html_entities`, 3 tests |
| Integration fit | No signature changes, no downstream impact |
| Maintainability | Convergence loop is a well-known pattern; docstring explains it |
| Compatibility | Existing callers unaffected |
| Test Quality | Happy path (double), edge (triple), failure (cap) all covered |
| Docs/Specs | Docstring updated |
| Consistency | Follows same `_strip_html_entities` pattern |

#### Now (runbook)

```bash
# 1. Edit _strip_html_entities in slug_engine.py — add convergence loop
# 2. Update docstring
# 3. Add 3 tests to test_slug_engine.py
# 4. Run targeted tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/shared/test_slug_engine.py -v
# 5. Run full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest --tb=short -q
```

---

### R2-02 — Compile Trademark Symbol Regex at Module Level

**Status**: Done
**Gap linkage**: R2-G02
**Role**: Senior engineer. Drop-in, production-ready.

#### Scope

**Fix**: Extract inline `re.sub(r"[®™©]", "", text)` in `_strip_html_entities()` to a module-level compiled pattern `_TRADEMARK_SYMBOL_RE`. This is consistent with TH-03 which compiled `_ENTITY_ARTIFACT_RE` for the same reason.

```python
# Module level:
_TRADEMARK_SYMBOL_RE = re.compile(r"[®™©]")

# In _strip_html_entities():
text = _TRADEMARK_SYMBOL_RE.sub("", text)
```

**Allowed paths**:
- `src/launcher/shared/slug_engine.py`

**Forbidden**: any other file/path.

#### Acceptance checks

- **CLI**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/shared/test_slug_engine.py -v` — all pass
- **Tests**: No new tests needed (pure refactor, behavior identical)
- **Config respected end-to-end**: No config changes
- **No mock data in production paths**: N/A
- **Full suite**: 0 failures

#### Deliverables

- Modified `src/launcher/shared/slug_engine.py` — 1 module-level constant + 1 line change

#### Hard rules

- Pattern name follows convention (`_UPPERCASE_RE`)
- Behavior identical — verified by existing tests passing
- No new dependencies

#### Review dimensions — what 5/5 means

| Dimension | 5/5 definition |
|-----------|----------------|
| Correctness | Identical behavior verified by existing 68 tests |
| Consistency | All regexes in slug_engine.py now compiled at module level |
| Minimality | 2 lines changed |
| Performance | Compiled once instead of per-call (marginal) |
| Maintainability | Single definition, easy to extend (e.g., add `℠`) |
| Integration fit | Follows codebase convention |
| All others | N/A or 5/5 by default (pure refactor) |

#### Now (runbook)

```bash
# 1. Add _TRADEMARK_SYMBOL_RE at module level in slug_engine.py
# 2. Replace re.sub call in _strip_html_entities
# 3. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/shared/test_slug_engine.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest --tb=short -q
```

---

### R2-03 — Add Missing Edge-Case Test Coverage

**Status**: Done
**Gap linkage**: R2-G03
**Role**: Senior engineer. Drop-in, production-ready.

#### Scope

**Fix**: Add parameterized tests for confirmed-working but untested paths:
1. Case-insensitive malformed entity (`&REG`, `&Reg`)
2. Mixed entities in one string (`"Excel&reg; and Windows&trade; files"`)
3. Service mark `℠` handled by slugification (confirm no artifact)

These paths all work correctly today (verified empirically) but have no regression tests.

**Allowed paths**:
- `tests/unit/shared/test_slug_engine.py`

**Forbidden**: any other file/path.

#### Acceptance checks

- **CLI**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/shared/test_slug_engine.py -v` — all pass
- **Tests**:
  - New: `test_malformed_entity_uppercase` — `"Excel&REG files"` → clean slug
  - New: `test_malformed_entity_mixed_case` — `"Excel&Reg files"` → clean slug
  - New: `test_mixed_entities_same_string` — `"Excel&reg; and Windows&trade; files"` → no `reg` or `trade`
  - New: `test_service_mark_stripped_by_slugification` — `"Excel℠ service"` → no `℠` artifact
  - Existing: all 68+ tests still pass
- **Config respected end-to-end**: No config changes
- **No mock data in production paths**: Tests only
- **No network in offline tests**: Pure string tests
- **Full suite**: 0 failures

#### Deliverables

- Updated `tests/unit/shared/test_slug_engine.py` — 4 new tests

#### Hard rules

- Tests must be deterministic (no randomness)
- No code changes — tests only
- Each test must assert on the specific artifact that should NOT be present

#### Review dimensions — what 5/5 means

| Dimension | 5/5 definition |
|-----------|----------------|
| Test Quality | Every confirmed-working-but-untested path has a regression test |
| Coverage | Case sensitivity, mixed input, non-ASCII symbols all covered |
| Correctness | Tests verify actual behavior matches expectations |
| Minimality | 4 focused tests, no code changes |
| Maintainability | Tests are self-documenting with descriptive names |
| All others | N/A (tests only) |

#### Now (runbook)

```bash
# 1. Add 4 new tests to test_slug_engine.py
# 2. Run targeted tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/shared/test_slug_engine.py -v
# 3. Run full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest --tb=short -q
```

---

### R2-04 — Pilot E2E Verification

**Status**: Done
**Gap linkage**: R2-G04
**Role**: Senior engineer. Drop-in, production-ready.

#### Scope

**Fix**: Run the pilot script with a real config to verify zero trademark artifacts in generated slugs end-to-end. This was required by the orchestrator protocol Step 7 but skipped in the TH-01..TH-05 sprint.

The pilot should be run with `--resume-from planner` to exercise only the slug-relevant workers (Planner → Generate → Evaluate) using an existing intake+understand checkpoint.

After the pilot, grep all generated slug values for entity artifacts and capture evidence.

**Allowed paths**:
- `reports/agents/B/R2-04/evidence.md`

**Forbidden**: any other file/path.

#### Acceptance checks

- **CLI**:
  ```bash
  .venv/Scripts/python.exe scripts/run_pilot.py configs/pilots/aspose-cells-foss-python.yaml --resume-from planner
  ```
- **Tests**: N/A (pilot verification, not unit tests)
- **Evidence**:
  - `reports/agents/B/R2-04/evidence.md` with:
    - Pilot run command + exit status
    - All slugs from `planner_checkpoint.json` listed
    - Grep for `reg|trade|copy|amp` artifacts in slug values
    - Count: 0 artifacts = PASS
- **Config respected end-to-end**: Uses existing pilot config
- **No mock data in production paths**: Real pilot run with real config

#### Deliverables

- `reports/agents/B/R2-04/evidence.md` with pilot results

#### Hard rules

- Must use existing checkpoint (do not re-run intake/understand if checkpoint exists)
- If no checkpoint exists, run from scratch and document
- Evidence must include every slug produced, not just a summary
- Any artifact found is a FAIL — route back for root-cause fix

#### Review dimensions — what 5/5 means

| Dimension | 5/5 definition |
|-----------|----------------|
| Evidence | Every slug listed with pass/fail status |
| Correctness | Zero entity artifacts in any slug |
| Integration fit | Uses existing pilot infrastructure |
| Thoroughness | All pages checked, not a sample |
| All others | N/A (verification task) |

#### Now (runbook)

```bash
# 1. Check if planner checkpoint exists
ls runs/pilot_cells_*/planner_checkpoint.json 2>/dev/null || echo "No checkpoint — run from scratch"
# 2. Run pilot
.venv/Scripts/python.exe scripts/run_pilot.py configs/pilots/aspose-cells-foss-python.yaml --resume-from planner
# 3. Extract all slugs from planner checkpoint
.venv/Scripts/python.exe -c "
import json, pathlib, re
for f in sorted(pathlib.Path('runs').glob('pilot_cells_*/planner_checkpoint.json')):
    data = json.loads(f.read_text())
    for page in data.get('pages', []):
        slug = page.get('slug', '')
        artifacts = re.findall(r'(?:reg|trade|copy|amp)(?=-|$)', slug)
        status = 'FAIL' if artifacts else 'PASS'
        print(f'  [{status}] {slug}  {artifacts or \"\"}')
    break
"
# 4. Write evidence
```
