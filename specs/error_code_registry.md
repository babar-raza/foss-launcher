# Error Code Registry

**Purpose**: Canonical registry of all error codes used across foss-launcher

**Authority**: specs/01_system_contract.md:92-136 defines error taxonomy

---

## Error Code Format

Pattern: `{COMPONENT}_{ERROR_TYPE}_{SPECIFIC}`

Example: `REPO_FLOATING_REF_DETECTED`

---

## Error Code Catalog

*(To be populated during implementation)*

### Policy Errors (POLICY_*)

| Error Code | Component | Description | Severity | Source |
|------------|-----------|-------------|----------|--------|
| POLICY_PATH_ESCAPE | path_validation | Path escapes allowed boundary | BLOCKER | src/launch/util/path_validation.py:72 |
| POLICY_PATH_TRAVERSAL | path_validation | Path contains traversal attempt | BLOCKER | src/launch/util/path_validation.py:159 |
| POLICY_PATH_SUSPICIOUS | path_validation | Path contains suspicious patterns | BLOCKER | src/launch/util/path_validation.py:168 |
| POLICY_PATH_NOT_ALLOWED | path_validation | Path not in allowed_paths | BLOCKER | src/launch/util/path_validation.py:130 |
| POLICY_CHANGE_BUDGET_EXCEEDED | diff_analyzer | Change budget exceeded | BLOCKER (prod) | src/launch/util/diff_analyzer.py:21 |
| POLICY_NETWORK_UNAUTHORIZED_HOST | http | Host not in allowlist | BLOCKER | src/launch/clients/http.py:24 |
| POLICY_FLOATING_REF_DETECTED | repo_validation | Floating ref detected | BLOCKER | TBD (TC-460) |
| POLICY_FORMATTING_ONLY_DIFF | diff_analyzer | >80% formatting-only changes | BLOCKER (prod) | TBD (TC-300) |

### Budget Errors (BUDGET_*)

| Error Code | Component | Description | Severity | Source |
|------------|-----------|-------------|----------|--------|
| BUDGET_EXCEEDED_LLM_CALLS | budget_tracker | LLM call budget exceeded | BLOCKER | src/launch/util/budget_tracker.py:21 |
| BUDGET_EXCEEDED_FILE_WRITES | budget_tracker | File write budget exceeded | BLOCKER | src/launch/util/budget_tracker.py:21 |
| BUDGET_EXCEEDED_RUNTIME | budget_tracker | Runtime budget exceeded | BLOCKER | src/launch/util/budget_tracker.py:21 |

### Security Errors (SECURITY_*)

| Error Code | Component | Description | Severity | Source |
|------------|-----------|-------------|----------|--------|
| SECURITY_SECRET_LEAKED | secrets_hygiene | Secret detected in commit | BLOCKER | specs/34_strict_compliance_guarantees.md:151 |
| SECURITY_UNTRUSTED_EXECUTION | subprocess | Untrusted code execution attempt | BLOCKER | src/launch/util/subprocess.py:18 |

### Network Errors (NETWORK_*)

| Error Code | Component | Description | Severity | Source |
|------------|-----------|-------------|----------|--------|
| NETWORK_BLOCKED | http | Network request blocked by allowlist | BLOCKER | src/launch/clients/http.py:24 |

### Gate Errors (GATE_*)

| Error Code | Component | Description | Severity | Source |
|------------|-----------|-------------|----------|--------|
| GATE_RUN_LAYOUT_MISSING_PATHS | cli | Required RUN_DIR paths missing | BLOCKER | src/launch/validators/cli.py:125 |
| GATE_TOOLCHAIN_LOCK_FAILED | cli | Toolchain lock validation failed | BLOCKER | src/launch/validators/cli.py:148 |
| GATE_TIMEOUT | validator | Gate execution timed out | BLOCKER | specs/09_validation_gates.md:116-119 |

### PR Errors (PR_*)

| Error Code | Component | Description | Severity | Source |
|------------|-----------|-------------|----------|--------|
| PR_MISSING_ROLLBACK_METADATA | pr_manager | Rollback metadata missing in PR | BLOCKER (prod) | TBD (TC-480) |

---

## Enforcement

**Preflight Gate**: (To be implemented in TC-100 or TC-300)
- Scan all source files for error_code usage
- Validate all error codes present in this registry
- Fail if unregistered error codes found

**Runtime Enforcement**:
- All error codes logged to telemetry (REQ-042)
- Error codes stable across versions (REQ-041)

---

## Updates

When adding new error codes:
1. Add entry to this registry (specs/error_code_registry.md)
2. Use error code in implementation
3. Log to telemetry
4. Add tests for error code path
