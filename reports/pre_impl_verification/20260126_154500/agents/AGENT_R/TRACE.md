# AGENT_R: Cross-File Requirements Traceability

**Purpose**: Map requirements that appear in multiple specification files to track consistency and identify conflicts.

**Format**: Each section lists a requirement concept, its primary source, all secondary references, and any conflicts or clarifications.

---

## Traceability Matrix

### T-001: Temperature Defaults to 0.0

**Primary Source**: specs/01_system_contract.md:39, 156

**Requirement ID**: REQ-CFG-006, REQ-DET-001

**All References**:
1. specs/01_system_contract.md:39 - "LLM provider params (temperature MUST default to 0.0)"
2. specs/01_system_contract.md:156 - "Temperature MUST default to 0.0."
3. specs/10_determinism_and_caching.md:5 - "temperature: 0.0"

**Status**: ✅ Consistent

**Notes**: Appears 3 times. All references agree. No conflicts.

---

### T-002: MCP Requirement (Non-Negotiable)

**Primary Source**: specs/00_overview.md:32-34

**Requirement ID**: REQ-SYS-009

**All References**:
1. specs/00_overview.md:33 - "All features MUST be exposed via MCP endpoints/tools (not only CLI)."
2. specs/01_system_contract.md:6 - "**MCP**: MUST expose MCP endpoints/tools for all features (not CLI-only)."
3. specs/14_mcp_endpoints.md:5 - "CLI may exist, but MCP is required for full feature parity."

**Status**: ✅ Consistent

**Notes**: Appears in 3 files. Spec 14 clarifies that CLI is optional but MCP is mandatory.

---

### T-003: Telemetry Requirement (Always-On)

**Primary Source**: specs/00_overview.md:36-38

**Requirement ID**: REQ-SYS-010, REQ-TEL-001, REQ-TEL-006, REQ-TEL-007

**All References**:
1. specs/00_overview.md:37 - "All run events and all LLM operations MUST be logged via a centralized local-telemetry HTTP API endpoint."
2. specs/01_system_contract.md:7 - "**Telemetry**: MUST use centralized local-telemetry via HTTP API for all run events and all LLM operations."
3. specs/01_system_contract.md:149 - "Telemetry MUST be treated as **required**, but transport failures MUST be handled safely"
4. specs/16_local_telemetry_api.md:13 - "1) **Always-on**: Telemetry emission is required for every run."
5. specs/16_local_telemetry_api.md:16 - "4) **Non-fatal transport**: Telemetry transport failures must not crash the run; the system MUST buffer and retry."
6. docs/architecture.md:29 - "If the telemetry service is temporarily unavailable, payloads must be buffered to `RUN_DIR/telemetry_outbox.jsonl` and retried."

**Status**: ✅ Consistent

**Notes**: Appears in 4 specs + 1 doc. All agree telemetry is required but transport failures are non-fatal. Buffer-and-retry strategy defined in specs/01 and docs/architecture.

---

### T-004: Commit Service Requirement (No Direct Git)

**Primary Source**: specs/00_overview.md:40-42

**Requirement ID**: REQ-SYS-011, REQ-SEC-003, REQ-WRK-025

**All References**:
1. specs/00_overview.md:41 - "All commits/PR actions against aspose.org MUST go through a centralized GitHub commit service"
2. specs/01_system_contract.md:8 - "**Commits**: MUST commit to aspose.org via a centralized GitHub commit service with configurable message/body templates."
3. specs/01_system_contract.md:64 - "Direct `git commit` from orchestrator is forbidden in production mode."
4. specs/17_github_commit_service.md:6 - "The orchestrator MUST NOT run `git commit`, `git push`, or open PRs directly in **production mode**."
5. specs/21_worker_contracts.md:268 - "MUST call the GitHub commit service (`specs/17_github_commit_service.md`) in production mode."

**Status**: ✅ Consistent

**Notes**: 5 references. All agree. Production mode uses commit service. Spec 17 is authoritative for commit service contract.

---

### T-005: Allowed Paths Enforcement

**Primary Source**: specs/01_system_contract.md:60-62

**Requirement ID**: REQ-SEC-001, REQ-SEC-002, REQ-PAT-002, REQ-PAT-003, REQ-STR-008, REQ-CMP-003

