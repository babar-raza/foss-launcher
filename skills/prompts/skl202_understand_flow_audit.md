---
name: understand-flow-audit
description: Trace whether understanding_bundle.json fields are fully and correctly consumed by downstream workers (Generate, Evaluate, Plan) — field-by-field handoff audit.
---

# SKL-202: understand-flow-audit

You are tracing whether the data produced by the Understand phase is fully
and correctly consumed by downstream workers.

## Context

The Understand worker produces `understanding_bundle.json`. Downstream workers
(Generate, Evaluate, and the Plan phase inside Understand) consume fields from
this bundle. This audit verifies that no important field is dropped, ignored,
transformed incorrectly, or left unused.

Do not stop at a surface review. Trace field-by-field from bundle → worker
input → prompt → output.

## Required inputs

- `understanding_bundle.json` for the run being audited
- At minimum 2 downstream worker implementations (Generate and Evaluate are
  the minimum; Plan is also important)
- Phase store artifacts for the run being audited

## What to do

1. List every top-level field in `understanding_bundle.json`:
   `product`, `repo`, `richness_tier`, `api_surface`, `claims`, `snippets`,
   `product_evidence`, `keyword_research`, and any others present.

2. For each field, trace:
   - Which downstream worker receives it
   - Whether the full field is passed or only a subset
   - Whether the mapping from bundle field to worker input is correct
   - Whether the worker actually uses the field in its prompts or validation

3. For each of the two minimum workers (Generate and Evaluate), produce a
   table with columns:
   `Bundle field | Passed? | How consumed | Gaps or errors`

4. Identify every useful Understand field that is dropped, partially consumed,
   or consumed incorrectly.

## Output you must produce

- Per-worker assessment: inputs received, completeness of mapping, gaps
- Assessment of whether each important field is being used effectively
- Concrete fix tasks for incomplete or incorrect consumption, ordered correctly

## Constraints

- Audit actual handoff code and phase store artifacts — not just specs
- Do not stop at surface review — go field-by-field

## Escalation rules

- If a field is dropped at the worker boundary and fixing it requires a schema
  change, stop and create a taskcard before proceeding (protected path)
- If downstream consumption is correct but output is still wrong, escalate to
  SKL-201 — the problem is in Understand itself, not the handoff

## Verification

After fixes are applied:
- Every field in `understanding_bundle.json` that should influence content
  reaches the relevant downstream prompt or validation
- Re-run and verify no important field is silently dropped in the new output
