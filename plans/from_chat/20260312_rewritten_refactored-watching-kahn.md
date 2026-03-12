# Current Recovery Plan for Scout and Understand

**Plan type**: Rewritten execution plan
**Source replaced**: `C:\Users\prora\.claude\plans\refactored-watching-kahn.md`
**Date**: 2026-03-12
**Branch**: `v2`

---

## Executive Summary

The original `refactored-watching-kahn.md` was directionally useful, but it is no longer current enough to execute as written. Its two biggest assumptions are now false: post-redesign pilots have already been run, and the named confidence-override bug is no longer the active failure mode. The repo has moved past "run the first pilot and verify fact binding exists" into a later stage where the remaining work is narrower and more concrete.

The current picture is mixed rather than linear. One recent 3D Python pilot reached `53%` A+B, `16%` D+F, and `2` critical findings, while a later run regressed to `16%` A+B, `11%` D+F, and `1` critical finding. That means the immediate problem is not lack of evidence; it is instability plus a smaller set of active defects. The plan now needs to prioritize stabilizing the pipeline, fixing the remaining `understand` leaks that still surface invalid API evidence, and tightening `generate` so pages stop going off-topic or collapsing into thin placeholder sections.

Format coverage still matters. The latest promoted `understand.json` still shows only five supported formats for 3D (`COLLADA`, `FBX`, `GLTF`, `OBJ`, `STL`). That remains a real ceiling on format-related coverage, but it is no longer the first action. The current evidence says the faster path to a passing pilot is: lock a stable baseline, eliminate the known `understand` leaks, fix `generate` routing and completeness failures, then return to format-matrix expansion if it is still limiting quality.

---

## Current Evidence Snapshot

### What is already proven

- Post-redesign pilots already exist. This is not a pre-pilot state.
- Fact-binding validation is active in production runs.
- Low-confidence unbound claims are being downgraded and dropped before generation.
- The active failure set is now split between `understand` and `generate`, not concentrated only in format extraction.

### Current measured signals

- Run `260312_162917_3d_python_b5ee`: `53%` A+B, `16%` D+F, `2` critical, `NO_GO`
- Run `260312_170705_3d_python_301a`: `16%` A+B, `11%` D+F, `1` critical, `NO_GO`
- Latest promoted 3D `understand.json`: `supported_formats = 5`
- Fact-binding evidence from `260312_162917_3d_python_b5ee`:
  - `bound_claims = 6`
  - `unbound_claims_downgraded = 23`
  - `low_confidence_claims_dropped = 23`

### Current dominant defect classes

- `understand`
  - invalid API behavior still leaking into evidence or downstream claims
  - examples such as `scene.root_node.child_nodes.add(mesh)`
  - unknown or unsupported identifiers such as `VertexElement`
  - backlog note also flags option/settings leakage like `ObjLoadOptions`, `ObjSaveOptions`, `flip_coordinate_system`, and `scale`
- `generate`
  - `claim_coverage` and `completeness` critical failures on `api-overview` and `use-cases`
  - repeated thin or empty "Best Practices" sections
  - route inconsistency and off-topic page bodies
  - boilerplate or test-like content appearing instead of user-facing docs

---

## What Is Stale in the Original Plan

### Stale item 1: "Run a pilot first"

That step has already been completed multiple times. The current task is to reason from the existing pilots, not to treat the repo as unmeasured.

### Stale item 2: "Check whether `llm_unbound` is missing from `_CONFIDENCE_BY_SOURCE`"

That is no longer the live code path. Unbound claims are now rewritten to `llm_fallback`, and the downgrade/drop pipeline is visibly working in run artifacts.

### Stale item 3: "Format matrix is the single highest-priority technical gap"

The format matrix is still thin, but the live evidence shows more urgent blockers ahead of it: unstable 3D pilot output, specific `understand` API-evidence leaks, and `generate` pages that ignore assigned claims or drift off-topic.

### Stale item 4: "Scout is the main phase under review"

Scout is not the current bottleneck. The active blockers are downstream of Scout unless new evidence proves otherwise.

---

## Revised Goal

Move from unstable `NO_GO` pilots to repeatable `GO`-ready 3D Python pilots by fixing the still-active `understand` and `generate` defects first, while preserving the format-matrix expansion as a secondary evidence-quality lane rather than the first step.

---

## Revised Priority Order

1. Stabilize the pilot baseline and regression story.
2. Eliminate active `understand` evidence leaks that still create invalid API claims.
3. Fix `generate` misrouting, claim omission, and placeholder-page behavior.
4. Fix systemic section-thinness and empty "Best Practices" blocks.
5. Revisit format-matrix expansion if completeness or format coverage is still capped after Steps 1-4.

---

## Detailed Execution Plan

### Step 0: Lock a stable baseline before more code changes

The repo has enough pilot data to act, but the last two 3D runs diverged sharply. Before starting the next protected-path fix, anchor the work on a stable comparison set instead of whichever run is most convenient.

**Actions**

- Compare the two most recent full 3D Python runs plus the current promoted `phase_store` snapshot.
- Record a short regression table for:
  - A+B rate
  - D+F rate
  - CRITICAL count
  - top 3 root-cause buckets by responsible worker
