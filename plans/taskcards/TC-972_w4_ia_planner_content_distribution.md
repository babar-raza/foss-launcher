---
id: TC-972
title: "W4 IAPlanner - Content Distribution Implementation"
status: Ready
priority: Critical
owner: "Agent B (Backend/Workers)"
updated: "2026-02-04"
tags: ["w4", "ia-planner", "content-distribution", "phase-2"]
depends_on: ["TC-971"]
allowed_paths:
  - plans/taskcards/TC-972_w4_ia_planner_content_distribution.md
  - src/launch/workers/w4_ia_planner/worker.py
  - tests/unit/workers/test_w4_content_distribution.py
evidence_required:
  - reports/agents/AGENT_B/TC-972/evidence.md
  - reports/agents/AGENT_B/TC-972/self_review.md
spec_ref: "3e91498d6b9dbda85744df6bf8d5f3774ca39c60"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# Taskcard TC-972 — W4 IAPlanner - Content Distribution Implementation

## Objective
Implement content distribution strategy in W4 IAPlanner worker to create missing pages (docs TOC, developer-guide, KB feature showcases), assign page roles, and populate content strategy fields for all pages.

## Problem Statement
W4 IAPlanner currently lacks the logic to:
1. Create docs/_index.md as table of contents (page_role: "toc")
2. Create docs/developer-guide/_index.md as comprehensive guide (page_role: "comprehensive_guide")
3. Create KB feature showcase articles (page_role: "feature_showcase") - currently KB is troubleshooting-only
4. Assign page_role field to all pages
5. Build content_strategy object with primary_focus, forbidden_topics, claim_quota, child_pages
6. Populate child_pages array for TOC pages

This causes three of the five critical gaps in the content distribution strategy.

## Required spec references
- C:\Users\prora\.claude\plans\magical-prancing-fountain.md (Primary implementation plan, Phase 2 Tasks 2.1-2.4)
- specs/08_content_distribution_strategy.md (NEW spec from TC-971 - defines distribution rules)
- specs/06_page_planning.md (Updated by TC-971 - defines page roles and content strategies)
- specs/schemas/page_plan.schema.json (Updated by TC-971 - schema with page_role and content_strategy fields)
- src/launch/workers/w4_ia_planner/worker.py (Current W4 implementation)
- specs/rulesets/ruleset.v1.yaml (Section quotas and style rules)
- CONTRIBUTING.md (Repo governance - no manual edits, .venv policy, validation requirements)

## Scope

### In scope
- Add helper functions: assign_page_role(), build_content_strategy() (~80 lines)
- Modify docs section planning to create 3 pages: TOC + getting-started + developer-guide (~100 lines)
- Modify KB section planning to create 2-3 feature showcases + 1-2 troubleshooting (~80 lines)
- Add post-processing to populate child_pages for TOC pages (~20 lines)
- Remove individual workflow pages (replaced by single comprehensive developer-guide)
- All pages get page_role and content_strategy fields
- Unit tests for new functions and modified planning logic (~150 lines)
- Integration test verifying page_plan.json has new fields

### Out of scope
- W5 SectionWriter modifications (covered by TC-973)
- W7 Validator Gate 14 implementation (covered by TC-974)
- Template creation (covered by TC-975)
- Spec/schema creation (covered by TC-971)
- Modification of existing pilot configurations
- Products or blog section changes (already compliant)

## Inputs
- specs/08_content_distribution_strategy.md (from TC-971)
- specs/06_page_planning.md (updated by TC-971)
- specs/schemas/page_plan.schema.json (updated by TC-971)
- src/launch/workers/w4_ia_planner/worker.py (current implementation)
- product_facts.json (workflows array for developer-guide)
- snippet_catalog.json (snippets for feature selection)
- ruleset.v1.yaml (section quotas)

