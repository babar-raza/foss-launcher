"""Unit tests for Gate 14: Content Distribution Compliance (TC-974).

Tests validate_content_distribution() function in W7 Validator worker.

Covers:
- Rule 1: Schema compliance (page_role and content_strategy present)
- Rule 2: TOC compliance (no code snippets, all children referenced)
- Rule 3: Comprehensive guide completeness (all workflows, scenario_coverage)
- Rule 4: Forbidden topics enforcement
- Rule 5: Claim quota compliance (min/max)
- Rule 6: Content duplication detection (blog exempted)
- Profile-based severity (local, ci, prod)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import pytest

from src.launch.workers.w7_validator.worker import validate_content_distribution


# Fixtures


@pytest.fixture
def temp_site_dir(tmp_path: Path) -> Path:
    """Create temporary site content directory."""
    site_dir = tmp_path / "work" / "site"
    site_dir.mkdir(parents=True, exist_ok=True)
    return site_dir


@pytest.fixture
def basic_page_plan() -> Dict[str, Any]:
    """Create basic page plan with minimal fields."""
    return {
        "product_slug": "test-product",
        "pages": [],
    }


@pytest.fixture
def basic_product_facts() -> Dict[str, Any]:
    """Create basic product facts."""
    return {
        "product_name": "Test Product",
        "workflows": [
            {"id": "workflow1", "name": "Basic Workflow"},
            {"id": "workflow2", "name": "Advanced Workflow"},
        ],
    }


# Test Rule 1: Schema Compliance


def test_gate14_missing_page_role(basic_page_plan, basic_product_facts, temp_site_dir):
    """Page without page_role should trigger GATE14_ROLE_MISSING."""
    basic_page_plan["pages"] = [
        {
            "slug": "test-page",
            "output_path": "content/test-page.md",
            "content_strategy": {"claim_quota": {"min": 0, "max": 5}},
        }
    ]

    issues = validate_content_distribution(
        basic_page_plan, basic_product_facts, temp_site_dir, profile="local"
    )

    assert len(issues) == 1
    assert issues[0]["error_code"] == "GATE14_ROLE_MISSING"
    assert "test-page" in issues[0]["message"]
    assert issues[0]["severity"] == "warn"  # local profile


def test_gate14_missing_content_strategy(basic_page_plan, basic_product_facts, temp_site_dir):
    """Page without content_strategy should trigger GATE14_STRATEGY_MISSING."""
    basic_page_plan["pages"] = [
        {
            "slug": "test-page",
            "page_role": "toc",
            "output_path": "content/test-page.md",
        }
    ]

    issues = validate_content_distribution(
        basic_page_plan, basic_product_facts, temp_site_dir, profile="local"
    )

    assert len(issues) == 1
    assert issues[0]["error_code"] == "GATE14_STRATEGY_MISSING"
    assert "test-page" in issues[0]["message"]


# Test Rule 2: TOC Compliance


def test_gate14_toc_with_code_snippets(basic_page_plan, basic_product_facts, temp_site_dir):
    """TOC page with code snippets should trigger GATE14_TOC_HAS_SNIPPETS (blocker in prod)."""
    # Create TOC page with code snippet
    toc_file = temp_site_dir / "content" / "toc-page.md"
    toc_file.parent.mkdir(parents=True, exist_ok=True)
    toc_file.write_text(
        """---
title: TOC Page
---

# Table of Contents

Here's some code:

```python
print("Hello World")
```
""",
        encoding="utf-8",
    )

    basic_page_plan["pages"] = [
        {
            "slug": "toc-page",
            "page_role": "toc",
            "output_path": "content/toc-page.md",
            "content_strategy": {"child_pages": []},
        }
    ]

    # Test prod profile (blocker)
    issues = validate_content_distribution(
        basic_page_plan, basic_product_facts, temp_site_dir, profile="prod"
    )

    assert len(issues) >= 1
    snippet_issue = next(
        (i for i in issues if i["error_code"] == "GATE14_TOC_HAS_SNIPPETS"), None
    )
    assert snippet_issue is not None
    assert snippet_issue["severity"] == "blocker"

    # Test ci profile (error)
    issues = validate_content_distribution(
        basic_page_plan, basic_product_facts, temp_site_dir, profile="ci"
    )
    snippet_issue = next(
        (i for i in issues if i["error_code"] == "GATE14_TOC_HAS_SNIPPETS"), None
    )
    assert snippet_issue["severity"] == "error"


def test_gate14_toc_missing_children(basic_page_plan, basic_product_facts, temp_site_dir):
    """TOC page missing child references should trigger GATE14_TOC_MISSING_CHILDREN."""
    # Create TOC page without child references
    toc_file = temp_site_dir / "content" / "toc-page.md"
    toc_file.parent.mkdir(parents=True, exist_ok=True)
    toc_file.write_text(
        """---