**All References**:
1. specs/01_system_contract.md:61 - "The system MUST refuse to edit outside `run_config.allowed_paths`."
2. specs/01_system_contract.md:62 - "Any attempt to patch outside allowed_paths MUST fail the run with a blocker."
3. specs/08_patch_engine.md:37 - "Patch engine must refuse to write outside allowed_paths in run config."
4. specs/18_site_repo_layout.md:105 - "A run must declare allowed_paths in run_config."
5. specs/21_worker_contracts.md:201-202 - "MUST ensure only allowed_paths are changed: if a patch touches an out-of-scope path, open blocker `AllowedPathsViolation`"
6. specs/29_project_repo_structure.md:136 - "All writes MUST be refused if outside `run_config.allowed_paths`."
7. specs/34_strict_compliance_guarantees.md:63 - "All file operations MUST be confined to `RUN_DIR` and MUST NOT escape via path traversal"
8. specs/34_strict_compliance_guarantees.md:73 - "Any attempt to write outside `RUN_DIR` or `run_config.allowed_paths` MUST raise BLOCKER error code `POLICY_PATH_ESCAPE`"

**Status**: ✅ Consistent

**Notes**: 8 references across 6 specs. All agree. Spec 34 (Guarantee B) adds path traversal protections. Error code defined: POLICY_PATH_ESCAPE.

---

### T-006: Virtual Environment Policy (.venv Only)

**Primary Source**: specs/00_environment_policy.md:14-18

**Requirement ID**: REQ-ENV-001 to REQ-ENV-008

**All References**:
1. specs/00_environment_policy.md:14 - "All Python work in this repository MUST use exactly one virtual environment: `.venv/`"
2. specs/00_environment_policy.md:26 - "**FORBIDDEN**: Using global/system Python"
3. specs/00_environment_policy.md:27-35 - "**FORBIDDEN**: Creating alternate virtual environments"
4. README.md:53 - "This repository enforces a **strict `.venv` policy**"
5. README.md:60 - "All developers, agents, and CI must use `.venv` explicitly."
6. README.md:115-119 - "**ALL agents must**: - Verify they are running from `.venv` before starting work... - Never create alternate virtual environments... - Document `.venv` usage in all reports"

**Status**: ✅ Consistent

**Notes**: Appears in spec 00 (binding policy) and README (workflow). Gate enforcement via tools/validate_dotvenv_policy.py.

---

### T-007: Claim Stability (sha256-based IDs)

**Primary Source**: specs/04_claims_compiler_truth_lock.md:12

**Requirement ID**: REQ-ING-003, REQ-CLM-002, REQ-WRK-011

**All References**:
1. specs/04_claims_compiler_truth_lock.md:12 - "claim_id must be stable across runs"
2. specs/02_repo_ingestion.md:144 - "EvidenceMap claim_id must be stable (see `04_claims_compiler_truth_lock.md`)."
3. specs/21_worker_contracts.md:100-101 - "Claim IDs MUST be stable: `claim_id = sha256(normalized_claim_text + evidence_anchor + ruleset_version)`"

**Status**: ✅ Consistent

**Notes**: Spec 04 is primary authority. Spec 21 defines exact algorithm. Spec 02 references spec 04.

---

### T-008: Worker Idempotence

**Primary Source**: specs/21_worker_contracts.md:16

**Requirement ID**: REQ-WRK-003

**All References**:
1. specs/21_worker_contracts.md:16 - "Workers MUST be idempotent: re-running with the same inputs MUST reproduce the same outputs."
2. specs/21_worker_contracts.md (W1-W9 sections) - Each worker section restates idempotence requirement
3. specs/08_patch_engine.md:26 - "Patch apply must be idempotent"

**Status**: ✅ Consistent

**Notes**: Global requirement + per-worker reinforcement. Patch engine idempotence is specialized case.

---

### T-009: Manual Edits Policy (Emergency Only)

**Primary Source**: specs/01_system_contract.md:69-75

**Requirement ID**: REQ-SEC-005 to REQ-SEC-008, REQ-VAL-007, REQ-VAL-008

