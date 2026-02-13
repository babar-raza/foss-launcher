---
id: TC-1204
title: "Page Expansion — W4 Feature Sub-Page Generation"
status: Draft
priority: High
owner: "Agent B (Backend/Workers)"
updated: "2026-02-11"
tags: ["w4", "sub-pages", "page-expansion", "phase-2"]
depends_on: ["TC-1200", "TC-1203"]
allowed_paths:
  - plans/taskcards/TC-1204_w4_feature_sub_pages.md
  - src/launch/workers/w4_ia_planner/worker.py
  - tests/unit/workers/test_w4_sub_pages.py
evidence_required:
  - reports/agents/AGENT_B/TC-1204/evidence.md
  - reports/agents/AGENT_B/TC-1204/self_review.md
spec_ref: "33242628c6242b03c2c83a5e978f73d5155f247a"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# Taskcard TC-1204 — Page Expansion — W4 Feature Sub-Page Generation

## Objective
Implement the feature sub-page model in W4 so that each qualifying feature page in the docs section can spawn up to N child sub-pages (overview, quickstart, examples, troubleshooting), dramatically expanding the docs section page count with richly-focused content.

## Required spec references
- specs/06_page_planning.md (updated by TC-1200 — sub-page model definition)
- specs/schemas/page_plan.schema.json (updated by TC-1200 — `sub_pages`, `parent_page` fields)
- specs/schemas/run_config.schema.json (updated by TC-1200 — `page_expansion.max_feature_sub_pages`)
- src/launch/workers/w4_ia_planner/worker.py (current W4 — page planning pipeline)

## Scope

### In scope
1. **Sub-page eligibility check** — A feature page qualifies for sub-pages when:
   - It is in the `docs` section with `page_role` in (`workflow_page`, `format_conversion`, `tutorial`)
   - It has `claim_count >= 3` AND `snippet_count >= 1`
   - `page_expansion.max_feature_sub_pages > 0` in run_config
2. **Sub-page generation function** — New `generate_feature_sub_pages()`:
   - Up to `max_feature_sub_pages` sub-pages per parent (default 4, configurable 0-6)
   - Sub-page types (in priority order):
     1. `overview` — Feature overview (always generated if eligible)
     2. `quickstart` — Minimal getting-started (requires snippets)
     3. `examples` — Multiple code samples (requires 2+ snippets)
     4. `troubleshooting` — Feature-specific issues (requires limitation claims)
   - Each sub-page gets its own `page_role`, `content_strategy`, `parent_page` reference
3. **URL structure** — Sub-pages nest under parent:
   - Parent: `/{family}/docs/developer-guide/{feature}/`
   - Sub-pages: `/{family}/docs/developer-guide/{feature}/overview/`, `.../quickstart/`, etc.
4. **Parent-child linking** — Parent page gets `sub_pages: [...]` array, sub-pages get `parent_page: "{parent_slug}"`
5. **Quota awareness** — Sub-pages count toward section max_pages. Stop generating if quota exhausted.
6. **Unit tests** — Coverage for eligibility, generation, quota capping, URL structure

### Out of scope
- W5 content generation for sub-pages (TC-1206)
- Templates for sub-pages (TC-1205)
- New policy sources (TC-1203 — sub-pages are generated from EXISTING feature pages, not from policies)

## Inputs
- Page plan (after mandatory + optional page generation from TC-1203)
- product_facts.json (claims, snippets for eligibility check)
- run_config (page_expansion.max_feature_sub_pages)

## Outputs
- src/launch/workers/w4_ia_planner/worker.py (UPDATED — +200 lines: sub-page generation)
- tests/unit/workers/test_w4_sub_pages.py (NEW — ~150 lines)

## Allowed paths
- plans/taskcards/TC-1204_w4_feature_sub_pages.md
- src/launch/workers/w4_ia_planner/worker.py
- tests/unit/workers/test_w4_sub_pages.py

### Allowed paths rationale
W4 worker only. Sub-page generation is a post-processing step after the main page plan is built.

## Implementation steps

