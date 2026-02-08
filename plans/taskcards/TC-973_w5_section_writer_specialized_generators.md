---
id: TC-973
title: "W5 SectionWriter - Specialized Content Generators"
status: Ready
priority: Critical
owner: "Agent B (Backend/Workers)"
updated: "2026-02-04"
tags: ["w5", "section-writer", "content-generation", "phase-2"]
depends_on: ["TC-971", "TC-972", "TC-975"]
allowed_paths:
  - plans/taskcards/TC-973_w5_section_writer_specialized_generators.md
  - src/launch/workers/w5_section_writer/worker.py
  - tests/unit/workers/test_w5_specialized_generators.py
evidence_required:
  - reports/agents/AGENT_B/TC-973/evidence.md
  - reports/agents/AGENT_B/TC-973/self_review.md
spec_ref: "3e91498d6b9dbda85744df6bf8d5f3774ca39c60"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# Taskcard TC-973 — W5 SectionWriter - Specialized Content Generators

## Objective
Implement specialized content generators in W5 SectionWriter for new page roles (toc, comprehensive_guide, feature_showcase), routing content generation based on page_role field, and respecting content_strategy boundaries.

## Problem Statement
W5 SectionWriter currently uses generic template-driven or LLM-based generation for all pages. It lacks:
1. TOC generator - Creates navigation hub listing child pages (no code snippets)
2. Comprehensive guide generator - Lists ALL workflows with code snippets in single page
3. Feature showcase generator - Creates how-to article for single prominent feature
4. Content generation routing based on page_role field
5. Forbidden topics enforcement from content_strategy

This prevents generating the specialized content types required by the content distribution strategy, causing content that doesn't match page role expectations.

## Required spec references
- C:\Users\prora\.claude\plans\magical-prancing-fountain.md (Primary implementation plan, Phase 2 Tasks 2.5-2.9)
- specs/08_content_distribution_strategy.md (From TC-971 - defines content rules per role)
- specs/07_section_templates.md (Updated by TC-971 - defines template types)
- src/launch/workers/w5_section_writer/worker.py (Current W5 implementation)
- specs/templates/docs.aspose.org/3d/__LOCALE__/__PLATFORM__/_index.md (From TC-975 - TOC template)
- specs/templates/docs.aspose.org/3d/__LOCALE__/__PLATFORM__/developer-guide/_index.md (From TC-975 - comprehensive guide template)
- specs/templates/kb.aspose.org/3d/__LOCALE__/__PLATFORM__/__TOPIC_SLUG__.variant-feature-showcase.md (From TC-975 - feature showcase template)
- CONTRIBUTING.md (No manual edits policy, .venv policy)

## Scope

### In scope
- Add specialized generator: generate_toc_content() (~60 lines)
- Add specialized generator: generate_comprehensive_guide_content() (~80 lines)
- Add specialized generator: generate_feature_showcase_content() (~70 lines)
- Modify content generation routing in generate_section_content() to dispatch by page_role (~30 lines)
- Update execute_section_writer() to pass page_plan to generators (~10 lines)
- Unit tests for 3 new generators (~180 lines total)
- Integration test verifying correct content routing by page_role
- All generated content respects forbidden_topics from content_strategy

### Out of scope
- W4 IAPlanner modifications (covered by TC-972)
- W7 Validator Gate 14 implementation (covered by TC-974)
- Template file creation (covered by TC-975)
- Spec/schema creation (covered by TC-971)
- LLM-based generation improvements (existing logic unchanged)
- Modification of existing generators for products, blog, reference sections

## Inputs
- specs/08_content_distribution_strategy.md (from TC-971)
- specs/07_section_templates.md (updated by TC-971)
- page_plan.json with page_role and content_strategy fields (from TC-972)
- product_facts.json (workflows array for comprehensive guide)
- snippet_catalog.json (snippets for code examples)
- Templates from TC-975 (TOC, comprehensive guide, feature showcase)
- src/launch/workers/w5_section_writer/worker.py (current implementation)

## Outputs
- src/launch/workers/w5_section_writer/worker.py (modified, +250 lines net)
- tests/unit/workers/test_w5_specialized_generators.py (NEW, ~180 lines)
- Generated markdown content respecting page roles and content strategies
- Evidence showing correct content routing by page_role
- Evidence showing TOC has no code snippets, comprehensive guide has all workflows
- Git diff showing modifications
- Test coverage report showing ≥85% coverage for new code

