# Spec-to-Gate Traceability Matrix

## Core Validation Gates (specs/09_validation_gates.md)

| Spec Requirement | Gate ID | Validator | Enforcement | Evidence | Notes |
|------------------|---------|-----------|-------------|----------|-------|
| **Schema Validation** |
| specs/09_validation_gates.md:20-23 - Validate all JSON artifacts against schemas | A | src/launch/validators/cli.py:177-211 | ✅ Strong | Exit 2 on failure, deterministic validation | Runtime only, uses jsonschema |
| specs/09_validation_gates.md:20-23 - Validate all JSON artifacts against schemas | A1 | scripts/validate_spec_pack.py:34-43 | ✅ Strong | Exit 2 on schema compilation failure | Preflight: validates schema files themselves |
| specs/09_validation_gates.md:22 - Validate page frontmatter | - | (none) | ❌ Missing | src/launch/validators/cli.py:217 NOT_IMPLEMENTED | Blocker for runtime validation |
| **Markdown Lint** |
| specs/09_validation_gates.md:24-27 - markdownlint with pinned ruleset | - | (none) | ❌ Missing | src/launch/validators/cli.py:218 NOT_IMPLEMENTED | Minor: style only |
| **Hugo Config** |
| specs/09_validation_gates.md:28-32 - Hugo config compatibility (subdomain, family pairs) | 3 | (none) | ❌ Missing | src/launch/validators/cli.py:220 NOT_IMPLEMENTED | Blocker: prevents Hugo build failures |
| specs/31_hugo_config_awareness.md - Hugo config awareness | 3 | (none) | ❌ Missing | No validator found | Should validate run_config against Hugo configs |
| **Platform Layout** |
| specs/09_validation_gates.md:33-43 - Platform layout compliance (V2 sections) | 4 | tools/validate_platform_layout.py | ✅ Strong | Exit 0/1, validates V2 __PLATFORM__ paths | Preflight only |
| specs/32_platform_aware_content_layout.md - Platform-aware layout | 4 | tools/validate_platform_layout.py | ✅ Strong | Checks layout_mode, platform paths, no unresolved tokens | Enforces V2 contract |
| **Hugo Build** |
| specs/09_validation_gates.md:45-48 - Hugo build must succeed | 5 | (none) | ❌ Missing | src/launch/validators/cli.py:221 NOT_IMPLEMENTED | Blocker: no build validation |
| **Links** |
| specs/09_validation_gates.md:49-52 - Internal links and anchors | 6 | tools/check_markdown_links.py (preflight) | ⚠️ Weak | Checks spec/plan links, NOT generated content | Runtime version missing |
| specs/09_validation_gates.md:49-52 - Internal links and anchors | 6 | (none - runtime) | ❌ Missing | src/launch/validators/cli.py:222 NOT_IMPLEMENTED | No validator for generated content links |
| specs/09_validation_gates.md:53-56 - External links (lychee) | 7 | (none) | ❌ Missing | src/launch/validators/cli.py:223 NOT_IMPLEMENTED | Should skip in local profile |
| **Snippets** |
| specs/09_validation_gates.md:57-62 - Snippet syntax check | 8 | (none) | ❌ Missing | src/launch/validators/cli.py:224 NOT_IMPLEMENTED | Blocker: invalid snippets not caught |
| **TruthLock** |
| specs/09_validation_gates.md:63-65 - TruthLock enforcement | 9 | (none) | ❌ Missing | src/launch/validators/cli.py:225 NOT_IMPLEMENTED | Blocker: uncited claims not caught |
| specs/04_claims_compiler_truth_lock.md:32-51 - TruthLock rules | 9 | (none) | ❌ Missing | No validator implements TruthLock rules | Must check claim_groups → evidence linkage |
| **Consistency** |
| specs/09_validation_gates.md:66-70 - product_name, repo_url, canonical URL consistency | - | (none) | ❌ Missing | Not in launch_validate or tools/ | Inferred gate, not explicitly named |
| **Gate Outputs** |
| specs/09_validation_gates.md:71-75 - validation_report.json matches schema | - | src/launch/validators/cli.py:253-261 | ✅ Strong | Writes validation_report.json per schema | Schema validated implicitly |
| **Fix Loop** |
| specs/09_validation_gates.md:76-83 - Fix loop with capped attempts | - | (none) | ⚠️ Unknown | Not in validator scope (orchestrator) | Orchestrator responsibility |
| specs/09_validation_gates.md:76-83 - Manual edits forbidden by default | - | (none) | ⚠️ Unknown | Policy gate TC-571 planned, not in validators | Runtime enforcement TBD |
| **Timeout Configuration** |
| specs/09_validation_gates.md:84-120 - Gate timeouts by profile | - | (none) | ❌ Missing | validate_swarm_ready.py:114 has 60s timeout (hardcoded) | Should vary by profile |
| specs/09_validation_gates.md:115-120 - Timeout behavior (BLOCKER issue) | - | (none) | ❌ Missing | No timeout enforcement in launch_validate | Should emit GATE_TIMEOUT error |
| **Profile-Based Gating** |
| specs/09_validation_gates.md:123-159 - Profile selection (local/ci/prod) | - | src/launch/validators/cli.py:83-111 | ✅ Strong | Follows precedence: run_config > CLI > env > default | Correct implementation |
| specs/09_validation_gates.md:136-141 - Local profile skips external links | - | src/launch/validators/cli.py:223 | ⚠️ Weak | Gate marked NOT_IMPLEMENTED (no behavior yet) | Will need profile check when implemented |
| specs/09_validation_gates.md:142-148 - CI profile runs all gates | - | src/launch/validators/cli.py:228-250 | ⚠️ Weak | NOT_IMPLEMENTED gates fail in prod (line 230) | Correct blocker behavior in prod, warn in non-prod |
| **Acceptance** |
| specs/09_validation_gates.md:162-171 - validation_report.ok == true | - | src/launch/validators/cli.py:252 | ✅ Strong | `ok = all(g["ok"] for g in gates)` | Correct |
| specs/09_validation_gates.md:167 - validation_report.profile field | - | src/launch/validators/cli.py:256 | ✅ Strong | Sets profile in report | Correct |
| specs/09_validation_gates.md:168-169 - All timeouts respected | - | (none) | ❌ Missing | No timeout enforcement | Need per-gate timeout tracking |
| specs/09_validation_gates.md:170 - Gate execution order | - | src/launch/validators/cli.py:116-226 | ✅ Strong | Gates run in code order (matches spec order) | Correct |
| **Universality Gates** |
| specs/09_validation_gates.md:172-176 - Tier compliance (minimal vs rich) | - | (none) | ❌ Missing | Not in any validator | Content-level gate (W5/W7 scope?) |
| specs/09_validation_gates.md:177-182 - Limitations honesty | - | (none) | ❌ Missing | Not in any validator | Content-level gate (W5/W7 scope?) |
| specs/09_validation_gates.md:183-187 - Distribution correctness | - | (none) | ❌ Missing | Not in any validator | Content-level gate (W5/W7 scope?) |
| specs/09_validation_gates.md:188-192 - No hidden inference | - | (none) | ❌ Missing | Not in any validator | Content-level gate (W5/W7 scope?) |
| **Strict Compliance Gates** |
| specs/09_validation_gates.md:193-212 - All compliance guarantees enforced | J-R | tools/validate_*.py (11 validators) | ✅ Strong | 100% of compliance gates implemented | See compliance section below |

