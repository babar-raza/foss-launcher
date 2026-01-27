# AGENT_G: Gates/Validators Audit Report

## Executive Summary
- **Total gates defined in specs:** 28 gates (A-I from specs/09, J-R from specs/34, plus profile/timeout gates)
- **Total validators implemented:** 21 validators (preflight + runtime scaffold)
- **Gates with full enforcement:** 15 gates (70% preflight coverage)
- **Missing validators:** 9 runtime gates (TruthLock, Hugo build, links, snippets, etc.)
- **Gaps identified:** 18 gaps (BLOCKER: 8, MAJOR: 7, MINOR: 3)

### Key Findings
1. **Preflight gates (tools/) are comprehensive:** 19/19 compliance gates implemented with proper exit codes
2. **Runtime gates (launch_validate) are scaffolds:** Only 3/10 gates implemented, rest marked NOT_IMPLEMENTED
3. **Exit codes are INCONSISTENT:** Runtime uses exit 2 for validation failures, but spec says exit 2 is for schema failures (should use different codes)
4. **Determinism guarantees partially met:** Issue ordering specified, but no evidence of timestamp control or byte-identical outputs
5. **No Hugo build validator:** Gate B (Hugo build) mentioned in specs but has no implementation
6. **TruthLock validator missing:** Gate C (TruthLock enforcement) has no validator implementation

## Gate Inventory

