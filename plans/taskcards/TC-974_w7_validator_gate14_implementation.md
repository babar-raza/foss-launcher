---
id: TC-974
title: "W7 Validator - Gate 14 Implementation"
status: Ready
priority: Critical
owner: "Agent B (Backend/Workers)"
updated: "2026-02-04"
tags: ["w7", "validator", "gate14", "content-distribution", "phase-2"]
depends_on: ["TC-971", "TC-972", "TC-973"]
allowed_paths:
  - plans/taskcards/TC-974_w7_validator_gate14_implementation.md
  - src/launch/workers/w7_validator/worker.py
  - tests/unit/workers/test_w7_gate14.py
evidence_required:
  - reports/agents/AGENT_B/TC-974/evidence.md
  - reports/agents/AGENT_B/TC-974/self_review.md
spec_ref: "3e91498d6b9dbda85744df6bf8d5f3774ca39c60"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# Taskcard TC-974 — W7 Validator - Gate 14 Implementation

## Objective
Implement Gate 14 validation in W7 Validator to enforce content distribution strategy compliance, validating page roles, content strategies, TOC compliance, comprehensive guide completeness, claim quotas, and content duplication prevention.

## Problem Statement
W7 Validator currently lacks validation for the content distribution strategy. It needs:
1. Gate 14 validation function checking 7 validation rules
2. Schema compliance checks (page_role and content_strategy fields present)
3. TOC compliance (no code snippets, all children referenced)
4. Comprehensive guide completeness (all workflows covered)
5. Forbidden topics enforcement
6. Claim quota compliance
7. Content duplication detection (except blog)
8. Profile-based severity (local=warning, ci=error, prod=blocker)
9. 9 error codes for different violation types

Without Gate 14, violations of content distribution strategy go undetected, causing non-compliant content to reach production.

## Required spec references
- C:\Users\prora\.claude\plans\magical-prancing-fountain.md (Primary implementation plan, Phase 2 Task 2.10)
- specs/09_validation_gates.md (Updated by TC-971 - Gate 14 specification)
- specs/08_content_distribution_strategy.md (From TC-971 - validation rules source)
- src/launch/workers/w7_validator/worker.py (Current W7 implementation)
- specs/schemas/page_plan.schema.json (From TC-971 - fields to validate)
- CONTRIBUTING.md (Validation profile requirements, .venv policy)

## Scope

### In scope
- Add Gate 14 validation function: validate_content_distribution() (~150 lines)
- 7 validation rules: schema compliance, TOC checks, comprehensive guide checks, forbidden topics, claim quotas, content duplication
- 9 error codes: GATE14_ROLE_MISSING, GATE14_STRATEGY_MISSING, GATE14_TOC_HAS_SNIPPETS, GATE14_TOC_MISSING_CHILDREN, GATE14_GUIDE_INCOMPLETE, GATE14_GUIDE_COVERAGE_INVALID, GATE14_FORBIDDEN_TOPIC, GATE14_CLAIM_QUOTA_EXCEEDED, GATE14_CLAIM_QUOTA_UNDERFLOW, GATE14_CLAIM_DUPLICATION
- Profile-based severity: local (warnings), ci (errors), prod (blockers for critical)
- Integration into execute_validator() main loop (~10 lines)
- Unit tests for all 7 validation rules (~200 lines)
- Integration test verifying Gate 14 catches violations

### Out of scope
- W4 IAPlanner modifications (covered by TC-972)
- W5 SectionWriter modifications (covered by TC-973)
- Spec/schema creation (covered by TC-971)
- Template creation (covered by TC-975)
- Modification of Gates 1-13 (existing gates unchanged)
- Validation profile configuration (already exists)

## Inputs
- specs/09_validation_gates.md (updated by TC-971 with Gate 14 spec)
- specs/08_content_distribution_strategy.md (from TC-971)
- page_plan.json with page_role and content_strategy fields (from TC-972)
- product_facts.json (workflows array for comprehensive guide validation)
- Generated markdown files in site_content_dir (for TOC snippet check, forbidden topics scan)
- run_config.yaml (validation_profile: local, ci, or prod)
- src/launch/workers/w7_validator/worker.py (current implementation)

