---
id: TC-3783
title: "Relax 'use ALL claims' prompt constraint"
status: In-Progress
priority: Critical
owner: agent
updated: "2026-03-07"
tags: [content-quality, generate, P0]
depends_on: [TC-3782]
allowed_paths:
  - plans/taskcards/TC-3783_prompt_claim_relaxation.md
  - src/launcher/workers/generate/section_prompt.py
  - src/launcher/prompts/section_writer.txt
  - src/launcher/workers/generate/worker.py
  - tests/test_prompt_relaxation.py
evidence_required:
  - runs/*/evidence/llm_calls/*.json
---

# Taskcard TC-3783 — Relax "use ALL claims" prompt constraint

## Objective

Change the generate prompt from "use ALL of these claims, do not invent new facts" to "use the most relevant claims from the list below". This prevents the LLM from producing confused content when claims include marginal or off-topic entries (defense-in-depth after TC-3782 filtering). Also reduce prompt bloat by limiting snippets per section.

## Required spec references

- `specs/worker_generate.md` (Section prompt construction)
- `specs/system_overview.md` (Rule 5: Sandwich model)

## Scope

### In scope
- Change "use ALL" to "use the most relevant" in prompt template
- Add product name and section topic as relevance anchors
- Cap snippets per section to reduce prompt size (max 5 per section)
- Add LLM error logging in _call_llm (log exception type/message)

### Out of scope
- Claim extraction filtering (TC-3782)
- Fallback renderer improvements (future TC)
- Planner relevance scoring (future TC)

## Inputs

- `src/launcher/prompts/section_writer.txt` — prompt template
- `src/launcher/workers/generate/section_prompt.py` — prompt builder

## Outputs

- Updated prompt template with relaxed claim constraint
- Reduced prompt sizes (target: <50KB per section vs current 114-215KB)
- LLM error messages logged on failure

## Allowed paths

- `plans/taskcards/TC-3783_prompt_claim_relaxation.md` — this taskcard
- `src/launcher/workers/generate/section_prompt.py` — prompt builder changes
- `src/launcher/prompts/section_writer.txt` — prompt template text
- `src/launcher/workers/generate/worker.py` — LLM error logging + snippet cap
- `tests/test_prompt_relaxation.py` — tests

### Allowed paths rationale
- section_prompt.py: Changes claim/snippet formatting and distribution
- section_writer.txt: Changes the "use ALL" instruction text
- worker.py: Add error logging and snippet cap in _generate_page
- tests/: New test file

## Implementation steps

### Step 1: Update prompt template (section_writer.txt)

Change:
```
CLAIMS TO USE (use ALL of these, do not invent new facts):
```
To:
```
CLAIMS (use the most relevant claims below; skip any that don't fit this section's topic):
```

Add product anchoring:
```
FOCUS: This section is about {display_name} ({canonical_import}). Only include information directly relevant to this product.
```

### Step 2: Cap snippets per section in section_prompt.py

In `build_section_prompt`, limit `section_snippets` to max 5 (sorted by relevance — prefer snippets whose claim_ids overlap with section claims).

### Step 3: Add LLM error logging in worker.py

In `_call_llm` exception handlers (lines 436-437, 457-458):
- Log the full exception type and first 200 chars of the message
- Emit an event: `llm.call.failed` with `{endpoint, error_type, error_msg[:200]}`

### Step 4: Add tests

- Test that prompt contains "most relevant" not "ALL"
- Test that snippet count per section <= 5
- Test prompt size is reduced

## Failure modes

### Failure mode 1: LLM drops all claims and produces empty content

**Detection**: parse_and_validate_blocks returns None or empty blocks for sections with claims
**Resolution**: Add minimum claim usage instruction: "use at least 1 claim if any are provided"
**Gate**: Generate self-review checks word count >= 50 per content section

### Failure mode 2: Prompt template format string breaks

**Detection**: KeyError during `template.format()` call
**Resolution**: Verify all `{placeholders}` match the format call arguments
**Gate**: Unit test that builds a prompt without error

### Failure mode 3: Snippet cap removes critical code examples

**Detection**: Generated pages have 0 code blocks for code-required roles
**Resolution**: Prioritize snippets by claim_id overlap, not arbitrary order
**Gate**: Generate self-review checks code_block_count > 0 for workflow pages

## Task-specific review checklist

1. [ ] Prompt contains "most relevant" not "ALL"
2. [ ] Prompt includes product name anchoring
3. [ ] Snippet count per section <= 5
4. [ ] Average prompt size < 50KB (measure on pilot)
5. [ ] LLM errors are logged with type and message
6. [ ] All existing tests pass

## Deliverables

1. Updated `src/launcher/prompts/section_writer.txt`
2. Updated `src/launcher/workers/generate/section_prompt.py`
3. Updated `src/launcher/workers/generate/worker.py` (error logging)
4. New `tests/test_prompt_relaxation.py`

## Acceptance checks

1. [ ] Prompt template updated
2. [ ] Snippet cap implemented
3. [ ] Error logging added
4. [ ] All tests pass
5. [ ] Fresh pilot run prompt sizes < 50KB average

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Evidence captured: prompt samples from pilot run

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/test_prompt_relaxation.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -v --timeout=60
```

**Expected results**:
- All tests pass
- Pilot run LLM fallback rate < 20%

## Integration boundary proven

**Upstream**: Planner provides PlanBundle with assigned claims/snippets
**Downstream**: Section validator parses LLM response into BlockIR
**Contract**: Prompt text format unchanged (JSON array of blocks expected from LLM)
