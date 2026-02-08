---
id: TC-421
title: "W3.1 Snippet inventory and tagging"
status: Done
owner: "W3_AGENT"
updated: "2026-01-28"
depends_on:
  - TC-400
allowed_paths:
  - src/launch/workers/w3_snippet_curator/extract_doc_snippets.py
  - tests/unit/workers/test_tc_421_extract_doc_snippets.py
  - reports/agents/**/TC-421/**
evidence_required:
  - reports/agents/<agent>/TC-421/report.md
  - reports/agents/<agent>/TC-421/self_review.md
spec_ref: f48fc5dbb12c5513f42aabc2a90e2b08c6170323
ruleset_version: ruleset.v1
templates_version: templates.v1
---

# Taskcard TC-421 — W3.1 Snippet inventory and tagging

## Objective
Generate `snippet_catalog.json` by discovering snippets/examples deterministically and tagging them for later selection.

## Required spec references
- specs/05_example_curation.md
- specs/26_repo_adapters_and_variability.md
- specs/27_universal_repo_handling.md
- specs/10_determinism_and_caching.md
- specs/schemas/snippet_catalog.schema.json
- specs/schemas/issue.schema.json

## Scope
### In scope
- Deterministic discovery of snippet candidates (examples/, samples/, docs code blocks, etc.)
- Tagging rules:
  - language
  - feature area
  - requires_assets (yes/no)
  - runnable (yes/no)
- Stable ordering and stable IDs

### Out of scope
- Selecting snippets for specific pages (TC-422)
- Running snippets (validator optional gate)

## Inputs
- `RUN_DIR/work/repo` + repo profile/adapters
- Optional repo_hints.preferred_examples_roots

## Outputs
- `RUN_DIR/artifacts/snippet_catalog.json` (schema-valid)
- Issues for:
  - unreadable/unsupported files
  - ambiguous language detection

## Allowed paths
- src/launch/workers/w3_snippet_curator/extract_doc_snippets.py
- tests/unit/workers/test_tc_421_extract_doc_snippets.py
- reports/agents/**/TC-421/**
## Implementation steps
1) Enumerate candidate paths deterministically (sorted).
2) Extract code blocks/snippet files, normalize line endings, and classify language.
3) Generate stable snippet IDs (hash of normalized content + source locator).
4) Tag snippets using deterministic heuristics; record unknown tags explicitly.
5) Validate schema and write artifact atomically.
6) Tests:
   - stable ID generation test
   - deterministic ordering test

## E2E verification
**Concrete command(s) to run:**
```bash
python -m launch.workers.w3_snippet_curator.inventory --repo-dir workdir/repos/<sha>
```

**Expected artifacts:**
- artifacts/snippet_inventory.json

**Success criteria:**
- [ ] All code examples found
- [ ] Deterministic ordering

> If E2E harness not yet implemented, this defines the stub contract for TC-520/522/523.

## Integration boundary proven
What upstream/downstream wiring was validated:
- Upstream: TC-401 (cloned repo)
- Downstream: TC-422 (selection rules)
- Contracts: snippet_catalog.schema.json inventory fields

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
  - snippet inventory + tagging
- Tests:
  - determinism tests
- Reports (required):
  - reports/agents/<agent>/TC-421/report.md
  - reports/agents/<agent>/TC-421/self_review.md

## Acceptance checks
- [ ] snippet_catalog validates against schema
- [ ] snippet IDs stable across runs
- [ ] tagging is deterministic and documented
- [ ] Tests passing

## Self-review
Use `reports/templates/self_review_12d.md`. Any dimension <4 must include a concrete fix plan.