### Step 1: Read current W4 pipeline flow
Understand where sub-page generation should be inserted. It must run AFTER:
- Mandatory page injection
- Optional page generation (TC-1203)
- BEFORE: Cross-link population, collision detection

**Resilience note**: Look for comments or function calls marking the pipeline stages. Insert sub-page generation as a new stage between optional page generation and cross-linking.

### Step 2: Implement eligibility check function
```python
def is_eligible_for_sub_pages(
    page: Dict[str, Any],
    product_facts: Dict[str, Any],
    max_sub_pages: int,
) -> bool:
    """Check if a page qualifies for sub-page expansion."""
    if max_sub_pages <= 0:
        return False
    if page.get("section") != "docs":
        return False
    eligible_roles = {"workflow_page", "format_conversion", "tutorial"}
    if page.get("page_role") not in eligible_roles:
        return False
    claim_count = len(page.get("required_claim_ids", []))
    snippet_count = len(page.get("required_snippet_tags", []))
    return claim_count >= 3 and snippet_count >= 1
```

### Step 3: Implement `generate_feature_sub_pages()`
```python
def generate_feature_sub_pages(
    parent_page: Dict[str, Any],
    product_facts: Dict[str, Any],
    snippet_catalog: Dict[str, Any],
    max_sub_pages: int,
) -> List[Dict[str, Any]]:
    """Generate up to max_sub_pages child sub-pages for a feature page."""
    sub_pages = []
    parent_slug = parent_page["slug"]
    parent_claims = parent_page.get("required_claim_ids", [])
    parent_snippets = parent_page.get("required_snippet_tags", [])

    # 1. Overview (always if eligible)
    if len(sub_pages) < max_sub_pages:
        sub_pages.append(_build_sub_page(parent_slug, "overview", ...))

    # 2. Quickstart (requires snippets)
    if len(sub_pages) < max_sub_pages and parent_snippets:
        sub_pages.append(_build_sub_page(parent_slug, "quickstart", ...))

    # 3. Examples (requires 2+ snippets)
    if len(sub_pages) < max_sub_pages and len(parent_snippets) >= 2:
        sub_pages.append(_build_sub_page(parent_slug, "examples", ...))

    # 4. Troubleshooting (requires limitation claims)
    limitation_claims = [c for c in parent_claims if _is_limitation_claim(c, product_facts)]
    if len(sub_pages) < max_sub_pages and limitation_claims:
        sub_pages.append(_build_sub_page(parent_slug, "troubleshooting", ...))

    return sub_pages
```

### Step 4: Implement `_build_sub_page()` helper
Constructs a page plan entry for a sub-page:
- `slug`: `{parent_slug}/{sub_type}` (e.g., `model-loading/quickstart`)
- `url_path`: `/{family}/docs/developer-guide/{parent_slug}/{sub_type}/`
- `output_path`: follows content path resolver pattern
- `page_role`: maps sub_type → role (overview→`landing`, quickstart→`workflow_page`, examples→`example_walkthrough`, troubleshooting→`troubleshooting`)
- `parent_page`: parent_slug
- `content_strategy`: sub-type-specific focus and forbidden topics
- `required_claim_ids`: subset of parent's claims relevant to this sub-type
- `required_snippet_tags`: subset of parent's snippets

### Step 5: Integrate into W4 pipeline
After optional page generation, before cross-links:

```python
# Sub-page expansion
page_expansion_config = run_config.get("page_expansion", {})
max_sub_pages = page_expansion_config.get("max_feature_sub_pages", 4)
remaining_quota = effective_max - len(all_pages)

if max_sub_pages > 0 and remaining_quota > 0:
    new_sub_pages = []
    for page in list(all_pages):  # Iterate copy to avoid mutation during loop
        if not is_eligible_for_sub_pages(page, product_facts, max_sub_pages):
            continue
        if remaining_quota <= 0:
            break
        subs = generate_feature_sub_pages(page, product_facts, snippet_catalog, max_sub_pages)
        # Cap to remaining quota
        subs = subs[:remaining_quota]
        # Link parent → children
        page["sub_pages"] = [s["slug"] for s in subs]
        new_sub_pages.extend(subs)
        remaining_quota -= len(subs)
    all_pages.extend(new_sub_pages)
    logger.info(f"[W4] Generated {len(new_sub_pages)} sub-pages for {len([p for p in all_pages if p.get('sub_pages')])} parent features")
```

