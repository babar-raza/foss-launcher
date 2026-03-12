# Healing Plan — breezy-cooking-storm Quality Root-Cause Fix (Phase U/G/P/E)

## Context

After completing 9 taskcards (TC-4224 through TC-4232) across Phase U
(Understand stability), Phase G (Generate structural fixes), Phase P (Planner
relevance), and Phase E (Evaluate calibration), the self-review Phase 1 scored
3.8/5 average with **REVISION REQUIRED** verdict. This healing plan captures
the 3 gaps and assigns remediation taskcards.

---

## Gap Table

| Gap ID | Description | Severity | Taskcard | Status |
|--------|-------------|----------|----------|--------|
| HQ-01 | No pilot run evidence — success criteria from breezy-cooking-storm unverified | **Blocker** | HQ-01 | **Blocked — live LLM required** |
| HQ-02 | G-3 code-block retry fires only when `sec_snippets` non-empty — reference page Properties/Methods sections may have no snippet overlap | High | TC-4249 | **Done** |
| HQ-03 | TC-4241/4244 changes appeared via parallel agent work — scope not explicitly acknowledged in plan | Low | HQ-03 (note only) | **Done** |
| HQ-04 | TC-4249 tests are source guards only — no behavioral test exercises the retry path at runtime | Medium | HQ-04 | **Done** |

---

## Taskcard HQ-01 — Run verification pilot and capture evidence

**Status:** Not Started
**Gap linkage:** HQ-01 (Thoroughness / Production readiness)
**Role:** Senior engineer — run pilot, parse logs, write evidence.

### Problem

The 10 success criteria in `breezy-cooking-storm.md` were never verified
against an actual pilot run. The plan's gate requires:

1. `fallback_rate = 0.0` in understand checkpoint
2. No claims with `confidence < 0.5` in understand checkpoint
3. Zero `canonical_import` violations in generated `.md` files
4. Zero `L1_VALIDATOR_FAIL_FINAL` events per cycle
5. Zero `Section gate FAIL` for reference/api_reference pages
6. Zero `finish_reason: length` events per cycle
7. `A+B rate ≥ 30%` in all 3 runs
8. `D+F rate ≤ 30%` consistently
9. Grade distribution consistent across runs (≤ 2 pages changing grade)
10. `hallucination_rate` CRITICAL findings = 0 in all runs

Without an actual run, all code changes may be correct in isolation but
still fail in the integrated pipeline.

### Scope

**In scope:**
- Run the pilot once and capture log evidence for each success criterion
- Verify understand checkpoint JSON: no `confidence < 0.5`, `claim_source != llm_fallback`
- Grep generated `.md` files for wrong canonical import patterns
- Grep run events for L1_VALIDATOR_FAIL_FINAL, Section gate FAIL, finish_reason: length
- Check evaluate findings JSON for hallucination_rate CRITICAL
- Capture A+B/D+F/grade distribution from evaluate output
- Write evidence to `reports/BREEZY/evidence.md`

**Out of scope:**
- Fixing new failures found (those become separate healing taskcards)
- Running 3 consecutive runs (out of scope for this card — 1 run is sufficient
  for initial gate check; 3-run consistency check is a follow-up)

### Allowed paths

- `plans/healing/BREEZY-00-quality-fix-healing-plan.md`
- `reports/BREEZY/evidence.md` (new, created by this task)

### Runbook

