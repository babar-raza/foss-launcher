# Strict Compliance Guarantees (Binding)

## Purpose

This specification defines **mandatory** compliance guarantees that MUST be enforced via automated gates, runtime validation, and tests. These guarantees eliminate entire classes of supply-chain, security, and reliability risks.

**Status**: BINDING for all production runs and agent implementations.

## Dependencies

- [specs/01_system_contract.md](01_system_contract.md) - System-wide contracts
- [specs/09_validation_gates.md](09_validation_gates.md) - Validation gate contracts
- [specs/19_toolchain_and_ci.md](19_toolchain_and_ci.md) - Toolchain and CI contracts
- [specs/29_project_repo_structure.md](29_project_repo_structure.md) - RUN_DIR isolation contracts
- [tools/validate_swarm_ready.py](../tools/validate_swarm_ready.py) - Preflight gate runner
- [src/launch/validators/cli.py](../src/launch/validators/cli.py) - Runtime validation (`launch_validate`)

---

## Production Paths (Binding Definition)

**Production paths** are code paths that MUST NOT contain placeholders, stubs, or "NOT_IMPLEMENTED" patterns that could produce false passes in validation.

Production paths include:
- `src/launch/**` (all runtime launcher code)
- Validation paths: `tools/validate_*.py`, `src/launch/validators/**`
- Gate scripts invoked by `tools/validate_swarm_ready.py`

**Exemptions**:
- Test fixtures under `tests/` MAY use placeholders for negative test cases
- Development scripts under `scripts/` that are not invoked by gates
- Documentation and examples under `docs/`, `specs/examples/`

---

## Guarantees (A-M)

All guarantees are **MUST/SHALL** requirements. Violations MUST fail preflight or runtime validation.

### A) Input Immutability - Pinned Commit SHAs

**Requirement**: All repository references in production run configs MUST use commit SHAs, NOT floating branches or tags.

**Rationale**: Prevents supply-chain attacks and ensures reproducibility.

**Enforcement surfaces**:
- Preflight: Gate J in `tools/validate_swarm_ready.py`
- Runtime: `launch_validate` MUST reject floating refs in prod profile
- Schema: `specs/schemas/run_config.schema.json` SHOULD enforce SHA format for `*_ref` fields in prod configs

**Failure behavior**:
- If any `*_ref` field (e.g., `github_ref`, `site_ref`, `workflows_ref`) uses a branch name (e.g., `main`, `master`) or tag instead of a commit SHA in a production run config, emit BLOCKER issue and fail the run.

**Allowed exceptions**:
- **Template configs only**: Files matching pattern `*_template.*` or `*.template.*` (e.g., `configs/products/_template.run_config.yaml`, `configs/pilots/_template.pinned.run_config.yaml`) MAY use placeholders like `FILL_ME`, `PIN_TO_COMMIT_SHA`, `main`, or `default_branch`. These are developer starting points and are NOT executable configs.
- **Pilot configs** (e.g., `specs/pilots/*/run_config.pinned.yaml`) MUST use pinned commit SHAs for all `*_ref` fields. The `*.pinned.*` naming signals deterministic regression testing and has no exceptions.
- **Production configs** have no exceptions. All `*_ref` fields MUST be commit SHAs.

#### Runtime Enforcement (Guarantee A)

**Gate**: `launch_validate` runtime check (in addition to Gate J preflight)

**Purpose**: Reject runs that use floating refs at runtime (defense in depth)

**Validation Rules**:
1. At start of `launch_validate` call, re-check all `*_ref` fields in `run_config`
2. All `*_ref` fields MUST match pattern `^[a-f0-9]{40}$` (40-char SHA)
3. Reject floating refs:
   - `refs/heads/*` (branch references)
   - `refs/tags/*` (tag references)
   - Branch names (e.g., `main`, `develop`)
   - `HEAD` or relative refs (`HEAD~1`, `@{upstream}`)

**Error Code**: `POLICY_FLOATING_REF_DETECTED`

**Behavior**:
- If floating ref detected: Raise error, terminate run immediately
- Error logged to telemetry
- Issue added to `issues[]` with severity: BLOCKER

**Integration**:
- TC-300 (Orchestrator): Call runtime validation before starting workers
- TC-460 (Validator): Implement runtime check in `launch_validate`

**Rationale**: Defense in depth. Even if Gate J passes at preflight, runtime check prevents race conditions or config tampering.

