---
id: TC-3912
title: "Deterministic Prerequisites & Code Example fallback for zero-claim sections"
status: Done
priority: High
owner: "agent"
updated: "2026-03-09"
tags: [fallback, generate, prerequisites, content-quality]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-3912_prerequisite-deterministic-fallback.md
  - src/launcher/workers/generate/fallback.py
  - tests/unit/generate/test_fallback_deterministic.py
evidence_required:
  - reports/TC-3912/evidence.md
---

# Taskcard TC-3912 — Deterministic Prerequisites & Code Example fallback for zero-claim sections

## Objective

`render_section_deterministic` currently produces placeholder stubs ("For details on prerequisites, see the Aspose.X documentation.") when `claims=[]` and `snippets=[]`. This fires for ALL how-to pages because the planner assigns 0 claims to kb/how-to-* pages. Fix the fallback to produce real, canonical content for well-known boilerplate section types (Prerequisites, Code Example) using only `product.canonical_import` and `product.platform` — no LLM required.

## Required spec references

- `specs/workers_generate.md` (Section: fallback renderer requirements)

## Scope

### In scope
- Modify `render_section_deterministic` in `fallback.py` to generate real content for `prerequisites` and `code example` sections when `claims=[]` and `snippets=[]`
- Add unit tests for the new deterministic outputs
- Prerequisites: pip install command + import statement (list block + code block)
- Code Example: minimal runnable example with canonical import

### Out of scope
- Fixing the planner's claim assignment for how-to pages (separate concern)
- Fixing the LLM prompt conflict for 0-claim sections (separate TC)
- Modifying enforce_block_spec (not needed)

## Inputs

- `product.canonical_import` (e.g. `aspose_cells_foss`)
- `product.platform` (e.g. `python`)
- `section.heading` (e.g. `Prerequisites`, `Code Example`)

## Outputs

- `src/launcher/workers/generate/fallback.py` — enhanced `render_section_deterministic`
- `tests/unit/generate/test_fallback_deterministic.py` — unit tests

## Allowed paths

- `plans/taskcards/TC-3912_prerequisite-deterministic-fallback.md`
- `src/launcher/workers/generate/fallback.py`
- `tests/unit/generate/test_fallback_deterministic.py`

### Allowed paths rationale
- `fallback.py`: target of the fix — adds boilerplate section handlers
- `test_fallback_deterministic.py`: new test file covering the fix

## Implementation steps

### Step 1: Add boilerplate section constants to fallback.py

Add a frozenset `_PREREQUISITES_HEADINGS` covering heading variants:
```python
_PREREQUISITES_HEADINGS: frozenset[str] = frozenset({
    "prerequisites", "requirements", "setup", "installation prerequisites",
    "before you begin", "what you need",
})

_CODE_EXAMPLE_HEADINGS: frozenset[str] = frozenset({
    "code example", "code examples", "code sample", "code samples",
    "working example", "example code", "complete code example",
})
```

### Step 2: Add deterministic helper functions

Add two helpers before `render_section_deterministic`:

```python
def _render_prerequisites_blocks(product: ProductIdentity) -> list[BlockIR]:
    """Deterministic Prerequisites block for zero-claim sections."""
    lang = get_lang_tag(product.platform)
    canonical = product.canonical_import or "aspose_foss"
    items = [
        f"Python 3.7+ (or the platform runtime for {product.platform})",
        f"Install via pip: `pip install {canonical}`",
    ]
    return [
        BlockIR(type=BlockType.list, items=items),
        BlockIR(
            type=BlockType.code,
            content=f"import {canonical}",
            language=lang,
        ),
    ]

def _render_code_example_blocks(product: ProductIdentity) -> list[BlockIR]:
    """Deterministic Code Example block for zero-claim sections."""
    lang = get_lang_tag(product.platform)
    canonical = product.canonical_import or "aspose_foss"
    code = f"import {canonical}\n\n# Initialize — see the {canonical} API reference for available classes"
    return [
        BlockIR(
            type=BlockType.paragraph,
            content=f"The following example demonstrates how to get started with {product.display_name}.",
        ),
        BlockIR(type=BlockType.code, content=code, language=lang),
    ]
```

### Step 3: Integrate into render_section_deterministic

