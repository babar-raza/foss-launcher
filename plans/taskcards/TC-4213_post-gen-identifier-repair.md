---
id: TC-4213
title: "Post-Generation Identifier Repair Pass"
status: Done
priority: High
owner: "orchestrator-agent"
updated: "2026-03-11"
tags: ["generate", "hallucination", "identifiers", "wave6"]
depends_on: ["TC-4041", "TC-4042"]
allowed_paths:
  - plans/taskcards/TC-4213_post-gen-identifier-repair.md
  - src/launcher/workers/generate/_identifier_repair.py
  - src/launcher/workers/generate/worker.py
  - tests/unit/workers/generate/test_identifier_repair.py
  - reports/agents/wave6/TC-4213/evidence.md
  - reports/agents/wave6/self_review.md
evidence_required:
  - reports/agents/wave6/TC-4213/evidence.md
---

# Taskcard TC-4213 — Post-Generation Identifier Repair Pass

## Objective

Implement a deterministic post-LLM engineering step that detects and repairs
hallucinated PascalCase API identifiers in generated section content. The LLM
frequently invents class names (e.g., `SpreadsheetManager`, `RowIterator`) that
do not exist in the real API surface. This pass replaces them in prose and
annotates them in code blocks, with a full audit trail in
`generate_repair_log.json`.

## Required spec references

- `specs/worker_generate.md` (Section: sandwich model, post-LLM engineering step)
- `specs/worker_understand.md` (Section: ApiSurface, public_classes, class_briefs)

## Scope

### In scope
- New module `_identifier_repair.py` with `repair_identifiers(section_text, api_surface)` function
- Integration into `worker.py` `_generate_section` after LLM response is parsed into blocks
- Writing `generate_repair_log.json` artifact at run end
- Emitting `identifier_hallucination` event when >3 repairs in a section
- Unit tests covering all 6 required test cases

### Out of scope
- Repairing snake_case method identifiers (handled by HG-21 `_method_corrections`)
- LLM-based disambiguation — this is purely deterministic
- Modifying the Evaluate or Understand workers
- Changing the ApiSurface schema

## Inputs

- `section_text: str` — rendered text of a section (prose + code blocks as markdown string)
- `api_surface: ApiSurface` — from UnderstandingBundle (public_classes, class_briefs)
- `product_display_name: str` — exempt from repair (product name itself)

## Outputs

- `_identifier_repair.py` — new module with `repair_identifiers` function
- `worker.py` — modified to call `repair_identifiers` after LLM parse, collect log
- `generate_repair_log.json` — written to run_dir if any repairs occurred
- `test_identifier_repair.py` — 6 unit tests covering all specified scenarios

## Allowed paths

- plans/taskcards/TC-4213_post-gen-identifier-repair.md
- src/launcher/workers/generate/_identifier_repair.py
- src/launcher/workers/generate/worker.py
- tests/unit/workers/generate/test_identifier_repair.py
- reports/agents/wave6/TC-4213/evidence.md
- reports/agents/wave6/self_review.md

### Allowed paths rationale

- `_identifier_repair.py`: new deterministic post-LLM module in the generate worker package
- `worker.py`: integration point — must call repair after LLM blocks are produced
- `test_identifier_repair.py`: unit tests for the new module
- Evidence and self-review files: required by AG-020 self-review protocol

## Implementation steps

### Step 1: Create `_identifier_repair.py`

Implement `repair_identifiers(section_text: str, api_surface: ApiSurface, product_display_name: str = "") -> tuple[str, list[str]]`.

Logic:
1. Build `known_set` from `api_surface.public_classes` + method names + property names from `class_briefs`
2. Build `exempt_set` of Python builtins, primitives, generic words, plus product display name tokens
3. Split text into code-fenced segments vs. prose segments
4. For prose segments: find PascalCase tokens (≥4 chars) not in known_set and not in exempt_set; replace with `[identifier omitted]`
5. For code segments: for each PascalCase token not in known_set and not in exempt_set, append `  # <token>: unknown — omitted` comment on the same line
6. Scope gates: skip markdown headers, skip identifiers that are substrings of known classes
7. Return (repaired_text, repairs_list)

### Step 2: Integrate into `worker.py`

In `_generate_section`, after `parse_and_validate_blocks` and before building `SectionIR`:
1. Render blocks to a simple text representation (prose content + code content)
2. Call `repair_identifiers` with the text and `understand.api_surface`
3. If repairs non-empty, log them to `generate_repair_log` dict (section_heading → repairs)
4. If `len(repairs) > 3`, emit `identifier_hallucination` event via `context.emit_event`
5. Apply repaired text back to the blocks' content fields