### Step 6: Write unit tests
Create `tests/unit/workers/test_w4_sub_pages.py`:

1. **test_eligibility_docs_workflow_page** — Eligible page → True
2. **test_eligibility_non_docs** — KB page → False
3. **test_eligibility_insufficient_claims** — 1 claim → False
4. **test_eligibility_disabled** — max_sub_pages=0 → False
5. **test_generate_all_four_sub_types** — Full evidence → 4 sub-pages
6. **test_generate_limited_by_max** — max_sub_pages=2 → only overview + quickstart
7. **test_generate_no_snippets** — No snippets → only overview (no quickstart/examples)
8. **test_sub_page_url_structure** — Verify nested URL pattern
9. **test_sub_page_parent_link** — Verify parent_page field set
10. **test_quota_capping** — remaining_quota=2, 3 eligible parents → only first parent gets sub-pages until quota exhausted
11. **test_deterministic_output** — Run twice → identical results

### Step 7: Run tests
```bash
.venv/Scripts/python.exe -m pytest tests/unit/workers/test_w4_sub_pages.py -v
.venv/Scripts/python.exe -m pytest tests/unit/workers/ -k "w4" -v  # regression
```

## Failure modes

### Failure mode 1: Sub-page URLs collide with existing pages
**Detection:** Collision detection (already in W4) flags duplicate URLs after sub-page generation.
**Resolution:** Sub-pages always nest under `{parent_slug}/` so they cannot collide with top-level pages unless a top-level page has the same nested path. The collision detector runs AFTER sub-page generation.
**Spec/Gate:** specs/06 collision detection, URL uniqueness rule

### Failure mode 2: Quota overflow — sub-pages push total beyond max_pages
**Detection:** Page count exceeds section max_pages after sub-page expansion.
**Resolution:** The implementation caps at `remaining_quota`. This is calculated as `effective_max - len(all_pages)` before sub-page generation starts.
**Spec/Gate:** specs/08 quota enforcement rules

### Failure mode 3: Parent page has no claims after claim deduplication
**Detection:** A page that was eligible pre-dedup becomes ineligible post-dedup because claims were reassigned.
**Resolution:** Sub-page generation runs BEFORE claim deduplication. The eligibility check uses the page's `required_claim_ids` which are assigned during page planning, not after dedup.
**Spec/Gate:** specs/08 claim deduplication ordering

## Task-specific review checklist
1. [ ] Eligibility check covers section, role, claim_count, snippet_count, and config
2. [ ] 4 sub-page types implemented in priority order
3. [ ] Sub-page URLs nest correctly under parent
4. [ ] parent_page and sub_pages linkage is bidirectional
5. [ ] Quota capping prevents overflow
6. [ ] max_feature_sub_pages=0 completely disables sub-page generation
7. [ ] Each sub-page gets appropriate page_role and content_strategy
8. [ ] Claim/snippet subsets are disjoint across sub-pages (no duplication)
9. [ ] Pipeline insertion point is after optional pages, before cross-links
10. [ ] 11+ unit tests covering all paths

## Deliverables
- src/launch/workers/w4_ia_planner/worker.py (UPDATED — +200 lines)
- tests/unit/workers/test_w4_sub_pages.py (NEW — ~150 lines)
- reports/agents/AGENT_B/TC-1204/evidence.md
- reports/agents/AGENT_B/TC-1204/self_review.md

## Acceptance checks
1. [ ] Sub-page generation works for eligible feature pages
2. [ ] Config disabling (max=0) prevents all sub-pages
3. [ ] Quota capping works correctly
4. [ ] URL structure is correct (nested under parent)
5. [ ] All tests pass
6. [ ] Existing W4 tests pass (no regression)
7. [ ] Deterministic output

## Preconditions / dependencies
- TC-1200 completed (sub-page model spec)
- TC-1203 completed (optional pages generated — sub-pages expand from those)

## Self-review
[To be completed by Agent B after implementation]