## Outputs
- src/launch/workers/w4_ia_planner/worker.py (modified, +280 lines net)
- tests/unit/workers/test_w4_content_distribution.py (NEW, ~150 lines)
- page_plan.json artifacts with page_role and content_strategy fields for all pages
- Evidence showing deterministic page role assignment
- Git diff showing modifications
- Test coverage report showing ≥85% coverage for new code

## Allowed paths
- plans/taskcards/TC-972_w4_ia_planner_content_distribution.md
- src/launch/workers/w4_ia_planner/worker.py
- tests/unit/workers/test_w4_content_distribution.py

### Allowed paths rationale
TC-972 implements the W4 IAPlanner changes for content distribution. All changes are in worker code and tests. No specs, schemas, or templates modified (those are handled by TC-971 and TC-975).

## Implementation steps

### Step 1: Add helper function assign_page_role()
Add new function after imports (around line 80) to assign page role based on section and slug.

**Function signature:**
```python
def assign_page_role(section: str, slug: str, is_index: bool = False) -> str:
    """Assign page role based on section, slug, and type.

    Implements content distribution strategy from specs/08_content_distribution_strategy.md.

    Returns: Page role string (landing, toc, comprehensive_guide, workflow_page,
             feature_showcase, troubleshooting, api_reference)
    """
```

**Logic:**
- if is_index and section == "docs" → "toc"
- if slug == "developer-guide" or slug.endswith("/developer-guide") → "comprehensive_guide"
- if slug in ["overview", "index", "_index"] and section == "products" → "landing"
- if section == "docs" → "workflow_page"
- if section == "kb" and ("how-to" in slug or "showcase" in slug) → "feature_showcase"
- if section == "kb" → "troubleshooting"
- if section == "reference" → "api_reference"
- if section == "blog" → "landing"
- else → "landing"

**Acceptance:** Function returns correct role for all 7 role types, deterministic

### Step 2: Add helper function build_content_strategy()
Add new function after assign_page_role() to build content_strategy object.

**Function signature:**
```python
def build_content_strategy(
    page_role: str,
    section: str,
    workflows: List[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build content distribution strategy based on page role.

    Implements content strategy rules from specs/08_content_distribution_strategy.md.

    Returns: Content strategy dictionary with primary_focus, forbidden_topics,
             claim_quota (min/max), child_pages (for toc), scenario_coverage (for comprehensive_guide)
    """
```

**Strategy rules by role:**
- **landing (products)**: focus="Product positioning", forbidden=["detailed_api", "troubleshooting"], quota={min:5, max:10}
- **toc**: focus="Navigation hub", forbidden=["duplicate_child_content", "code_snippets"], quota={min:0, max:2}, child_pages=[]
- **comprehensive_guide**: focus="All usage scenarios", forbidden=["installation", "troubleshooting"], quota={min:len(workflows), max:50}, scenario_coverage="all"
- **workflow_page**: focus="How-to guide", forbidden=["other_workflows"], quota={min:3, max:8}
- **feature_showcase**: focus="Prominent feature how-to", forbidden=["general_features", "api_reference", "other_features"], quota={min:3, max:8}
- **troubleshooting**: focus="Problem-solution", forbidden=["features", "installation"], quota={min:1, max:5}
- **landing (blog)**: focus="Synthesized overview", forbidden=[], quota={min:10, max:20}

**Acceptance:** Function returns correct strategy for all 7 roles, quota values match specs

### Step 3: Modify docs section planning
Replace lines 562-608 (current docs planning) with new implementation creating 3 pages.

**New pages:**
1. **TOC (_index.md)**:
   - page_role = assign_page_role("docs", "_index", is_index=True) → "toc"
   - content_strategy = build_content_strategy("toc", "docs", workflows)
   - title = "{product_name} Documentation"
   - purpose = "Table of contents and navigation hub"
   - required_headings = ["Introduction", "Documentation Index", "Quick Links"]
   - required_claim_ids = claims[:2] (brief intro only)
   - required_snippet_tags = [] (no code on TOC)

