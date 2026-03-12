# GE — Golden Reference Enforcement: Completion

**Source**: Self-review of TC-3833 (G001), TC-3843 (G002), TC-3847 (G003), TC-3844 (G004),
TC-3834 (G005). Five implementation gaps remain across the Golden Reference Integration plan.

Gaps range from critical (Pass 2 LLM retry silently deferred, breaking the 3-pass enforcement
promise) to minor (OPT-2/OPT-4 wiring unverified, has_code acceptance assertion missing).

**Codebase**: `v2` branch
**Sequencing**: GE-01 before GE-02 (both touch `generate/worker.py`); GE-03 and GE-04 independent.

---

## Gap → Taskcard Map

| Gap ID  | Description                                                            | Taskcard | Priority |
|---------|------------------------------------------------------------------------|----------|----------|
| G-GE-01 | G3: Pass 2 LLM retry in `enforce_block_spec` deferred (comment in code) | GE-01  | Critical |
| G-GE-02 | G3: OPT-5 section-level parallelism not implemented                    | GE-02    | High     |
| G-GE-03 | G2: OPT-2 `max_tokens` computation not confirmed wired to LLM call     | GE-03    | Medium   |
| G-GE-04 | G2: OPT-4 `api_surface_block` pruning not confirmed wired              | GE-04    | Medium   |
| G-GE-05 | G1: Acceptance check `sections[0].has_code == True` not tested         | GE-05    | Low      |

---

## GE-01 — G3: Implement Pass 2 LLM Retry in enforce_block_spec

**Status**: Done
**Evidence**: 15/15 tests pass (`test_enforcement.py`); 2603 total suite green.
**Files changed**: `src/launcher/workers/generate/worker.py` (Pass 2 block + new params `original_prompt`, `richness_tier`; `section_prompt_str` tracked in page loop; enforce call updated), `tests/unit/workers/test_enforcement.py` (+5 Pass 2 tests)
**Gap linkage**: G-GE-01
**Role**: Senior engineer. Drop-in, production-ready.

### Scope

**Fix**: Remove the `# Pass 2: LLM retry — deferred in this TC` comment from
`generate/worker.py` and implement the full Pass 2 logic inside `enforce_block_spec()`.

Pass 2 spec (from plan `twinkly-beaming-wren.md` Phase 3):
- Only for Tier A/B (skip entirely for Tier C)
- Build retry prompt: prepend `"ENFORCEMENT OVERRIDE — PREVIOUS RESPONSE DID NOT MEET REQUIREMENTS:\n{violations}\n\nREQUIRED FOR THIS RETRY:\n{per_violation_hard_rules}\n\n"` to the original prompt (cap prepend at 300 chars; truncate golden excerpt to 400 chars if present)
- Call LLM once; parse and validate with `check_against_spec()`
- If compliant → return `(retry_blocks, "pass2")`; if not → fall through to Pass 3
- Pass 2 triggers a single `llm_call` via the existing `_call_llm()` mechanism; no new LLM client

Update `pass_used` return values: `"none"` | `"pass1"` | `"pass2"` | `"pass3"`.

**Allowed paths**:
- `src/launcher/workers/generate/worker.py`
- `tests/unit/workers/test_enforcement.py` (or nearest enforcement test file)

**Forbidden**: Any other file or path.

### Acceptance checks

