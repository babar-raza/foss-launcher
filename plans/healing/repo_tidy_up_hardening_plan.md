# Architectural Healing Plan: Repo Tidy-Up and Hygiene Hardening

**Date**: 2026-02-16  
**Status**: PROPOSED  
**Scope**: Repository structure, tracked artifact hygiene, and repeatable cleanup automation

## Executive Summary

This plan standardizes repository hygiene so the project stays auditable without accumulating root-level clutter and accidental artifacts.

Current signals in this repo show:
1. Tracked ad-hoc temporary artifacts in the root (for example `temp_*`, `link_check_*.txt`, `telemetry.db`).
2. Overlapping directory names with unclear ownership (`config/` vs `configs/`, `baseline/` vs `baselines/`).
3. High local workspace growth from runtime artifacts (`runs/` is very large locally, though ignored).
4. Governance evidence is required and tracked (`reports/`), but retention and placement rules need stronger boundaries.

## Objectives

1. Make root directory purpose-driven and low-noise.
2. Define canonical locations for config, baselines, evidence, and temporary outputs.
3. Prevent reintroduction of ad-hoc temp artifacts into Git.
4. Enforce binding artifact-placement rules for all agents.
5. Keep auditability guarantees intact for `reports/` and planning docs.
6. Add a one-command hygiene audit and optional local cleanup flow.

## Non-Goals

1. Rewriting worker architecture.
2. Removing required governance evidence from version control.
3. Purging Git history in this phase.

## Baseline Findings (2026-02-16)

1. Root includes tracked temporary-like files:
   - `temp_analyze_broken_links.py`
   - `temp_broken_links_categorized.json`
   - `temp_link_check_results.json`
   - `temp_link_checker.py`
   - `temp_links.txt`
   - `temp_links_output.txt`
   - `temp_md_files.txt`
   - `link_check_output.txt`
   - `link_check_full_output.txt`
   - `telemetry.db`
2. Top-level overlap requiring normalization:
   - `config/` and `configs/`
   - `baseline/` and `baselines/`
3. Local size profile indicates runtime sprawl risk:
   - `runs/` very large (local, ignored)
   - `.venv/` large but expected
   - `reports/` intentionally tracked and sizeable

## Healing Principles

1. Keep evidence explicit, but scoped to dedicated directories.
2. Keep runtime byproducts untracked and easy to purge.
3. Use automation and CI checks instead of manual discipline.
4. Prefer additive migration with compatibility shims before hard removal.

## Binding Agent Artifact-Placement Rules (Prevention Layer)

These rules are mandatory for all agent work and are designed to prevent future tidy-up waves.
Canonical policy document: `plans/policies/artifact_placement_rules.md`.

### Rule Set

1. New files may only be created in approved directories for their artifact class.
2. Root-level ad-hoc outputs are forbidden (`temp_*`, `*_output.txt`, scratch scripts, DB files, one-off JSON dumps).
3. Every generated artifact must have one of two lifecycles:
   - tracked governance evidence, or
   - local runtime artifact (ignored by Git).
4. Names must communicate intent:
   - use `run_<timestamp>` for execution evidence
   - avoid `temp`, `misc`, `new`, `test2` style names
5. If an artifact type has no designated home, the agent must stop and add policy placement before creating it.

### Placement Matrix (Agent Contract)

1. Production source code: `src/`
2. Test code and fixtures: `tests/`
3. Executable utilities and maintenance scripts: `tools/` or `scripts/`
4. Product/pilot run configuration: `configs/`
5. Tooling/policy config (linters, allowlists, lock policy): `config/`
6. Specifications and templates: `specs/`
7. Planning documents and taskcards: `plans/`
8. Auditable execution evidence and reviews: `reports/`
9. Local ephemeral run outputs and working files: `runs/`, `tmp/`, caches (ignored)
10. Baseline datasets and comparison snapshots: canonicalized in Phase 2, then only one approved root

### Forbidden Placement Examples

1. `telemetry.db` at repo root.
2. `temp_*.py` and `temp_*.json` at repo root.
3. Validation/log dump files at repo root (`*output*.txt`, ad-hoc result JSON).
4. Agent evidence under `docs/`, `plans/`, or root when it belongs under `reports/`.

### Required Agent Workflow Checks

1. Before writing files, agent labels each output as `SOURCE`, `GOVERNANCE`, `GENERATED_TRACKED`, or `GENERATED_UNTRACKED`.
2. Agent verifies path against placement matrix.
3. Agent runs hygiene audit before finalizing.
4. PR must include a placement declaration for new top-level paths (if any).

## Phase 0: Inventory and Classification Contract

### Deliverables
1. Add a short contract doc: `docs/repo_hygiene_contract.md`.
2. Classify every top-level path as one of:
   - `SOURCE` (code/specs/tests)
   - `GOVERNANCE` (plans/reports/docs)
   - `GENERATED_TRACKED` (only if explicitly approved)
   - `GENERATED_UNTRACKED` (runtime/temp/local)
