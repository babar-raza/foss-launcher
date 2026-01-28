# Taskcard-to-Spec Trace

**Generated**: 2026-01-27
**Auditor**: AGENT_P
**Purpose**: Map all taskcards to their governing specs and verify completeness

---

## Trace Summary

- **Total Taskcards**: 41
- **Total Specs Covered**: 35+
- **Coverage**: 100% (all specs have implementing taskcards)
- **Orphaned Taskcards**: 0 (all taskcards cite spec authority)
- **Missing Implementation**: 39 (all Ready for implementation; 2 Done)

---

## Core Contracts

| Taskcard ID | Title | Spec Coverage | Status | Implementation Complete | Issues |
|-------------|-------|---------------|--------|------------------------|--------|
| TC-100 | Bootstrap repo | specs/29 (project structure), specs/19 (toolchain), specs/25 (frameworks), specs/10 (determinism) | Ready | ❌ Not started | None |
| TC-200 | Schemas and IO | specs/schemas/*, specs/01 (system contract), specs/10 (determinism) | Ready | ❌ Not started | None |
| TC-201 | Emergency mode | specs/34 (compliance), plans/policies/no_manual_content_edits.md | Ready | ❌ Not started | None |
| TC-250 | Shared libs governance | specs/34 (compliance), plans/taskcards/00_TASKCARD_CONTRACT.md | Ready | ❌ Not started | None |
| TC-300 | Orchestrator | specs/state-graph.md, specs/state-management.md, specs/11 (state/events), specs/28 (coordination), specs/21 (worker contracts) | Ready | ❌ Not started | **CRITICAL**: Required for all workers |

**Notes**:
- TC-300 is **prerequisite** for all workers (W1-W9)
- TC-200 is **shared library owner** for io/util (write fence enforced)
- TC-250 is **shared library owner** for models (write fence enforced)

---

## Worker 1 — RepoScout (Inputs & Ingestion)

| Taskcard ID | Title | Spec Coverage | Status | Implementation Complete | Issues |
|-------------|-------|---------------|--------|------------------------|--------|
| TC-401 | Clone and resolve SHAs | specs/21 (W1 contract), specs/02 (repo ingestion), specs/34 (Guarantee A: pinned refs) | Ready | ❌ Not started | None |
| TC-402 | Repo fingerprint | specs/21 (W1 contract), specs/02 (repo ingestion), specs/26 (repo adapters), specs/10 (determinism) | Ready | ❌ Not started | None |
| TC-403 | Frontmatter discovery | specs/21 (W1 contract), specs/18 (site layout), specs/26 (repo adapters), specs/examples/frontmatter_models.md | Ready | ❌ Not started | None |
| TC-404 | Hugo site context | specs/21 (W1 contract), specs/31 (hugo config), specs/18 (site layout), specs/30 (site/workflow repos) | Ready | ❌ Not started | None |
| TC-400 | W1 RepoScout (epic) | specs/21 (W1 contract), all TC-401..404 specs | Ready | ❌ Not started | Depends on TC-401..404 |

**Artifact Outputs**:
- `repo_inventory.json` (schema: specs/schemas/repo_inventory.schema.json)
- `frontmatter_contract.json` (schema: specs/schemas/frontmatter_contract.schema.json)
- `site_context.json` (schema: specs/schemas/site_context.schema.json)

---

## Worker 2 — FactsBuilder (Facts, Evidence, TruthLock)

| Taskcard ID | Title | Spec Coverage | Status | Implementation Complete | Issues |
|-------------|-------|---------------|--------|------------------------|--------|
| TC-411 | Facts extract | specs/21 (W2 contract), specs/03 (product facts), specs/10 (determinism) | Ready | ❌ Not started | None |
| TC-412 | Evidence map | specs/21 (W2 contract), specs/03 (product facts), specs/04 (claims compiler) | Ready | ❌ Not started | None |
| TC-413 | Truth lock compile | specs/21 (W2 contract), specs/04 (claims compiler), specs/23 (claim markers) | Ready | ❌ Not started | None |
| TC-410 | W2 FactsBuilder (epic) | specs/21 (W2 contract), all TC-411..413 specs | Ready | ❌ Not started | Depends on TC-411..413 |

**Artifact Outputs**:
- `product_facts.json` (schema: specs/schemas/product_facts.schema.json)
- `evidence_map.json` (schema: specs/schemas/evidence_map.schema.json)
- `truth_lock_report.json` (schema: specs/schemas/truth_lock_report.schema.json)

**Validation Gates**:
- Gate 9 (TruthLock) — Validates all claims link to EvidenceMap

---

## Worker 3 — SnippetCurator

| Taskcard ID | Title | Spec Coverage | Status | Implementation Complete | Issues |
|-------------|-------|---------------|--------|------------------------|--------|
| TC-421 | Snippet inventory | specs/21 (W3 contract), specs/05 (example curation), specs/10 (determinism) | Ready | ❌ Not started | None |
| TC-422 | Snippet selection rules | specs/21 (W3 contract), specs/05 (example curation) | Ready | ❌ Not started | None |
| TC-420 | W3 SnippetCurator (epic) | specs/21 (W3 contract), all TC-421..422 specs | Ready | ❌ Not started | Depends on TC-421..422 |

**Artifact Outputs**:
- `snippet_catalog.json` (schema: specs/schemas/snippet_catalog.schema.json)

**Validation Gates**:
- Gate 8 (Snippet checks) — Validates snippet syntax, optionally runs in container

---

## Worker 4 — IAPlanner (Page Planning)

| Taskcard ID | Title | Spec Coverage | Status | Implementation Complete | Issues |
|-------------|-------|---------------|--------|------------------------|--------|
| TC-430 | W4 IAPlanner | specs/21 (W4 contract), specs/06 (page planning), specs/22 (navigation), specs/33 (public URL mapping), specs/32 (platform layout) | Ready | ❌ Not started | None |

**Artifact Outputs**:
- `page_plan.json` (schema: specs/schemas/page_plan.schema.json)

**Validation Gates**:
- Gate 4 (content_layout_platform) — Validates V2 platform paths

---

## Worker 5 — SectionWriter (Content Drafting)

| Taskcard ID | Title | Spec Coverage | Status | Implementation Complete | Issues |
|-------------|-------|---------------|--------|------------------------|--------|
| TC-440 | W5 SectionWriter | specs/21 (W5 contract), specs/07 (section templates), specs/20 (rulesets/templates), specs/23 (claim markers), specs/10 (determinism) | Ready | ❌ Not started | None |

**Artifact Outputs**:
- Draft Markdown files with claim markers (written to RUN_DIR/work/site/)

**Validation Gates**:
- TemplateTokenLint gate — Detects unresolved tokens (`__PLATFORM__`, etc.)

---

## Worker 6 — LinkerAndPatcher (Patch Engine)

| Taskcard ID | Title | Spec Coverage | Status | Implementation Complete | Issues |
|-------------|-------|---------------|--------|------------------------|--------|
| TC-450 | W6 LinkerAndPatcher | specs/21 (W6 contract), specs/08 (patch engine), specs/22 (navigation), specs/34 (Guarantee G: change budgets) | Ready | ❌ Not started | None |

**Artifact Outputs**:
- `patch_bundle.json` (schema: specs/schemas/patch_bundle.schema.json)

**Validation Gates**:
- Gate O (change budgets) — Enforces max_lines_per_file, max_files_changed

**Runtime Enforcers**:
- diff_analyzer.py — Detects formatting-only diffs, enforces change budgets

---

## Worker 7 — Validator (Validation Gates)

| Taskcard ID | Title | Spec Coverage | Status | Implementation Complete | Issues |
|-------------|-------|---------------|--------|------------------------|--------|
| TC-460 | W7 Validator | specs/21 (W7 contract), specs/09 (validation gates), specs/04 (truth lock), specs/19 (toolchain CI), specs/31 (hugo config) | Ready | ❌ Not started | **CRITICAL**: Required for all gates |
| TC-570 | Validation gates ext | specs/09 (validation gates), specs/18 (site layout), specs/31 (hugo config), specs/32 (platform layout), specs/10 (determinism) | Ready | ❌ Not started | None |
| TC-571 | Policy gate: no manual edits | specs/09 (validation gates), plans/policies/no_manual_content_edits.md | Ready | ❌ Not started | None |

**Artifact Outputs**:
- `validation_report.json` (schema: specs/schemas/validation_report.schema.json)

**Validation Gates Implemented**:
- Gate 1 (schema validation) — All artifacts validate against schemas
- Gate 2 (markdown lint + frontmatter) — markdownlint, frontmatter contract
- Gate 3 (Hugo config compatibility) — Site context + hugo_config checks
- Gate 4 (platform layout) — V2 path validation (NEW)
- Gate 5 (Hugo build) — hugo build --environment production
- Gate 6 (internal links) — Relative links and anchors
- Gate 7 (external links) — lychee or equivalent (optional)
- Gate 8 (snippet checks) — Snippet syntax + execution (optional)
- Gate 9 (TruthLock) — All claims link to evidence
- Gate 10 (consistency) — product_name, repo_url, canonical URL, required headings
- TemplateTokenLint gate — Unresolved tokens (`__PLATFORM__`, `__LOCALE__`)
- Universality gates — Tier compliance, limitations honesty, distribution correctness, no hidden inference

**Notes**:
- TC-460 is **critical path** for all validation
- TC-570 extends TC-460 with platform layout, timeout enforcement, token linting

---

## Worker 8 — Fixer (Fix Loop)

| Taskcard ID | Title | Spec Coverage | Status | Implementation Complete | Issues |
|-------------|-------|---------------|--------|------------------------|--------|
| TC-470 | W8 Fixer | specs/21 (W8 contract), specs/09 (validation gates), specs/34 (compliance) | Ready | ❌ Not started | None |

**Notes**:
- Consumes validation_report.json from TC-460
- Iterates on single issue per invocation
- Bounded by max_fix_attempts in run_config

---

## Worker 9 — PRManager (PR & Release)

| Taskcard ID | Title | Spec Coverage | Status | Implementation Complete | Issues |
|-------------|-------|---------------|--------|------------------------|--------|
| TC-480 | W9 PRManager | specs/21 (W9 contract), specs/12 (PR/release), specs/17 (commit service), specs/16 (telemetry), specs/34 (Guarantee L: rollback) | Ready | ❌ Not started | **REQUIRED**: Rollback metadata (base_ref, run_id, rollback_steps, affected_paths) |

**Artifact Outputs**:
- `pr.json` (schema: specs/schemas/pr.schema.json)
  - **REQUIRED fields** (Guarantee L): base_ref, run_id, rollback_steps, affected_paths

**Notes**:
- Taskcard lines 36-41 specify rollback fields are REQUIRED in prod profile
- Validator will fail if pr.json missing rollback metadata (Guarantee L enforcement)

---

## Cross-Cutting Taskcards

| Taskcard ID | Title | Spec Coverage | Status | Implementation Complete | Issues |
|-------------|-------|---------------|--------|------------------------|--------|
| TC-500 | Clients & Services | specs/15 (LLM providers), specs/16 (telemetry), specs/17 (commit service), specs/34 (Guarantee D: network allowlist) | Ready | ❌ Not started | **Shared lib owner**: clients/** |
| TC-510 | MCP server | specs/14 (MCP endpoints), specs/24 (MCP tool schemas) | Ready | ❌ Not started | None |
| TC-511 | MCP quickstart (product URL) | specs/14 (MCP endpoints), specs/33 (public URL mapping) | Ready | ❌ Not started | Depends on TC-510, TC-540 |
| TC-512 | MCP quickstart (GitHub repo) | specs/14 (MCP endpoints), specs/02 (repo ingestion) | Ready | ❌ Not started | Depends on TC-510, TC-540, TC-401 |
| TC-520 | Pilots & regression | specs/13 (pilots), specs/10 (determinism) | Ready | ❌ Not started | None |
| TC-522 | Pilot E2E CLI | specs/13 (pilots), specs/10 (determinism) | Ready | ❌ Not started | Depends on TC-520, TC-530, TC-560 |
| TC-523 | Pilot E2E MCP | specs/13 (pilots), specs/10 (determinism) | Ready | ❌ Not started | Depends on TC-520, TC-510, TC-560 |
| TC-530 | CLI entrypoints | specs/19 (toolchain CI), specs/29 (project structure), specs/11 (state/events), specs/12 (PR/release) | Ready | ❌ Not started | None |
| TC-540 | Content path resolver | specs/32 (platform layout), specs/18 (site layout), specs/33 (public URL mapping) | Ready | ❌ Not started | None |
| TC-550 | Hugo config awareness | specs/31 (hugo config), specs/18 (site layout) | Ready | ❌ Not started | None |
| TC-560 | Determinism harness | specs/10 (determinism), specs/34 (Guarantee I: non-flaky tests) | Ready | ❌ Not started | None |
| TC-580 | Observability | specs/16 (telemetry), specs/11 (state/events) | Ready | ❌ Not started | None |
| TC-590 | Security & secrets | specs/34 (Guarantee E: secret hygiene) | Ready | ❌ Not started | **PENDING**: Secret redaction runtime enforcer |
| TC-600 | Failure recovery | specs/11 (state/events), specs/34 (Guarantee L: rollback) | Ready | ❌ Not started | None |
| TC-601 | Windows reserved names | specs/18 (site layout), specs/34 (compliance) | Done | ✅ Implemented | None |
| TC-602 | Specs README sync | specs/README.md navigation | Done | ✅ Implemented | None |

---

## Spec-to-Taskcard Mapping (Critical Specs)

### State Management & Orchestration

| Spec | Implementing Taskcards | Status | Completeness |
|------|------------------------|--------|--------------|
| `specs/state-graph.md` | TC-300 (orchestrator graph) | Ready | **NOT STARTED** — Critical path blocker |
| `specs/state-management.md` | TC-300 (state persistence) | Ready | **NOT STARTED** — Critical path blocker |
| `specs/28_coordination_and_handoffs.md` | TC-300 (worker orchestration) | Ready | **NOT STARTED** — Critical path blocker |
| `specs/11_state_and_events.md` | TC-300 (event log), TC-200 (event schema) | Ready | **NOT STARTED** |

**CRITICAL**: TC-300 is **prerequisite** for all workers. Must be implemented first.

### Worker Contracts

| Spec | Implementing Taskcards | Status | Completeness |
|------|------------------------|--------|--------------|
| `specs/21_worker_contracts.md` | TC-400 (W1), TC-410 (W2), TC-420 (W3), TC-430 (W4), TC-440 (W5), TC-450 (W6), TC-460 (W7), TC-470 (W8), TC-480 (W9) | Ready | **ALL 9 WORKERS MAPPED** |

**Status**: All worker taskcards Ready, waiting for TC-300 (orchestrator).

### Validation & Compliance

| Spec | Implementing Taskcards | Status | Completeness |
|------|------------------------|--------|--------------|
| `specs/09_validation_gates.md` | TC-460 (validator), TC-570 (gates ext), TC-571 (policy gate) | Ready | **NOT STARTED** — Runtime gates pending |
| `specs/34_strict_compliance_guarantees.md` | Multiple (A-L guarantees) | Mixed | **Preflight gates: ✅ Done; Runtime enforcers: Partial** |

**Compliance Guarantee Status**:
- **A (Pinned refs)**: Gate J ✅ Implemented, runtime rejection pending TC-300
- **B (Hermetic)**: path_validation.py ✅ Implemented
- **C (Supply chain)**: Gate K ✅ Implemented
- **D (Network allowlist)**: http.py ✅ Implemented (TC-500 extends)
- **E (Secret hygiene)**: Gate L ✅ Implemented (preflight), TC-590 pending (runtime redaction)
- **F (Budgets)**: Gate O ✅ Implemented (preflight), budget_tracker.py ✅ Implemented
- **G (Change budgets)**: diff_analyzer.py ✅ Implemented
- **H (CI parity)**: Gate Q ✅ Implemented
- **I (Non-flaky tests)**: Gate H ✅ Implemented, TC-560 extends (determinism harness)
- **J (No untrusted code)**: Gate R ✅ Implemented, subprocess.py ✅ Implemented
- **K (Version locking)**: Gates B, P ✅ Implemented
- **L (Rollback)**: TC-480 pending (pr.json rollback fields specified in taskcard)

### Schemas & Data Models

| Spec | Implementing Taskcards | Status | Completeness |
|------|------------------------|--------|--------------|
| `specs/schemas/run_config.schema.json` | TC-200 (schema validation) | Ready | **NOT STARTED** |
| `specs/schemas/validation_report.schema.json` | TC-460 (validator output) | Ready | **NOT STARTED** |
| `specs/schemas/product_facts.schema.json` | TC-411 (facts extract) | Ready | **NOT STARTED** |
| `specs/schemas/pr.schema.json` | TC-480 (PRManager output) | Ready | **NOT STARTED** |
| `specs/schemas/frontmatter_contract.schema.json` | TC-403 (frontmatter discovery) | Ready | **NOT STARTED** |
| `specs/schemas/site_context.schema.json` | TC-404 (Hugo site context) | Ready | **NOT STARTED** |

**Status**: All schema-producing taskcards Ready, waiting for TC-200 (schema validation helpers).

### Platform & Layout

| Spec | Implementing Taskcards | Status | Completeness |
|------|------------------------|--------|--------------|
| `specs/32_platform_aware_content_layout.md` | TC-540 (path resolver), TC-403 (frontmatter), TC-404 (site context), TC-570 (platform gate) | Ready | **NOT STARTED** |
| `specs/18_site_repo_layout.md` | TC-404 (site context), TC-540 (path resolver) | Ready | **NOT STARTED** |
| `specs/31_hugo_config_awareness.md` | TC-404 (Hugo scan), TC-550 (Hugo awareness ext) | Ready | **NOT STARTED** |

**Validation**: Gate 4 (content_layout_platform) validates V2 paths (TC-570).

### PR & Release

| Spec | Implementing Taskcards | Status | Completeness |
|------|------------------------|--------|--------------|
| `specs/12_pr_and_release.md` | TC-480 (PRManager) | Ready | **NOT STARTED** — Rollback metadata specified |
| `specs/17_github_commit_service.md` | TC-480 (commit service client), TC-500 (service implementation) | Ready | **NOT STARTED** |

**Rollback Requirement**: TC-480 taskcard lines 36-41 specify REQUIRED rollback fields (base_ref, run_id, rollback_steps, affected_paths) per Guarantee L.

---

## Coverage Gaps Analysis

### ✅ COMPLETE COVERAGE

All 35+ binding specs have implementing taskcards. No orphaned specs detected.

### ❌ MISSING IMPLEMENTATION (Expected)

**Status**: All 39 "Ready" taskcards are awaiting implementation (pre-implementation phase).

**Critical Path**:
1. **TC-100** (bootstrap) → **TC-200** (schemas/IO) → **TC-300** (orchestrator)
2. All workers (TC-400..480) depend on TC-200, TC-300
3. Validation (TC-460, TC-570) depends on workers
4. Pilots (TC-522, TC-523) depend on all above

**Estimated Dependency Depth**:
- Level 0: TC-100 (no dependencies)
- Level 1: TC-200, TC-201, TC-250 (depend on TC-100)
- Level 2: TC-300, TC-500 (depend on TC-200)
- Level 3: TC-401..404, TC-411..413, TC-421..422, TC-530, TC-510, TC-540, TC-550, TC-560 (depend on TC-300)
- Level 4: TC-400, TC-410, TC-420 (epic wrappers), TC-430, TC-440, TC-450 (depend on Level 3)
- Level 5: TC-460, TC-570 (depend on TC-450, TC-550)
- Level 6: TC-470, TC-480, TC-571 (depend on TC-460, TC-570)
- Level 7: TC-520, TC-580, TC-590, TC-600 (depend on TC-480)
- Level 8: TC-522, TC-523 (E2E pilots, depend on all above)

---

## Traceability Matrix Cross-Check

**Source**: `plans/traceability_matrix.md:1-543`

**Verified**:
- ✅ All specs listed in traceability matrix have implementing taskcards
- ✅ All taskcards cite spec authority
- ✅ Schemas mapped to governing specs + validating gates
- ✅ Gates mapped to validators + spec references
- ✅ Runtime enforcers mapped to guarantees + taskcards

**Cross-Reference**:
- Plans/traceability_matrix.md lines 7-543 → All taskcards audited
- Plans/taskcards/STATUS_BOARD.md lines 19-61 → All taskcards tracked
- Plans/taskcards/INDEX.md lines 8-76 → All taskcards indexed

**Consistency**: ✅ **100% CONSISTENT** (no conflicts between documents)

---

## Implementation Roadmap (Suggested)

Based on dependency analysis and critical path:

### Phase 1: Foundation (TC-100, TC-200)
- **TC-100** (bootstrap) — 0 dependencies
- **TC-200** (schemas/IO) — Depends on TC-100
- **TC-201** (emergency mode) — Depends on TC-200
- **TC-250** (shared libs governance) — Depends on TC-200

### Phase 2: Orchestrator (TC-300)
- **TC-300** (orchestrator) — Depends on TC-200 (CRITICAL PATH)

### Phase 3: Workers Parallel (TC-401..422, TC-500, TC-530, TC-540, TC-550, TC-560)
All depend on TC-300, can execute in parallel:
- **W1 microtasks**: TC-401, TC-402, TC-403, TC-404 (parallel safe)
- **W2 microtasks**: TC-411, TC-412, TC-413 (parallel safe)
- **W3 microtasks**: TC-421, TC-422 (parallel safe)
- **Cross-cutting**: TC-500 (services), TC-530 (CLI), TC-540 (path resolver), TC-550 (Hugo awareness), TC-560 (determinism harness)

### Phase 4: Epic Wrappers + Content Pipeline (TC-400, TC-410, TC-420, TC-430, TC-440, TC-450)
- **TC-400** (W1 epic) — Depends on TC-401..404
- **TC-410** (W2 epic) — Depends on TC-411..413
- **TC-420** (W3 epic) — Depends on TC-421..422
- **TC-430** (W4 IAPlanner) — Depends on TC-410, TC-420
- **TC-440** (W5 SectionWriter) — Depends on TC-430
- **TC-450** (W6 LinkerAndPatcher) — Depends on TC-440

### Phase 5: Validation (TC-460, TC-570, TC-571)
- **TC-460** (W7 Validator) — Depends on TC-450
- **TC-570** (validation gates ext) — Depends on TC-460, TC-550
- **TC-571** (policy gate) — Depends on TC-460, TC-201

### Phase 6: Fix & Release (TC-470, TC-480, TC-510, TC-511, TC-512)
- **TC-470** (W8 Fixer) — Depends on TC-460
- **TC-480** (W9 PRManager) — Depends on TC-470
- **TC-511** (MCP quickstart product URL) — Depends on TC-510, TC-540
- **TC-512** (MCP quickstart GitHub repo) — Depends on TC-510, TC-540, TC-401

### Phase 7: Observability & Hardening (TC-520, TC-580, TC-590, TC-600)
- **TC-520** (pilots/regression) — Depends on TC-300, TC-460
- **TC-580** (observability) — Depends on TC-300, TC-460
- **TC-590** (security/secrets) — Depends on TC-300
- **TC-600** (failure recovery) — Depends on TC-300

### Phase 8: E2E Validation (TC-522, TC-523)
- **TC-522** (pilot E2E CLI) — Depends on TC-520, TC-530, TC-560
- **TC-523** (pilot E2E MCP) — Depends on TC-520, TC-510, TC-560

---

## Conclusion

**Traceability**: ✅ **100% COMPLETE**

All specs mapped to implementing taskcards. All taskcards cite spec authority. No orphaned specs or taskcards.

**Implementation Status**: 39 Ready, 2 Done (TC-601, TC-602), 0 In-Progress

**Critical Path**: TC-100 → TC-200 → TC-300 → (all workers in parallel)

**Estimated Implementation Depth**: 8 levels (TC-100 → TC-522/523)

**Swarm Readiness**: ✅ **READY** (no path overlaps, clear dependencies)

---

**Trace Generated**: 2026-01-27
**Auditor**: AGENT_P
**Source Documents**: plans/traceability_matrix.md, plans/taskcards/*.md, plans/taskcards/STATUS_BOARD.md