- **CLI**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_enforcement.py -v` — all PASS
- **UI/Web/API**: N/A
- **Tests**:
  - `test_pass2_called_when_pass1_fails_tier_a` — when Pass 1 does not satisfy spec and richness_tier="A", LLM called once with ENFORCEMENT OVERRIDE prefix
  - `test_pass2_skipped_for_tier_c` — richness_tier="C" → Pass 2 never called, goes directly to Pass 3
  - `test_pass2_satisfies_spec_returns_pass2` — when retry LLM response passes `check_against_spec`, return `(blocks, "pass2")`
  - `test_pass2_fails_falls_through_to_pass3` — when retry LLM response still fails, Pass 3 called
  - `test_pass2_prepend_capped_at_300_chars` — enforcement override prepend is ≤300 chars
- **Config respected end-to-end**: `richness_tier` drives Pass 2 skip; no config file change needed
- **No mock data in production paths**: LLM call uses real `_call_llm()` mock in tests; no hardcoded response in production

### Deliverables

- `src/launcher/workers/generate/worker.py` — Pass 2 implementation replacing the deferred comment; all 3 passes functional
- `tests/unit/workers/test_enforcement.py` — full file replacement with 5 new Pass 2 test functions added (all existing Pass 1/Pass 3 tests preserved)
- No stubs, no TODOs; `pass_used` values updated to include `"pass2"`

### Hard rules

- Pass 2 is max 1 LLM call — no retry loop inside Pass 2
- Prepend hard-capped at 300 chars; golden excerpt hard-capped at 400 chars in retry prompt
- `check_against_spec()` call reused unchanged — no duplication
- `_call_llm()` used for Pass 2 (same as Pass 1 LLM call); no new LLM client
- Tier C must NEVER invoke Pass 2 — test this boundary explicitly
- No new dependencies

### Review dimensions

| Dimension | 5/5 means |
|-----------|-----------|
| D3 Sandwich Model | Pass 2: engineering build prompt → LLM call → engineering validate response; fallback to Pass 3 if invalid |
| D5 Error Isolation | LLM failure in Pass 2 → fall through to Pass 3, not raise |
| D7 Test Coverage | 5 functions: Pass 2 triggered + Tier C skip + pass2 success + pass2 fail + prepend cap |
| D10 Performance | Max 1 LLM call for Pass 2; GoldenIndex loaded once at worker startup (not per retry) |
| D13 Integration | `check_against_spec()` is the shared validator; same spec object used across all passes |

### Now (runbook)

```bash
# 1. Find the deferred comment and surrounding context
grep -n "Pass 2\|deferred\|llm_retry\|richness_tier" src/launcher/workers/generate/worker.py | head -20

# 2. Read enforce_block_spec function to understand current structure
# Read src/launcher/workers/generate/worker.py (lines around enforce_block_spec)

# 3. Find _call_llm signature
grep -n "def _call_llm\|async def _call_llm" src/launcher/workers/generate/worker.py

# 4. Read existing enforcement test file
# Glob tests/**/*enforcement*
# Read tests/unit/workers/test_enforcement.py (or equivalent)

# 5. Implement Pass 2 block; update pass_used enum string

# 6. Run enforcement tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_enforcement.py -v

# 7. Full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q
```

---

## GE-02 — G3: OPT-5 Section-Level Parallelism Within a Page

**Status**: Done
**Evidence**: 4/4 tests pass (TestSectionGather); 2645 total suite green. Files: worker.py (_SECTION_CONCURRENCY=4, for loop → asyncio.gather with semaphore + exception handling), tests/unit/workers/test_enforcement.py (+TestSectionGather class).
**Gap linkage**: G-GE-02
**Depends on**: GE-01 complete (`enforce_block_spec` stable)
**Role**: Senior engineer. Drop-in, production-ready.

### Scope

**Fix**: In `generate/worker.py` per-page section loop, wrap per-section LLM calls in
`asyncio.gather()` limited by `_SECTION_CONCURRENCY = 4` semaphore. This is the section-level
parallelism within a single page (OPT-5), distinct from the page-level parallelism in HO-05.

Implementation:
1. Extract per-section generation body into `async def _generate_section(skel_section, ...)`.
2. Wrap with `asyncio.Semaphore(_SECTION_CONCURRENCY)`.
3. `asyncio.gather(*[_generate_section(s, ...) for s in page_skeleton.sections])`.
4. Collect results in section order; apply `enforce_block_spec` per section after gather.
5. Cross-section deduplication in `section_validator.py` applied post-collect (over all sections).

**Allowed paths**:
- `src/launcher/workers/generate/worker.py`
- `tests/unit/workers/test_enforcement.py`

**Forbidden**: Any other file or path.

### Acceptance checks

- **CLI**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_enforcement.py -v` — all PASS
- **UI/Web/API**: N/A
- **Tests**:
  - `test_sections_gathered_in_order` — output section order matches skeleton section order
  - `test_section_semaphore_limits_concurrency` — mock verifies ≤4 concurrent section calls
  - `test_cross_section_dedup_applied_post_gather` — deduplication runs after all sections gathered
  - `test_one_section_failure_does_not_abort_page` — one section error → fallback for that section; others succeed
