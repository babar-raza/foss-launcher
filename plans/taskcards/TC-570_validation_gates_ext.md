---
id: TC-570
title: "Validation Gates (schema, links, Hugo smoke, policy)"
status: Done
owner: "W7_AGENT"
updated: "2026-01-28"
depends_on:
  - TC-460
  - TC-550
allowed_paths:
  - src/launch/validators/cli.py
  - src/launch/tools/validate.py
  - src/launch/tools/frontmatter_validate.py
  - src/launch/tools/linkcheck.py
  - src/launch/tools/hugo_smoke.py
  - src/launch/tools/template_token_lint.py
  - tests/unit/tools/test_tc_570_validation.py
  - reports/agents/**/TC-570/**
evidence_required:
  - reports/agents/<agent>/TC-570/report.md
  - reports/agents/<agent>/TC-570/self_review.md
spec_ref: f48fc5dbb12c5513f42aabc2a90e2b08c6170323
ruleset_version: ruleset.v1
templates_version: templates.v1
---

# Taskcard TC-570 — Validation Gates (schema, links, Hugo smoke, policy)

## Objective
Implement the full validation gates runner that blocks merges unless artifacts and content pass required checks.

## Required spec references
- specs/09_validation_gates.md
- specs/18_site_repo_layout.md
- specs/31_hugo_config_awareness.md
- specs/10_determinism_and_caching.md
- specs/12_pr_and_release.md

## Scope
### In scope
- Implement `launch_validate` tool/CLI that runs:
  - schema validation (run_config, artifacts, patches)
  - markdown/frontmatter validation against discovered contract
  - **content_layout_platform gate**: V2 platform path structure validation (NEW)
  - link checks for relative links and internal anchors (best-effort)
  - Hugo build smoke test (best-effort; skip with recorded reason if unavailable)
  - policy check: no manual edits (plans/policies/no_manual_content_edits.md)
- Produce machine-readable and human-readable reports
- Exit non-zero on required gate failure

### Out of scope
- Deep content quality scoring (W7/W8)
- PR creation (W9)

## Inputs
- `RUN_DIR` (artifacts, patches, updated content files)
- `site_context.json` and `hugo_facts.json` (if present)

## Outputs
- `RUN_DIR/artifacts/validation_report.json` (schema: specs/schemas/validation_report.schema.json)
- `RUN_DIR/logs/gate_*.log` (per-gate logs)
- Event: `VALIDATION_COMPLETED`

## Allowed paths

- `src/launch/validators/cli.py`
- `src/launch/tools/validate.py`
- `src/launch/tools/frontmatter_validate.py`
- `src/launch/tools/linkcheck.py`
- `src/launch/tools/hugo_smoke.py`
- `src/launch/tools/template_token_lint.py`
- `tests/unit/tools/test_tc_570_validation.py`
- `reports/agents/**/TC-570/**`## Implementation steps
1) Implement a gate registry with structured results.
2) Schema gate: validate all artifacts via JSON Schema.
3) Frontmatter gate:
   - use discovered contract when available
   - fallback to warnings when contract missing
4) **Platform layout gate** (content_layout_platform):
   - Read resolved `layout_mode` per section from artifacts
   - When V2 detected:
     - Verify non-blog paths contain `/{locale}/{platform}/`
     - Verify blog paths contain `/{platform}/`
     - Verify products use `/{locale}/{platform}/` (NOT `/{platform}/` alone)
     - Check all writes are within `allowed_paths`
     - Lint for unresolved `__PLATFORM__` tokens in generated content
   - Emit BLOCKER issues on violations
   - See specs/32_platform_aware_content_layout.md
5) Link gate:
   - resolve relative links within repo
   - anchor checks best-effort
6) Hugo smoke:
   - use config locations from TC-550 artifact
   - capture logs under RUN_DIR/logs/
7) **TemplateTokenLint gate** (required per specs/19_toolchain_and_ci.md line 172):
   - Scan all newly generated/modified Markdown files for pattern: `__([A-Z0-9]+(?:_[A-Z0-9]+)*)__`
   - Emit BLOCKER if any unresolved tokens remain (e.g., `__PLATFORM__`, `__LOCALE__`)
   - Report file path + line number for each match
   - Run after markdownlint and before Hugo-config/link checks
8) **Gate timeout enforcement** (required per specs/09_validation_gates.md lines 84-120):
   - Implement timeout values per profile (local, ci, prod)
   - On timeout: emit BLOCKER issue with error_code=GATE_TIMEOUT
   - Record which gate timed out in validation_report.json
   - Log timeout events to telemetry with gate name + elapsed time
9) Policy gate:
   - fail on unexplained file edits
10) Write reports (including profile field) and exit accordingly.
11) Add fixtures/tests for pass and fail (including V2 path validation tests, timeout tests, TemplateTokenLint tests).

## E2E verification
**Concrete command(s) to run:**
```bash
# Canonical interface per specs/19_toolchain_and_ci.md
launch_validate --run_dir runs/<run_id> --profile ci
```

**Expected artifacts:**
- `RUN_DIR/artifacts/validation_report.json` - validates against schema
- `RUN_DIR/logs/gate_*.log` - per-gate logs

**Success criteria:**
- [ ] All specified gates run in order per specs/09_validation_gates.md
- [ ] validation_report.json includes profile field matching --profile arg
- [ ] Blocker issues include error_code field per specs/01_system_contract.md
- [ ] Exit code 2 on validation failure, 0 on success
- [ ] Gate timeouts enforced per specs/09_validation_gates.md timeout tables
- [ ] TemplateTokenLint gate runs and detects unresolved tokens (e.g., __PLATFORM__)

> If E2E harness not yet implemented, this defines the stub contract for TC-520/522/523.

## Integration boundary proven
What upstream/downstream wiring was validated:
- Upstream: TC-460 (validator orchestration)
- Downstream: TC-470 (fixer consumes gate failures)
- Contracts: specs/09_validation_gates.md gate definitions

## Failure modes

### Failure mode 1: Gate timeout exceeded but no GATE_TIMEOUT blocker emitted
**Detection:** Gate execution exceeds timeout threshold (e.g., Gate L >60s); validation continues instead of failing; validation_report.json missing GATE_TIMEOUT error_code; no blocker artifact created
**Resolution:** Review timeout enforcement in launch_validate CLI; verify timeout values loaded from specs/09_validation_gates.md timeout tables; ensure timeout handler emits BLOCKER issue with error_code=GATE_TIMEOUT; check that gate name and elapsed time logged to telemetry; test with artificially low timeout
**Spec/Gate:** specs/09_validation_gates.md lines 84-120 (timeout enforcement), specs/01_system_contract.md (error_code contract)

### Failure mode 2: Platform layout gate fails to detect unresolved template tokens in V2 content
**Detection:** Pages with __PLATFORM__ or __LOCALE__ tokens pass validation; broken links or missing pages in generated site; Hugo build fails with template errors
**Resolution:** Review TemplateTokenLint gate implementation; ensure regex pattern matches __[A-Z_]+__ tokens; verify gate scans all .md files in content/ directory; check that V2 layout mode triggers strict token checking; add test case with unresolved __PLATFORM__ in frontmatter and body
**Spec/Gate:** specs/32_platform_aware_content_layout.md (template token contract), specs/09_validation_gates.md (TemplateTokenLint gate definition)

### Failure mode 3: Hugo smoke test gate records SKIP but doesn't verify Hugo availability
**Detection:** Hugo not installed or wrong version; gate skips silently; later stages fail with Hugo errors; no actionable error message
**Resolution:** Review Hugo smoke test gate logic; ensure `hugo version` command executed and version checked against requirements; verify skip reason logged to validation_report with expected_version and actual_version fields; emit WARNING issue when Hugo unavailable (not silent skip); document Hugo version requirement in gate output
**Spec/Gate:** specs/09_validation_gates.md (Hugo smoke test), specs/19_toolchain_and_ci.md (toolchain requirements)

### Failure mode 4: validation_report.json missing profile field causing CI/local behavior divergence
**Detection:** Validation passes locally but fails in CI or vice versa; timeout values differ; no profile field in validation_report.json; unclear which profile was used
**Resolution:** Review launch_validate CLI argument parsing; ensure --profile flag captured and passed to validator; verify profile field written to validation_report.json root level; check that timeout values loaded from correct profile (local/ci/prod) in specs/09_validation_gates.md; validate profile against allowed values (local, ci, prod)
**Spec/Gate:** specs/09_validation_gates.md (profile-based timeouts), specs/11_state_and_events.md (validation_report schema)

## Task-specific review checklist
Beyond the standard acceptance checks, verify:
- [ ] All schema files validate as proper JSON Schema Draft 7
- [ ] Schema validation helpers cover all required artifact types
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
- [ ] Exits non-zero on required gate failure
- [ ] Writes both JSON and MD reports
- [ ] Platform layout gate enforces V2 path structure when layout_mode=v2
- [ ] Platform layout gate verifies products use /{locale}/{platform}/
- [ ] Platform layout gate fails on unresolved __PLATFORM__ tokens
- [ ] Hugo smoke records skip reason when unavailable
- [ ] Policy gate prevents unexplained manual edits

## Self-review
Use `reports/templates/self_review_12d.md`. Any dimension <4 must include a concrete fix plan.