```bash
# Step 1: Run pilot
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m launcher.cli.main run configs/pilots/aspose-cells-foss-python.yaml

# Step 2: Find the run directory (most recent under runs/)
# Note the run_id from output, e.g., 260312_XXXXXX_cells_python_YYYY

# Step 3: Check understand checkpoint for low-confidence claims
# Look for claims with confidence < 0.5 — expected: 0 found
python -c "
import json, pathlib, sys
ckpt = list(pathlib.Path('runs').rglob('understand_checkpoint.json'))
if not ckpt: sys.exit('no checkpoint found')
data = json.loads(ckpt[-1].read_text())
claims = data.get('claims', [])
low = [c for c in claims if c.get('confidence', 1.0) < 0.5]
print(f'Total claims: {len(claims)}, Low confidence: {len(low)}')
for c in low[:5]: print(' ', c.get('claim_id'), c.get('confidence'), c.get('claim_source'))
"

# Step 4: Check for wrong canonical imports in generated .md files
python -c "
import pathlib, re
md_files = list(pathlib.Path('runs').rglob('*.md'))
wrong = []
for f in md_files:
    text = f.read_text(errors='replace')
    if re.search(r'import aspose\.cells', text):
        wrong.append(str(f))
print(f'Wrong import in {len(wrong)} files:')
for w in wrong[:10]: print(' ', w)
"

# Step 5: Check events for L1_VALIDATOR_FAIL_FINAL
python -c "
import pathlib
evts = list(pathlib.Path('runs').rglob('events.ndjson'))
if not evts: print('no events file'); exit()
lines = evts[-1].read_text().splitlines()
finals = [l for l in lines if 'L1_VALIDATOR_FAIL_FINAL' in l]
print(f'L1_VALIDATOR_FAIL_FINAL count: {len(finals)}')
"

# Step 6: Check for Section gate FAIL on reference pages
python -c "
import pathlib
logs = list(pathlib.Path('runs').rglob('events.ndjson'))
if not logs: exit()
lines = logs[-1].read_text().splitlines()
sec_gate = [l for l in lines if 'Section gate FAIL' in l]
print(f'Section gate FAIL count: {len(sec_gate)}')
for l in sec_gate[:10]: print(' ', l[:200])
"

# Step 7: Check finish_reason: length
python -c "
import pathlib
logs = list(pathlib.Path('runs').rglob('events.ndjson'))
if not logs: exit()
lines = logs[-1].read_text().splitlines()
trunc = [l for l in lines if 'finish_reason' in l and 'length' in l]
print(f'finish_reason:length count: {len(trunc)}')
"

# Step 8: Check evaluate findings for hallucination_rate CRITICAL
python -c "
import json, pathlib
rpts = list(pathlib.Path('runs').rglob('evaluation_report.json'))
if not rpts: print('no evaluation report'); exit()
data = json.loads(rpts[-1].read_text())
pages = data.get('pages', [])
crit = [p for p in pages if any(
    f.get('check') == 'hallucination_rate' and f.get('severity') == 'critical'
    for f in p.get('findings', [])
)]
print(f'hallucination_rate CRITICAL pages: {len(crit)}')
grades = {}
for p in pages:
    g = p.get('grade', '?')
    grades[g] = grades.get(g, 0) + 1
print(f'Grade distribution: {grades}')
ab = grades.get('A',0) + grades.get('B',0)
df = grades.get('D',0) + grades.get('F',0)
total = sum(grades.values())
if total:
    print(f'A+B rate: {ab/total:.0%}, D+F rate: {df/total:.0%}')
"
```

### Evidence format

Write `reports/BREEZY/evidence.md` with:

```markdown
# Breezy-Cooking-Storm — Pilot Run Evidence
Run ID: [actual run ID]
Date: 2026-03-12

| Criterion | Expected | Actual | Pass? |
|-----------|----------|--------|-------|
| fallback_rate | 0.0 | X | Y/N |
| claims confidence < 0.5 | 0 | X | Y/N |
| canonical_import violations | 0 | X | Y/N |
| L1_VALIDATOR_FAIL_FINAL | 0 | X | Y/N |
| Section gate FAIL (reference) | 0 | X | Y/N |
| finish_reason: length | 0 | X | Y/N |
| A+B rate | ≥30% | X% | Y/N |
| D+F rate | ≤30% | X% | Y/N |
| hallucination_rate CRITICAL | 0 | X | Y/N |

## Failures Requiring Follow-up
[List any criteria that failed, with raw log evidence]
```

### Acceptance checks

- [ ] Pilot run completes without Python crash
- [ ] `reports/BREEZY/evidence.md` exists with all 9 criteria filled
- [ ] Each failing criterion becomes a new healing taskcard in `plans/healing/`
- [ ] Any criteria that pass are documented as confirmed

### Hard rules

- Do NOT fix failures found during this run inline — create a new healing taskcard per failure
- Evidence must come from actual run artifacts, not constructed data
- If the run crashes before evaluate, capture the crash log as evidence and mark all downstream criteria as "N/A — run crashed"

---

## Taskcard HQ-02 — Verify G-3 code-block retry fires for reference page sections

**Status:** Not Started
**Gap linkage:** HQ-02 (G-3 correctness for sections without `sec_snippets`)
**Role:** Senior engineer — code review + targeted test.

### Problem

The G-3 fix (TC-4229) adds a code-block retry for reference page sections only
when `sec_snippets` (section-level snippets) is non-empty. The retry logic is:

