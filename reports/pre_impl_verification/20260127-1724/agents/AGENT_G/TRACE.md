# Gate-to-Spec Traceability Matrix

**Audit Date**: 2026-01-27
**Auditor**: AGENT_G (Gates/Validators Auditor)
**Scope**: Validation gates and validators audit per specs/09_validation_gates.md

---

## Overview

This document maps all validation gates defined in specifications to their implementations (preflight and runtime).

**Legend**:
- **Status**: ✅ Implemented | ⚠ Partial | ❌ Missing | 🔧 Stub
- **Enforcement Strength**: Strong (BLOCKER) | Weak (WARN) | Profile-dependent

---

## Runtime Gates (launch_validate)

These gates are executed during runtime validation (`launch_validate` command) per specs/09_validation_gates.md.

| Gate ID | Gate Name | Spec Authority | Enforcement Strength | Implementation Status | Implementation Path | Evidence |
|---------|-----------|----------------|----------------------|----------------------|---------------------|----------|
| Gate 0 | Run Layout | specs/09:116-134 | Strong | ✅ Implemented | src/launch/validators/cli.py | cli.py:116-134 |
| Gate 1 | Schema Validation | specs/09:21-50 | Strong | ⚠ Partial | src/launch/validators/cli.py | cli.py:177-211 (artifacts only) |
| Gate 2 | Markdown Lint | specs/09:53-84 | Strong | ❌ Missing | N/A | cli.py:217-227 (NOT_IMPLEMENTED) |
| Gate 3 | Hugo Config | specs/09:86-116 | Strong | ❌ Missing | N/A | cli.py:217-227 (NOT_IMPLEMENTED) |
| Gate 4 | Platform Layout | specs/09:118-154 | Strong | ❌ Missing | N/A | NOT_IMPLEMENTED |
| Gate 5 | Hugo Build | specs/09:156-186 | Strong | ❌ Missing | N/A | cli.py:217-227 (NOT_IMPLEMENTED) |
| Gate 6 | Internal Links | specs/09:188-218 | Strong | ❌ Missing | N/A | cli.py:217-227 (NOT_IMPLEMENTED) |
| Gate 7 | External Links | specs/09:220-249 | Profile-dependent | ❌ Missing | N/A | cli.py:217-227 (NOT_IMPLEMENTED) |
| Gate 8 | Snippet Checks | specs/09:251-282 | Strong | ❌ Missing | N/A | cli.py:217-227 (NOT_IMPLEMENTED) |
| Gate 9 | TruthLock | specs/09:284-317 | Strong | ❌ Missing | N/A | cli.py:217-227 (NOT_IMPLEMENTED) |
| Gate 10 | Consistency | specs/09:319-353 | Strong | ❌ Missing | N/A | NOT_IMPLEMENTED |
| Gate 11 | Template Token Lint | specs/09:355-383 | Strong | ❌ Missing | N/A | cli.py:217-227 (NOT_IMPLEMENTED) |
| Gate 12 | Universality | specs/09:385-428 | Strong | ❌ Missing | N/A | NOT_IMPLEMENTED |
| Gate 13 | Rollback Metadata | specs/09:430-468 | Profile-dependent | ❌ Missing | N/A | NOT_IMPLEMENTED |
| Gate T | Test Determinism | specs/09:471-495 | Strong | ❌ Missing | N/A | NOT_IMPLEMENTED |

**Runtime Gates Summary**: 2/15 gates implemented (13%)

---

## Preflight Gates (validate_swarm_ready.py)

These gates are executed at preflight via `tools/validate_swarm_ready.py` per specs/34_strict_compliance_guarantees.md.

