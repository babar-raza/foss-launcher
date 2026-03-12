---
name: multi-plan-consolidate
description: Consolidate two or more overlapping or dependent plan files into a single conflict-free execution strategy with correct ordering, explicit dependencies, and checkpoints.
---

# SKL-203: multi-plan-consolidate

You are consolidating multiple interrelated plan files into a single,
complete, conflict-free execution strategy.

## Context

Two or more plan files exist that overlap, depend on each other, or must be
executed as a coordinated unit. Your job is to read all of them, understand
how they connect, and produce a single consolidated execution strategy that
covers every item from every plan without omission.

## Required inputs

- All plan file paths (you must read each file in full before analysis begins)

## What to do

1. Read every plan file fully. Do not start analysis until all files are read.

2. Identify:
   - How the plans connect to each other
   - Overlapping items (same work described differently)
   - Dependencies (item A must complete before item B)
   - Conflicts (two items describe incompatible behavior)
   - Gaps (work implied but not explicitly described in any plan)
   - Stale items (reference files or phases that no longer exist)

3. Produce a consolidated execution strategy:
   - Correct execution order
   - Which tasks can run in parallel and which must be sequential
   - Explicit dependencies with which prior task must complete first
   - How overlapping items are merged (no intent should be lost)
   - How conflicts are resolved (or flagged if resolution requires operator input)

4. For each major step, define a checkpoint:
   - What artifact or output proves the step completed
   - How to verify the checkpoint before moving to the next step

## Output you must produce

- How the plans relate to each other
- Consolidated execution order
- Parallel vs sequential task groupings
- Dependencies and prerequisites per task
- Gaps, duplications, contradictions (with resolution or flag)
- Checkpoints after each major group with verification method

## Constraints

- Read ALL plan files fully before proposing execution
- Every item from every plan must appear in the consolidated output
- If an item is unclear, resolve it using the codebase — do not skip it
- If two items overlap, merge them without losing intent
- Make all dependencies explicit

## Escalation rules

- If two plans directly contradict each other on the same behavior, stop and
  present the contradiction to the operator for resolution before executing
- If a plan item references a file or phase that no longer exists, note it as
  stale and ask the operator whether to remove or update it — do not silently drop it

## Verification

- Every item from every input plan appears in the consolidated output
- Checkpoints are defined after each major execution group
- Verification method is specified for each checkpoint
