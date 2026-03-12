---
id: TC-3909
title: "Inject code blocks for Code Example sections when golden spec lookup fails"
status: Done
priority: High
owner: "agent"
updated: "2026-03-09"
tags: [generate, enforce_block_spec, howto_article, code_correctness]
depends_on: [TC-3908]
allowed_paths:
  - plans/taskcards/TC-3909_code-example-section-injection.md
  - src/launcher/workers/generate/worker.py
  - tests/unit/workers/generate/
evidence_required:
  - reports/TC-3909/evidence.md
---

# Taskcard TC-3909 — Inject code blocks for Code Example sections

## Objective

`howto_article` pages with "Code Example" skeleton sections consistently fail
`structure HIGH` ("no code block found") because `enforce_block_spec` returns early
when `get_spec(page_role, variant, heading)` returns None.

Root cause: the golden howto standard file sections (Step-by-Step Guide, Common Issues,
FAQ) don't match the planner-generated skeleton headings (Code Example, Solution Steps,
Prerequisites). Jaccard threshold 0.5 catches nothing since the heading words differ.

Fix: in `enforce_block_spec`, when `spec is None` but the section heading contains
code-indicating keywords ("code example", "code snippet", "working example", etc.),
synthesize a minimal GoldenBlockSpec requiring a code block. This ensures a code block
is injected via `_gap_fill_code_block` even when no matching golden section exists.

## Required spec references

- `specs/09_quality_evaluation.md` (structure check)

## Scope

### In scope
- Add heuristic in `enforce_block_spec` for code-indicating section headings
- Synthesize GoldenBlockSpec when spec=None but heading implies code

### Out of scope
- Changing golden files
- Changing golden_loader.py
- Any other check or worker

## Inputs

- `src/launcher/workers/generate/worker.py` — `enforce_block_spec` function (~line 1125)

## Outputs

- `enforce_block_spec` injects code blocks for "Code Example" sections even without
  a matching golden spec

## Allowed paths

- plans/taskcards/TC-3909_code-example-section-injection.md
- src/launcher/workers/generate/worker.py
- tests/unit/workers/generate/

## Implementation steps

### Step 1: Add heuristic in `enforce_block_spec`

After `spec = golden_index.get_spec(...)`, when spec is None, check heading:

```python
# TC-3909: Synthesize a minimal spec for code-indicating section headings when
# no golden spec was found. Ensures "Code Example" sections always get a code block
# injection attempt even when golden section heading matching fails.
if spec is None:
    heading_lower = (skel_section.heading or "").lower()
    _CODE_HEADING_KEYWORDS = (
        "code example", "code snippet", "working example",
        "example code", "code sample", "code block",
    )
    if any(kw in heading_lower for kw in _CODE_HEADING_KEYWORDS):
        spec = GoldenBlockSpec(
            required_block_types=["paragraph", "code"],
            min_words=30,
        )
```

Then the existing `check_against_spec` and `_gap_fill_code_block` logic handles the rest.

### Step 2: Add tests

### Step 3: Run tests

## Failure modes

### Failure mode 1: Synthetic spec causes over-injection of code blocks

**Detection**: Pages that should have no code get code injected
**Resolution**: Heuristic only fires for exact keyword phrases ("code example", etc.)
Generic headings like "Problem", "Prerequisites", "Overview" don't match.
**Gate**: Existing tests for pages without "Code Example" sections unchanged

### Failure mode 2: Injected code block uses wrong snippet

**Detection**: Code block content is from a different page/topic
**Resolution**: `_gap_fill_code_block` uses the section's `section_snippets` which are
already filtered to be relevant to the section's claims. Fallback uses generic snippets.
**Gate**: Unit test confirms code block is injected

### Failure mode 3: spec=None + check_against_spec(section_ir, spec) early return

**Detection**: The existing `if spec is None or check_against_spec(...)` guard returns
before the heuristic can apply the synthetic spec.
**Resolution**: The heuristic must be inserted BEFORE the existing return statement.
Current code:
```python
spec = golden_index.get_spec(...)
if spec is None or check_against_spec(section_ir, spec):
    return section_ir, "none"
```
Change to:
```python
spec = golden_index.get_spec(...)
if spec is None:
    # TC-3909 heuristic here
    ...
if spec is None or check_against_spec(section_ir, spec):
    return section_ir, "none"
```
**Gate**: Code review + test

## Task-specific review checklist

1. [ ] Heuristic inserted BEFORE the `if spec is None or ...` guard
2. [ ] Keywords match "code example" family only (not generic headings)
3. [ ] Synthetic spec has required_block_types=["paragraph", "code"] and min_words=30
4. [ ] Test: "Code Example" heading with no code → code injected
5. [ ] Test: "Overview" heading with no code → NOT injected
6. [ ] Tests pass

## Deliverables

1. `src/launcher/workers/generate/worker.py` — `enforce_block_spec` updated

## Acceptance checks

1. [ ] `fix-spreadsheets-errors-python` structure HIGH gone
2. [ ] `save-spreadsheets-python` code_correctness HIGH for no-code fixed
3. [ ] A+B rate ≥ 50% in pilot run

## Self-review

### Verification results
- [ ] Tests pass
- [ ] Evidence: reports/TC-3909/evidence.md

## E2E verification

`fix-spreadsheets-errors-python` should have code blocks in next pilot run.

## Integration boundary proven

**Upstream**: LLM generates "Code Example" sections without code blocks
**Downstream**: structure check fires HIGH for missing code
**Contract**: enforce_block_spec injects code → no structure HIGH → page grade improves