### Guarantee L: Floating Reference Detection

**Guarantee:** System MUST detect and reject floating Git references (branches, tags) in spec_ref field

**Definition:** Floating reference = Git ref that can move over time (e.g., branch name "main", tag "latest")

**Enforcement:**
1. Validate spec_ref field is exactly 40-character hex SHA (see specs/01:180-195 field definition)
2. Reject branch names (e.g., "main", "develop", "feature/foo")
3. Reject tag names (e.g., "v1.0.0", "latest")
4. Reject short SHAs (e.g., "a1b2c3d" - 7 chars)
5. Reject symbolic refs (e.g., "HEAD", "FETCH_HEAD")

**Error Cases:**
- spec_ref is branch/tag → ERROR: SPEC_REF_INVALID (see specs/01:134)
- spec_ref is not 40-char hex → ERROR: SPEC_REF_INVALID
- spec_ref field missing → ERROR: SPEC_REF_MISSING (see specs/01:135)

**Validation:**
- Preflight Gate 2 validates spec_ref format (see specs/09:30-42)
- Runtime Gate 1 validates spec_ref resolves to commit (see specs/09:145-158)

**Rationale:** Floating refs break reproducibility. Only immutable commit SHAs allowed.

**Example (VALID):**
```json
{
  "spec_ref": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0"
}
```

**Example (INVALID):**
```json
{
  "spec_ref": "main"  // ERROR: branch name not allowed
}
```

**Test Case:** See `tests/test_spec_ref_validation.py` (TO BE CREATED during implementation phase)

---

### B) Hermetic Execution Boundaries

**Requirement**: All file operations MUST be confined to `RUN_DIR` and MUST NOT escape via path traversal (`..`), absolute paths, or symlink resolution.

**Rationale**: Prevents accidental or malicious writes outside allowed scope.

**Enforcement surfaces**:
- Preflight: Gate B in `tools/validate_swarm_ready.py` validates `allowed_paths` do not escape repo root
- Runtime: Path resolution utilities in `src/launch/io/atomic.py` MUST use `Path.resolve()` and reject paths outside allowed boundaries
- Runtime: All file write operations MUST validate against `run_config.allowed_paths` after symlink resolution

**Failure behavior**:
- Any attempt to write outside `RUN_DIR` or `run_config.allowed_paths` MUST raise BLOCKER error code `POLICY_PATH_ESCAPE` and fail the run.

**Implementation requirements**:
- Add `validate_path_in_allowed(path, allowed_paths)` utility
- Enforce at patch application time (W6 Linker/Patcher)
- Add tests for `..`, absolute paths, symlink chains

---

### C) Supply-Chain Pinning

**Requirement**: All dependencies MUST be installed from a lock file (`uv.lock` or `poetry.lock`). No ad-hoc `pip install` without locking.

**Rationale**: Prevents dependency confusion and ensures reproducible builds.

**Enforcement surfaces**:
- Preflight: Gate K in `tools/validate_swarm_ready.py` validates lockfile exists
- Preflight: Gate K validates install commands use `uv sync --frozen` or equivalent
- CI: `.github/workflows/**` MUST use locked install commands

**Failure behavior**:
- If `.venv` does not exist, fail with error code `ENV_MISSING_VENV`
- If `uv.lock` (or `poetry.lock`) does not exist, fail with error code `ENV_MISSING_LOCKFILE`
- If Makefile or install scripts use non-frozen install, fail with warning (blocker in prod profile)

**Implementation requirements**:
- Gate K script: `tools/validate_supply_chain_pinning.py`
- Validates `Makefile` contains `uv sync --frozen` or `poetry install --frozen`
- Validates CI workflows use same commands

---

### D) Network Egress Allowlist

**Requirement**: All network requests MUST be to explicitly allow-listed hosts. No ad-hoc HTTP requests to arbitrary URLs.

**Rationale**: Prevents data exfiltration and supply-chain attacks via malicious endpoints.

**Enforcement surfaces**:
- Preflight: Gate N validates `config/network_allowlist.yaml` exists
- Preflight: Gate N validates all `run_config` endpoint hosts are in allowlist
- Runtime: HTTP client wrapper MUST check allowlist before making requests

**Allowlist file**: `config/network_allowlist.yaml`

**Allowed exception**:
- WebFetch for ingested repo documentation URLs (but these MUST NOT be arbitrary user input)