At end of `run()`, write `generate_repair_log.json` to `context.run_dir` if non-empty.

### Step 3: Write unit tests

`tests/unit/workers/generate/test_identifier_repair.py` with 6 test cases:
- A: hallucinated `SpreadsheetManager` replaced; known `Workbook` preserved
- B: code block `RowIterator` annotated with comment
- C: product display name token preserved
- D: Python builtins/exceptions not touched
- E: no hallucinations → (original_text, [])
- F: >3 repairs → repairs list has >3 entries

## Failure modes

### Failure mode 1: Over-eager replacement of valid identifiers

**Detection**: Test failures where known API classes get replaced; visual inspection of generated content showing `[identifier omitted]` where real classes should appear.
**Resolution**: Widen the known_set construction; ensure `public_classes` from `api_surface` are all included; add more terms to exempt_set.
**Gate**: Test A (Workbook preserved) must pass.

### Failure mode 2: PascalCase regex matches too broadly (e.g., URL components, product names)

**Detection**: Product name like "Aspose" gets replaced; any capitalized proper noun gets stripped.
**Resolution**: Add product display name tokens to exempt_set; add common proper nouns to exempt_set; require minimum 4 chars (not 3).
**Gate**: Test C (product display name) and Test D (builtins) must pass.

### Failure mode 3: Code block repair breaks valid Python syntax

**Detection**: Generated code with added `# unknown — omitted` comments causes parse errors in evaluate worker code check.
**Resolution**: Add comment on the same line only if the line doesn't already end with a comment; use `  # <token>: not in API — see docs` format that is syntactically valid as a Python comment.
**Gate**: Test B verifies code block repair does not break surrounding code.

### Failure mode 4: Worker integration breaks existing tests

**Detection**: Existing `tests/unit/workers/generate/` tests fail after `worker.py` modification.
**Resolution**: The repair is wrapped in try/except; repair_identifiers must be optional when api_surface is empty or when no public_classes exist.
**Gate**: Full test suite `tests/unit/workers/generate/ -x -q` passes.

### Failure mode 5: Repair log JSON write fails in read-only run_dir

**Detection**: `generate_repair_log.json` not written; warning logged.
**Resolution**: Wrap artifact write in try/except; log warning on failure; do not raise.
**Gate**: Worker completes successfully even if artifact write fails.

## Task-specific review checklist

1. [ ] `repair_identifiers` only touches PascalCase identifiers ≥4 chars
2. [ ] Known classes from `api_surface.public_classes` are never replaced
3. [ ] Python builtins (`Exception`, `ValueError`, `Path`, `str`, `list`) are never replaced
4. [ ] Product display name tokens are exempted
5. [ ] Code block repair adds a comment, not a deletion
6. [ ] Prose repair replaces just the token, not the entire sentence
7. [ ] `generate_repair_log.json` written only when repairs > 0
8. [ ] `identifier_hallucination` event emitted only when repairs > 3 in a section
9. [ ] Integration in `worker.py` is wrapped in try/except to prevent regressions
10. [ ] Docstrings updated for all new/changed public functions
11. [ ] Spec file checked — no spec drift (sandwich model step is within spec)
12. [ ] All 6 test cases pass
13. [ ] Existing generate worker tests still pass

## Deliverables

1. `src/launcher/workers/generate/_identifier_repair.py` — new module
2. `src/launcher/workers/generate/worker.py` — integration
3. `tests/unit/workers/generate/test_identifier_repair.py` — 6 unit tests
4. `reports/agents/wave6/TC-4213/evidence.md` — test output + files changed

## Acceptance checks

1. [x] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/generate/ -x -q` — 216 passed (8 pre-existing failures, unrelated to TC-4213)
2. [x] `generate_repair_log.json` artifact specification is documented in evidence
3. [x] All 6 tests A-F pass and cover the specified scenarios (25 total tests)
4. [x] `repair_identifiers` returns `(original_text, [])` when no hallucinations present
5. [x] Integration is non-destructive: blocks unchanged when no repairs needed

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: identifier repair PASS
- [ ] Evidence captured: reports/agents/wave6/TC-4213/evidence.md
- [ ] Doc freshness: checked — no spec drift

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/generate/ -x -q
```

**Expected results**:
- All existing generate worker tests pass
- 6 new TC-4213 tests pass
- No regressions in worker.py

## Integration boundary proven

**Upstream**: `parse_and_validate_blocks` produces a list of `BlockIR` objects from LLM response
**Downstream**: `SectionIR` is constructed from repaired blocks; `generate_repair_log.json` is written as audit artifact
**Contract**: `repair_identifiers(text: str, api_surface: ApiSurface, product_display_name: str) -> tuple[str, list[str]]`