title: TOC Page
---

# Table of Contents

Some content here.
""",
        encoding="utf-8",
    )

    basic_page_plan["pages"] = [
        {
            "slug": "toc-page",
            "page_role": "toc",
            "output_path": "content/toc-page.md",
            "content_strategy": {
                "child_pages": ["child-page-1", "child-page-2"]
            },
        }
    ]

    issues = validate_content_distribution(
        basic_page_plan, basic_product_facts, temp_site_dir, profile="ci"
    )

    assert len(issues) >= 1
    child_issue = next(
        (i for i in issues if i["error_code"] == "GATE14_TOC_MISSING_CHILDREN"), None
    )
    assert child_issue is not None
    assert child_issue["severity"] == "error"  # ci profile
    assert "child-page-1" in child_issue["message"]
    assert "child-page-2" in child_issue["message"]


def test_gate14_toc_all_children_present(basic_page_plan, basic_product_facts, temp_site_dir):
    """TOC page with all children referenced should pass."""
    # Create TOC page with child references
    toc_file = temp_site_dir / "content" / "toc-page.md"
    toc_file.parent.mkdir(parents=True, exist_ok=True)
    toc_file.write_text(
        """---
title: TOC Page
---

# Table of Contents

- [Child Page 1](child-page-1)
- [Child Page 2](child-page-2)
""",
        encoding="utf-8",
    )

    basic_page_plan["pages"] = [
        {
            "slug": "toc-page",
            "page_role": "toc",
            "output_path": "content/toc-page.md",
            "content_strategy": {
                "child_pages": ["child-page-1", "child-page-2"]
            },
        }
    ]

    issues = validate_content_distribution(
        basic_page_plan, basic_product_facts, temp_site_dir, profile="ci"
    )

    # Should have no TOC-related issues
    child_issue = next(
        (i for i in issues if i["error_code"] == "GATE14_TOC_MISSING_CHILDREN"), None
    )
    assert child_issue is None


# Test Rule 3: Comprehensive Guide Completeness


def test_gate14_guide_incomplete(basic_page_plan, basic_product_facts, temp_site_dir):
    """Comprehensive guide with fewer claims than workflows should trigger GATE14_GUIDE_INCOMPLETE."""
    basic_page_plan["pages"] = [
        {
            "slug": "comprehensive-guide",
            "page_role": "comprehensive_guide",
            "output_path": "content/guide.md",
            "content_strategy": {"scenario_coverage": "all"},
            "required_claim_ids": ["claim1"],  # Only 1 claim, but 2 workflows
        }
    ]

    issues = validate_content_distribution(
        basic_page_plan, basic_product_facts, temp_site_dir, profile="ci"
    )

    assert len(issues) >= 1
    incomplete_issue = next(
        (i for i in issues if i["error_code"] == "GATE14_GUIDE_INCOMPLETE"), None
    )
    assert incomplete_issue is not None
    assert incomplete_issue["severity"] == "error"  # ci profile
    assert "covers 1 workflows, expected 2" in incomplete_issue["message"]


def test_gate14_guide_coverage_invalid(basic_page_plan, basic_product_facts, temp_site_dir):
    """Comprehensive guide with scenario_coverage != 'all' should trigger GATE14_GUIDE_COVERAGE_INVALID."""
    basic_page_plan["pages"] = [
        {
            "slug": "comprehensive-guide",
            "page_role": "comprehensive_guide",
            "output_path": "content/guide.md",
            "content_strategy": {"scenario_coverage": "partial"},
            "required_claim_ids": ["claim1", "claim2"],
        }
    ]

    issues = validate_content_distribution(
        basic_page_plan, basic_product_facts, temp_site_dir, profile="ci"
    )

    assert len(issues) >= 1
    coverage_issue = next(
        (i for i in issues if i["error_code"] == "GATE14_GUIDE_COVERAGE_INVALID"), None
    )
    assert coverage_issue is not None
    assert coverage_issue["severity"] == "error"  # ci profile
    assert "scenario_coverage='partial'" in coverage_issue["message"]


def test_gate14_guide_complete(basic_page_plan, basic_product_facts, temp_site_dir):
    """Comprehensive guide with all workflows covered should pass."""
    basic_page_plan["pages"] = [
        {
            "slug": "comprehensive-guide",
            "page_role": "comprehensive_guide",
            "output_path": "content/guide.md",
            "content_strategy": {"scenario_coverage": "all"},
            "required_claim_ids": ["claim1", "claim2"],  # 2 claims for 2 workflows
        }
    ]

    issues = validate_content_distribution(
        basic_page_plan, basic_product_facts, temp_site_dir, profile="ci"
    )

    # Should have no guide-related issues
    guide_issues = [
        i for i in issues
        if i["error_code"] in ["GATE14_GUIDE_INCOMPLETE", "GATE14_GUIDE_COVERAGE_INVALID"]
    ]
    assert len(guide_issues) == 0


# Test Rules 4-5: Forbidden Topics and Claim Quotas


def test_gate14_claim_quota_underflow(basic_page_plan, basic_product_facts, temp_site_dir):
    """Page below minimum claims should trigger GATE14_CLAIM_QUOTA_UNDERFLOW (warning)."""
    basic_page_plan["pages"] = [
        {
            "slug": "feature-page",
            "page_role": "feature_showcase",
            "output_path": "content/feature.md",
            "content_strategy": {"claim_quota": {"min": 3, "max": 5}},
            "required_claim_ids": ["claim1"],  # Only 1 claim, min is 3
        }
    ]

    issues = validate_content_distribution(
        basic_page_plan, basic_product_facts, temp_site_dir, profile="ci"
    )

    assert len(issues) >= 1
    underflow_issue = next(
        (i for i in issues if i["error_code"] == "GATE14_CLAIM_QUOTA_UNDERFLOW"), None
    )
    assert underflow_issue is not None
    assert underflow_issue["severity"] == "warn"  # Always warning
    assert "has 1 claims, below minimum of 3" in underflow_issue["message"]


def test_gate14_claim_quota_exceeded(basic_page_plan, basic_product_facts, temp_site_dir):
    """Page above maximum claims should trigger GATE14_CLAIM_QUOTA_EXCEEDED."""
    basic_page_plan["pages"] = [
        {
            "slug": "feature-page",
            "page_role": "feature_showcase",
            "output_path": "content/feature.md",
            "content_strategy": {"claim_quota": {"min": 1, "max": 3}},
            "required_claim_ids": ["claim1", "claim2", "claim3", "claim4"],  # 4 claims, max is 3
        }
    ]

    issues = validate_content_distribution(
        basic_page_plan, basic_product_facts, temp_site_dir, profile="ci"
    )

    assert len(issues) >= 1
    exceeded_issue = next(
        (i for i in issues if i["error_code"] == "GATE14_CLAIM_QUOTA_EXCEEDED"), None
    )
    assert exceeded_issue is not None
    assert "has 4 claims, exceeds maximum of 3" in exceeded_issue["message"]


def test_gate14_forbidden_topic(basic_page_plan, basic_product_facts, temp_site_dir):
    """Page containing forbidden topic should trigger GATE14_FORBIDDEN_TOPIC."""
    # Create page with forbidden topic
    page_file = temp_site_dir / "content" / "feature.md"
    page_file.parent.mkdir(parents=True, exist_ok=True)
    page_file.write_text(
        """---
