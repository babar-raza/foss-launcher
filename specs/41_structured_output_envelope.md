# Spec 41: Structured Output Envelope

**Status**: Binding
**Version**: 1.0
**TC-Ref**: TC-2376
**Effective**: 2026-02-20

---

## Overview

W5 SectionWriter uses JSON-structured output for draft generation, eliminating ~35
post-processing sanitizers. Instead of one large LLM call per page that returns raw
markdown (which then requires extensive sanitization), the orchestrator makes one small
LLM call per section, requesting a structured JSON envelope. A deterministic renderer
converts the envelope to valid markdown.

---

## JSON Schema

Each LLM call for a single section returns one section object:

```json
{
  "heading": "Getting Started",
  "level": 2,
  "body": "prose text with <!-- claim: id --> markers",
  "claim_ids_used": ["claim-abc123"],
  "snippet_ids_used": ["snip-001"],
  "code_blocks": [
    {
      "language": "python",
      "code": "...",
      "caption": "..."
    }
  ]
}
```

The assembled page is a `sections` wrapper:

```json
{
  "sections": [
    { ... section objects ... }
  ]
}
```

### Field Definitions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `heading` | string | yes | Section heading text (no `#` prefix) |
| `level` | integer | yes | Heading level (2–4) |
| `body` | string | yes | Prose markdown with `<!-- claim: id -->` markers |
| `claim_ids_used` | list[string] | no | Claim IDs referenced in this section |
| `snippet_ids_used` | list[string] | no | Snippet IDs used for code blocks |
| `code_blocks` | list[object] | no | Structured code blocks (see below) |

**code_block object**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `language` | string | yes | Fence language identifier (e.g. `python`, `csharp`) |
| `code` | string | yes | Source code content |
| `caption` | string | no | Optional italicized caption below the code block |

---

## Renderer Contract

`render_envelope(envelope: dict) -> str` converts the JSON dict to valid markdown.

Implemented in `src/launch/workers/w5_section_writer/renderer.py`:

- `json_to_markdown(json_output: dict, page: dict) -> str`
  - Iterates `json_output["sections"]`
  - For each section: emits heading at given level, body text, then fenced code blocks
  - Returns a clean markdown string (stripped)

- `parse_json_draft(raw_content: str) -> Optional[dict]`
  - Strips `\`\`\`json` or bare `\`\`\`` fences if present
  - Calls `json.loads()` on extracted content
  - Returns `None` on parse failure (does **not** raise)

---

## Fallback Policy

If the LLM returns non-JSON:

1. Log `W5_ENVELOPE_PARSE_FAILURE` at WARNING level.
2. Use the raw text string as the section `body` with empty `code_blocks`.
3. Continue assembling remaining sections (non-fatal per-section failure).
4. If **all** sections fail, fall back to `_deterministic_fallback()`.

---

## Feature Flags

Both flags are read from `run_config` (the dict passed to `MultiPassOrchestrator`):

| Flag | Default | Description |
|------|---------|-------------|
| `use_json_draft` | `true` | Request JSON output from draft LLM calls |
| `per_section_draft` | `true` | Make one LLM call per section (not one per page) |

When `per_section_draft` is `false`, the orchestrator calls the legacy
`_generate_draft_legacy()` single-call path unchanged. This preserves full
backwards compatibility for existing pilot configs.

---

## LLM Call Parameters

Each per-section call uses:

```python
llm_client.chat_completion(
    messages=[system_prompt_message, user_section_message],
    call_id=f"mp_section_{slug}_{index}",
    temperature=0.1,       # low for determinism
    max_tokens=1500,       # sufficient for one section
    response_format={"type": "json_object"},  # JSON mode if supported
)
```

---

## Dependencies

- **TC-2378**: `_FenceState` class in `content_sanitizer.py` — used by renderer fallback
- **TC-2379**: `get_context_for_role()` dispatch in `content_generators.py` — per-section claim routing

---

## Acceptance Criteria

- `renderer.py` passes all 7 unit tests in `test_tc_440_section_writer.py`
- `_generate_draft()` makes N LLM calls for N sections (verified by mock test)
- Legacy path (`per_section_draft: false`) passes existing multi-pass tests unchanged
- `MAX_PROMPT_CHARS` truncation block removed from `_call_llm_for_content()` in `worker.py`