| Gate ID | Gate Name | Spec Authority | Guarantee | Enforcement Strength | Implementation Status | Implementation Path | Evidence |
|---------|-----------|----------------|-----------|----------------------|----------------------|---------------------|----------|
| Gate 0 | .venv Policy | specs/00 | N/A | Strong | ✅ Implemented | tools/validate_dotvenv_policy.py | validate_swarm_ready.py:214-218 |
| Gate A1 | Spec Schemas | Internal | N/A | Strong | ✅ Implemented | scripts/validate_spec_pack.py | validate_swarm_ready.py:220-225 |
| Gate A2 | Plans Integrity | Internal | N/A | Strong | ✅ Implemented | scripts/validate_plans.py | validate_swarm_ready.py:227-233 |
| Gate B | Taskcards | Internal | K (partial) | Strong | ✅ Implemented | tools/validate_taskcards.py | validate_swarm_ready.py:235-240 |
| Gate C | Status Board | Internal | N/A | Strong | ✅ Implemented | tools/generate_status_board.py | validate_swarm_ready.py:242-247 |
| Gate D | Link Integrity | Internal | N/A | Strong | ✅ Implemented | tools/check_markdown_links.py | validate_swarm_ready.py:249-254 |
| Gate E | Allowed Paths Audit | Internal | B (partial) | Strong | ✅ Implemented | tools/audit_allowed_paths.py | validate_swarm_ready.py:256-261 |
| Gate F | Platform Layout | specs/26 | N/A | Strong | ✅ Implemented | tools/validate_platform_layout.py | validate_swarm_ready.py:263-268 |
| Gate G | Pilots Contract | specs/13 | N/A | Strong | ✅ Implemented | tools/validate_pilots_contract.py | validate_swarm_ready.py:270-275 |
| Gate H | MCP Contract | specs/14,24 | N/A | Strong | ✅ Implemented | tools/validate_mcp_contract.py | validate_swarm_ready.py:277-282 |
| Gate I | Phase Reports | Internal | N/A | Strong | ✅ Implemented | tools/validate_phase_report_integrity.py | validate_swarm_ready.py:284-289 |
| Gate J | Pinned Refs | specs/34:40-86 | A | Strong | ✅ Implemented | tools/validate_pinned_refs.py | validate_swarm_ready.py:291-296 |
| Gate K | Supply Chain | specs/34:110-130 | C | Strong | ✅ Implemented | tools/validate_supply_chain_pinning.py | validate_swarm_ready.py:298-303 |
| Gate L | Secrets Hygiene | specs/34:161-187 | E | Strong | 🔧 Stub (functional) | tools/validate_secrets_hygiene.py | validate_swarm_ready.py:305-310 |
| Gate M | No Placeholders | specs/34:161-187 | E | Strong | ✅ Implemented | tools/validate_no_placeholders_production.py | validate_swarm_ready.py:312-317 |
| Gate N | Network Allowlist | specs/34:132-158 | D | Strong | ✅ Implemented | tools/validate_network_allowlist.py | validate_swarm_ready.py:319-324 |
| Gate O | Budget Config | specs/34:190-278 | F, G | Strong | ✅ Implemented | tools/validate_budgets_config.py | validate_swarm_ready.py:326-331 |
| Gate P | Version Locks | specs/34:362-393 | K | Strong | ✅ Implemented | tools/validate_taskcard_version_locks.py | validate_swarm_ready.py:333-338 |
| Gate Q | CI Parity | specs/34:280-303 | H | Strong | ✅ Implemented | tools/validate_ci_parity.py | validate_swarm_ready.py:340-345 |
| Gate R | Untrusted Code | specs/34:333-361 | J | Strong | 🔧 Stub (basic) | tools/validate_untrusted_code_policy.py | validate_swarm_ready.py:347-352 |
| Gate S | Windows Names | Internal | N/A | Strong | ✅ Implemented | tools/validate_windows_reserved_names.py | validate_swarm_ready.py:354-359 |

**Preflight Gates Summary**: 19/21 gates implemented (90%) — 2 stubs exist but are functional

---

## Cross-Reference: Spec Gates vs Implementation