**Failure behavior**:
- If allowlist missing in prod profile, fail with error code `POLICY_NETWORK_ALLOWLIST_MISSING`
- If `run_config` contains non-allowlisted host, fail with error code `POLICY_NETWORK_UNAUTHORIZED_HOST`
- If runtime HTTP request attempts non-allowlisted host, fail with error code `NETWORK_BLOCKED`

**Implementation requirements**:
- Create `config/network_allowlist.yaml` (initially allow localhost and known Aspose/GitHub endpoints)
- Gate N script: `tools/validate_network_allowlist.py`
- Runtime enforcement: `src/launch/clients/**` wrappers MUST check allowlist

---

### E) Secret Hygiene / Redaction

**Requirement**: Secrets MUST NEVER appear in logs, artifacts, or reports. All secret-like patterns MUST be redacted.

**Rationale**: Prevents credential leakage.

**Enforcement surfaces**:
- Preflight: Gate L runs secrets scan on repository
- Preflight: Gate M validates no placeholders in production code
- Runtime: Logging utilities MUST redact secret patterns
- Post-run: Scan `runs/**/logs/**` and `runs/**/reports/**` for leaked secrets

**Secret patterns** (minimum):
- API keys: `[A-Za-z0-9_-]{32,}` in specific contexts
- GitHub tokens: `ghp_[A-Za-z0-9_]+`, `github_pat_[A-Za-z0-9_]+`
- Bearer tokens: `Bearer\s+[A-Za-z0-9._-]+`
- Environment variable values for keys ending in `_TOKEN`, `_KEY`, `_SECRET`

**Failure behavior**:
- If secrets scan detects leakage, fail with error code `SECURITY_SECRET_LEAKED`
- Logs MUST show `***REDACTED***` instead of actual secret values

**Implementation requirements**:
- Gate L script: `tools/validate_secrets_hygiene.py` (scan for patterns)
- Runtime redaction: `src/launch/util/logging.py` filters
- Tests: Verify redaction works for all secret patterns

---

### F) Budget + Circuit Breakers

**Requirement**: All runs MUST have explicit budgets for runtime, retries, LLM calls, tokens, and file churn. Exceeding budgets MUST fail fast.

**Rationale**: Prevents runaway costs and infinite loops.

**Enforcement surfaces**:
- Preflight: Gate O validates `run_config.budgets` exists and is non-empty in prod configs
- Runtime: Orchestrator MUST enforce budgets and emit BLOCKER on violation

**Required budget fields** (in `run_config.budgets`):
- `max_runtime_s`: Maximum wall-clock time for entire run (seconds)
- `max_llm_calls`: Maximum LLM API calls across all workers
- `max_llm_tokens`: Maximum total tokens (input + output) across all LLM calls
- `max_file_writes`: Maximum files written to `RUN_DIR/work/site/`
- `max_patch_attempts`: Maximum patch bundle retries (separate from `max_fix_attempts`)

**Failure behavior**:
- If budget missing in prod profile, fail with error code `POLICY_BUDGET_MISSING`
- If budget exceeded during run, fail with error code `BUDGET_EXCEEDED_{BUDGET_TYPE}`

**Implementation requirements**:
- Extend `specs/schemas/run_config.schema.json` with `budgets` object
- Gate O script: `tools/validate_budgets_config.py`
- Runtime tracking: `src/launch/orchestrator/**` state tracking
- Tests: Verify budget violations are detected

---

### G) Change Budget + Minimal-Diff Discipline

**Requirement**: Runs MUST NOT produce excessive diffs or formatting-only mass rewrites. Patch bundles MUST respect change budgets.

**Rationale**: Prevents uncontrolled repository churn and makes diffs reviewable.

**Enforcement surfaces**:
- Preflight: Gate O validates change budget configuration (combined with Guarantee F)
- Runtime: `launch_validate` MUST check patch bundles for excessive churn
- Post-run: Diff analysis MUST flag formatting-only changes

**Change budget policy** (binding):
- Maximum lines changed per file: 500 (configurable in `run_config.budgets.max_lines_per_file`)
- Maximum files changed per run: 100 (configurable in `run_config.budgets.max_files_changed`)
- Formatting-only changes (whitespace, line endings) MUST be flagged and require explicit approval

