# Phase 5 Swarm Hardening - Errata

**Date**: 2026-01-22
**Phase**: Phase 5 Swarm Hardening
**Purpose**: Correct misleading policy statements from earlier phases

---

## Summary

This errata document clarifies and corrects policy statements that were imprecise or could mislead swarm agents. These corrections are binding and supersede any conflicting statements in earlier reports.

---

## Correction 1: Gate A1 Failures Are NOT Acceptable

### Previous Statement (Incorrect)
In [plans/taskcards/00_TASKCARD_CONTRACT.md](../../plans/taskcards/00_TASKCARD_CONTRACT.md):
> "All gates must pass before proceeding (Gate A1 may fail due to missing `jsonschema` module - this will be resolved by TC-100)"

### Corrected Statement (Binding)
**All gates must pass before proceeding. No exceptions.**

### Rationale
- Swarm agents must not be given ambiguous guidance about acceptable failures
- The correct workflow is:
  1. Run `make install` (or pip editable install) to install dependencies
  2. Run `python tools/validate_swarm_ready.py`
  3. All gates must pass (exit code 0)
- If Gate A1 fails due to missing dependencies, this indicates the agent has not followed step 1
- Gate failures indicate planning/specification issues or missing setup steps, not acceptable operating states

### Location of Fix
- [plans/taskcards/00_TASKCARD_CONTRACT.md](../../plans/taskcards/00_TASKCARD_CONTRACT.md) lines 32-37

---

## Correction 2: Frontmatter Is Authoritative for Allowed Paths

### Previous Behavior (Imprecise)
- Taskcards had `allowed_paths` in frontmatter and a `## Allowed paths` section in the body
- These sections were not consistently synchronized
- No binding rule existed for which was authoritative

### Corrected Policy (Binding)
**The frontmatter `allowed_paths` list is the single source of truth.**

The body section `## Allowed paths` MUST:
- Be an exact mirror of frontmatter (same entries, same order)
- Contain only paths that appear in frontmatter
- NOT include additional paths that are not in frontmatter

Optional: The body may include a subsection `### Allowed paths rationale` with explanations, but NOT additional paths.

### Enforcement
- Validation tooling now enforces this rule (Gate B in preflight)
- Mismatches cause validation failure
- All 35 taskcards have been corrected as of Phase 5

### Location of Fix
- [plans/taskcards/00_TASKCARD_CONTRACT.md](../../plans/taskcards/00_TASKCARD_CONTRACT.md) lines 32-37
- [tools/validate_taskcards.py](../../tools/validate_taskcards.py) - added body/frontmatter consistency check
- All taskcards in [plans/taskcards/](../../plans/taskcards/) - body sections updated

---

## Correction 3: Overlaps Are Eliminated (Zero Tolerance for Critical Paths)

### Previous State
Two overlapping paths existed:
- `README.md` (TC-100 and TC-530)
- `src/launch/__main__.py` (TC-100 and TC-530)

These were documented but not treated as violations.

### Corrected Policy (Binding)
**Zero tolerance for overlaps in critical paths:**
- All `src/**` paths
- Repo-root files: README.md, Makefile, pyproject.toml, .gitignore

**Rationale for zero tolerance:**
- Multiple taskcards with write access to the same critical file create merge conflicts
- Swarm agents must have clear, non-overlapping write boundaries
- Single-writer governance prevents race conditions and inconsistent states

**Acceptable overlaps:**
- `reports/agents/**` paths (each taskcard writes to its own subdirectory)
- `tests/**` paths (if properly scoped by module/taskcard)

### Enforcement
- Validation tooling now fails on critical overlaps (Gate E in preflight)
- All critical overlaps have been eliminated as of Phase 5

### Location of Fix
- [plans/taskcards/TC-100_bootstrap_repo.md](../../plans/taskcards/TC-100_bootstrap_repo.md) - removed README.md and src/launch/__main__.py
- [tools/audit_allowed_paths.py](../../tools/audit_allowed_paths.py) - added critical overlap detection and enforcement

---

## Verification

All corrections have been verified via:
- `python tools/validate_taskcards.py` - passes (all taskcards valid, body/frontmatter match)
- `python tools/audit_allowed_paths.py` - passes (0 critical overlaps, 0 shared lib violations)
- `python tools/validate_swarm_ready.py` - passes (all gates pass)

Evidence captured in [gate_outputs/](gate_outputs/).

---

## Applicability

These corrections are:
- **Binding** for all future taskcard implementations
- **Enforced** by preflight validation tooling
- **Superseding** any conflicting statements in earlier reports or docs

Swarm agents MUST NOT rely on earlier imprecise statements. This errata establishes the definitive policy.

---

**End of Errata**
