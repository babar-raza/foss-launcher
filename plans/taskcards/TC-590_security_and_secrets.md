---
id: TC-590
title: "Security and Secrets Handling (redaction + lightweight scan)"
status: Done
owner: "SECURITY_AGENT"
updated: "2026-01-28"
depends_on:
  - TC-300
allowed_paths:
  - src/launch/tools/secrets_scan.py
  - src/launch/tools/redact.py
  - src/launch/tools/secure_logging.py
  - tests/unit/tools/test_tc_590_security.py
  - reports/agents/**/TC-590/**
evidence_required:
  - reports/agents/<agent>/TC-590/report.md
  - reports/agents/<agent>/TC-590/self_review.md
spec_ref: f48fc5dbb12c5513f42aabc2a90e2b08c6170323
ruleset_version: ruleset.v1
templates_version: templates.v1
---

# Taskcard TC-590 — Security and Secrets Handling (redaction + lightweight scan)

## Objective
Ensure secrets are never written to disk logs/reports and that the system uses safe defaults for credentials handling.

## Required spec references
- specs/01_system_contract.md
- specs/11_state_and_events.md
- specs/17_github_commit_service.md
- specs/19_toolchain_and_ci.md

## Scope
### In scope
- Redaction filter for logs and reports
- Standard env var names for tokens
- Ensure tokens never appear in `RUN_DIR/logs/**`, `RUN_DIR/reports/**`, or repo-root `reports/**`
- Lightweight secrets scan integrated into TC-570 gate (pattern based)
- Unit tests for common token patterns

### Out of scope
- _None._

## Inputs
- Environment variables (GitHub token, provider keys)
- Log messages and error payloads

## Outputs
- `RUN_DIR/reports/security.json` (summary, no token values)
- Event: `SECURITY_CHECK_COMPLETED`

## Allowed paths
- src/launch/tools/secrets_scan.py
- src/launch/tools/redact.py
- src/launch/tools/secure_logging.py
- tests/unit/tools/test_tc_590_security.py
- reports/agents/**/TC-590/**
## Implementation steps
1) Define minimal secret patterns used in your environment.
2) Implement `redact_text()` that replaces detected values with `REDACTED`.
3) Integrate redaction before writing to disk.
4) Implement scan tool that reports files and counts only.
5) Add unit tests with synthetic tokens.

## E2E verification
**Concrete command(s) to run:**
```bash
python -m launch.security.scan --config specs/pilots/pilot-aspose-3d-foss-python/run_config.pinned.yaml
```

**Expected artifacts:**
- artifacts/security_scan.json

**Success criteria:**
- [ ] No secrets in output
- [ ] Redaction applied

> If E2E harness not yet implemented, this defines the stub contract for TC-520/522/523.

## Integration boundary proven
What upstream/downstream wiring was validated:
- Upstream: TC-200 (config with secret env vars)
- Downstream: TC-480 (PR manager redacts sensitive data)
- Contracts: specs/security scanning rules

## Failure modes

### Failure mode 1: Secrets scan misses token in logs due to incomplete regex pattern
**Detection:** Gate L passes but manual review finds unredacted API token, GitHub PAT, or LLM API key in RUN_DIR/logs/**; security audit flags leaked secret; token visible in evidence bundle
**Resolution:** Review secret patterns in secrets_scan.py; add missing patterns for common token formats (gh[pousr]_[A-Za-z0-9]{36}, sk-[a-zA-Z0-9]{48}, etc.); test against real token samples (obfuscated); ensure pattern matches token prefix and sufficient suffix length; update pattern list in specs if new token types discovered
**Spec/Gate:** specs/09_validation_gates.md (Gate L secrets scan), specs/34_strict_compliance_guarantees.md (Guarantee J: secret hygiene)

### Failure mode 2: Redaction applied too late allowing secrets in intermediate artifacts
**Detection:** Secrets found in temp files or early-stage artifacts before redaction; W5 writes unredacted content to disk; error logs contain raw tokens before redact_text() called
**Resolution:** Review redaction integration points; ensure redact_text() called BEFORE writing to disk at all code paths; verify secure_logging wrapper applied to all logger instances; check that error exception messages redacted before serialization; integrate redaction at IO boundary level (e.g., write_json/write_text wrappers)
**Spec/Gate:** specs/34_strict_compliance_guarantees.md (Guarantee J), TC-200 (IO utilities integration)

### Failure mode 3: Redaction false positive masks legitimate content breaking functionality
**Detection:** Valid URLs, file paths, or identifiers redacted incorrectly; W4 output contains REDACTED where it shouldn't; broken links or missing data in generated pages; overly broad regex pattern
**Resolution:** Review redaction patterns for specificity; ensure token patterns require prefix (e.g., "Bearer ", "token=") or known format; avoid generic patterns like [A-Za-z0-9]{20,} that match UUIDs or SHAs; add whitelist for known-safe patterns; test redaction with non-secret data samples; document safe vs unsafe patterns
**Spec/Gate:** specs/34_strict_compliance_guarantees.md (Guarantee J: minimal redaction), specs/10_determinism_and_caching.md (artifact integrity)

### Failure mode 4: security.json report itself contains secret values defeating purpose
**Detection:** Gate L scans security.json and finds secrets in report; recursive exposure problem; summary includes token samples for debugging
**Resolution:** Review security.json generation; ensure report includes only counts, file paths, and pattern names (NOT matched values); verify no token values included in examples or debugging output; apply redaction to security.json itself before writing; validate that report shows "3 secrets found in file X" without showing actual secrets
**Spec/Gate:** specs/09_validation_gates.md (Gate L output format), specs/11_state_and_events.md (security report schema)

## Task-specific review checklist
Beyond the standard acceptance checks, verify:
- [ ] All outputs are written atomically per specs/10_determinism_and_caching.md
- [ ] No manual content edits made (compliance with no_manual_content_edits policy)
- [ ] Determinism verified by running task twice and comparing artifacts byte-for-byte
- [ ] All spec references listed in taskcard were consulted during implementation
- [ ] Evidence files (report.md, self_review.md) include all required sections and command outputs
- [ ] No placeholder values (PIN_ME, TODO, FIXME, etc.) remain in production code paths

## Deliverables
- Code + tests
- Report and self review under repo-root reports/

## Acceptance checks
- [ ] No tool prints raw secrets
- [ ] Redaction occurs before write
- [ ] Scan report contains file paths and counts only

## Self-review
Use `reports/templates/self_review_12d.md`. Any dimension <4 must include a concrete fix plan.