- **Config respected end-to-end**: `_SECTION_CONCURRENCY = 4` module constant; existing tests unaffected
- **No mock data in production paths**: asyncio.Semaphore is stdlib; no production path hardcoding

### Deliverables

- `src/launcher/workers/generate/worker.py` — per-page section loop replaced with `asyncio.gather()` pattern
- Tests covering: order preservation + concurrency limit + dedup post-gather + per-section error isolation
- No stubs, no TODOs

### Hard rules

- Section order MUST match skeleton order; gather results as list, preserve original index
- `asyncio.gather(return_exceptions=True)` then handle exceptions per element
- `enforce_block_spec` runs per-section inside each coroutine (not batched)
- Cross-section dedup (`section_validator.py`) runs once after all coroutines complete
- `_SECTION_CONCURRENCY = 4` named constant at module level
- No new dependencies

### Review dimensions

| Dimension | 5/5 means |
|-----------|-----------|
| D4 Determinism | Output section order locked to skeleton order; PYTHONHASHSEED=0 stable |
| D5 Error Isolation | Failed section → deterministic fallback (`render_section_deterministic`); other sections unaffected |
| D7 Test Coverage | 4 functions: order + concurrency + dedup post-gather + section failure isolated |
| D10 Performance | ~3-4x wall-clock reduction for multi-section pages |
| D13 Integration | `enforce_block_spec` still called per-section inside each coroutine; GoldenIndex still loaded once |

### Now (runbook)

```bash
# 1. Find per-section loop in generate/worker.py
grep -n "for.*skel_section\|for.*section\|_generate_section\|asyncio" src/launcher/workers/generate/worker.py | head -30

# 2. Find cross-section dedup call
grep -n "dedup\|deduplication\|section_validator" src/launcher/workers/generate/worker.py | head -10

# 3. Implement _generate_section coroutine + gather pattern; move dedup post-gather

# 4. Run enforcement tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_enforcement.py -v

# 5. Full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q
```

---

## GE-03 — G2: OPT-2 max_tokens Wiring Verification and Fix

**Status**: Done
**Evidence**: 3/3 tests pass (TestMaxTokensWiring); 2641 total suite green. Files: worker.py (section_max_tokens computed at call site, threaded to _call_llm), section_prompt.py (no change needed for computation), tests/unit/workers/generate/test_section_prompt.py (+TestMaxTokensWiring class).
**Gap linkage**: G-GE-03
**Role**: Senior engineer. Drop-in, production-ready.

### Scope

**Fix**: Verify that `max_tokens = max(512, (section.max_words or 200) * 3)` is computed
in `build_section_prompt()` and passed through to `_call_llm()` → `chat_completion(max_tokens=...)`.
If any link in this chain is broken (computed but not returned, returned but not threaded through,
threaded but not passed to the provider), fix it.

Read the current state first:
1. Does `build_section_prompt()` compute `max_tokens`?
2. Is `max_tokens` returned or accessible to the caller?
3. Does `worker.py` pass `max_tokens` to `_call_llm()`?
4. Does `_call_llm()` pass it to `chat_completion()`?

Fix whichever links are broken. If all are working, add a test that confirms the value
reaches the LLM call (currently untested).

**Allowed paths**:
- `src/launcher/workers/generate/section_prompt.py`
- `src/launcher/workers/generate/worker.py`
- `tests/workers/generate/test_section_prompt.py` (or nearest test file)

**Forbidden**: Any other file or path.

### Acceptance checks

