---
id: TC-570
title: "Validation Gates (schema, links, Hugo smoke, policy)"
status: Ready
owner: "unassigned"
updated: "2026-01-22"
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
- src/launch/validators/cli.py
- src/launch/tools/validate.py
- src/launch/tools/frontmatter_validate.py
- src/launch/tools/linkcheck.py
- src/launch/tools/hugo_smoke.py
- src/launch/tools/template_token_lint.py
- tests/unit/tools/test_tc_570_validation.py
- reports/agents/**/TC-570/**
## Implementation steps
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