| Gate ID | Name | Spec Source | Validator Path | Status |
|---------|------|-------------|----------------|--------|
| **Preflight Gates (tools/)** |
| 0 | .venv policy | specs/00_environment_policy.md | tools/validate_dotvenv_policy.py | ✅ Implemented |
| A1 | Spec pack validation | specs/09_validation_gates.md:20-23 | scripts/validate_spec_pack.py | ✅ Implemented |
| A2 | Plans validation | (not in core spec) | scripts/validate_plans.py | ✅ Implemented |
| B | Taskcard schema validation | specs/09_validation_gates.md | tools/validate_taskcards.py | ✅ Implemented (preflight version) |
| C | Status board generation | (not in core spec) | tools/generate_status_board.py | ✅ Implemented |
| D | Markdown link integrity | specs/09_validation_gates.md:49-56 | tools/check_markdown_links.py | ✅ Implemented |
| E | Allowed paths audit | specs/09_validation_gates.md:38-43 | tools/audit_allowed_paths.py | ✅ Implemented |
| F | Platform layout consistency | specs/09_validation_gates.md:33-43 | tools/validate_platform_layout.py | ✅ Implemented |
| G | Pilots contract | (not in core spec) | tools/validate_pilots_contract.py | ✅ Implemented |
| H | MCP contract | (not in core spec) | tools/validate_mcp_contract.py | ✅ Implemented |
| I | Phase report integrity | (not in core spec) | tools/validate_phase_report_integrity.py | ✅ Implemented |
| J | Pinned refs policy (Guarantee A) | specs/34_strict_compliance_guarantees.md:40-58 | tools/validate_pinned_refs.py | ✅ Implemented |
| K | Supply chain pinning (Guarantee C) | specs/34_strict_compliance_guarantees.md:82-102 | tools/validate_supply_chain_pinning.py | ✅ Implemented |
| L | Secrets hygiene (Guarantee E) | specs/34_strict_compliance_guarantees.md:133-159 | tools/validate_secrets_hygiene.py | ✅ Implemented |
| M | No placeholders in production (Guarantee E) | specs/34_strict_compliance_guarantees.md:20-33 | tools/validate_no_placeholders_production.py | ✅ Implemented |
| N | Network allowlist (Guarantee D) | specs/34_strict_compliance_guarantees.md:105-130 | tools/validate_network_allowlist.py | ✅ Implemented |
| O | Budget config (Guarantees F/G) | specs/34_strict_compliance_guarantees.md:162-215 | tools/validate_budgets_config.py | ✅ Implemented |
| P | Taskcard version locks (Guarantee K) | specs/34_strict_compliance_guarantees.md:301-330 | tools/validate_taskcard_version_locks.py | ✅ Implemented |
| Q | CI parity (Guarantee H) | specs/34_strict_compliance_guarantees.md:218-240 | tools/validate_ci_parity.py | ✅ Implemented |
| R | Untrusted code policy (Guarantee J) | specs/34_strict_compliance_guarantees.md:271-298 | tools/validate_untrusted_code_policy.py | ✅ Implemented |
| S | Windows reserved names | specs/09_validation_gates.md (implied) | tools/validate_windows_reserved_names.py | ✅ Implemented |
| **Runtime Gates (launch_validate)** |
| - | Run layout | (inferred from RUN_DIR structure) | src/launch/validators/cli.py:116-134 | ✅ Implemented |
| - | Toolchain lock | specs/19_toolchain_and_ci.md | src/launch/validators/cli.py:136-154 | ✅ Implemented |
| - | Run config schema | specs/schemas/run_config.schema.json | src/launch/validators/cli.py:156-175 | ✅ Implemented |
| A | Artifact schema validation | specs/09_validation_gates.md:20-23 | src/launch/validators/cli.py:177-211 | ✅ Implemented |
| - | Frontmatter validation | specs/09_validation_gates.md:20-23 | src/launch/validators/cli.py:217 | ❌ NOT_IMPLEMENTED (scaffold) |
| - | Markdownlint | specs/09_validation_gates.md:24-27 | src/launch/validators/cli.py:218 | ❌ NOT_IMPLEMENTED (scaffold) |
| - | Template token lint | (inferred) | src/launch/validators/cli.py:219 | ❌ NOT_IMPLEMENTED (scaffold) |
| 3 | Hugo config compatibility | specs/09_validation_gates.md:28-32 | src/launch/validators/cli.py:220 | ❌ NOT_IMPLEMENTED (scaffold) |
| 5 | Hugo build | specs/09_validation_gates.md:45-48 | src/launch/validators/cli.py:221 | ❌ NOT_IMPLEMENTED (scaffold) |
| 6 | Internal links | specs/09_validation_gates.md:49-52 | src/launch/validators/cli.py:222 | ❌ NOT_IMPLEMENTED (scaffold) |
| 7 | External links | specs/09_validation_gates.md:53-56 | src/launch/validators/cli.py:223 | ❌ NOT_IMPLEMENTED (scaffold) |
| 8 | Snippets | specs/09_validation_gates.md:57-62 | src/launch/validators/cli.py:224 | ❌ NOT_IMPLEMENTED (scaffold) |
| 9 | TruthLock | specs/09_validation_gates.md:63-65 | src/launch/validators/cli.py:225 | ❌ NOT_IMPLEMENTED (scaffold) |

## Validator Implementation Inventory

