# GEN-001 Plan: Structural Fix for Generate Worker Code Quality

## Problem

The generate worker has a 14% A+B quality rate (target 70%). Root cause: the LLM
generates code blocks using Aspose commercial SDK patterns (`ObjLoadOptions`,
`Scene.open()`, etc.) that don't exist in the FOSS API surface. Training priors
override explicit prompt guards. Healing iterations HG-11 to HG-21 tried
prompt-level prohibition and plateaued at 27%. HG-16 tried post-generation
identifier repair and briefly reached 41% but dropped to 22% due to false
positives from scanning code comments.

## Structural Fix (Phase 1)

Never generate code blocks in the LLM call. Code comes from pre-selected
snippets injected deterministically.

### Sub-change 1: worker.py — Snippet pre-selection (Phase A) + injection (Phase C)

- Added `_select_snippets_for_section(sec_claim_ids, all_snippets, max_snippets=2)`
  - Scores snippets by overlap with section claim IDs
  - Requires `syntax_valid != False`
  - Returns top 2 snippets sorted by overlap desc, then index for determinism

- Phase A (before LLM call): Pre-select snippets; set `_prose_only_mode = True`
  when snippets are available

- Pass `prose_only=_prose_only_mode` to `build_section_prompt`

- Suppress `_needs_code_retry` when in prose_only mode (code injected in Phase C,
  not from LLM)

- Phase C (after LLM prose accepted): Inject selected snippets as BlockIR code
  blocks with source traceability comment. Insert after first claim-matching
  paragraph, or at end of section. Skip when fallback renderer was used (it
  already injects snippets).

### Sub-change 2: section_prompt.py — Prose-only prompt mode

- Added `prose_only: bool = False` parameter to `build_section_prompt`

- When `prose_only=True`:
  - Relabels "CODE EXAMPLES (use verbatim, do not modify):" as
    "CODE CONTEXT (for your prose to explain — do NOT reproduce these as code
    blocks in your output):"
  - Appends OUTPUT FORMAT OVERRIDE block instructing LLM to output only
    paragraph/list/heading/table blocks

- Backwards compatible: `prose_only=False` default preserves existing behaviour

### Sub-change 3: section_validator.py + _identifier_repair.py — Code block rejection + identifier scan narrowing

**section_validator.py** (`parse_and_validate_blocks`):
- Before calling `_validate_block`, detect and reject code-type raw blocks from
  LLM output (both explicit `"type": "code"` and TC-4228 inferred code blocks)
- After `_validate_block`, add secondary guard to reject any inferred-code blocks
- Log WARNING with section heading for each rejected block; log INFO with count

**_identifier_repair.py** (`_repair_code_segment`):
- Strip `#` comment content before scanning code lines for hallucinated tokens
- Lines that are entirely comments are passed through unchanged
- Prevents false positives from scanning comment text like "# Load the Scene"
  (this was HG-16's false-positive source)

## Fallback Behaviour

When `_selected_snippets` is empty (no syntax-valid snippets overlap the section
claims), `_prose_only_mode = False` and the existing LLM path runs unchanged,
including code generation. This preserves backwards compatibility for sections
with no snippet evidence.
