# Requirements Inventory

**Pre-Implementation Verification Run**: 20260127-1518
**Source**: AGENT_R (Requirements Extractor)
**Date**: 2026-01-27
**Total Requirements**: 88 (REQ-001 through REQ-088)

---

## Requirements by Category

### System Architecture & Contracts (10 requirements)

| ID | Statement | Source | Notes |
|----|-----------|--------|-------|
| REQ-001 | The system SHALL launch hundreds of products deterministically | specs/00_overview.md:12-19 | Core system requirement |
| REQ-032 | The system MUST produce at minimum 11 authoritative artifacts under RUN_DIR | specs/01_system_contract.md:42-56 | Includes repo_inventory.json, product_facts.json, page_plan.json, validation_report.json, etc. |
| REQ-033 | All JSON outputs MUST validate against schemas and unknown keys are forbidden | specs/01_system_contract.md:57 | Schema strictness |
| REQ-039 | A run MUST classify outcomes into one of: OK, FAILED, or BLOCKED | specs/01_system_contract.md:81-85 | Error classification |
| REQ-048 | A run is successful when: all required artifacts exist and validate, all gates pass, telemetry includes complete trail, PR includes summary/evidence/checklist | specs/01_system_contract.md:162-170 | Acceptance criteria |
| REQ-049 | All run events and all LLM operations MUST be logged via centralized local-telemetry HTTP API | specs/00_overview.md:36-38, specs/01_system_contract.md:7 | Non-negotiable telemetry |
| REQ-050 | All commits/PR actions MUST go through centralized GitHub commit service with configurable message/body templates | specs/00_overview.md:40-42, specs/01_system_contract.md:8 | Non-negotiable commit service |
| REQ-051 | Every run MUST pin ruleset_version and templates_version | specs/01_system_contract.md:11 | Change control |
| REQ-052 | Schema versions MUST be explicit in every artifact (schema_version fields) | specs/01_system_contract.md:12 | Schema versioning |
| REQ-053 | Any behavior change MUST be recorded by bumping ruleset version, templates version, or schema version (no silent drift) | specs/01_system_contract.md:13 | Versioning discipline |

### Safety & Security (12 requirements)

| ID | Statement | Source | Notes |
|----|-----------|--------|-------|
| REQ-013 | (Guarantee A) Input immutability - pinned commit SHAs | specs/34_strict_compliance_guarantees.md:40-58 | All *_ref fields must be commit SHAs |
| REQ-014 | (Guarantee B) Hermetic execution boundaries | specs/34_strict_compliance_guarantees.md:62-80 | Only write within allowed_paths |
| REQ-015 | (Guarantee C) Supply-chain pinning | specs/34_strict_compliance_guarantees.md:84-102 | Lockfiles, frozen installs |
| REQ-016 | (Guarantee D) Network egress allowlist | specs/34_strict_compliance_guarantees.md:106-130 | Only approved hosts |
| REQ-017 | (Guarantee E) Secret hygiene / redaction | specs/34_strict_compliance_guarantees.md:134-159 | No secrets in logs/commits |
| REQ-022 | (Guarantee J) No execution of untrusted repo code | specs/34_strict_compliance_guarantees.md:272-298 | Never run code from target repos |
| REQ-034 | The system MUST refuse to edit outside run_config.allowed_paths | specs/01_system_contract.md:61-62 | Safety requirement |
| REQ-035 | Any attempt to patch outside allowed_paths MUST fail the run with a blocker | specs/01_system_contract.md:62 | Enforcement requirement |
| REQ-062 | MCP server MUST reject run_id values that do not match pattern ^[a-zA-Z0-9_-]{8,64}$ | specs/14_mcp_endpoints.md:114 | Security requirement |
| REQ-064 | MCP server MUST enforce allowed_paths for all file operations and NOT expose absolute file system paths in responses | specs/14_mcp_endpoints.md:126-127 | Security requirement |
| REQ-067 | Ingestion MUST NOT send binary payloads to LLMs | specs/02_repo_ingestion.md:160 | Safety requirement |
| REQ-075 | Patch engine MUST refuse to write outside allowed_paths in run config | specs/08_patch_engine.md:117 | Safety requirement |

### Determinism & Reproducibility (10 requirements)

