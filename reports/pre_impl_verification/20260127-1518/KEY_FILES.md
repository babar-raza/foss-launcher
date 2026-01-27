# Key Files Inventory (Authoritative Starting Points)

**Verification Run**: 20260127-1518
**Date**: 2026-01-27
**Orchestrator**: Pre-Implementation Verification Supervisor

---

## Authority Order (Binding)

1. **Specs** (`specs/**/*.md`) — PRIMARY AUTHORITY
2. **Requirements** (extracted from README, docs, specs) — REQUIREMENTS SOURCE
3. **Schemas** (`specs/schemas/*.schema.json`) — ENFORCE SPECS
4. **Gates/Validators** (`tools/validate_*.py`, `src/launch/validators/**`) — ENFORCE SPECS & SCHEMAS
5. **Plans/Taskcards** (`plans/**`, `plans/taskcards/**`) — OPERATIONALIZE SPECS

---

## Root-Level Authority Documents

### Requirements & High-Level Guidance
- `README.md` — System overview, quick start, swarm coordination
- `CONTRIBUTING.md` — Development rules, ground rules, PR process
- `TRACEABILITY_MATRIX.md` — Root-level requirement→spec→taskcard mapping (24 REQ entries)
- `GLOSSARY.md` — Terminology definitions
- `ASSUMPTIONS.md` — Documented assumptions
- `OPEN_QUESTIONS.md` — Unresolved questions
- `DECISIONS.md` — Design decisions

### Binding Specifications (Primary Authority)
- `specs/README.md` — Spec index and overview
- `specs/00_overview.md` — System overview
- `specs/01_system_contract.md` — Core system contract
- `specs/00_environment_policy.md` — .venv policy (mandatory)
- `specs/34_strict_compliance_guarantees.md` — 12 guarantees (A-L)
- All `specs/*.md` files (00-34, binding unless marked REFERENCE)

### Schemas (Enforcement Contracts)
- `specs/schemas/README.md` — Schema index
- `specs/schemas/*.schema.json` — JSON Schema Draft 2020-12 contracts
  - Key schemas: `run_config.schema.json`, `validation_report.schema.json`, `issue.schema.json`, `pr.schema.json`, `ruleset.schema.json`, `product_facts.schema.json`

### Plans & Taskcards (Implementation Operationalization)
- `plans/00_README.md` — Plan index
- `plans/00_orchestrator_master_prompt.md` — Master orchestrator prompt
- `plans/traceability_matrix.md` — Detailed spec→taskcard mapping
- `plans/taskcards/00_TASKCARD_CONTRACT.md` — Taskcard contract (binding rules)
- `plans/taskcards/INDEX.md` — Taskcard index
- `plans/taskcards/STATUS_BOARD.md` — Taskcard status tracking
- `plans/swarm_coordination_playbook.md` — Swarm execution rules

### Gates & Validators (Enforcement Tooling)
- `tools/validate_swarm_ready.py` — Preflight validation (Gates 0-K)
- `tools/validate_*.py` — Individual gate validators (Gates 0, A1, B, E, J, K, L, M, N, O, P, Q, R)
- `src/launch/validators/cli.py` — Runtime validator entry point (launch_validate command)
- `src/launch/util/path_validation.py` — Runtime path escape blocker
- `src/launch/util/budget_tracker.py` — Runtime budget enforcer
- `src/launch/util/diff_analyzer.py` — Runtime change budget enforcer

### Templates & Reference
- `reports/README.md` — Evidence requirements
- `reports/templates/agent_report.md` — Agent report template
- `reports/templates/self_review_12d.md` — 12-dimension self-review template
- `docs/architecture.md` — Architecture reference (non-binding)
- `docs/cli_usage.md` — CLI usage reference

---

## File Counts (Initial Scan)

- **Markdown files**: 100+ (specs, docs, plans, taskcards, reports)
- **JSON schemas**: 26 files in `specs/schemas/`
- **Python validators**: 3 files in `src/launch/validators/`
- **Python tools**: 20+ validation scripts in `tools/`
- **Taskcards**: 50+ in `plans/taskcards/`

---

## Repository Snapshot

See: `TREE.txt` (full repository tree, depth 5)

---

**Last Updated**: 2026-01-27T15:18:00Z
**Authority Source**: Repository contents at commit c8dab0c
