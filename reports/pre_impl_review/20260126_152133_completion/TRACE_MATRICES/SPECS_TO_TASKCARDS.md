# Binding Specs → Taskcards Traceability

**Generated**: 2026-01-26
**Purpose**: Map every binding spec to implementing and validating taskcards

## Taskcard Registry

**Total Taskcards**: 41 (TC-100 through TC-602)

**Status Distribution** (from [plans/taskcards/STATUS_BOARD.md](/plans/taskcards/STATUS_BOARD.md)):
- Ready: 41 taskcards (100%)
- All taskcards have valid version locks (Gate P passing)

---

## Specs → Taskcards Mapping

### 00_environment_policy.md

**Implementing Taskcards**:
- **TC-100**: Bootstrap repo (sets up .venv, enforces policy)

**Validating Taskcards**:
- Gate 0 (not a taskcard, but validates .venv policy)

**Coverage**: ✅ Complete

---

### 00_overview.md

**Implementing Taskcards**:
- **TC-300**: Orchestrator (implements architecture from overview)
- **TC-100**: Repo bootstrap (implements project structure)

**Validating Taskcards**:
- All pilots (TC-522, TC-523) validate overall architecture

**Coverage**: ✅ Complete

---

### 01_system_contract.md

**Implementing Taskcards**:
- **TC-300**: Orchestrator (enforces system-wide contracts)
- **TC-200**: Schemas and I/O (contract enforcement)
- **TC-201**: Emergency mode for manual edits

**Validating Taskcards**:
- **TC-460**: Validator W7 (validates contracts)
- **TC-570**: Validation gates extension (enforces contracts)
- **TC-571**: Policy gate (no manual edits)

**Coverage**: ✅ Complete

---

### 02_repo_ingestion.md

**Implementing Taskcards**:
- **TC-401**: Clone and resolve SHAs
- **TC-402**: Repo fingerprint and inventory

**Validating Taskcards**:
- **TC-522**, **TC-523**: E2E pilots validate ingestion

**Coverage**: ✅ Complete

---

### 03_product_facts_and_evidence.md

**Implementing Taskcards**:
- **TC-411**: Facts extract catalog
- **TC-412**: Evidence map linking

**Validating Taskcards**:
- **TC-460**: Validator W7 (validates evidence map)

**Coverage**: ✅ Complete

---

### 04_claims_compiler_truth_lock.md

**Implementing Taskcards**:
- **TC-413**: Truth lock compile
- **TC-460**: Truth-lock gate integration

**Validating Taskcards**:
- **TC-460**: Validator W7 (TruthLock gate)
- **TC-570**: Validation gates extension (claim validation)

**Coverage**: ✅ Complete

---

### 05_example_curation.md

**Implementing Taskcards**:
- **TC-421**: Snippet inventory and tagging
- **TC-422**: Snippet selection rules

**Validating Taskcards**:
- **TC-460**: Validator W7 (snippet validation)

**Coverage**: ✅ Complete

---

### 06_page_planning.md

**Implementing Taskcards**:
- **TC-430**: IA planner W4 (page inventory, launch tiers)

**Validating Taskcards**:
- **TC-460**: Validator W7 (validates page plan)

**Coverage**: ✅ Complete

---

### 07_section_templates.md

**Implementing Taskcards**:
- **TC-440**: Section writer W5 (template selection + usage)

**Validating Taskcards**:
- **TC-460**: Validator W7 (template usage validation)
- **TC-570**: Template token lint

**Coverage**: ✅ Complete

---

### 08_patch_engine.md

**Implementing Taskcards**:
- **TC-450**: Linker and patcher W6 (patch engine)
- **TC-540**: Content path resolver (path safety)

**Validating Taskcards**:
- **TC-571**: Policy gate (validates no manual edits, patch safety)
- **TC-560**: Determinism harness (idempotency)

**Coverage**: ✅ Complete

---

### 09_validation_gates.md

**Implementing Taskcards**:
- **TC-460**: Validator W7 (core validation framework)
- **TC-570**: Validation gates extension (additional gates)
- **TC-571**: Policy gate (no manual edits gate)

**Validating Taskcards**:
- All 21 preflight gates validate the validation system itself
- **TC-522**, **TC-523**: E2E validation in pilots

**Coverage**: ✅ Complete

---

### 10_determinism_and_caching.md

**Implementing Taskcards**:
- **TC-200**: Schemas and I/O (deterministic serialization)
- **TC-560**: Determinism harness (hashing, stable ordering)
- **TC-401..TC-404**: RepoScout micro-taskcards (deterministic ingestion)

**Validating Taskcards**:
- **TC-560**: Self-validating (harness tests determinism)
- **TC-460**: Validator W7
- **TC-522**, **TC-523**: CLI/MCP determinism proofs

**Coverage**: ✅ Complete

---

### 11_state_and_events.md