**Failure behavior**:
- If patch bundle exceeds change budget, fail with error code `POLICY_CHANGE_BUDGET_EXCEEDED`
- If >80% of diff is formatting-only, emit warning (blocker in prod profile)

#### Formatting-Only Detection Algorithm

**Purpose**: Detect when >80% of diff is formatting-only (Guarantee G enforcement)

**Algorithm** (implemented in `src/launch/util/diff_analyzer.py`):

1. **Normalize whitespace** for both old and new content:
   - Strip leading/trailing whitespace from each line
   - Collapse multiple spaces to single space
   - Normalize line endings to LF

2. **Compare semantic content**:
   - If normalized contents are identical → 100% formatting-only
   - If normalized contents differ → calculate formatting percentage

3. **Calculate formatting percentage**:
   ```
   total_lines_changed = lines_added + lines_removed
   formatting_lines = lines where normalized content matches but original differs
   formatting_percentage = (formatting_lines / total_lines_changed) * 100
   ```

4. **Threshold enforcement**:
   - If `formatting_percentage > 80%`:
     - Emit warning: "Diff is {formatting_percentage}% formatting-only"
     - In prod profile: Emit BLOCKER issue with error_code: POLICY_FORMATTING_ONLY_DIFF
     - In local/ci profiles: Emit WARN issue

**Edge Cases**:
- Empty diffs (no changes): Not considered formatting-only, no warning
- Comment-only changes: Treated as semantic changes (not formatting)
- Docstring changes: Treated as semantic changes (not formatting)

**Measurement Unit**: By lines (not by characters or by files)

**Implementation requirements**:
- Runtime enforcement in `src/launch/util/diff_analyzer.py` (analyzes `patch_bundle.json`)
- Diff analysis: Detect formatting-only changes via heuristics
- Tests: Verify formatting-only diffs are flagged in `tests/unit/util/test_diff_analyzer.py`

---

### H) CI Parity / Single Canonical Entrypoint

**Requirement**: CI MUST use the same commands as local development. No CI-specific scripts or workarounds.

**Rationale**: "Works on my machine" bugs are eliminated.

**Enforcement surfaces**:
- Preflight: Gate Q validates CI workflows reference canonical commands
- CI: Workflows MUST call `make install-uv`, `python tools/validate_swarm_ready.py`, `pytest`

**Canonical commands**:
- Install: `make install-uv` (deterministic) or `make install` (fallback)
- Preflight: `python tools/validate_swarm_ready.py`
- Tests: `pytest`
- Validation: `launch_validate --run_dir <path> --profile ci`

**Failure behavior**:
- If CI workflow does not reference canonical commands, fail Gate Q with error code `POLICY_CI_PARITY_VIOLATION`

**Implementation requirements**:
- Gate Q script: `tools/validate_ci_parity.py` (parse `.github/workflows/*.yml`)
- Tests: Verify gate detects non-canonical CI commands

---

### I) Non-Flaky Tests

**Requirement**: All tests MUST be deterministic and stable. No random failures.

**Rationale**: Flaky tests erode trust and waste time.

**Enforcement surfaces**:
- Preflight: Verify test configuration enforces determinism
- CI: Run tests with stable seeds
- Test runner: Enforce `PYTHONHASHSEED=0` or equivalent

**Determinism requirements**:
- All random operations MUST use seeded RNGs
- Timestamps MUST be mocked or frozen in tests
- File iteration order MUST be sorted
- Test execution order MUST be deterministic

**Failure behavior**:
- If `PYTHONHASHSEED` is not set in test runner config, emit warning
- If tests fail intermittently (detected via CI history), fail with error code `TEST_FLAKY_DETECTED`

**Implementation requirements**:
- Update `pyproject.toml` or `pytest.ini` to enforce `PYTHONHASHSEED=0`
- Add test helper for seeded randomness
- CI: Log test seeds for reproducibility

---

### J) No Execution of Untrusted Repo Code

**Requirement**: Ingested repository code MUST be parse-only. No subprocess execution of scripts from `RUN_DIR/work/repo/`.

**Rationale**: Prevents supply-chain attacks via malicious repo scripts.

**Enforcement surfaces**:
- Preflight: Gate R validates ingestion policy
- Runtime: Subprocess wrapper MUST refuse execution with `cwd` under `RUN_DIR/work/repo/`

**Allowed operations**:
- Parse files (Python AST, JSON, YAML, TOML)
- Read files
- Analyze metadata

