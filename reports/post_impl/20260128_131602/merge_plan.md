# Merge Plan: Wave-by-Wave Integration Strategy
**Created:** 2026-01-28 13:16:02
**Base Branch:** main (c8dab0c)
**Target Branches:** 41 feature branches
**Strategy:** Progressive wave-based merges with gate validation

## Executive Summary

This plan orchestrates the integration of 41 feature branches into main through 5 carefully sequenced waves. Each wave groups related functionality and includes mandatory gate checkpoints to ensure system integrity.

### Key Metrics
- **Total Branches:** 41
- **Total Waves:** 5
- **Estimated Duration:** 4-6 hours (with gate execution)
- **Gate Checkpoints:** After each wave
- **Rollback Strategy:** Wave-level rollback on gate failure

---

## Merge Strategy

### Principles
1. **Dependencies First:** Foundation components before consumers
2. **Isolation:** Each wave can be validated independently
3. **Incrementalism:** Small, testable changes per wave
4. **Safety:** Full gate validation after each wave
5. **Reversibility:** Clean rollback possible at wave boundaries

### Gate Checkpoints
After each wave, run:
```bash
# Activate venv
.venv\Scripts\activate

# Run validation suite
python tools/validate_swarm_ready.py

# Run tests
set PYTHONHASHSEED=0
python -m pytest -q

# Check git status
git status
```

**Pass Criteria:**
- All gates must maintain or improve their status
- No new test failures
- No uncommitted changes (unless expected)

**Failure Protocol:**
1. Record failure in `post_state.json`
2. Identify failing branch
3. Rollback wave: `git reset --hard <pre-wave-commit>`
4. Create fix branch from feature branch
5. Re-run wave after fix

---

## Wave Definitions

### Wave 1: Foundation Layer 🏗️

**Purpose:** Establish core infrastructure (schemas, I/O, models, governance)

**Branches (4):**
1. `feat/TC-100-bootstrap-repo` (f4b545c)
2. `feat/TC-200-schemas-and-io` (2f24053)
3. `feat/TC-201-emergency-mode` (ffbab4f)
4. `feat/TC-250-shared-libs-governance` (af850f4)

**Dependencies:** None (clean base)

**Merge Order:**
```bash
# 1. Bootstrap repo structure
git merge feat/TC-100-bootstrap-repo --no-ff -m "Merge TC-100: Bootstrap repository structure"

# 2. Add schemas and I/O
git merge feat/TC-200-schemas-and-io --no-ff -m "Merge TC-200: Schemas and I/O layer"

# 3. Add emergency mode
git merge feat/TC-201-emergency-mode --no-ff -m "Merge TC-201: Emergency mode for manual edits"

# 4. Add shared libs governance
git merge feat/TC-250-shared-libs-governance --no-ff -m "Merge TC-250: Shared libraries governance"
```

**Expected Changes:**
- `src/launch/` directory created
- `src/launch/models/` (base, state, event)
- `src/launch/io/` (schema validation, atomic writes, hashing)
- `src/launch/state/` (emergency mode)
- `tests/unit/` foundation tests
- `pyproject.toml` with dependencies

**Gate Checkpoint 1:**
```bash
# Run gates
python tools/validate_swarm_ready.py

# Run tests
set PYTHONHASHSEED=0
python -m pytest tests/unit/test_bootstrap.py tests/unit/models/ tests/unit/io/ tests/unit/state/ -q

# Expected: All foundation tests pass
```

**Success Criteria:**
- ✅ Gate A1 (Spec pack): PASS
- ✅ Gate F (Platform layout): PASS
- ✅ Foundation tests: 100% pass

---

### Wave 2: Core Infrastructure 🔧

**Purpose:** Orchestrator and client services

**Branches (2):**
1. `feat/TC-300-orchestrator-langgraph` (10672ed)
2. `feat/TC-500-clients-services` (8d52840)

**Dependencies:** Wave 1 (models, schemas, I/O)

**Merge Order:**
```bash
# 1. Add orchestrator
git merge feat/TC-300-orchestrator-langgraph --no-ff -m "Merge TC-300: LangGraph orchestrator with single-run execution"

# 2. Add client services
git merge feat/TC-500-clients-services --no-ff -m "Merge TC-500: Client services (LLM, HTTP, commit)"
```

**Expected Changes:**
- `src/launch/orchestrator/` (graph, run loop)
- `src/launch/clients/` (llm_provider, http, commit_service)
- `tests/unit/orchestrator/`
- `tests/integration/test_tc_300_run_loop.py`
- `tests/unit/clients/`

