# Artifact Placement Rules (Binding)

**Effective date**: 2026-02-16  
**Applies to**: all agents, orchestrators, scripts, and manual contributors

## Purpose

Prevent repository drift by enforcing deterministic artifact placement and banning root-level clutter.

## Rules

1. Every new file must be placed in an approved directory for its artifact class.
2. Root-level scratch artifacts are forbidden.
3. If no approved directory exists for an artifact class, update this policy first, then add files.
4. Runtime-generated artifacts must be untracked unless explicitly designated as governance evidence.
5. Naming must be explicit and stable; ambiguous names (`temp`, `misc`, `new`) are forbidden.

## Approved Placement Matrix

1. Runtime code: `src/`
2. Tests and test fixtures: `tests/`
3. Implementation/maintenance utilities: `tools/` and `scripts/`
4. Runtime product/pilot configs: `configs/`
5. Tooling and lint config: `config/`
6. Specifications and template contracts: `specs/`
7. Planning/task orchestration docs: `plans/`
8. Auditable evidence and run reviews: `reports/`
9. Local ephemeral outputs: `runs/`, `tmp/`, `.pytest_cache/`, `.ruff_cache/` (ignored)
10. Baseline artifacts: only the canonical baseline root approved by hygiene migration

## Forbidden Root-Level Patterns

1. `temp_*`
2. `*_output*.txt`
3. ad-hoc result dumps (`*.json`, `*.csv`) not part of source/spec/governance contracts
4. database files (`*.db`) except explicitly approved fixtures under `tests/fixtures/`
5. throwaway helper scripts (move to `tools/`/`scripts/` with meaningful names)

## Evidence Placement Rules

1. Agent execution evidence must live under `reports/agents/<AGENT>/<TASK>/run_<YYYYMMDD_HHMMSS>/`.
2. Required run artifacts remain:
   - `plan.md`
   - `changes.md`
   - `evidence.md`
   - `self_review.md`
   - `commands.sh`
   - `artifacts/`
3. Evidence must not be written into root, `docs/`, or `plans/` unless explicitly a planning document.

## Enforcement

1. Local: pre-commit/pre-push hygiene checks reject forbidden placement.
2. CI: hygiene audit blocks merges when placement rules are violated.
3. Review: any PR with new top-level paths requires explicit policy approval.

## Exception Process

1. Open a short policy exception note in `plans/healing/` with rationale and expiry.
2. Get maintainer approval before merging exception-based placement.
3. Remove exceptions once canonical support is added.
