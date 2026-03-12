---
id: TC-3889
title: "Fix semantic_structure false positive: H2 sections with H3 sub-headings flagged as empty"
status: Done
priority: High
owner: "agent"
updated: "2026-03-09"
tags: [evaluate, semantic_structure, false_positive]
depends_on: [TC-3886]
allowed_paths:
  - plans/taskcards/TC-3889_fix_semantic_structure_subsection_false_positive.md
  - src/launcher/workers/evaluate/checks/semantic_structure.py
  - tests/unit/workers/evaluate/checks/
evidence_required:
  - reports/TC-3889/evidence.md
---

# Taskcard TC-3889 — Fix semantic_structure false positive for H2→H3 subsection structure

## Objective

`check_semantic_structure` fires "Empty section under heading: 'Optimization Steps'" for
H2 sections that go directly to H3 sub-headings with no intro prose. This is valid
structure for howto articles (e.g., `## Optimization Steps` → `### Step 1`, `### Step 2`).

The current code already suppresses this check for `_REFERENCE_ROLES` pages, but not
for howto or article pages. This causes a `semantic_structure MED` on
`optimize-spreadsheets-python` (H=1, M=3), preventing it from reaching Grade B (needs M≤2).

Fix: extend the empty-section suppression to any H2 section whose next heading is an H3
(sub-section). A section with sub-sections is not empty — the sub-sections are the content.

## Required spec references

- `specs/09_quality_evaluation.md` (semantic_structure check definition)

## Scope

### In scope
- Modify empty-section check in `check_semantic_structure` to not flag H2 sections
  whose immediately following heading is an H3 (level 3)

### Out of scope
- Changing the terminal-heading check (See Also, References, etc.)
- Changing the duplicate-heading check
- Changing any other check or worker

## Inputs

- `src/launcher/workers/evaluate/checks/semantic_structure.py` — empty-section check (line ~121)

## Outputs

- Fixed semantic_structure check that does not flag H2→H3 subsection structure

## Allowed paths

- plans/taskcards/TC-3889_fix_semantic_structure_subsection_false_positive.md
- src/launcher/workers/evaluate/checks/semantic_structure.py
- tests/unit/workers/evaluate/checks/

### Allowed paths rationale
- semantic_structure.py — contains the empty-section check to fix
- tests/ — test coverage

## Implementation steps

### Step 1: Modify the empty-section check

Change from:
```python
between = "\n".join(lines[line_idx + 1 : next_line]).strip()
if not between:
    findings.append(
        Finding(
            check="semantic_structure",
            message=f"Empty section under heading: '{text}'",
            severity="medium",
            location=slug,
        )
    )
```

To:
```python
between = "\n".join(lines[line_idx + 1 : next_line]).strip()
# H2 sections that go directly to H3 sub-headings are valid structure.
# The sub-headings are the content (same logic used for _REFERENCE_ROLES).
next_is_subsection = (
    i + 1 < len(headings) and headings[i + 1][1] > level
)
if not between and not next_is_subsection:
    findings.append(
        Finding(
            check="semantic_structure",
            message=f"Empty section under heading: '{text}'",
            severity="medium",
            location=slug,
        )
    )
```

### Step 2: Update/add tests

In `tests/unit/workers/evaluate/checks/test_semantic_structure.py`:
- H2 section with H3 subsection (no intro) → NO finding
- H2 section with truly empty body (no content, no sub-headings) → MED finding
- H2 section with intro prose before H3 → NO finding

### Step 3: Run tests

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/evaluate/checks/ -v
```

## Failure modes

### Failure mode 1: Genuinely empty H2 sections stop being flagged

**Detection**: H2 with no content and no subsections passes review
**Resolution**: The guard `not next_is_subsection` only suppresses the check when the
NEXT heading is at a deeper level. Truly empty sections (no subsection) still fire.
**Gate**: test: empty H2 still flagged

### Failure mode 2: H3-under-H2 suppression hides multi-level structure issues

**Detection**: A page with multiple levels of empty sections is under-flagged
**Resolution**: Only the IMMEDIATELY next heading level is checked. If H2→H3→H4 all
have empty intros, H3 with empty intro (next is H4) would also be suppressed.
This is acceptable — subsection chains are valid structure.
**Gate**: Pilot run quality review

### Failure mode 3: Other pages' semantic_structure MEDs change unexpectedly

**Detection**: A page that should have MED no longer does
**Resolution**: Only suppresses when `next_is_subsection` — i.e., the next heading
is at a deeper level than the current heading. This is a narrow exemption.
**Gate**: Full test suite

## Task-specific review checklist

1. [ ] `next_is_subsection` guard added
2. [ ] Suppression only applies when next heading is deeper level
3. [ ] Genuinely empty sections (no subsections) still flagged
4. [ ] Test: H2→H3 not flagged
5. [ ] Test: truly empty H2 still flagged
6. [ ] Tests pass

## Deliverables

1. `src/launcher/workers/evaluate/checks/semantic_structure.py` — empty-section check fixed

## Acceptance checks

1. [ ] `optimize-spreadsheets-python` semantic_structure MED eliminated
2. [ ] All unit tests pass

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Evidence captured: reports/TC-3889/evidence.md

## E2E verification

`optimize-spreadsheets-python` should have M=2 in next pilot run (from M=3).

## Integration boundary proven

**Upstream**: Generate worker produces H2→H3 subsection structure
**Downstream**: check_semantic_structure evaluates empty sections
**Contract**: H2 sections with H3 sub-headings no longer flagged → semantic_structure MED eliminated → C→B
