---
id: TC-440
title: "W5 SectionWriter (draft Markdown with claim markers)"
status: Ready
owner: "unassigned"
updated: "2026-01-22"
depends_on:
  - TC-430
allowed_paths:
  - src/launch/workers/w5_section_writer.py
  - src/launch/workers/_render/**
  - tests/unit/workers/test_tc_440_section_writer.py
  - reports/agents/**/TC-440/**
evidence_required:
  - reports/agents/<agent>/TC-440/report.md
  - reports/agents/<agent>/TC-440/self_review.md
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
- src/launch/workers/w5_section_writer.py
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