### Spec-Defined Runtime Gates (specs/09_validation_gates.md)

**Gate 1: Schema Validation** (specs/09:21-50)
- **Status**: ⚠ Partial
- **Implementation**: src/launch/validators/cli.py:177-211
- **Coverage**:
  - ✅ JSON artifact validation against schemas
  - ❌ Frontmatter YAML validation (not implemented)
  - ❌ Frontmatter contract validation (not implemented)
- **Gap**: Gate only validates JSON artifacts, not markdown frontmatter

**Gate 2: Markdown Lint and Frontmatter** (specs/09:53-84)
- **Status**: ❌ Missing
- **Implementation**: None (marked NOT_IMPLEMENTED in cli.py:217-227)
- **Required Rules**:
  - Markdownlint with pinned ruleset
  - Frontmatter required field validation
  - Frontmatter type checking
- **Gap**: Entire gate not implemented

**Gate 3: Hugo Config Compatibility** (specs/09:86-116)
- **Status**: ❌ Missing
- **Implementation**: None (marked NOT_IMPLEMENTED)
- **Required Rules**:
  - Validate planned content has Hugo config coverage
  - Validate output paths match content root contract
  - Validate subdomain/family pairs enabled
- **Gap**: Entire gate not implemented

**Gate 4: Platform Layout Compliance** (specs/09:118-154)
- **Status**: ❌ Missing
- **Implementation**: None (NOT_IMPLEMENTED)
- **Note**: Preflight Gate F validates platform layout in taskcards, but runtime validation of generated content is missing
- **Gap**: Runtime validation of V2 platform paths not implemented

**Gate 5: Hugo Build** (specs/09:156-186)
- **Status**: ❌ Missing
- **Implementation**: None (marked NOT_IMPLEMENTED)
- **Required Rules**:
  - Run hugo build in production mode
  - Validate exit code 0
  - Capture and log build output
- **Gap**: Entire gate not implemented

**Gate 6: Internal Links** (specs/09:188-218)
- **Status**: ❌ Missing
- **Implementation**: None (marked NOT_IMPLEMENTED)
- **Required Rules**:
  - Validate internal markdown links resolve
  - Validate anchor references to headings
  - Validate cross-references between pages
- **Gap**: Entire gate not implemented

**Gate 7: External Links** (specs/09:220-249)
- **Status**: ❌ Missing
- **Implementation**: None (marked NOT_IMPLEMENTED)
- **Profile Behavior**: Skip in local, optional in ci, required in prod
- **Gap**: Entire gate not implemented

**Gate 8: Snippet Checks** (specs/09:251-282)
- **Status**: ❌ Missing
- **Implementation**: None (marked NOT_IMPLEMENTED)
- **Required Rules**:
  - Syntax validation for code snippets
  - Language match validation
  - Snippet catalog consistency
  - Optional: Snippet execution (ci/prod)
- **Gap**: Entire gate not implemented

**Gate 9: TruthLock** (specs/09:284-317)
- **Status**: ❌ Missing
- **Implementation**: None (marked NOT_IMPLEMENTED)
- **Required Rules**:
  - Claims must link to EvidenceMap
  - No uncited facts (unless allow_inference)
  - Claim ID stability validation
  - Contradiction resolution validation
- **Gap**: Entire gate not implemented

**Gate 10: Consistency** (specs/09:319-353)
- **Status**: ❌ Missing
- **Implementation**: None (NOT_IMPLEMENTED)
- **Required Rules**:
  - product_name consistency across artifacts
  - repo_url consistency
  - canonical_url consistency
  - Required headings/sections validation
- **Gap**: Entire gate not implemented

**Gate 11: Template Token Lint** (specs/09:355-383)
- **Status**: ❌ Missing
- **Implementation**: None (marked NOT_IMPLEMENTED)
- **Required Rules**:
  - No unresolved `__UPPER_SNAKE__` tokens
  - No unresolved `__PLATFORM__` tokens
  - No unresolved `{{template_var}}` tokens
  - Exclude code blocks from validation
