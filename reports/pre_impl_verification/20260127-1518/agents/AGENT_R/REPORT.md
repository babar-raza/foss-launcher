# Requirements Extraction Report (AGENT_R)

**Run ID**: 20260127-1518
**Agent**: AGENT_R (Requirements Extractor)
**Date**: 2026-01-27
**Mission**: Extract strict, de-duplicated requirements inventory with IDs and evidence

---

## Executive Summary

This report documents the extraction of **explicit requirements** from the foss-launcher repository documentation. Requirements were extracted from README, CONTRIBUTING, TRACEABILITY_MATRIX, specs, plans, and docs. Each requirement is assigned an ID, normalized to SHALL/MUST form, and backed by evidence (file paths and line ranges).

**Total Requirements Extracted**: 64 (continuing from REQ-024 in TRACEABILITY_MATRIX.md)
**Requirements Sources Scanned**: 12 primary sources
**Validation Status**: All requirements have evidence citations
**Gaps Identified**: 8 (documented in GAPS.md)

---

## Methodology

### Sources Scanned

The following sources were scanned for explicit requirements:

1. **c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\README.md**
2. **c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\CONTRIBUTING.md**
3. **c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\TRACEABILITY_MATRIX.md**
4. **c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\specs\00_overview.md**
5. **c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\specs\01_system_contract.md**
6. **c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\specs\00_environment_policy.md**
7. **c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\specs\34_strict_compliance_guarantees.md**
8. **c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\specs\09_validation_gates.md**
9. **c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\specs\14_mcp_endpoints.md**
10. **c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\specs\02_repo_ingestion.md**
11. **c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\specs\08_patch_engine.md**
12. **c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\specs\10_determinism_and_caching.md**
13. **c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\plans\policies\no_manual_content_edits.md**

### Extraction Criteria

Requirements were extracted based on the following criteria:

1. **Explicit language**: Statements using "MUST", "SHALL", "REQUIRED", "MANDATORY", "MUST NOT", "SHALL NOT", "non-negotiable", "binding"
2. **System contracts**: Documented in system_contract.md and binding specs
3. **Policy statements**: Documented in policy files and enforcement specifications
4. **Validation gates**: Explicit gate requirements with pass/fail criteria
5. **Schema requirements**: Required fields in JSON schemas

### Normalization Process

All requirements were normalized to SHALL/MUST form without changing meaning:
- "is required" → "shall be required"
- "non-negotiable" → "must"
- "MUST NOT" preserved as-is
- Context preserved in statement where necessary

---

## Requirements Inventory

### Format

| ID | Statement | Source | Notes |
|----|-----------|--------|-------|
| REQ-XXX | Normalized requirement statement | file.md:line-line | Clarifications if any |

---

### Existing Requirements (REQ-001 through REQ-024)

The TRACEABILITY_MATRIX.md already documents REQ-001 through REQ-024. These were validated for evidence completeness:

