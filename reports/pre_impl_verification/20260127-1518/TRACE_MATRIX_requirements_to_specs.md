# Trace Matrix: Requirements → Specs

**Pre-Implementation Verification Run**: 20260127-1518
**Source**: AGENT_R/TRACE.md
**Date**: 2026-01-27

---

## Format

| REQ-ID | Requirement | Primary Spec(s) | Status | Cross-References |
|--------|-------------|-----------------|--------|------------------|

---

## Virtual Environment Requirements (REQ-025 through REQ-031)

| REQ-ID | Requirement | Primary Spec(s) | Status | Evidence |
|--------|-------------|-----------------|--------|----------|
| REQ-025 | Single .venv virtual environment | specs/00_environment_policy.md:14-19 | ✅ Implemented | Gate 0, README.md:51-87, CONTRIBUTING.md:22-28 |
| REQ-026 | Forbid global/system Python | specs/00_environment_policy.md:23-36 | ✅ Implemented | Gate 0 |
| REQ-027 | Forbid alternate virtual environments | specs/00_environment_policy.md:27-34 | ✅ Implemented | Gate 0 checks |
| REQ-028 | Makefile must use explicit .venv paths | specs/00_environment_policy.md:85-95 | ✅ Implemented | Makefile |
| REQ-029 | CI must create .venv explicitly | specs/00_environment_policy.md:99-116 | ⚠️ Partial | Depends on CI workflow implementation |
| REQ-030 | Agents must verify .venv before starting | specs/00_environment_policy.md:120-125 | ✅ Policy | Agent discipline |
| REQ-031 | Enforcement gate validates .venv policy | specs/00_environment_policy.md:130-148 | ✅ Implemented | tools/validate_dotvenv_policy.py |

## System Contract Requirements (REQ-032 through REQ-048)

| REQ-ID | Requirement | Primary Spec(s) | Status | Evidence |
|--------|-------------|-----------------|--------|----------|
| REQ-032 | Produce 11 authoritative artifacts | specs/01_system_contract.md:42-56 | ⚠️ Not Implemented | Spec defined, TC-300 pending |
| REQ-033 | JSON outputs must validate, unknown keys forbidden | specs/01_system_contract.md:57 | ⚠️ Partial | Schema validation exists, runtime pending |
| REQ-034 | Refuse edits outside allowed_paths | specs/01_system_contract.md:61-62 | ✅ Implemented | src/launch/util/path_validation.py |
| REQ-035 | Patch outside allowed_paths must fail with blocker | specs/01_system_contract.md:62 | ✅ Implemented | path_validation.py, tests |
| REQ-036 | Direct git commit forbidden in production | specs/01_system_contract.md:64-66 | ⚠️ Not Implemented | TC-480 PR Manager |
| REQ-037 | All claims must map to claim IDs and evidence | specs/01_system_contract.md:67-68 | ⚠️ Not Implemented | TC-410, TC-413 |
| REQ-038 | allow_manual_edits must default to false | specs/01_system_contract.md:70-71 | ✅ Schema | run_config.schema.json default |
| REQ-039 | Classify outcomes as OK/FAILED/BLOCKED | specs/01_system_contract.md:81-85 | ⚠️ Not Implemented | TC-460 Validator |
| REQ-040 | Error codes follow {COMPONENT}_{ERROR_TYPE}_{SPECIFIC} pattern | specs/01_system_contract.md:92-136 | ⚠️ Partial | Used in implemented code |
| REQ-041 | Error codes must be stable across versions | specs/01_system_contract.md:134 | ✅ Policy | Policy defined |
| REQ-042 | Error codes must be logged to telemetry | specs/01_system_contract.md:135 | ⚠️ Not Implemented | TC-500 telemetry client |
| REQ-043 | Telemetry failures handled via outbox | specs/01_system_contract.md:149-153 | ⚠️ Not Implemented | TC-500 |
| REQ-044 | Temperature must default to 0.0 | specs/01_system_contract.md:156 | ✅ Schema | Schema default |
| REQ-045 | Artifact ordering must follow stable rules | specs/01_system_contract.md:157 | ⚠️ Not Implemented | All workers must implement |
| REQ-046 | Fix loops single-issue, capped by max_fix_attempts | specs/01_system_contract.md:158 | ⚠️ Not Implemented | TC-470 Fixer |
| REQ-047 | Runs must be replayable/resumable | specs/01_system_contract.md:159 | ⚠️ Not Implemented | TC-300 orchestrator |
| REQ-048 | Run successful when artifacts validate, gates pass, telemetry complete, PR includes summary | specs/01_system_contract.md:162-170 | ⚠️ Not Implemented | Full pipeline |

## LLM & API Requirements (REQ-005, REQ-049, REQ-050)

| REQ-ID | Requirement | Primary Spec(s) | Status | Evidence |
|--------|-------------|-----------------|--------|----------|
| REQ-005 | OpenAI-compatible LLM providers only | specs/15_llm_providers.md | ⚠️ Not Implemented | TC-500 LLM client |
| REQ-049 | All events/LLM ops logged to telemetry | specs/00_overview.md:36-38 | ⚠️ Not Implemented | TC-500, TC-580 |
| REQ-050 | All commits via centralized commit service | specs/00_overview.md:40-42 | ⚠️ Not Implemented | TC-480 PR Manager |

## Configuration & Versioning (REQ-051 through REQ-055)