- **Gap**: Entire gate not implemented

**Gate 12: Universality Gates** (specs/09:385-428)
- **Status**: ❌ Missing
- **Implementation**: None (NOT_IMPLEMENTED)
- **Required Rules**:
  - Tier compliance (minimal vs rich)
  - Limitations honesty (ProductFacts.limitations)
  - Distribution correctness (install commands)
  - No hidden inference
- **Gap**: Entire gate not implemented

**Gate 13: Rollback Metadata Validation** (specs/09:430-468)
- **Status**: ❌ Missing
- **Implementation**: None (NOT_IMPLEMENTED)
- **Profile Behavior**: Only in prod profile (BLOCKER), warn in ci, skip in local
- **Required Fields**: base_ref, run_id, rollback_steps, affected_paths
- **Gap**: Entire gate not implemented

**Gate T: Test Determinism Configuration** (specs/09:471-495)
- **Status**: ❌ Missing
- **Implementation**: None (NOT_IMPLEMENTED)
- **Required Rules**:
  - Validate PYTHONHASHSEED=0 in test config
  - Check pyproject.toml, pytest.ini, or CI workflows
- **Gap**: Entire gate not implemented

---

## Determinism Analysis

Per specs/09_validation_gates.md requirement: "Same inputs must produce same validation reports."

### Deterministic Gates

**Preflight Gates (all deterministic)**:
- Gate J (Pinned Refs): ✅ Pure function (config parsing + regex)
- Gate K (Supply Chain): ✅ File existence checks + text parsing
- Gate L (Secrets): ✅ Pattern matching (deterministic patterns)
- Gate M (Placeholders): ✅ Pattern matching + file scanning
- Gate N (Network Allowlist): ✅ YAML parsing + set membership
- Gate O (Budgets): ✅ Schema validation (deterministic)
- Gate P (Version Locks): ✅ YAML field validation
- Gate Q (CI Parity): ✅ YAML parsing + pattern matching
- Gate R (Untrusted Code): ✅ Static analysis (deterministic)

**Runtime Gates (implemented)**:
- Gate 0 (Run Layout): ✅ File existence checks
- Gate 1 (Schema): ✅ JSON Schema Draft 2020-12 (deterministic validator)

### Non-Deterministic Risks

**Potential non-determinism sources**:
- Gate 7 (External Links): Network checks are inherently non-deterministic (timeouts, availability)
  - **Spec mitigation**: Profile-dependent, skip by default in local
- Gate 5 (Hugo Build): Build timestamps may vary
  - **Spec mitigation**: Only check exit code, not output contents
- Gate 8 (Snippet Execution): Container execution may have timing variance
  - **Spec mitigation**: Optional, syntax-only in local profile

**All NOT_IMPLEMENTED gates**: Cannot assess determinism (not implemented)

---

## Profile Support Analysis

Per specs/09_validation_gates.md:550-586, gates must support three profiles: local, ci, prod.

### Profile Configuration

**Profile Precedence** (specs/09:83-105):
1. run_config.validation_profile (highest)
2. --profile CLI argument
3. LAUNCH_VALIDATION_PROFILE env var
4. Default: "local"

**Implementation Evidence**: src/launch/validators/cli.py:83-111 implements correct precedence

### Profile-Specific Behavior

**Implemented Gates**:
- ✅ Gate 0-1 (Runtime): Profile recorded in validation_report.json (cli.py:256)
- ✅ All preflight gates: No profile variance (always strict)

**NOT_IMPLEMENTED Gates**:
- ⚠ Gates 2-13, T: Profile behavior marked as BLOCKER in prod (cli.py:230)
- ✅ Good: Prevents false passes per Guarantee E

