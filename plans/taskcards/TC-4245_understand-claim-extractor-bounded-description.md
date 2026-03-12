---
id: TC-4245
title: "Rewrite claim_extractor.txt — LLM as describer of verified facts, not discoverer"
status: Done
priority: P0
owner: "B_implementation"
updated: "2026-03-12"
tags: ["understand", "llm", "prompt", "hallucination"]
depends_on: ["TC-4242", "TC-4244"]
allowed_paths:
  - plans/taskcards/TC-4245_understand-claim-extractor-bounded-description.md
  - src/launcher/prompts/claim_extractor.txt
  - src/launcher/workers/understand/extract/_llm.py
  - tests/unit/workers/understand/test_extract.py
  - reports/agents/B_implementation/TC-4245/evidence.md
  - reports/agents/B_implementation/TC-4245/self_review.md
evidence_required:
  - reports/agents/B_implementation/TC-4245/evidence.md
---

# Taskcard TC-4245 — Rewrite claim_extractor.txt — LLM as describer of verified facts, not discoverer

## Objective

Rewrite the LLM claim extraction prompt (`claim_extractor.txt`) from open-ended discovery mode to bounded-description mode. The LLM receives a structured set of verified facts and describes them, instead of discovering facts from raw documentation. This is the core architectural change that eliminates LLM hallucination of API names, format names, and capabilities not present in the source code.

## Required spec references

- `specs/worker_understand.md` (Claim extraction algorithm, sandwich model)
- `specs/claims_evidence.md` (Claim structure, evidence anchoring)

## Scope

### In scope
- Rewrite `src/launcher/prompts/claim_extractor.txt` to support both discovery mode and bounded-description mode via template variables
- Add `_DISCOVERY_TASK_INSTRUCTIONS` module-level constant to `_llm.py`
- Update the `prompt_template.format()` call in `_call_llm_extract()` to supply new template variables with backward-compatible defaults
- Add `source_fact_id` optional field to the OUTPUT FORMAT example in the prompt

### Out of scope
- ExtractionDatabase population (TC-4244)
- Injection of ExtractionDatabase facts into the new template variables (TC-4246)
- Any changes to `_entry.py`, `_deterministic.py`, or other extract modules
- Any changes to claim models or schemas

## Inputs

- `src/launcher/prompts/claim_extractor.txt` — current prompt (discovery mode only)
- `src/launcher/workers/understand/extract/_llm.py` — current LLM call code
- Current template variables: `{family}`, `{platform}`, `{repo_url}`, `{source_material}`, `{family_slug}`

## Outputs

- Updated `src/launcher/prompts/claim_extractor.txt` with new template variables supporting bounded-description mode
- Updated `src/launcher/workers/understand/extract/_llm.py` with `_DISCOVERY_TASK_INSTRUCTIONS` constant and new `format()` call
- Evidence file at `reports/agents/B_implementation/TC-4245/evidence.md`

## Allowed paths

- plans/taskcards/TC-4245_understand-claim-extractor-bounded-description.md
- src/launcher/prompts/claim_extractor.txt
- src/launcher/workers/understand/extract/_llm.py
- tests/unit/workers/understand/test_extract.py
- reports/agents/B_implementation/TC-4245/evidence.md
- reports/agents/B_implementation/TC-4245/self_review.md

### Allowed paths rationale
- `claim_extractor.txt`: The prompt being rewritten
- `_llm.py`: The caller that formats and passes the template variables
- `test_extract.py`: May need updating if tests check prompt variable names
- Evidence files: Required by AG-002

## Implementation steps

### Step 1: Rewrite `claim_extractor.txt`

Replace the current prompt with the new template supporting three new variables:
- `{verified_facts_block}`: Empty string in backward-compatible mode; structured facts in bounded-description mode
- `{source_context_block}`: Wraps `{source_material}` with appropriate label
- `{task_instructions}`: Either discovery instructions or description instructions

Keep CLAIM KINDS, EXCLUSIONS, PRIORITY, and EXAMPLES sections verbatim. Add `source_fact_id` optional field to the OUTPUT FORMAT example.

### Step 2: Add `_DISCOVERY_TASK_INSTRUCTIONS` constant to `_llm.py`