**Gate Checkpoint 2:**
```bash
# Run gates
python tools/validate_swarm_ready.py

# Run tests
set PYTHONHASHSEED=0
python -m pytest tests/unit/orchestrator/ tests/unit/clients/ tests/integration/test_tc_300_run_loop.py -q

# Expected: Orchestrator and client tests pass
```

**Success Criteria:**
- ✅ Orchestrator tests: PASS
- ✅ Client tests: PASS
- ✅ Single-run execution: Functional

---

### Wave 3: Worker Fleet 👷

**Purpose:** All 9 workers (W1-W9) with their sub-components

**Branches (31):**

**W1 - Repo Scout (5 branches):**
- `feat/TC-400-repo-scout` (33673f0)
- `feat/TC-401-clone-resolve-shas` (be1f101)
- `feat/TC-402-fingerprint` (cd8086b)
- `feat/TC-403-discover-docs` (e0a217e)
- `feat/TC-404-discover-examples` (9b146f4)

**W2 - Facts Builder (4 branches):**
- `feat/TC-410-facts-builder` (7962c7b)
- `feat/TC-411-extract-claims` (dba509f)
- `feat/TC-412-map-evidence` (4428fe0)
- `feat/TC-413-detect-contradictions` (cdb94da)

**W3 - Snippet Curator (3 branches):**
- `feat/TC-420-snippet-curator` (b21a289)
- `feat/TC-421-extract-doc-snippets` (73d56ea)
- `feat/TC-422-extract-code-snippets` (cdf0da9)

**W4 - IA Planner (1 branch):**
- `feat/TC-430-ia-planner` (feb34ad)

**W5 - Section Writer (1 branch):**
- `feat/TC-440-section-writer` (a039d4a)

**W6 - Linker & Patcher (1 branch):**
- `feat/TC-450-linker-and-patcher` (111c41a)

**W7 - Validator (3 branches):**
- `feat/TC-460-validator` (27a683c)
- `feat/TC-570-extended-gates` (2901e83)
- `feat/TC-571-perf-security-gates` (c8dbee7)

**W8 - Fixer (1 branch):**
- `feat/TC-470-fixer` (eda48de)

**W9 - PR Manager (1 branch):**
- `feat/TC-480-pr-manager` (958da5a)

**Dependencies:** Wave 2 (orchestrator for worker invocation)

**Merge Order (Worker-by-Worker):**
```bash
# W1: Repo Scout
git merge feat/TC-400-repo-scout --no-ff -m "Merge TC-400: W1 Repo Scout base"
git merge feat/TC-401-clone-resolve-shas --no-ff -m "Merge TC-401: Clone and resolve SHAs"
git merge feat/TC-402-fingerprint --no-ff -m "Merge TC-402: Repo fingerprinting"
git merge feat/TC-403-discover-docs --no-ff -m "Merge TC-403: Documentation discovery"
git merge feat/TC-404-discover-examples --no-ff -m "Merge TC-404: Examples discovery"

# W2: Facts Builder
git merge feat/TC-410-facts-builder --no-ff -m "Merge TC-410: W2 Facts Builder base"
git merge feat/TC-411-extract-claims --no-ff -m "Merge TC-411: Claim extraction"
git merge feat/TC-412-map-evidence --no-ff -m "Merge TC-412: Evidence mapping"
git merge feat/TC-413-detect-contradictions --no-ff -m "Merge TC-413: Contradiction detection"

# W3: Snippet Curator
git merge feat/TC-420-snippet-curator --no-ff -m "Merge TC-420: W3 Snippet Curator base"
git merge feat/TC-421-extract-doc-snippets --no-ff -m "Merge TC-421: Doc snippet extraction"
git merge feat/TC-422-extract-code-snippets --no-ff -m "Merge TC-422: Code snippet extraction"

# W4: IA Planner
git merge feat/TC-430-ia-planner --no-ff -m "Merge TC-430: W4 IA Planner"

# W5: Section Writer
git merge feat/TC-440-section-writer --no-ff -m "Merge TC-440: W5 Section Writer"

# W6: Linker & Patcher
git merge feat/TC-450-linker-and-patcher --no-ff -m "Merge TC-450: W6 Linker and Patcher"

# W7: Validator (base + extended + security)
git merge feat/TC-460-validator --no-ff -m "Merge TC-460: W7 Validator base (gates 2-13)"
git merge feat/TC-570-extended-gates --no-ff -m "Merge TC-570: Extended validation gates"
git merge feat/TC-571-perf-security-gates --no-ff -m "Merge TC-571: Performance and security gates"

# W8: Fixer
git merge feat/TC-470-fixer --no-ff -m "Merge TC-470: W8 Fixer"

# W9: PR Manager
git merge feat/TC-480-pr-manager --no-ff -m "Merge TC-480: W9 PR Manager"
```

