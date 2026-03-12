---
name: phase-store-diagnose
description: Review the phase_store for a failed pipeline run to identify the first phase where quality degrades — produces root cause analysis and a fix plan starting from that phase.
---

# SKL-206: phase-store-diagnose

You are reviewing the phase_store for the most recent run to identify the
first phase where quality meaningfully degrades.

## Context

Content quality is poor and the root cause phase is not yet known. You must
inspect each phase in sequence, compare outputs, and isolate the primary
culprit. Do not patch later phases until the first culprit is confirmed.

## Required inputs

- `phase_store/` directory for the most recent run
- All phase output artifacts:
  - `intake_bundle.json`
  - `understanding_bundle.json`
  - `content_manifest.json`
  - `evaluation_report.json`

## What to do

1. For each phase in sequence (Intake → Understand → Generate → Evaluate):
   - What does this phase receive as input?
   - What does it produce as output?
   - Is the output correct, complete, and useful?
   - Does quality improve, stay flat, or degrade at this point?
   - What specific defects, omissions, distortions, or weak transformations
     are introduced here?

2. Identify the first phase where quality meaningfully fails. This is the
   primary culprit.

3. For the primary culprit phase, produce a deeper review:
   - What exactly is going wrong?
   - Which artifacts or fields show the failure?
   - Is the issue caused by: missing input, weak transformation, dropped data,
     bad assumptions, schema mismatch, prompt weakness, or another design flaw?
   - Why is this phase the main problem maker?

4. Produce a concrete fix plan starting from the primary culprit:
   - Smallest practical tasks
   - Correct sequence
   - Root-cause fixes before secondary cleanup
   - Verification method using actual phase outputs

## Output you must produce

- Phase-by-phase assessment with quality verdict for each phase
- Identification of the first meaningfully failing phase with evidence
- Root cause analysis of that phase (specific artifacts and fields)
- Fix plan starting from that phase, sequenced correctly

## Constraints

- Inspect actual stored outputs — not only logs
- Do not move to later-phase analysis until the first culprit is confirmed
- Later-phase patching is not a substitute for fixing the first failing phase

## Escalation rules

- If the culprit phase is Intake, fix Intake before diagnosing Understand or
  Generate
- If quality degrades in every phase equally, the root cause is likely
  Understand output quality — escalate to SKL-201 before further diagnosis

## Verification

- After applying phase fixes, re-run the pipeline
- Verify that the defect introduced by the culprit phase is no longer present
  in its output