| ID | Statement | Source | Notes |
|----|-----------|--------|-------|
| REQ-001 | The system SHALL launch hundreds of products deterministically | specs/00_overview.md:12-19 | Same inputs → same outputs |
| REQ-011 | (REQ-011) Idempotent patch engine | specs/08_patch_engine.md:25-70 | Running twice produces identical state |
| REQ-044 | Temperature MUST default to 0.0 | specs/01_system_contract.md:156, specs/10_determinism_and_caching.md:5 | Determinism requirement |
| REQ-045 | Artifact ordering MUST follow specs/10_determinism_and_caching.md stable ordering rules | specs/01_system_contract.md:157, specs/10_determinism_and_caching.md:40-48 | Determinism requirement |
| REQ-047 | Runs MUST be replayable/resumable via event sourcing | specs/01_system_contract.md:159 | Event sourcing requirement |
| REQ-059 | MCP tools MUST be deterministic: same inputs produce same outputs | specs/14_mcp_endpoints.md:26 | MCP determinism |
| REQ-069 | Same github_ref must produce identical RepoInventory and equivalent ProductFacts | specs/02_repo_ingestion.md:184 | Determinism |
| REQ-070 | Sorting must be stable (paths, lists) | specs/02_repo_ingestion.md:185 | Determinism |
| REQ-071 | EvidenceMap claim_id must be stable | specs/02_repo_ingestion.md:186 | Determinism |
| REQ-078 | All lists MUST be sorted deterministically per stable ordering rules | specs/10_determinism_and_caching.md:40-48 | Determinism |
| REQ-079 | Repeat run with same inputs MUST produce byte-identical artifacts (PagePlan, PatchBundle, drafts, reports) | specs/10_determinism_and_caching.md:51-52 | Determinism acceptance |

### Virtual Environment Policy (7 requirements)

| ID | Statement | Source | Notes |
|----|-----------|--------|-------|
| REQ-025 | The system SHALL use exactly one virtual environment named .venv/ at repository root | specs/00_environment_policy.md:14-19 | Binding policy, zero exceptions |
| REQ-026 | The system SHALL forbid using global/system Python for development, testing, CI, or agent execution | specs/00_environment_policy.md:23-36 | Part of .venv policy |
| REQ-027 | The system SHALL forbid creating alternate virtual environments with any name other than .venv/ | specs/00_environment_policy.md:27-34 | Includes venv/, env/, .tox/, etc. |
| REQ-028 | All Makefile targets SHALL use explicit .venv/Scripts/python (Windows) or .venv/bin/python (Linux/macOS) paths | specs/00_environment_policy.md:85-95 | Cross-platform requirement |
| REQ-029 | All CI workflows SHALL create .venv explicitly before installing dependencies | specs/00_environment_policy.md:99-116 | CI enforcement |
| REQ-030 | All LLM agents SHALL verify they are running from .venv before starting work and fail fast if not | specs/00_environment_policy.md:120-125 | Agent requirement |
| REQ-031 | The enforcement gate tools/validate_dotvenv_policy.py SHALL check: (1) current Python is from .venv, (2) no forbidden venv directories at root, (3) no alternate venvs anywhere in repo tree | specs/00_environment_policy.md:130-148 | Automated enforcement (Gate 0) |

### MCP Endpoints (9 requirements)

| ID | Statement | Source | Notes |
|----|-----------|--------|-------|
| REQ-004 | MCP endpoints for all features | specs/14_mcp_endpoints.md | Non-negotiable MCP |
| REQ-056 | All features MUST be available via MCP tools (not CLI-only) | specs/14_mcp_endpoints.md:3-5, specs/00_overview.md:32-34 | Non-negotiable MCP |
| REQ-057 | MCP tools MUST emit telemetry events for every call | specs/14_mcp_endpoints.md:24 | MCP telemetry |
| REQ-058 | MCP tools MUST enforce allowed_paths and forbid out-of-scope edits | specs/14_mcp_endpoints.md:25 | MCP safety |
| REQ-059 | MCP tools MUST be deterministic: same inputs produce same outputs | specs/14_mcp_endpoints.md:26 | MCP determinism |
| REQ-060 | MCP server MUST use STDIO protocol (JSON-RPC) with capabilities tools and resources | specs/14_mcp_endpoints.md:32-34 | MCP protocol |
| REQ-061 | MCP server MUST validate all tool arguments against JSON Schema before execution | specs/14_mcp_endpoints.md:49, specs/14_mcp_endpoints.md:111-114 | Argument validation |
| REQ-062 | MCP server MUST reject run_id values that do not match pattern ^[a-zA-Z0-9_-]{8,64}$ | specs/14_mcp_endpoints.md:114 | Security requirement |
| REQ-063 | MCP tool execution errors MUST be returned as MCP error responses with structured error_code from specs/01 | specs/14_mcp_endpoints.md:56-79 | Error handling |
| REQ-064 | MCP server MUST enforce allowed_paths for all file operations and NOT expose absolute file system paths in responses | specs/14_mcp_endpoints.md:126-127 | Security requirement |

### Validation & Gates (8 requirements)