**Forbidden operations**:
- `subprocess.run` with `cwd=RUN_DIR/work/repo/`
- `exec()`, `eval()` on ingested code
- Dynamic imports from ingested repo

**Failure behavior**:
- If subprocess execution attempted from ingested repo, fail with error code `SECURITY_UNTRUSTED_EXECUTION`

**Implementation requirements**:
- Gate R script: `tools/validate_untrusted_code_policy.py` (static analysis)
- Runtime wrapper: `src/launch/util/subprocess.py` validates `cwd` parameter
- Tests: Verify execution attempts are blocked

---

### K) Spec/Taskcard Version Locking

**Requirement**: All taskcards and run configs MUST specify version locks for specs, rulesets, and templates.

**Rationale**: Prevents silent drift and ensures reproducibility.

**Enforcement surfaces**:
- Preflight: Gate B (taskcard validation) validates version lock fields
- Preflight: Gate P (taskcard version locks) validates all taskcards have required version fields
- Preflight: Run config validation validates `templates_version` and `ruleset_version` exist
- Runtime: Orchestrator MUST record version locks in `snapshot.json`

**Required fields**:
- Taskcards: `spec_ref` (commit SHA of spec pack), `ruleset_version`, `templates_version`
- Run configs: `ruleset_version`, `templates_version`

**Canonical values**:
- `ruleset_version: "ruleset.v1"`
- `templates_version: "templates.v1"`
- `spec_ref: "<commit_sha>"` (obtained via `git rev-parse HEAD`)

**Failure behavior**:
- If taskcard missing version lock fields, fail Gate B with error code `TASKCARD_MISSING_VERSION_LOCK`
- If run config missing version locks, fail with error code `CONFIG_MISSING_VERSION_LOCK`

**Implementation requirements**:
- Update `tools/validate_taskcards.py` REQUIRED_KEYS
- Update `specs/schemas/run_config.schema.json` to require version fields
- Mass-update all taskcards (see Phase 3)

---

### L) Rollback + Recovery Contract

**Requirement**: All PR artifacts MUST include rollback steps, base ref, and run_id linkage for recovery.

**Rationale**: Enables safe rollback when launches fail in production.

**Enforcement surfaces**:
- Preflight: Validate PR contract includes rollback fields
- Runtime: `launch_validate` in prod profile MUST check rollback metadata exists
- PR template: MUST include rollback checklist

**Required rollback fields** (in `RUN_DIR/artifacts/pr.json`):
- `base_ref`: The commit SHA of the site repo before changes
- `run_id`: The run that produced this PR
- `rollback_steps`: List of commands to revert changes
- `affected_paths`: List of all modified/created files

**Failure behavior**:
- If PR artifacts missing rollback metadata in prod profile, fail with error code `PR_MISSING_ROLLBACK_METADATA`

**Implementation requirements**:
- Update `specs/12_pr_and_release.md` with rollback requirements
- Update `specs/schemas/pr.schema.json` (create if missing) with rollback fields
- Runtime validation: `launch_validate` checks for rollback metadata
- Tests: Verify rollback metadata is generated

---

### M) Repository URL Allowlist

**Requirement**: All repository URLs cloned by the system MUST match explicitly approved patterns. Arbitrary GitHub repositories MUST be blocked.

**Rationale**: Prevents supply-chain attacks via repository injection. Ensures only authorized Aspose product repositories can be ingested for documentation generation.

**Enforcement surfaces**:
- Preflight: Gate M in `tools/validate_swarm_ready.py` validates run config repo URLs
- Runtime: Pre-clone validation in `src/launch/workers/w1_repo_scout/clone.py` MUST call validator before any git clone
- Validator: `src/launch/workers/_git/repo_url_validator.py` enforces allowed patterns

**Allowed repository patterns** (exhaustive):

1. **Product repositories**: `https://github.com/{org}/aspose-{family}-foss-{platform}`
   - `{family}`: One of: 3d, barcode, cad, cells, diagram, email, finance, font, gis, html, imaging, note, ocr, page, pdf, psd, slides, svg, tasks, tex, words, zip
   - `{platform}`: One of: android, cpp, dotnet, go, java, javascript, net, nodejs, php, python, ruby, rust, swift, typescript
   - Organization: ANY valid GitHub organization name

2. **Site repository** (fixed): `https://github.com/Aspose/aspose.org`