```python
if page_role in _CODE_REQUIRED_ROLES and sec_snippets and not _has_code_block(sections):
    _needs_code_retry = True
```

For `reference_object_page` sections (Properties, Methods), `sec_snippets` is
populated only if snippet claim IDs overlap with that section's claim IDs. If
a Properties section has no snippet-producing claims, `sec_snippets` will be
empty and the retry will NOT fire — even though a code block is required.

**Risk**: Section gate FAIL for Properties/Methods sections persists after
TC-4229 because the retry guard is too narrow.

### Scope

**In scope:**
- Read the actual `sec_snippets` population logic in `worker.py` to confirm
  whether Properties/Methods sections ever get `sec_snippets`
- If `sec_snippets` is always empty for these sections: change the retry guard
  to fire when `page_role in _CODE_REQUIRED_ROLES` regardless of `sec_snippets`
  (the instruction to generate code is still valid even without example snippets)
- Write a targeted unit test: reference page section with no snippets must still
  trigger retry when code block is absent
- Update TC-4229 taskcard self-review if a code change is needed

**Out of scope:**
- Changing how snippets are produced or assigned (Understand worker scope)
- Changes to any other retry logic

### Allowed paths

- `src/launcher/workers/generate/worker.py`
- `plans/taskcards/TC-4229_generate-code-block-enforcement.md`
- `tests/unit/workers/generate/` (new test file)
- `plans/healing/BREEZY-00-quality-fix-healing-plan.md`

### Investigation step

Read `worker.py` around the `sec_snippets` population — search for where
`sec_snippets` is built (likely from a dict keyed by section claim IDs or
section index). Determine whether Properties sections of `reference_object_page`
pages will ever have non-empty `sec_snippets`.

Then check Section gate FAIL log messages from any available pilot run to see
which sections are still failing.

### Decision tree

**Case A**: `sec_snippets` IS sometimes populated for reference sections → G-3
is correct as written; add a test that exercises the populated case. No code
change needed.

**Case B**: `sec_snippets` is NEVER populated for reference sections because
snippets attach to API-level claims, not property-level claims → change the
guard from `sec_snippets and not _has_code_block(...)` to `not _has_code_block(...)`
for reference roles. This widens the retry to always fire when code is required.

### Acceptance checks

- [ ] Investigation completed and decision documented in this card
- [ ] If Case B: code change in `worker.py` made and TC-4229 taskcard updated
- [ ] Unit test added: reference section with no snippets + no code block → retry fires
- [ ] Unit test: non-reference role with no code block → retry does NOT fire
- [ ] Tests pass: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/generate/ -v`

### Hard rules

- Do not change retry behavior for non-reference roles
- If widening the guard: add a log line so retry reason is observable

---

## Taskcard HQ-03 — Acknowledge TC-4241/4244 as authorized parallel changes

**Status:** Done (note-only — no code change)
**Gap linkage:** HQ-03 (Scope & constraints adherence — unplanned changes appeared)
**Role:** Analysis only.

### Problem

During parallel execution of this plan, two additional taskcards (TC-4241 and
TC-4244) modified files in the allowed paths of our Phase U work:

- **TC-4241**: Raised `_MAX_DOCSTRING_CLAIMS = 200 → 2000`,
  `_MAX_TYPED_METHODS_CLAIMS = 10 → 50`, `_MAX_TYPED_PROPS_CLAIMS = 10 → 50`
  in `_entry.py`. These changes increase the surface area of deterministic
  extraction, which is orthogonal to our confidence filter (TC-4225).
- **TC-4244**: Added `ExtractionDatabase` builder helpers to `_entry.py` and
  changed `run_extract()` to return a 5-tuple instead of 4-tuple. This is
  the bounded-description extraction infrastructure (TC-4245 template prep).

### Resolution

Both changes are:
- From authorized concurrent taskcards (TC-4241, TC-4244 exist in `plans/taskcards/`)
- Compatible with our changes (TC-4225 confidence filter runs after extraction,
  regardless of how many claims are extracted)
- Already integrated (tests passing as of implementation)

**No code change needed.** The scope gap was in plan coordination, not
implementation.

### Documentation

The breezy-cooking-storm plan's "Critical Files" table should be read as
**intersecting** with TC-4241/4244 scope. Our Phase U work addresses
reliability; TC-4241/4244 address completeness. Both goals are compatible.

---

---

## Taskcard HQ-01 — BLOCKED: pilot run requires live LLM endpoint

**Status:** Blocked
**Gap linkage:** HQ-01 (Thoroughness / Production readiness)
**Blocked reason:** Live LLM endpoint `https://llm.professionalize.com/v1` required.
Cannot be executed autonomously without user authorization and network access.