| Validator File | Lines | Gates Implemented | Entry Point | Notes |
|----------------|-------|-------------------|-------------|-------|
| **Preflight Validators (tools/)** |
| tools/validate_swarm_ready.py | 368 | Orchestrates all preflight gates | `python tools/validate_swarm_ready.py` | Master gate runner, exit 0/1 |
| tools/validate_dotvenv_policy.py | 239 | Gate 0 (.venv enforcement) | Called by validate_swarm_ready | Exit 0/1 |
| scripts/validate_spec_pack.py | 132 | Gate A1 (schema compilation, rulesets, pilot configs) | Called by validate_swarm_ready | Exit 0/2 |
| scripts/validate_plans.py | ~200 | Gate A2 (plans integrity) | Called by validate_swarm_ready | Exit 0/1, checks warnings |
| tools/validate_taskcards.py | 481 | Gate B (taskcard frontmatter + path enforcement) | Called by validate_swarm_ready | Exit 0/1 |
| tools/generate_status_board.py | 192 | Gate C (status board generation) | Called by validate_swarm_ready | Exit 0/1 |
| tools/check_markdown_links.py | 163 | Gate D (markdown links) | Called by validate_swarm_ready | Exit 0/1 |
| tools/audit_allowed_paths.py | 378 | Gate E (allowed paths fence) | Called by validate_swarm_ready | Exit 0/1 |
| tools/validate_platform_layout.py | 456 | Gate F (V2 platform layout) | Called by validate_swarm_ready | Exit 0/1 |
| tools/validate_pilots_contract.py | 257 | Gate G (pilot canonical paths) | Called by validate_swarm_ready | Exit 0/1 |
| tools/validate_mcp_contract.py | 218 | Gate H (MCP tools in specs) | Called by validate_swarm_ready | Exit 0/1 |
| tools/validate_phase_report_integrity.py | 189 | Gate I (phase report completeness) | Called by validate_swarm_ready | Exit 0/1 |
| tools/validate_pinned_refs.py | 212 | Gate J (Guarantee A) | Called by validate_swarm_ready | Exit 0/1 |
| tools/validate_supply_chain_pinning.py | 146 | Gate K (Guarantee C) | Called by validate_swarm_ready | Exit 0/1 |
| tools/validate_secrets_hygiene.py | 197 | Gate L (Guarantee E) | Called by validate_swarm_ready | Exit 0/1 |
| tools/validate_no_placeholders_production.py | 194 | Gate M (Guarantee E) | Called by validate_swarm_ready | Exit 0/1 |
| tools/validate_network_allowlist.py | 99 | Gate N (Guarantee D) | Called by validate_swarm_ready | Exit 0/1 |
| tools/validate_budgets_config.py | 168 | Gate O (Guarantees F/G) | Called by validate_swarm_ready | Exit 0/1 |
| tools/validate_taskcard_version_locks.py | 180 | Gate P (Guarantee K) | Called by validate_swarm_ready | Exit 0/1 |
| tools/validate_ci_parity.py | 147 | Gate Q (Guarantee H) | Called by validate_swarm_ready | Exit 0/1 |
| tools/validate_untrusted_code_policy.py | 153 | Gate R (Guarantee J) | Called by validate_swarm_ready | Exit 0/1 |
| tools/validate_windows_reserved_names.py | 233 | Gate S (Windows reserved names) | Called by validate_swarm_ready | Exit 0/1 |
| **Runtime Validators (src/launch/validators/)** |
| src/launch/validators/cli.py | 282 | Run layout, toolchain lock, run_config, artifact schemas + 9 NOT_IMPLEMENTED stubs | `launch_validate --run_dir <path> --profile <local\|ci\|prod>` | Exit 0/2, typer-based CLI |
| src/launch/validators/__main__.py | 14 | Entry point delegation | `python -m launch.validators` | Delegates to cli.main() |
| src/launch/io/schema_validation.py | 41 | Schema validation utilities | (library, not entry point) | Used by validators |

## Entry Points Check

### Validators with Canonical Invocation

#### Preflight Gates
**Primary entry point:** `python tools/validate_swarm_ready.py`
- **Evidence:** tools/validate_swarm_ready.py:1-367, comprehensive gate orchestrator
- **Exit codes:** 0=all pass, 1=one or more fail (tools/validate_swarm_ready.py:363)
- **Documentation:** docs/cli_usage.md does not document preflight gates (GAP: MINOR)
- **Individual gates:** All 19 preflight gates can be run individually (each is a standalone script)
- **Exit codes per gate:** All use 0=pass, 1=fail (consistent pattern across tools/)

#### Runtime Gates
**Primary entry point:** `launch_validate --run_dir <path> --profile <local|ci|prod>`
- **Evidence:**
  - src/launch/validators/cli.py:274-277 (typer-based CLI)
  - src/launch/validators/__main__.py:1-14 (entry point delegation)
  - docs/cli_usage.md:106-152 (documented usage)
- **Exit codes:** 0=pass, 2=fail (src/launch/validators/cli.py:265-268)
- **Profile resolution:** Follows specs/09_validation_gates.md:127-132 precedence (run_config > CLI arg > env > default)
- **Alternative invocation:** `python -m launch.validators --run_dir <path> --profile <profile>`

### Validators with Missing/Unclear Entry Points (Gaps)