| REQ-ID | Requirement | Primary Spec(s) | Status | Evidence |
|--------|-------------|-----------------|--------|----------|
| REQ-051 | Every run must pin ruleset_version and templates_version | specs/01_system_contract.md:11 | ✅ Enforced | Gate B, Gate P |
| REQ-052 | Schema versions explicit in every artifact | specs/01_system_contract.md:12 | ✅ Implemented | All schema files have version field |
| REQ-053 | Behavior changes recorded via version bumps | specs/01_system_contract.md:13 | ✅ Policy | Policy defined |
| REQ-054 | run_config.locales is authoritative for locale targeting | specs/01_system_contract.md:31 | ✅ Schema | Schema field |
| REQ-055 | If both locale and locales present, constraints apply | specs/01_system_contract.md:33 | ✅ Schema | Schema constraint |

## MCP Requirements (REQ-056 through REQ-064)

| REQ-ID | Requirement | Primary Spec(s) | Status | Evidence |
|--------|-------------|-----------------|--------|----------|
| REQ-056 | All features available via MCP tools | specs/14_mcp_endpoints.md:3-5 | ⚠️ Not Implemented | TC-510 MCP server |
| REQ-057 | MCP tools must emit telemetry | specs/14_mcp_endpoints.md:24 | ⚠️ Not Implemented | TC-510 |
| REQ-058 | MCP tools must enforce allowed_paths | specs/14_mcp_endpoints.md:25 | ⚠️ Not Implemented | TC-510 |
| REQ-059 | MCP tools must be deterministic | specs/14_mcp_endpoints.md:26 | ⚠️ Not Implemented | TC-510 |
| REQ-060 | MCP server uses STDIO JSON-RPC protocol | specs/14_mcp_endpoints.md:32-34 | ⚠️ Not Implemented | TC-510 |
| REQ-061 | MCP server validates arguments against schema | specs/14_mcp_endpoints.md:49 | ⚠️ Not Implemented | TC-510 |
| REQ-062 | MCP server rejects invalid run_id pattern | specs/14_mcp_endpoints.md:114 | ⚠️ Not Implemented | TC-510 |
| REQ-063 | MCP errors include structured error_code | specs/14_mcp_endpoints.md:56-79 | ⚠️ Not Implemented | TC-510 |
| REQ-064 | MCP enforces allowed_paths, no absolute paths in responses | specs/14_mcp_endpoints.md:126-127 | ⚠️ Not Implemented | TC-510 |

## Repo Ingestion Requirements (REQ-065 through REQ-073)

| REQ-ID | Requirement | Primary Spec(s) | Status | Evidence |
|--------|-------------|-----------------|--------|----------|
| REQ-065 | Ingestion produces repo_profile with specified fields | specs/02_repo_ingestion.md:16-25 | ⚠️ Not Implemented | TC-400 RepoScout |
| REQ-066 | Unknown values allowed but fields must be present | specs/02_repo_ingestion.md:31 | ✅ Schema | Schema enforcement |
| REQ-067 | Ingestion must not send binaries to LLMs | specs/02_repo_ingestion.md:160 | ⚠️ Not Implemented | TC-402 |
| REQ-068 | Snippet extraction skips binary files | specs/02_repo_ingestion.md:161 | ⚠️ Not Implemented | TC-420 |
| REQ-069 | Same github_ref produces identical RepoInventory | specs/02_repo_ingestion.md:184 | ⚠️ Not Implemented | TC-400, TC-560 |
| REQ-070 | Sorting must be stable | specs/02_repo_ingestion.md:185 | ⚠️ Not Implemented | All workers |
| REQ-071 | EvidenceMap claim_id must be stable | specs/02_repo_ingestion.md:186 | ⚠️ Not Implemented | TC-412 |
| REQ-072 | Adapter selection deterministic and logged | specs/02_repo_ingestion.md:264-268 | ⚠️ Not Implemented | TC-400 |
| REQ-073 | Universal fallback adapter must exist | specs/02_repo_ingestion.md:257 | ⚠️ Not Implemented | Adapter registry |

## Validation Gate Requirements (REQ-083 through REQ-088)

| REQ-ID | Requirement | Primary Spec(s) | Status | Evidence |
|--------|-------------|-----------------|--------|----------|
| REQ-083 | Validation varies by profile | specs/09_validation_gates.md:123-155 | ⚠️ Not Implemented | TC-460, TC-570 |
| REQ-084 | Profile set at run start, immutable | specs/09_validation_gates.md:156 | ⚠️ Not Implemented | Orchestrator |
| REQ-085 | Each gate has explicit timeouts | specs/09_validation_gates.md:85-120 | ⚠️ Not Implemented | TC-460 |
| REQ-086 | Timeout emits BLOCKER, no auto-retry | specs/09_validation_gates.md:116-119 | ⚠️ Not Implemented | TC-460 |
| REQ-087 | All compliance gates implemented | specs/09_validation_gates.md:196-211 | ⚠️ Partial | Preflight ✓, runtime pending |
| REQ-088 | Compliance failures blocker in prod | specs/09_validation_gates.md:211 | ⚠️ Not Implemented | TC-460 prod profile |

---

## Summary Statistics

| Status | Count | Percentage |
|--------|-------|------------|
| ✅ Implemented | 15 | 17% |
| ✅ Policy/Schema | 9 | 10% |
| ⚠️ Partial | 11 | 13% |
| ⚠️ Not Implemented | 53 | 60% |

**Total Requirements**: 88

**Coverage Analysis**:
- **Strong Coverage** (Implemented + Policy): 24/88 (27%)
- **Weak Coverage** (Partial): 11/88 (13%)
- **No Coverage** (Not Implemented): 53/88 (60%)

---

**Evidence Source**: reports/pre_impl_verification/20260127-1518/agents/AGENT_R/TRACE.md
**Cross-Reference Method**: Spec file paths, line numbers, and taskcard mappings
