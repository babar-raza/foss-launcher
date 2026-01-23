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
**Decision**: Use **uv** with `uv.lock` for deterministic Python dependency management.
**Rationale**:
- `specs/25_frameworks_and_dependencies.md` prefers uv for fast, deterministic installs
- `specs/10_determinism_and_caching.md` requires reproducible builds
- uv provides cross-platform lockfile with hash pinning
**Alternatives Considered**:
- Poetry (rejected: slower, more complex for this use case)
- pip-tools (rejected: less deterministic than uv)
- Plain pip freeze (rejected: no cross-platform guarantees)
**Implementation**:
- Fresh install: `uv sync`
- Lock regeneration: `uv lock` (after pyproject.toml changes)
- CI install: `uv sync --frozen` (fail if lock is stale)
**Date Added**: 2026-01-22
**Updated**: 2026-01-23
**Status**: ACTIVE

---

### DEC-005: Worker module structure standard (resolves OQ-PRE-001)
**Category**: Architecture
**Decision**: Each worker (W1-W9) is implemented as a **package** with standardized structure:
- Package location: `src/launch/workers/<wX_name>/`
- Required files: `__init__.py` and `__main__.py`
- Subcommands: separate modules (e.g., `clone.py`, `fingerprint.py`)
- Supports both invocation patterns:
  - `python -m launch.workers.w1_repo_scout` (runs __main__.py)
  - `python -m launch.workers.w1_repo_scout.clone` (runs specific subcommand)
**Rationale**:
- Taskcards reference E2E commands using `python -m` syntax, which requires package structure
- Package structure provides cleaner CLI invocability and modular organization
- Matches Python best practices for executable modules
**Alternatives Considered**:
- Files only (rejected: breaks `-m` invocation pattern in taskcards)
- Change E2E commands to function calls (rejected: less user-friendly)
**Implementation Impact**:
- Taskcards TC-400, TC-410, TC-420, TC-430, TC-440, TC-450, TC-460, TC-470, TC-480 must allow `__main__.py` in allowed_paths
- Initial structural shims (empty packages with NOT_IMPLEMENTED stubs) can be created to satisfy contracts
**Date Added**: 2026-01-23
**Status**: ACTIVE

---

### DEC-006: Directory structure for tools, MCP tools, and inference (resolves OQ-PRE-002)
**Category**: Architecture
**Decision**: Create the following package directories as referenced by taskcards:
- `src/launch/tools/` - Runtime validation gates for RUN_DIR (distinct from repo root `tools/`)
- `src/launch/mcp/tools/` - MCP tool implementations
- `src/launch/inference/` - LLM inference utilities
Each directory must have `__init__.py` to be a valid Python package.
**Rationale**:
- Multiple taskcards (TC-511, TC-512, TC-560) explicitly reference these paths
- Clear separation of concerns: repo root `tools/` are for repo validation, `src/launch/tools/` are for runtime validation
- Matches taskcard expectations without requiring changes to 39 taskcards
**Alternatives Considered**:
- Consolidate into existing structure (rejected: requires updating many taskcards)
- Use flat structure without subdirectories (rejected: unclear separation of concerns)
**Documentation Required**:
- Add note in `src/launch/tools/README.md` explaining difference from repo root `tools/`
**Date Added**: 2026-01-23
**Status**: ACTIVE

---

### DEC-007: Validator invocation pattern (resolves OQ-PRE-003)
**Category**: Implementation
**Decision**: Create `src/launch/validators/__main__.py` that delegates to `launch.validators.cli:main()`.
This enables the invocation pattern: `python -m launch.validators --help`
**Rationale**:
- TC-570 E2E commands reference `python -m launch.validators` invocation
- Having `__main__.py` provides user-friendly CLI entry point
- Delegation pattern keeps implementation in `cli.py` (single source of truth)
**Alternatives Considered**:
- Update E2E commands to use `launch.validators.cli` (rejected: less user-friendly)
- Keep only `cli.py` (rejected: breaks taskcard E2E commands)
**Implementation**:
```python
# src/launch/validators/__main__.py
from launch.validators.cli import main
if __name__ == "__main__":
    main()
```
**Date Added**: 2026-01-23
**Status**: ACTIVE