**All References**:
1. specs/01_system_contract.md:70 - "By default, `run_config.allow_manual_edits` MUST be **false** (or omitted)."
2. specs/01_system_contract.md:72-74 - "If set to **true**, the system MAY accept manual edits **only** if: - every manually-edited file is explicitly listed in the orchestrator master review with rationale..."
3. specs/09_validation_gates.md:80-82 - "**Manual content edits are forbidden by default**. If `run_config.allow_manual_edits=false` (default): any changed file must have a patch/evidence record... If `run_config.allow_manual_edits=true` (emergency only): validator must set `validation_report.manual_edits=true`..."
4. plans/policies/no_manual_content_edits.md:4 - "Agents must not manually edit content files to make reviews pass. All content changes must be produced by the pipeline stages (W4–W8) and be traceable to evidence."
5. plans/policies/no_manual_content_edits.md:12-17 - "For each modified content file, the run must produce: 1. A patch entry in `patch_bundle.json`... 2. Claim traceability..."
6. plans/policies/no_manual_content_edits.md:19-27 - "The validation gates tool (TC-570) must include a policy gate that: 1. Reads `run_config.allow_manual_edits`... 2. If false (default): scan git diff... 3. If true: ensure `validation_report.manual_edits=true`..."

**Status**: ✅ Consistent

**Notes**: 3 specs + 1 policy doc. All agree. Default=false. Emergency mode requires explicit listing and rationale. Policy gate defined in plans/policies.

---

### T-010: Hugo Build Success

**Primary Source**: specs/09_validation_gates.md:46-47

**Requirement ID**: REQ-VAL-004

**All References**:
1. specs/09_validation_gates.md:47 - "build must succeed."
2. specs/19_toolchain_and_ci.md:122 - "build must succeed"
3. specs/19_toolchain_and_ci.md:123 - "build output must be discarded after validation (do not commit generated files)"

**Status**: ✅ Consistent

**Notes**: Gate 5 defined in spec 09. Spec 19 adds implementation detail: discard output after validation.

---

### T-011: Determinism Requirements (Byte-Identical Artifacts)

**Primary Source**: specs/10_determinism_and_caching.md:51-52

**Requirement ID**: REQ-DET-009

**All References**:
1. specs/10_determinism_and_caching.md:51 - "Repeat run with the same inputs produces **byte-identical** artifacts (PagePlan, PatchBundle, drafts, reports)."
2. specs/10_determinism_and_caching.md:52 - "The only allowed run-to-run variance is inside the local event stream (`events.ndjson`) where `ts`/`event_id` values differ."
3. specs/00_overview.md:22 - "Same inputs -> same plan -> near-identical diffs."
4. specs/02_repo_ingestion.md:142 - "Same `github_ref` must produce identical RepoInventory and equivalent ProductFacts."

**Status**: ⚠️ Minor inconsistency

**Notes**:
- Spec 10 says "byte-identical"
- Spec 00 says "near-identical diffs" (vaguer)
- Gap R-GAP-007 logged

**Reconciliation**: Treat spec 10 as authoritative (more precise). "Near-identical" in spec 00 is clarified by spec 10.

---

### T-012: Schema Validation (All Artifacts)

**Primary Source**: specs/01_system_contract.md:57

**Requirement ID**: REQ-ART-013, REQ-VAL-001, REQ-WRK-004

**All References**:
1. specs/01_system_contract.md:57 - "All JSON outputs MUST validate. Unknown keys are forbidden."
2. specs/09_validation_gates.md:21 - "Validate all JSON artifacts against schemas/."
3. specs/21_worker_contracts.md:17 - "Every JSON artifact output MUST validate against its schema under `specs/schemas/`."
4. specs/19_toolchain_and_ci.md:84 - "validate all JSON artifacts against `specs/schemas/*.schema.json`"

**Status**: ✅ Consistent

**Notes**: 4 references. All agree. Gate 1 (schema validation) is mandatory.

---

### T-013: Artifact Ordering (Deterministic Sorting)

**Primary Source**: specs/10_determinism_and_caching.md:40-46

**Requirement ID**: REQ-DET-007, REQ-WRK-006