- Decide whether the newest run is:
  - the new working baseline, or
  - a regression/outlier that must be explained before further tuning

**Why this is first**

Without this step, the team will keep optimizing against moving targets and may misclassify noise as progress.

**Acceptance**

- A written regression table exists for the latest 3D pilots.
- The next implementation task names a single baseline run and explains why.

---

### Step 1: Fix the active `understand` leaks

The current `understand` problems are no longer abstract. Recent evaluations already identify recurring invalid API evidence patterns. That means the next work should start from exact failing identifiers and code patterns, not from broad prompt speculation.

**Primary targets**

- invalid collection/method behavior such as `child_nodes.add(...)`
- identifiers not present in the known API surface such as `VertexElement`
- option/settings leakage noted in backlog evidence:
  - `ObjLoadOptions`
  - `ObjSaveOptions`
  - `flip_coordinate_system`
  - `scale`

**Method**

- inspect the latest 3D `understand` bundle and the run-local artifacts for the failing pages
- trace each bad identifier or method shape back to its source:
  - API extraction
  - deterministic claim harvesting
  - contradiction resolution
  - evidence normalization
  - snippet-to-claim linkage
- fix only the root cause
- add regression tests for each distinct leak class

**Do not do**

- do not reopen the old `llm_unbound` confidence issue
- do not patch generated markdown as a substitute for fixing `understand`

**Acceptance**

- rerun shows the targeted `understand` findings removed or materially reduced
- no recurrence of the fixed leak patterns in generated pages
- regression tests fail without the fix and pass with it

---

### Step 2: Fix `generate` pages that ignore assigned claims or go off-topic

The strongest current `generate` failures are not subtle quality nits. They are structural misses: pages with zero meaningful claim coverage, unrelated test-style content, and route-topic drift.

**Primary targets**

- `api-overview`
- `use-cases`
- any page failing `claim_coverage`, `completeness`, or `route_consistency`

**Method**

- inspect the assigned claims and page briefs for the failing pages
- compare them against the generated markdown and the page-specific prompt inputs
- determine whether the defect is caused by:
  - bad claim routing
  - missing claim-to-section mapping
  - weak section instructions
  - generic fallback prose
  - test/example snippets overwhelming user-facing explanation
- fix the generator or planner source of the problem

**Acceptance**

- zero `claim_coverage` critical findings
- zero `completeness` critical findings
- route-consistency failures removed from the targeted pages

---

### Step 3: Fix the repeated thin-section pattern

Even when pages are on-topic, the system still produces thin sections, especially empty or near-empty "Best Practices" blocks. This is now a cross-page generation problem and should be treated as one.

**Primary targets**

- repeated empty "Best Practices" sections
- bullet-only sections with no explanatory prose
- placeholder headings like "Overview" or "Code Examples" with weak narrative

**Method**

- identify the common template or prompt path used by the affected page families
- strengthen the minimum prose expectations at the source
- ensure section instructions require explanation, not only bullets or code blocks

**Acceptance**

- targeted rerun removes the repeated zero-word "Best Practices" failures
- affected pages meet content-density and structure checks without manual editing

---

### Step 4: Reassess format-matrix expansion after the above fixes

Format extraction still looks thin for 3D, but it should be addressed after the more immediate `understand` and `generate` failures unless new evidence proves it is the blocker for current critical pages.

**Current state**

- promoted 3D `supported_formats` still equals 5

**When to prioritize this step**

- if format-related pages remain incomplete after Steps 1-3
- if `understand` still lacks enough verified format facts to support useful content
- if generated format claims remain narrow but otherwise accurate

**Preferred direction**

- expand deterministic extraction where the repo actually stores format evidence
- scan constants, docstrings, README tables, and non-standard enum shapes only if the repo evidence supports those paths
- keep format expansion evidence-bound

**Acceptance**

- increase verified 3D supported formats from 5 to at least 10 before declaring the lane healthy
- stretch target: 15 verified formats if the repo genuinely exposes them

---

## Guardrails

- Do not treat "no pilot exists" as a blocker. That is false now.
- Do not spend time on the superseded `llm_unbound` mapping issue.
- Do not shift effort back to generic Scout cleanup unless current evidence points there.
- Do not patch output files directly to hide upstream defects.
- Every protected-path change still requires a taskcard, regression test, and doc freshness review where applicable.

---

## Evidence to Capture After Each Step

- latest run ID
- `evaluate_checkpoint.json`
- relevant `events.ndjson` excerpts
- 2-3 representative generated pages
- exact failing identifiers or claims before the fix
- exact post-fix evidence that those patterns are gone or reduced
- AG-018 comparison against the two most recent prior runs

---

## Exit Criteria

The plan is complete only when all of the following are true:

- two consecutive 3D Python pilots meet the current GO thresholds, or one passes and the next confirms no regression
- `CRITICAL findings = 0`
- A+B rate meets or exceeds the configured threshold
- D+F rate stays within the configured threshold
- no known active `understand` leak class remains unowned
- no page still fails because it ignores assigned claims or drifts off-topic

If the repo cannot reach `GO` within the current lane, the output must be a narrower follow-up plan with the exact blocker, its owner, and the evidence proving why it remains.