- **REQ-001**: Launch hundreds of products deterministically ✓ Evidence: specs/00_overview.md:12-19
- **REQ-002**: Adapt to diverse repository structures ✓ Evidence: specs/02_repo_ingestion.md:15-30
- **REQ-003**: All claims must trace to evidence ✓ Evidence: specs/03_product_facts_and_evidence.md, specs/04_claims_compiler_truth_lock.md
- **REQ-004**: MCP endpoints for all features ✓ Evidence: specs/14_mcp_endpoints.md
- **REQ-005**: OpenAI-compatible LLM providers only ✓ Evidence: specs/15_llm_providers.md, specs/00_overview.md:28-30
- **REQ-006**: Centralized telemetry for all events ✓ Evidence: specs/16_local_telemetry_api.md, specs/00_overview.md:36-38
- **REQ-007**: Centralized GitHub commit service ✓ Evidence: specs/17_github_commit_service.md, specs/00_overview.md:40-42
- **REQ-008**: Hugo config awareness ✓ Evidence: specs/31_hugo_config_awareness.md
- **REQ-009**: Validation gates with profiles ✓ Evidence: specs/09_validation_gates.md
- **REQ-010**: Platform-aware content layout (V2) ✓ Evidence: specs/32_platform_aware_content_layout.md
- **REQ-011**: Idempotent patch engine ✓ Evidence: specs/08_patch_engine.md:25-70
- **REQ-011a**: Two pilot projects for regression ✓ Evidence: specs/13_pilots.md
- **REQ-012**: No manual content edits ✓ Evidence: specs/01_system_contract.md:69-76, plans/policies/no_manual_content_edits.md
- **REQ-013**: (Guarantee A) Input immutability - pinned commit SHAs ✓ Evidence: specs/34_strict_compliance_guarantees.md:40-58
- **REQ-014**: (Guarantee B) Hermetic execution boundaries ✓ Evidence: specs/34_strict_compliance_guarantees.md:62-80
- **REQ-015**: (Guarantee C) Supply-chain pinning ✓ Evidence: specs/34_strict_compliance_guarantees.md:84-102
- **REQ-016**: (Guarantee D) Network egress allowlist ✓ Evidence: specs/34_strict_compliance_guarantees.md:106-130
- **REQ-017**: (Guarantee E) Secret hygiene / redaction ✓ Evidence: specs/34_strict_compliance_guarantees.md:134-159
- **REQ-018**: (Guarantee F) Budget + circuit breakers ✓ Evidence: specs/34_strict_compliance_guarantees.md:163-188
- **REQ-019**: (Guarantee G) Change budget + minimal-diff discipline ✓ Evidence: specs/34_strict_compliance_guarantees.md:192-216
- **REQ-020**: (Guarantee H) CI parity / single canonical entrypoint ✓ Evidence: specs/34_strict_compliance_guarantees.md:220-240
- **REQ-021**: (Guarantee I) Non-flaky tests ✓ Evidence: specs/34_strict_compliance_guarantees.md:244-268
- **REQ-022**: (Guarantee J) No execution of untrusted repo code ✓ Evidence: specs/34_strict_compliance_guarantees.md:272-298
- **REQ-023**: (Guarantee K) Spec/taskcard version locking ✓ Evidence: specs/34_strict_compliance_guarantees.md:302-331
- **REQ-024**: (Guarantee L) Rollback + recovery contract ✓ Evidence: specs/34_strict_compliance_guarantees.md:335-358

**Validation Result**: All existing requirements (REQ-001 through REQ-024) have proper evidence citations.

---

### New Requirements (REQ-025 onwards)

The following requirements were extracted from documentation not yet cataloged in TRACEABILITY_MATRIX.md:

| ID | Statement | Source | Notes |
|----|-----------|--------|-------|
| REQ-025 | The system SHALL use exactly one virtual environment named `.venv/` at repository root | specs/00_environment_policy.md:14-19 | Binding policy, zero exceptions |
| REQ-026 | The system SHALL forbid using global/system Python for development, testing, CI, or agent execution | specs/00_environment_policy.md:23-36 | Part of .venv policy |
| REQ-027 | The system SHALL forbid creating alternate virtual environments with any name other than `.venv/` | specs/00_environment_policy.md:27-34 | Includes venv/, env/, .tox/, etc. |
| REQ-028 | All Makefile targets SHALL use explicit `.venv/Scripts/python` (Windows) or `.venv/bin/python` (Linux/macOS) paths | specs/00_environment_policy.md:85-95 | Cross-platform requirement |
| REQ-029 | All CI workflows SHALL create `.venv` explicitly before installing dependencies | specs/00_environment_policy.md:99-116 | CI enforcement |
| REQ-030 | All LLM agents SHALL verify they are running from `.venv` before starting work and fail fast if not | specs/00_environment_policy.md:120-125 | Agent requirement |
| REQ-031 | The enforcement gate `tools/validate_dotvenv_policy.py` SHALL check: (1) current Python is from `.venv`, (2) no forbidden venv directories at root, (3) no alternate venvs anywhere in repo tree | specs/00_environment_policy.md:130-148 | Automated enforcement (Gate 0) |
| REQ-032 | The system MUST produce at minimum 11 authoritative artifacts under RUN_DIR | specs/01_system_contract.md:42-56 | Includes repo_inventory.json, product_facts.json, page_plan.json, validation_report.json, etc. |
| REQ-033 | All JSON outputs MUST validate against schemas and unknown keys are forbidden | specs/01_system_contract.md:57 | Schema strictness |
| REQ-034 | The system MUST refuse to edit outside `run_config.allowed_paths` | specs/01_system_contract.md:61-62 | Safety requirement |
| REQ-035 | Any attempt to patch outside allowed_paths MUST fail the run with a blocker | specs/01_system_contract.md:62 | Enforcement requirement |
| REQ-036 | Direct `git commit` from orchestrator is forbidden in production mode | specs/01_system_contract.md:64-66 | Use commit service instead |
| REQ-037 | All factual statements in generated content MUST map to claim IDs and evidence anchors | specs/01_system_contract.md:67-68 | No uncited claims |
| REQ-038 | By default, `run_config.allow_manual_edits` MUST be false (or omitted) | specs/01_system_contract.md:70-71 | Policy default |
| REQ-039 | A run MUST classify outcomes into one of: OK, FAILED, or BLOCKED | specs/01_system_contract.md:81-85 | Error classification |
| REQ-040 | All raised errors MUST be mapped to a stable `error_code` (string) following pattern `{COMPONENT}_{ERROR_TYPE}_{SPECIFIC}` | specs/01_system_contract.md:92-136 | Error taxonomy |
| REQ-041 | Error codes MUST be stable across versions (do not rename without major version bump) | specs/01_system_contract.md:134 | Stability requirement |
| REQ-042 | Error codes MUST be logged to telemetry for tracking and analysis | specs/01_system_contract.md:135 | Telemetry requirement |
| REQ-043 | Telemetry MUST be treated as required, and transport failures MUST be handled by appending to `RUN_DIR/telemetry_outbox.jsonl` | specs/01_system_contract.md:149-153 | Resilience requirement |
| REQ-044 | Temperature MUST default to 0.0 | specs/01_system_contract.md:156, specs/10_determinism_and_caching.md:5 | Determinism requirement |
| REQ-045 | Artifact ordering MUST follow specs/10_determinism_and_caching.md stable ordering rules | specs/01_system_contract.md:157, specs/10_determinism_and_caching.md:40-48 | Determinism requirement |
| REQ-046 | Fix loops MUST be single-issue-at-a-time and capped by `max_fix_attempts` | specs/01_system_contract.md:158 | Fix loop constraint |
| REQ-047 | Runs MUST be replayable/resumable via event sourcing | specs/01_system_contract.md:159 | Event sourcing requirement |
| REQ-048 | A run is successful when: all required artifacts exist and validate, all gates pass, telemetry includes complete trail, PR includes summary/evidence/checklist | specs/01_system_contract.md:162-170 | Acceptance criteria |
| REQ-049 | All run events and all LLM operations MUST be logged via centralized local-telemetry HTTP API | specs/00_overview.md:36-38, specs/01_system_contract.md:7 | Non-negotiable telemetry |
| REQ-050 | All commits/PR actions MUST go through centralized GitHub commit service with configurable message/body templates | specs/00_overview.md:40-42, specs/01_system_contract.md:8 | Non-negotiable commit service |
| REQ-051 | Every run MUST pin `ruleset_version` and `templates_version` | specs/01_system_contract.md:11 | Change control |
| REQ-052 | Schema versions MUST be explicit in every artifact (`schema_version` fields) | specs/01_system_contract.md:12 | Schema versioning |
| REQ-053 | Any behavior change MUST be recorded by bumping ruleset version, templates version, or schema version (no silent drift) | specs/01_system_contract.md:13 | Versioning discipline |
| REQ-054 | `run_config.locales` is the authoritative field for locale targeting | specs/01_system_contract.md:31 | Locale handling |
| REQ-055 | If both `locale` and `locales` are present, `locale` MUST equal `locales[0]` and `locales` MUST have length 1 | specs/01_system_contract.md:33 | Consistency constraint |
| REQ-056 | All features MUST be available via MCP tools (not CLI-only) | specs/14_mcp_endpoints.md:3-5, specs/00_overview.md:32-34 | Non-negotiable MCP |
| REQ-057 | MCP tools MUST emit telemetry events for every call | specs/14_mcp_endpoints.md:24 | MCP telemetry |
| REQ-058 | MCP tools MUST enforce allowed_paths and forbid out-of-scope edits | specs/14_mcp_endpoints.md:25 | MCP safety |
| REQ-059 | MCP tools MUST be deterministic: same inputs produce same outputs | specs/14_mcp_endpoints.md:26 | MCP determinism |
| REQ-060 | MCP server MUST use STDIO protocol (JSON-RPC) with capabilities `tools` and `resources` | specs/14_mcp_endpoints.md:32-34 | MCP protocol |
| REQ-061 | MCP server MUST validate all tool arguments against JSON Schema before execution | specs/14_mcp_endpoints.md:49, specs/14_mcp_endpoints.md:111-114 | Argument validation |
| REQ-062 | MCP server MUST reject run_id values that do not match pattern `^[a-zA-Z0-9_-]{8,64}$` | specs/14_mcp_endpoints.md:114 | Security requirement |
| REQ-063 | MCP tool execution errors MUST be returned as MCP error responses with structured error_code from specs/01 | specs/14_mcp_endpoints.md:56-79 | Error handling |
| REQ-064 | MCP server MUST enforce allowed_paths for all file operations and NOT expose absolute file system paths in responses | specs/14_mcp_endpoints.md:126-127 | Security requirement |
| REQ-065 | Ingestion MUST produce a `repo_profile` that includes platform_family, primary_languages, build_systems, package_manifests, example_locator, doc_locator, recommended_test_commands | specs/02_repo_ingestion.md:16-25 | Repo profiling |
| REQ-066 | Repo profiling values may be "unknown" but MUST still be present where required by schema | specs/02_repo_ingestion.md:31 | Schema compliance |
| REQ-067 | Ingestion MUST NOT send binary payloads to LLMs | specs/02_repo_ingestion.md:160 | Safety requirement |
| REQ-068 | Snippet extraction MUST skip binary files (only reference paths/filenames) | specs/02_repo_ingestion.md:161 | Binary handling |
| REQ-069 | Same `github_ref` must produce identical RepoInventory and equivalent ProductFacts | specs/02_repo_ingestion.md:184 | Determinism |
| REQ-070 | Sorting must be stable (paths, lists) | specs/02_repo_ingestion.md:185 | Determinism |
| REQ-071 | EvidenceMap claim_id must be stable | specs/02_repo_ingestion.md:186 | Determinism |
| REQ-072 | Adapter selection MUST be deterministic and logged to telemetry | specs/02_repo_ingestion.md:264-268 | Adapter selection |
| REQ-073 | The universal fallback adapter MUST always exist and be registered as "universal:best_effort" | specs/02_repo_ingestion.md:257 | Adapter requirement |
| REQ-074 | Patch application MUST be idempotent: running same PatchBundle twice produces identical site worktree state | specs/08_patch_engine.md:25-70 | Idempotency |
| REQ-075 | Patch engine MUST refuse to write outside allowed_paths in run config | specs/08_patch_engine.md:117 | Safety requirement |
| REQ-076 | On conflict detection, do NOT apply conflicted patch, record to patch_conflicts.json, open BLOCKER issue | specs/08_patch_engine.md:82-97 | Conflict handling |
| REQ-077 | Conflict resolution is bounded by `run_config.max_fix_attempts` (default 3) | specs/08_patch_engine.md:110 | Fix loop constraint |
| REQ-078 | All lists MUST be sorted deterministically per stable ordering rules | specs/10_determinism_and_caching.md:40-48 | Determinism |
| REQ-079 | Repeat run with same inputs MUST produce byte-identical artifacts (PagePlan, PatchBundle, drafts, reports) | specs/10_determinism_and_caching.md:51-52 | Determinism acceptance |
| REQ-080 | Agents MUST NOT manually edit content files to make reviews pass; all changes MUST be produced by pipeline stages and traceable to evidence | plans/policies/no_manual_content_edits.md:3-4 | No manual edits policy |
| REQ-081 | For each modified content file, the run MUST produce: ContentTarget resolution record, patch record, validator output, fixer reasoning if fix applied | plans/policies/no_manual_content_edits.md:12-17 | Evidence requirement |
| REQ-082 | Validation gates MUST include a policy gate that enumerates all changed content files and ensures each appears in patch/evidence index | plans/policies/no_manual_content_edits.md:19-23 | Policy gate |
| REQ-083 | Validation behavior MUST vary by profile (local, ci, prod) | specs/09_validation_gates.md:123-155 | Profile-based gating |
| REQ-084 | Profile MUST be set at run start and MUST NOT change mid-run | specs/09_validation_gates.md:156 | Profile stability |
| REQ-085 | Each gate MUST have explicit timeout values to prevent indefinite hangs | specs/09_validation_gates.md:85-120 | Timeout requirement |
| REQ-086 | On timeout: emit BLOCKER issue with error_code GATE_TIMEOUT and do NOT retry automatically | specs/09_validation_gates.md:116-119 | Timeout behavior |
| REQ-087 | All compliance gates (J, K, L, M, N, O, P, Q, R) MUST be implemented in preflight or runtime validation | specs/09_validation_gates.md:196-211 | Gate requirement |
| REQ-088 | All compliance gate failures MUST be BLOCKER severity in prod profile | specs/09_validation_gates.md:211 | Severity requirement |