## Allowed paths
- plans/taskcards/TC-973_w5_section_writer_specialized_generators.md
- src/launch/workers/w5_section_writer/worker.py
- tests/unit/workers/test_w5_specialized_generators.py

### Allowed paths rationale
TC-973 implements the W5 SectionWriter changes for specialized content generation. All changes are in worker code and tests. No specs, schemas, or templates modified (those are handled by TC-971 and TC-975).

## Implementation steps

### Step 1: Add generate_toc_content() function
Add new function around line 400 to generate table of contents page content.

**Function signature:**
```python
def generate_toc_content(
    page: Dict[str, Any],
    product_facts: Dict[str, Any],
    page_plan: Dict[str, Any],
) -> str:
    """Generate table of contents page content.

    Creates navigation hub listing all child pages in the section.
    MUST NOT include code snippets (forbidden by specs/08).

    Returns: Markdown content for TOC page
    """
```

**Logic:**
1. Extract product_name, child_slugs from page.content_strategy.child_pages
2. Build intro paragraph (1-2 sentences about product documentation)
3. Build child page list:
   - For each child_slug, find child page in page_plan
   - Format: `- [child_title](child_url_path) - child_purpose`
   - Sort by slug for determinism
4. Build quick links section:
   - Find URLs for products, reference, KB, repo from page_plan
   - Format: `- [Product Overview](products_url)`, etc.
5. Combine sections into markdown with H2 headings: "Documentation Index", "Quick Links"
6. **CRITICAL**: No code snippets (```...```) in output - violates Gate 14

**Acceptance:** Function generates TOC with child list, no code snippets, deterministic output

### Step 2: Add generate_comprehensive_guide_content() function
Add new function after generate_toc_content() to generate developer guide listing all workflows.

**Function signature:**
```python
def generate_comprehensive_guide_content(
    page: Dict[str, Any],
    product_facts: Dict[str, Any],
    snippet_catalog: Dict[str, Any],
) -> str:
    """Generate comprehensive developer guide content.

    Lists ALL workflows from product_facts with code snippets.
    Each workflow must have description + code snippet + repo link.

    Returns: Markdown content for comprehensive guide
    """
```

**Logic:**
1. Extract product_name, workflows from product_facts
2. Build intro paragraph explaining guide purpose
3. For each workflow in workflows:
   - Extract name, description, workflow_id
   - Find matching snippet by workflow_id or tags
   - Build H3 section: `### {workflow_name}`
   - Add description (2-3 sentences)
   - Add code block with language and snippet.code
   - Add repo link: `[View full example on GitHub]({repo_url}/blob/{sha}/{snippet.source.path})`
   - Add separator: `---`
4. Build Additional Resources section with links to getting-started, API reference, KB
5. **CRITICAL**: MUST cover ALL workflows (scenario_coverage="all") - Gate 14 Rule 5

**Acceptance:** Function generates guide with all workflows, each has code snippet, deterministic order

### Step 3: Add generate_feature_showcase_content() function
Add new function after generate_comprehensive_guide_content() to generate KB feature showcase article.

**Function signature:**
```python
def generate_feature_showcase_content(
    page: Dict[str, Any],
    product_facts: Dict[str, Any],
    snippet_catalog: Dict[str, Any],
) -> str:
    """Generate KB feature showcase article content.

    Creates how-to guide for a specific prominent feature.
    MUST focus on single feature (1 primary claim) - Gate 14 Rule 4.

    Returns: Markdown content for feature showcase
    """
```

**Logic:**
1. Extract claim_ids from page.required_claim_ids (should have 1 primary claim)
2. Find feature claim in product_facts.claims matching claim_ids[0]
3. Extract feature_text = claim.claim_text
4. Find matching snippet from snippet_catalog by tags
5. Build sections:
   - **Overview**: feature_text + claim marker `<!-- claim_id:{claim_id} -->`
   - **When to Use**: "This feature is particularly useful when you need to {feature_text.lower()}."
   - **Step-by-Step Guide**: Generic 4-step process (Import, Initialize, Configure, Execute)
   - **Code Example**: Code block with snippet.language and snippet.code
   - **Related Links**: Links to developer guide, API reference, GitHub repo
6. **CRITICAL**: Single feature focus only (no other features mentioned)

**Acceptance:** Function generates showcase with single feature, has code example, respects forbidden_topics

### Step 4: Modify generate_section_content() routing
Modify existing generate_section_content() function (around line 255) to dispatch by page_role.