In the `if not claims and not snippets:` branch (line 107-116), replace the placeholder "For details..." paragraph with deterministic content:

```python
if not claims and not snippets:
    heading_lower = section.heading.lower()
    if heading_lower in _PREREQUISITES_HEADINGS:
        blocks.extend(_render_prerequisites_blocks(product))
    elif heading_lower in _CODE_EXAMPLE_HEADINGS:
        blocks.extend(_render_code_example_blocks(product))
    else:
        blocks.append(BlockIR(
            type=BlockType.paragraph,
            content=(
                f"For details on {section.heading.lower()}, "
                f"see the {product.display_name} documentation."
            ),
        ))
```

### Step 4: Write unit tests

Create `tests/unit/generate/test_fallback_deterministic.py` with:
- `test_prerequisites_zero_claims_produces_list_and_code` — checks list block + code block with correct import
- `test_code_example_zero_claims_produces_paragraph_and_code` — checks paragraph + code
- `test_other_section_zero_claims_still_uses_fallback_stub` — verifies non-boilerplate still uses old placeholder
- `test_prerequisites_with_claims_uses_claims_not_boilerplate` — when claims exist, use claims (not boilerplate)
- `test_code_example_with_snippets_uses_snippets` — when snippets exist, use them
- `test_content_hint_stub_still_generated` — content_hint stub still appears before boilerplate blocks

### Step 5: Run tests

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/generate/test_fallback_deterministic.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

## Failure modes

### Failure mode 1: heading_lower doesn't match known variants

**Detection**: `render_section_deterministic` for "Before You Begin" heading still produces stub
**Resolution**: Add "before you begin" to `_PREREQUISITES_HEADINGS` frozenset
**Gate**: Unit test `test_prerequisites_zero_claims_produces_list_and_code`

### Failure mode 2: canonical_import is None or empty

**Detection**: Code block content is `"import None"` or `"import "`
**Resolution**: Guard with `canonical = product.canonical_import or "aspose_foss"` (already in step 2)
**Gate**: Unit test with `canonical_import=None`

### Failure mode 3: Language tag wrong for non-Python platforms

**Detection**: TypeScript/JavaScript pages get `python` language tag on code blocks
**Resolution**: `get_lang_tag(product.platform)` already handles this correctly
**Gate**: Unit test with `platform="typescript"`

## Task-specific review checklist

1. [ ] `_PREREQUISITES_HEADINGS` covers "prerequisites", "requirements", "setup" at minimum
2. [ ] `_CODE_EXAMPLE_HEADINGS` covers "code example", "code examples", "code sample" at minimum
3. [ ] New helpers `_render_prerequisites_blocks` and `_render_code_example_blocks` are private (prefixed `_`)
4. [ ] The `content_hint` stub is still emitted before the boilerplate blocks (not instead of them)
5. [ ] When `claims` or `snippets` are non-empty, the old behavior is unchanged
6. [ ] No LLM calls — fully deterministic
7. [ ] Docstrings updated for `render_section_deterministic`
8. [ ] Spec file updated if worker behavior changed (or confirmed no spec drift)
9. [ ] Schema `"description"` fields present for all new/changed properties
10. [ ] Checked `docs/README.md` ownership map — if a trigger event applies, relevant guide updated
11. [ ] If a new `docs/guides/` file was added: `docs/README.md` index updated

## Deliverables

1. `src/launcher/workers/generate/fallback.py` — enhanced with boilerplate section handlers
2. `tests/unit/generate/test_fallback_deterministic.py` — 6 unit tests

## Acceptance checks

1. [ ] All 6 unit tests in `test_fallback_deterministic.py` pass
2. [ ] Full test suite passes: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q`
3. [ ] No IR files in snapshots/ contain "For details on prerequisites" after re-promotion

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Evidence captured: reports/TC-3912/evidence.md

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/generate/test_fallback_deterministic.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

**Expected results**:
- All new tests pass
- Full suite passes (≥3236 tests)

## Integration boundary proven

**Upstream**: `enforce_block_spec` pass3 calls `render_section_deterministic` with `section_claims=[]`, `section_snippets=[]`
**Downstream**: Generated `SectionIR` fed into `PageIR` → evaluated by gates → promoted to snapshots
**Contract**: `SectionIR` with non-placeholder blocks satisfies safety gates
