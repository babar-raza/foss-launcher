---
id: TC-3802
title: "Post-LLM Table Validation + HTML Sanitization + Fallback Tables"
status: Done
priority: High
owner: agent
updated: "2026-03-07"
tags: [generate, validation, fallback, table]
depends_on: [TC-3801]
allowed_paths:
  - plans/taskcards/TC-3802_table_validation_fallback.md
  - src/launcher/workers/generate/section_validator.py
  - src/launcher/workers/generate/fallback.py
  - src/launcher/shared/ir_renderer.py
evidence_required:
  - reports/TC-3802/evidence.md
---

# Taskcard TC-3802 — Post-LLM Table Validation + HTML Sanitization + Fallback Tables

## Objective

Catch and repair malformed table content (JSON arrays instead of pipe-delimited markdown), sanitize HTML anchor tags to markdown links, and provide deterministic table fallback for reference page sections.

## Required spec references

- `specs/content_model_pageir.md` (Section: table block — content must be pipe-delimited markdown, emitted verbatim)
- `specs/worker_generate.md` (Section: sandwich model — post-LLM validation layer)

## Scope

### In scope
- Add `_validate_table_content()` to convert JSON arrays to markdown tables
- Add `_sanitize_html_links()` to convert `<a href>` to `[text](url)`
- Wire both into `_validate_block()` in `section_validator.py`
- Add table generation to `render_section_deterministic()` in `fallback.py`
- Add safety guard in `ir_renderer.py` for table blocks without pipe characters

### Out of scope
- Prompt changes (TC-3801)
- Evaluation gate (TC-3803)
- Full HTML sanitization beyond anchor tags

## Inputs

- `section_validator.py` — current validator (285 lines)
- `fallback.py` — current deterministic fallback (155 lines)
- `ir_renderer.py` — current renderer (70 lines)

## Outputs

- Modified `section_validator.py` with table validation + HTML sanitization
- Modified `fallback.py` with table block generation for tabular sections
- Modified `ir_renderer.py` with table safety guard

## Allowed paths

- plans/taskcards/TC-3802_table_validation_fallback.md
- src/launcher/workers/generate/section_validator.py
- src/launcher/workers/generate/fallback.py
- src/launcher/shared/ir_renderer.py

### Allowed paths rationale
- `section_validator.py`: Post-LLM validation is the sandwich model's engineering layer
- `fallback.py`: Deterministic fallback must produce valid table blocks for tabular sections
- `ir_renderer.py`: Last defense against malformed table content reaching markdown output

## Implementation steps

### Step 1: Add _validate_table_content() in section_validator.py

Add after `_strip_claim_citations()` (line 105):

```python
def _validate_table_content(content: str) -> str:
    """Validate and repair table block content.

    If content is already pipe-delimited markdown, return as-is.
    If content is a JSON/Python array of dicts, convert to markdown table.
    Otherwise, return content wrapped in a minimal table.
    """
    stripped = content.strip()
    if not stripped:
        return content

    # Already valid pipe-delimited table
    if re.search(r"^\|.+\|$", stripped, re.MULTILINE):
        return content

    # Try to parse as JSON array of dicts
    if stripped.startswith("["):
        try:
            # Handle Python-style single quotes by replacing with double
            json_str = stripped.replace("'", '"')
            rows = json.loads(json_str)
            if isinstance(rows, list) and rows and isinstance(rows[0], dict):
                return _json_array_to_markdown_table(rows)
        except (json.JSONDecodeError, ValueError):
            pass

    # Last resort: wrap in single-column table
    logger.warning("Table content is not pipe-delimited markdown; wrapping as single-column")
    return f"| Content |\n|---|\n| {stripped} |"


def _json_array_to_markdown_table(rows: list[dict]) -> str:
    """Convert a list of dicts to a pipe-delimited markdown table."""
    if not rows:
        return ""
    headers = list(rows[0].keys())
    header_line = "| " + " | ".join(headers) + " |"
    separator = "| " + " | ".join("---" for _ in headers) + " |"
    data_lines = []
    for row in rows:
        cells = [str(row.get(h, "")).replace("|", "\\|").replace("\n", " ") for h in headers]
        data_lines.append("| " + " | ".join(cells) + " |")
    return "\n".join([header_line, separator] + data_lines)
```

### Step 2: Add _sanitize_html_links() in section_validator.py

Add after `_validate_table_content()`:

```python
def _sanitize_html_links(content: str) -> str:
    """Convert HTML anchor tags to markdown links."""
    return re.sub(
        r'<a\s+href=["\']([^"\']+)["\'](?:\s[^>]*)?>(.*?)</a>',
        r'[\2](\1)',
        content,
        flags=re.IGNORECASE,
    )
```

