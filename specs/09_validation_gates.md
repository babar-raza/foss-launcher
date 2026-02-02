# Validation Gates (Stop the line)

## Purpose
Define quality gates that MUST pass before a run can be released, including timeout behavior, profile-based gating, and gate execution order.

## Dependencies
- [specs/01_system_contract.md](01_system_contract.md) - Error handling and exit codes
- [specs/04_claims_compiler_truth_lock.md](04_claims_compiler_truth_lock.md) - TruthLock rules
- [specs/18_site_repo_layout.md](18_site_repo_layout.md) - Content root contracts
- [specs/31_hugo_config_awareness.md](31_hugo_config_awareness.md) - Hugo config validation
- [specs/34_strict_compliance_guarantees.md](34_strict_compliance_guarantees.md) - Binding compliance guarantees (A-L)
- [specs/schemas/validation_report.schema.json](schemas/validation_report.schema.json) - Validation report schema
- [specs/schemas/issue.schema.json](schemas/issue.schema.json) - Issue schema

---

# Validation Gates (Stop the line)

## Gates

### Gate 1: Schema Validation

**Purpose**: Validate all JSON artifacts validate against their schemas

**Inputs**:
- All `*.json` files under `RUN_DIR/artifacts/`
- All schemas under `specs/schemas/`
- All page frontmatter in `*.md` files under `RUN_DIR/work/site/`

**Validation Rules**:
1. All JSON artifacts MUST validate against their respective schemas
2. Schema validation MUST use JSON Schema Draft 2020-12
3. All page frontmatter MUST be valid YAML
4. If `frontmatter_contract.json` exists, all frontmatter MUST validate against it

**Error Codes**:
- `GATE_SCHEMA_VALIDATION_FAILED`: JSON artifact failed schema validation
- `GATE_FRONTMATTER_INVALID_YAML`: Frontmatter is not valid YAML
- `GATE_FRONTMATTER_CONTRACT_VIOLATION`: Frontmatter violates contract

**Timeout** (per profile):
- local: 30s per artifact
- ci: 60s per artifact
- prod: 60s per artifact

**Acceptance Criteria**:
- Gate passes if all artifacts pass schema validation
- Gate fails if any artifact violates its schema
- Issues array populated with specific file + validation error

---

### Gate 2: Markdown Lint and Frontmatter Validation

**Purpose**: Validate markdown quality and frontmatter compliance

**Inputs**:
- All `*.md` files under `RUN_DIR/work/site/`
- `RUN_DIR/artifacts/frontmatter_contract.json` (from W1 RepoScout)
- markdownlint ruleset (pinned version)

**Validation Rules**:
1. All markdown files MUST pass markdownlint with pinned ruleset
2. No new lint errors allowed (compared to baseline if exists)
3. All required frontmatter fields MUST be present (per frontmatter_contract)
4. All frontmatter field types MUST match contract

**Error Codes**:
- `GATE_MARKDOWN_LINT_ERROR`: Markdown lint rule violation
- `GATE_FRONTMATTER_MISSING`: File missing frontmatter
- `GATE_FRONTMATTER_REQUIRED_FIELD_MISSING`: Required field absent
- `GATE_FRONTMATTER_TYPE_MISMATCH`: Field type doesn't match contract

**Timeout** (per profile):
- local: 60s
- ci: 120s
- prod: 120s

**Acceptance Criteria**:
- Gate passes if all files pass markdown lint and frontmatter validation
- Gate fails if any file has lint errors or frontmatter violations
- Issues array populated with specific file:line violations

---

### Gate 3: Hugo Config Compatibility

**Purpose**: Validate Hugo config coverage for planned content

**Inputs**:
- `RUN_DIR/artifacts/page_plan.json` (from W4 IAPlanner)
- `RUN_DIR/artifacts/site_context.json` (from W1 RepoScout)
- Hugo config files from site repo

**Validation Rules**:
1. All planned `(subdomain, family)` pairs MUST be enabled by Hugo configs
2. Every planned `output_path` MUST match content root contract
3. Hugo config MUST exist for all required sections
4. Content roots MUST match `site_layout.subdomain_roots` from run_config