**Expected Changes:**
- `src/launch/workers/w1_repo_scout/` through `w9_pr_manager/`
- `src/launch/workers/_git/` (Git helpers)
- `src/launch/workers/_shared/` (Shared policies)
- `tests/unit/workers/` (45+ test files)
- All worker `__main__.py` files

**Gate Checkpoint 3:**
```bash
# Run gates (NOTE: Gate R failures expected - see final_gates.md)
python tools/validate_swarm_ready.py

# Run all worker tests
set PYTHONHASHSEED=0
python -m pytest tests/unit/workers/ -q

# Expected: 400+ tests pass
```

**Success Criteria:**
- ✅ All worker tests: PASS
- ✅ Worker structure: Verified
- ⚠️ Gate R (subprocess): Known failures in clone_helpers.py and gate_13_hugo_build.py (acceptable)

**Note:** This is the largest wave. Consider sub-checkpoints after W3, W6, W9 if desired.

---

### Wave 4: Services & Interfaces 🖥️

**Purpose:** MCP server, telemetry API, CLI, content resolvers

**Branches (12):**

**MCP Server (3 branches):**
- `feat/TC-510-mcp-server-setup` (2790dfa)
- `feat/TC-511-mcp-tool-registration` (2ddaf75)
- `feat/TC-512-mcp-tool-handlers` (7a54d2b)

**Telemetry API (4 branches):**
- `feat/TC-520-telemetry-api-setup` (4c97438)
- `feat/TC-521-telemetry-run-endpoints` (42df129)
- `feat/TC-522-telemetry-batch-upload` (3873ff3)
- `feat/TC-523-telemetry-metadata-endpoints` (dc2734e)

**CLI & Content (3 branches):**
- `feat/TC-530-cli-entrypoints` (8282263)
- `feat/TC-540-content-path-resolver` (675b19d)
- `feat/TC-550-hugo-config` (a95bf2a)

**Chore (1 branch):**
- `chore/pre_impl_readiness_sweep` (7f7786a) - Pre-implementation cleanup

**Dependencies:** Wave 3 (workers for MCP tool handlers)

**Merge Order:**
```bash
# Pre-implementation cleanup (if not already merged)
git merge chore/pre_impl_readiness_sweep --no-ff -m "Merge chore: Pre-implementation readiness sweep"

# MCP Server
git merge feat/TC-510-mcp-server-setup --no-ff -m "Merge TC-510: MCP server setup"
git merge feat/TC-511-mcp-tool-registration --no-ff -m "Merge TC-511: MCP tool registration"
git merge feat/TC-512-mcp-tool-handlers --no-ff -m "Merge TC-512: MCP tool handlers"

# Telemetry API
git merge feat/TC-520-telemetry-api-setup --no-ff -m "Merge TC-520: Telemetry API setup"
git merge feat/TC-521-telemetry-run-endpoints --no-ff -m "Merge TC-521: Telemetry run endpoints"
git merge feat/TC-522-telemetry-batch-upload --no-ff -m "Merge TC-522: Telemetry batch upload"
git merge feat/TC-523-telemetry-metadata-endpoints --no-ff -m "Merge TC-523: Telemetry metadata endpoints"

# CLI & Content
git merge feat/TC-530-cli-entrypoints --no-ff -m "Merge TC-530: CLI entrypoints"
git merge feat/TC-540-content-path-resolver --no-ff -m "Merge TC-540: Content path resolver"
git merge feat/TC-550-hugo-config --no-ff -m "Merge TC-550: Hugo configuration"
```

**Expected Changes:**
- `src/launch/mcp/` (server, tool registration)
- `src/launch/telemetry_api/` (FastAPI routes)
- `src/launch/cli.py`
- `src/launch/content/path_resolver.py`
- `tests/unit/mcp/`
- `tests/unit/test_tc_530_entrypoints.py`
- `pyproject.toml` scripts updated

**Gate Checkpoint 4:**
```bash
# Run gates
python tools/validate_swarm_ready.py

# Run interface tests
set PYTHONHASHSEED=0
python -m pytest tests/unit/mcp/ tests/unit/test_tc_530_entrypoints.py -q

# Test CLI entrypoints (smoke test)
python -m launch.cli --help
python -m launch.mcp.server --help

# Expected: CLI/MCP invocation works
```

