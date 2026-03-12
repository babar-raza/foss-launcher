---
id: TC-3888
title: "Fix inline commercial package names in prose blocks"
status: Done
priority: High
owner: "agent"
updated: "2026-03-09"
tags: [generate, canonical_import, false_positive]
depends_on: [TC-3887]
allowed_paths:
  - plans/taskcards/TC-3888_fix_inline_canonical_import_in_prose.md
  - src/launcher/workers/generate/worker.py
  - tests/unit/workers/generate/
evidence_required:
  - reports/TC-3888/evidence.md
---

# Taskcard TC-3888 — Fix inline commercial package names in prose blocks

## Objective

The LLM sometimes generates prose sections that include inline code references to the
commercial package name (e.g. `` `pip install Aspose.Cells` `` or `` `import Aspose.Cells` ``)
instead of the FOSS canonical import (`aspose_cells_foss`). These appear in prose
`paragraph` blocks (not fenced code blocks), so `_sanitize_code_blocks` does not catch them.

The `check_canonical_import` evaluator flags these as `canonical_import HIGH` and
`factual_accuracy HIGH`, causing 2 `_index` pages to be Grade C instead of B.

Fix: add `_fix_prose_canonical_imports(blocks, canonical_import)` in generate/worker.py
that replaces wrong package names in inline code spans within prose blocks.

## Required spec references

- `specs/09_quality_evaluation.md` (canonical_import check)

## Scope

### In scope
- Add `_fix_prose_canonical_imports(blocks, canonical_import)` to `generate/worker.py`
- Apply after `_sanitize_code_blocks` in `_generate_section` (initial LLM path)
- Apply after `_strip_commercial_urls` in the final cleanup block

### Out of scope
- Changing `_sanitize_code_blocks` (fenced code block fix already implemented)
- Changing the canonical_import check logic
- Changing any other worker

## Inputs

- `src/launcher/workers/generate/worker.py` — `_generate_section` function

## Outputs

- Fixed generate worker that replaces wrong inline package names in prose

## Allowed paths

- plans/taskcards/TC-3888_fix_inline_canonical_import_in_prose.md
- src/launcher/workers/generate/worker.py
- tests/unit/workers/generate/

### Allowed paths rationale
- generate/worker.py — contains `_generate_section` and inline fix point
- tests/ — test coverage

## Implementation steps

### Step 1: Add `_fix_prose_canonical_imports` function

Add after `_normalize_code_languages` in worker.py:

```python
_WRONG_INLINE_PKG_RE = re.compile(
    r"`((?:pip install|pip3 install|from|import)\s+)(Aspose\.\w+|aspose\.\w+)([^`]*)`",
    re.IGNORECASE,
)

def _fix_prose_canonical_imports(
    blocks: list[BlockIR], canonical_import: str
) -> list[BlockIR]:
    """Replace wrong inline package names in prose blocks (TC-3888).

    Catches LLM-generated prose like `pip install Aspose.Cells` or
    `import Aspose.Cells` and replaces with the correct canonical import.
    Only modifies paragraph/prose blocks, not fenced code blocks.
    """
    if not canonical_import:
        return blocks

    result: list[BlockIR] = []
    changed = 0
    for block in blocks:
        if block.type not in (BlockType.paragraph, BlockType.prose) or not block.content:
            result.append(block)
            continue

        def _replace(m: re.Match) -> str:
            verb = m.group(1)
            rest = m.group(3)
            return f"`{verb}{canonical_import}{rest}`"

        new_content = _WRONG_INLINE_PKG_RE.sub(_replace, block.content)
        if new_content != block.content:
            changed += 1
            result.append(block.model_copy(update={"content": new_content}))
        else:
            result.append(block)

    if changed:
        logger.info("[Generate] Fixed %d prose blocks with wrong inline canonical imports", changed)
    return result
```

### Step 2: Apply in `_generate_section`

Apply `_fix_prose_canonical_imports` in the final cleanup block (after `_normalize_code_languages`):

```python
# Fix wrong inline package names in prose (TC-3888)
fixed_blocks = _fix_prose_canonical_imports(list(section_ir.blocks), product.canonical_import)
if fixed_blocks != list(section_ir.blocks):
    section_ir = section_ir.model_copy(update={"blocks": fixed_blocks})
```

### Step 3: Add tests

In `tests/unit/workers/generate/test_fix_prose_canonical_imports.py`:
- prose block with `` `pip install Aspose.Cells` `` → `` `pip install aspose_cells_foss` ``
- prose block with `` `import Aspose.Cells` `` → `` `import aspose_cells_foss` ``
- prose block with `` `from Aspose.Cells import Workbook` `` → `` `from aspose_cells_foss import Workbook` ``
- fenced code block (type=code) NOT modified
- non-code prose without inline code → unchanged
- correct import already → unchanged

### Step 4: Run tests

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/generate/ -v
```

## Failure modes

### Failure mode 1: Regex over-matches product display name

**Detection**: "Aspose.Cells" in non-import prose is replaced (e.g., "Aspose.Cells is a library")
**Resolution**: The regex requires `pip install|from|import` prefix before the package name, so plain display name mentions are not affected
**Gate**: test suite

### Failure mode 2: canonical_import is empty/None

**Detection**: None — guard `if not canonical_import: return blocks` prevents issues
**Gate**: unit test with empty canonical_import

### Failure mode 3: BlockType.paragraph not correct enum value

**Detection**: Import error or attribute error when checking block.type
**Resolution**: Use same BlockType enum as `_sanitize_code_blocks` uses
**Gate**: test suite

## Task-specific review checklist

1. [ ] `_fix_prose_canonical_imports` function added
2. [ ] Applied in `_generate_section` final cleanup block
3. [ ] Regex only matches import/install commands (not display name prose)
4. [ ] Code blocks (type=code) not touched
5. [ ] Tests cover pip install, import, from..import patterns
6. [ ] Tests confirm display name prose is NOT affected
7. [ ] Tests pass

## Deliverables

1. `src/launcher/workers/generate/worker.py` — `_fix_prose_canonical_imports` added and applied

## Acceptance checks

1. [ ] `docs/_index.md` no longer has `pip install Aspose.Cells` in prose
2. [ ] `canonical_import HIGH` eliminated from affected _index pages
3. [ ] All tests pass

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Evidence captured: reports/TC-3888/evidence.md

## E2E verification

Check two `_index` pages in evaluate_checkpoint: canonical_import HIGH should be gone.

## Integration boundary proven

**Upstream**: LLM generates prose with wrong inline package names
**Downstream**: check_canonical_import evaluates content; factual_accuracy LLM check
**Contract**: Wrong inline imports fixed → canonical_import HIGH eliminated → C→B