**All References**:
1. specs/10_determinism_and_caching.md:40-46 - "Sort all lists deterministically: - paths lexicographically - sections in config order - pages by `(section_order, output_path)` - issues by `(severity_rank, gate, location.path, location.line, issue_id)` - claims by `claim_id` - snippets by `(language, tag, snippet_id)`"
2. specs/10_determinism_and_caching.md:48 - "**Severity rank (binding):** `blocker` > `error` > `warn` > `info`."
3. specs/01_system_contract.md:157 - "Artifact ordering MUST follow `specs/10_determinism_and_caching.md`."
4. specs/02_repo_ingestion.md:143 - "Sorting must be stable (paths, lists)."
5. specs/21_worker_contracts.md:19 - "All ordering MUST follow `specs/10_determinism_and_caching.md`."

**Status**: ✅ Consistent

**Notes**: Spec 10 is definitive ordering spec. Specs 01, 02, 21 all reference it.

---

### T-014: RUN_DIR Isolation

**Primary Source**: specs/29_project_repo_structure.md:130

**Requirement ID**: REQ-STR-005, REQ-SEC-010

**All References**:
1. specs/29_project_repo_structure.md:130 - "**Isolation**: workers MUST NOT read or write outside `RUN_DIR` (except for reading installed tools and env vars)."
2. specs/34_strict_compliance_guarantees.md:63 - "All file operations MUST be confined to `RUN_DIR` and MUST NOT escape via path traversal (`..`), absolute paths, or symlink resolution."

**Status**: ✅ Consistent

**Notes**: Spec 29 defines project structure. Spec 34 (Guarantee B) adds security enforcement.

---

### T-015: Lockfile Requirement (Supply Chain Pinning)

**Primary Source**: specs/34_strict_compliance_guarantees.md:84

**Requirement ID**: REQ-SEC-011, REQ-STR-002, REQ-CMP-004, REQ-CMP-005

**All References**:
1. specs/34_strict_compliance_guarantees.md:84 - "All dependencies MUST be installed from a lock file (`uv.lock` or `poetry.lock`). No ad-hoc `pip install` without locking."
2. specs/29_project_repo_structure.md:58 - "Production/CI runs MUST use exactly one lock strategy: `uv` (`uv.lock`) **or** Poetry (`poetry.lock`)."
3. specs/34_strict_compliance_guarantees.md:94-95 - "If `.venv` does not exist, fail with error code `ENV_MISSING_VENV`. If `uv.lock` (or `poetry.lock`) does not exist, fail with error code `ENV_MISSING_LOCKFILE`"

**Status**: ✅ Consistent

**Notes**: Guarantee C (spec 34). Error codes defined. Spec 29 clarifies "one strategy" (not both).

---

### T-016: Network Allowlist Requirement

**Primary Source**: specs/34_strict_compliance_guarantees.md:107

**Requirement ID**: REQ-SEC-012, REQ-CMP-006, REQ-CMP-007, REQ-CMP-008

**All References**:
1. specs/34_strict_compliance_guarantees.md:107 - "All network requests MUST be to explicitly allow-listed hosts."
2. specs/34_strict_compliance_guarantees.md:116 - "**Allowlist file**: `config/network_allowlist.yaml`"
3. specs/34_strict_compliance_guarantees.md:122-124 - "If allowlist missing in prod profile, fail with error code `POLICY_NETWORK_ALLOWLIST_MISSING`. If `run_config` contains non-allowlisted host, fail with error code `POLICY_NETWORK_UNAUTHORIZED_HOST`. If runtime HTTP request attempts non-allowlisted host, fail with error code `NETWORK_BLOCKED`"

**Status**: ✅ Consistent

**Notes**: Guarantee D (spec 34). Error codes defined. Gate N will enforce.

---

### T-017: Secrets Redaction

**Primary Source**: specs/34_strict_compliance_guarantees.md:135

**Requirement ID**: REQ-SEC-013, REQ-CMP-009, REQ-CMP-010

**All References**:
1. specs/34_strict_compliance_guarantees.md:135 - "Secrets MUST NEVER appear in logs, artifacts, or reports. All secret-like patterns MUST be redacted."
2. specs/34_strict_compliance_guarantees.md:152-153 - "If secrets scan detects leakage, fail with error code `SECURITY_SECRET_LEAKED`. Logs MUST show `***REDACTED***` instead of actual secret values"

