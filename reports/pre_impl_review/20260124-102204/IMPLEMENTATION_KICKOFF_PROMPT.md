# IMPLEMENTATION KICKOFF PROMPT

**Status**: READY FOR IMPLEMENTATION ✅
**Decision Date**: 2026-01-24 10:50:00
**Pre-Implementation Review**: [reports/pre_impl_review/20260124-102204/](../20260124-102204/)

---

## CRITICAL: Repository Rules Discovered

### Write-Fence / Allowed Paths (ZERO TOLERANCE)

**Rule**: Agents MAY ONLY modify files listed in their taskcard's `allowed_paths` frontmatter.

**Shared Library Boundaries** (ZERO TOLERANCE):
- `src/launch/io/**` → TC-200 (owner only)
- `src/launch/util/**` → TC-200 (owner only)
- `src/launch/models/**` → TC-250 (owner only)
- `src/launch/clients/**` → TC-500 (owner only)

**Violations**: Gate E (`tools/audit_allowed_paths.py`) enforces zero violations. Preflight will FAIL if violations exist.

**Source**: [plans/taskcards/00_TASKCARD_CONTRACT.md](../../../plans/taskcards/00_TASKCARD_CONTRACT.md)

---

## Mandatory Preflight + Gate Order

**Before ANY implementation work**:
```bash
# 1. Ensure .venv is active
python --version  # Must be >= 3.12

# 2. Install dependencies (deterministic)
make install-uv  # OR: .venv/Scripts/uv.exe sync --frozen

# 3. Run preflight (all 20 gates must PASS)
python tools/validate_swarm_ready.py
```

**Gate Execution Order** (20 gates total):
- Gate 0: venv policy
- Gates A1-A2: Spec/plans validation
- Gate B: Taskcard validation + path enforcement
- Gates C-S: Infrastructure + strict compliance (A-L guarantees)

**Exit Code**: Must be 0 (all gates pass). Exit code 1 = stop work, fix gates first.

---

## Implementation Phases (Derived from Plans/Taskcards)

### Phase 0: Bootstrap (TC-100)
- ✅ **COMPLETE** - Repository scaffolding exists

### Phase 1: Schemas + IO (TC-200, TC-250)
- Core schemas and I/O utilities
- **Owned Paths**: `src/launch/io/**`, `src/launch/util/**`, `src/launch/models/**`
- **Tests Required**: Full coverage for atomic writes, path validation, schema validation

### Phase 2: Shared Services (TC-500)
- HTTP clients, telemetry, commit service, LLM providers
- **Owned Paths**: `src/launch/clients/**`
- **Tests Required**: Client tests, integration tests with mocks

### Phase 3: Workers W1-W9 (TC-400, TC-410, TC-420, TC-430, TC-440, TC-450, TC-460, TC-470, TC-480)
- Worker implementations (9 workers)
- **Owned Paths**: `src/launch/workers/<worker_name>/`
- **Tests Required**: Per-worker tests + integration tests

### Phase 4: Orchestrator (TC-300)
- LangGraph orchestrator
- **Owned Paths**: `src/launch/orchestrator/**`
- **Tests Required**: State machine tests, coordination tests

### Phase 5: Validators + Gates (TC-460, TC-570, TC-571)
- Validation gates implementation
- **Tests Required**: Gate tests, integration tests

### Phase 6: MCP Server (TC-510, TC-511, TC-512)
- FastAPI MCP server
- **Tests Required**: MCP tool tests, quickstart tests

### Phase 7: CLI + Entrypoints (TC-530)
- CLI implementation
- **Tests Required**: CLI smoke tests

### Phase 8: Pilots + E2E (TC-520, TC-522, TC-523)
- Pilot execution and regression testing
- **Tests Required**: E2E tests, golden output comparisons

---

## Check-Before-Change Rule (MANDATORY)

Before modifying ANY file:
1. **Read it first** to understand current state
2. **Check if it already exists** and is verified
3. **Verify write-fence** - is this path in your taskcard's `allowed_paths`?
4. If NO → STOP, create BLOCKER issue, do not modify

---

## Evidence Artifacts (Required Per Agent)

Every agent execution MUST produce:
- `reports/agents/<agent>/<task_id>/report.md`
- `reports/agents/<agent>/<task_id>/self_review.md`
- Console outputs captured verbatim in `evidence_*.txt` files
- Test results
- Gate outputs

