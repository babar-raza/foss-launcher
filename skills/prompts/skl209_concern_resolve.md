---
name: concern-resolve
description: Find the best generic solution for each remaining pipeline failure root cause after a healing pass — classifies, ranks, and produces an ordered fix plan without regressing previous fixes.
---

# SKL-209: concern-resolve

You are finding the best possible generic solution for each remaining failure
root cause, without undoing previous fixes.

## Context

Known concerns remain after a healing pass. The cause type for each is known
(RUNTIME_FAILED, MISSING, COMPILE_FAILED, FINAL_REVIEW_FAILED, INFRA_BLOCKED).
Your job is to find solutions that work across all families, not just one.

## Required inputs

- List of remaining failures with root causes
- Current pipeline code and check implementations
- Previous fix history (what was already applied)

## What to do

1. For each remaining concern:
   - Confirm the actual root problem (re-verify, do not assume the prior
     diagnosis is complete)
   - Classify it as one or more of: system design gap / deterministic repair
     gap / content-source gap / validation gap / infrastructure gap
   - Determine whether a generic fix or a local fix is appropriate
   - Identify risks if the fix is implemented poorly

2. Propose the best solution for each concern:
   - Preferred solution
   - Alternative options where relevant
   - Your recommendation and why
   - Expected effect on scores and concern clearance

3. Identify generic hardening opportunities:
   - Fixes that would benefit all families (e.g., BCL allow-list expansion,
     stronger framework-wrapper filtering, improved fixture readiness checks)

4. Produce an execution plan:
   - Smallest practical tasks
   - Correct order (system-level generic fixes first)
   - What can be solved at the system level before targeting local issues
   - What requires source-content correction
   - What should remain rejected rather than auto-fixed

## Output you must produce

- Issue-by-issue assessment with classification
- Best-solution plan per issue with options and recommendation
- Generic hardening opportunities
- Ordered execution plan

## Constraints

- Generic fixes before local patches
- Do not force resolution when source content is genuinely broken
- Do not use automated fixes for source-content issues
- Do not regress previous fixes

## Escalation rules

- FINAL_REVIEW_FAILED concerns from broken source content must not be auto-fixed
  — escalate to operator for source correction
- If fixing one concern introduces a regression in a previously passing concern,
  stop and re-analyse — do not apply partial fixes

## Verification

- Every solution has a defined verification method
- After applying fixes, confirm each RESOLVED concern with evidence from actual output
- No previously passing concerns have regressed
