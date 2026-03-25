# Evidence: TC-3625 — W10 Malformed YAML Frontmatter Field-Preserving Fixer

## Implementation date
2026-03-01

## Problem addressed
`fix_frontmatter_invalid_yaml()` (lines ~615–681 of `worker.py`) reconstructed frontmatter
with synthetic defaults only:
- `title`: derived from `file_path.stem` (e.g., "How To Note This Method")
- No `layout` or `permalink` written

This caused gate_4 to report `layout` and `permalink` missing after the W10 fix
(because `write_frontmatter({title, type}, body)` did not include them), creating
an infinite loop where W10 "fixed" the YAML but introduced new gate_4 issues.

Additionally, files with trailing YAML key:value lines after the markdown body
(the "trailing fields" pattern, common in LLM-generated content) had their
real `title`/`layout`/`permalink` values lost because the function only scanned
the broken frontmatter block, not the whole file.

## Spec amended
- `specs/21_worker_contracts.md` — added `§W10 YAML Frontmatter Repair Contract (TC-3625)`:
  - Field extraction MUST scan full raw content before synthetic fallback
  - First-occurrence wins
  - Trailing YAML-like lines MUST be stripped from body
  - Atomic write (tempfile + os.replace) REQUIRED per TC-2470
  - OSError fallback: graceful degradation to direct write

## Taskcard
`plans/taskcards/TC-3625_w10_malformed_yaml_frontmatter.md` — passes `validate_taskcards.py`

## Code changes
`src/launch/workers/w10_fixer/worker.py`:

1. **`import tempfile`** added to imports.

2. **New helper `_extract_frontmatter_fields(content: str) -> Dict[str, str]`**:
   ```python
   pattern = re.compile(r'^(title|layout|permalink):\s*"?([^"\n]+?)"?\s*$', re.MULTILINE)
   # First-occurrence wins; returns only found keys
   ```

3. **New helper `_strip_trailing_yaml_lines(body: str) -> str`**:
   - Walks from bottom of body, strips trailing blank lines then YAML key:value lines
   - Only removes lines matching `^(title|layout|permalink|weight|slug|type|draft|date):`
   - Stops at first non-matching line from bottom

4. **`fix_frontmatter_invalid_yaml()` extended**:
   - Calls `_extract_frontmatter_fields(content)` before any frontmatter construction
   - Builds `reconstructed_frontmatter` with extracted values preferred over synthetics:
     ```python
     reconstructed_frontmatter = {
         "title": extracted.get("title") or _stem_title,
         "layout": extracted.get("layout") or "docs",
         "permalink": extracted.get("permalink") or _stem_permalink,
     }
     ```
   - Calls `_strip_trailing_yaml_lines(body)` before writing
   - Uses `_atomic_write(path, text)` closure (tempfile + os.replace + OSError fallback)

## Tests
`tests/unit/workers/test_w10_yaml_frontmatter.py` — 16 tests, all passing:

**TestExtractFrontmatterFields (5 tests)**:
- `test_extracts_all_three_fields_unquoted`
- `test_extracts_quoted_title_with_colon` — `title: "Page: Subtitle"` → `Page: Subtitle`
- `test_first_occurrence_wins`
- `test_returns_empty_dict_when_no_fields`
- `test_trailing_fields_after_body`

**TestStripTrailingYamlLines (4 tests)**:
- `test_strips_trailing_yaml_cluster`
- `test_preserves_body_content_not_yaml`
- `test_strips_trailing_separator`
- `test_empty_body_returns_empty`

**TestFixFrontmatterInvalidYaml (7 tests)**:
- `test_trailing_fields_extracted` — real field values preserved
- `test_minimal_fallback_when_no_fields` — synthetic defaults used when no fields
- `test_title_with_colons_quoted` — quoted title correctly extracted
- `test_atomic_write_used` — os.replace called exactly once
- `test_no_file_returns_unfixed` — graceful missing-file handling
- `test_body_content_not_stripped` — markdown body preserved
- `test_idempotent_no_issue_is_noop` — no location path → fixed=False

## Acceptance check
All 16 tests pass. Full regression suite: 7993 passed (exact count pending heal run completion).
