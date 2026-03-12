---
id: SNP-06
title: "Document or populate line_start/line_end for fenced blocks and whole-file examples"
status: Done
priority: Low
owner: agent
updated: "2026-03-11"
tags: [understand, snippets, provenance, TC-4063]
depends_on: [TC-4063]
allowed_paths:
  - plans/healing/SNP-06-line-range-handling.md
  - src/launcher/workers/understand/extract/_snippets.py
evidence_required:
  - reports/SNP-06/evidence.md
---

# SNP-06 — Document or populate `line_start`/`line_end` for snippet extraction

## Objective

TC-4063 added `line_start` and `line_end` fields to `Snippet` but left them as `None` for
all extracted snippets. The taskcard stated this was intentional for fenced blocks
("position not tracked during extraction") but did not document this in code or commit to
a specific policy. Downstream consumers that display or index snippets by location need to
know whether `None` means "unknown" or "whole file".

This taskcard either:
- (A) Documents the None-for-all policy clearly in the docstring of `_extract_snippets()`
  and the field docstring in `Snippet`, OR
- (B) Implements approximate line tracking for fenced blocks by scanning for the code
  fence in the file text and recording the line number of the opening fence.

## Required spec references

- `specs/claims_evidence.md` (Snippet model: line_start, line_end semantics)
- `specs/worker_understand.md` (Phase B.3: snippet extraction contract)

## Scope

### In scope
**Option A (preferred — documentation only)**:
- Add to `_extract_snippets()` docstring: "Note: `line_start` and `line_end` are always
  `None` for fenced code blocks (position not tracked); use `source_file` for traceability."
- Add to `Snippet` field comment: "# Approximate line range; None for fenced blocks (see TC-4063)"

**Option B (implementation — if Option A is rejected by reviewer)**:
- In the fenced block extraction loop, track `line_no` by counting newlines up to each
  block's opening fence in the file text
- Pass `line_start=line_no` to `Snippet(...)`
- `line_end = line_no + code.count("\n")` (approximate)

### Out of scope
- Implementing byte-offset or character-offset tracking
- Changing `EvidenceAnchor.line_start`/`line_end` semantics on `Claim`
- Schema changes (already handled in TC-4063 — both fields are optional with null default)

## Inputs

- `src/launcher/workers/understand/extract/_snippets.py` (extraction logic)
- `src/launcher/models/claims.py` (Snippet field definitions)

## Outputs

**Option A**: `_snippets.py` docstring update + `claims.py` comment update
**Option B**: `_snippets.py` with approximate line tracking

## Allowed paths

- plans/healing/SNP-06-line-range-handling.md
- src/launcher/workers/understand/extract/_snippets.py

### Allowed paths rationale
Documentation change in `_snippets.py` docstring is sufficient for Option A.
`claims.py` comment may optionally be updated but is a secondary concern.

## Implementation steps

### Step 1: Confirm current behaviour

Read `_snippets.py` `_extract_snippets()` function and confirm:
- Fenced blocks: `Snippet(... source_file=rel_path)` — no `line_start`/`line_end` passed → both `None`
- Whole-file examples: same (or check if line 1..N is passed for any case)

### Step 2A (Option A — documentation): Update `_extract_snippets()` docstring

Add or extend the function docstring:
```python
def _extract_snippets(...) -> list[Snippet]:
    """Extract fenced code snippets and whole-file source examples from repo docs.

    ...existing docstring content...

    Note:
        ``line_start`` and ``line_end`` on returned ``Snippet`` objects are always
        ``None`` — fenced block position within source files is not tracked during
        extraction. Use ``source_file`` for traceability back to the originating file.
        See TC-4063 for rationale.
    """
```

### Step 2B (Option B — implementation): Track line numbers for fenced blocks

Inside the fenced block extraction loop, after obtaining the file text, compute the line
number of each fence opening:

