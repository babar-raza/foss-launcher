---
id: TC-3896
title: "Linker idempotency: replace See Also blocks instead of appending"
status: Done
priority: High
owner: "agent"
updated: "2026-03-09"
tags: [linker, bug, generate]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-3896_linker-idempotency.md
  - src/launcher/shared/linker.py
evidence_required:
  - plans/taskcards/TC-3896_linker-idempotency.md
---

# Taskcard TC-3896 — Linker idempotency: replace See Also blocks instead of appending

## Objective

Each heal step that re-runs the generate worker calls `link_pages()` again, which calls `inject_links()`, which appends a new link block to the existing See Also section. After 3 heal steps, pages have 4 identical/near-identical link blocks. Fix `inject_links()` to replace the See Also section's blocks instead of appending.

## Scope

### In scope
- `inject_links()` in `linker.py`: change append-to-existing logic to replace

### Out of scope
- Anchor text generation (LLM sandwich) — unchanged
- Link scoring logic — unchanged
- Changes to generate worker

## Inputs

- `linker.py` current `inject_links()` function

## Outputs

- `linker.py` with idempotent `inject_links()`

## Allowed paths

- plans/taskcards/TC-3896_linker-idempotency.md
- src/launcher/shared/linker.py

## Implementation steps

### Step 1: Fix inject_links() in linker.py

In the branch where `see_also_idx is not None`, replace the section's blocks list with `[link_block]` instead of appending.

### Step 2: Run linker tests

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -k "linker" -v --tb=short
```

## Failure modes

### Failure mode 1: See Also section had author-written prose before links

**Detection**: Prose content lost after fix
**Resolution**: Preserve non-list blocks before the link block (filter by block type)
**Gate**: content review

### Failure mode 2: SectionIR doesn't support dataclasses.replace

**Detection**: AttributeError or TypeError
**Resolution**: Create new SectionIR manually with same fields but updated blocks
**Gate**: test suite

### Failure mode 3: `see_also_idx` path finds wrong section

**Detection**: A different section's content is overwritten
**Resolution**: Add assertion that `sections[see_also_idx].section_id == "see_also"`
**Gate**: test suite

## Task-specific review checklist

1. [ ] Existing See Also blocks are REPLACED not appended to
2. [ ] Non-link content in See Also (if any) is preserved
3. [ ] New See Also sections still created correctly when none exists
4. [ ] Calling inject_links() twice on same PageIR → exactly 1 link block
5. [ ] All linker tests pass
6. [ ] Regression test added for idempotency
7. [ ] Docstrings updated — minimal, logic change
8. [ ] No schema changes needed
9. [ ] No spec changes needed
10. [ ] docs/README.md — N/A

## Deliverables

1. `linker.py` with idempotent inject_links()
2. New regression test in test_linker.py

## Acceptance checks

1. [ ] inject_links() called twice → PageIR has exactly 1 See Also link block
2. [ ] inject_links() called once → same output as before (no regression)
3. [ ] All linker tests pass (0 failures)

## Self-review

### Verification results
- [ ] Tests: X/X PASS

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -k "linker" -v
```

## Integration boundary proven

**Upstream**: generate worker calls link_pages() → inject_links() per page
**Downstream**: evaluate worker reads content_bundle with See Also section
**Contract**: Each page has exactly 1 See Also link block after linker runs, regardless of how many times it runs
