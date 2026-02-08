---
id: TC-422
title: "W3.2 Extract code snippets from examples"
status: Done
owner: "W3_AGENT"
updated: "2026-01-28"
depends_on:
  - TC-400
  - TC-410
allowed_paths:
  - src/launch/workers/w3_snippet_curator/extract_code_snippets.py
  - tests/unit/workers/test_tc_422_extract_code_snippets.py
  - reports/agents/**/TC-422/**
evidence_required:
  - reports/agents/<agent>/TC-422/report.md
  - reports/agents/<agent>/TC-422/self_review.md
spec_ref: f48fc5dbb12c5513f42aabc2a90e2b08c6170323
ruleset_version: ruleset.v1
templates_version: templates.v1
---

# Taskcard TC-422 — W3.2 Snippet selection and normalization rules

## Objective
Implement the deterministic selection rules that map snippet candidates to page-plan needs (feature coverage, runnable preference, asset constraints).

## Required spec references
- specs/05_example_curation.md
- specs/06_page_planning.md
- specs/10_determinism_and_caching.md
- specs/schemas/snippet_catalog.schema.json
- specs/schemas/page_plan.schema.json
- specs/schemas/issue.schema.json

## Scope
### In scope
- Rules to pick “best” snippet(s) for a given feature/section deterministically
- Normalization rules for code formatting (indent, fences, language tags)
- Emitting Issues when no suitable snippet exists for a required claim group

### Out of scope
- Writing markdown pages (W5)
- Running snippets (validator gate)

## Inputs
- `RUN_DIR/artifacts/snippet_catalog.json`
- `RUN_DIR/artifacts/page_plan.json` (or planner output) specifying needed features/claims

## Outputs
- Selection mapping artifact (if defined) OR embedded selection fields within page_plan (as per schema)
- Issues for missing snippet coverage

## Allowed paths
- src/launch/workers/w3_snippet_curator/extract_code_snippets.py
- tests/unit/workers/test_tc_422_extract_code_snippets.py
- reports/agents/**/TC-422/**
## Implementation steps
1) Define selection scoring (deterministic tie-breakers):
   - runnable > non-runnable
   - closer feature tag match > broader
   - fewer required assets > more
   - stable tie-breaker by snippet_id
2) Normalize selected snippet presentation (fence + language tag + trimming rules).
3) Record selections with stable ordering.
4) Tests:
   - deterministic selection given equal candidates
   - missing coverage => Issue

## E2E verification
**Concrete command(s) to run:**
```bash
python -m launch.workers.w3_snippet_curator.select --inventory artifacts/snippet_inventory.json
```

**Expected artifacts:**
- artifacts/snippet_catalog.json

**Success criteria:**
- [ ] Selection rules applied
- [ ] Output deterministic

> If E2E harness not yet implemented, this defines the stub contract for TC-520/522/523.

## Integration boundary proven
What upstream/downstream wiring was validated:
- Upstream: TC-421 (snippet inventory)
- Downstream: TC-430 (IAPlanner)
- Contracts: specs/05_example_curation.md selection rules

## Failure modes

### Failure mode 1: Snippet validation fails - syntax errors or incomplete code blocks
**Detection:** Extracted snippets have unclosed brackets; syntax check fails; code blocks incomplete
**Resolution:** Validate snippet syntax; emit WARNING for syntax errors but include snippet with validated=false flag
**Spec/Gate:** specs/03_snippet_curation.md

### Failure mode 2: Snippet tagging is inconsistent or missing required tags
**Detection:** snippet_catalog.json entries missing required tags; tag names not normalized
**Resolution:** Verify all snippets have required tags; normalize tag names; deduplicate snippets
**Spec/Gate:** specs/03_snippet_curation.md, specs/schemas/snippet_catalog.schema.json

### Failure mode 3: Snippet selection exceeds quota or misses critical workflows
**Detection:** snippet_catalog.json has too many snippets; selection algorithm misses high-priority workflows
**Resolution:** Apply selection algorithm from specs; rank snippets by quality; ensure quota enforced
**Spec/Gate:** specs/03_snippet_curation.md, specs/rulesets/ruleset.v1.yaml


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
- Code:
  - selection rules + normalization
- Tests:
  - tie-break determinism tests
- Reports (required):
  - reports/agents/<agent>/TC-422/report.md
  - reports/agents/<agent>/TC-422/self_review.md

## Acceptance checks
- [ ] selection rules are deterministic with stable tie-breakers
- [ ] missing required snippets emits Issues
- [ ] Tests passing

## Self-review
Use `reports/templates/self_review_12d.md`. Any dimension <4 must include a concrete fix plan.