**Success Criteria:**
- ✅ MCP tests: PASS (44 tests)
- ✅ CLI tests: PASS
- ✅ Scripts invocable: `launch_run --help`, `launch_mcp --help`
- ✅ Gate H (MCP contract): PASS

---

### Wave 5: Quality, Observability & Resilience 🔍

**Purpose:** Determinism, observability, security, failure recovery

**Branches (4):**
1. `feat/TC-560-determinism-harness` (2fcb1d4)
2. `feat/TC-580-observability` (c4d15a0)
3. `feat/TC-590-security-handling` (1450676)
4. `feat/TC-600-failure-recovery` (b3d5242)

**Dependencies:** All previous waves (cross-cutting concerns)

**Merge Order:**
```bash
# 1. Determinism harness
git merge feat/TC-560-determinism-harness --no-ff -m "Merge TC-560: Determinism harness (Guarantee I)"

# 2. Observability
git merge feat/TC-580-observability --no-ff -m "Merge TC-580: Observability (evidence packages, reports index)"

# 3. Security handling
git merge feat/TC-590-security-handling --no-ff -m "Merge TC-590: Security handling (subprocess wrapper)"

# 4. Failure recovery
git merge feat/TC-600-failure-recovery --no-ff -m "Merge TC-600: Failure recovery (retry, backoff, circuit breakers)"
```

**Expected Changes:**
- `tests/unit/test_determinism.py` (47 tests)
- `conftest.py` (pytest fixtures)
- `src/launch/observability/` (evidence_packager, reports_index, run_summary)
- `src/launch/util/subprocess.py` (subprocess wrapper)
- `tests/unit/util/test_subprocess.py`
- Retry/backoff utilities

**Gate Checkpoint 5 (FINAL):**
```bash
# Run FULL gate suite
python tools/validate_swarm_ready.py

# Run FULL test suite with determinism
set PYTHONHASHSEED=0
python -m pytest -q

# Run determinism-specific tests
python -m pytest tests/unit/test_determinism.py -v

# Generate evidence package (verify TC-580)
python -c "from pathlib import Path; from src.launch.observability.reports_index import generate_reports_index; idx = generate_reports_index(Path('reports/agents')); print(idx.to_json())"

# Expected: All tests pass, evidence generation works
```

**Success Criteria:**
- ✅ Determinism tests: 47/47 PASS
- ✅ Observability tests: 67/67 PASS
- ✅ Security tests: PASS
- ✅ Full test suite: 528+ tests PASS
- ✅ Gate I (Determinism): PASS
- ✅ Evidence packaging: Functional

---

## Post-Merge Validation

### Final System Check

```bash
# 1. Activate venv
.venv\Scripts\activate

# 2. Run complete validation
python tools/validate_swarm_ready.py > reports/post_impl/20260128_131602/final_validation.txt

# 3. Run complete test suite
set PYTHONHASHSEED=0
python -m pytest -q > reports/post_impl/20260128_131602/final_tests.txt

# 4. Verify all scripts
launch_run --help
launch_mcp --help
launch_validate --help

# 5. Generate final reports index
python -c "from pathlib import Path; from src.launch.observability.reports_index import generate_reports_index; idx = generate_reports_index(Path('reports/agents')); print(idx.to_json())" > reports/post_impl/20260128_131602/final_reports_index.json
```

### Expected Final State

**Gates Status:**
- ✅ 16/21 gates PASSING (same as pre-merge)
- ❌ 5/21 gates FAILING (same failures, documented as non-blocking)

**Test Status:**
- ✅ 528+ tests PASSING (100%)
- ❌ 0 tests FAILING

**Branch Status:**
- ✅ All 41 feature branches merged
- ✅ main branch at new HEAD
- ✅ All feature branches can be deleted (archive first)

---

## Merge Execution Checklist

### Pre-Merge

- [ ] All feature branches exist and are ahead of main
- [ ] Working tree is clean
- [ ] .venv is activated
- [ ] Base commit recorded: c8dab0c
- [ ] Backup created (optional): `git tag pre-merge-backup main`

### Wave 1: Foundation

- [ ] Merge TC-100, TC-200, TC-201, TC-250
- [ ] Run Gate Checkpoint 1
- [ ] Record wave 1 commit: `git rev-parse HEAD`
- [ ] Update post_state.json

### Wave 2: Core Infrastructure

- [ ] Merge TC-300, TC-500
- [ ] Run Gate Checkpoint 2
- [ ] Record wave 2 commit
- [ ] Update post_state.json