**Root cause**: The pipeline makes real HTTP calls to the LLM endpoint via
`LLMProviderClient`. There is no offline/mock mode that exercises the full
Understand → Generate → Evaluate pipeline with realistic claim extraction.

**Resolution**: User must run the pilot manually. Full runbook is in the
`## Taskcard HQ-01 — Run verification pilot and capture evidence` section above.
Evidence captured in `reports/BREEZY/evidence.md` will close this gap.

**Unblocking condition**: User executes:
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m launcher.cli.main run configs/pilots/aspose-cells-foss-python.yaml
```
Then runs the evidence capture script from the runbook above.

---

## Taskcard HQ-04 — Behavioral test for TC-4249 code-block retry

**Status:** Done
**Gap linkage:** HQ-04 (Testability — source guards only)
**Role:** Senior engineer. Drop-in, production-ready.

### Problem

All 6 TC-4249 tests are source guards (inspect the source text). They cannot
verify at runtime that `_needs_code_retry = True` is actually set and that a
retry LLM call is made when a reference section has no code block and no
snippet overlap. A runtime behavioral test provides stronger assurance.

### Scope

**Fix:** Add a behavioral test that:
1. Mocks `_call_llm` to return a response without a code block on attempt 1,
   then with a code block on attempt 2
2. Calls `_generate_section` (or verifies through `generate_page`) with
   `page_role = "reference_object_page"` and `sec_snippets = []`
3. Asserts that `_call_llm` was called twice (retry fired)
4. Asserts the final output has a code block

**Alternative** (if `_generate_section` cannot be invoked cleanly): Use the
`inspect` approach to verify that the condition is checked BEFORE `sec_snippets`
is tested — i.e., parse the AST of the function and confirm the `if` condition
structure. This is stronger than string matching.

**Allowed paths:**
- `tests/unit/workers/generate/test_code_block_retry.py` (extend existing)

**Forbidden:** any other path

### Implementation approach

Option A — AST guard (strong, no mock overhead):
```python
import ast, inspect
import launcher.workers.generate.worker as w

src = inspect.getsource(w._generate_section)  # if accessible
tree = ast.parse(src)
# Find all If nodes containing both _CODE_REQUIRED_ROLES and _needs_code_retry
# Verify sec_snippets NOT in the condition test
```

Option B — Mock `_call_llm` at module level:
```python
with patch("launcher.workers.generate.worker._call_llm") as mock_llm:
    mock_llm.side_effect = [
        json.dumps([{"type": "paragraph", "content": "word " * 50}]),  # no code, attempt 1
        json.dumps([
            {"type": "paragraph", "content": "word " * 50},
            {"type": "code", "content": "import aspose_cells_foss", "language": "python"},
        ]),  # with code, attempt 2
    ]
    # invoke _generate_section with reference_object_page + empty sec_snippets
    # assert mock_llm.call_count == 2
```

### Acceptance checks

- [ ] New test `test_code_retry_fires_at_runtime_without_snippets` passes
- [ ] Test is deterministic (PYTHONHASHSEED=0 compatible)
- [ ] Full generate suite still 247/247

### Hard rules

- No network calls
- PYTHONHASHSEED=0 compatible
- No new test dependencies

### Review dimensions

| Dimension | 5/5 means |
|-----------|-----------|
| Testability | Retry path verified at runtime, not just at source level |
| Correctness | Two LLM calls confirmed when code block absent on first attempt |
| Robustness | Test handles both Option A (AST) and falls back to mock if needed |
| Minimality | Extends existing test file, no new file |

### Runbook

```bash
# 1. Extend tests/unit/workers/generate/test_code_block_retry.py with behavioral test
# 2. Run targeted tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/generate/test_code_block_retry.py -v
# 3. Run full generate suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/generate/ -v -q
```

---

## Healing Plan Execution Order (updated)

```
HQ-03 (done)
HQ-02 → TC-4249 (done)
HQ-04 (behavioral test — in progress)
HQ-01 (blocked — live LLM; user must run manually)
```
