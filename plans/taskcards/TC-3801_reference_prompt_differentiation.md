---
id: TC-3801
title: "Reference Prompt Differentiation + Table Example"
status: Done
priority: High
owner: agent
updated: "2026-03-07"
tags: [generate, api_reference, prompt]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-3801_reference_prompt_differentiation.md
  - src/launcher/prompts/section_writer.txt
  - src/launcher/workers/generate/section_prompt.py
evidence_required:
  - reports/TC-3801/evidence.md
---

# Taskcard TC-3801 — Reference Prompt Differentiation + Table Example

## Objective

Make the LLM produce structured reference content (tables, signatures) instead of prose for API reference pages by adding a table block example to the prompt OUTPUT FORMAT and injecting role-aware directives for reference page roles.

## Required spec references

- `specs/content_model_pageir.md` (Section: BlockIR table type — content must be pipe-delimited markdown)
- `specs/worker_generate.md` (Section: sandwich model — pre-LLM prompt engineering)
- `specs/templates_rulesets.md` (Section: template variant selection by page_role)

## Scope

### In scope
- Add table block example to OUTPUT FORMAT in `section_writer.txt`
- Add reference-specific preamble injection in `section_prompt.py`
- Override structure directives for reference page roles (overview, remarks, see also)
- Works for all platforms and product families

### Out of scope
- Post-LLM validation of table content (TC-3802)
- Deterministic fallback table generation (TC-3802)
- Evaluation gate for reference completeness (TC-3803)
- ApiSurface model enrichment (separate future work)

## Inputs

- `src/launcher/prompts/section_writer.txt` — current prompt template (49 lines)
- `src/launcher/workers/generate/section_prompt.py` — current prompt builder (500 lines)
- Existing `_STRUCTURE_DIRECTIVES` dict (lines 21-352)

## Outputs

- Modified `section_writer.txt` with table block example in OUTPUT FORMAT
- Modified `section_prompt.py` with reference preamble injection and directive overrides

## Allowed paths

- plans/taskcards/TC-3801_reference_prompt_differentiation.md
- src/launcher/prompts/section_writer.txt
- src/launcher/workers/generate/section_prompt.py

### Allowed paths rationale
- `section_writer.txt`: Needs table block example added to OUTPUT FORMAT section
- `section_prompt.py`: Needs reference-aware prompt building logic

## Implementation steps

### Step 1: Add table block example to OUTPUT FORMAT

In `section_writer.txt`, add a 4th example to the OUTPUT FORMAT section (after line 45, before the closing `]`):

```json
  {"type": "table", "content": "| Name | Type | Description |\n|------|------|-------------|\n| value | str | The cell value |", "claim_ids": ["CLM-001"]}
```

This shows the LLM the exact JSON shape for a table block. The content field is a pipe-delimited markdown table string.

### Step 2: Add reference constants in section_prompt.py

Add after line 14 (imports):

```python
_REFERENCE_ROLES: set[str] = {"api_reference", "reference_object_page"}

_REFERENCE_PREAMBLE: str = (
    "IMPORTANT — This is a REFERENCE page, not a content page.\n"
    "- Lead with structured data (tables, signatures). Limit prose to 1-2 sentences before each table.\n"
    "- For Constructors, Properties, Methods sections: the table IS the primary content.\n"
    "  Do NOT write multi-paragraph descriptions before the table.\n"
    "- Table content MUST be pipe-delimited markdown (| Col1 | Col2 |), "
    "NOT JSON arrays or Python dicts.\n"
    "- Do NOT write marketing language, feature lists, or general product descriptions.\n\n"
)
```

### Step 3: Add reference directive overrides

Add after `_REFERENCE_PREAMBLE`:

```python
_REFERENCE_DIRECTIVE_OVERRIDES: dict[str, str] = {
    "overview": (
        "Write exactly 1-3 sentences stating what this class or module does. "
        "No feature lists, no marketing language, no general product descriptions."
    ),
    "remarks": (
        "Write 1-2 sentences about usage caveats or important notes. "
        "No general library descriptions."
    ),
    "see also": (
        "Produce a list block with 2-5 markdown links. "
        "Do NOT use HTML anchor tags (<a href>). Use markdown [text](url) syntax only."
    ),
}
```

