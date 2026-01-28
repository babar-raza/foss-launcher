---
id: TC-440
title: "W5 SectionWriter (draft Markdown with claim markers)"
status: Done
owner: "W5_AGENT"
updated: "2026-01-28"
depends_on:
  - TC-430
allowed_paths:
  - src/launch/workers/w5_section_writer/**
  - src/launch/workers/_render/**
  - tests/unit/workers/test_tc_440_section_writer.py
  - reports/agents/**/TC-440/**
evidence_required:
  - reports/agents/<agent>/TC-440/report.md
  - reports/agents/<agent>/TC-440/self_review.md
spec_ref: f48fc5dbb12c5513f42aabc2a90e2b08c6170323
ruleset_version: ruleset.v1
templates_version: templates.v1
---

# Taskcard TC-440 — W5 SectionWriter (draft Markdown with claim markers)

## Objective
Implement **W5: SectionWriter** to draft Markdown per section, strictly following templates and embedding claim markers for every factual statement.

## Required spec references
- specs/21_worker_contracts.md (W5)
- specs/07_section_templates.md
- specs/20_rulesets_and_templates_registry.md
- specs/23_claim_markers.md
- specs/04_claims_compiler_truth_lock.md
- specs/10_determinism_and_caching.md

## Scope
### In scope
- A generic SectionWriter engine that can write drafts for a given `section` (products/docs/reference/kb/blog)
- Template rendering that:
  - fills all placeholders
  - removes scaffolding tokens (no unresolved `__UPPER_SNAKE__`)
- Claim marker embedding rules for every factual sentence/bullet
- Draft output layout that mirrors `page_plan.pages[].output_path` under `RUN_DIR/drafts/<section>/...`
- Deterministic ordering and stable formatting rules

### Out of scope
- Patching into site worktree (W6)
- Running validation tools (W7)

## Inputs
- `RUN_DIR/artifacts/page_plan.json`
- `RUN_DIR/artifacts/product_facts.json`
- `RUN_DIR/artifacts/evidence_map.json`
- `RUN_DIR/artifacts/snippet_catalog.json`
- Templates under `specs/templates/**` (read-only)

## Outputs
- Draft Markdown files under `RUN_DIR/drafts/<section>/<output_path>`

## Allowed paths
- src/launch/workers/w5_section_writer/**
- src/launch/workers/_render/**
- tests/unit/workers/test_tc_440_section_writer.py
- reports/agents/**/TC-440/**
## Implementation steps
1) Load page_plan and filter pages for the requested section.
2) For each page (deterministic order):
   - load template
   - render frontmatter and body sections
   - insert only snippets allowed by `required_snippet_tags`
   - enforce claim markers on factual statements (per spec)
3) Detect and fail on unresolved placeholders:
   - any `__UPPER_SNAKE__`
   - any `__BODY_*__`
4) Write draft file with stable newline policy (LF) and deterministic whitespace rules.
5) Emit events for each file written (draft writes can emit ARTIFACT_WRITTEN-like events but must be distinguishable from JSON artifacts).

## E2E verification
**Concrete command(s) to run:**
```bash
python -m launch.workers.w5_section_writer --page-plan artifacts/page_plan.json
```

**Expected artifacts:**
- artifacts/draft_sections/*.md (with claim markers)

**Success criteria:**
- [ ] All planned sections written
- [ ] Claim markers present

> If E2E harness not yet implemented, this defines the stub contract for TC-520/522/523.

## Integration boundary proven
What upstream/downstream wiring was validated:
- Upstream: TC-430 (page_plan)
- Downstream: TC-450 (LinkerAndPatcher)
- Contracts: specs/23_claim_markers.md marker format

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
- [ ] Worker emits required events per specs/21_worker_contracts.md
- [ ] Worker outputs validate against declared schemas
- [ ] Worker handles missing/malformed inputs gracefully with blocker artifacts
- [ ] All outputs are written atomically per specs/10_determinism_and_caching.md
- [ ] No manual content edits made (compliance with no_manual_content_edits policy)
- [ ] Determinism verified by running task twice and comparing artifacts byte-for-byte
- [ ] All spec references listed in taskcard were consulted during implementation
- [ ] Evidence files (report.md, self_review.md) include all required sections and command outputs
- [ ] No placeholder values (PIN_ME, TODO, FIXME, etc.) remain in production code paths

## Deliverables
- Code: W5 section writer + template renderer
- Tests:
  - unit tests verifying placeholder removal
  - unit tests verifying claim marker injection
  - golden test for deterministic draft bytes for a small fixture plan
- Reports:
  - reports/agents/<agent>/TC-440/report.md
  - reports/agents/<agent>/TC-440/self_review.md

## Acceptance checks
- [ ] Draft paths match `RUN_DIR/drafts/<section>/<output_path>` exactly
- [ ] No unresolved template tokens remain
- [ ] Claim markers are present for each factual statement
- [ ] Re-run yields byte-identical drafts for the same inputs

## Self-review
Use `reports/templates/self_review_12d.md`.
