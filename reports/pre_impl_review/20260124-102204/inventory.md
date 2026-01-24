# Baseline Inventory

## Inventory Generation Timestamp
2026-01-24 10:30:30

## Repository Summary
- **Path**: c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher
- **Branch**: chore/pre_impl_readiness_sweep
- **Commit**: f48fc5d
- **Python**: 3.13.2
- **Lock File**: uv.lock (frozen install)

## Key Files

### Specs (35 spec documents)
- specs/00_environment_policy.md
- specs/00_overview.md
- specs/01_system_contract.md
- specs/09_validation_gates.md
- specs/34_strict_compliance_guarantees.md
- specs/29_project_repo_structure.md
- specs/README.md
- (+ 28 additional spec files)

### Plans and Taskcards (44 taskcards)
- plans/taskcards/00_TASKCARD_CONTRACT.md (binding contract)
- plans/taskcards/INDEX.md
- plans/taskcards/STATUS_BOARD.md
- TC-100 through TC-602 (41 implementation taskcards)

### Tools (20 validation scripts)
- tools/validate_swarm_ready.py (preflight gate runner)
- tools/audit_allowed_paths.py
- tools/validate_taskcards.py
- tools/validate_pinned_refs.py
- tools/validate_secrets_hygiene.py
- tools/validate_budgets_config.py
- tools/validate_network_allowlist.py
- tools/validate_untrusted_code_policy.py
- tools/validate_windows_reserved_names.py
- (+ 11 additional validation tools)

### Source Code (src/launch/)
Core packages:
- src/launch/orchestrator/
- src/launch/workers/ (W1-W9 implementations)
- src/launch/validators/
- src/launch/mcp/
- src/launch/clients/
- src/launch/models/
- src/launch/io/
- src/launch/util/

Key modules:
- src/launch/io/atomic.py
- src/launch/io/schema_validation.py
- src/launch/util/subprocess.py (untrusted code protection)
- src/launch/util/budget_tracker.py
- src/launch/util/path_validation.py
- src/launch/clients/http.py

### Tests
- tests/unit/ (unit tests)
- tests/integration/ (integration tests)
- tests/conftest.py (pytest configuration)

### Schemas (21 JSON schemas)
- specs/schemas/run_config.schema.json
- specs/schemas/repo_inventory.schema.json
- specs/schemas/product_facts.schema.json
- specs/schemas/evidence_map.schema.json
- specs/schemas/page_plan.schema.json
- specs/schemas/validation_report.schema.json
- specs/schemas/truth_lock_report.schema.json
- specs/schemas/issue.schema.json
- (+ 13 additional schemas)

### CI/CD
- .github/workflows/ci.yml (canonical CI pipeline)

## Critical File Hashes (SHA256)

| File | SHA256 |
|------|--------|
| specs/README.md | 065adb6e3d23bf73b39bf43915fdf1b25f4bc0c03b1578f18f2be01c4a49f900 |
| specs/34_strict_compliance_guarantees.md | 5596f42166a3b725a76464a6962b7d84276db43ff33b4ca688526f63f878a4c4 |
| specs/09_validation_gates.md | 09c71805f3bc8dcc0444e8659ad5d1b73d0f82ea8afe865e530bd2ca3270e0fa |
| specs/01_system_contract.md | 595e19c492a35ee082c5ee6f68b5d04a2d2da4a1c8302c466435c5547949c8bc |
| plans/taskcards/00_TASKCARD_CONTRACT.md | 029bdf526de5aa460c86413e3cb405e356f56a93ea0a87034b191efd1bbdabc7 |
| tools/validate_swarm_ready.py | dd94928378465c16107a42205b1f8ef3522bc1d1226b366e6037b399b35c2073 |
| pyproject.toml | 7a0945f52962a0c040179b2488bcc30fe9ee6b10534eb3143b22bf0a34d008b0 |
| uv.lock | 4027030d268b3fb5ca3ad7808e1867b572d72c7205ce9bffc7118fab14e9baf4 |

## Gate Execution Results (from preflight)

All 20 gates PASSED:
- Gate 0: Virtual environment policy
- Gates A1-A2: Spec and plans validation
- Gate B: Taskcard validation + path enforcement
- Gates C-I: Infrastructure and integrity checks
- Gates J-R: Strict compliance guarantees (A-L)
- Gate S: Windows reserved names prevention

**Note**: Gates L, O, R were previously marked as "STUB" in validate_swarm_ready.py comments but all passed validation.