| ID | Statement | Source | Notes |
|----|-----------|--------|-------|
| REQ-009 | Validation gates with profiles | specs/09_validation_gates.md | Local/ci/prod profiles |
| REQ-082 | Validation gates MUST include a policy gate that enumerates all changed content files and ensures each appears in patch/evidence index | plans/policies/no_manual_content_edits.md:19-23 | Policy gate |
| REQ-083 | Validation behavior MUST vary by profile (local, ci, prod) | specs/09_validation_gates.md:123-155 | Profile-based gating |
| REQ-084 | Profile MUST be set at run start and MUST NOT change mid-run | specs/09_validation_gates.md:156 | Profile stability |
| REQ-085 | Each gate MUST have explicit timeout values to prevent indefinite hangs | specs/09_validation_gates.md:85-120 | Timeout requirement |
| REQ-086 | On timeout: emit BLOCKER issue with error_code GATE_TIMEOUT and do NOT retry automatically | specs/09_validation_gates.md:116-119 | Timeout behavior |
| REQ-087 | All compliance gates (J, K, L, M, N, O, P, Q, R) MUST be implemented in preflight or runtime validation | specs/09_validation_gates.md:196-211 | Gate requirement |
| REQ-088 | All compliance gate failures MUST be BLOCKER severity in prod profile | specs/09_validation_gates.md:211 | Severity requirement |

### Error Handling (5 requirements)

| ID | Statement | Source | Notes |
|----|-----------|--------|-------|
| REQ-040 | All raised errors MUST be mapped to a stable error_code (string) following pattern {COMPONENT}_{ERROR_TYPE}_{SPECIFIC} | specs/01_system_contract.md:92-136 | Error taxonomy |
| REQ-041 | Error codes MUST be stable across versions (do not rename without major version bump) | specs/01_system_contract.md:134 | Stability requirement |
| REQ-042 | Error codes MUST be logged to telemetry for tracking and analysis | specs/01_system_contract.md:135 | Telemetry requirement |
| REQ-043 | Telemetry MUST be treated as required, and transport failures MUST be handled by appending to RUN_DIR/telemetry_outbox.jsonl | specs/01_system_contract.md:149-153 | Resilience requirement |
| REQ-063 | MCP tool execution errors MUST be returned as MCP error responses with structured error_code from specs/01 | specs/14_mcp_endpoints.md:56-79 | Error handling |

### Patching & Idempotency (5 requirements)

| ID | Statement | Source | Notes |
|----|-----------|--------|-------|
| REQ-011 | (REQ-011) Idempotent patch engine | specs/08_patch_engine.md:25-70 | Running twice produces identical state |
| REQ-074 | Patch application MUST be idempotent: running same PatchBundle twice produces identical site worktree state | specs/08_patch_engine.md:25-70 | Idempotency |
| REQ-075 | Patch engine MUST refuse to write outside allowed_paths in run config | specs/08_patch_engine.md:117 | Safety requirement |
| REQ-076 | On conflict detection, do NOT apply conflicted patch, record to patch_conflicts.json, open BLOCKER issue | specs/08_patch_engine.md:82-97 | Conflict handling |
| REQ-077 | Conflict resolution is bounded by run_config.max_fix_attempts (default 3) | specs/08_patch_engine.md:110 | Fix loop constraint |

### Content & Evidence (5 requirements)

| ID | Statement | Source | Notes |
|----|-----------|--------|-------|
| REQ-003 | All claims must trace to evidence | specs/03_product_facts_and_evidence.md, specs/04_claims_compiler_truth_lock.md | No uncited claims |
| REQ-012 | No manual content edits | specs/01_system_contract.md:69-76, plans/policies/no_manual_content_edits.md | Policy enforcement |
| REQ-037 | All factual statements in generated content MUST map to claim IDs and evidence anchors | specs/01_system_contract.md:67-68 | No uncited claims |
| REQ-080 | Agents MUST NOT manually edit content files to make reviews pass; all changes MUST be produced by pipeline stages and traceable to evidence | plans/policies/no_manual_content_edits.md:3-4 | No manual edits policy |
| REQ-081 | For each modified content file, the run MUST produce: ContentTarget resolution record, patch record, validator output, fixer reasoning if fix applied | plans/policies/no_manual_content_edits.md:12-17 | Evidence requirement |

### Repo Ingestion & Adaptation (6 requirements)