title: Feature Page
---

# Feature

## Installation

Steps to install the library.

## Configuration

How to configure settings.
""",
        encoding="utf-8",
    )

    basic_page_plan["pages"] = [
        {
            "slug": "feature-page",
            "page_role": "feature_showcase",
            "output_path": "content/feature.md",
            "content_strategy": {
                "claim_quota": {"min": 1, "max": 5},
                "forbidden_topics": ["installation", "configuration"],
            },
            "required_claim_ids": ["claim1"],
        }
    ]

    issues = validate_content_distribution(
        basic_page_plan, basic_product_facts, temp_site_dir, profile="ci"
    )

    assert len(issues) >= 1
    forbidden_issues = [
        i for i in issues if i["error_code"] == "GATE14_FORBIDDEN_TOPIC"
    ]
    assert len(forbidden_issues) >= 1
    assert forbidden_issues[0]["severity"] == "error"


# Test Rule 6: Content Duplication


def test_gate14_claim_cross_section(basic_page_plan, basic_product_facts, temp_site_dir):
    """Same claim in multiple sections should trigger GATE14_CLAIM_CROSS_SECTION (warning).

    TC-VFV: Only CROSS-SECTION duplication is detected (same claim in docs AND reference).
    Within-section duplication is acceptable since related pages share thematic claims.
    """
    basic_page_plan["pages"] = [
        {
            "slug": "page1",
            "page_role": "feature_showcase",
            "section": "docs",
            "output_path": "content/page1.md",
            "content_strategy": {"claim_quota": {"min": 1, "max": 5}},
            "required_claim_ids": ["shared-claim-123"],
        },
        {
            "slug": "page2",
            "page_role": "workflow_page",
            "section": "reference",
            "output_path": "content/page2.md",
            "content_strategy": {"claim_quota": {"min": 1, "max": 5}},
            "required_claim_ids": ["shared-claim-123"],
        },
    ]

    issues = validate_content_distribution(
        basic_page_plan, basic_product_facts, temp_site_dir, profile="ci"
    )

    assert len(issues) >= 1
    duplication_issue = next(
        (i for i in issues if i["error_code"] == "GATE14_CLAIM_CROSS_SECTION"), None
    )
    assert duplication_issue is not None
    assert duplication_issue["severity"] == "warn"  # Always warning
    assert "multiple sections" in duplication_issue["message"]


def test_gate14_blog_exemption(basic_page_plan, basic_product_facts, temp_site_dir):
    """Claim duplication allowed for blog section pages.

    Blog pages are excluded from cross-section duplication checks.
    A claim used in blog and docs is NOT considered duplication.
    """
    basic_page_plan["pages"] = [
        {
            "slug": "blog-post",
            "page_role": "landing",
            "section": "blog",
            "output_path": "content/blog/post.md",
            "content_strategy": {"claim_quota": {"min": 1, "max": 5}},
            "required_claim_ids": ["shared-claim-123"],
        },
        {
            "slug": "feature-page",
            "page_role": "feature_showcase",
            "section": "docs",
            "output_path": "content/feature.md",
            "content_strategy": {"claim_quota": {"min": 1, "max": 5}},
            "required_claim_ids": ["shared-claim-123"],
        },
    ]

    issues = validate_content_distribution(
        basic_page_plan, basic_product_facts, temp_site_dir, profile="ci"
    )

    # Should have no cross-section issues (blog is exempted)
    duplication_issue = next(
        (i for i in issues if i["error_code"] == "GATE14_CLAIM_CROSS_SECTION"), None
    )
    assert duplication_issue is None


# Test Profile-Based Severity


def test_gate14_profile_severity_local(basic_page_plan, basic_product_facts, temp_site_dir):
    """Local profile should return warnings for all violations."""
    # Create TOC with code snippets
    toc_file = temp_site_dir / "content" / "toc.md"
    toc_file.parent.mkdir(parents=True, exist_ok=True)
    toc_file.write_text("```python\ncode\n```", encoding="utf-8")

    basic_page_plan["pages"] = [
        {
            "slug": "toc-page",
            "page_role": "toc",
            "output_path": "content/toc.md",
            "content_strategy": {"child_pages": []},
        }
    ]

    issues = validate_content_distribution(
        basic_page_plan, basic_product_facts, temp_site_dir, profile="local"
    )

    snippet_issue = next(
        (i for i in issues if i["error_code"] == "GATE14_TOC_HAS_SNIPPETS"), None
    )
    assert snippet_issue is not None
    assert snippet_issue["severity"] == "warn"  # local profile = warning


def test_gate14_profile_severity_ci(basic_page_plan, basic_product_facts, temp_site_dir):
    """CI profile should return errors for critical violations."""
    # Create TOC with code snippets
    toc_file = temp_site_dir / "content" / "toc.md"
    toc_file.parent.mkdir(parents=True, exist_ok=True)
    toc_file.write_text("```python\ncode\n```", encoding="utf-8")

    basic_page_plan["pages"] = [
        {
            "slug": "toc-page",
            "page_role": "toc",
            "output_path": "content/toc.md",
            "content_strategy": {"child_pages": []},
        }
    ]

    issues = validate_content_distribution(
        basic_page_plan, basic_product_facts, temp_site_dir, profile="ci"
    )

    snippet_issue = next(
        (i for i in issues if i["error_code"] == "GATE14_TOC_HAS_SNIPPETS"), None
    )
    assert snippet_issue is not None
    assert snippet_issue["severity"] == "error"  # ci profile = error


def test_gate14_profile_severity_prod(basic_page_plan, basic_product_facts, temp_site_dir):
    """Prod profile should return blockers for TOC code snippets."""
    # Create TOC with code snippets
    toc_file = temp_site_dir / "content" / "toc.md"
    toc_file.parent.mkdir(parents=True, exist_ok=True)
    toc_file.write_text("```python\ncode\n```", encoding="utf-8")

    basic_page_plan["pages"] = [
        {
            "slug": "toc-page",
            "page_role": "toc",
            "output_path": "content/toc.md",
            "content_strategy": {"child_pages": []},
        }
    ]

    issues = validate_content_distribution(
        basic_page_plan, basic_product_facts, temp_site_dir, profile="prod"
    )

    snippet_issue = next(
        (i for i in issues if i["error_code"] == "GATE14_TOC_HAS_SNIPPETS"), None
    )
    assert snippet_issue is not None
    assert snippet_issue["severity"] == "blocker"  # prod profile = blocker


def test_gate14_all_pass(basic_page_plan, basic_product_facts, temp_site_dir):
    """Compliant page_plan should produce no issues."""
    # Create compliant TOC page
    toc_file = temp_site_dir / "content" / "toc.md"
    toc_file.parent.mkdir(parents=True, exist_ok=True)
    toc_file.write_text(
        """---
