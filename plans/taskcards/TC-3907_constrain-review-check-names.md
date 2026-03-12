---
id: TC-3907
title: "Constrain LLM reviewer to only use predefined check names in findings"
status: Done
priority: High
owner: "agent"
updated: "2026-03-09"
tags: [evaluate, llm_review, hallucination, grading]
depends_on: [TC-3886]
allowed_paths:
  - plans/taskcards/TC-3907_constrain-review-check-names.md
  - src/launcher/prompts/review_prompt.txt
evidence_required:
  - reports/TC-3907/evidence.md
---

# Taskcard TC-3907 — Constrain LLM reviewer to only use predefined check names

## Objective

The LLM reviewer (Phase B) invents check names not in the predefined checklist
(e.g., `code_example_presence`, `depth_sufficiency`, `prose_code_balance`,
`broken_link`). These invented findings are counted as HIGH findings by the
grader, incorrectly downgrading pages from B to C or C to D.

Fix: add an explicit constraint in `review_prompt.txt` OUTPUT FORMAT section
that the `check` field in each finding MUST be one of the 10 defined names only.

## Required spec references

- `specs/09_quality_evaluation.md` (LLM review phase definition)

## Scope

### In scope
- Add a MUST-use constraint listing the 10 allowed check names in the OUTPUT FORMAT section
- Immediately after the findings array example

### Out of scope
- Changing check logic, grader, or any other file
- Adding new check names

## Inputs

- `src/launcher/prompts/review_prompt.txt` — OUTPUT FORMAT section (line ~93-102)

## Outputs

- Updated prompt with explicit constraint preventing invented check names

## Allowed paths

- plans/taskcards/TC-3907_constrain-review-check-names.md
- src/launcher/prompts/review_prompt.txt

### Allowed paths rationale
- review_prompt.txt — the only file that needs to change

## Implementation steps

### Step 1: Add constraint after findings example

After the closing `]` of the findings array example and before `"summary"`,
add:

```
  IMPORTANT: The "check" field in each finding MUST be one of these exact values:
  factual_accuracy | canonical_import | completeness | heading_quality |
  code_correctness | content_density | tone_and_style | api_consistency |
  audience_appropriateness | code_formatting
  Do NOT invent new check names. Any finding with a check name not in this list is invalid.
```

### Step 2: Verify prompt renders correctly

Confirm no `{{}}` escaping issues by reading the file.

## Failure modes

### Failure mode 1: LLM ignores the constraint

**Detection**: Post-run analysis still shows invented check names
**Resolution**: Move the constraint to BEFORE the checklist items and repeat it
**Gate**: Pilot run analysis

### Failure mode 2: Constraint breaks JSON structure in prompt

**Detection**: `{` and `}` escaping issues in template rendering
**Resolution**: The constraint is plain text outside the JSON block, no escaping needed
**Gate**: Read file after edit to verify

### Failure mode 3: Grades become too lenient

**Detection**: A+B rate jumps but D+F pages also have no findings
**Resolution**: The constraint only removes invented names; real failures still fire
**Gate**: Pilot run quality review

## Task-specific review checklist

1. [ ] Constraint added after findings example
2. [ ] Lists all 10 check names explicitly
3. [ ] States "Do NOT invent new check names"
4. [ ] No escaping issues in the template
5. [ ] Constraint positioned prominently (not buried)
6. [ ] Pilot run launched to validate

## Deliverables

1. `src/launcher/prompts/review_prompt.txt` — constraint added

## Acceptance checks

1. [ ] `code_example_presence` check name no longer appears in pilot run evaluate artifacts
2. [ ] `depth_sufficiency` check name no longer appears
3. [ ] A+B rate ≥50% in pilot run with all fixes combined

## Self-review

### Verification results
- [ ] File edited correctly
- [ ] Evidence captured: reports/TC-3907/evidence.md

## E2E verification

Fresh pilot run should have 0 invented check names in evaluate_checkpoint.json.

## Integration boundary proven

**Upstream**: LLM reviewer generates findings JSON
**Downstream**: `grader.py` counts HIGH/MED findings per check
**Contract**: Only predefined check names appear → grader counts correctly → grades accurate
