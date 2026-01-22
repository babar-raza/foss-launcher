# Decisions

This file records architectural and design decisions made during spec/plan hardening that are **derivable from existing documentation**.

Use this file to capture:
- decisions that are effectively fixed by spec requirements, and
- decisions that the specs intentionally leave as a choice (track as PENDING until selected).

## Format

Each decision should include:
- **ID**: Unique identifier (DEC-###)
- **Category**: Area (specs/plans/architecture/implementation)
- **Decision**: Clear statement of what was decided
- **Rationale**: Why this decision was made (cite specs/plans)
- **Alternatives Considered**: Other options and why they were rejected
- **Date Added**: When decision was made
- **Status**: ACTIVE | SUPERSEDED | PENDING

## Decisions

### DEC-001: Use LangGraph for orchestration state machine
**Category**: Architecture  
**Decision**: Implement the orchestration/control plane using LangGraph.  
**Rationale**: `specs/25_frameworks_and_dependencies.md` and `specs/28_coordination_and_handoffs.md` define a state-graph driven orchestrator.  
**Alternatives Considered**: Custom state machine (rejected: spec set assumes LangGraph semantics).  
**Date Added**: 2026-01-22  
**Status**: ACTIVE  

---

### DEC-002: All site-repo changes must go through the GitHub commit service
**Category**: Release  
**Decision**: Prohibit direct `git commit/push` to the site repo in production mode; use the centralized commit service.  
**Rationale**: `specs/12_pr_and_release.md` and `specs/17_github_commit_service.md` make this non-negotiable.  
**Alternatives Considered**: Direct git operations (rejected: forbidden by specs).  
**Date Added**: 2026-01-22  
**Status**: ACTIVE  

---

### DEC-003: Toolchain lock file is authoritative for deterministic gates
**Category**: CI / Validation  
**Decision**: Treat `config/toolchain.lock.yaml` as the single source of truth for tool versions used by gates.  
**Rationale**: `specs/19_toolchain_and_ci.md` requires a lock file and deterministic runner behavior.  
**Alternatives Considered**: Rely on system-installed tools (rejected: non-deterministic).  
**Date Added**: 2026-01-22  
**Status**: ACTIVE  

---

### DEC-004: Python dependency lock strategy selection
**Category**: Implementation  
**Decision**: Select and enforce a single Python dependency lock strategy (uv preferred; Poetry allowed).  
**Rationale**: `plans/00_orchestrator_master_prompt.md` requires the orchestrator to choose this during Phase 0 bootstrap.  
**Alternatives Considered**: Mixed tooling (rejected: increases drift and non-determinism).  
**Date Added**: 2026-01-22  
**Status**: PENDING  
