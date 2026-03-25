# TC-4308 Changes

## Files Modified

### src/launcher/workers/generate/section_prompt.py

**Change 1** (after `api_surface_block` in `build_section_prompt`):
- Defensive check for raw dict repr in plain text (outside code fences)
- Logs warning if `[{'` or `{'Signature'` or `[{'name'` detected

**Change 2** (after `api_surface_block` in `build_page_prompt`):
- Same defensive check

**Change 3** (STRICT RULES block in `build_page_prompt`):
- Added KEYWORD DENSITY mandatory rule
- Limits product name to 1 per 300 words, suggests substitutes

### src/launcher/prompts/section_writer.txt

**Change 4** (STRICT RULES section):
- Added KEYWORD DENSITY mandatory rule inline after existing keyword-stuffing rule

### tests/unit/workers/generate/test_section_validator.py

Added `TestTC4308ClassBriefsPromptSerialization` class with 3 tests:
- `test_typed_methods_formatted_as_readable_signatures`
- `test_no_dict_repr_with_parameters`
- `test_keyword_density_rule_in_page_prompt`