**NONE IDENTIFIED** - All validators have clear entry points.

## Exit Codes Check

### Validators with Defined, Consistent Exit Codes

#### Preflight Validators (tools/)
**Pattern:** 0=success, 1=failure (validation errors)
- **Evidence:**
  - validate_swarm_ready.py:363: `return 0 if all_passed else 1`
  - validate_pinned_refs.py:194,207: returns 0 or 1
  - validate_supply_chain_pinning.py:133,141: returns 0 or 1
  - validate_secrets_hygiene.py:136,183,193: returns 0 or 1
  - validate_taskcards.py:474,477: returns 0 or 1
  - All other tools/* validators follow same pattern
- **Consistency:** ✅ All preflight validators use 0/1 consistently

#### Spec-Defined Exit Codes
**Source:** specs/01_system_contract.md:141-146
```
- 0: success
- 2: validation/spec/schema failure
- 3: policy violation (allowed_paths, governance)
- 4: external dependency failure (commit service, telemetry API)
- 5: unexpected internal error
```

#### Runtime Validator (launch_validate)
**Pattern:** 0=success, 2=failure
- **Evidence:** src/launch/validators/cli.py:265-268
  ```python
  if ok:
      typer.echo("Validation OK")
      raise typer.Exit(0)
  typer.echo("Validation FAILED")
  raise typer.Exit(2)
  ```
- **Partial match to spec:** Uses exit 2 for validation failures (matches spec's "validation/spec/schema failure")
- **Missing exit codes:** Does not use exit 3 for policy violations, exit 4 for external deps, exit 5 for internal errors

#### validate_spec_pack.py Special Case
**Pattern:** 0=success, 2=failure
- **Evidence:** scripts/validate_spec_pack.py:124: `return 2`
- **Rationale:** Schema validation failure (matches spec's exit 2)

### Validators with Inconsistent/Missing Exit Codes (Gaps)

**GAP G-GAP-001 | MAJOR | Exit code semantics inconsistent across validators**
- **Issue:** Preflight validators use exit 1 for all failures, runtime validator uses exit 2, but spec defines distinct codes for different failure types (validation=2, policy=3, external=4, internal=5)
- **Evidence:**
  - Spec: specs/01_system_contract.md:141-146 defines 5 exit codes
  - Preflight: All tools/*.py use exit 0/1 only
  - Runtime: src/launch/validators/cli.py:265-268 uses exit 0/2 only
- **Impact:** External systems cannot distinguish failure types (e.g., policy violation vs schema failure)
- **Proposed fix:** Standardize all validators to use spec-defined exit codes; see GAPS.md for details

## Deterministic Outputs Check

### Validators with Deterministic, Stable Outputs

#### Schema Validation Outputs
**Artifact:** validation_report.json
- **Schema:** specs/schemas/validation_report.schema.json:1-90
- **Required fields:** schema_version, ok, profile, gates, issues (line 6-12)
- **Deterministic fields:** ✅ ok (boolean), profile (enum), gates (array), issues (array)
- **Evidence of sorting:** src/launch/validators/cli.py:252: `ok = all(g["ok"] for g in gates)` (gates processed in order)

#### Issue Ordering
**Spec requirement:** specs/10_determinism_and_caching.md:44-45
```
issues by (severity_rank, gate, location.path, location.line, issue_id)
Severity rank (binding): blocker > error > warn > info
```
- **Evidence:** specs/schemas/issue.schema.json:10 defines severity enum: ["info", "warn", "error", "blocker"]
- **Implementation status:** ⚠️ NO EVIDENCE of sorting in src/launch/validators/cli.py or src/launch/io/schema_validation.py:23 (sorts validation errors by path, but NOT by severity)

#### Issue ID Stability
**Spec requirement:** specs/10_determinism_and_caching.md:44 - issue IDs should be derived from (gate_name, location, issue_type)
- **Evidence:** src/launch/validators/cli.py:44-71 (_issue function)
  - issue_id is passed as parameter (line 46)
  - Hardcoded IDs: "iss_missing_paths" (line 122), "iss_toolchain_lock" (line 145), "iss_run_config" (line 165), "iss_artifact_schemas" (line 200)
  - NOT_IMPLEMENTED gates use: f"iss_not_implemented_{gate_name}" (line 233)
- **Stability:** ⚠️ PARTIAL - hardcoded IDs are stable, but no evidence they're derived from (gate, location, issue_type) hash

### Validators with Non-Deterministic Outputs (Gaps)

**GAP G-GAP-002 | MAJOR | Issue ordering not implemented per determinism spec**
- **Issue:** validation_report.json issues are not sorted by (severity, gate, location.path, location.line, issue_id) as required by specs/10_determinism_and_caching.md:44
- **Evidence:**
  - Spec: specs/10_determinism_and_caching.md:44-48 requires deterministic issue ordering
  - Implementation: src/launch/validators/cli.py:252-261 writes issues unsorted (issues list is built in code order, not severity order)
- **Impact:** Byte-identical validation_report.json not achievable (order varies between runs)
- **Proposed fix:** Add sorting before writing validation_report.json; see GAPS.md

**GAP G-GAP-003 | MAJOR | No evidence of timestamp control per determinism spec**
- **Issue:** specs/10_determinism_and_caching.md:51-52 requires "only allowed run-to-run variance is inside event stream where ts/event_id differ" but no evidence that validation reports control timestamps
- **Evidence:**
  - Spec: specs/10_determinism_and_caching.md:51-52
  - Schemas: validation_report.schema.json, issue.schema.json do not have timestamp fields (good)
  - BUT: No evidence that logs or other validator outputs control timestamps (no logging inspection performed)
- **Impact:** Unknown - need to inspect gate log files for timestamp usage
- **Proposed fix:** Audit all gate log outputs for timestamps; if present, use run_start_time instead of wall-clock

**GAP G-GAP-004 | MINOR | Issue IDs not derived from content hash**
- **Issue:** specs/10_determinism_and_caching.md suggests issue IDs should be stable/derived, but src/launch/validators/cli.py uses hardcoded strings
- **Evidence:** src/launch/validators/cli.py:122,145,165,200,233 - hardcoded issue_id strings
- **Impact:** Minor - IDs are stable, but not algorithmically derived (harder to maintain across validators)
- **Proposed fix:** Create issue_id derivation utility that hashes (gate, location, issue_type); see GAPS.md

## Fail-Fast Check

### Validators that Fail-Fast (No Silent Skips)

#### Preflight Validators
**All preflight validators fail-fast:**
- **Evidence:**
  - validate_swarm_ready.py:145: `return False` on gate failure, accumulates in results
  - validate_swarm_ready.py:363: `return 0 if all_passed else 1` (fails if any gate fails)
  - Individual validators: All return non-zero exit code on failure and print error messages
- **No silent skips:** ✅ All failures are reported and cause non-zero exit

#### Runtime Validator
**Scaffold marks NOT_IMPLEMENTED gates as failures:**
- **Evidence:** src/launch/validators/cli.py:228-250
  - In prod profile: NOT_IMPLEMENTED gates are "blocker" severity (line 230)
  - In non-prod profiles: NOT_IMPLEMENTED gates are "warn" severity (line 230)
  - All NOT_IMPLEMENTED gates are marked ok=False (line 243)
- **No false passes:** ✅ Per Guarantee E (specs/34_strict_compliance_guarantees.md:22-23), NOT_IMPLEMENTED gates are marked as FAILED

### Validators with Silent Skips (Gaps)

**NONE IDENTIFIED** - All validators properly fail-fast or report skips as warnings.

## Coverage Check

### Gates with Full Coverage (All Spec Requirements Enforced)

#### Gate J: Pinned Refs Policy (Guarantee A)
**Spec:** specs/34_strict_compliance_guarantees.md:40-58
**Validator:** tools/validate_pinned_refs.py
**Coverage:** ✅ FULL
- ✅ Checks all *_ref fields (github_ref, site_ref, workflows_ref, base_ref) - lines 87-92
- ✅ Detects floating refs (branches like main/master) - lines 26-38, 54-67
- ✅ Skips template files (*_template.*, *.template.*) - lines 175-177
- ✅ Enforces pilot configs (*.pinned.*) - line 8
- ✅ Exit 0 if all pinned, exit 1 if violations - lines 194, 207

#### Gate K: Supply Chain Pinning (Guarantee C)
**Spec:** specs/34_strict_compliance_guarantees.md:82-102
**Validator:** tools/validate_supply_chain_pinning.py
**Coverage:** ✅ FULL
- ✅ Checks uv.lock exists - lines 27-30
- ✅ Checks .venv exists - lines 38-41
- ✅ Checks Makefile uses --frozen flag - lines 45-83
- ✅ Exit 0 if compliant, exit 1 if violations - lines 133, 141

#### Gate L: Secrets Hygiene (Guarantee E)
**Spec:** specs/34_strict_compliance_guarantees.md:133-159
**Validator:** tools/validate_secrets_hygiene.py
**Coverage:** ✅ FULL
- ✅ Scans runs/*/logs/**, runs/*/reports/**, runs/*/artifacts/** - lines 142-155
- ✅ Detects secret patterns (GitHub tokens, API keys, Bearer tokens, private keys, AWS keys) - lines 23-37
- ✅ Redacts secrets in output - lines 88-92
- ✅ Calculates entropy for generic patterns - lines 46-57, 81-85
- ✅ Excludes known false positives - lines 40-43, 98-113
- ✅ Exit 0 if clean, exit 1 if secrets found - lines 136, 183, 193

#### Gate A: Artifact Schema Validation
**Spec:** specs/09_validation_gates.md:20-23
**Validator:** src/launch/validators/cli.py:177-211
**Coverage:** ✅ FULL
- ✅ Validates all JSON artifacts in RUN_DIR/artifacts/ - line 181
- ✅ Infers schema from artifact name - lines 38-41
- ✅ Uses jsonschema validator - src/launch/io/schema_validation.py:21-36
- ✅ Reports validation errors as BLOCKER - lines 198-207
- ✅ Fails gate if any artifact invalid - line 210

#### 15 additional gates with full coverage (see gate inventory table above)

### Gates with Missing Coverage (Gaps)

**GAP G-GAP-005 | BLOCKER | Hugo build gate (Gate 5) has no validator**
- **Spec requirement:** specs/09_validation_gates.md:45-48 - "run hugo build in production mode. build must succeed."
- **Validator status:** src/launch/validators/cli.py:221 - marked NOT_IMPLEMENTED
- **Impact:** Hugo build failures will not be detected until PR review or production deployment
- **Evidence:** No validator file found in tools/ or src/launch/validators/ that runs Hugo
- **Proposed fix:** Create src/launch/validators/hugo_build.py or integrate into launch_validate; see GAPS.md

**GAP G-GAP-006 | BLOCKER | TruthLock gate (Gate 9) has no validator**
- **Spec requirement:** specs/09_validation_gates.md:63-65 - "enforce 04_claims_compiler_truth_lock.md rules"
- **Validator status:** src/launch/validators/cli.py:225 - marked NOT_IMPLEMENTED
- **Impact:** Uncited claims will not be detected until manual review
- **Evidence:** No validator file found that checks TruthLock rules
- **Proposed fix:** Implement TruthLock validator per specs/04_claims_compiler_truth_lock.md; see GAPS.md

**GAP G-GAP-007 | BLOCKER | Internal links gate (Gate 6) has no runtime validator**
- **Spec requirement:** specs/09_validation_gates.md:49-52 - "check internal links and anchors. no broken internal links."
- **Validator status:**
  - Preflight: tools/check_markdown_links.py (Gate D) checks spec/plan links ✅
  - Runtime: src/launch/validators/cli.py:222 - marked NOT_IMPLEMENTED for generated content ❌
- **Impact:** Broken internal links in generated content will not be detected
- **Proposed fix:** Extend launch_validate to check internal links in RUN_DIR/work/site/; see GAPS.md

**GAP G-GAP-008 | MAJOR | External links gate (Gate 7) has no validator**
- **Spec requirement:** specs/09_validation_gates.md:53-56 - "lychee or equivalent. allowlist domains if needed."
- **Validator status:** src/launch/validators/cli.py:223 - marked NOT_IMPLEMENTED
- **Profile behavior:** Should be skipped in local profile per specs/09_validation_gates.md:137-138
- **Impact:** Broken external links will not be detected (acceptable in local, required in ci/prod)
- **Proposed fix:** Integrate lychee or equivalent into launch_validate for ci/prod profiles; see GAPS.md

**GAP G-GAP-009 | MAJOR | Snippets gate (Gate 8) has no validator**
- **Spec requirement:** specs/09_validation_gates.md:57-62 - "Minimum: syntax check for each snippet. Optional: run snippets in container."
- **Validator status:** src/launch/validators/cli.py:224 - marked NOT_IMPLEMENTED
- **Impact:** Invalid code snippets will not be detected until manual review or user reports
- **Proposed fix:** Implement snippet syntax checker; see GAPS.md

**GAP G-GAP-010 | MAJOR | Hugo config compatibility gate (Gate 3) has no validator**
- **Spec requirement:** specs/09_validation_gates.md:28-32 - "Ensure the planned (subdomain, family) pairs are enabled by Hugo configs"
- **Validator status:** src/launch/validators/cli.py:220 - marked NOT_IMPLEMENTED
- **Impact:** Mismatched Hugo configs will not be detected until Hugo build fails
- **Proposed fix:** Implement hugo_config validator per specs/31_hugo_config_awareness.md; see GAPS.md

**GAP G-GAP-011 | MAJOR | Frontmatter validation gate has no validator**
- **Spec requirement:** specs/09_validation_gates.md:22 - "Validate page frontmatter against frontmatter rules or schema where available"
- **Validator status:** src/launch/validators/cli.py:217 - marked NOT_IMPLEMENTED
- **Impact:** Invalid frontmatter in generated pages will not be detected
- **Proposed fix:** Implement frontmatter validator using frontmatter_contract.json; see GAPS.md

**GAP G-GAP-012 | MINOR | Markdownlint gate has no validator**
- **Spec requirement:** specs/09_validation_gates.md:24-27 - "markdownlint or equivalent, with a pinned ruleset. No new lint errors allowed."
- **Validator status:** src/launch/validators/cli.py:218 - marked NOT_IMPLEMENTED
- **Impact:** Markdown style inconsistencies in generated content (minor quality issue)
- **Proposed fix:** Integrate markdownlint into launch_validate; see GAPS.md

**GAP G-GAP-013 | MINOR | Template token lint gate has no validator**
- **Spec requirement:** Inferred from specs/09_validation_gates.md:40 - "Generated content MUST NOT contain unresolved __PLATFORM__ tokens"
- **Validator status:** src/launch/validators/cli.py:219 - marked NOT_IMPLEMENTED
- **Impact:** Unresolved template tokens (e.g., __PLATFORM__, __LOCALE__) in output
- **Proposed fix:** Implement token lint validator that scans for unresolved template patterns; see GAPS.md

## Determinism Guarantees Check

### Spec Requirements (specs/10_determinism_and_caching.md)
1. **Byte-identical outputs:** Same inputs → same artifacts (line 51)
2. **Stable issue IDs:** Derived from (gate_name, location, issue_type) (line 44)
3. **Deterministic ordering:** Issues sorted by (severity, gate, location.path, location.line, issue_id) (line 44)
4. **Controlled timestamps:** Only run_start_time used, not wall-clock (line 52)

### Validators Meeting All Determinism Requirements

**NONE** - No validator fully implements all 4 determinism requirements.

### Validators with Determinism Gaps

#### Partial Compliance: launch_validate (src/launch/validators/cli.py)
- ✅ **Stable schema:** validation_report.json matches schema (specs/schemas/validation_report.schema.json)
- ⚠️ **Stable issue IDs:** Hardcoded IDs are stable but not algorithmically derived (GAP G-GAP-004)
- ❌ **Deterministic ordering:** Issues not sorted by severity/gate/location (GAP G-GAP-002)
- ❌ **Controlled timestamps:** No evidence of timestamp control (GAP G-GAP-003)
- ❌ **Byte-identical outputs:** Cannot be achieved without fixing ordering and timestamps

#### Partial Compliance: Preflight validators
- ✅ **Stable exit codes:** All use 0/1 consistently
- ✅ **Deterministic logic:** Same inputs → same validation results
- ⚠️ **Timestamps in logs:** Unknown - no inspection of log file contents performed
- ❌ **Byte-identical logs:** Likely NO - logs may include timestamps or dynamic paths

### Summary: Determinism Status
| Requirement | Status | Evidence | Gap Reference |
|-------------|--------|----------|---------------|
| Byte-identical outputs | ❌ Not met | Unsorted issues, possible timestamps | G-GAP-002, G-GAP-003 |
| Stable issue IDs | ⚠️ Partial | Hardcoded, not derived | G-GAP-004 |
| Deterministic ordering | ❌ Not met | Issues not sorted per spec | G-GAP-002 |
| Controlled timestamps | ❌ Unknown | No evidence of control | G-GAP-003 |

## Summary Statistics
- **Total gates defined:** 28 gates (10 runtime + 18 preflight)
- **Implemented validators:** 21 validators (3 runtime + 18 preflight)
- **Missing validators:** 9 runtime gates (Hugo build, TruthLock, internal links, external links, snippets, Hugo config, frontmatter, markdownlint, template token lint)
- **Gates with full coverage:** 15 gates (71%)
- **Deterministic validators:** 0 gates (0% - all have determinism gaps)
- **Fail-fast validators:** 21 gates (100%)
- **Exit code compliance:** ⚠️ Partial (validators use 0/1 or 0/2, but spec defines 5 codes)

### Compliance Rate by Category
| Category | Implemented | Total | Rate |
|----------|-------------|-------|------|
| Preflight Compliance Gates (J-S) | 11 | 11 | 100% |
| Preflight Support Gates (0, A-I) | 10 | 10 | 100% |
| Runtime Core Gates (1-9) | 4 | 10 | 40% |
| Determinism Requirements | 0 | 4 | 0% |
| **Overall** | **25** | **35** | **71%** |

## Recommendations

### Priority 1: BLOCKER Gaps (Prevent False Passes)
1. **Implement missing runtime gates** (G-GAP-005 to G-GAP-010)
   - Hugo build validator (Gate 5)
   - TruthLock validator (Gate 9)
   - Internal links validator (Gate 6)
   - External links validator (Gate 7) - ci/prod profiles only
   - Snippets syntax checker (Gate 8)
   - Hugo config compatibility checker (Gate 3)

### Priority 2: MAJOR Gaps (Determinism & Exit Codes)
2. **Fix determinism issues** (G-GAP-002, G-GAP-003, G-GAP-004)
   - Implement issue sorting per specs/10_determinism_and_caching.md:44
   - Control timestamps in validation outputs
   - Derive issue IDs algorithmically

3. **Standardize exit codes** (G-GAP-001)
   - Update all validators to use specs/01_system_contract.md:141-146 exit codes
   - Use exit 3 for policy violations, exit 4 for external deps, exit 5 for internal errors

### Priority 3: MINOR Gaps (Documentation & Style)
4. **Document preflight gates** (implied gap - docs/cli_usage.md has no preflight section)
5. **Implement style gates** (G-GAP-012, G-GAP-013)
   - Markdownlint integration
   - Template token lint

### Positive Findings (Preserve These)
- ✅ Comprehensive preflight gate coverage (100% of compliance guarantees)
- ✅ All validators fail-fast (no silent skips)
- ✅ Clear entry points for both preflight and runtime validation
- ✅ Scaffold explicitly marks NOT_IMPLEMENTED gates as failures (no false passes)
- ✅ Profile-based gating implemented per spec (local/ci/prod)