## Outputs
- src/launch/workers/w7_validator/worker.py (modified, +160 lines: validate_content_distribution() ~150 lines, integration ~10 lines)
- tests/unit/workers/test_w7_gate14.py (NEW, ~200 lines)
- Validation reports with Gate 14 issues (error codes, severity, file paths, messages)
- Evidence showing Gate 14 catches all 9 error types
- Evidence showing profile-based severity working (local vs ci vs prod)
- Git diff showing modifications
- Test coverage report showing ≥85% coverage for new code

## Allowed paths
- plans/taskcards/TC-974_w7_validator_gate14_implementation.md
- src/launch/workers/w7_validator/worker.py
- tests/unit/workers/test_w7_gate14.py

### Allowed paths rationale
TC-974 implements the W7 Validator changes for Gate 14. All changes are in worker code and tests. No specs, schemas, or templates modified (those are handled by TC-971, TC-972, TC-973, TC-975).

## Implementation steps

### Step 1: Add validate_content_distribution() function
Add new function around line 400 implementing Gate 14 validation.

**Function signature:**
```python
def validate_content_distribution(
    page_plan: Dict[str, Any],
    product_facts: Dict[str, Any],
    site_content_dir: Path,
    profile: str = "local",
) -> List[Dict[str, Any]]:
    """Validate content distribution strategy compliance (Gate 14).

    Implements validation rules from specs/09_validation_gates.md Gate 14.

    Returns: List of validation issues with severity, code, message, file, gate
    """
```

**Profile-based severity helper:**
```python
def get_severity(violation_type: str) -> str:
    if profile == "local":
        return "warning"
    elif profile == "ci":
        return "error" if violation_type in ["toc_snippets", "missing_children", "incomplete_guide"] else "warning"
    else:  # prod
        return "blocker" if violation_type == "toc_snippets" else "error"
```

**Acceptance:** Function defined with correct signature, severity helper implemented

### Step 2: Implement Rule 1 - Schema compliance checks
Add validation checking all pages have page_role and content_strategy fields.

**Logic:**
```python
for page in page_plan.get("pages", []):
    if "page_role" not in page:
        issues.append({
            "severity": get_severity("missing_role"),
            "code": "GATE14_ROLE_MISSING",
            "message": f"Page '{page.get('slug', 'unknown')}' missing page_role field",
            "file": page.get("output_path", "unknown"),
            "gate": 14
        })
        continue  # Skip other checks if role missing (backward compatibility)

    if "content_strategy" not in page:
        issues.append({
            "severity": get_severity("missing_strategy"),
            "code": "GATE14_STRATEGY_MISSING",
            "message": f"Page '{page.get('slug', 'unknown')}' missing content_strategy field",
            "file": page.get("output_path", "unknown"),
            "gate": 14
        })
        continue  # Skip other checks if strategy missing
```

**Acceptance:** Missing page_role or content_strategy detected, backward compatible (continues if missing)

### Step 3: Implement Rule 2 - TOC pages compliance
Add validation checking TOC pages have no code snippets and reference all children.

**Logic for no code snippets (BLOCKER):**
```python
for page in page_plan.get("pages", []):
    if page.get("page_role") == "toc":
        draft_file = site_content_dir / page.get("output_path", "")
        if draft_file.exists():
            content = draft_file.read_text(encoding="utf-8")
            if "```" in content:
                issues.append({
                    "severity": get_severity("toc_snippets"),  # BLOCKER in prod
                    "code": "GATE14_TOC_HAS_SNIPPETS",
                    "message": f"TOC page '{page['slug']}' contains code snippets (forbidden by content distribution strategy)",
                    "file": str(draft_file),
                    "gate": 14
                })
```

**Logic for all children referenced:**
```python
        expected_children = page.get("content_strategy", {}).get("child_pages", [])
        if draft_file.exists():
            content = draft_file.read_text(encoding="utf-8")
            missing_children = []
            for child_slug in expected_children:
                if child_slug not in content:
                    missing_children.append(child_slug)

            if missing_children:
                issues.append({
                    "severity": get_severity("missing_children"),  # ERROR in ci/prod
                    "code": "GATE14_TOC_MISSING_CHILDREN",
                    "message": f"TOC page '{page['slug']}' missing child references: {', '.join(missing_children)}",
                    "file": str(draft_file),
                    "gate": 14
                })
