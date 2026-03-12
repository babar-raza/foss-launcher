---
id: TC-3877
title: "Include code snippets in claim extraction source material to fix thin-content NO-GO"
status: Done
priority: Critical
owner: "claude-agent"
updated: "2026-03-09"
tags: [understand, claims, content-density, no-go-blocker]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-3877_snippet_driven_claim_extraction.md
  - src/launcher/workers/understand/extract.py
  - tests/unit/workers/understand/test_snippet_claim_extraction.py
evidence_required:
  - reports/TC-3877/evidence.md
---

# Taskcard TC-3877 — Include code snippets in claim extraction to fix thin-content NO-GO

## Objective

The claim extractor sends only 24KB of documentation files to the LLM.
For FOSS wrappers like aspose-cells-foss-python (280 snippets, 33 claims,
0 public classes from compiled `.pyd` extensions), the docs are minimal and
the code examples are the primary knowledge source. By adding a representative
sample of code snippets to the LLM source material, the LLM can extract
50-100+ specific API and feature claims, eliminating the content_density high
findings that cause 19/19 D grades.

## Required spec references

- `src/launcher/workers/understand/extract.py` — `_build_doc_contexts`, `_call_llm_extract`
- `src/launcher/prompts/claim_extractor.txt` — LLM prompt with `{source_material}`

## Scope

### In scope
- Add a `_build_snippet_context()` function that collects a representative sample
  of code snippets (up to 30, capped at 8,000 chars) and formats them for the
  LLM source material
- Append the snippet block to the source material in `_extract_claims_llm`
- Increase `_MAX_SOURCE_CHARS` from 24,000 to 32,000 to accommodate snippet block

### Out of scope
- No changes to the claim extractor prompt template
- No changes to snippet storage or the Snippet model
- No changes to claim validation/normalization pipeline

## Inputs

- `src/launcher/workers/understand/extract.py` (current state)
- Code snippets collected in the understand phase

## Outputs

- `src/launcher/workers/understand/extract.py` — snippet block added to source material
- `tests/unit/workers/understand/test_snippet_claim_extraction.py` — unit tests

## Allowed paths

- `src/launcher/workers/understand/extract.py`
- `tests/unit/workers/understand/test_snippet_claim_extraction.py`

### Allowed paths rationale
Extract module and its tests only.

## Implementation steps

### Step 1: Add `_build_snippet_context()` function

```python
_SNIPPET_SAMPLE_MAX: int = 30
_SNIPPET_CHAR_BUDGET: int = 8_000

def _build_snippet_context(snippets: list[Snippet]) -> str:
    """Build a code-examples block for the LLM claim extractor.

    Selects up to _SNIPPET_SAMPLE_MAX snippets, deduplicates by code content,
    caps total characters at _SNIPPET_CHAR_BUDGET.  Returns empty string when
    no snippets are available.
    """
    if not snippets:
        return ""
    seen: set[str] = set()
    selected: list[str] = []
    total_chars = 0
    for s in snippets:
        key = s.code[:200]  # dedup by first 200 chars
        if key in seen:
            continue
        seen.add(key)
        block = f"```python\n{s.code}\n```"
        if total_chars + len(block) > _SNIPPET_CHAR_BUDGET:
            break
        selected.append(block)
        total_chars += len(block)
        if len(selected) >= _SNIPPET_SAMPLE_MAX:
            break
    if not selected:
        return ""
    return (
        "\n\n## CODE EXAMPLES (extract API-level claims from these)\n\n"
        + "\n\n".join(selected)
    )
```

### Step 2: Call `_build_snippet_context` and append to source_material

In `_call_llm_extract`, after building `source_material` from doc_contexts,
append the snippet block:
```python
snippet_block = _build_snippet_context(snippets or [])
if snippet_block:
    source_material = source_material + snippet_block
```

Pass `snippets` into `_call_llm_extract` as a new optional parameter.

### Step 3: Increase `_MAX_SOURCE_CHARS`

Change from 24,000 to 32,000 to accommodate the additional snippet block.

### Step 4: Unit tests

Test: `_build_snippet_context` deduplicates, caps chars, returns empty for empty input.

## Failure modes

### Failure mode 1: Snippet block pushes total context over LLM token limit
**Detection**: L1 validator fail or truncated JSON from LLM
**Resolution**: The `_SNIPPET_CHAR_BUDGET = 8_000` cap limits the block; combined with
32KB doc budget = 40KB total — within qwen3-next's 6000 max_tokens context window.
Actually max_tokens is the OUTPUT limit, not input. Input context is typically 128k.
**Gate**: `_SNIPPET_CHAR_BUDGET` hard cap prevents runaway; existing retry logic handles failures

### Failure mode 2: LLM extracts claims about example file patterns, not product features
**Detection**: Claims like "The file uses `import aspose_cells_foss as ac`"
**Resolution**: Existing contamination filter and dedup pipeline removes duplicates;
rules in claim_extractor.txt say "extract facts only — do NOT infer"
**Gate**: Post-LLM validation in `_validate_and_normalize_claims`

### Failure mode 3: `snippets` parameter not available in `_call_llm_extract` call site
**Detection**: TypeError on missing parameter
**Resolution**: Use `snippets: list[Snippet] | None = None` with default None
**Gate**: Unit test verifies empty snippets → no snippet block appended

## Task-specific review checklist

1. [x] `_build_snippet_context` function added with dedup and char cap
2. [x] `_SNIPPET_SAMPLE_MAX = 30` and `_SNIPPET_CHAR_BUDGET = 8_000` constants defined
3. [x] `_call_llm_extract` accepts `snippets` parameter (optional, default None)
4. [x] Snippet block appended to source_material when snippets present
5. [x] `_MAX_SOURCE_CHARS` increased from 24,000 to 32,000
6. [x] Unit tests: dedup, char cap, empty input, snippets appended to source_material
7. [x] Full test suite passes

## Deliverables

1. Modified `src/launcher/workers/understand/extract.py`
2. New `tests/unit/workers/understand/test_snippet_claim_extraction.py`

## Acceptance checks

1. [ ] Next pilot run shows 60+ claims (up from 33)
2. [ ] content_density high findings reduce significantly
3. [x] Unit tests pass (PYTHONHASHSEED=0)

## Self-review

### Verification results
- [x] Tests: 17/17 PASS (snippet tests) + 3034/3034 PASS (full suite)

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/test_snippet_claim_extraction.py -v
```

## Integration boundary proven

**Upstream**: `_extract_claims_llm(doc_contexts, product, context)` — adds `snippets` param
**Downstream**: LLM claim extraction → `_validate_and_normalize_claims` → `Claim` objects
**Contract**: Snippet block is appended to `source_material` string, same format as doc_contexts