**Implementing Taskcards**:
- **TC-300**: Orchestrator (state machine, event emission)
- **TC-200**: Schemas and I/O (state + event schemas)

**Validating Taskcards**:
- **TC-460**: Validator W7 (validates state transitions)

**Coverage**: ✅ Complete

---

### 12_pr_and_release.md

**Implementing Taskcards**:
- **TC-480**: PR manager W9 (PR creation, deployment)

**Validating Taskcards**:
- **TC-522**, **TC-523**: E2E pilots (validate PR flow)

**Coverage**: ✅ Complete

---

### 13_pilots.md

**Implementing Taskcards**:
- **TC-520**: Pilots and regression (pilot framework)

**Validating Taskcards**:
- **TC-522**: CLI E2E pilot (pilot-aspose-3d-foss-python)
- **TC-523**: MCP E2E pilot (pilot-aspose-note-foss-python)

**Coverage**: ✅ Complete (2 pilots, 2 archetypes)

---

### 14_mcp_endpoints.md

**Implementing Taskcards**:
- **TC-510**: MCP server (core MCP implementation)
- **TC-511**: MCP quickstart: product URL
- **TC-512**: MCP quickstart: GitHub repo URL

**Validating Taskcards**:
- **TC-523**: MCP E2E pilot

**Coverage**: ✅ Complete

---

### 15_llm_providers.md

**Implementing Taskcards**:
- **TC-500**: Clients and services (LLM client abstraction)

**Validating Taskcards**:
- **TC-522**, **TC-523**: E2E pilots (validate LLM usage)

**Coverage**: ✅ Complete

---

### 16_local_telemetry_api.md

**Implementing Taskcards**:
- **TC-500**: Clients and services (telemetry client)

**Validating Taskcards**:
- **TC-580**: Observability and evidence bundle (validates telemetry)

**Coverage**: ✅ Complete

---

### 17_github_commit_service.md

**Implementing Taskcards**:
- **TC-500**: Clients and services (GitHub commit client)
- **TC-480**: PR manager W9 (uses commit service)

**Validating Taskcards**:
- **TC-522**, **TC-523**: E2E pilots (validate commit flow)

**Coverage**: ✅ Complete

---

### 18_site_repo_layout.md

**Implementing Taskcards**:
- **TC-404**: Hugo site context + build matrix (site layout detection)
- **TC-540**: Content path resolver (layout-aware path resolution)
- **TC-430**: IA planner W4 (layout-aware planning)

**Validating Taskcards**:
- **TC-460**, **TC-570**: Validators (layout validation)

**Coverage**: ✅ Complete

---

### 19_toolchain_and_ci.md

**Implementing Taskcards**:
- **TC-100**: Bootstrap repo (toolchain.lock.yaml, CI setup)
- **TC-530**: CLI entrypoints and runbooks (CLI commands)
- **TC-560**: Determinism harness (test framework)

**Validating Taskcards**:
- Gate A1 (toolchain lock validation)
- Gate Q (CI parity)

**Coverage**: ✅ Complete

---

### 20_rulesets_and_templates_registry.md

**Implementing Taskcards**:
- **TC-100**: Bootstrap repo (ruleset/template versioning in repo)
- **TC-440**: Section writer W5 (template selection)
- **TC-200**: Schemas and I/O (ruleset schema validation)

**Validating Taskcards**:
- Gate A1 (spec pack validation includes ruleset validation)
- **TC-460**: Validator W7

**Coverage**: ✅ Complete

---

### 23_claim_markers.md

**Implementing Taskcards**:
- **TC-413**: Truth lock compile (claim ID assignment)
- **TC-440**: Section writer W5 (claim marker insertion)

**Validating Taskcards**:
- **TC-460**: Validator W7 (claim marker validation gate)

**Coverage**: ✅ Complete

---

### 24_mcp_tool_schemas.md

**Implementing Taskcards**:
- **TC-510**: MCP server (tool schema implementation)
- **TC-511**, **TC-512**: MCP quickstart tools

**Validating Taskcards**:
- **TC-523**: MCP E2E pilot (validates tool schemas)

**Coverage**: ✅ Complete

---

### 25_frameworks_and_dependencies.md

**Implementing Taskcards**:
- **TC-100**: Bootstrap repo (dependency pinning, uv.lock)
- **TC-300**: Orchestrator (LangGraph usage)

**Validating Taskcards**:
- Gate K (supply chain pinning validation)

**Coverage**: ✅ Complete

---

### 26_repo_adapters_and_variability.md

**Implementing Taskcards**:
- **TC-402**: Repo fingerprint and inventory (archetype detection)
- **TC-403**: Frontmatter contract discovery (adapter selection)

**Validating Taskcards**:
- **TC-522**, **TC-523**: Pilots validate adapter detection on 2 archetypes

**Coverage**: ✅ Complete

---

### 27_universal_repo_handling.md