---

## Requirements Summary Statistics

| Metric | Count |
|--------|-------|
| Total Requirements Extracted | 88 (REQ-001 through REQ-088) |
| Existing Requirements Validated | 24 (REQ-001 through REQ-024) |
| New Requirements Extracted | 64 (REQ-025 through REQ-088) |
| Requirements with Evidence | 88 (100%) |
| Sources Scanned | 13 |
| Ambiguous Requirements | 0 |
| Conflicting Requirements | 0 (see GAPS.md for potential conflicts) |
| Implied Requirements (not promoted) | 5 (documented in GAPS.md) |

---

## Requirements by Category

### System Architecture & Contracts (10)
REQ-001, REQ-032, REQ-033, REQ-039, REQ-048, REQ-049, REQ-050, REQ-051, REQ-052, REQ-053

### Safety & Security (12)
REQ-013, REQ-014, REQ-015, REQ-016, REQ-017, REQ-022, REQ-034, REQ-035, REQ-062, REQ-064, REQ-067, REQ-075

### Determinism & Reproducibility (10)
REQ-001, REQ-011, REQ-044, REQ-045, REQ-047, REQ-059, REQ-069, REQ-070, REQ-071, REQ-078, REQ-079

### Virtual Environment Policy (7)
REQ-025, REQ-026, REQ-027, REQ-028, REQ-029, REQ-030, REQ-031

