# GEN-001 Changes

## File 1: src/launcher/workers/generate/worker.py

### Added: `_select_snippets_for_section` function (~line 2490)

Lines added at approximately line 2490 (before `_validate_identifiers`):
- New function `_select_snippets_for_section(sec_claim_ids, all_snippets, max_snippets=2)`
- Scores snippets by overlap count with `sec_claim_ids`
- Excludes snippets with `syntax_valid == False`
- Returns `list[tuple[int, Snippet]]` sorted by (-overlap, original_index) for determinism
- Returns empty list when no overlapping snippets found

### Added: Phase A pre-selection in `_generate_section` (~line 1435)

After `sec_snippets = ...` at the top of `_generate_section`:
- Call `_select_snippets_for_section(sec_claim_ids, page_snippets, max_snippets=2)`
- Set `_prose_only_mode = bool(_selected_snippets)`
- Log DEBUG when snippets are pre-selected

### Changed: `build_section_prompt` call (~line 1516)

Added `prose_only=_prose_only_mode` to the `build_section_prompt(...)` call.

### Changed: `_needs_code_retry` check (~line 1594)

Changed condition from:
```python
if page_plan.page_role in _CODE_REQUIRED_ROLES:
```
to:
```python
if page_plan.page_role in _CODE_REQUIRED_ROLES and not _prose_only_mode:
```
This prevents infinite code-retry loops in prose_only mode where the LLM is
intentionally forbidden from generating code blocks.

### Added: Phase C snippet injection (~line 1680)

After the `if section_ir is None:` fallback block, before golden enforcement:
- Guard: `if _selected_snippets and _prose_only_mode and not _fb:`
- Build `BlockIR(type=BlockType.code, ...)` for each selected snippet
- Add `# source: snippet_{idx}` traceability comment to snippet code
- Filter `claim_ids` to section-assigned claims only (TC-4286 pattern)
- Insert code blocks after first claim-matching paragraph, or at end of section
- Log INFO with count of injected blocks

## File 2: src/launcher/workers/generate/section_prompt.py

### Changed: `build_section_prompt` signature (~line 761)

Added parameter:
```python
prose_only: bool = False,  # GEN-001: When True, instruct LLM to produce prose blocks only (no code)
```
Default `False` preserves existing behaviour for all callers that don't pass `prose_only`.

### Added: Prose-only post-processing block (~line 1022)

After `result = _canonical_reminder + result` and before TC-GLD-011 word count injection:
- When `prose_only=True`:
  - Replace "CODE EXAMPLES (use verbatim, do not modify):" label with
    "CODE CONTEXT (for your prose to explain — do NOT reproduce these as code blocks in your output):"
  - Append "OUTPUT FORMAT OVERRIDE (GEN-001 prose-only mode):" block forbidding
    code blocks and explaining code will be injected separately

## File 3: src/launcher/workers/generate/section_validator.py

### Changed: `parse_and_validate_blocks` — code block rejection (~line 128)

Before calling `_validate_block` for each raw block:
- Detect code-type blocks: explicit `"type": "code"`, blocks with `"language"` key
  (TC-4228 inference trigger), or blocks with triple-backtick content
- Log WARNING for each rejected block with section heading
- Skip `_validate_block` call for these blocks (count them in `_rejected_code_count`)
- After `_validate_block`: secondary guard rejecting any block where the
  inferred type resolved to `BlockType.code`
- Log INFO with total count when any rejections occurred

## File 4: src/launcher/workers/generate/_identifier_repair.py

### Changed: `_repair_code_segment` — comment-line skip (~line 471)

In the main line-iteration loop of `_repair_code_segment`:
After the fence-delimiter pass-through:
- Extract code portion: `_code_part_for_scan = stripped.split("#")[0] if "#" in stripped else stripped`
- If the code portion is empty (line is entirely a comment): append line unchanged
  and `continue` (skip identifier scanning entirely for that line)
- Change `_PASCAL_RE.finditer(stripped)` to `_PASCAL_RE.finditer(_code_part_for_scan)`
  so comment text is never scanned for PascalCase identifiers

This narrows the identifier scan to actual code tokens only, not comment text.
Prevents false positives like "# Load the Scene" flagging "Scene" as a
hallucinated identifier (HG-16's false-positive source).
