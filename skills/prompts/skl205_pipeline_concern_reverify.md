---
name: pipeline-concern-reverify
description: Verify whether a targeted fix resolved specific known pipeline concerns — classifies each as RESOLVED, STILL_FAILING, or MASKED with evidence from actual output.
---

# SKL-205: pipeline-concern-reverify

You are verifying whether a targeted fix resolved specific known concerns in
the pipeline output.

## Context

A fix has been applied and you must confirm whether the concerns it targeted
are now resolved. You must classify each concern as RESOLVED, STILL_FAILING,
or MASKED — with evidence from actual output, not inference.

## Required inputs

- Pipeline target (family, subdomain, specific page set)
- List of known concerns (specific — not "quality issues")
- Previous run artifacts (for before/after comparison)

## What to do

1. Run the pipeline for the specified target.

2. For each known concern, inspect the actual generated output:
   - Is the concern now resolved in the output?
   - What specific evidence in the output confirms resolution?
   - Or is the concern still failing? If so, what is the root cause?
   - Or is the concern masked by a different failure that hides it?

3. For each STILL_FAILING concern, determine which layer the problem comes
   from:
   - Input quality (Understand phase)
   - Pipeline logic (worker code)
   - Example extraction or transformation
   - Template behavior
   - Validation gap
   - Missing repository evidence
   - Structural issue in the output

4. Produce fix tasks for remaining failures, ordered from earliest phase to
   latest.

## Output you must produce

- Per-concern classification: RESOLVED / STILL_FAILING / MASKED
- Evidence from actual output for each classification
- For STILL_FAILING: root cause layer and specific fix tasks
- For MASKED: identify the masking failure and fix it first

## Constraints

- Do not rely on assumptions — inspect actual generated output
- Map findings directly to individual concerns — not summary judgements
- Distinguish genuine fix vs masking

## Escalation rules

- If a concern is STILL_FAILING after a fix was applied, escalate to the
  earliest responsible pipeline phase — do not re-apply the same fix
- If a concern is MASKED, fix the masking failure first, then re-run reverify

## Verification

- Each concern is classified as: RESOLVED, STILL_FAILING, or MASKED
- RESOLVED concerns have evidence from actual output, not just inference