| ID | Statement | Source | Notes |
|----|-----------|--------|-------|
| REQ-002 | Adapt to diverse repository structures | specs/02_repo_ingestion.md:15-30 | Universal repo handling |
| REQ-065 | Ingestion MUST produce a repo_profile that includes platform_family, primary_languages, build_systems, package_manifests, example_locator, doc_locator, recommended_test_commands | specs/02_repo_ingestion.md:16-25 | Repo profiling |
| REQ-066 | Repo profiling values may be "unknown" but MUST still be present where required by schema | specs/02_repo_ingestion.md:31 | Schema compliance |
| REQ-068 | Snippet extraction MUST skip binary files (only reference paths/filenames) | specs/02_repo_ingestion.md:161 | Binary handling |
| REQ-072 | Adapter selection MUST be deterministic and logged to telemetry | specs/02_repo_ingestion.md:264-268 | Adapter selection |
| REQ-073 | The universal fallback adapter MUST always exist and be registered as "universal:best_effort" | specs/02_repo_ingestion.md:257 | Adapter requirement |

### Configuration & Change Control (6 requirements)

| ID | Statement | Source | Notes |
|----|-----------|--------|-------|
| REQ-023 | (Guarantee K) Spec/taskcard version locking | specs/34_strict_compliance_guarantees.md:302-331 | Version lock enforcement |
| REQ-038 | By default, run_config.allow_manual_edits MUST be false (or omitted) | specs/01_system_contract.md:70-71 | Policy default |
| REQ-051 | Every run MUST pin ruleset_version and templates_version | specs/01_system_contract.md:11 | Change control |
| REQ-052 | Schema versions MUST be explicit in every artifact (schema_version fields) | specs/01_system_contract.md:12 | Schema versioning |
| REQ-053 | Any behavior change MUST be recorded by bumping ruleset version, templates version, or schema version (no silent drift) | specs/01_system_contract.md:13 | Versioning discipline |
| REQ-055 | If both locale and locales are present, locale MUST equal locales[0] and locales MUST have length 1 | specs/01_system_contract.md:33 | Consistency constraint |

### Budgets & Circuit Breakers (4 requirements)

| ID | Statement | Source | Notes |
|----|-----------|--------|-------|
| REQ-018 | (Guarantee F) Budget + circuit breakers | specs/34_strict_compliance_guarantees.md:163-188 | LLM calls, file writes, runtime limits |
| REQ-019 | (Guarantee G) Change budget + minimal-diff discipline | specs/34_strict_compliance_guarantees.md:192-216 | Max lines per file, max files changed |
| REQ-046 | Fix loops MUST be single-issue-at-a-time and capped by max_fix_attempts | specs/01_system_contract.md:158 | Fix loop constraint |
| REQ-077 | Conflict resolution is bounded by run_config.max_fix_attempts (default 3) | specs/08_patch_engine.md:110 | Fix loop constraint |

### Testing & CI (3 requirements)

| ID | Statement | Source | Notes |
|----|-----------|--------|-------|
| REQ-020 | (Guarantee H) CI parity / single canonical entrypoint | specs/34_strict_compliance_guarantees.md:220-240 | CI must match local |
| REQ-021 | (Guarantee I) Non-flaky tests | specs/34_strict_compliance_guarantees.md:244-268 | No non-deterministic tests |
| REQ-029 | All CI workflows SHALL create .venv explicitly before installing dependencies | specs/00_environment_policy.md:99-116 | CI enforcement |

### Other (9 requirements)

| ID | Statement | Source | Notes |
|----|-----------|--------|-------|
| REQ-005 | OpenAI-compatible LLM providers only | specs/15_llm_providers.md, specs/00_overview.md:28-30 | No provider-specific assumptions |
| REQ-006 | Centralized telemetry for all events | specs/16_local_telemetry_api.md, specs/00_overview.md:36-38 | Non-negotiable telemetry |
| REQ-007 | Centralized GitHub commit service | specs/17_github_commit_service.md, specs/00_overview.md:40-42 | Non-negotiable commit service |
| REQ-008 | Hugo config awareness | specs/31_hugo_config_awareness.md | Required for site generation |
| REQ-010 | Platform-aware content layout (V2) | specs/32_platform_aware_content_layout.md | /{locale}/{platform}/ paths |
| REQ-011a | Two pilot projects for regression | specs/13_pilots.md | Pilot validation |
| REQ-024 | (Guarantee L) Rollback + recovery contract | specs/34_strict_compliance_guarantees.md:335-358 | PR rollback metadata |
| REQ-036 | Direct git commit from orchestrator is forbidden in production mode | specs/01_system_contract.md:64-66 | Use commit service instead |
| REQ-054 | run_config.locales is the authoritative field for locale targeting | specs/01_system_contract.md:31 | Locale handling |

---

## All Requirements (REQ-001 through REQ-088)

Complete list available in AGENT_R/REPORT.md lines 110-175.

---

**Evidence Source**: reports/pre_impl_verification/20260127-1518/agents/AGENT_R/REPORT.md
**Extraction Method**: Explicit language scanning (MUST/SHALL/REQUIRED), normalized to binding form
**Validation Status**: All 88 requirements have evidence citations (100%)
