---
id: TC-3890
title: "Fix Linker Dict-Coercion Bug in _parse_anchor_response"
status: Done
priority: High
owner: "agent"
updated: "2026-03-09"
tags: [linker, bug, anchor-text, rendering]
depends_on: []
allowed_paths:
  - src/launcher/shared/linker.py
  - tests/test_linker.py
---

## Objective

Fix `_parse_anchor_response` in `linker.py` so that when the LLM returns a JSON array
of dicts (e.g., `[{"type": "anchor", "text": "FAQ"}]`) instead of plain strings, the
dict's text value is extracted properly instead of being stringified as a Python dict
literal which then renders as broken link text in generated pages.

Also strengthen `_sanitize_anchor_text` to reject dict-literal strings as a safety net.

## Root Cause

`_parse_anchor_response` line 428: `[str(x) for x in parsed[:expected_count]]`
When `x` is a dict, `str(dict)` → `"{'type': 'anchor', 'text': 'FAQ'}"` as anchor text.

`_sanitize_anchor_text` line 434: banned character set `[\[\]()#*`]` does not include
`{`, `}`, `'` so dict literals pass sanitization unchanged.

## Scope

In: `src/launcher/shared/linker.py`, `tests/test_linker.py`
Out: everything else

## Implementation Steps

1. `_parse_anchor_response`: replace `str(x)` with dict-aware extraction
2. `_sanitize_anchor_text`: add early-exit for dict/list-literal patterns
3. Add tests

## Acceptance Checks

- [ ] `_parse_anchor_response('[{"type":"anchor","text":"FAQ"}]', 1)` → `["FAQ"]`
- [ ] `_parse_anchor_response('["FAQ"]', 1)` → `["FAQ"]` (existing behavior preserved)
- [ ] `_sanitize_anchor_text("{'type': 'anchor', 'text': 'FAQ'}", "FAQ")` → `"FAQ"`
- [ ] All existing linker tests pass
- [ ] New TC-3890 tests pass