**Status**: ✅ Consistent

**Notes**: Guarantee E (spec 34). Gate L will enforce. Redaction pattern defined.

---

### T-018: Budgets & Circuit Breakers

**Primary Source**: specs/34_strict_compliance_guarantees.md:164

**Requirement ID**: REQ-CMP-011, REQ-CMP-012, REQ-CMP-013

**All References**:
1. specs/34_strict_compliance_guarantees.md:164 - "All runs MUST have explicit budgets for runtime, retries, LLM calls, tokens, and file churn."
2. specs/34_strict_compliance_guarantees.md:172-177 - "**Required budget fields** (in `run_config.budgets`): - `max_runtime_s`: Maximum wall-clock time... - `max_llm_calls`: Maximum LLM API calls... - `max_llm_tokens`: Maximum total tokens... - `max_file_writes`: Maximum files written... - `max_patch_attempts`: Maximum patch bundle retries"
3. specs/34_strict_compliance_guarantees.md:180-181 - "If budget missing in prod profile, fail with error code `POLICY_BUDGET_MISSING`. If budget exceeded during run, fail with error code `BUDGET_EXCEEDED_{BUDGET_TYPE}`"

**Status**: ✅ Consistent

**Notes**: Guarantee F (spec 34). Gate O will enforce. Error codes defined.

---

### T-019: Change Budget (Minimal-Diff Discipline)

**Primary Source**: specs/34_strict_compliance_guarantees.md:193

**Requirement ID**: REQ-CMP-014, REQ-CMP-015, REQ-CMP-016

**All References**:
1. specs/34_strict_compliance_guarantees.md:193 - "Runs MUST NOT produce excessive diffs or formatting-only mass rewrites. Patch bundles MUST respect change budgets."
2. specs/34_strict_compliance_guarantees.md:202-204 - "**Change budget policy** (binding): - Maximum lines changed per file: 500 (configurable in `run_config.budgets.max_lines_per_file`) - Maximum files changed per run: 100 (configurable in `run_config.budgets.max_files_changed`)"
3. specs/34_strict_compliance_guarantees.md:208-209 - "If patch bundle exceeds change budget, fail with error code `POLICY_CHANGE_BUDGET_EXCEEDED`. If >80% of diff is formatting-only, emit warning (blocker in prod profile)"

**Status**: ✅ Consistent

**Notes**: Guarantee G (spec 34). Gap R-GAP-006 logged (thresholds lack rationale). Error code defined.

---

### T-020: CI Parity (Canonical Commands)

**Primary Source**: specs/34_strict_compliance_guarantees.md:220

**Requirement ID**: REQ-TCI-012, REQ-TCI-014, REQ-CMP-017

**All References**:
1. specs/34_strict_compliance_guarantees.md:220 - "CI MUST use the same commands as local development. No CI-specific scripts or workarounds."
2. specs/34_strict_compliance_guarantees.md:228-232 - "**Canonical commands**: - Install: `make install-uv` (deterministic) or `make install` (fallback) - Preflight: `python tools/validate_swarm_ready.py` - Tests: `pytest` - Validation: `launch_validate --run_dir <path> --profile ci`"
3. specs/34_strict_compliance_guarantees.md:235 - "If CI workflow does not reference canonical commands, fail Gate Q with error code `POLICY_CI_PARITY_VIOLATION`"
4. specs/19_toolchain_and_ci.md:77 - "These commands are canonical. The implementation can wrap them, but the underlying behavior must match."

**Status**: ✅ Consistent

**Notes**: Guarantee H (spec 34). Spec 19 reinforces. Gate Q will enforce.

---

### T-021: Untrusted Code Execution Prohibition

**Primary Source**: specs/34_strict_compliance_guarantees.md:273

**Requirement ID**: REQ-SEC-014, REQ-CMP-019