**Missing Profile Support**:
- ❌ Gate 7 (External Links): Should skip in local, optional in ci, required in prod
- ❌ Gate 8 (Snippet Execution): Should skip execution in local, run in ci/prod
- ❌ Gate 13 (Rollback): Should skip in local, warn in ci, BLOCKER in prod

---

## Timeout Enforcement

Per specs/09_validation_gates.md:511-547, all gates must have explicit timeouts.

### Timeout Configuration (Binding)

**Spec Requirements** (specs/09:515-542):
- local: Fast (30-300s depending on gate)
- ci: Longer (60-600s depending on gate)
- prod: Same as ci

### Implementation Status

**Preflight Gates**:
- ✅ Gate runner timeout: 60s hardcoded (validate_swarm_ready.py:113)
- ⚠ Individual gate timeouts: Not configurable per profile
- ❌ Timeout behavior: Emits "Timeout" status but does not use GATE_TIMEOUT error code

**Runtime Gates**:
- ❌ No timeout enforcement found in cli.py
- ❌ Gates do not respect profile-specific timeout values
- ❌ No GATE_TIMEOUT error code emission

**Gap**: Timeout values are hardcoded, not profile-dependent per spec

---

## Error Code Consistency

Per specs/01_system_contract.md and specs/error_code_registry.md, all gates must use registered error codes.

### Error Codes Defined in Spec

**Gate Error Codes** (specs/09_validation_gates.md):
- Schema (Gate 1): GATE_SCHEMA_VALIDATION_FAILED, GATE_FRONTMATTER_INVALID_YAML, GATE_FRONTMATTER_CONTRACT_VIOLATION
- Markdown (Gate 2): GATE_MARKDOWN_LINT_ERROR, GATE_FRONTMATTER_MISSING, GATE_FRONTMATTER_REQUIRED_FIELD_MISSING, GATE_FRONTMATTER_TYPE_MISMATCH
- Hugo Config (Gate 3): GATE_HUGO_CONFIG_MISSING, GATE_HUGO_CONFIG_PATH_MISMATCH, GATE_HUGO_CONFIG_SUBDOMAIN_NOT_ENABLED
- Platform (Gate 4): GATE_PLATFORM_LAYOUT_MISSING_SEGMENT, GATE_PLATFORM_TOKEN_UNRESOLVED, GATE_PLATFORM_PATH_NOT_ALLOWED, GATE_PLATFORM_INCONSISTENT_MODE
- Hugo Build (Gate 5): GATE_HUGO_BUILD_FAILED, GATE_HUGO_BUILD_ERROR, GATE_HUGO_BUILD_TIMEOUT
- Links (Gate 6,7): GATE_LINK_BROKEN_INTERNAL, GATE_LINK_BROKEN_ANCHOR, GATE_LINK_BROKEN_RELATIVE, GATE_LINK_EXTERNAL_UNREACHABLE, GATE_LINK_EXTERNAL_TIMEOUT
- Snippets (Gate 8): GATE_SNIPPET_SYNTAX_ERROR, GATE_SNIPPET_LANGUAGE_MISMATCH, GATE_SNIPPET_EXECUTION_FAILED, GATE_SNIPPET_NOT_IN_CATALOG
- TruthLock (Gate 9): GATE_TRUTHLOCK_UNCITED_FACT, GATE_TRUTHLOCK_INVALID_CLAIM_ID, GATE_TRUTHLOCK_UNRESOLVED_CONTRADICTION, GATE_TRUTHLOCK_EVIDENCE_MISSING
- Consistency (Gate 10): GATE_CONSISTENCY_PRODUCT_NAME_MISMATCH, GATE_CONSISTENCY_REPO_URL_MISMATCH, GATE_CONSISTENCY_CANONICAL_URL_MISMATCH, GATE_CONSISTENCY_REQUIRED_HEADING_MISSING, GATE_CONSISTENCY_REQUIRED_SECTION_MISSING
- Template (Gate 11): GATE_TEMPLATE_TOKEN_UNRESOLVED, GATE_TEMPLATE_PLATFORM_TOKEN
- Universality (Gate 12): GATE_UNIVERSALITY_TIER_VIOLATION, GATE_UNIVERSALITY_LIMITATIONS_MISSING, GATE_UNIVERSALITY_DISTRIBUTION_MISMATCH, GATE_UNIVERSALITY_HIDDEN_INFERENCE
- Rollback (Gate 13): PR_MISSING_ROLLBACK_METADATA, PR_INVALID_BASE_REF_FORMAT, PR_EMPTY_ROLLBACK_STEPS, PR_EMPTY_AFFECTED_PATHS, PR_AFFECTED_PATH_NOT_IN_DIFF
- Test Determinism (Gate T): TEST_MISSING_PYTHONHASHSEED, TEST_DETERMINISM_NOT_ENFORCED