### Step 3: Wire into _validate_block()

In `_validate_block()`, after line 150 (`content = str(content) if content is not None else ""`):

```python
    # Sanitize HTML links in all non-code blocks
    if block_type != BlockType.code:
        content = _sanitize_html_links(content)

    # Validate table content format
    if block_type == BlockType.table:
        content = _validate_table_content(content)
```

### Step 4: Add table generation to fallback.py

Add constant and helper after imports (line 12):

```python
_TABULAR_HEADINGS: set[str] = frozenset({
    "constructors", "constructor", "properties", "methods",
    "key members", "api summary", "error messages", "supported formats",
})


def _claims_to_table(claims: list[Claim]) -> str:
    """Build a 2-column markdown table from claims."""
    header = "| Item | Description |"
    separator = "| --- | --- |"
    rows = []
    for c in claims:
        # Split claim text at first period for name vs description
        parts = c.text.split(". ", 1)
        name = parts[0].strip()
        desc = parts[1].strip() if len(parts) > 1 else ""
        # Escape pipes
        name = name.replace("|", "\\|")
        desc = desc.replace("|", "\\|")
        rows.append(f"| {name} | {desc} |")
    return "\n".join([header, separator] + rows)
```

In `render_section_deterministic()`, after the opening paragraph block (line 52), before the claims-as-list block (line 55), add:

```python
    # For tabular sections, render claims as a table instead of a list
    if section.heading.lower() in _TABULAR_HEADINGS and claims:
        table_md = _claims_to_table(claims)
        blocks.append(
            BlockIR(
                type=BlockType.table,
                content=table_md,
                claim_ids=[c.claim_id for c in claims],
            )
        )
    elif claims:
        # existing list fallback
        items = [c.text for c in claims]
        blocks.append(...)
```

### Step 5: Add table safety in ir_renderer.py

In `_render_block()`, replace lines 61-63:

```python
    if bt == BlockType.table:
        if block.content and "|" not in block.content:
            logger.warning("Table block content has no pipe characters; wrapping")
            return f"| Content |\n|---|\n| {block.content} |"
        return block.content
```

## Failure modes

### Failure mode 1: JSON-to-table conversion produces garbled output

**Detection**: Rendered markdown has misaligned columns or escaped characters
**Resolution**: The conversion escapes pipe characters and replaces newlines. Test with actual LLM output samples.
**Gate**: gate_reference_completeness (TC-3803)

### Failure mode 2: HTML sanitization strips legitimate code content

**Detection**: Code blocks lose `<a>` tags that were intended as code
**Resolution**: Sanitization is guarded by `block_type != BlockType.code` — code blocks are never touched.
**Gate**: check_code gate

### Failure mode 3: Fallback table has empty cells

**Detection**: Claim text doesn't contain a period, so the split produces empty description
**Resolution**: When no period found, use full claim text as Item and leave Description empty. This is acceptable for fallback quality.
**Gate**: Content density gate

## Task-specific review checklist

1. [ ] `_validate_table_content()` handles empty content gracefully
2. [ ] `_json_array_to_markdown_table()` escapes pipe characters in cell content
3. [ ] `_sanitize_html_links()` only runs on non-code blocks
4. [ ] Fallback table generation only triggers for `_TABULAR_HEADINGS` sections
5. [ ] `ir_renderer.py` safety guard logs a warning (not silent)
6. [ ] No platform-specific logic in any function

## Deliverables

1. Modified `src/launcher/workers/generate/section_validator.py`
2. Modified `src/launcher/workers/generate/fallback.py`
3. Modified `src/launcher/shared/ir_renderer.py`
4. Evidence bundle at `reports/TC-3802/evidence.md`

## Acceptance checks

1. [ ] `_validate_table_content("[{'Name': 'x'}]")` returns `"| Name |\n| --- |\n| x |"`
2. [ ] `_sanitize_html_links('<a href="url">text</a>')` returns `"[text](url)"`
3. [ ] Fallback for "Properties" section produces a table block (not a list)
4. [ ] `ir_renderer.py` wraps tableless content in a safety table
5. [ ] All existing tests pass: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x`

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: table conversion PASS
- [ ] Evidence captured: reports/TC-3802/

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_generate.py tests/unit/shared/test_ir_renderer.py -v
```

**Expected results**:
- All tests pass
- Table blocks with JSON array content are converted to pipe-delimited markdown
- HTML links are converted to markdown links

## Integration boundary proven

**Upstream**: LLM raw response → `parse_and_validate_blocks()` (sandwich post-LLM layer)
**Downstream**: `ir_renderer.py` → markdown output (table content emitted verbatim)
**Contract**: `BlockIR.type == "table"` always has pipe-delimited markdown content after validation
