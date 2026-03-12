---
id: TC-3895
title: "Gate hardening: contextual placeholder detection + empty href severity"
status: Done
priority: High
owner: "agent"
updated: "2026-03-09"
tags: [gate, density, artifacts, prompt]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-3895_gate-hardening-placeholder-empty-href.md
  - src/launcher/workers/evaluate/checks/density.py
  - src/launcher/workers/evaluate/checks/artifacts.py
  - src/launcher/prompts/section_writer.txt
evidence_required:
  - plans/taskcards/TC-3895_gate-hardening-placeholder-empty-href.md
---

# Taskcard TC-3895 — Gate hardening: contextual placeholder detection + empty href severity

## Objective

Manual review of the note_python GO run (automated A+B=100%) revealed pages graded A/B that contain "For details, see the documentation" placeholder prose and broken empty-href links. Both passed the automated gates silently. This TC closes those gaps.

## Required spec references

- `src/launcher/workers/evaluate/checks/density.py` — content density gate
- `src/launcher/workers/evaluate/checks/artifacts.py` — artifact pattern gate
- `src/launcher/prompts/section_writer.txt` — LLM generation prompt

## Scope

### In scope
- Add 5 regex patterns for documentation-referral placeholders to density.py
- Escalate empty-href severity from "medium" to "high" in artifacts.py
- Add explicit rule to section_writer.txt forbidding referral-placeholder sentences

### Out of scope
- Changes to grader, go_criteria, or other gates
- Changes to review_prompt.txt (separate concern)

## Inputs

- `density.py` current state
- `artifacts.py` current state
- `section_writer.txt` current state

## Outputs

- Updated `density.py` with `_REFERRAL_PATTERNS` and detection loop
- Updated `artifacts.py` with "high" severity for empty hrefs
- Updated `section_writer.txt` with explicit referral-placeholder prohibition

## Allowed paths

- plans/taskcards/TC-3895_gate-hardening-placeholder-empty-href.md
- src/launcher/workers/evaluate/checks/density.py
- src/launcher/workers/evaluate/checks/artifacts.py
- src/launcher/prompts/section_writer.txt

### Allowed paths rationale
Gate logic and generation prompt only. No model or schema changes needed.

## Implementation steps

### Step 1: Update density.py

Add `_REFERRAL_PATTERNS` tuple and detection loop in the section iteration.

### Step 2: Update artifacts.py

Change empty-href finding severity from "medium" to "high".

### Step 3: Update section_writer.txt

Add explicit referral-placeholder prohibition rule.

### Step 4: Run tests

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -k "density or artifact" -v --tb=short
```

## Failure modes

### Failure mode 1: False positives on legitimate "see also" references

**Detection**: Tests fail on pages with valid cross-references
**Resolution**: Narrow patterns — require "see the [X] documentation" not just "see"
**Gate**: density

### Failure mode 2: empty-href severity change breaks existing tests

**Detection**: test_artifacts tests assert "medium" severity
**Resolution**: Update test assertions to "high"
**Gate**: artifacts

### Failure mode 3: Pattern matches code blocks

**Detection**: Code examples containing "see" trigger false positives
**Resolution**: Ensure density check strips code blocks before pattern matching
**Gate**: density

## Task-specific review checklist

1. [ ] All 5 `_REFERRAL_PATTERNS` patterns are IGNORECASE and bounded to avoid false positives
2. [ ] Pattern matching runs on prose-only text (code blocks stripped)
3. [ ] Each section gets at most 1 finding per section (no duplicate findings for same section)
4. [ ] Empty-href severity is "high" in artifacts.py
5. [ ] section_writer.txt rule is under the existing placeholder prohibition block
6. [ ] All density/artifact tests pass
7. [ ] Docstrings updated for changed functions — N/A (logic additions, no new public functions)
8. [ ] Spec file updated if worker behavior changed — N/A (gate logic only)
9. [ ] Schema `"description"` fields present — N/A (no schema changes)
10. [ ] docs/README.md ownership map — N/A

## Deliverables

1. `density.py` with referral-pattern detection
2. `artifacts.py` with "high" severity for empty hrefs
3. `section_writer.txt` with prohibition rule

## Acceptance checks

1. [ ] Unit test: page with "For details, see the documentation" → HIGH finding from content_density
2. [ ] Unit test: page with "Refer to the official documentation" → HIGH finding
3. [ ] Unit test: page with `[text](` broken link → HIGH finding (not medium)
4. [ ] Unit test: page with normal "see also" cross-reference link → NO referral-pattern finding
5. [ ] Full test suite: 0 failures (PYTHONHASHSEED=0)

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Evidence captured: inline

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -k "density or artifact" -v
```

**Expected results**:
- New tests for referral patterns pass
- Existing tests pass (no regressions)

## Integration boundary proven

**Upstream**: generate worker produces content; linker injects See Also
**Downstream**: evaluate worker calls density and artifacts checks
**Contract**: density.py emits Finding(check="content_density", severity="high") for referral patterns
