---
id: TC-3778
title: "Linker integration into Generate worker"
status: In-Progress
priority: Normal
owner: "agent-b"
updated: "2026-03-07"
tags: [generate, linker, cross-links, see-also]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-3778_linker_integration.md
  - src/launcher/shared/linker.py
  - src/launcher/models/content.py
  - src/launcher/workers/generate/worker.py
  - configs/pipeline.yaml
  - specs/schemas/content_manifest.schema.json
  - tests/test_linker.py
  - reports/agents/B/TC-3778/evidence.md
evidence_required:
  - reports/agents/B/TC-3778/evidence.md
---

# Taskcard TC-3778 — Linker integration into Generate worker

## Objective

Port v1's cross-page linking capabilities into v2's Generate worker as a
post-generation, pre-render linking pass. Uses deterministic scoring for link
selection and an LLM sandwich for natural anchor text, with title fallback.

## Required spec references

- `specs/21_worker_contracts.md` (Section: Generate worker I/O contract)
- `specs/schemas/content_manifest.schema.json` (CrossLink schema)
- `specs/templates/` (SECTION_SUBDOMAIN_MAP for URL resolution)

## Scope

### In scope
- New `src/launcher/shared/linker.py` module (scoring, injection, absolutization)
- Hybrid sandwich for anchor text (LLM + deterministic fallback)
- CrossLink model extension (url, link_type fields)
- Generate worker 3-phase refactor (generate → link → render)
- Pipeline config for linker tuning knobs
- Schema update for new CrossLink fields
- Unit + integration tests
- Self-review check additions

### Out of scope
- Patch engine (v2 creates files fresh, no patching)
- Navigation file generation (Publish concern)
- Inline links within paragraph prose (only See Also sections)
- Gate changes (existing gates should pass)

## Inputs

- `PlanBundle` (list of PlannedPage with assigned_claims, frontmatter URLs)
- `UnderstandingBundle` (product, claims, snippets)
- `SECTION_SUBDOMAIN_MAP` from template_loader.py

## Outputs

- Modified `PageIR` objects with See Also sections injected
- `ContentManifest.cross_links` populated with url and link_type
- Rendered `.md` files with See Also links in markdown

## Allowed paths

- plans/taskcards/TC-3778_linker_integration.md
- src/launcher/shared/linker.py
- src/launcher/models/content.py
- src/launcher/workers/generate/worker.py
- configs/pipeline.yaml
- specs/schemas/content_manifest.schema.json
- tests/test_linker.py
- reports/agents/B/TC-3778/evidence.md

### Allowed paths rationale
- linker.py: new module for linking logic
- content.py: CrossLink model needs url + link_type fields
- worker.py: refactor from 1-phase to 3-phase flow
- pipeline.yaml: linker config knobs
- schema: must match pydantic model
- tests: verification
- evidence: orchestrator requirement

## Implementation steps

### Step 1: Create src/launcher/shared/linker.py

Core linking module with:
- PageEntry, LinkerConfig, ScoredLink dataclasses
- build_page_index() — page_id to PageEntry lookup
- score_links() — Jaccard + cross-section bonus + role affinity
- generate_anchor_texts() — LLM sandwich with title fallback
- inject_links() — See Also SectionIR creation/append
- absolutize_urls() — cross-subdomain URL resolution
- link_pages() — async orchestrator

### Step 2: Extend CrossLink model

Add `url: str = ""` and `link_type: str = "see_also"` to CrossLink.

### Step 3: Refactor Generate worker

Change run() to 3-phase: generate all PageIRs → link_pages() → render+write.
Remove _build_cross_links().

### Step 4: Pipeline config

Add `linker:` section to configs/pipeline.yaml.

### Step 5: Schema update

Add url and link_type to cross_links in content_manifest.schema.json.

### Step 6: Tests

Write tests/test_linker.py with 12 test cases covering scoring,
injection, absolutization, fallback, and end-to-end.

### Step 7: Self-review additions

Add checks to worker self_review(): non-TOC pages with >=3 claims have
cross-links; no broken cross-links.

## Failure modes

### Failure mode 1: LLM anchor text call fails

**Detection**: generate_anchor_texts returns with empty anchor_text
**Resolution**: Deterministic fallback uses target page title as anchor text
**Gate**: No gate impact — fallback always produces valid links

### Failure mode 2: Zero links scored above threshold

**Detection**: score_links returns empty list for a page
**Resolution**: This is valid — not every page needs See Also links. No action needed.
**Gate**: Self-review only flags pages with >=3 claims and zero links

### Failure mode 3: Cross-subdomain URL resolution fails

**Detection**: SECTION_SUBDOMAIN_MAP missing section key
**Resolution**: Default to relative URL (same as same-subdomain behavior)
**Gate**: Gate 5 cross-page link validity would catch broken URLs

## Task-specific review checklist

1. [ ] linker.py has no I/O side effects (pure functions except LLM call)
2. [ ] Scoring is deterministic (same input → same output, PYTHONHASHSEED=0)
3. [ ] TOC pages are excluded from See Also injection
4. [ ] Anchor text validation rejects URLs/markdown/excessive length
5. [ ] Cross-subdomain links use absolute URLs
6. [ ] Same-subdomain links use relative URLs
7. [ ] Existing tests still pass after worker.py refactor
8. [ ] Schema matches pydantic model exactly

## Deliverables

1. `src/launcher/shared/linker.py` — core linking module
2. `tests/test_linker.py` — 12 test cases
3. Updated `src/launcher/models/content.py`
4. Updated `src/launcher/workers/generate/worker.py`
5. Updated `configs/pipeline.yaml`
6. Updated `specs/schemas/content_manifest.schema.json`
7. `reports/agents/B/TC-3778/evidence.md`

## Acceptance checks

1. [ ] All 12 linker tests pass
2. [ ] Existing test suite passes (no regressions)
3. [ ] CrossLink model has url and link_type fields
4. [ ] Schema validates with new fields
5. [ ] worker.py uses 3-phase flow
6. [ ] linker.py importable without errors

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: schema PASS
- [ ] Evidence captured: reports/agents/B/TC-3778/evidence.md

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/test_linker.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -v --tb=short
```

**Expected results**:
- All linker tests pass
- No regressions in existing tests
- CrossLink model serializes with url and link_type

## Integration boundary proven

**Upstream**: Planner worker provides PlanBundle with assigned_claims and frontmatter URLs
**Downstream**: Evaluate worker receives ContentManifest with populated cross_links
**Contract**: content_manifest.schema.json with url and link_type in cross_links items
