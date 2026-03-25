# Evidence: TC-2376 — W5 Structured Output Envelope (JSON draft + per-section calls)

**Agent**: W5_AGENT
**Date**: 2026-02-20
**Status**: Done
**Spec**: specs/41_structured_output_envelope.md

---

## Summary

Implemented TC-2376 in full: W5 draft pass now makes one LLM call per section requesting
structured JSON output, and a deterministic renderer converts the JSON to valid markdown.
The old single-shot full-page draft call is preserved as `_generate_draft_legacy()` behind
a `per_section_draft: False` feature flag for backwards compatibility.

---

## Files Changed

### New files

| File | Description |
|------|-------------|
| `specs/41_structured_output_envelope.md` | Governance spec (written FIRST per ruleset) |
| `src/launch/workers/w5_section_writer/renderer.py` | `json_to_markdown()` + `parse_json_draft()` |
| `reports/agents/W5_AGENT/TC-2376/evidence.md` | This file |
| `reports/agents/W5_AGENT/TC-2376/self_review.md` | 12D self-review |

### Modified files

| File | Change |
|------|--------|
| `src/launch/workers/w5_section_writer/multi_pass.py` | Feature flags, module-level helpers, new `_generate_draft()`, legacy method renamed |
| `src/launch/workers/w5_section_writer/worker.py` | Removed TC-2311 `MAX_PROMPT_CHARS` truncation block |
| `tests/unit/workers/test_tc_440_section_writer.py` | Added 7 new tests in `TestTC2376StructuredOutputEnvelope` class |
| `tests/unit/workers/test_tc_1780_prompt_multipass.py` | Updated 4 tests to use legacy path (`per_section_draft: False`) so they test the correct original behavior |

---

## Implementation Details

### renderer.py

Pure Python stdlib, no external dependencies.

- `parse_json_draft(raw_content)`: Strips ` ```json ` or bare ` ``` ` fences, then calls
  `json.loads()`. Returns `None` on failure (no raise). Logs `W5_ENVELOPE_PARSE_FAILURE`.
- `json_to_markdown(json_output, page)`: Iterates `sections[]`, emits `#`-level headings,
  body text, and fenced code blocks with optional italicized captions. Returns stripped string.

### multi_pass.py changes

**Imports added** (line 37):
```python
from launch.workers.w5_section_writer.renderer import json_to_markdown, parse_json_draft
```

**Feature flags** (in `__init__()`):
```python
if isinstance(run_config, dict):
    self._use_json_draft = run_config.get("use_json_draft", True)
    self._per_section_draft = run_config.get("per_section_draft", True)
else:
    self._use_json_draft = True
    self._per_section_draft = True
```

**Module-level helpers** (before class definition):
- `_get_section_claims(section_claim_ids, all_page_claims, max_claims=5)` — filters claims by ID set, falls back to first N
- `_get_section_snippets(section_claims, all_snippets, max_snippets=2)` — uses `demo_snippet_ids` from claims, falls back to first N

**New `_generate_draft()`**:
- When `_per_section_draft` is `True` (default): iterates `outline["sections"]`, makes one
  `chat_completion` call per section at temperature 0.1, max_tokens 1500, `response_format={"type": "json_object"}`.
  Parses response with `parse_json_draft()`. Falls back to raw text on parse failure.
  Returns `json_to_markdown({"sections": assembled}, page)`.
- When `_per_section_draft` is `False`: delegates to `_generate_draft_legacy()` (old behavior).
- When outline has no sections: delegates to `_generate_draft_legacy()`.

**`generate()` dict-safety fix**:
```python
if self.run_config is None:
    mp_config = {}
elif isinstance(self.run_config, dict):
    mp_config = self.run_config
else:
    mp_config = self.run_config.get_multi_pass_config()
```

### worker.py change

Removed the `MAX_PROMPT_CHARS = 48000` truncation block (TC-2311) from
`_call_llm_for_content()`. Per-section calls keep prompts small (one section at a time),
making the truncation unnecessary. Replaced with a one-line comment noting the removal.

---

## Test Results

```
4620 passed, 9 skipped, 0 failed, 1 warning in 170.04s
```

New tests (all pass):
- `TestTC2376StructuredOutputEnvelope::test_parse_json_draft_valid`
- `TestTC2376StructuredOutputEnvelope::test_parse_json_draft_fenced`
- `TestTC2376StructuredOutputEnvelope::test_parse_json_draft_invalid`
- `TestTC2376StructuredOutputEnvelope::test_json_to_markdown_sections`
- `TestTC2376StructuredOutputEnvelope::test_json_to_markdown_code_blocks`
- `TestTC2376StructuredOutputEnvelope::test_json_to_markdown_empty`
- `TestTC2376StructuredOutputEnvelope::test_get_section_claims_with_ids`

---

## Acceptance Checks

- [x] `specs/41_structured_output_envelope.md` created with schema and renderer contract
- [x] `renderer.py` created with `json_to_markdown()` and `parse_json_draft()`
- [x] `_generate_draft()` makes one LLM call per section (not one per page) when `per_section_draft: true`
- [x] `use_json_draft: true` in run_config uses JSON mode (passes `response_format={"type": "json_object"}`)
- [x] Legacy path preserved when `per_section_draft: false`
- [x] Prompt truncation block removed from `worker.py`
- [x] All 7 new tests pass; full suite: 4620 passed, 0 failed

---

## Backwards Compatibility

- Existing `MockRunConfig` objects (not dicts) default to `_per_section_draft = True`.
  The 4 legacy multi-pass orchestration tests were updated to use `{"per_section_draft": False}`
  as a plain dict run_config, so they continue to test the old 3-call behavior.
- Production `RunConfig` (dataclass) also defaults to `_per_section_draft = True` since it's
  not a dict. Production callers wishing to disable must pass a dict run_config or extend
  `RunConfig` to support these flags.
- The `_generate_draft_legacy()` method is fully intact and tested via legacy-path tests.