**Error Codes**:
- `GATE_HUGO_CONFIG_MISSING`: Hugo config missing for section
- `GATE_HUGO_CONFIG_PATH_MISMATCH`: Output path doesn't match contract
- `GATE_HUGO_CONFIG_SUBDOMAIN_NOT_ENABLED`: Subdomain not enabled in config

**Timeout** (per profile):
- local: 10s
- ci: 20s
- prod: 20s

**Acceptance Criteria**:
- Gate passes if all planned content is covered by Hugo config
- Gate fails (BLOCKER) if any section lacks config coverage
- Issues array populated with specific config gaps

### REQ-HUGO-FP-001: Hugo Config Fingerprinting Algorithm

**Purpose:** Deterministic fingerprint for Hugo configuration files

**Algorithm:**
1. Load hugo.toml or config.toml (whichever exists, prefer hugo.toml if both)
2. Canonicalize:
   - Sort all keys lexicographically (including nested keys)
   - Normalize booleans (true/false lowercase)
   - Strip comments (lines starting with #)
   - Normalize whitespace (single space after colons)
3. Compute SHA-256 hash of canonical form → **hugo_config_fingerprint**
4. Store in site_context.json field: `hugo_config_fingerprint` (string, 64-char hex)
5. Gate 3 validates fingerprint matches expected value from run_config

**Determinism:** Guaranteed (canonicalization is deterministic, SHA-256 is deterministic)

**Error Cases:**
- No hugo.toml or config.toml found → ERROR: HUGO_CONFIG_MISSING
- Multiple config files with conflicting values → ERROR: HUGO_CONFIG_AMBIGUOUS

**Example:**
```json
{
  "hugo_config_fingerprint": "b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7q8r9s0t1u2v3w4x5y6z7a8b9c0d1e2f3g4"
}
```

---

### Gate 4: Platform Layout Compliance

**Purpose**: Validate V2 platform-aware content layout compliance

**Inputs**:
- `RUN_DIR/artifacts/page_plan.json` (from W4 IAPlanner)
- `RUN_DIR/artifacts/patch_bundle.json` (from W6 LinkerAndPatcher)
- `run_config.layout_mode` and `run_config.target_platform`
- Taskcard `allowed_paths` from run_config

**Validation Rules**:
1. When `layout_mode=v2` for a section:
   - Non-blog sections MUST contain `/{locale}/{platform}/` in output paths
   - Blog section MUST contain `/{platform}/` at correct depth
   - Products section MUST use `/{locale}/{platform}/` (NOT `/{platform}/` alone)
2. All planned writes MUST be within taskcard `allowed_paths`
3. `allowed_paths` MUST include platform-level roots for V2 sections
4. Generated content MUST NOT contain unresolved `__PLATFORM__` tokens
5. Resolved `layout_mode` per section MUST be consistent across artifacts

**Error Codes**:
- `GATE_PLATFORM_LAYOUT_MISSING_SEGMENT`: Required platform segment missing
- `GATE_PLATFORM_TOKEN_UNRESOLVED`: Unresolved `__PLATFORM__` token found
- `GATE_PLATFORM_PATH_NOT_ALLOWED`: Path not in allowed_paths
- `GATE_PLATFORM_INCONSISTENT_MODE`: layout_mode inconsistent across artifacts

**Timeout** (per profile):
- local: 30s
- ci: 60s
- prod: 60s

**Acceptance Criteria**:
- Gate passes if all V2 paths comply with platform layout requirements
- Gate fails (BLOCKER) if any path violates layout rules
- No acceptable warnings (all violations are blockers)

---

### Gate 5: Hugo Build

**Purpose**: Validate Hugo site builds successfully in production mode

**Inputs**:
- `RUN_DIR/work/site/` (all generated content)
- Hugo config files from site repo
- `run_config.validation_profile`

**Validation Rules**:
1. Hugo build MUST succeed in production mode
2. Build MUST complete without errors
3. Build warnings MAY be allowed (profile-dependent)
4. Build MUST produce output in expected locations

**Error Codes**:
- `GATE_HUGO_BUILD_FAILED`: Hugo build returned non-zero exit code
- `GATE_HUGO_BUILD_ERROR`: Hugo reported build errors
- `GATE_HUGO_BUILD_TIMEOUT`: Build exceeded timeout

**Timeout** (per profile):
- local: 300s (5 minutes)
- ci: 600s (10 minutes)
- prod: 600s (10 minutes)

**Acceptance Criteria**:
- Gate passes if hugo build exits with code 0
- Gate fails if hugo build fails or times out
- Build output logged for debugging

---

### Gate 6: Internal Links

**Purpose**: Validate no broken internal links or anchors

**Inputs**:
- All `*.md` files under `RUN_DIR/work/site/`
- Hugo build output (rendered HTML)
- `RUN_DIR/artifacts/page_plan.json` (for expected pages)

**Validation Rules**:
1. All internal markdown links MUST resolve to existing files
2. All anchor references (`#heading`) MUST resolve to existing headings
3. All cross-references between pages MUST be valid
4. No broken relative links allowed

**Error Codes**:
- `GATE_LINK_BROKEN_INTERNAL`: Internal link points to non-existent file
- `GATE_LINK_BROKEN_ANCHOR`: Anchor reference to non-existent heading
- `GATE_LINK_BROKEN_RELATIVE`: Relative link cannot be resolved

**Timeout** (per profile):
- local: 120s
- ci: 180s
- prod: 180s

**Acceptance Criteria**:
- Gate passes if all internal links resolve
- Gate fails if any internal link is broken
- Issues array includes file:line for each broken link

---

### Gate 7: External Links

**Purpose**: Validate external links are reachable (optional by config)

**Inputs**:
- All `*.md` files under `RUN_DIR/work/site/`
- `run_config.validation_profile` (determines if enabled)
- External link allowlist (if configured)

**Validation Rules**:
1. All external HTTP/HTTPS links SHOULD be reachable (HTTP 200-399)
2. Links to allowlisted domains always checked
3. Redirects (3xx) are acceptable
4. Rate limiting and timeouts handled gracefully

**Error Codes**:
- `GATE_LINK_EXTERNAL_UNREACHABLE`: External link returned 4xx/5xx
- `GATE_LINK_EXTERNAL_TIMEOUT`: External link check timed out

**Timeout** (per profile):
- local: 300s (5 minutes, skip by default)
- ci: 600s (10 minutes, when enabled)
- prod: 600s (10 minutes)

**Acceptance Criteria**:
- Gate passes if all checked external links are reachable
- Gate skipped in local profile unless explicitly enabled
- Warnings for unreachable links in ci/prod profiles

---

### Gate 8: Snippet Checks

**Purpose**: Validate code snippet syntax and optionally execution

**Inputs**:
- `RUN_DIR/artifacts/snippet_catalog.json` (from W3 SnippetCurator)
- All code snippets embedded in content
- `run_config.validation_profile`

**Validation Rules**:
1. All code snippets MUST pass syntax validation for their language
2. Snippets MUST match language declared in code fence
3. Optional: Runnable snippets executed in container (ci/prod only)
4. Snippet sources MUST exist in snippet catalog

**Error Codes**:
- `GATE_SNIPPET_SYNTAX_ERROR`: Snippet has syntax errors
- `GATE_SNIPPET_LANGUAGE_MISMATCH`: Declared language doesn't match syntax
- `GATE_SNIPPET_EXECUTION_FAILED`: Runnable snippet failed to execute
- `GATE_SNIPPET_NOT_IN_CATALOG`: Snippet not found in catalog

**Timeout** (per profile):
- local: 60s per snippet file
- ci: 120s per snippet file
- prod: 120s per snippet file

**Acceptance Criteria**:
- Gate passes if all snippets pass syntax checks
- Optional execution in ci/prod profiles
- Issues array includes snippet location and error details

---

### Gate 9: TruthLock

**Purpose**: Enforce claim stability and evidence grounding requirements

**Inputs**:
- `RUN_DIR/artifacts/truth_lock_report.json` (from W2 FactsBuilder)
- `RUN_DIR/artifacts/evidence_map.json` (from W2)
- All generated content with claim markers
- `run_config.allow_inference`

**Validation Rules**:
1. All claims in content MUST link to EvidenceMap entries
2. No uncited facts allowed (unless allow_inference=true with constraints)
3. Claim IDs MUST be stable (match truth_lock_report)
4. Evidence sources MUST be traceable to repo artifacts
5. Contradictions MUST be resolved (per priority rules)

**Error Codes**:
- `GATE_TRUTHLOCK_UNCITED_FACT`: Claim without evidence link
- `GATE_TRUTHLOCK_INVALID_CLAIM_ID`: Claim ID not in truth_lock_report
- `GATE_TRUTHLOCK_UNRESOLVED_CONTRADICTION`: Contradiction not resolved
- `GATE_TRUTHLOCK_EVIDENCE_MISSING`: Evidence source not found

**Timeout** (per profile):
- local: 60s
- ci: 120s
- prod: 120s

**Acceptance Criteria**:
- Gate passes if all claims are grounded in evidence
- Gate fails if any uncited facts or unresolved contradictions exist
- TruthLock report must show zero violations

---

### Gate 10: Consistency

**Purpose**: Validate cross-artifact consistency and required content presence

**Inputs**:
- `RUN_DIR/artifacts/product_facts.json` (from W2 FactsBuilder)
- `RUN_DIR/artifacts/page_plan.json` (from W4 IAPlanner)
- All generated content files
- `run_config` (for canonical URLs)

**Validation Rules**:
1. `product_name` MUST be consistent across all artifacts and content
2. `repo_url` MUST match across ProductFacts and page frontmatter
3. Canonical URLs MUST match run_config canonical_urls
4. Required headings MUST be present (per page type)
5. Required sections MUST be present (per required_sections)

**Error Codes**:
- `GATE_CONSISTENCY_PRODUCT_NAME_MISMATCH`: product_name inconsistent
- `GATE_CONSISTENCY_REPO_URL_MISMATCH`: repo_url inconsistent
- `GATE_CONSISTENCY_CANONICAL_URL_MISMATCH`: canonical_url inconsistent
- `GATE_CONSISTENCY_REQUIRED_HEADING_MISSING`: Required heading absent
- `GATE_CONSISTENCY_REQUIRED_SECTION_MISSING`: Required section absent

**Timeout** (per profile):
- local: 30s
- ci: 60s
- prod: 60s

**Acceptance Criteria**:
- Gate passes if all consistency checks pass
- Gate fails if any inconsistencies found
- Issues array details specific inconsistencies with locations

---

### Gate 11: Template Token Lint

**Purpose**: Validate no unresolved template tokens remain in generated content

**Inputs**:
- All `*.md` files under `RUN_DIR/work/site/`
- All `*.json` files under `RUN_DIR/artifacts/`

**Validation Rules**:
1. No unresolved `__UPPER_SNAKE__` tokens allowed in content
2. No unresolved `__PLATFORM__` tokens allowed
3. No unresolved `{{template_var}}` tokens allowed
4. Template tokens in code blocks are allowed (not evaluated)

**Error Codes**:
- `GATE_TEMPLATE_TOKEN_UNRESOLVED`: Unresolved template token found
- `GATE_TEMPLATE_PLATFORM_TOKEN`: Unresolved __PLATFORM__ token

**Timeout** (per profile):
- local: 30s
- ci: 60s
- prod: 60s

**Acceptance Criteria**:
- Gate passes if no unresolved tokens found
- Gate fails (BLOCKER) if any token found outside code blocks
- Issues include file:line:token

---

### Gate 12: Universality Gates

**Purpose**: Validate content meets universality requirements

**Inputs**:
- `RUN_DIR/artifacts/product_facts.json` (from W2)
- All generated content
- `run_config.launch_tier`

**Validation Rules**:

1. **Tier Compliance**:
   - If `launch_tier=minimal`: Pages MUST NOT include exhaustive API lists or ungrounded workflow claims
   - If `launch_tier=rich`: Pages MUST demonstrate grounding (claim_groups -> snippets) before expanding page count

2. **Limitations Honesty**:
   - If `ProductFacts.limitations` is non-empty: docs + reference MUST include Limitations section
   - Limitations content MUST come from ProductFacts only

3. **Distribution Correctness**:
   - If `ProductFacts.distribution` is present: Install commands MUST match `distribution.install_commands` exactly
   - No invented package names allowed

4. **No Hidden Inference**:
   - Even with `allow_inference=true`: Capabilities must be grounded in EvidenceMap
   - Only page structure decisions may be inferred, not product capabilities

**Error Codes**:
- `GATE_UNIVERSALITY_TIER_VIOLATION`: Content violates launch_tier constraints
- `GATE_UNIVERSALITY_LIMITATIONS_MISSING`: Required Limitations section missing
- `GATE_UNIVERSALITY_DISTRIBUTION_MISMATCH`: Install commands don't match ProductFacts
- `GATE_UNIVERSALITY_HIDDEN_INFERENCE`: Ungrounded capability claim detected

**Timeout** (per profile):
- local: 60s
- ci: 120s
- prod: 120s

**Acceptance Criteria**:
- Gate passes if all universality rules satisfied
- Gate fails if any rule violated
- Issues detail specific violations with evidence

---

### Gate 13: Rollback Metadata Validation (Guarantee L)

**Purpose**: Validate PR artifacts include rollback metadata (prod profile only)

**Inputs**:
- `RUN_DIR/artifacts/pr.json` (from W9 PRManager)
- `run_config.validation_profile`

**Validation Rules** (only in prod profile):
1. `pr.json` MUST exist
2. `pr.json` MUST validate against `specs/schemas/pr.schema.json`
3. Required fields MUST be present: `base_ref`, `run_id`, `rollback_steps`, `affected_paths`
4. `base_ref` MUST match pattern `^[a-f0-9]{40}$` (40-char SHA)
5. `rollback_steps` array MUST have minItems: 1
6. `affected_paths` array MUST have minItems: 1
7. All paths in `affected_paths` MUST appear in PR diff

**Error Codes**:
- `PR_MISSING_ROLLBACK_METADATA`: Required rollback field missing
- `PR_INVALID_BASE_REF_FORMAT`: base_ref not a valid SHA
- `PR_EMPTY_ROLLBACK_STEPS`: rollback_steps array empty
- `PR_EMPTY_AFFECTED_PATHS`: affected_paths array empty
- `PR_AFFECTED_PATH_NOT_IN_DIFF`: Path in affected_paths missing from PR diff

**Behavior by Profile**:
- **prod**: BLOCKER if validation fails
- **ci**: WARN if validation fails
- **local**: SKIP (not run)

**Timeout**:
- local: N/A (not run)
- ci: 5s
- prod: 10s

**Acceptance Criteria**:
- Gate passes if all validation rules pass (prod profile)
- Gate skipped if profile != prod
- Issues array populated with specific violations

---

### Gate T: Test Determinism Configuration (Guarantee I)

**Purpose**: Validate test configuration enforces determinism (PYTHONHASHSEED=0)

**Inputs**:
- `pyproject.toml` (pytest configuration)
- `pytest.ini` (if exists)
- `.github/workflows/*.yml` (CI test commands)

**Validation Rules**:
1. One of the following MUST be true:
   - `pyproject.toml` contains `[tool.pytest.ini_options]` with `env = ["PYTHONHASHSEED=0"]`
   - `pytest.ini` contains `[pytest]` section with `env = PYTHONHASHSEED=0`
   - All CI workflow test commands set `PYTHONHASHSEED=0` before running pytest

**Error Codes**:
- `TEST_MISSING_PYTHONHASHSEED`: PYTHONHASHSEED=0 not set in test config
- `TEST_DETERMINISM_NOT_ENFORCED`: No determinism controls in test config

**Timeout**: 5s (all profiles)

**Acceptance Criteria**:
- Gate passes if any validation rule is true
- Gate fails if all validation rules are false

---

## Gate outputs
- validation_report.json (schemas/validation_report.schema.json)
- truth_lock_report.json (schemas/truth_lock_report.schema.json)
- issues list (schemas/issue.schema.json)

## Fix loop
VALIDATING -> FAIL -> FIXING -> VALIDATING
- Fix attempts must be capped (config).
- Each fix must be targeted and recorded as patches.
- **Manual content edits are forbidden by default**.
  - If `run_config.allow_manual_edits=false` (default): any changed file must have a patch/evidence record produced by the pipeline stages; unexplained diffs fail with a policy issue.
  - If `run_config.allow_manual_edits=true` (emergency only): validator must set `validation_report.manual_edits=true` and enumerate the affected files; orchestrator master review must list and justify them.

## Timeout Configuration (binding)

Each gate MUST have explicit timeout values to prevent indefinite hangs:

### Gate Timeouts by Profile

**local profile** (development):
- Schema validation: 30s per artifact
- Markdown lint: 60s
- Hugo config check: 10s
- Hugo build: 300s (5 minutes)
- Internal links: 120s
- External links: 300s (when enabled)
- Snippet syntax checks: 60s per snippet file
- TruthLock: 60s
- Consistency checks: 30s

**ci profile** (continuous integration):
- Schema validation: 60s per artifact
- Markdown lint: 120s
- Hugo config check: 20s
- Hugo build: 600s (10 minutes)
- Internal links: 180s
- External links: 600s (when enabled)
- Snippet syntax checks: 120s per snippet file
- TruthLock: 120s
- Consistency checks: 60s

**prod profile** (not typically used for gating, reference only):
- Same as CI profile but may include additional checks

### Timeout Behavior
- On timeout: emit BLOCKER issue with `error_code: GATE_TIMEOUT`
- Record which gate timed out in validation_report.json
- Do NOT retry timed-out gates automatically (orchestrator decides)
- Log timeout events to telemetry with gate name and elapsed time

---

## Profile-Based Gating (binding)

Validation behavior varies by profile:

### Profile Selection
Profile is determined by:
1. `run_config.validation_profile` (if present)
2. `--profile` CLI argument to `launch_validate`
3. Environment variable `LAUNCH_VALIDATION_PROFILE`
4. Default: `local`

### Profile Characteristics

**local** (development, fast feedback):
- Skip external link checks by default (override with `--check-external-links`)
- Skip runnable snippet execution (syntax check only)
- Relaxed timeout values
- Warnings don't fail the run (only errors)

**ci** (continuous integration, comprehensive):
- Run all gates including external links (if configured)
- Stricter timeouts
- Warnings MAY fail the run (configurable per `run_config.ci_strictness`)
- Hugo build in production mode
- Full TruthLock enforcement

**prod** (hypothetical, maximum rigor):
- All gates enabled
- Zero tolerance for warnings
- Longest timeouts
- Additional compliance checks (if defined)

### Profile Transitions
- Profile MUST be set at run start and MUST NOT change mid-run
- Validation reports MUST record which profile was used
- Fix loops inherit the profile from the initial validation

---

## Acceptance
All gates pass and validation_report.ok == true.

Additional acceptance criteria:
- validation_report.json validates against schema
- validation_report.profile field matches the profile used
- All timeouts are respected (no gate exceeds its timeout)
- All issues are recorded in issues[] array
- Gate execution order is: schema → lint → hugo_config → content_layout_platform → hugo_build → links → snippets → truthlock → consistency

## Universality Gates

### Gate: Tier compliance (new)
- If `launch_tier=minimal`, pages MUST NOT include exhaustive API lists or ungrounded workflow claims.
- If `launch_tier=rich`, pages MUST demonstrate grounding (claim_groups -> snippets) before expanding page count.

### Gate: Limitations honesty (new)
If ProductFacts.limitations is non-empty, then:
- docs + reference MUST include a Limitations section (or equivalent) populated only from ProductFacts.
- products MAY include a short limitations note (optional).

### Gate: Distribution correctness (new)
If ProductFacts.distribution is present, then:
- Install commands shown in products/docs MUST match distribution.install_commands exactly.
- Do not invent package names.

### Gate: "No hidden inference" (clarified)
Even when `allow_inference=true`, the system MAY only infer:
- page structure decisions (what to write), not product capabilities.
Capabilities must always be grounded in EvidenceMap or omitted.

## Strict Compliance Gates (Binding)

**All guarantees defined in [specs/34_strict_compliance_guarantees.md](34_strict_compliance_guarantees.md) MUST be enforced via gates.**

The following compliance gates are REQUIRED and MUST be implemented in preflight (`tools/validate_swarm_ready.py`) and/or runtime validation (`launch_validate`):

- **Gate J**: Pinned refs policy (Guarantee A) - No floating branches/tags in production configs
- **Gate K**: Frozen deps / lock integrity (Guarantee C) - Lock file exists and is used
- **Gate L**: Secrets scan (Guarantee E) - No secrets in logs/artifacts/reports
- **Gate M**: No placeholders in production paths (Guarantee E) - No NOT_IMPLEMENTED that produces false passes
- **Gate N**: Network allowlist contract present + validated (Guarantee D) - All endpoints allowlisted
- **Gate O**: Budget config contract present + validated (Guarantees F, G) - Budgets defined and enforced
- **Gate P**: Taskcard version-lock compliance (Guarantee K) - All taskcards have version locks
- **Gate Q**: CI parity (Guarantee H) - CI uses canonical commands
- **Gate R**: Untrusted-code non-execution policy (Guarantee J) - Ingested repo is parse-only

**Implementation status**: These gates MUST be added to `tools/validate_swarm_ready.py` as part of compliance hardening implementation.

**Failure behavior**: All compliance gate failures MUST be BLOCKER severity in prod profile.

---

### Gate U: Taskcard Authorization

**Purpose**: Validate all file modifications are authorized by taskcard's allowed_paths (Layer 4 post-run audit)

**Inputs**:
- `RUN_DIR/run_config.json` (taskcard_id field)
- `plans/taskcards/TC-{id}_{slug}.md` (taskcard file with allowed_paths)
- Git diff of modified files in RUN_DIR/work/site/

**Validation Rules**:
1. Production runs (validation_profile=prod) MUST have taskcard_id in run_config
2. Taskcard MUST exist in plans/taskcards/ directory
3. Taskcard MUST have active status (In-Progress or Done)
4. All modified files MUST match at least one pattern in taskcard's allowed_paths
5. Glob patterns support:
   - Exact paths: `pyproject.toml`
   - Recursive glob: `reports/**` (matches all files under reports/)
   - Wildcard directory: `src/launch/workers/w1_*/**` (matches w1_repo_scout, w1_*, etc.)
   - Wildcard files: `src/**/*.py` (matches all .py files under src/)

**Error Codes**:
- `GATE_U_TASKCARD_MISSING`: Production run has no taskcard_id
- `GATE_U_TASKCARD_INACTIVE`: Taskcard status is Draft, Blocked, or Cancelled
- `GATE_U_TASKCARD_PATH_VIOLATION`: Modified file not in allowed_paths
- `GATE_U_TASKCARD_LOAD_FAILED`: Failed to load taskcard file
- `GATE_U_RUN_CONFIG_INVALID`: Failed to load run_config.json

**Timeout** (per profile):
- local: 10s
- ci: 30s
- prod: 30s

**Acceptance Criteria**:
- Gate passes if all modified files match allowed_paths patterns
- Gate fails with BLOCKER if production run has no taskcard_id
- Gate fails with BLOCKER if file modified outside allowed_paths
- Gate skipped (passes) in local/ci mode if no taskcard_id provided
- Gate validates taskcard is in active status before checking paths

**Defense-in-depth layer**: Layer 4 (Post-run audit)

This gate is part of a 4-layer defense-in-depth system:
- Layer 0: Schema validation (taskcard_id format)
- Layer 1: Run initialization validation (fail fast before graph execution)
- Layer 3: Atomic write enforcement (strongest - validates at write time)
- Layer 4: Post-run audit (this gate - catches any bypasses)

**Spec references**:
- specs/34_strict_compliance_guarantees.md (Guarantee E: Write fence)
- plans/taskcards/00_TASKCARD_CONTRACT.md (Taskcard structure and lifecycle)
