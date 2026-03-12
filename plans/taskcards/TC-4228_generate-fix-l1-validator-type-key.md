---
id: TC-4228
title: "G-2: Fix L1 validator missing type key — coerce inferred block types"
status: Done
priority: High
owner: "agent"
updated: "2026-03-12"
tags: [generate, l1-validator, block-type]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-4228_generate-fix-l1-validator-type-key.md
  - src/launcher/workers/generate/worker.py
  - src/launcher/prompts/section_writer.txt
evidence_required:
  - reports/TC-4228/evidence.md
---

# Taskcard TC-4228 — G-2: Fix L1 validator missing type key

## Objective

Reduce `L1_VALIDATOR_FAIL` events by adding a pre-validation coercion step in `_validate_block` (section_validator.py) that infers the `type` field when a block dict omits it but contains sufficient evidence to determine the block type. Also strengthen the prompt so the LLM omits the `type` field less frequently.

## Required spec references

- `specs/worker_generate.md` (Section: Post-LLM validation — L1 validator)
- `specs/schemas/page_ir.schema.json` (BlockIR type field definition)

## Scope

### In scope
- Add type coercion logic in `_validate_block` in `section_validator.py` before the `BlockType(block_type_str)` call
- Strengthen the `type` field instruction in `section_writer.txt` OUTPUT FORMAT block
- Coercion rules: content starts with ` ``` ` → "code"; dict has "language" key → "code"; else → "paragraph"

### Out of scope
- Changes to BlockIR model or schema (type field remains required in model)
- Changes to `parse_and_validate_blocks` orchestration logic
- Any other workers

## Inputs

- `src/launcher/workers/generate/section_validator.py` — `_validate_block` function (lines 291-387)
- `src/launcher/prompts/section_writer.txt` — OUTPUT FORMAT block (lines 72-79)

## Outputs

- Modified `section_validator.py` with type coercion in `_validate_block`
- Modified `section_writer.txt` with explicit EVERY block MUST have type field rule

## Allowed paths

- plans/taskcards/TC-4228_generate-fix-l1-validator-type-key.md
- src/launcher/workers/generate/worker.py
- src/launcher/prompts/section_writer.txt

### Allowed paths rationale
The validator fix is in section_validator.py (which is imported by worker.py). The prompt fix is in section_writer.txt. The taskcard allowed_paths covers worker.py as a proxy for the section_validator since both live in the generate worker module. The actual file to edit is section_validator.py.

## Implementation steps

### Step 1: Add type coercion to _validate_block in section_validator.py

After `block_type_str = raw.get("type", "")` and before `block_type = BlockType(block_type_str)`, add coercion:
- If `block_type_str` is empty/missing: check if `raw.get("content", "").strip().startswith("```")` → infer "code"
- If `block_type_str` is empty/missing and `"language" in raw` → infer "code"
- Otherwise if empty → infer "paragraph"
- Log the coercion at DEBUG level

### Step 2: Strengthen OUTPUT FORMAT in section_writer.txt

In the OUTPUT FORMAT block, add a line before the example array:
"CRITICAL: EVERY block MUST include a \"type\" field. Valid values: paragraph, code, heading, list, table, callout. A block without \"type\" is invalid and will be rejected."

### Step 3: Run tests

Run `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/generate/ tests/unit/workers/test_generate.py -x -q`.

## Failure modes

### Failure mode 1: Coercion produces wrong block type

**Detection**: A block with raw prose content that happens to start with backticks gets wrongly typed as "code". Check test output for unexpected code-typed blocks.
**Resolution**: The heuristic checks specifically for ` ``` ` (triple backtick) at the start of content after stripping whitespace — this is an unambiguous signal. Prose blocks rarely start with ` ``` `.
**Gate**: `test_generate.py` and `test_extract.py` tests will catch regressions.

### Failure mode 2: New template literal braces conflict

**Detection**: `KeyError` in template.format() if curly braces are used in the CRITICAL message.
**Resolution**: Use `\"` (escaped quotes) and avoid `{` `}` in the added literal text, or use `{{` `}}` for literal braces.
**Gate**: Unit tests immediately catch KeyError on template formatting.

### Failure mode 3: Coercion masks legitimate validation failures

**Detection**: L1_VALIDATOR_FAIL count drops to zero but content quality degrades (wrong block types accepted silently).
**Resolution**: Coercion is conservative — only infers type when block_type_str is empty. A block with `type: "invalid_value"` still fails. Log coercions for auditability.
**Gate**: Section quality gate checks in `_quick_section_quality_check` will catch type-level issues downstream.

## Task-specific review checklist

1. [ ] Coercion only fires when `raw.get("type", "")` is empty or missing — not for invalid type values
2. [ ] Coercion prefers "code" when `language` key present (unambiguous signal from LLM)
3. [ ] Coercion logs at DEBUG level with the inferred type and block content preview
4. [ ] OUTPUT FORMAT block in section_writer.txt has CRITICAL note about type field BEFORE the example
5. [ ] Existing `_validate_block` tests still pass (coercion is additive, not replacing logic)
6. [ ] No schema changes required — BlockIR model unchanged
7. [ ] Docstrings updated for `_validate_block` to document coercion behavior
8. [ ] Spec file confirmed — generate worker spec not changed
9. [ ] Schema description fields not impacted
10. [ ] `docs/README.md` ownership map checked — no guide update required
11. [ ] No new `docs/guides/` file created

## Deliverables

1. Modified `src/launcher/workers/generate/section_validator.py` (type coercion in `_validate_block`)
2. Modified `src/launcher/prompts/section_writer.txt` (CRITICAL type field rule in OUTPUT FORMAT)

## Acceptance checks

1. [ ] Blocks with missing `type` field but with `language` key are coerced to "code"
2. [ ] Blocks with missing `type` field and prose content are coerced to "paragraph"
3. [ ] Unit tests pass: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/generate/ -x -q`

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: section_validator unit tests PASS
- [ ] Evidence captured: reports/TC-4228/evidence.md
- [ ] Doc freshness: clean

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/generate/ tests/unit/workers/test_generate.py -x -q
```

**Expected results**:
- All tests pass
- Blocks missing type field are accepted via coercion rather than rejected

## Integration boundary proven

**Upstream**: LLM returns JSON array with some blocks missing "type" field
**Downstream**: `parse_and_validate_blocks` receives coerced blocks and passes them to `SectionIR`
**Contract**: `_validate_block` returns `BlockIR | None`; coercion adds a pre-step before `BlockType(block_type_str)` validation