2. **Getting Started (getting-started/_index.md)**:
   - page_role = assign_page_role("docs", "getting-started") → "workflow_page"
   - content_strategy = build_content_strategy("workflow_page", "docs", workflows)
   - title = "Getting Started"
   - purpose = "Installation instructions and first task guide"
   - required_headings = ["Installation", "Basic Usage", "Prerequisites", "Next Steps"]
   - required_claim_ids = [c for c in claims if c.get("claim_group") in ["install_steps", "quickstart_steps"]][:5]
   - required_snippet_tags = snippet_tags[:1] (first quickstart snippet)

3. **Developer Guide (developer-guide/_index.md)** - NEW:
   - page_role = assign_page_role("docs", "developer-guide") → "comprehensive_guide"
   - content_strategy = build_content_strategy("comprehensive_guide", "docs", workflows)
   - title = "Developer Guide - All Usage Scenarios"
   - purpose = "Comprehensive listing of all major usage scenarios with source code"
   - required_headings = ["Introduction", "Common Scenarios", "Advanced Scenarios", "Additional Resources"]
   - required_claim_ids = [one claim per workflow from workflows array]
   - required_snippet_tags = sorted(set(all snippet tags))

**Remove:** Individual workflow pages (per user requirement for single comprehensive page)

**Acceptance:** Docs section creates exactly 3 pages, all have page_role and content_strategy

### Step 4: Modify KB section planning
Replace lines 653-701 (current KB planning) with new implementation creating 2-3 feature showcases + 1-2 troubleshooting.

**Feature showcase selection:**
- Filter claims where claim_group == "key_features"
- For each top feature (up to 3 for standard/rich, 2 for minimal):
  - Check if snippets exist with matching tags
  - Only create showcase if feature has code examples
  - Generate slug: "how-to-{feature_text[:40].lower().replace(' ', '-')}"
  - page_role = assign_page_role("kb", slug) → "feature_showcase"
  - content_strategy = build_content_strategy("feature_showcase", "kb")
  - required_headings = ["Overview", "When to Use", "Step-by-Step Guide", "Code Example", "Related Links"]
  - required_claim_ids = [single feature claim]
  - forbidden_topics = ["general_features", "api_reference", "other_features"]

**Troubleshooting pages:**
- FAQ (always created):
  - page_role = assign_page_role("kb", "faq") → "troubleshooting"
  - content_strategy = build_content_strategy("troubleshooting", "kb")
- Troubleshooting guide (standard/rich tiers only):
  - page_role = "troubleshooting"
  - content_strategy = build_content_strategy("troubleshooting", "kb")

**Acceptance:** KB section creates 2-3 feature showcases + 1-2 troubleshooting, all have page_role and content_strategy

### Step 5: Add post-processing for TOC child_pages
Add new code before cross-link population (around line 724) to populate child_pages for TOC pages.

**Logic:**
```python
# Populate child_pages for TOC pages
logger.info("[W4] Populating child_pages for TOC pages")
for page in all_pages:
    if page.get("page_role") == "toc":
        section = page["section"]
        # Find all pages in same section (excluding TOC itself)
        child_slugs = [
            p["slug"]
            for p in all_pages
            if p["section"] == section and p["slug"] != "_index"
        ]
        # Sort for deterministic ordering
        child_slugs.sort()
        page["content_strategy"]["child_pages"] = child_slugs
        logger.debug(f"[W4] TOC page {section}/_index has {len(child_slugs)} children: {child_slugs}")
```

**Acceptance:** TOC pages have child_pages array populated with sorted slugs of all section children

### Step 6: Create unit tests
Create new test file tests/unit/workers/test_w4_content_distribution.py with test coverage for:

**Test cases:**
1. test_assign_page_role_docs_toc() - Verify is_index=True + section="docs" → "toc"
2. test_assign_page_role_developer_guide() - Verify slug="developer-guide" → "comprehensive_guide"
3. test_assign_page_role_kb_feature_showcase() - Verify "how-to" in slug → "feature_showcase"
4. test_assign_page_role_kb_troubleshooting() - Verify other KB slugs → "troubleshooting"
5. test_build_content_strategy_toc() - Verify toc strategy has child_pages=[], forbidden=["code_snippets"]
6. test_build_content_strategy_comprehensive_guide() - Verify scenario_coverage="all", quota.min=len(workflows)
7. test_build_content_strategy_feature_showcase() - Verify single feature focus, quota={min:3, max:8}
8. test_docs_section_creates_three_pages() - Integration test: run plan_pages_for_section("docs"), verify 3 pages
9. test_kb_section_creates_showcases_and_troubleshooting() - Integration test: verify mix of feature_showcase + troubleshooting
10. test_toc_child_pages_populated() - Integration test: verify TOC page.content_strategy.child_pages is populated

**Acceptance:** All tests pass, coverage ≥85% for new code

### Step 7: Run validation and evidence collection
Validate all changes pass existing gates and collect evidence.

```bash
# Activate virtual environment
.venv\Scripts\activate

# Run unit tests
python -m pytest tests/unit/workers/test_w4_content_distribution.py -v --cov=src/launch/workers/w4_ia_planner --cov-report=term

# Run existing W4 tests (regression check)
python -m pytest tests/unit/workers/test_w4_ia_planner.py -v

# Lint check
make lint

# Schema validation (TC-971 schemas)
python -c "import json, jsonschema; schema = json.load(open('specs/schemas/page_plan.schema.json')); jsonschema.Draft202012Validator.check_schema(schema); print('Schema valid')"

# Generate page_plan.json with pilot config (determinism check)
python -m src.launch.cli plan --config pilot-configs/aspose-3d-python/run_config.yaml --output test_page_plan_1.json
python -m src.launch.cli plan --config pilot-configs/aspose-3d-python/run_config.yaml --output test_page_plan_2.json
diff test_page_plan_1.json test_page_plan_2.json  # Should be identical

# Git diff
git diff src/launch/workers/w4_ia_planner/worker.py > reports/agents/AGENT_B/TC-972/changes.diff
```

**Acceptance:** All tests pass, lint passes, determinism verified (2 runs identical), git diff captured

## Failure modes

### Failure mode 1: Helper functions assign wrong page roles (breaks validation)
**Detection:** Unit tests fail with assertion errors on page_role values; integration test shows unexpected roles in page_plan.json; W7 Gate 14 fails with GATE14_ROLE_MISSING or wrong role for page type
**Resolution:** Review assign_page_role() logic against specs/08_content_distribution_strategy.md; verify slug matching patterns (exact match for "developer-guide", substring match for "how-to"); check is_index flag handling; add debug logging to trace role assignment; verify all 7 roles have deterministic assignment rules
**Spec/Gate:** specs/08_content_distribution_strategy.md Section Responsibilities, specs/06_page_planning.md Page Roles section

### Failure mode 2: Content strategy claim quotas conflict with existing claim distribution
**Detection:** Unit tests fail on quota validation; page_plan.json shows required_claim_ids count outside quota range; W7 Gate 14 fails with GATE14_CLAIM_QUOTA_EXCEEDED or GATE14_CLAIM_QUOTA_UNDERFLOW; pages have too many or too few claims
**Resolution:** Review build_content_strategy() quota values against specs/08 (products 5-10, toc 0-2, comprehensive_guide min=len(workflows), feature_showcase 3-8); adjust claim selection logic in section planning to respect quotas; ensure developer-guide gets exactly one claim per workflow; verify KB showcase gets single feature claim
**Spec/Gate:** specs/08_content_distribution_strategy.md Content Allocation Rules, specs/09_validation_gates.md Gate 14 Rule 6

