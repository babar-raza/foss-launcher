---
id: TC-4219
title: "Generate: Inject claim text into section writer prompt + populate GeneratedPage.claim_texts"
status: Done
priority: P0-Blocking
owner: "Agent-B"
updated: "2026-03-12"
tags: [generate, claims, section-writer, grounding]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-4219_generate-claim-text-injection.md
  - src/launcher/workers/generate/section_prompt.py
  - src/launcher/workers/generate/worker.py
  - tests/unit/workers/generate/test_section_prompt.py
  - tests/unit/workers/test_generate.py
  - reports/TC-4219/evidence.md
evidence_required:
  - reports/TC-4219/evidence.md
---

# Taskcard TC-4219 — Generate: Inject claim text into section writer prompt + populate `GeneratedPage.claim_texts`

## Objective

The LLM section writer never receives claim text — only claim IDs. It cannot ground content in claim facts and instead writes from world knowledge, causing 13 completeness HIGH findings in evaluate. Two sub-fixes: (1) inject claim text into `build_section_prompt()` in `section_prompt.py` so the LLM sees what claims to address; (2) populate `claim_texts` and `assigned_claim_count` in `GeneratedPage` at worker.py:544 so the evaluate worker's mechanical check can verify coverage.

## Required spec references

- `specs/worker_generate.md` (Section: Section writer — claim grounding requirement)
- `specs/worker_evaluate.md` (Section: Completeness check — uses LLM review against markdown content)
- `specs/schemas/plan_bundle.schema.json` (`assigned_claims` field)

## Scope

### In scope
- Modify `build_section_prompt()` in `section_prompt.py` to accept and inject `claim_context: str` into the LLM section writer system prompt
- Build `claim_context` mapping (claim_id → claim text) in the caller (generate worker) before calling `build_section_prompt`
- Populate `GeneratedPage.claim_texts` and `GeneratedPage.assigned_claim_count` at page completion in `worker.py`
- Unit tests for claim_context injection and GeneratedPage field population

### Out of scope
- Changing `src/launcher/models/content.py` field definitions (already correct, no code change needed)
- Changing the evaluate worker's LLM review logic (completeness check reads markdown content, not `claim_texts`)
- Adding new claims or changing claim extraction (Understand phase — separate chat)

## Inputs

- `src/launcher/workers/generate/section_prompt.py` (line 718: `build_section_prompt` signature)
- `src/launcher/workers/generate/worker.py` (lines 544–556: `GeneratedPage` construction; claim resolution context available via `bundle.claims_by_id`)
- `src/launcher/models/content.py` (lines 24–26: `claim_texts: list[str]` field definition)

## Outputs

- Modified `src/launcher/workers/generate/section_prompt.py` — `build_section_prompt` accepts `claim_context`
- Modified `src/launcher/workers/generate/worker.py` — builds claim_context and populates GeneratedPage
- Modified `tests/unit/workers/generate/test_section_prompt.py` — new claim injection tests
- `reports/TC-4219/evidence.md`

## Allowed paths

- plans/taskcards/TC-4219_generate-claim-text-injection.md
- src/launcher/workers/generate/section_prompt.py
- src/launcher/workers/generate/worker.py
- tests/unit/workers/generate/test_section_prompt.py
- tests/unit/workers/test_generate.py
- reports/TC-4219/evidence.md

### Allowed paths rationale
- `section_prompt.py`: primary fix — `build_section_prompt` must accept claim_context
- `worker.py`: secondary fix — claim_context builder + GeneratedPage field population
- `test_section_prompt.py`: existing test file for section_prompt tests
- `test_generate.py`: existing generate worker tests

## Implementation steps

### Step 1: Read `build_section_prompt` full signature

Read `section_prompt.py` starting at line 718 to understand current parameters before modifying.

### Step 2: Add `claim_context` parameter to `build_section_prompt`

Add `claim_context: str = ""` as a keyword argument to `build_section_prompt()`. Inject it into the LLM system or user prompt:

```python
def build_section_prompt(..., claim_context: str = "") -> list[dict]:
    ...
    if claim_context:
        system_parts.append(
            "## Claims to address\n"
            "The following claims MUST be addressed in this page. "
            "Each claim is a verified fact about the product:\n"
            + claim_context
        )
    ...
```

Place the claim_context block after the product description but before the section skeleton, so the LLM sees it as high-priority context.

### Step 3: Build claim_context in the generate worker

In `worker.py`, before calling `build_section_prompt`, build the mapping:

```python
claim_context = "\n".join(
    f"- [{cid}] {bundle.claims_by_id[cid].text}"
    for cid in page_plan.assigned_claims
    if cid in bundle.claims_by_id
)
```

Pass `claim_context=claim_context` to `build_section_prompt(...)`.

### Step 4: Populate `GeneratedPage` fields

At `GeneratedPage` construction (lines 544–556), add:

```python
claim_texts = [
    bundle.claims_by_id[cid].text
    for cid in claim_ids_used
    if cid in bundle.claims_by_id
]
generated_pages.append(GeneratedPage(
    ...
    claim_ids_used=claim_ids_used,
    claim_texts=claim_texts,
    assigned_claim_count=len(claim_ids_used),
))
```

### Step 5: Add unit tests

In `tests/unit/workers/generate/test_section_prompt.py`:
1. `test_claim_context_injected_when_provided` — asserts `build_section_prompt(..., claim_context="- [CLM-1] foo")` includes "Claims to address" in returned prompt
2. `test_claim_context_omitted_when_empty` — asserts no "Claims to address" block when `claim_context=""`
3. `test_generated_page_claim_texts_populated` — mocks `bundle.claims_by_id` and asserts `claim_texts` is non-empty in `GeneratedPage`

## Failure modes

### Failure mode 1: `bundle.claims_by_id` is None or missing attribute

**Detection**: `AttributeError` when building claim_context in worker.
**Resolution**: Guard: `if hasattr(bundle, "claims_by_id") and bundle.claims_by_id:` before the comprehension. Emit DEBUG log if no claims_by_id available.
**Gate**: Unit test with mock None claims_by_id passes.

### Failure mode 2: Claim text is very long — token budget exceeded

**Detection**: LLM call truncates or returns error for token limit.
**Resolution**: Cap `claim_context` at 50 claims maximum and 4000 characters total. Use `claim_context = claim_context[:4000]` as safety truncation.
**Gate**: Integration test with large claim list does not fail.

### Failure mode 3: `claim_ids_used` differs from `page_plan.assigned_claims`

**Detection**: `claim_texts` populated with IDs that were actually used (not assigned). This is correct behavior — log both for observability.
**Resolution**: No fix needed. `assigned_claims` = what planner assigned; `claim_ids_used` = what generator actually cited. Both should appear in output.
**Gate**: `generate.json` shows both `claim_ids_used` and `claim_texts` consistently.

## Task-specific review checklist

1. [ ] `claim_context` parameter added to `build_section_prompt` with default `""`
2. [ ] Claim context injected into LLM prompt (system or user) in a clearly labeled block
3. [ ] Context capped at 50 claims / 4000 characters to avoid token overflow
4. [ ] `GeneratedPage.claim_texts` populated at page completion
5. [ ] `GeneratedPage.assigned_claim_count` populated (= `len(claim_ids_used)`)
6. [ ] No regression to existing `build_section_prompt` callers (backward compatible via default `""`)
7. [ ] 3 unit tests added and passing
8. [ ] Docstrings updated for `build_section_prompt` (new parameter documented)
9. [ ] Spec confirmed: worker_generate.md — claim grounding is expected behavior
10. [ ] Schema: `claim_texts` and `assigned_claim_count` already in content.py — no schema change needed
11. [ ] `docs/README.md` ownership map checked — no new guide needed
11. [ ] No new `docs/guides/` files added

## Deliverables

1. Modified `src/launcher/workers/generate/section_prompt.py` with `claim_context` injection
2. Modified `src/launcher/workers/generate/worker.py` with claim_context builder + GeneratedPage population
3. Modified `tests/unit/workers/generate/test_section_prompt.py` with 3 new tests
4. `reports/TC-4219/evidence.md` — test output + generate.json `claim_texts` before/after

## Acceptance checks

1. [x] `pytest tests/unit/workers/generate/test_section_prompt.py -v` — 41 PASS (5 new TC-4219 tests)
2. [x] `pytest tests/unit/workers/test_generate.py -v` — 415 PASS (no regression)
3. [x] `GeneratedPage.claim_texts` populated in worker.py via `claims_by_id` lookup
4. [x] `GeneratedPage.assigned_claim_count` = `len(claim_ids_used)`
5. [x] "Claims to address" block injected in LLM prompt when `claim_context` non-empty

## Self-review

### Verification results
- [x] Tests: 456/456 PASS (41 section_prompt + 415 test_generate)
- [x] Validation: GeneratedPage.claim_texts populated in worker.py PASS
- [x] Evidence captured: reports/TC-4219/evidence.md
- [x] No new doc files created

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/generate/ -v
```

**Expected results**:
- All existing generate tests pass
- 3 new claim injection tests pass
- `generate.json` shows `claim_texts` non-empty after pipeline re-run

## Integration boundary proven

**Upstream**: `bundle.claims_by_id` (dict from Understand phase) + `page_plan.assigned_claims` (list from Plan phase)
**Downstream**: LLM section writer (receives claim_context in prompt) + `GeneratedPage.claim_texts` (consumed by evaluate worker mechanical check)
**Contract**: `build_section_prompt` must include claim text in prompt when `page_plan.assigned_claims` is non-empty