---

## Determinism Recording Requirements

**Requirement**: Byte-for-byte reproducible runs where applicable.

**Required Records**:
- Input hashes (repo SHA, site SHA, workflows SHA)
- Python version + all dependency versions (from uv.lock)
- Seed values (`PYTHONHASHSEED=0` enforced in pytest.ini)
- File iteration order (sorted)
- Timestamps (mocked/frozen in tests)

**Validation**: `tools/validate_swarm_ready.py` (Gate K - supply chain pinning)

---

## Stop-The-Line Triggers (MANDATORY STOP)

**STOP immediately and create BLOCKER issue if**:
1. **Ambiguity**: Spec/taskcard requires guessing (no improvisation rule)
2. **Write-Fence Violation**: Required change is outside `allowed_paths`
3. **Shared Library Boundary Crossed**: Attempting to modify library owned by another taskcard
4. **Preflight Failure**: `validate_swarm_ready.py` exits with code 1
5. **Test Failure**: Any test fails after your changes
6. **Schema Violation**: Artifact fails schema validation
7. **Budget Exceeded**: Runtime/LLM calls/file writes exceed configured budgets
8. **Secret Detected**: Gate L detects secrets in logs/artifacts

**Blocker Format**:
```json
{
  "schema_version": "1.0",
  "issue_id": "BLOCKER-<LETTER>-<slug>",
  "severity": "blocker",
  "component": "<component>",
  "description": "<clear explanation>",
  "proposed_resolution": "<actionable steps>"
}
```

Validate against: `specs/schemas/issue.schema.json`

---

## Required 12-Dimension Self-Review (Per Agent)

Every agent MUST complete self-review scoring 1-5 for:
1. Coverage
2. Correctness
3. Evidence Quality
4. Test Quality
5. Maintainability
6. Safety
7. Security
8. Reliability
9. Observability
10. Performance
11. Compatibility
12. Specs/Docs Fidelity

**Template**: [reports/templates/self_review_12d.md](../../../reports/templates/self_review_12d.md)

**Rule**: Any score <4 requires concrete remediation note or documented exception.

---

## Orchestrator Final Review (After All Agents)

After all agents complete, orchestrator MUST produce:
- `reports/orchestrator_master_review.md`
- Summary of all agent reports
- Consolidated gate results
- GO/NO-GO for release
- Evidence bundle

---

## Known Blockers (Address in Parallel)

### BLOCKER-A: Spec Classification (MEDIUM)
- **Issue**: 5 specs lack explicit binding vs informational classification
- **Workaround**: Use existing traceability matrices (86% coverage sufficient for MVP)
- **Optional Fix**: Add classification section to specs/README.md

### BLOCKER-B: Gate Comments Outdated (LOW)
- **Issue**: validate_swarm_ready.py comments label Gates L, O, R as "STUB" but they're fully implemented
- **Optional Fix**: Update comments in tools/validate_swarm_ready.py:305-351

**Note**: Both blockers are documentation-level and do NOT prevent implementation.

---

## Acceptance Criteria (Implementation Complete When)

1. All 44 taskcards implemented (TC-100 through TC-602)
2. All gates pass: `python tools/validate_swarm_ready.py` exits 0
3. All tests pass: `pytest` exits 0
4. Both pilots produce expected outputs (golden comparisons pass)
5. CLI and MCP endpoints functional
6. All strict compliance guarantees (A-L) enforced at runtime
7. All agents have completed 12-dimension self-reviews
8. Orchestrator final review complete with GO decision

---

## Quick Reference

- **Preflight**: `python tools/validate_swarm_ready.py`
- **Tests**: `pytest` (with `PYTHONHASHSEED=0` enforced)
- **Install**: `make install-uv` (deterministic)
- **Taskcard Contract**: [plans/taskcards/00_TASKCARD_CONTRACT.md](../../../plans/taskcards/00_TASKCARD_CONTRACT.md)
- **Traceability**: [TRACEABILITY_MATRIX.md](../../../TRACEABILITY_MATRIX.md)
- **Strict Guarantees**: [specs/34_strict_compliance_guarantees.md](../../../specs/34_strict_compliance_guarantees.md)

---

**READY FOR IMPLEMENTATION** ✅
**Pre-Implementation Review Complete**: 2026-01-24 10:50:00