### Step 4: Modify _get_structure_directive() for role awareness

In `_get_structure_directive()` (line 365), after resolving the canonical key (line 371), check reference overrides first:

```python
def _get_structure_directive(heading: str, page_role: str = "") -> str:
    key = heading.strip().lower()
    canonical = _HEADING_ALIASES.get(key, key)
    # Reference pages use tighter directives for certain sections
    if page_role in _REFERENCE_ROLES:
        override = _REFERENCE_DIRECTIVE_OVERRIDES.get(canonical)
        if override:
            return override
    directive = _STRUCTURE_DIRECTIVES.get(canonical, "")
    # ... rest unchanged
```

### Step 5: Inject reference preamble in build_section_prompt()

In `build_section_prompt()` (after line 445, where `template.format(...)` returns):

```python
    result = template.format(...)
    if page.page_role in _REFERENCE_ROLES:
        result = _REFERENCE_PREAMBLE + result
    return result
```

## Failure modes

### Failure mode 1: Token budget bloat for non-reference pages

**Detection**: Non-reference page prompts grow unexpectedly; check prompt length in logs
**Resolution**: The preamble is only injected when `page.page_role in _REFERENCE_ROLES`. The table example in OUTPUT FORMAT adds ~50 tokens — minimal impact.
**Gate**: N/A — prompt size is not gated

### Failure mode 2: LLM ignores table format despite example

**Detection**: Generated `.ir.json` still contains `type: "table"` blocks with JSON array content
**Resolution**: TC-3802 adds post-LLM validation to catch and repair this. The prompt fix addresses the root cause; validation is defense-in-depth.
**Gate**: gate_reference_completeness (TC-3803)

### Failure mode 3: Reference preamble conflicts with structure directives

**Detection**: LLM produces confusing output (e.g., tables where prose is expected, or vice versa)
**Resolution**: The preamble uses "for Constructors, Properties, Methods" qualifier — not blanket. Overview/Remarks still get prose. Test with pilot run.
**Gate**: Content review grading

### Failure mode 4: Existing tests break due to prompt changes

**Detection**: `pytest tests/unit/workers/test_generate.py` failures
**Resolution**: Tests that assert exact prompt content need updating. Tests that assert structure (headings, block types) should pass.
**Gate**: CI test suite

## Task-specific review checklist

1. [ ] Table example in OUTPUT FORMAT uses valid JSON with escaped newlines
2. [ ] Reference preamble is only injected for `_REFERENCE_ROLES` page roles
3. [ ] `_get_structure_directive()` checks reference overrides BEFORE generic directives
4. [ ] No hardcoded platform or language references in preamble/overrides
5. [ ] Existing structure directives for constructors/properties/methods remain unchanged
6. [ ] `_REFERENCE_ROLES` includes both `api_reference` and `reference_object_page`
7. [ ] Prompt template format placeholders (`{...}`) are properly escaped in preamble

## Deliverables

1. Modified `src/launcher/prompts/section_writer.txt` with table block example
2. Modified `src/launcher/workers/generate/section_prompt.py` with reference injection
3. Evidence bundle at `reports/TC-3801/evidence.md`

## Acceptance checks

1. [ ] `section_writer.txt` OUTPUT FORMAT section contains table block example
2. [ ] `build_section_prompt()` prepends reference preamble for api_reference pages
3. [ ] `_get_structure_directive("overview", page_role="api_reference")` returns the tighter override
4. [ ] `_get_structure_directive("overview", page_role="workflow_page")` returns the generic directive
5. [ ] All existing tests pass: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x`

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: prompt format PASS
- [ ] Evidence captured: reports/TC-3801/

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_generate.py -v
```

**Expected results**:
- All generate worker tests pass
- Prompt for api_reference pages contains "REFERENCE page" preamble
- Prompt for workflow_page does NOT contain reference preamble

## Integration boundary proven

**Upstream**: Page skeletons (`page_skeletons.py`) provide section structure; unchanged
**Downstream**: `section_validator.py` receives LLM output; table blocks will now have proper pipe-delimited content (TC-3802 adds validation)
**Contract**: BlockIR `type: "table"` with `content` as pipe-delimited markdown string (per `specs/content_model_pageir.md`)