3. Record path ownership and allowed file patterns.
4. Add a policy reference section in `AGENTS.md` and agent prompts pointing to this placement contract.
5. Adopt and publish `plans/policies/artifact_placement_rules.md` as the binding artifact placement policy.

### Exit Criteria
1. Every top-level directory has an owner and lifecycle category.
2. Contract is linked from `README.md` and/or `DEVELOPMENT.md`.
3. Agent instructions include explicit "artifact placement required" language.

## Phase 1: Root Artifact Triage and Relocation

### Actions
1. Move historical link-analysis artifacts from root into a dated archival folder under `reports/forensics/` (or `docs/_audit/` if preferred by maintainers).
2. Move one-off helper scripts with durable value into `tools/` or `scripts/` and rename away from `temp_*`.
3. Remove root-level outputs that are reproducible and non-canonical.
4. Decide policy for `telemetry.db`:
   - keep only as local runtime artifact (preferred), or
   - migrate to curated fixture under `tests/fixtures/` if tests truly require a committed DB sample.

### Exit Criteria
1. No `temp_*` files remain at repository root.
2. No root-level analysis outputs remain outside approved docs/report locations.
3. `telemetry.db` policy is explicit and implemented.

## Phase 2: Directory Canonicalization

### Actions
1. Choose one canonical config root (`config/` or `configs/`) and one canonical baseline root (`baseline/` or `baselines/`).
2. Create migration map and compatibility period:
   - temporary read fallback (if code reads both)
   - deprecation notice in docs
3. Update all references in:
   - code
   - tests
   - docs
   - plans

### Exit Criteria
1. Duplicate top-level naming pairs are resolved.
2. Reference scan confirms no stale paths remain.

## Phase 3: Guardrails and Automation

### Actions
1. Add `tools/repo_hygiene_audit.py` to check:
   - forbidden root file patterns (`temp_*`, raw `*.db`, ad-hoc outputs)
   - duplicate top-level category violations
   - tracked file placement for reports/evidence
2. Add CI gate (non-blocking for first rollout window, then blocking).
3. Add local command target in `Makefile`:
   - `make hygiene-audit`
   - optional `make hygiene-clean` for local ignored artifacts (`runs/`, `tmp/`, caches) with safe prompts.
4. Add pre-commit/pre-push hook checks for forbidden root artifacts.
5. Add a "new top-level path" CI rule that fails unless path is allowlisted in the hygiene contract.
6. Add a lightweight artifact classifier check in CI:
   - sample rule: files under `reports/` cannot be imported by runtime code
   - sample rule: files under `scripts/` and `tools/` must not be named `temp_*`

### Exit Criteria
1. CI reports hygiene results on every PR.
2. New forbidden artifacts are blocked from merge.
3. New top-level directories cannot be introduced accidentally.

## Phase 4: Retention Policy for Large Local and Evidence Trees

### Actions
1. Define retention windows:
   - `runs/` local cleanup policy (for example age or count based)
   - log/artifact pruning policy for non-essential outputs
2. Add cleanup utility (for example `tools/prune_runs.py`) with dry-run mode.
3. Document operator workflow for safe cleanup.

### Exit Criteria
1. Local workspace growth can be controlled with one documented command.
2. Cleanup does not remove required governance evidence.

## Rollout Plan

1. Week 1: Phase 0 and Phase 1.
2. Week 2: Phase 2 migration and reference updates.
3. Week 3: Phase 3 audit tooling + CI in report-only mode.
4. Week 4: Phase 4 retention utilities and CI blocking enforcement.

## Risks and Mitigations

1. Risk: Removing files still referenced by docs/tests.
   - Mitigation: run reference scans before deletion; migrate then delete.
2. Risk: Over-aggressive hygiene checks block valid workflows.
   - Mitigation: start with report-only CI and tune allowlist.
3. Risk: Confusion during directory migration.
   - Mitigation: compatibility window plus explicit deprecation timeline.

## Verification Plan

1. `git ls-files` audit confirms root cleanup targets are gone or relocated.
2. `rg` path scans confirm no stale `config(s)` and `baseline(s)` references.
3. `python tools/repo_hygiene_audit.py` passes locally and in CI.
4. `python tools/validate_swarm_ready.py` still passes after migration.
5. Simulated bad-placement PR (test branch) is rejected by hooks/CI.

## Definition of Done

1. Root directory contains only intentional source/governance files.
2. Canonical paths are documented and enforced.
3. Hygiene audit exists, is documented, and runs in CI.
4. All agent instructions include binding artifact-placement rules.
5. Runtime artifact retention is documented and automatable.
6. No regression in required evidence/governance workflows.