### Failure mode 3: TOC child_pages array not populated or has wrong slugs
**Detection:** Unit test test_toc_child_pages_populated() fails; page_plan.json shows TOC page with empty child_pages=[]; W7 Gate 14 fails with GATE14_TOC_MISSING_CHILDREN; generated docs/_index.md doesn't list child pages
**Resolution:** Check post-processing loop runs after all pages created; verify section filtering (p["section"] == section); exclude TOC itself (p["slug"] != "_index"); ensure slugs are sorted for determinism; add debug logging showing child_slugs before assignment; verify loop runs for all TOC pages (not just docs section if multiple TOCs)
**Spec/Gate:** specs/08_content_distribution_strategy.md TOC section, specs/09_validation_gates.md Gate 14 Rule 4

### Failure mode 4: KB section creates no feature showcases (still troubleshooting-only)
**Detection:** Integration test shows KB pages all have page_role="troubleshooting"; no "how-to-*" slugs in page_plan.json; W7 Gate 14 warning about missing feature showcases; KB section has <2 feature_showcase pages
**Resolution:** Verify feature claim selection filters claim_group=="key_features"; check snippet matching logic (tags overlap); ensure showcase_count calculation (2 for minimal, 3 for standard/rich); verify slug generation includes "how-to" prefix; check if snippets are empty (need sample data for testing)
**Spec/Gate:** specs/08_content_distribution_strategy.md KB section (2-3 feature showcases required), specs/06_page_planning.md Mandatory Pages by Section

### Failure mode 5: Developer guide missing workflow claims (incomplete coverage)
**Detection:** Integration test shows developer-guide with fewer required_claim_ids than len(workflows); W7 Gate 14 fails with GATE14_GUIDE_INCOMPLETE; comprehensive guide page doesn't list all scenarios
**Resolution:** Check workflow claim gathering logic (c for c in claims if wf_id in c.get("claim_group")); verify workflow_id extraction from workflow objects; ensure one claim per workflow (wf_claims[:1]); check if workflows array is empty (need sample data); verify claim_group naming convention matches workflow_id
**Spec/Gate:** specs/08_content_distribution_strategy.md Developer Guide section (ALL workflows), specs/09_validation_gates.md Gate 14 Rule 5

## Task-specific review checklist
1. [ ] Helper function assign_page_role() returns correct role for all 7 role types (deterministic, no randomness)
2. [ ] Helper function build_content_strategy() returns correct strategy for all roles with proper quotas
3. [ ] Docs section creates exactly 3 pages: TOC + getting-started + developer-guide (not individual workflows)
4. [ ] TOC page has page_role="toc", content_strategy.child_pages populated with sorted slugs
5. [ ] Developer-guide page has page_role="comprehensive_guide", scenario_coverage="all", required_claim_ids covers all workflows
6. [ ] KB section creates 2-3 feature showcases (page_role="feature_showcase") + 1-2 troubleshooting
7. [ ] Feature showcase pages have single feature focus (1 primary claim), "how-to-" slug prefix
8. [ ] All pages have page_role and content_strategy fields (no pages missing these fields)
9. [ ] Unit tests cover all new functions and modified planning logic (≥85% coverage)
10. [ ] Integration tests verify page_plan.json has correct structure and determinism (2 runs identical)
11. [ ] Existing W4 tests still pass (no regressions in products, blog, reference sections)
12. [ ] Git diff shows +280 lines net (helper functions ~80, docs planning ~100, KB planning ~80, post-processing ~20)

## Deliverables
- src/launch/workers/w4_ia_planner/worker.py (modified, +280 lines: helpers, docs/KB planning, TOC post-processing)
- tests/unit/workers/test_w4_content_distribution.py (NEW, ~150 lines, 10+ test cases)
- Test output showing all tests pass, coverage ≥85%
- page_plan.json samples showing page_role and content_strategy fields for all pages
- Determinism evidence: 2 identical page_plan.json outputs from same input
- Git diff at reports/agents/AGENT_B/TC-972/changes.diff
- Evidence bundle at reports/agents/AGENT_B/TC-972/evidence.md
- Self-review at reports/agents/AGENT_B/TC-972/self_review.md (12 dimensions, scores 1-5)

