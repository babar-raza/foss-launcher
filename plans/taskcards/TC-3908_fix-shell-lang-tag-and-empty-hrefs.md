---
id: TC-3908
title: "Fix wrong python-tagged shell blocks and empty href links in generate worker"
status: Done
priority: High
owner: "agent"
updated: "2026-03-09"
tags: [generate, code_correctness, artifacts, postprocessing]
depends_on: [TC-3887, TC-3895]
allowed_paths:
  - plans/taskcards/TC-3908_fix-shell-lang-tag-and-empty-hrefs.md
  - src/launcher/workers/generate/worker.py
  - tests/unit/workers/generate/
evidence_required:
  - reports/TC-3908/evidence.md
---

# Taskcard TC-3908 — Fix wrong python-tagged shell blocks and empty href links

## Objective

Two generate-phase defects cause `code_correctness HIGH` and `artifacts HIGH` on `_index`
pages (toc/landing roles), pushing them from B to C.

### Defect 1: Wrong python language tag on shell command blocks

`_normalize_code_languages` only assigns language to blocks with no language tag.
When the LLM explicitly generates ` ```python\npip install aspose_cells_foss\n``` `, the
block has `language="python"` so `_normalize_code_languages` skips it. The evaluate worker
then flags `code_correctness HIGH`: "shell command in Python-tagged block".

Fix: extend `_normalize_code_languages` to also correct already-tagged blocks where
content starts with a shell prefix and language is set to "python" or "py".

### Defect 2: Empty/unclosed href links in prose blocks

The LLM generates links like `[Aspose.Cells docs](` without a URL (unclosed paren). In
"See Also" / "Related" sections of `toc` pages, the LLM doesn't know the actual URL so
it leaves it empty. The artifacts check flags these as `HIGH`.

Fix: add `_fix_empty_hrefs` post-processing function that converts `[text]()` and
`[text](\n` to plain text `text` in paragraph and list blocks.

Both fixes run after `_fix_prose_canonical_imports` in `_generate_section`.

## Required spec references

- `specs/09_quality_evaluation.md` (artifacts, code_correctness checks)

## Scope

### In scope
- Extend `_normalize_code_languages` to correct wrong python tag on shell blocks
- Add `_fix_empty_hrefs` function and apply it in `_generate_section`

### Out of scope
- Changing artifacts.py or review_prompt.txt
- Fixing code_correctness issues from hallucinated API methods (separate concern)

## Inputs

- `src/launcher/workers/generate/worker.py`

## Outputs

- Fixed generate worker with both post-processing fixes

## Allowed paths

- plans/taskcards/TC-3908_fix-shell-lang-tag-and-empty-hrefs.md
- src/launcher/workers/generate/worker.py
- tests/unit/workers/generate/

## Implementation steps

### Step 1: Extend `_normalize_code_languages`

Change the guard from `if block.type != "code" or block.language:` to also correct
explicitly wrong python/py tags when content is a shell command:

```python
# Current: only fix untagged blocks
if block.type != "code" or block.language:
    result.append(block)
    continue

# New: fix untagged OR wrong python/py tag on shell content
if block.type != "code":
    result.append(block)
    continue
first_line = (block.content or "").lstrip().split("\n")[0].lstrip()
is_shell = any(first_line.startswith(p) for p in _SHELL_PREFIXES)
if block.language and not (is_shell and block.language in ("python", "py")):
    # Already tagged correctly
    result.append(block)
    continue
lang = "bash" if is_shell else "python"
result.append(BlockIR(..., language=lang, ...))
```

### Step 2: Add `_fix_empty_hrefs` function

```python
_EMPTY_HREF_RE2 = re.compile(
    r'\[([^\[\]]+)\]\(\s*\)'           # [text]()
    r'|'
    r'\[([^\[\]]+)\]\(\s*$',           # [text]( at end of line
    re.MULTILINE,
)

def _fix_empty_hrefs(blocks: list[BlockIR]) -> list[BlockIR]:
    """Remove empty/unclosed href links in prose and list blocks (TC-3908).

    Converts [text]() and [text]( (unclosed) to plain text.
    Prevents artifacts HIGH for broken links the LLM generates without URLs.
    """
    ...
```

Apply to paragraph blocks (block.content) and list blocks (block.items).

### Step 3: Apply in `_generate_section` after `_fix_prose_canonical_imports`

### Step 4: Add tests

## Failure modes

### Failure mode 1: Valid Python-tagged blocks with shell-like first line are renamed

**Detection**: A block like ` ```python\n# pip install is not needed\n``` ` becomes bash
**Resolution**: The guard checks if the FIRST non-empty line starts with shell prefix.
A comment line starts with `#`, not `pip `. Safe.
**Gate**: Unit test: python block with comment first line unchanged

### Failure mode 2: Empty href stripping removes intentional empty links

**Detection**: Any valid use of `[text]()` (unlikely in generated docs)
**Resolution**: In generated documentation, `[text]()` is always a bug. The LLM never
intentionally generates empty hrefs.
**Gate**: Unit test confirms strip happens

### Failure mode 3: List block items not processed

**Detection**: artifacts HIGH still fires on list items in "See Also" sections
**Resolution**: `_fix_empty_hrefs` processes both `block.content` and `block.items`
**Gate**: Pilot run artifacts HIGH on _index = 0

## Task-specific review checklist

1. [ ] `_normalize_code_languages` corrects python→bash for shell content
2. [ ] `_normalize_code_languages` does NOT change non-python explicit tags
3. [ ] `_fix_empty_hrefs` strips `[text]()` → `text`
4. [ ] `_fix_empty_hrefs` strips unclosed `[text](\n` → `text`
5. [ ] Both paragraph and list block items are processed
6. [ ] Both fixes applied in `_generate_section` after existing post-processing

## Deliverables

1. `src/launcher/workers/generate/worker.py` — both fixes

## Acceptance checks

1. [ ] `code_correctness HIGH` for "shell command in python block" gone from _index pages
2. [ ] `artifacts HIGH` for empty hrefs gone from _index pages
3. [ ] 3 _index pages move from C to B/A → A+B rate ≥50%

## Self-review

### Verification results
- [ ] Tests pass
- [ ] Evidence: reports/TC-3908/evidence.md

## E2E verification

`_index` pages in next pilot run: no artifacts HIGH, no code_correctness HIGH for shell-in-python.

## Integration boundary proven

**Upstream**: LLM generates blocks with wrong python tag / missing URLs
**Downstream**: evaluate checks artifacts + code_correctness
**Contract**: Post-processing in generate worker → clean markdown → no HIGH findings
