# 35. Test Harness Contract

**Status:** Binding
**Owner:** Test Infrastructure Team
**Last Updated:** 2026-01-27
**Cross-References:** specs/09 (validation gates), specs/13 (pilots)

---

## Purpose

Define the contract for the test harness that executes preflight gates, runtime gates, and integration tests.

## Requirements

### REQ-TH-001: Test Harness Invocation

**Requirement:** Test harness MUST be invocable via CLI command

**CLI Signature:**
```bash
python -m foss_launcher.test_harness [OPTIONS]
```

**Options:**
- `--mode {preflight|runtime|integration}` - Test mode (default: preflight)
- `--gates GATE_ID [GATE_ID ...]` - Specific gates to run (default: all)
- `--config PATH` - Path to run_config.json (required for runtime mode)
- `--output PATH` - Output path for validation_report.json (default: stdout)
- `--verbose` - Enable verbose logging

**Exit Codes:**
- 0: All tests passed
- 1: One or more tests failed
- 2: Configuration error
- 3: Test harness internal error

### REQ-TH-002: Preflight Gates Execution

**Requirement:** Test harness MUST execute all preflight gates (specs/09:20-135)

**Execution Order:**
1. Gate 1: Spec pack validation
2. Gate 2: Schema validation
3. Gate 3: Hugo config validation
4. ... (see specs/09 for complete list)

**Output:** validation_report.json with per-gate results (see specs/schemas/validation_report.schema.json)

### REQ-TH-003: Runtime Gates Execution

**Requirement:** Test harness MUST execute runtime gates during orchestration run

**Gates:**
- Runtime Gate 1: Repository fingerprint validation
- Runtime Gate 2: Empty repository detection
- Runtime Gate 3-13: (see specs/09:140-285)

**Integration:** Gates called at specific checkpoints per specs/11 (state transitions)

### REQ-TH-004: Test Isolation

**Requirement:** Each test MUST run in isolated environment

**Isolation Guarantees:**
- No shared state between tests
- Clean filesystem (temp directories per test)
- Independent process execution (no global state pollution)

**Cleanup:** Test harness MUST clean up temp directories after each test

### REQ-TH-005: Test Report Schema

**Requirement:** validation_report.json MUST conform to schema

**Schema Path:** specs/schemas/validation_report.schema.json

**Required Fields:**
- `run_id`: Test run identifier
- `timestamp`: ISO 8601 timestamp
- `mode`: "preflight" | "runtime" | "integration"
- `gates`: Array of gate results
- `summary`: { "total": N, "passed": N, "failed": N, "skipped": N }

**Example:**
```json
{
  "run_id": "test-20250127-1800",
  "timestamp": "2025-01-27T18:00:00Z",
  "mode": "preflight",
  "gates": [
    {
      "gate_id": "preflight-1",
      "name": "Spec Pack Validation",
      "status": "PASS",
      "duration_ms": 1234
    }
  ],
  "summary": {
    "total": 21,
    "passed": 21,
    "failed": 0,
    "skipped": 0
  }
}
```

### REQ-TH-006: Pilot Test Execution

**Requirement:** Test harness MUST support pilot test execution (specs/13)

**Pilot Tests:**
- `pilots/pilot-basic-hugo-site/` - Basic site generation
- `pilots/pilot-multilang-repo/` - Multi-language repository
- `pilots/pilot-large-monorepo/` - Large repository (>1000 files)
- `pilots/pilot-empty-repo/` - Empty repository edge case
- ... (see specs/13 for complete list)

**Execution:**
```bash
python -m foss_launcher.test_harness --mode integration --pilot pilot-basic-hugo-site
```

**Validation:** Compare actual outputs against expected/ directory in pilot folder

## Implementation Notes

- Test harness implementation in `src/test_harness/` (to be created during implementation phase)
- Preflight gates implemented in `src/launch/validators/` (partially implemented)
- Runtime gates NOT YET IMPLEMENTED (see TC-570, TC-580, TC-590)

## Cross-References

- **specs/09**: Validation gates definitions
- **specs/11**: State machine integration points
- **specs/13**: Pilot test specifications
- **specs/34**: Determinism guarantees (test reproducibility)
- **schemas/validation_report.schema.json**: Output schema