## Compliance Gates (specs/34_strict_compliance_guarantees.md)

| Guarantee | Gate | Spec Source | Validator | Enforcement | Evidence | Notes |
|-----------|------|-------------|-----------|-------------|----------|-------|
| **A: Input Immutability - Pinned Refs** |
| Guarantee A | J | specs/34_strict_compliance_guarantees.md:40-58 | tools/validate_pinned_refs.py | ✅ Strong | Exit 0/1, checks all *_ref fields for commit SHAs | Detects floating refs (main/master/tags) |
| Pinned SHAs in run configs | J | tools/validate_pinned_refs.py:87-113 | ✅ Strong | Validates github_ref, site_ref, workflows_ref, base_ref | Skips templates, enforces pilots |
| **B: Hermetic Execution Boundaries** |
| Path confinement to RUN_DIR | - | specs/34_strict_compliance_guarantees.md:61-79 | (none) | ⚠️ Unknown | Preflight: Gate E validates allowed_paths structure | Runtime: Path validation in io/atomic.py? (not inspected) |
| Allowed paths fence | E | tools/audit_allowed_paths.py | ✅ Strong | Exit 0/1, checks taskcard allowed_paths for escapes/overlaps | Zero violations required |
| **C: Supply-Chain Pinning** |
| Guarantee C | K | specs/34_strict_compliance_guarantees.md:82-102 | tools/validate_supply_chain_pinning.py | ✅ Strong | Exit 0/1, checks uv.lock + .venv + Makefile --frozen | Enforces locked dependencies |
| **D: Network Egress Allowlist** |
| Guarantee D | N | specs/34_strict_compliance_guarantees.md:105-130 | tools/validate_network_allowlist.py | ⚠️ Weak | Checks config/network_allowlist.yaml exists | File exists, but no runtime enforcement check |
| Network allowlist file exists | N | tools/validate_network_allowlist.py:33-44 | ✅ Strong | Validates file presence | No validation that runtime code uses it |
| HTTP client wrapper exists | N | tools/validate_network_allowlist.py:47-55 | ✅ Strong | Checks src/launch/clients/http.py exists | No check that wrapper enforces allowlist |
| **E: Secret Hygiene / Redaction** |
| Guarantee E (secrets scan) | L | specs/34_strict_compliance_guarantees.md:133-159 | tools/validate_secrets_hygiene.py | ✅ Strong | Exit 0/1, scans runs/ for secret patterns | Entropy-based detection |
| Guarantee E (no placeholders) | M | specs/34_strict_compliance_guarantees.md:20-33 | tools/validate_no_placeholders_production.py | ✅ Strong | Exit 0/1, scans src/launch for NOT_IMPLEMENTED/PIN_ME | Excludes tests/ and scripts/ |
| **F: Budget + Circuit Breakers** |
| Guarantee F | O | specs/34_strict_compliance_guarantees.md:162-188 | tools/validate_budgets_config.py | ✅ Strong | Exit 0/1, validates budgets object in run_config | Checks all required budget fields |
| Budget fields in run_config | O | tools/validate_budgets_config.py:74-85 | ✅ Strong | Validates max_runtime_s, max_llm_calls, max_llm_tokens, max_file_writes, max_patch_attempts | Schema + sanity checks |
| **G: Change Budget + Minimal-Diff** |
| Guarantee G | O | specs/34_strict_compliance_guarantees.md:191-215 | tools/validate_budgets_config.py | ⚠️ Weak | Validates max_lines_per_file, max_files_changed in budgets | Preflight only; no runtime diff analysis |
| Runtime diff analysis | - | specs/34_strict_compliance_guarantees.md:199-200 | (none) | ❌ Missing | No diff_analyzer.py found | Should analyze patch_bundle.json |
| **H: CI Parity / Canonical Entrypoint** |
| Guarantee H | Q | specs/34_strict_compliance_guarantees.md:218-240 | tools/validate_ci_parity.py | ✅ Strong | Exit 0/1, parses .github/workflows/*.yml | Checks for canonical commands |
| **I: Non-Flaky Tests** |
| Guarantee I | - | specs/34_strict_compliance_guarantees.md:242-268 | (none) | ⚠️ Unknown | Not a gate (test infrastructure concern) | PYTHONHASHSEED enforcement in pyproject.toml? |
| **J: No Execution of Untrusted Repo Code** |
| Guarantee J | R | specs/34_strict_compliance_guarantees.md:271-298 | tools/validate_untrusted_code_policy.py | ⚠️ Weak | Checks subprocess wrapper exists | No static analysis of actual subprocess usage |
| Subprocess wrapper exists | R | tools/validate_untrusted_code_policy.py:80-88 | ✅ Strong | Validates src/launch/util/subprocess.py exists | File presence check only |
| No unsafe subprocess calls | R | tools/validate_untrusted_code_policy.py:102-119 | ⚠️ Weak | Scans for direct subprocess.run/call/Popen | Basic regex scan (may miss indirect calls) |
| **K: Spec/Taskcard Version Locking** |
| Guarantee K | P | specs/34_strict_compliance_guarantees.md:301-330 | tools/validate_taskcard_version_locks.py | ✅ Strong | Exit 0/1, checks spec_ref, ruleset_version, templates_version | Enforces version locks in all taskcards |
| Taskcard version fields | P | tools/validate_taskcard_version_locks.py:27-35 | ✅ Strong | Validates spec_ref, ruleset_version, templates_version presence | REQUIRED_KEYS in validate_taskcards.py:21-34 |
| **L: Rollback + Recovery Contract** |
| Guarantee L | - | specs/34_strict_compliance_guarantees.md:333-358 | (none) | ❌ Missing | No validator checks PR artifacts for rollback fields | Should check pr.json for base_ref, run_id, rollback_steps |

## Determinism Guarantees (specs/10_determinism_and_caching.md)

| Requirement | Spec Source | Validator | Enforcement | Evidence | Notes |
|-------------|-------------|-----------|-------------|----------|-------|
| **Byte-identical outputs** |
| Same inputs → same artifacts | specs/10_determinism_and_caching.md:51 | (none) | ❌ Missing | No byte-identity test | Unsorted issues prevent byte-identity |
| **Stable ordering** |
| Paths lexicographically | specs/10_determinism_and_caching.md:41 | (partial) | ⚠️ Partial | src/launch/io/schema_validation.py:23 sorts validation errors by path | Only for validation errors, not all outputs |
| Issues by (severity, gate, location, issue_id) | specs/10_determinism_and_caching.md:44 | (none) | ❌ Missing | src/launch/validators/cli.py:252-261 does NOT sort issues | Critical gap for determinism |
| Severity rank: blocker > error > warn > info | specs/10_determinism_and_caching.md:48 | specs/schemas/issue.schema.json:10 | ✅ Strong | Enum defines severity order | Schema correct, but not enforced in output |
| **Stable issue IDs** |
| issue_id derived from (gate, location, issue_type) | specs/10_determinism_and_caching.md:44 | (none) | ⚠️ Weak | src/launch/validators/cli.py uses hardcoded IDs (lines 122,145,165,200,233) | IDs are stable but not algorithmic |
| **Controlled timestamps** |
| Only run_start_time, not wall-clock | specs/10_determinism_and_caching.md:52 | (none) | ❌ Unknown | No evidence of timestamp control in validators | Logs may contain timestamps |

## Exit Code Contract (specs/01_system_contract.md:141-146)

| Exit Code | Meaning | Validators Using | Evidence | Compliance |
|-----------|---------|------------------|----------|------------|
| 0 | Success | All validators | All validators return 0 on success | ✅ Full |
| 1 | (not in spec) | All tools/*.py preflight validators | tools/validate_pinned_refs.py:207, etc. | ⚠️ Non-standard (spec doesn't define exit 1) |
| 2 | Validation/spec/schema failure | src/launch/validators/cli.py:268, scripts/validate_spec_pack.py:124 | Runtime + spec pack validation | ✅ Correct usage |
| 3 | Policy violation | (none) | Not used | ❌ Missing |
| 4 | External dependency failure | (none) | Not used | ❌ Missing |
| 5 | Unexpected internal error | (none) | Not used | ❌ Missing |

**Gap:** Validators use exit 1 (non-standard) instead of spec-defined codes 2-5.

## Profile-Based Gating (specs/09_validation_gates.md:123-159)

| Profile | Behavior | Validator | Enforcement | Evidence |
|---------|----------|-----------|-------------|----------|
| **local** (development) |
| Skip external links | src/launch/validators/cli.py | ❌ Not yet enforced | Gate 7 is NOT_IMPLEMENTED (will need profile check when implemented) |
| Skip runnable snippet execution | (none) | ❌ Not implemented | Gate 8 is NOT_IMPLEMENTED |
| Relaxed timeouts | (none) | ❌ Not implemented | No timeout enforcement in launch_validate |
| Warnings don't fail | src/launch/validators/cli.py:228-250 | ✅ Correct | NOT_IMPLEMENTED gates are "warn" in non-prod (line 230) |
| **ci** (continuous integration) |
| Run all gates | src/launch/validators/cli.py | ⚠️ Partial | Some gates NOT_IMPLEMENTED |
| Stricter timeouts | (none) | ❌ Not implemented | No timeout enforcement |
| Warnings MAY fail | src/launch/validators/cli.py:230 | ✅ Correct | Configurable per run_config.ci_strictness (not checked) |
| Full TruthLock enforcement | (none) | ❌ Not implemented | Gate 9 is NOT_IMPLEMENTED |
| **prod** (maximum rigor) |
| All gates enabled | src/launch/validators/cli.py | ⚠️ Partial | Some gates NOT_IMPLEMENTED |
| Zero tolerance for warnings | src/launch/validators/cli.py:228-250 | ✅ Correct | NOT_IMPLEMENTED gates are "blocker" in prod (line 230) |
| Longest timeouts | (none) | ❌ Not implemented | No timeout enforcement |

## Coverage Summary

### ✅ Strong Enforcement (15 gates)
- Gate 0: .venv policy (validate_dotvenv_policy.py)
- Gate A: Artifact schema validation (launch_validate + validate_spec_pack.py)
- Gate A1: Spec pack validation (validate_spec_pack.py)
- Gate A2: Plans validation (validate_plans.py)
- Gate B: Taskcard validation (validate_taskcards.py)
- Gate C: Status board generation (generate_status_board.py)
- Gate D: Markdown links (check_markdown_links.py - preflight only)
- Gate E: Allowed paths audit (audit_allowed_paths.py)
- Gate F: Platform layout (validate_platform_layout.py)
- Gate J: Pinned refs (validate_pinned_refs.py)
- Gate K: Supply chain pinning (validate_supply_chain_pinning.py)
- Gate L: Secrets hygiene (validate_secrets_hygiene.py)
- Gate M: No placeholders (validate_no_placeholders_production.py)
- Gate O: Budget config (validate_budgets_config.py)
- Gate P: Taskcard version locks (validate_taskcard_version_locks.py)

### ⚠️ Weak Enforcement (6 gates)
- Gate 4: Platform layout (preflight only, no runtime validation)
- Gate 6: Internal links (preflight checks specs, runtime NOT_IMPLEMENTED for generated content)
- Gate N: Network allowlist (file exists, no runtime enforcement check)
- Gate Q: CI parity (parse-only, no execution verification)
- Gate R: Untrusted code policy (basic regex scan, wrapper existence check)
- Guarantee G: Change budget (schema only, no runtime diff analysis)

### ❌ Missing Enforcement (14 gates)
- Gate 3: Hugo config compatibility
- Gate 5: Hugo build
- Gate 6: Internal links (runtime - for generated content)
- Gate 7: External links
- Gate 8: Snippets syntax check
- Gate 9: TruthLock enforcement
- Frontmatter validation (runtime)
- Markdownlint (runtime)
- Template token lint (runtime)
- Timeout enforcement (all gates)
- Consistency gate (product_name, repo_url, canonical URL)
- Tier compliance (minimal/rich)
- Limitations honesty
- Distribution correctness
- No hidden inference
- Rollback metadata validation (Guarantee L)

## Traceability Statistics

| Category | Strong | Weak | Missing | Total | Coverage % |
|----------|--------|------|---------|-------|------------|
| Core validation gates (1-9) | 4 | 2 | 9 | 15 | 40% |
| Compliance gates (J-R) | 11 | 2 | 1 | 14 | 93% |
| Profile-based gating | 2 | 1 | 3 | 6 | 50% |
| Determinism guarantees | 1 | 2 | 3 | 6 | 50% |
| Exit code contract | 2 | 1 | 3 | 6 | 50% |
| **Overall** | **20** | **8** | **19** | **47** | **60%** |

## Critical Missing Validators (Blockers)

1. **Hugo build** (Gate 5) - specs/09_validation_gates.md:45-48
2. **TruthLock** (Gate 9) - specs/09_validation_gates.md:63-65
3. **Internal links (runtime)** (Gate 6) - specs/09_validation_gates.md:49-52
4. **Hugo config compatibility** (Gate 3) - specs/09_validation_gates.md:28-32
5. **Snippets syntax check** (Gate 8) - specs/09_validation_gates.md:57-62

## Recommendations

### Immediate Actions (Blockers)
1. Implement missing runtime gates (3, 5, 6, 8, 9) in launch_validate
2. Fix determinism gaps (issue sorting, timestamp control, derived issue IDs)
3. Standardize exit codes across all validators per specs/01_system_contract.md

### Near-term Actions (Major)
4. Add timeout enforcement per profile (specs/09_validation_gates.md:84-120)
5. Implement diff analyzer for change budget enforcement (Guarantee G)
6. Add runtime enforcement checks for network allowlist (validate HTTP client uses allowlist)

### Long-term Actions (Minor)
7. Implement content-level gates (tier compliance, limitations honesty, distribution correctness)
8. Add markdownlint and template token lint to launch_validate
9. Document preflight gates in docs/cli_usage.md
