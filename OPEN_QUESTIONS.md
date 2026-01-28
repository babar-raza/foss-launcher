# Open Questions

This file tracks unresolved questions that require user/stakeholder clarification before implementation proceeds.

## How to use this file
- If an implementation agent encounters ambiguity that would require guessing, they MUST:
  1) Write a blocker issue JSON (see `plans/taskcards/00_TASKCARD_CONTRACT.md`), and
  2) Add (or update) an entry here that links to the ambiguous doc section and the blocker artifact.
- Keep questions **actionable** and **scoped**. Prefer one question per entry.

## Format

Each question should include:
- **ID**: Unique identifier (OQ-###)
- **Category**: Area of concern (specs/plans/architecture/requirements)
- **Question**: Clear question statement
- **Impact**: What is blocked or affected
- **Date Added**: When question was raised
- **Status**: OPEN | ANSWERED | DEFERRED
- **Resolution**: Answer or decision (when status=ANSWERED)

## Current status

As of **2026-01-27**, one open question remains **OPEN** (see OQ-BATCH-001 below).

Previously open questions OQ-PRE-001, OQ-PRE-002, and OQ-PRE-003 have been answered via architectural decisions DEC-005, DEC-006, and DEC-007 respectively (see DECISIONS.md).

> If you believe items are still unresolved, add them below (do not keep "gaps" only in reports — this file is the canonical place for unanswered questions).

## Questions

---

### OQ-PRE-001: Worker module structure standard
**ID**: OQ-PRE-001
**Category**: Architecture
**Question**: Should workers (W1-W9) be implemented as files or packages? How should `python -m` invocation work?
**Impact**: Affects all worker taskcards (TC-400, TC-410, TC-420, TC-430, TC-440, TC-450, TC-460, TC-470, TC-480)
**Date Added**: 2026-01-23
**Status**: **ANSWERED**
**Resolution**: See **DEC-005** in DECISIONS.md. Workers are packages with `__init__.py` and `__main__.py`, supporting both `python -m launch.workers.wX` and subcommand invocation.

---

### OQ-PRE-002: Directory structure for tools, MCP tools, and inference
**ID**: OQ-PRE-002
**Category**: Architecture
**Question**: Should `src/launch/tools/`, `src/launch/mcp/tools/`, and `src/launch/inference/` directories be created as referenced by taskcards?
**Impact**: Affects TC-511, TC-512, TC-560
**Date Added**: 2026-01-23
**Status**: **ANSWERED**
**Resolution**: See **DEC-006** in DECISIONS.md. All three directories will be created as packages with `__init__.py`. Repo root `tools/` is for repo validation, `src/launch/tools/` is for runtime validation.

---

### OQ-PRE-003: Validator invocation pattern
**ID**: OQ-PRE-003
**Category**: Implementation
**Question**: Should validators support `python -m launch.validators` invocation or require `python -m launch.validators.cli`?
**Impact**: Affects TC-570, TC-571
**Date Added**: 2026-01-23
**Status**: **ANSWERED**
**Resolution**: See **DEC-007** in DECISIONS.md. Create `src/launch/validators/__main__.py` that delegates to `cli.main()` to support clean invocation pattern.

---

### OQ-BATCH-001: Batch execution (queue many runs) semantics
**ID**: OQ-BATCH-001
**Category**: Requirements
**Question**: `specs/00_overview.md` requires batch execution (queue many runs) with bounded concurrency, but what is the exact batch input shape and execution contract? Specifically: how are multiple runs specified (directory of run_config files, a batch manifest, CLI args), what scheduling/ordering rules ensure determinism, what resume/checkpoint artifacts are required, and what CLI + MCP endpoints expose batch execution?
**Impact**: Blocks deterministic implementation of batch execution and bounded concurrency; impacts orchestrator run loop (TC-300), CLI entrypoints/runbooks (TC-530), and MCP surface (specs/14_mcp_endpoints.md).
**Date Added**: 2026-01-27
**Status**: **OPEN**
**Resolution**: (pending)