3. **Workflows repository** (fixed): `https://github.com/Aspose/aspose.org-workflows`

4. **Legacy patterns** (temporary): `https://github.com/{org}/Aspose.{Family}-for-{Platform}-via-.NET`
   - Deprecated, but allowed for backward compatibility with existing pilots
   - Normalized internally to standard pattern

**Forbidden patterns**:
- Non-GitHub hosts (GitLab, Bitbucket, self-hosted)
- Non-HTTPS protocols (git://, ssh://, http://)
- Arbitrary GitHub repositories not matching approved patterns
- Path traversal or injection attempts

**Error codes**:
- `REPO_URL_POLICY_VIOLATION` - Generic policy violation
- `REPO_URL_INVALID_PROTOCOL` - Protocol is not HTTPS
- `REPO_URL_INVALID_HOST` - Host is not github.com
- `REPO_URL_INVALID_FAMILY` - Family not in allowed list
- `REPO_URL_INVALID_PLATFORM` - Platform not in allowed list
- `REPO_URL_MALFORMED` - URL structure is invalid

**Failure behavior**:
- If repository URL violates policy, emit BLOCKER issue with appropriate error code
- MUST NOT attempt to clone the repository
- Exit with status code 1 (user error - invalid input)
- Log violation to telemetry with event type `REPO_URL_BLOCKED`

**Implementation requirements**:
- Detailed spec: `specs/36_repository_url_policy.md` (binding contract)
- Validator module: `src/launch/workers/_git/repo_url_validator.py`
- Integration: `src/launch/workers/w1_repo_scout/clone.py` calls validator before clone
- Tests: `tests/unit/workers/_git/test_repo_url_validator.py` (all patterns)
- Preflight gate: `tools/validate_swarm_ready.py` Gate M validates run config URLs

**Validation rules** (binding):
1. Parse and normalize URL (strip `.git`, lowercase)
2. Validate protocol is `https://`
3. Validate host is `github.com`
4. Validate repository name matches allowed pattern for repo type
5. Validate family in allowed list (for product repos)
6. Validate platform in allowed list (for product repos)

**Telemetry events**:
- `REPO_URL_VALIDATED` - URL passed validation
- `REPO_URL_BLOCKED` - URL rejected by policy

**Spec reference**: [specs/36_repository_url_policy.md](36_repository_url_policy.md)

---

## Ambiguity Escalation (Blocker Process)

If any requirement in this spec is underspecified or conflicts with other binding specs, implementers MUST:

1. STOP work on that guarantee
2. Write a BLOCKER issue artifact to `reports/agents/<agent>/COMPLIANCE_HARDENING/blockers/<timestamp>_<slug>.issue.json`
3. Validate blocker against `specs/schemas/issue.schema.json`
4. Include in blocker:
   - `severity: "blocker"`
   - `component`: The guarantee letter (e.g., "Guarantee-A")
   - `description`: Clear explanation of the ambiguity
   - `proposed_resolution`: What spec/taskcard needs clarification

**No guessing. No partial implementation without clarification.**

---

## Acceptance Criteria

This spec is successfully implemented when:

1. All 13 guarantees (A-M) have:
   - Binding spec text (this document)
   - Preflight gates in `tools/validate_swarm_ready.py`
   - Runtime enforcement in `src/launch/**` or `launch_validate`
   - Tests in `tests/**`
   - Proof artifacts in compliance matrix

2. All gates pass: `python tools/validate_swarm_ready.py`

3. No production code paths contain:
   - `NOT_IMPLEMENTED` without explicit exemption
   - `TODO`, `FIXME`, `HACK` without issue linkage
   - `PIN_ME` sentinels

4. Compliance matrix (`reports/agents/<agent>/COMPLIANCE_HARDENING/<run_id>/compliance_matrix.md`) maps every guarantee to concrete enforcement

---

## See Also

- [specs/01_system_contract.md](01_system_contract.md) - Error handling and exit codes
- [specs/09_validation_gates.md](09_validation_gates.md) - Gate contracts
- [specs/19_toolchain_and_ci.md](19_toolchain_and_ci.md) - Toolchain lock policy
- [specs/29_project_repo_structure.md](29_project_repo_structure.md) - RUN_DIR isolation
- [plans/taskcards/00_TASKCARD_CONTRACT.md](../plans/taskcards/00_TASKCARD_CONTRACT.md) - Taskcard write-fence rules