**Implementing Taskcards**:
- **TC-400**: RepoScout W1 (universal handling orchestration)
- **TC-402**: Repo fingerprint and inventory (universal detection strategies)

**Validating Taskcards**:
- **TC-522**, **TC-523**: Pilots validate universal handling on diverse repos

**Coverage**: ✅ Complete

---

### 29_project_repo_structure.md

**Implementing Taskcards**:
- **TC-100**: Bootstrap repo (repo structure, RUN_DIR layout)
- **TC-200**: Schemas and I/O (RUN_DIR layout schemas)

**Validating Taskcards**:
- Gate E (allowed paths enforcement)
- Gate: run_layout (in launch_validate)

**Coverage**: ✅ Complete

---

### 30_site_and_workflow_repos.md

**Implementing Taskcards**:
- **TC-401**: Clone and resolve SHAs (handles site/workflow repo cloning)

**Validating Taskcards**:
- Gate J (validates site_ref, workflow_ref are pinned SHAs)

**Coverage**: ✅ Complete

---

### 31_hugo_config_awareness.md

**Implementing Taskcards**:
- **TC-404**: Hugo site context + build matrix (config scanning)
- **TC-550**: Hugo config awareness extension (advanced config handling)

**Validating Taskcards**:
- **TC-460**, **TC-570**: Validators (config-aware validation)

**Coverage**: ✅ Complete

---

### 32_platform_aware_content_layout.md

**Implementing Taskcards**:
- **TC-540**: Content path resolver (platform-aware path resolution)
- **TC-403**: Frontmatter contract discovery (V2 root detection)
- **TC-404**: Hugo site context (layout_mode resolution)
- **TC-570**: Validation gates extension (content_layout_platform gate)

**Validating Taskcards**:
- **TC-570**: Self-validating (platform layout gate)
- Gate F (platform layout consistency)

**Coverage**: ✅ Complete

---

### 34_strict_compliance_guarantees.md

**Implementing Taskcards** (multiple taskcards implement guarantees):
- **Guarantee A** (Pinned refs): TC-100, TC-200
- **Guarantee B** (Hermetic boundaries): TC-100, TC-200 (path validation)
- **Guarantee C** (Supply chain): TC-100 (uv.lock)
- **Guarantee D** (Network allowlist): TC-500 (HTTP client)
- **Guarantee E** (Secrets hygiene): TC-590 (security)
- **Guarantee F/G** (Budgets): TC-100, TC-200 (budget config)
- **Guarantee H** (CI parity): TC-100 (CI setup), TC-530 (CLI)
- **Guarantee I** (Deterministic hashing): TC-560 (harness)
- **Guarantee J** (Untrusted code): TC-200 (subprocess wrapper)
- **Guarantee K** (Version locks): All 41 taskcards (frontmatter)

**Validating Taskcards**:
- Gates J, K, L, M, N, O, P, Q, R, S (each guarantee has dedicated gate)

**Coverage**: ✅ Complete (all 11 guarantees have taskcard + gate coverage)

---

## Summary

**Total Binding Specs**: 32
**Total Taskcards**: 41

**Coverage Analysis**:
- ✅ **All 32 binding specs**: Have implementing taskcards (100%)
- ✅ **All 32 binding specs**: Have validating taskcards or gates (100%)
- ✅ **All 41 taskcards**: Have version locks (Gate P passing)

**Taskcard Distribution by Wave**:
- **W1** (RepoScout): TC-400..TC-404 (5 taskcards)
- **W2** (Facts Builder): TC-410..TC-413 (4 taskcards)
- **W3** (Snippet Curator): TC-420..TC-422 (3 taskcards)
- **W4** (IA Planner): TC-430 (1 taskcard)
- **W5** (Section Writer): TC-440 (1 taskcard)
- **W6** (Linker & Patcher): TC-450 (1 taskcard)
- **W7** (Validator): TC-460 (1 taskcard)
- **W8** (Fixer): TC-470 (1 taskcard)
- **W9** (PR Manager): TC-480 (1 taskcard)
- **Infrastructure**: TC-100, TC-200, TC-201, TC-250, TC-300, TC-500, TC-510..TC-512, TC-520..TC-523, TC-530, TC-540, TC-550, TC-560, TC-570, TC-571, TC-580, TC-590, TC-600, TC-601, TC-602 (24 taskcards)

**Key Observations**:
1. **No plan gaps**: Every binding spec has taskcard coverage
2. **Balanced coverage**: 17 worker taskcards (W1-W9) + 24 infrastructure/support taskcards
3. **Cross-cutting concerns**: Infrastructure taskcards (TC-200, TC-500, TC-560, TC-570) support multiple specs
4. **Strong validation**: Most specs have both implementing AND validating taskcards

**Status**: ✅ **TASKCARD COVERAGE COMPLETE** - Zero plan gaps

