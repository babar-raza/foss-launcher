---
id: TC-590
title: "Security and Secrets Handling (redaction + lightweight scan)"
status: Ready
owner: "unassigned"
updated: "2026-01-22"
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

## Deliverables
- Code + tests
- Report and self review under repo-root reports/

## Acceptance checks
- [ ] No tool prints raw secrets
- [ ] Redaction occurs before write
- [ ] Scan report contains file paths and counts only

## Self-review
Use `reports/templates/self_review_12d.md`. Any dimension <4 must include a concrete fix plan.