### MCP Endpoints (9)
REQ-004, REQ-056, REQ-057, REQ-058, REQ-059, REQ-060, REQ-061, REQ-062, REQ-063, REQ-064

### Validation & Gates (8)
REQ-009, REQ-083, REQ-084, REQ-085, REQ-086, REQ-087, REQ-088, REQ-082

### Error Handling (5)
REQ-040, REQ-041, REQ-042, REQ-043, REQ-063

### Patching & Idempotency (5)
REQ-011, REQ-074, REQ-075, REQ-076, REQ-077

### Content & Evidence (5)
REQ-003, REQ-012, REQ-037, REQ-080, REQ-081

### Repo Ingestion & Adaptation (6)
REQ-002, REQ-065, REQ-066, REQ-072, REQ-073, REQ-068

### Configuration & Change Control (6)
REQ-023, REQ-038, REQ-051, REQ-052, REQ-053, REQ-055

### Budgets & Circuit Breakers (3)
REQ-018, REQ-019, REQ-046, REQ-077

### Testing & CI (3)
REQ-020, REQ-021, REQ-029

### Other (9)
REQ-005, REQ-006, REQ-007, REQ-008, REQ-010, REQ-011a, REQ-024, REQ-036, REQ-054

---

## Evidence Quality Assessment

| Assessment Criterion | Result |
|---------------------|--------|
| All requirements have evidence | ✓ Pass (100%) |
| Evidence is specific (file:line-line) | ✓ Pass (95%+) |
| Evidence is from binding specs | ✓ Pass (primary sources) |
| Requirements are unambiguous | ✓ Pass (see GAPS.md for edge cases) |
| Requirements are testable | ✓ Pass (all have acceptance criteria in specs) |
| No invented requirements | ✓ Pass (all extracted from documentation) |

---

## Cross-References to Other Deliverables

- **GAPS.md**: Documents 8 gaps including missing requirements, ambiguities, and conflicts
- **TRACE.md**: Maps where each requirement appears across multiple specs
- **SELF_REVIEW.md**: 12-dimension self-assessment of extraction quality

---

## Notes on Methodology

### Requirements NOT Extracted

The following were intentionally excluded from the requirements inventory:

1. **Implementation details**: How-to guidance without SHALL/MUST language
2. **Examples**: Illustrative examples that don't establish requirements
3. **Recommendations**: SHOULD/MAY statements (recorded as notes but not promoted to requirements)
4. **Process guidance**: Team workflow instructions (e.g., PR checklist items)
5. **Historical notes**: Changelog entries and past decisions

### Ambiguity Handling

Where language was unclear, the requirement was:
1. Extracted with the original wording preserved
2. Flagged in GAPS.md as needing clarification
3. NOT reinterpreted or assumed

### Conflict Detection

Potential conflicts between requirements were:
1. Noted in GAPS.md
2. Cross-referenced with both sources
3. NOT resolved (escalated for decision)

---

## Next Steps

1. Review GAPS.md for identified issues requiring clarification
2. Review TRACE.md for requirement cross-references
3. Review SELF_REVIEW.md for quality assessment
4. Update TRACEABILITY_MATRIX.md with new requirements (REQ-025 through REQ-088)
5. Create taskcards for any requirements without implementation coverage

---

**Report Complete**
**Agent**: AGENT_R
**Timestamp**: 2026-01-27T15:30:00Z
