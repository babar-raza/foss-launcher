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
1. **Failure**: Schema validation fails for output artifacts
   - **Detection**: `validate_swarm_ready.py` or pytest fails with JSON schema errors
   - **Fix**: Review artifact structure against schema files in `specs/schemas/`; ensure all required fields are present and types match
   - **Spec/Gate**: specs/11_state_and_events.md, specs/09_validation_gates.md (Gate C)

2. **Failure**: Nondeterministic output detected
   - **Detection**: Running task twice produces different artifact bytes or ordering
   - **Fix**: Review specs/10_determinism_and_caching.md; ensure stable JSON serialization, stable sorting of lists, no timestamps/UUIDs in outputs
   - **Spec/Gate**: specs/10_determinism_and_caching.md, tools/validate_swarm_ready.py (Gate H)

3. **Failure**: Write fence violation (modified files outside allowed_paths)
   - **Detection**: `git status` shows changes outside allowed_paths, or Gate E fails
   - **Fix**: Revert unauthorized changes; if shared library modification needed, escalate to owning taskcard
   - **Spec/Gate**: plans/taskcards/00_TASKCARD_CONTRACT.md (Write fence rule), tools/validate_taskcards.py

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