- **CLI**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/workers/generate/ -v` — all PASS
- **UI/Web/API**: N/A
- **Tests**:
  - `test_max_tokens_computed_from_max_words` — `section.max_words=100` → `max_tokens=300`; `max_words=None` → `max_tokens=600` (200*3)
  - `test_max_tokens_minimum_is_512` — `max_words=10` → `max_tokens=512` (not 30)
  - `test_max_tokens_passed_to_llm_call` — verify mock LLM call received `max_tokens=<correct_value>`
- **Config respected end-to-end**: `max_words` from section skeleton drives `max_tokens`
- **No mock data in production paths**: `max_tokens` computed from real section data; LLM mock used only in tests

### Deliverables

- Whichever files in `allowed_paths` require fixing — full section replacement for changed functions only
- 3 test functions confirming computation + minimum + LLM pass-through
- No stubs, no TODOs

### Hard rules

- Formula is exactly `max(512, (section.max_words or 200) * 3)` — no deviation
- Public signature of `build_section_prompt()` must not break callers if `max_tokens` is added to return value; use keyword or update all call sites
- No new dependencies

### Review dimensions

| Dimension | 5/5 means |
|-----------|-----------|
| D1 Specification Alignment | Formula matches plan spec exactly: `max(512, max_words * 3)` with `or 200` default |
| D2 Contract Compliance | `max_tokens` reaches `chat_completion()`; no silent discard in chain |
| D7 Test Coverage | 3 functions: computation + minimum + LLM pass-through |
| D13 Integration | End-to-end: `section.max_words` → `build_section_prompt()` → `_call_llm()` → `chat_completion(max_tokens=N)` |

### Now (runbook)

```bash
# 1. Check if max_tokens computed in section_prompt.py
grep -n "max_tokens\|max_words" src/launcher/workers/generate/section_prompt.py | head -20

# 2. Check _call_llm signature and whether max_tokens is a param
grep -n "def _call_llm\|max_tokens" src/launcher/workers/generate/worker.py | head -20

# 3. Check chat_completion call in llm_provider.py
grep -n "max_tokens\|chat_completion" src/launcher/clients/llm_provider.py | head -20

# 4. Trace the chain; fix any broken link; write 3 tests

# 5. Run
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/workers/generate/ -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q
```

---

## GE-04 — G2: OPT-4 api_surface_block Pruning Verification and Fix

**Status**: Done
**Evidence**: 4/4 tests pass (TestApiSurfacePruning); 2641 total suite green. Files: section_prompt.py (OPT-4 pruning block added after golden_dir computation), tests/unit/workers/generate/test_section_prompt.py (+TestApiSurfacePruning class).
**Gap linkage**: G-GE-04
**Role**: Senior engineer. Drop-in, production-ready.

### Scope

**Fix**: Verify that OPT-4 is implemented: when `golden_index.get_spec(...)` returns a spec
where `"code"` is NOT in `required_block_types`, the `api_surface_block` in `build_section_prompt()`
is replaced with `"(No code output expected for this section — omit all code blocks)"`.

Also verify the guard: `api_reference` and `reference_object_page` roles must ALWAYS get the
full API surface regardless of golden spec.

If either the pruning or the guard is missing, implement it. If both are present but untested,
add tests.

**Allowed paths**:
- `src/launcher/workers/generate/section_prompt.py`
- `tests/workers/generate/test_section_prompt.py`

**Forbidden**: Any other file or path.

### Acceptance checks

- **CLI**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/workers/generate/test_section_prompt.py -v` — all PASS
- **UI/Web/API**: N/A
- **Tests**:
  - `test_api_surface_pruned_when_no_code_in_spec` — golden spec has `required_block_types=["paragraph"]` → prompt contains pruning message, not API surface
  - `test_api_surface_preserved_when_code_in_spec` — golden spec has `"code"` in required → full API surface preserved
  - `test_api_surface_preserved_for_api_reference_role` — `page_role="api_reference"` always gets full API surface even when golden spec lacks code
  - `test_api_surface_preserved_when_no_golden_spec` — golden returns None for spec → full API surface preserved
- **Config respected end-to-end**: golden spec drives pruning decision; no config file change
- **No mock data in production paths**: `GoldenBlockSpec` fixture used in tests; production `GoldenIndex` unchanged

### Deliverables