```

**Acceptance:** TOC code snippets detected as BLOCKER, missing children detected as ERROR

### Step 4: Implement Rule 3 - Comprehensive guide completeness
Add validation checking comprehensive guide covers all workflows.

**Logic:**
```python
workflows = product_facts.get("workflows", [])
for page in page_plan.get("pages", []):
    if page.get("page_role") == "comprehensive_guide":
        expected_workflow_count = len(workflows)
        required_claim_ids = page.get("required_claim_ids", [])
        scenario_coverage = page.get("content_strategy", {}).get("scenario_coverage", "")

        if scenario_coverage != "all":
            issues.append({
                "severity": get_severity("incomplete_guide"),  # ERROR in ci/prod
                "code": "GATE14_GUIDE_COVERAGE_INVALID",
                "message": f"Comprehensive guide '{page['slug']}' has scenario_coverage='{scenario_coverage}', expected 'all'",
                "file": page.get("output_path", "unknown"),
                "gate": 14
            })

        if len(required_claim_ids) < expected_workflow_count:
            issues.append({
                "severity": get_severity("incomplete_guide"),  # ERROR in ci/prod
                "code": "GATE14_GUIDE_INCOMPLETE",
                "message": f"Comprehensive guide '{page['slug']}' covers {len(required_claim_ids)} workflows, expected {expected_workflow_count}",
                "file": page.get("output_path", "unknown"),
                "gate": 14
            })
```

**Acceptance:** Missing workflows detected, scenario_coverage validated

### Step 5: Implement Rules 4-5 - Forbidden topics and claim quotas
Add validation for forbidden topics mentions and claim quota compliance.

**Forbidden topics (simplified keyword scan):**
```python
# Rule 4: Forbidden topics (simplified - full implementation would use NLP)
# Skip for MVP - can be added later if needed
# Would scan markdown for keywords in content_strategy.forbidden_topics
```

**Claim quota compliance:**
```python
for page in page_plan.get("pages", []):
    quota = page.get("content_strategy", {}).get("claim_quota", {})
    min_claims = quota.get("min", 0)
    max_claims = quota.get("max", 999)
    actual_claims = len(page.get("required_claim_ids", []))

    if actual_claims < min_claims:
        issues.append({
            "severity": "warning",
            "code": "GATE14_CLAIM_QUOTA_UNDERFLOW",
            "message": f"Page '{page['slug']}' has {actual_claims} claims, below minimum of {min_claims}",
            "file": page.get("output_path", "unknown"),
            "gate": 14
        })

    if actual_claims > max_claims:
        issues.append({
            "severity": get_severity("quota_exceeded"),
            "code": "GATE14_CLAIM_QUOTA_EXCEEDED",
            "message": f"Page '{page['slug']}' has {actual_claims} claims, exceeds maximum of {max_claims}",
            "file": page.get("output_path", "unknown"),
            "gate": 14
        })
```

**Acceptance:** Claim quota violations detected (underflow=warning, exceeded=error)

### Step 6: Implement Rule 6 - Content duplication detection
Add validation checking no claim duplication across non-blog pages.

**Logic:**
```python
# Rule 6: No claim duplication (except blog)
claim_usage = {}  # claim_id -> list of (page_slug, section)
for page in page_plan.get("pages", []):
    section = page.get("section", "unknown")
    slug = page.get("slug", "unknown")
    for claim_id in page.get("required_claim_ids", []):
        if claim_id not in claim_usage:
            claim_usage[claim_id] = []
        claim_usage[claim_id].append((slug, section))

for claim_id, usages in claim_usage.items():
    # Filter out blog section
    non_blog_usages = [(slug, section) for slug, section in usages if section != "blog"]
    if len(non_blog_usages) > 1:
        pages_str = ", ".join([f"{section}/{slug}" for slug, section in non_blog_usages])
        issues.append({
            "severity": "warning",  # Warning only (not blocker)
            "code": "GATE14_CLAIM_DUPLICATION",
            "message": f"Claim {claim_id[:16]}... used on multiple non-blog pages: {pages_str}",
            "file": "multiple",
            "gate": 14
        })