## Acceptance checks
1. [ ] Helper functions assign_page_role() and build_content_strategy() added (2 functions, ~80 lines)
2. [ ] Docs section creates 3 pages: TOC + getting-started + developer-guide
3. [ ] KB section creates 2-3 feature showcases + 1-2 troubleshooting
4. [ ] TOC post-processing populates child_pages array
5. [ ] All pages in page_plan.json have page_role field (no missing)
6. [ ] All pages in page_plan.json have content_strategy field (no missing)
7. [ ] Unit tests created with 10+ test cases covering new code
8. [ ] All tests pass (new + existing W4 tests)
9. [ ] Test coverage ≥85% for modified code
10. [ ] Lint passes (make lint exits 0)
11. [ ] Determinism verified (2 runs produce identical page_plan.json)
12. [ ] No regressions in products, blog, reference sections (existing tests pass)

## Preconditions / dependencies
- TC-971 completed (specs/08, updated schemas available)
- Python virtual environment activated (.venv)
- Access to specs/08_content_distribution_strategy.md
- Access to specs/schemas/page_plan.schema.json (with page_role and content_strategy fields)
- Sample product_facts.json with workflows array for testing
- Sample snippet_catalog.json for testing

## Self-review
[To be completed by Agent B after implementation]

Dimensions to score (1-5, need 4+ on all):
1. Coverage: All 4 W4 modifications complete (helpers, docs, KB, TOC post-processing) ✓
2. Correctness: Page roles assigned correctly per specs, quotas match ✓
3. Evidence: Tests pass, determinism verified, git diff captured ✓
4. Test Quality: 10+ unit tests, ≥85% coverage, integration tests ✓
5. Maintainability: Helper functions clear, section planning readable ✓
6. Safety: No breaking changes, backward compatible if fields optional ✓
7. Security: N/A (no user input, external APIs, or secrets)
8. Reliability: Deterministic page role assignment, no randomness ✓
9. Observability: Logging added for role assignment, child_pages population ✓
10. Performance: No performance impact (same number of loops, O(n) child_pages) ✓
11. Compatibility: Works with existing pilots, respects ruleset quotas ✓
12. Docs/Specs Fidelity: Implements specs/08 and specs/06 exactly ✓

## E2E verification
After TC-971, TC-972, TC-973, TC-974, TC-975 complete:
1. Run pilot with updated system: `python -m src.launch.cli launch --config pilot-configs/aspose-3d-python/run_config.yaml`
2. Verify page_plan.json has page_role and content_strategy for all pages
3. Verify docs section has 3 pages: _index.md (TOC), getting-started/_index.md, developer-guide/_index.md
4. Verify docs/_index.md has content_strategy.child_pages = ["getting-started", "developer-guide"]
5. Verify docs/developer-guide/_index.md has page_role="comprehensive_guide", scenario_coverage="all"
6. Verify KB has 2-3 "how-to-*" pages (feature_showcase) + 1-2 troubleshooting pages
7. Run W7 validator: Verify Gate 14 passes with no errors

## Integration boundary proven
**Boundary:** W4 IAPlanner (page planning) → W5 SectionWriter (content generation) + W7 Validator (validation)

**Contract:** W4 produces page_plan.json with page_role and content_strategy fields. W5 reads these fields and routes to specialized generators (TC-973). W7 validates compliance (TC-974).

**Verification:** After all 5 taskcards complete:
1. W4 outputs page_plan.json with new fields → W5 reads page_plan.json and generates correct content per role
2. W5 generates docs/_index.md (TOC) with no code snippets → W7 Gate 14 validates TOC compliance
3. W5 generates docs/developer-guide/_index.md listing all workflows → W7 Gate 14 validates comprehensive coverage
4. W5 generates KB feature showcases with single-feature focus → W7 Gate 14 validates single claim focus
5. End-to-end pilot run produces valid site content passing all gates
