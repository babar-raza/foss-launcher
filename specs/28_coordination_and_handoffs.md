# Coordination, Handoffs, and Decision Loops (authoritative)

## Purpose
Many specs define *what* artifacts must exist, but not *how* workers coordinate and hand off work.
This document defines the production-grade coordination model so implementers do not invent missing glue.

This document is binding.

## Workforce model (control plane vs data plane)

### Control plane: Orchestrator
The Orchestrator is the only component allowed to:
- move the run through states (see `specs/state-graph.md`)
- enqueue work items (workers)
- decide routing (fan-out, fix loop)
- mark a run FAILED or DONE

The Orchestrator MUST NOT:
- author long-form content for pages (writers do that)
- modify the site worktree directly (only W6 LinkerAndPatcher may do that)

### Data plane: Workers
Workers are deterministic, idempotent jobs with explicit artifact I/O (see `specs/21_worker_contracts.md`).
Workers communicate ONLY via:
1) **artifacts on disk** under `runs/<run_id>/`
2) **local event log** records (see `specs/11_state_and_events.md`)

No worker-to-worker “chat memory” is allowed.

## Handoff mechanism

### Artifact registry (single handoff surface)
Every worker MUST:
1) read declared inputs from the run folder
2) write declared outputs to the run folder
3) emit `ARTIFACT_WRITTEN` events for every output (name, sha256, schema_id)

The Orchestrator MUST maintain an **artifact index** inside the run snapshot:
- artifact_name -> { path, sha256, schema_id, writer_worker, ts }

### Work item contract (required)
The Orchestrator MUST represent every worker execution as a WorkItem record in the snapshot:

- `work_item_id` (stable): `{run_id}:{worker}:{attempt}:{scope_key}`
- `worker` (e.g., `W5.SectionWriter`)
- `scope_key` (required when parallel): section name, page slug, or gate name
- `inputs`: list of artifact names and/or fixed paths
- `outputs`: list of artifact names and/or fixed paths
- `attempt`: integer starting at 1
- `status`: queued | running | finished | failed | skipped
- `started_at`, `finished_at`
- `error` (if failed): normalized error object (see `specs/24_mcp_tool_schemas.md`)

**Binding rule:** a WorkItem MUST be re-runnable without changing its meaning:
same (worker, scope_key, attempt, inputs sha256s) => same outputs sha256s.

## Deterministic routing and decisions

### Decision ownership (no ambiguity)
All “choices” are owned by specific workers:

| Decision | Owner | Output artifact | Determinism rule |
|---|---|---|---|
| Repo adapter selection | W1 RepoScout | `repo_inventory.json` (`repo_profile.adapter_id`) | scoring rules in `specs/26_repo_adapters_and_variability.md` |
| Claim acceptance vs inference | W2 FactsBuilder | `product_facts.json`, `evidence_map.json` | `allow_inference=false` forbids speculative claims |
| Page inventory and template selection | W4 IAPlanner | `page_plan.json` | template registry + stable ordering rules |
| Snippet inclusion policy | W3 SnippetCurator | `snippet_catalog.json` | only snippets with provenance + stable tags |
| What to fix next | Orchestrator | N/A (uses `validation_report.json`) | pick first blocker/error by stable ordering in `specs/10_determinism_and_caching.md` |
| Patch strategy | W8 Fixer | `patch_bundle.delta.json` or updated `drafts/...` | minimal diff principle + gate-specific rules in `specs/08_patch_engine.md` |

### Loop policy (VALIDATING → FIXING → VALIDATING)
The Orchestrator MUST implement an explicit loop:

1) Run W7 Validator to produce `validation_report.json`.
2) If `ok=true`: advance to READY_FOR_PR.
3) If `ok=false`:
   - select **exactly one** issue to fix (first by deterministic order)
   - enqueue W8 Fixer with `scope_key=issue_id`
   - re-run W7 Validator
4) Stop conditions (any triggers FAIL):
   - attempts >= `run_config.max_fix_attempts`
   - Fixer produced no diff AND issue still present
   - Fix introduces new blocker in a different gate

**Binding rule:** Fixing is always single-issue-at-a-time (no batch fixes) to preserve determinism and debuggability.

### Plan revision policy (re-plan loop)
Re-planning is allowed only when validation fails due to missing planned pages or impossible requirements.

Trigger conditions:
- Validator emits `ISSUE_OPENED` with `gate=PlanCompleteness` or `gate=TemplateCompatibility`
- The issue is a blocker and cannot be resolved by a patch-only fix

In that case the Orchestrator MUST:
- enqueue W4 IAPlanner again (attempt+1)
- invalidate all drafts (`drafts/**`) by writing an `ISSUE_OPENED` note and moving them to `drafts/_obsolete/<attempt>/...`
- re-run drafting fan-out

## Concurrency model (battle-tested, safe by construction)

### Parallel drafting fan-out
W5 SectionWriter runs in parallel for each section.
Parallel-safe write rule:
- writers may only write under `runs/<run_id>/drafts/<section>/`
- writers may not modify the site worktree
- writers may not write shared artifacts (only section-local drafts)

### Single-writer critical section
Only W6 LinkerAndPatcher may modify the site worktree and it MUST:
- apply patches in deterministic order
- write `patch_bundle.json`
- emit `ARTIFACT_WRITTEN` for the patch bundle
- update `diff_report.md` after patch application

### Resource limits
The Orchestrator MUST enforce:
- bounded parallelism (configurable)
- per-worker timeout defaults (configurable)
- provider rate limits and retry/backoff (see `specs/25_frameworks_and_dependencies.md`)

## Escalation and failure
A run MUST transition to FAILED when any of these happen:
- required inputs are missing for any worker
- schemas fail validation and cannot be regenerated deterministically
- uncited claims remain after Fix loop exhaustion
- commit service rejects changes (policy or allowed_paths violation)

On failure the system MUST still:
- flush the local event log
- publish telemetry with final status
- write a human-readable `runs/<run_id>/reports/failure_summary.md`

## Acceptance
- A developer can implement coordination with no guesswork.
- Every decision has a single owner and deterministic rule.
- All loops and stop conditions are explicit and testable.