```

**Acceptance:** Claim duplication detected, blog section exempted

### Step 7: Integrate Gate 14 into execute_validator()
Integrate validate_content_distribution() into main validation loop (around line 800).

**Logic:**
```python
def execute_validator(
    run_dir: Path,
    run_config: Dict[str, Any],
) -> Dict[str, Any]:
    """Execute W7 Validator worker."""
    # ... existing setup ...

    # Load artifacts
    page_plan = load_artifact(artifacts_dir / "page_plan.json")
    product_facts = load_artifact(artifacts_dir / "product_facts.json")

    # ... existing gates 1-13 ...

    # Gate 14: Content distribution compliance
    logger.info("[W7 Validator] Running Gate 14: Content Distribution Compliance")
    content_issues = validate_content_distribution(
        page_plan=page_plan,
        product_facts=product_facts,
        site_content_dir=run_layout.site_content_dir,
        profile=run_config.get("validation_profile", "local")
    )
    all_issues.extend(content_issues)

    # ... rest of validation ...
```

**Acceptance:** Gate 14 integrated, runs after existing gates, issues aggregated

### Step 8: Create unit tests
Create new test file tests/unit/workers/test_w7_gate14.py with comprehensive test coverage.

**Test cases:**
1. test_gate14_missing_page_role() - Page without page_role → GATE14_ROLE_MISSING
2. test_gate14_missing_content_strategy() - Page without content_strategy → GATE14_STRATEGY_MISSING
3. test_gate14_toc_with_code_snippets() - TOC page with ``` → GATE14_TOC_HAS_SNIPPETS (blocker in prod)
4. test_gate14_toc_missing_children() - TOC missing child refs → GATE14_TOC_MISSING_CHILDREN
5. test_gate14_guide_incomplete() - Comprehensive guide with <len(workflows) claims → GATE14_GUIDE_INCOMPLETE
6. test_gate14_guide_coverage_invalid() - scenario_coverage != "all" → GATE14_GUIDE_COVERAGE_INVALID
7. test_gate14_claim_quota_underflow() - Page below min claims → GATE14_CLAIM_QUOTA_UNDERFLOW (warning)
8. test_gate14_claim_quota_exceeded() - Page above max claims → GATE14_CLAIM_QUOTA_EXCEEDED
9. test_gate14_claim_duplication() - Same claim on 2 non-blog pages → GATE14_CLAIM_DUPLICATION (warning)
10. test_gate14_profile_severity_local() - Profile=local → all warnings
11. test_gate14_profile_severity_ci() - Profile=ci → critical violations are errors
12. test_gate14_profile_severity_prod() - Profile=prod → TOC snippets are blocker
13. test_gate14_blog_exemption() - Claim duplication allowed for blog section
14. test_gate14_all_pass() - Compliant page_plan → no issues

**Acceptance:** All tests pass, coverage ≥85% for validate_content_distribution()

### Step 9: Run validation and evidence collection
Validate all changes pass existing gates and collect evidence.

```bash
# Activate virtual environment
.venv\Scripts\activate

# Run unit tests
python -m pytest tests/unit/workers/test_w7_gate14.py -v --cov=src/launch/workers/w7_validator --cov-report=term

# Run existing W7 tests (regression check)
python -m pytest tests/unit/workers/test_w7_validator.py -v

# Lint check
make lint

# Test Gate 14 with pilot config (should pass)
python -m src.launch.cli launch --config pilot-configs/aspose-3d-python/run_config.yaml --workers w4,w5,w7

# Test Gate 14 with intentionally bad data (should fail)
# Create test page_plan with TOC having code snippets
python scripts/test_gate14_violations.py

# Extract Gate 14 issues from validation report
jq '.validation_report.issues[] | select(.gate == 14)' work/run_*/artifacts/validation_report.json

# Git diff
git diff src/launch/workers/w7_validator/worker.py > reports/agents/AGENT_B/TC-974/changes.diff
```

**Acceptance:** All tests pass, lint passes, Gate 14 catches violations, git diff captured

## Failure modes

### Failure mode 1: Profile-based severity not working (all warnings or all errors)
**Detection:** test_gate14_profile_severity_*() tests fail; prod profile shows warnings instead of blockers; ci profile doesn't show errors for critical violations
**Resolution:** Check get_severity() function implementation; verify profile parameter passed to validate_content_distribution(); ensure violation_type strings match ("toc_snippets", "missing_children", "incomplete_guide"); add debug logging: logger.debug(f"[Gate 14] Profile={profile}, violation={violation_type}, severity={severity}"); verify run_config.get("validation_profile", "local") returns correct value
**Spec/Gate:** specs/09_validation_gates.md Gate 14 Behavior by Profile section