**All References**:
1. specs/34_strict_compliance_guarantees.md:273 - "Ingested repository code MUST be parse-only. No subprocess execution of scripts from `RUN_DIR/work/repo/`."
2. specs/34_strict_compliance_guarantees.md:292 - "If subprocess execution attempted from ingested repo, fail with error code `SECURITY_UNTRUSTED_EXECUTION`"
3. specs/27_universal_repo_handling.md:49 - "Snippets MAY reference binary paths but MUST NOT embed content"

**Status**: ✅ Consistent

**Notes**: Guarantee J (spec 34). Gate R will enforce. Parse-only policy.

---

### T-022: Version Locking (Specs/Rulesets/Templates)

**Primary Source**: specs/34_strict_compliance_guarantees.md:304

**Requirement ID**: REQ-CMP-020, REQ-CMP-021

**All References**:
1. specs/34_strict_compliance_guarantees.md:304 - "All taskcards and run configs MUST specify version locks for specs, rulesets, and templates."
2. specs/34_strict_compliance_guarantees.md:313-320 - "**Required fields**: - Taskcards: `spec_ref` (commit SHA of spec pack), `ruleset_version`, `templates_version` - Run configs: `ruleset_version`, `templates_version` **Canonical values**: - `ruleset_version: \"ruleset.v1\"` - `templates_version: \"templates.v1\"` - `spec_ref: \"<commit_sha>\"`"
3. specs/34_strict_compliance_guarantees.md:323-324 - "If taskcard missing version lock fields, fail Gate B with error code `TASKCARD_MISSING_VERSION_LOCK`. If run config missing version locks, fail with error code `CONFIG_MISSING_VERSION_LOCK`"
4. specs/01_system_contract.md:11-13 - "Every run MUST pin `ruleset_version` and `templates_version`. Schema versions MUST be explicit in every artifact (`schema_version` fields). Any behavior change MUST be recorded by bumping either the ruleset version, templates version, or schema version (no silent drift)."
5. specs/templates/README.md:55 - "`run_config.templates_version` is a required input for determinism."

**Status**: ✅ Consistent

**Notes**: Guarantee K (spec 34). Spec 01 defines version discipline. Gate B and Gate P will enforce.

---

### T-023: Rollback Metadata (PR Contract)

**Primary Source**: specs/34_strict_compliance_guarantees.md:336

**Requirement ID**: REQ-CMP-022, REQ-CMP-023

**All References**:
1. specs/34_strict_compliance_guarantees.md:336 - "All PR artifacts MUST include rollback steps, base ref, and run_id linkage for recovery."
2. specs/34_strict_compliance_guarantees.md:344-348 - "**Required rollback fields** (in `RUN_DIR/artifacts/pr.json`): - `base_ref`: The commit SHA of the site repo before changes - `run_id`: The run that produced this PR - `rollback_steps`: List of commands to revert changes - `affected_paths`: List of all modified/created files"
3. specs/34_strict_compliance_guarantees.md:351 - "If PR artifacts missing rollback metadata in prod profile, fail with error code `PR_MISSING_ROLLBACK_METADATA`"

**Status**: ✅ Consistent

**Notes**: Guarantee L (spec 34). PR schema needs update (spec 12). Error code defined.

---

### T-024: Toolchain Lock File

**Primary Source**: specs/19_toolchain_and_ci.md:13-17

**Requirement ID**: REQ-TCI-001, REQ-TCI-002, REQ-TCI-003

**All References**:
1. specs/19_toolchain_and_ci.md:13 - "The repo MUST include a lock file checked into version control: - config/toolchain.lock.yaml"
2. specs/19_toolchain_and_ci.md:17 - "The orchestrator and validators MUST refuse to run in production mode if this file is missing."
3. specs/19_toolchain_and_ci.md:25 - "The validator MUST fail fast (prod + CI profiles) if any required version fields are still `PIN_ME`."

**Status**: ✅ Consistent

**Notes**: Binding file: config/toolchain.lock.yaml. PIN_ME sentinel for unpinned versions.

---

### T-025: Frontmatter Contract Discovery

**Primary Source**: specs/18_site_repo_layout.md:110

**Requirement ID**: REQ-HUG-001