### Wave 3: Workers

- [ ] Merge W1 branches (TC-400 series)
- [ ] Merge W2 branches (TC-410 series)
- [ ] Merge W3 branches (TC-420 series)
- [ ] Merge W4-W9 branches
- [ ] Run Gate Checkpoint 3
- [ ] Record wave 3 commit
- [ ] Update post_state.json

### Wave 4: Services & Interfaces

- [ ] Merge MCP branches (TC-510 series)
- [ ] Merge Telemetry branches (TC-520 series)
- [ ] Merge CLI/Content branches (TC-530, TC-540, TC-550)
- [ ] Run Gate Checkpoint 4
- [ ] Record wave 4 commit
- [ ] Update post_state.json

### Wave 5: Quality & Observability

- [ ] Merge TC-560, TC-580, TC-590, TC-600
- [ ] Run Gate Checkpoint 5 (FINAL)
- [ ] Record wave 5 commit (FINAL)
- [ ] Update post_state.json (COMPLETE)

### Post-Merge

- [ ] Run final system validation
- [ ] Generate final reports
- [ ] Archive feature branches
- [ ] Push main to remote
- [ ] Create release tag: `v1.0.0`
- [ ] Update documentation

---

## Rollback Procedures

### Wave-Level Rollback

If a wave fails gate checkpoint:

```bash
# 1. Record failure
echo "Wave X failed at $(date)" >> reports/post_impl/20260128_131602/failures.log

# 2. Rollback to pre-wave commit
git reset --hard <wave-X-pre-commit>

# 3. Create fix branch
git checkout -b fix/wave-X-gate-failure

# 4. Investigate and fix
# ... fix code ...

# 5. Re-run wave
# ... re-execute wave merge commands ...
```

### Complete Rollback

If multiple waves fail or critical issue discovered:

```bash
# 1. Return to base
git reset --hard c8dab0c

# 2. Optional: Use backup tag
git reset --hard pre-merge-backup

# 3. Investigate root cause
# ... analyze failures ...

# 4. Restart merge process
# ... follow plan from Wave 1 ...
```

---

## Success Metrics

### Merge Completion

- [x] Base snapshot captured
- [ ] Wave 1 completed (4 branches)
- [ ] Wave 2 completed (2 branches)
- [ ] Wave 3 completed (31 branches)
- [ ] Wave 4 completed (12 branches)
- [ ] Wave 5 completed (4 branches)
- [ ] **Total: 53 merges** (41 feature branches + 12 sub-features)

### Quality Gates

- [ ] Gate checkpoints: 5/5 executed
- [ ] Test suite: 100% pass rate maintained
- [ ] No regressions introduced
- [ ] Documentation updated

### System Health

- [ ] All CLI commands functional
- [ ] All MCP endpoints operational
- [ ] Evidence packaging working
- [ ] Determinism enforced

---

## Timeline Estimate

**Optimistic:** 3 hours
- Wave 1: 20 min
- Wave 2: 15 min
- Wave 3: 90 min (largest wave)
- Wave 4: 30 min
- Wave 5: 25 min

**Realistic:** 4-5 hours
- Includes gate checkpoint execution (10-15 min each)
- Includes merge conflict resolution (estimate 10-20 conflicts)
- Includes validation and verification

**Pessimistic:** 6-8 hours
- Major conflicts requiring investigation
- Gate failures requiring fixes
- Multiple rollbacks and retries

---

## Notes

### Known Issues

1. **Gate R (Subprocess wrapper):** 2 files with direct subprocess calls (clone_helpers.py, gate_13_hugo_build.py). Acceptable for v1.0, fix in v1.1.

2. **Gate O (Budget config):** Incomplete budget configuration. Non-blocking for v1.0.

3. **Gate D (Markdown links):** Broken links in documentation. Low priority, fix post-merge.

4. **Gate B (Taskcard paths):** 12 taskcards with frontmatter/body mismatches. Documentation drift, fix post-merge.

5. **OQ-BATCH-001:** Batch execution not implemented (deferred). System works for single-run use cases.

### Architectural Decisions

- **Single-run execution:** Delivered as v1.0 baseline
- **Batch execution:** Deferred to v1.1 pending user feedback
- **MCP tools structure:** Integrated into server.py instead of separate tools/ directory
- **Determinism:** Full enforcement via PYTHONHASHSEED=0 and test fixtures

---

**Merge Plan Ready**
**Next Step:** Execute Wave 1 merges and gate checkpoint.
