---
id: TC-580
title: "Observability and Evidence Packaging (reports index + evidence zip)"
status: Done
owner: "OBSERVABILITY_AGENT"
updated: "2026-01-28"
depends_on:
  - TC-300
  - TC-460
allowed_paths:
  - src/launch/tools/evidence_bundle.py
  - src/launch/tools/report_index.py
  - tests/unit/tools/test_tc_580_evidence_bundle.py
  - reports/agents/**/TC-580/**
evidence_required:
  - reports/agents/<agent>/TC-580/report.md
  - reports/agents/<agent>/TC-580/self_review.md
spec_ref: f48fc5dbb12c5513f42aabc2a90e2b08c6170323
ruleset_version: ruleset.v1
templates_version: templates.v1
---

# Taskcard TC-580 — Observability and Evidence Packaging (reports index + evidence zip)

## Objective
Standardize run-time reporting and create an evidence bundle that reviewers can inspect without rerunning the system.

## Required spec references
- specs/11_state_and_events.md
- specs/16_local_telemetry_api.md
- specs/09_validation_gates.md
- specs/28_coordination_and_handoffs.md

## Scope
### In scope
- Standardize `RUN_DIR/reports/`:
  - `RUN_DIR/reports/INDEX.md`
  - `RUN_DIR/reports/summary.json`
- Implement evidence bundler:
  - `RUN_DIR/evidence_bundle.zip`
  - deterministic zip ordering
  - excludes secrets and caches
- Integrate helper into orchestrator end-of-run

### Out of scope
- _None._

## Inputs
- `RUN_DIR` with artifacts/logs/reports

## Outputs
- `RUN_DIR/reports/INDEX.md`
- `RUN_DIR/evidence_bundle.zip`
- Event: `EVIDENCE_BUNDLE_WRITTEN`

## Allowed paths

- `src/launch/tools/evidence_bundle.py`
- `src/launch/tools/report_index.py`
- `tests/unit/tools/test_tc_580_evidence_bundle.py`
- `reports/agents/**/TC-580/**`## Implementation steps
1) Define index format and required links to artifacts and gate reports.
2) Implement `build_report_index(RUN_DIR)`.
3) Build evidence zip with deterministic ordering and allowlist selection.
4) Add tests for deterministic content list and secret exclusion.

## E2E verification
**Concrete command(s) to run:**
```bash
python -m launch.observability.package --run-id test_run --output evidence_bundle.zip
```

**Expected artifacts:**
- evidence_bundle.zip (contains all run artifacts)
- artifacts/reports_index.json

**Success criteria:**
- [ ] Bundle created
- [ ] All artifacts included

> If E2E harness not yet implemented, this defines the stub contract for TC-520/522/523.

## Integration boundary proven
What upstream/downstream wiring was validated:
- Upstream: TC-300 (run completion)
- Downstream: Audit trail, debugging
- Contracts: specs/11_state_and_events.md evidence requirements

## Failure modes

### Failure mode 1: Evidence bundle includes secrets or sensitive data
**Detection:** Gate L (secrets scan) fails on evidence.zip; API tokens, credentials, or PII found in bundled logs or artifacts; security audit flags leaked secrets
**Resolution:** Review bundle_evidence() implementation; ensure Gate L (secrets scan) runs BEFORE bundling; verify .env files, credential JSON, and API keys excluded from bundle; check that redaction applied to logs with sensitive patterns; integrate TC-590 secret detection; add pre-bundle scan with explicit secret exclusion patterns
**Spec/Gate:** specs/09_validation_gates.md (Gate L secrets), TC-590 (security and secrets), specs/34_strict_compliance_guarantees.md (Guarantee J: secret hygiene)

### Failure mode 2: Evidence zip has non-deterministic file ordering breaking reproducibility
**Detection:** Gate H (determinism) fails; evidence.zip SHA256 differs across runs with identical content; zip file listing shows unstable ordering
**Resolution:** Review zip creation logic; ensure sorted() applied to file list before adding to archive; verify zipfile.ZipFile uses deterministic compression settings; set fixed timestamps for zip entries (e.g., 1980-01-01) to avoid timestamp variation; test with identical inputs producing identical zip bytes
**Spec/Gate:** specs/10_determinism_and_caching.md (stable artifacts), Gate H (determinism validation)

### Failure mode 3: INDEX.md contains broken links to artifacts due to wrong relative path construction
**Detection:** INDEX.md links return 404 when opened; relative paths incorrect; artifacts exist but not navigable from index
**Resolution:** Review INDEX.md generation in bundle script; verify relative paths constructed from RUN_DIR root; ensure links use forward slashes (Posix paths) even on Windows; test path construction with nested directories; validate all links with path.exists() check before writing INDEX.md; document expected RUN_DIR structure
**Spec/Gate:** specs/11_state_and_events.md (evidence structure), specs/10_determinism_and_caching.md (path normalization)

### Failure mode 4: Evidence bundle creation fails silently when disk quota exceeded
**Detection:** Partial evidence.zip created; missing artifacts; no error message; run appears successful but evidence incomplete
**Resolution:** Add disk space check before creating bundle; verify zipfile.ZipFile raises exception on write failure and don't suppress; log bundle size and artifact count; emit WARNING issue if bundle exceeds size threshold (e.g., >500MB); include bundle creation status in validation_report.json with success=true/false and error_message if failed
**Spec/Gate:** specs/11_state_and_events.md (evidence artifacts), specs/09_validation_gates.md (validation report completeness)

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
- [ ] Evidence zip produced with deterministic ordering
- [ ] INDEX.md contains direct relative links to top artifacts/reports
- [ ] No secrets included (TC-590)

## Self-review
Use `reports/templates/self_review_12d.md`. Any dimension <4 must include a concrete fix plan.