**Changes:**
1. Add page_plan parameter to function signature
2. Extract page_role from page.get("page_role", "landing")
3. Add routing logic at top of function:
```python
if page_role == "toc":
    logger.info(f"[W5] Generating TOC content for {page['slug']}")
    return generate_toc_content(page, product_facts, page_plan)

elif page_role == "comprehensive_guide":
    logger.info(f"[W5] Generating comprehensive guide for {page['slug']}")
    return generate_comprehensive_guide_content(page, product_facts, snippet_catalog)

elif page_role == "feature_showcase":
    logger.info(f"[W5] Generating feature showcase for {page['slug']}")
    return generate_feature_showcase_content(page, product_facts, snippet_catalog)

# ... existing template-driven and LLM-based generation logic for other roles ...
```

**Acceptance:** Function routes to specialized generators for toc, comprehensive_guide, feature_showcase roles

### Step 5: Update execute_section_writer() to pass page_plan
Modify execute_section_writer() function (around line 700) to load page_plan early and pass to generators.

**Changes:**
1. Load page_plan early in function:
```python
# Load page_plan early
page_plan = load_artifact(run_layout.artifacts_dir / "page_plan.json")
```

2. Update generate_section_content() call to pass page_plan:
```python
content = generate_section_content(
    page=page,
    product_facts=product_facts,
    snippet_catalog=snippet_catalog,
    page_plan=page_plan,  # NEW parameter
    llm_client=llm_client,
)
```

**Acceptance:** page_plan loaded and passed to content generators, no errors

### Step 6: Create unit tests
Create new test file tests/unit/workers/test_w5_specialized_generators.py with test coverage.

