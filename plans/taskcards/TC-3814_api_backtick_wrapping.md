---
id: TC-3814
title: "API Name Backtick Wrapping (Retroactive)"
status: Done
priority: Normal
owner: "agent"
updated: "2026-03-07"
tags: [backtick, api-names, disambiguation, generate]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-3814_api_backtick_wrapping.md
  - src/launcher/models/product.py
  - specs/schemas/understanding_bundle.schema.json
  - src/launcher/workers/understand/extract.py
  - src/launcher/prompts/section_writer.txt
  - src/launcher/workers/generate/section_prompt.py
  - src/launcher/workers/generate/worker.py
  - src/launcher/workers/generate/section_validator.py
  - src/launcher/prompts/review_prompt.txt
evidence_required:
  - plans/healing/BT-00-backtick-healing-gap-index.md
---

# Taskcard TC-3814 — API Name Backtick Wrapping (Retroactive)

> **Note**: Retroactive — created post-implementation to satisfy AG-002.
> Code was written and tested before this taskcard was created.
> Healing taskcards BT-01 through BT-07 cover follow-up fixes and tests.

## Objective

Ensure all API identifiers (class names, methods, properties) are wrapped in
backticks when mentioned in prose or table cells of generated .md files. The
system must disambiguate API names from regular English words (e.g., "Cells"
as a class vs. "cells" as a word) using AST-extracted inventories.

## Required spec references

- `specs/07_code_analysis_and_enrichment.md` (AST extraction pipeline)
- `specs/schemas/understanding_bundle.schema.json` (ApiSurface schema)

## Scope

### In scope
- Enrich ApiSurface model with `api_identifiers` field
- Update JSON schema for backward compatibility
- Collect class/method/property names during understanding phase
- Add backtick wrapping rule to LLM prompt
- Post-LLM sanitizer (`_backtick_api_names`) for engineering backstop
- Review prompt update with code formatting check

### Out of scope
- Gate reorganization (separate plan)
- Backtick detection gate (future work)
- Non-AST identifier sources

## Inputs

- AST analysis results from `code_analyzer.analyze_file_safe()`
- Understanding bundle with enriched ApiSurface
- LLM raw response (JSON array of BlockIR)

## Outputs

- Enriched `ApiSurface` with `api_identifiers: list[str]`
- Updated JSON schema with optional `api_identifiers` property
- Backtick-wrapped API names in all generated prose/table blocks
- Review prompt check #10 for code formatting

## Allowed paths

- plans/taskcards/TC-3814_api_backtick_wrapping.md
- src/launcher/models/product.py
- specs/schemas/understanding_bundle.schema.json
- src/launcher/workers/understand/extract.py
- src/launcher/prompts/section_writer.txt
- src/launcher/workers/generate/section_prompt.py
- src/launcher/workers/generate/worker.py
- src/launcher/workers/generate/section_validator.py
- src/launcher/prompts/review_prompt.txt

### Allowed paths rationale
Each file corresponds to one step in the 4-step plan: model enrichment,
schema update, extraction, prompt, formatting, validator, worker threading,
review prompt.

## Implementation steps

### Step 1: Enrich ApiSurface model
Added `api_identifiers: list[str] = Field(default_factory=list)` to
`ApiSurface` in `product.py`. Backward compatible via default factory.

### Step 2: Update JSON schema
Added `api_identifiers` property to `understanding_bundle.schema.json`
(NOT added to `required` array for backward compat).

### Step 3: Collect identifiers during extraction
Modified `_extract_api_surface()` in `extract.py` to harvest method and
property names from `analyze_file_safe()` results. Skips private names,
deduplicates, caps at 500.

### Step 4: LLM prompt + formatting
Added backtick rule to `section_writer.txt`. Updated `_format_api_surface()`
in `section_prompt.py` to present class names with backticks.

### Step 5: Post-LLM sanitizer
Added `_backtick_api_names()` to `section_validator.py`. Extended
`parse_and_validate_blocks()` and `_validate_block()` with optional
`api_identifiers` parameter. Threaded through from `worker.py`.

### Step 6: Review prompt
Added check #10 for code formatting to `review_prompt.txt`.

## Failure modes

### Failure mode 1: Old checkpoints missing api_identifiers
**Detection**: Deserialization error on checkpoint load
**Resolution**: `Field(default_factory=list)` fills with empty list
**Gate**: JSON schema validation (field not in `required`)

### Failure mode 2: Backtick wrapping corrupts product display name
**Detection**: "Aspose.`Cells`" in output
**Resolution**: Protected spans mask display_name occurrences
**Gate**: product_names check

### Failure mode 3: Table content loses backticks after restructuring
**Detection**: JSON-array tables have bare API names after conversion
**Resolution**: Fixed in BT-01 — table validation now runs before backtick pass
**Gate**: Manual inspection of table blocks

## Task-specific review checklist

1. [x] `api_identifiers` field has default factory (backward compat)
2. [x] JSON schema does NOT add field to `required`
3. [x] Private names (`_*`) excluded from collection
4. [x] Identifiers capped at 500
5. [x] Case-sensitive matching in `_backtick_api_names()`
6. [x] Protected spans: backticks, markdown links, display_name
7. [x] Longest-first matching prevents partial wrapping
8. [x] Code blocks excluded from backtick wrapping

## Deliverables

1. Modified: 8 files listed in Allowed paths
2. Healing taskcards: `plans/healing/BT-00` through `BT-07`
3. Unit tests: `TestBacktickApiNames` (13 tests), `TestCompileApiPatternCache` (2),
   `TestTableBlockBacktickOrdering` (2), `TestExtractApiSurfaceIdentifiers` (6)

## Acceptance checks

1. [x] All existing tests pass: 1949 passed
2. [x] `_backtick_api_names()` wraps API names correctly (13 unit tests)
3. [x] Table ordering bug fixed (BT-01, 2 regression tests)
4. [x] Regex pattern cached (BT-02, 2 cache tests)
5. [x] Old checkpoints deserialize with empty api_identifiers

## Self-review

### Verification results
- [x] Tests: 1949/1949 PASS
- [x] Validation: full pytest suite PASS
- [x] Evidence captured: plans/healing/BT-00-backtick-healing-gap-index.md

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

**Expected results**:
- All tests pass (1949+)
- No regressions in existing section validator tests

## Integration boundary proven

**Upstream**: Understanding worker produces `ApiSurface.api_identifiers`
**Downstream**: Generate worker consumes identifiers for backtick wrapping
**Contract**: `api_identifiers: list[str]` — optional, defaults to empty list,
schema allows absence for backward compat