- `src/launcher/workers/generate/section_prompt.py` — fix/verify OPT-4 pruning logic (targeted section only)
- `tests/workers/generate/test_section_prompt.py` — 4 new test functions for pruning behavior
- No stubs, no TODOs

### Hard rules

- `api_reference` and `reference_object_page` are the two protected roles — hardcoded set, not configurable
- When `golden_index is None` → no pruning (preserve current behavior exactly)
- Pruning message exact text: `"(No code output expected for this section — omit all code blocks)"`
- No new dependencies

### Review dimensions

| Dimension | 5/5 means |
|-----------|-----------|
| D1 Specification Alignment | Pruning message text matches plan spec exactly |
| D6 Production Robustness | Guards: `golden_index is None` → no pruning; reference roles → no pruning regardless |
| D7 Test Coverage | 4 functions: pruned + preserved-with-code + reference-role + no-golden |
| D12 Content Quality | Reference pages always get full API surface; text-only sections get cleaner prompts |

### Now (runbook)

```bash
# 1. Check current OPT-4 implementation status in section_prompt.py
grep -n "api_surface\|code.*spec\|required_block\|omit all code\|OPT-4\|opt.4" src/launcher/workers/generate/section_prompt.py | head -20

# 2. Check api_reference guard
grep -n "api_reference\|reference_object" src/launcher/workers/generate/section_prompt.py | head -10

# 3. Read test file to see existing coverage
# Glob tests/**/test_section_prompt*
# Read existing test file

# 4. Implement missing pieces; write 4 tests

# 5. Run
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/workers/generate/test_section_prompt.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q
```

---

## GE-05 — G1: has_code Acceptance Check Test

**Status**: Done
**Evidence**: test_code_required_when_has_code exists at tests/unit/test_golden_loader.py:146; verified in prior session.
**Gap linkage**: G-GE-05
**Role**: Senior engineer. Drop-in, production-ready.

### Scope

**Fix**: The plan (Phase 1) specifies the acceptance check:
`GoldenIndex.get("workflow_page", "standard").sections[0].has_code == True`.
This assertion is not in `tests/unit/test_golden_loader.py`. Add it, and add a companion
test that verifies the `workflow_page` golden page has at least 5 sections.

**Allowed paths**:
- `tests/unit/test_golden_loader.py`

**Forbidden**: Any other file or path. Do not modify `golden_loader.py` or any `src/` file.

### Acceptance checks

- **CLI**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/test_golden_loader.py -v` — all PASS
- **UI/Web/API**: N/A
- **Tests**:
  - `test_workflow_page_standard_first_section_has_code` — `index.get("workflow_page", "standard").sections[0].has_code == True`
  - `test_workflow_page_standard_has_min_five_sections` — `len(index.get("workflow_page", "standard").sections) >= 5`
- **Config respected end-to-end**: uses real `golden/` directory; test is not a mock assertion
- **No mock data in production paths**: loads real golden files from `golden/` directory

### Deliverables

- `tests/unit/test_golden_loader.py` — full replacement adding 2 new test functions in the `TestGoldenIndexGet` or equivalent class
- All 23 existing tests preserved verbatim

### Hard rules

- Tests use the real `golden/` directory fixture (same as existing tests in file)
- If `workflow_page` golden files don't exist or `sections[0].has_code` is False, the test finding reveals a real data gap — do not mock around it
- No new dependencies

### Review dimensions

| Dimension | 5/5 means |
|-----------|-----------|
| D1 Specification Alignment | Acceptance check from plan exactly implemented as a test |
| D7 Test Coverage | 2 functions: has_code on first section + min 5 sections |
| D13 Integration | Uses real golden directory and real GoldenIndex.load(); not a mock |

### Now (runbook)

```bash
# 1. Check what golden files exist for workflow_page
ls golden/ | grep workflow

# 2. Read test_golden_loader.py to find fixture pattern
# Read tests/unit/test_golden_loader.py

# 3. Find which (page_role, variant) key maps to workflow_page/standard
grep -n "workflow_page\|select_for_tier" tests/unit/test_golden_loader.py | head -10

# 4. Add 2 test functions in existing class

# 5. Run
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/test_golden_loader.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q
```