```python
lines = file_text.splitlines()
for block_idx, (lang, code) in enumerate(fenced_blocks):
    # Find the opening fence line
    fence_tag = f"```{lang}" if lang else "```"
    line_start = None
    occurrence = 0
    for ln, line in enumerate(lines, start=1):
        if line.strip().startswith(fence_tag):
            if occurrence == block_idx:
                line_start = ln
                break
            occurrence += 1
    line_end = (line_start + code.count("\n") + 1) if line_start else None
    # ... existing dedup + append logic ...
    snippets.append(Snippet(
        code=code.strip(),
        language=effective_lang,
        source_type="extracted",
        source_file=rel_path,
        line_start=line_start,
        line_end=line_end,
        claim_ids=linked_claim_ids,
    ))
```

Note: This is approximate — it will misfire if the same fence tag appears multiple times
in different contexts (e.g., in a table or inline code). It is explicitly "best-effort".

### Step 3: Run tests

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/test_extract.py -v -q
```

If Option B: SNP-01's `TestSnippetProvenance` test may need extending to also assert
`line_start is not None` for fenced blocks from a file with known structure.

## Failure modes

### Failure mode 1 (Option B): Off-by-one in line counting

**Detection**: `line_start` points to the line before or after the opening fence
**Resolution**: Adjust `enumerate(lines, start=1)` vs `start=0`; verify with a known file
**Gate**: Unit test that asserts `line_start == expected_line` for a fixture file

### Failure mode 2 (Option B): Multiple identical fence tags confuse the matcher

**Detection**: `line_start` points to a fence tag in a table rather than a code block
**Resolution**: This is a known limitation of approximate tracking. Add a comment stating
this is best-effort. The `None` fallback (Option A) is acceptable for fenced blocks.
**Gate**: Code review

### Failure mode 3: Docstring change breaks automated doc extraction

**Detection**: Doc generation tool fails on malformed docstring
**Resolution**: Follow Google/NumPy style already used in `_snippets.py`; check existing
docstring format before adding the Note section
**Gate**: CI doc check (if configured)

## Task-specific review checklist

1. [ ] Option A or B chosen and documented in evidence file
2. [ ] Option A: `_extract_snippets()` docstring explains None policy with TC-4063 reference
3. [ ] Option B: `line_start`/`line_end` populated for at least fenced blocks in README
4. [ ] Option B: "best-effort" / "approximate" language present in comment or docstring
5. [ ] No change to schema (already optional, null default from TC-4063)
6. [ ] `Snippet(code="x")` still constructs with `line_start=None, line_end=None` (backward compat)
7. [ ] Docstrings updated for all new/changed public functions
8. [ ] Spec file updated if worker behavior changed (or confirmed no spec drift)
9. [ ] Schema `"description"` fields present for all new/changed properties
10. [ ] Checked `docs/README.md` ownership map — no guide trigger from docstring update
11. [ ] N/A — no new docs/guides/ file added

## Deliverables

1. `src/launcher/workers/understand/extract/_snippets.py` with docstring (Option A) or line tracking (Option B)
2. `reports/SNP-06/evidence.md` with rationale for Option A vs B and test results

## Acceptance checks

1. [ ] `grep -A 5 "line_start" src/launcher/workers/understand/extract/_snippets.py` shows either docstring note (Option A) or assignment (Option B)
2. [ ] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/ -x -q` passes
3. [ ] Evidence file documents the choice made and why

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Evidence captured: reports/SNP-06/evidence.md

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/test_extract.py -v -q
```

**Expected results**:
- All snippet extraction tests pass
- Docstring present on `_extract_snippets()` (Option A) OR line numbers populated in test output (Option B)

## Integration boundary proven

**Upstream**: File text scanning in `_extract_snippets()` fenced block loop
**Downstream**: `Snippet.line_start`, `Snippet.line_end` consumed by downstream display or indexing tools
**Contract**: Both fields are `int | None` with null as explicit "unknown/not-tracked" signal; `source_file` is the primary traceability field