**All References**:
1. specs/18_site_repo_layout.md:110 - "FrontmatterContract must be discovered per: ..."
2. specs/examples/frontmatter_models.md:29-30 - "required_keys = intersection of keys across the sampled set... optional_keys = union(keys) - required_keys"
3. specs/examples/frontmatter_models.md:39-47 - "## How writers must use it - includes all required_keys for that section... Missing required keys is a blocker."
4. specs/21_worker_contracts.md:76-78 - "FrontmatterContract discovery (binding): MUST follow `specs/examples/frontmatter_models.md` deterministic discovery algorithm. Sampling MUST be deterministic..."

**Status**: ⚠️ Minor gap

**Notes**: Spec 18 references frontmatter discovery. Examples/frontmatter_models.md defines algorithm. Spec 21 requires deterministic sampling. Gap R-GAP-010 logged (sampling not fully deterministic).

---

### T-026: Event Emission (Workers)

**Primary Source**: specs/21_worker_contracts.md:35-39

**Requirement ID**: REQ-WRK-007, REQ-WRK-008

**All References**:
1. specs/21_worker_contracts.md:35-36 - "Each worker execution MUST emit: - `WORK_ITEM_STARTED` - `WORK_ITEM_FINISHED` or `WORK_ITEM_FAILED`"
2. specs/21_worker_contracts.md:38-39 - "Each artifact write MUST emit: - `ARTIFACT_WRITTEN` with `{ name, path, sha256, schema_id }`"
3. specs/11_state_and_events.md:69-70 - "`trace_id` (required), `span_id` (required)"

**Status**: ✅ Consistent

**Notes**: Spec 21 defines worker event contract. Spec 11 defines event schema fields.

---

### T-027: Completed WorkItems Not Re-Run

**Primary Source**: specs/state-management.md:69

**Requirement ID**: REQ-CRD-003

**All References**:
1. specs/state-management.md:69 - "Completed WorkItems MUST NOT be re-run unless: - explicitly forced - invalidated by upstream artifact changes"
2. specs/reference/system-requirements.md:459 - "Completed work items MUST NOT be re-run unless explicitly forced or invalidated by upstream artifact changes."

**Status**: ✅ Consistent

**Notes**: Appears in binding spec (state-management.md) and reference doc. Agrees.

---

### T-028: LangGraph Orchestration Requirement

**Primary Source**: specs/25_frameworks_and_dependencies.md:30

**Requirement ID**: REQ-CRD-004, REQ-CRD-005

**All References**:
1. specs/25_frameworks_and_dependencies.md:30 - "**Rule:** LangChain must not be used as the orchestrator. LangGraph owns orchestration."
2. specs/reference/system-requirements.md:487 - "The orchestrator MUST be implemented using **LangGraph** (LangChain is allowed for prompt composition, but MUST NOT own orchestration)."

**Status**: ✅ Consistent

**Notes**: LangGraph required for orchestration. LangChain allowed for prompts only.

---

## Summary Statistics

- **Total cross-file mappings**: 28
- **Consistent mappings**: 26 (92.9%)
- **Mappings with minor gaps**: 2 (7.1%)
- **Conflicting mappings**: 0 (0%)

---

## Conflict Resolution

### Minor Inconsistency: T-011 (Determinism)

**Issue**: Spec 00 says "near-identical" vs Spec 10 says "byte-identical"

**Resolution**: Spec 10 is authoritative (more precise definition). "Near-identical" in spec 00 is clarified by spec 10 to mean "byte-identical artifacts, timestamp variance in events.ndjson only".

**Action**: None required. Gap R-GAP-007 logged for future clarification.

---

### Minor Gap: T-025 (Frontmatter Sampling)

**Issue**: Sampling algorithm exists but lacks full determinism specification

**Resolution**: Gap R-GAP-010 logged. Proposed fix: Add sample size + file selection order to examples/frontmatter_models.md.

**Action**: Resolve gap before W1 (RepoScout) implementation.

---

## Recommendations

1. **Use this trace map during implementation**: When implementing a requirement, check this file to find all related references.

2. **Update trace map if specs change**: If specs are modified during development, update affected trace entries.

3. **Resolve gaps before final review**: Address R-GAP-007 and R-GAP-010 to eliminate minor inconsistencies.

4. **Validate schema references**: All requirements referencing schemas (e.g., T-012) should be tested against actual schema files.

---

**End of Traceability Report**