Add a module-level constant containing the discovery mode task instructions (same rules as the current prompt's RULES section).

### Step 3: Update `_call_llm_extract()` format call

Replace the 5-variable `format()` call with a 8-variable call that includes the three new variables, defaulting to backward-compatible values. Keep `source_material` variable to avoid breaking any legacy references.

### Step 4: Run tests

```bash
cd c:/Users/prora/OneDrive/Documents/GitHub/foss-launcher-v2
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/ tests/integration/test_understand_pipeline.py -v --tb=short 2>&1 | tail -30
```

### Step 5: Write evidence.md

Capture the before/after diff and backward-compatibility proof.

## Failure modes

### Failure mode 1: Python str.format() KeyError for unescaped braces

**Detection**: `KeyError` during `prompt_template.format(...)` in `_call_llm_extract()`. The OUTPUT FORMAT JSON example uses `{{` and `}}` to escape literal braces; if any `{` or `}` in the new template sections is not escaped, format() raises KeyError.
**Resolution**: Audit every `{` and `}` in the new template. Only the 8 named variables should use single braces. All JSON examples and other literal braces must use double braces.
**Gate**: Unit test that calls `_call_llm_extract()` with a mocked LLM client

### Failure mode 2: `source_material` variable removed, breaking evidence_context injection

**Detection**: Tests referencing `evidence_context` injection fail; `_entry.py` passes `evidence_context` which gets prepended to `source_material` before the format call — if `{source_material}` is removed from template, the format() call fails.
**Resolution**: Keep `{source_material}` in the template OR remove it only after `{source_context_block}` fully replaces its role. For TC-4245, keep both.
**Gate**: `tests/unit/workers/understand/test_extract.py` passes

### Failure mode 3: Conditional empty `{verified_facts_block}` creates double blank lines

**Detection**: Prompt renders with visually awkward double blank lines when `verified_facts_block=""`. This is cosmetic, not functional.
**Resolution**: The template uses `{verified_facts_block}\n\n` — empty string means one extra blank line, which is acceptable. OR pre-compute the block as `"\n" + facts + "\n"` vs `""` in the caller.
**Gate**: Manual inspection of rendered prompt with empty verified_facts_block

## Task-specific review checklist

1. [x] New template variables are backward-compatible: existing tests pass without any change
2. [x] `{source_material}` variable is still present in template for backward-compatibility
3. [x] All JSON example braces in the template are doubled (`{{`, `}}`)
4. [x] `_DISCOVERY_TASK_INSTRUCTIONS` matches the RULES section from the old prompt verbatim
5. [x] `source_fact_id` field added to OUTPUT FORMAT example with default `""`
6. [x] Bounded-description mode constraints documented (API identifiers from VERIFIED FACTS only)
7. [x] Docstrings updated for `_call_llm_extract()` to mention new template variables
8. [x] Spec file confirmed: no spec drift (prompt rewrite, not behavior change in bounded mode)
9. [x] Schema `"description"` fields: not applicable (no schema change)
10. [x] `docs/README.md` ownership map checked — no trigger event
11. [x] Evidence file written at `reports/agents/B_implementation/TC-4245/evidence.md`

## Deliverables

1. `src/launcher/prompts/claim_extractor.txt` — rewritten prompt with 3 new template variables
2. `src/launcher/workers/understand/extract/_llm.py` — updated with constant and new format() call
3. `reports/agents/B_implementation/TC-4245/evidence.md` — diff + backward-compatibility proof

## Acceptance checks

1. [x] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/ -v --tb=short` — 324 passed
2. [x] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=no` — 602 understand-related passed; 7 pre-existing failures unrelated to TC-4245
3. [x] `src/launcher/prompts/claim_extractor.txt` contains `{verified_facts_block}`, `{source_context_block}`, `{task_instructions}`
4. [x] `_llm.py` contains `_DISCOVERY_TASK_INSTRUCTIONS` module-level constant
5. [x] `_llm.py` format() call passes `verified_facts_block=""`, `source_context_block=...`, `task_instructions=_DISCOVERY_TASK_INSTRUCTIONS`
6. [x] Evidence file exists at `reports/agents/B_implementation/TC-4245/evidence.md`

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: backward-compatibility verified
- [ ] Evidence captured: reports/agents/B_implementation/TC-4245/evidence.md
- [ ] Doc freshness: checked — no spec drift

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/ tests/integration/test_understand_pipeline.py -v --tb=short
```

**Expected results**:
- All understand worker unit tests pass
- Integration pipeline test passes
- No KeyError from format() call

## Integration boundary proven

**Upstream**: `_entry.py::run_extract()` calls `_extract_claims_llm()` → `_call_llm_extract()` with `evidence_context` string
**Downstream**: LLM response parsed by `_parse_claims_json()`, validated by `_validate_and_normalize_claims()`
**Contract**: `claim_extractor.txt` template accepts 8 named variables; returns JSON array of claim dicts matching the output format schema