**Test cases:**
1. test_generate_toc_content_basic() - Verify TOC with 2 child pages, has intro + child list + quick links
2. test_generate_toc_content_no_code_snippets() - Verify output has no triple backticks (```), critical for Gate 14
3. test_generate_toc_content_empty_children() - Verify TOC with child_pages=[] still renders (graceful degradation)
4. test_generate_comprehensive_guide_all_workflows() - Verify guide with 3 workflows, each has H3 + description + code + link
5. test_generate_comprehensive_guide_missing_snippets() - Verify guide still renders if some snippets missing (graceful degradation)
6. test_generate_comprehensive_guide_deterministic_order() - Verify same workflows input → same output order
7. test_generate_feature_showcase_single_claim() - Verify showcase has 1 claim marker, Overview + When to Use + Steps + Code + Links
8. test_generate_feature_showcase_with_snippet() - Verify showcase includes code block with snippet.code
9. test_generate_feature_showcase_without_snippet() - Verify showcase renders placeholder code if snippet missing
10. test_generate_section_content_routing_toc() - Integration test: page_role="toc" → calls generate_toc_content()
11. test_generate_section_content_routing_guide() - Integration test: page_role="comprehensive_guide" → calls generate_comprehensive_guide_content()
12. test_generate_section_content_routing_showcase() - Integration test: page_role="feature_showcase" → calls generate_feature_showcase_content()

**Acceptance:** All tests pass, coverage ≥85% for new code

### Step 7: Run validation and evidence collection
Validate all changes pass existing gates and collect evidence.

```bash
# Activate virtual environment
.venv\Scripts\activate

# Run unit tests
python -m pytest tests/unit/workers/test_w5_specialized_generators.py -v --cov=src/launch/workers/w5_section_writer --cov-report=term

# Run existing W5 tests (regression check)
python -m pytest tests/unit/workers/test_w5_section_writer.py -v

# Lint check
make lint

# Generate sample content with pilot config (end-to-end check)
python -m src.launch.cli launch --config pilot-configs/aspose-3d-python/run_config.yaml --workers w4,w5

# Verify generated docs/_index.md has no code snippets
grep -c '```' work/site/content/docs/_index.md  # Should be 0

# Verify generated docs/developer-guide/_index.md has all workflows
grep -c '^###' work/site/content/docs/developer-guide/_index.md  # Should equal workflow count

# Git diff
git diff src/launch/workers/w5_section_writer/worker.py > reports/agents/AGENT_B/TC-973/changes.diff
```

**Acceptance:** All tests pass, lint passes, generated content validated, git diff captured

## Failure modes

### Failure mode 1: TOC generator includes code snippets (Gate 14 blocker)
**Detection:** test_generate_toc_content_no_code_snippets() fails; grep finds ``` in generated docs/_index.md; W7 Gate 14 fails with GATE14_TOC_HAS_SNIPPETS blocker
**Resolution:** Review generate_toc_content() to ensure no code blocks added; check child page descriptions don't include code; verify quick links section is plain markdown; add assertion in test: `assert '```' not in content`; scan all string formatting for code block insertion
**Spec/Gate:** specs/08_content_distribution_strategy.md TOC section (forbidden: code_snippets), specs/09_validation_gates.md Gate 14 Rule 2 (BLOCKER severity)

### Failure mode 2: Comprehensive guide missing workflows (incomplete coverage)
**Detection:** test_generate_comprehensive_guide_all_workflows() fails with count mismatch; W7 Gate 14 fails with GATE14_GUIDE_INCOMPLETE; generated developer-guide has fewer H3 sections than len(workflows)
**Resolution:** Check loop over workflows array (for workflow in workflows); verify each workflow generates H3 + description + code; ensure no workflows filtered/skipped; check if workflows array is empty in test data; add logging: logger.info(f"[W5] Generated guide with {len(workflows)} workflows"); verify graceful handling if snippet missing (show placeholder code instead of skipping workflow)
**Spec/Gate:** specs/08_content_distribution_strategy.md Developer Guide (scenario_coverage="all"), specs/09_validation_gates.md Gate 14 Rule 5

### Failure mode 3: Feature showcase violates single-feature focus (multiple claims)
**Detection:** test_generate_feature_showcase_single_claim() finds multiple claim markers; W7 Gate 14 warning GATE14_CLAIM_QUOTA_EXCEEDED (quota.max=8 but should be 1 primary); generated KB article mentions multiple features
**Resolution:** Verify generate_feature_showcase_content() uses only first claim: claim_ids[0]; check Overview section has single claim marker; ensure no additional claims inserted in Steps or Links sections; verify claim_text extraction doesn't include multiple features; scan for forbidden_topics mentions (other_features)
**Spec/Gate:** specs/08_content_distribution_strategy.md Feature Showcase section (single feature focus), specs/09_validation_gates.md Gate 14 Rule 4

### Failure mode 4: Content generation routing doesn't dispatch by page_role
**Detection:** Integration tests fail: test_generate_section_content_routing_*() calls wrong generator; page_role="toc" still generates generic content; logs don't show "[W5] Generating TOC content" messages
**Resolution:** Check page_role extraction: page.get("page_role", "landing"); verify if-elif routing order (toc → comprehensive_guide → feature_showcase before fallback); ensure return statements after each specialized generator call (don't fall through to default logic); add debug logging for each branch; verify page_plan passed to generate_section_content() signature
**Spec/Gate:** specs/07_section_templates.md template type definitions

### Failure mode 5: Missing page_plan parameter causes AttributeError
**Detection:** Runtime error: `TypeError: generate_section_content() missing required positional argument: 'page_plan'`; test_generate_section_content_routing_*() raises exception
**Resolution:** Verify execute_section_writer() loads page_plan before loop: `page_plan = load_artifact(...)` around line 700; check generate_section_content() call site passes page_plan parameter; update function signature: `def generate_section_content(..., page_plan: Dict[str, Any]):`; ensure page_plan passed in all call sites (not just new routing)
**Spec/Gate:** N/A (implementation error)

## Task-specific review checklist
1. [ ] generate_toc_content() function added, generates navigation hub with child list
2. [ ] TOC content has NO code snippets (```...```) - critical Gate 14 blocker if violated
3. [ ] generate_comprehensive_guide_content() function added, lists ALL workflows
4. [ ] Comprehensive guide has code snippet for each workflow with repo link
5. [ ] generate_feature_showcase_content() function added, single feature focus
6. [ ] Feature showcase has exactly 1 claim marker in Overview section
7. [ ] generate_section_content() modified to route by page_role (if-elif dispatch)
8. [ ] execute_section_writer() loads page_plan and passes to generators
9. [ ] Unit tests cover all 3 new generators (12 test cases, ≥85% coverage)
10. [ ] Integration tests verify correct routing by page_role (toc → TOC generator, etc.)
11. [ ] Existing W5 tests still pass (no regressions in products, blog, reference generation)
12. [ ] Generated content validates with Gate 14 (no TOC snippets, guide complete, showcase single-focus)

## Deliverables
- src/launch/workers/w5_section_writer/worker.py (modified, +250 lines: 3 generators ~210 lines, routing ~30 lines, page_plan passing ~10 lines)
- tests/unit/workers/test_w5_specialized_generators.py (NEW, ~180 lines, 12 test cases)
- Test output showing all tests pass, coverage ≥85%
- Sample generated content: docs/_index.md (TOC), docs/developer-guide/_index.md (comprehensive guide), kb/how-to-*.md (feature showcase)
- Evidence showing TOC has no code snippets (grep output)
- Evidence showing comprehensive guide has all workflows (H3 count)
- Git diff at reports/agents/AGENT_B/TC-973/changes.diff
- Evidence bundle at reports/agents/AGENT_B/TC-973/evidence.md
- Self-review at reports/agents/AGENT_B/TC-973/self_review.md (12 dimensions, scores 1-5)

## Acceptance checks
1. [ ] 3 specialized generators added: generate_toc_content(), generate_comprehensive_guide_content(), generate_feature_showcase_content()
2. [ ] Content generation routing modified to dispatch by page_role
3. [ ] execute_section_writer() loads and passes page_plan to generators
4. [ ] Unit tests created with 12 test cases covering new generators
5. [ ] All tests pass (new + existing W5 tests)
6. [ ] Test coverage ≥85% for modified code
7. [ ] Lint passes (make lint exits 0)
8. [ ] Generated docs/_index.md has NO code snippets (grep '```' returns 0)
9. [ ] Generated docs/developer-guide/_index.md has all workflows (H3 count equals workflow count)
10. [ ] Generated kb/how-to-*.md has single claim marker
11. [ ] No regressions in products, blog, reference content generation
12. [ ] Git diff shows +250 lines net for 3 generators + routing

## Preconditions / dependencies
- TC-971 completed (specs/08 available)
- TC-972 completed (page_plan.json has page_role and content_strategy fields)
- TC-975 completed or in progress (templates available for reference, but not strictly required for generators)
- Python virtual environment activated (.venv)
- Sample product_facts.json with workflows array for testing
- Sample snippet_catalog.json for code examples

## Self-review
[To be completed by Agent B after implementation]

Dimensions to score (1-5, need 4+ on all):
1. Coverage: All 3 generators + routing + page_plan passing complete ✓
2. Correctness: TOC has no code, guide has all workflows, showcase single-focus ✓
3. Evidence: Tests pass, generated samples validated, grep evidence ✓
4. Test Quality: 12 unit tests, ≥85% coverage, integration tests ✓
5. Maintainability: Generators are focused functions, clear routing ✓
6. Safety: No breaking changes, graceful degradation if data missing ✓
7. Security: N/A (no user input, external APIs, or secrets)
8. Reliability: Deterministic content generation, no randomness ✓
9. Observability: Logging added for each generator dispatch ✓
10. Performance: No performance impact (same generation complexity) ✓
11. Compatibility: Works with existing W5 flow, respects page_plan contracts ✓
12. Docs/Specs Fidelity: Implements specs/08 content rules exactly ✓

## E2E verification
After TC-971, TC-972, TC-973, TC-974, TC-975 complete:
1. Run pilot: `python -m src.launch.cli launch --config pilot-configs/aspose-3d-python/run_config.yaml`
2. Verify docs/_index.md exists and has child page list
3. Verify docs/_index.md has NO code snippets: `grep -c '```' work/site/content/docs/_index.md` returns 0
4. Verify docs/developer-guide/_index.md exists and lists all workflows
5. Verify each workflow in developer-guide has H3 heading + code block
6. Verify kb/how-to-*.md files exist (2-3 feature showcases)
7. Verify each feature showcase has exactly 1 claim marker
8. Run W7 validator: Verify Gate 14 passes (no GATE14_TOC_HAS_SNIPPETS, no GATE14_GUIDE_INCOMPLETE)

## Integration boundary proven
**Boundary:** W4 IAPlanner (page planning) → W5 SectionWriter (content generation) → W7 Validator (validation)

**Contract:** W4 produces page_plan.json with page_role field. W5 reads page_role and dispatches to specialized generators. W7 validates generated content matches role expectations.

**Verification:** After all 5 taskcards complete:
1. W4 assigns page_role="toc" → W5 generate_toc_content() generates navigation hub → W7 Gate 14 validates no code snippets
2. W4 assigns page_role="comprehensive_guide" → W5 generate_comprehensive_guide_content() lists all workflows → W7 Gate 14 validates complete coverage
3. W4 assigns page_role="feature_showcase" → W5 generate_feature_showcase_content() single feature → W7 Gate 14 validates single claim focus
4. End-to-end pilot run produces all expected page types with correct content