title: TOC
---

# Table of Contents

No code snippets here.
""",
        encoding="utf-8",
    )

    basic_page_plan["pages"] = [
        {
            "slug": "toc-page",
            "page_role": "toc",
            "output_path": "content/toc.md",
            "content_strategy": {
                "child_pages": [],
                "claim_quota": {"min": 0, "max": 2},
            },
            "required_claim_ids": [],
        }
    ]

    issues = validate_content_distribution(
        basic_page_plan, basic_product_facts, temp_site_dir, profile="prod"
    )

    assert len(issues) == 0


# Edge Cases


def test_gate14_empty_workflows(basic_page_plan, temp_site_dir):
    """Empty workflows array should skip comprehensive guide validation."""
    product_facts_no_workflows = {
        "product_name": "Test Product",
        "workflows": [],
    }

    basic_page_plan["pages"] = [
        {
            "slug": "guide",
            "page_role": "comprehensive_guide",
            "output_path": "content/guide.md",
            "content_strategy": {"scenario_coverage": "all"},
            "required_claim_ids": [],
        }
    ]

    issues = validate_content_distribution(
        basic_page_plan, product_facts_no_workflows, temp_site_dir, profile="ci"
    )

    # Should not raise exception or produce guide-related issues
    guide_issues = [
        i for i in issues
        if "GATE14_GUIDE" in i["error_code"]
    ]
    assert len(guide_issues) == 0


def test_gate14_missing_output_path(basic_page_plan, basic_product_facts, temp_site_dir):
    """Page without output_path should not crash."""
    basic_page_plan["pages"] = [
        {
            "slug": "test-page",
            "page_role": "feature_showcase",
            "content_strategy": {"claim_quota": {"min": 1, "max": 5}},
            "required_claim_ids": ["claim1"],
            # Missing output_path
        }
    ]

    # Should not raise exception
    issues = validate_content_distribution(
        basic_page_plan, basic_product_facts, temp_site_dir, profile="ci"
    )

    # May have issues but should complete without crashing
    assert isinstance(issues, list)