### Failure mode 2: TOC code snippet check has false positives (detects non-code backticks)
**Detection:** test_gate14_toc_with_code_snippets() fails or has false positives; TOC pages with inline code (\`variable\`) flagged as violations; regex or string matching too broad
**Resolution:** Refine check to look for triple backticks only: `if "```" in content` (not single backticks); consider using regex: `re.search(r'```\w*\n', content)`; verify test data has real code blocks (```python...```); ensure inline code allowed; scan for fenced code blocks specifically
**Spec/Gate:** specs/09_validation_gates.md Gate 14 Rule 2 (code snippets = fenced code blocks, not inline code)

### Failure mode 3: Child pages check fails if slug substring matches (false negatives)
**Detection:** test_gate14_toc_missing_children() passes when it should fail; TOC page has "getting-started-guide" slug but check looks for "getting-started" and passes
**Resolution:** Change substring check `if child_slug not in content` to more specific check: search for markdown link pattern `[.*]({child_slug})` or `child_slug` as word boundary; use regex: `re.search(rf'\b{re.escape(child_slug)}\b', content)`; verify test data uses realistic slugs
**Spec/Gate:** specs/09_validation_gates.md Gate 14 Rule 4 (TOC must reference all child pages, not substrings)

### Failure mode 4: Claim duplication check includes blog section (false positives)
**Detection:** test_gate14_blog_exemption() fails; blog pages with same claims as other sections flagged; error count higher than expected
**Resolution:** Verify blog filtering logic: `non_blog_usages = [(slug, section) for slug, section in usages if section != "blog"]`; ensure blog section name is exactly "blog" (case-sensitive); check if test data uses correct section names; add debug logging: logger.debug(f"[Gate 14] Claim {claim_id} usage: {usages}, non-blog: {non_blog_usages}")
**Spec/Gate:** specs/09_validation_gates.md Gate 14 Rule 7 (blog section exempted from duplication check)

### Failure mode 5: Comprehensive guide validation fails with empty workflows array
**Detection:** test_gate14_guide_incomplete() raises exception or fails unexpectedly; ZeroDivisionError or empty array handling; guide validation skipped if workflows=[]
**Resolution:** Add guard: `workflows = product_facts.get("workflows", [])` and `if not workflows: logger.warning("[Gate 14] No workflows found, skipping comprehensive guide check")`; verify test data has workflows array; check if empty workflows is valid case (should be warning, not error); handle gracefully
**Spec/Gate:** N/A (implementation defensive coding)

## Task-specific review checklist
1. [ ] validate_content_distribution() function added (~150 lines) with 7 validation rules
2. [ ] Profile-based severity helper get_severity() implemented (local/ci/prod)
3. [ ] Rule 1: Schema compliance checks (page_role and content_strategy present)
4. [ ] Rule 2: TOC compliance checks (no code snippets = BLOCKER, children referenced)
5. [ ] Rule 3: Comprehensive guide completeness (all workflows, scenario_coverage="all")
6. [ ] Rule 4-5: Claim quota compliance (underflow=warning, exceeded=error)
7. [ ] Rule 6: Content duplication detection (blog exempted)
8. [ ] 9 error codes defined: GATE14_ROLE_MISSING, GATE14_STRATEGY_MISSING, GATE14_TOC_HAS_SNIPPETS, etc.
9. [ ] Gate 14 integrated into execute_validator() main loop
10. [ ] Unit tests cover all 7 rules + profile variations (14 test cases, ≥85% coverage)
11. [ ] Existing W7 tests still pass (no regressions in Gates 1-13)
12. [ ] Git diff shows +160 lines net (validate_content_distribution() ~150, integration ~10)

## Deliverables
- src/launch/workers/w7_validator/worker.py (modified, +160 lines: validate_content_distribution() ~150 lines, integration ~10 lines)
- tests/unit/workers/test_w7_gate14.py (NEW, ~200 lines, 14 test cases)
- Test output showing all tests pass, coverage ≥85%
- Validation reports with Gate 14 issues (sample JSON output)
- Evidence showing profile-based severity working (local vs ci vs prod)
- Evidence showing all 9 error codes trigger correctly
- Git diff at reports/agents/AGENT_B/TC-974/changes.diff
- Evidence bundle at reports/agents/AGENT_B/TC-974/evidence.md
- Self-review at reports/agents/AGENT_B/TC-974/self_review.md (12 dimensions, scores 1-5)

## Acceptance checks
1. [ ] validate_content_distribution() function added with 7 validation rules
2. [ ] Profile-based severity working (local=warning, ci=error for critical, prod=blocker for TOC snippets)
3. [ ] All 9 error codes defined and tested
4. [ ] Gate 14 integrated into execute_validator() main loop
5. [ ] Unit tests created with 14 test cases covering all rules
6. [ ] All tests pass (new + existing W7 tests)
7. [ ] Test coverage ≥85% for validate_content_distribution()
8. [ ] Lint passes (make lint exits 0)
9. [ ] Gate 14 catches TOC code snippets as BLOCKER (prod profile)
10. [ ] Gate 14 catches incomplete comprehensive guide as ERROR (ci/prod)
11. [ ] Gate 14 allows blog section claim duplication
12. [ ] No regressions in existing gates (Gates 1-13 still work)

## Preconditions / dependencies
- TC-971 completed (specs/09 has Gate 14 specification)
- TC-972 completed (page_plan.json has page_role and content_strategy fields)
- TC-973 completed (generated content available for validation)
- Python virtual environment activated (.venv)
- Sample page_plan.json with page_role and content_strategy fields
- Sample product_facts.json with workflows array
- Generated markdown files in site_content_dir for scanning

## Self-review
[To be completed by Agent B after implementation]

Dimensions to score (1-5, need 4+ on all):
1. Coverage: All 7 validation rules + profile-based severity + 9 error codes complete ✓
2. Correctness: Validation rules match specs/09 Gate 14 exactly ✓
3. Evidence: Tests pass, all error codes tested, profile variations tested ✓
4. Test Quality: 14 unit tests, ≥85% coverage, comprehensive scenarios ✓
5. Maintainability: Clear validation logic, well-structured helper functions ✓
6. Safety: Backward compatible (skips checks if fields missing) ✓
7. Security: N/A (no user input, external APIs, or secrets)
8. Reliability: Deterministic validation, no false positives/negatives ✓
9. Observability: Logging added for Gate 14 execution, issue counts ✓
10. Performance: Validation runs in <60s (local), <120s (ci/prod) ✓
11. Compatibility: Works with existing validation flow, respects profile settings ✓
12. Docs/Specs Fidelity: Implements specs/09 Gate 14 exactly ✓

## E2E verification
After TC-971, TC-972, TC-973, TC-974, TC-975 complete:
1. Run pilot: `python -m src.launch.cli launch --config pilot-configs/aspose-3d-python/run_config.yaml`
2. Verify validation_report.json has Gate 14 section
3. Verify Gate 14 passes with no errors (if content compliant)
4. Test violation detection:
   - Create TOC with code snippet → GATE14_TOC_HAS_SNIPPETS blocker
   - Create comprehensive guide missing workflows → GATE14_GUIDE_INCOMPLETE error
   - Duplicate claim across non-blog pages → GATE14_CLAIM_DUPLICATION warning
5. Test profile variations:
   - local profile: all warnings
   - ci profile: critical violations are errors
   - prod profile: TOC snippets are blockers
6. Verify Gate 14 timeout doesn't exceed 60s (local), 120s (ci/prod)

## Integration boundary proven
**Boundary:** W4 IAPlanner + W5 SectionWriter (content generation) → W7 Validator (validation)

**Contract:** W4/W5 produce page_plan.json and generated markdown content. W7 Gate 14 validates content distribution compliance per specs/08 and specs/09.

**Verification:** After all 5 taskcards complete:
1. W4 assigns page_role → W7 Gate 14 validates page_role present
2. W5 generates TOC with no code → W7 Gate 14 validates no code snippets
3. W5 generates comprehensive guide with all workflows → W7 Gate 14 validates complete coverage
4. W5 generates feature showcases → W7 Gate 14 validates single claim focus
5. End-to-end pilot run with Gate 14 enabled passes validation or reports expected violations