### Error Codes in Implementation

**Runtime Gates (cli.py)**:
- ✅ GATE_RUN_LAYOUT_MISSING_PATHS (cli.py:125)
- ✅ GATE_TOOLCHAIN_LOCK_FAILED (cli.py:148)
- ✅ SCHEMA_VALIDATION_FAILED (cli.py:168)
- ❌ GATE_NOT_IMPLEMENTED (cli.py:236) - Not in spec registry

**Preflight Gates**:
- Preflight gates do not use structured error codes (only exit codes)
- Exit codes: 0 = pass, 1 = fail

**Gap**: NOT_IMPLEMENTED gates do not emit spec-defined error codes

---

## Schema Compliance

### Validation Report Schema

**Schema**: specs/schemas/validation_report.schema.json

**Required Fields**:
- schema_version
- ok
- profile
- gates (array of {name, ok, log_path?})
- issues (array of issue.schema.json)

**Implementation Evidence**: src/launch/validators/cli.py:253-261

**Compliance**:
- ✅ All required fields present
- ✅ Profile field correct (cli.py:256)
- ✅ Gates array structure matches schema
- ✅ Issues array structure matches issue.schema.json

### Issue Schema

**Schema**: specs/schemas/issue.schema.json

**Required Fields**:
- issue_id, gate, severity, message, status
- error_code (required for severity=error/blocker)

**Implementation Evidence**: cli.py:44-71

**Compliance**:
- ✅ All required fields present in _issue() helper
- ✅ error_code included when severity=blocker
- ⚠ Optional fields (location, files, suggested_fix) supported

---

## Acceptance Criteria (specs/09:589-598)

**Spec Requirements**:
1. ✅ validation_report.ok == true when all gates pass
2. ✅ validation_report.json validates against schema
3. ✅ validation_report.profile field matches profile used
4. ❌ All timeouts respected (NOT IMPLEMENTED)
5. ✅ All issues recorded in issues[] array
6. ❌ Gate execution order enforced (NOT DEFINED in implementation)

**Gate Execution Order** (specs/09:598):
> schema → lint → hugo_config → content_layout_platform → hugo_build → links → snippets → truthlock → consistency

**Implementation**: cli.py executes gates sequentially but order is: run_layout, toolchain_lock, run_config_schema, artifact_schema, then all NOT_IMPLEMENTED

**Gap**: Spec-defined gate execution order not followed (most gates not implemented)

---

## Summary Statistics

**Runtime Gates**: 2/15 implemented (13%)
**Preflight Gates**: 19/21 implemented (90%)
**Total Gates**: 21/36 implemented (58%)

**Blocker Gaps**:
- 13 runtime gates not implemented (87% gap)
- Runtime validation severely incomplete
- TruthLock gate (critical for evidence grounding) missing
- Hugo build/config validation missing (site generation cannot be validated)

**Compliance Gaps**:
- Profile-specific timeouts not implemented
- Gate execution order not enforced
- NOT_IMPLEMENTED gates marked as FAILED (good: prevents false passes)
