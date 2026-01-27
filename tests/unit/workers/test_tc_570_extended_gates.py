"""Unit tests for TC-570: Extended Validation Gates.

Tests for Gates 2-9, 12-13 per specs/09_validation_gates.md.

Test coverage:
- Gate 2: Claim Marker Validity (2 tests)
- Gate 3: Snippet References (2 tests)
- Gate 4: Frontmatter Required Fields (2 tests)
- Gate 5: Cross-Page Link Validity (2 tests)
- Gate 6: Accessibility (2 tests)
- Gate 7: Content Quality (2 tests)
- Gate 8: Claim Coverage (2 tests)
- Gate 9: Navigation Integrity (2 tests)
- Gate 12: Patch Conflicts (2 tests)
- Gate 13: Hugo Build (2 tests)

Total: 20+ tests
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from launch.workers.w7_validator.gates import (
    gate_2_claim_marker_validity,
    gate_3_snippet_references,
    gate_4_frontmatter_required_fields,
    gate_5_cross_page_link_validity,
    gate_6_accessibility,
    gate_7_content_quality,
    gate_8_claim_coverage,
    gate_9_navigation_integrity,
    gate_12_patch_conflicts,
    gate_13_hugo_build,
)


@pytest.fixture
def temp_run_dir():
    """Create temporary run directory structure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = Path(tmpdir) / "run_001"
        run_dir.mkdir()

        # Create subdirectories
        (run_dir / "artifacts").mkdir()
        (run_dir / "work" / "site").mkdir(parents=True)

        yield run_dir


# =============================================================================
# Gate 2: Claim Marker Validity
# =============================================================================


def test_gate_2_pass_valid_claims(temp_run_dir):
    """Gate 2 passes when all claim markers reference valid claim_ids."""
    # Create product_facts.json with valid claims
    product_facts = {
        "product_name": "TestLib",
        "claim_groups": [
            {"claim_id": "claim_001", "claim": "Supports Python 3.8+"},
            {"claim_id": "claim_002", "claim": "Cross-platform"},
        ],
    }

    with open(temp_run_dir / "artifacts" / "product_facts.json", "w") as f:
        json.dump(product_facts, f)

    # Create markdown file with valid claim markers
    md_content = """---
title: Test
layout: default
permalink: /test/
---

# Test

This library [claim:claim_001] works on {claim:claim_002}.
"""

    site_dir = temp_run_dir / "work" / "site"
    (site_dir / "test.md").write_text(md_content)

    # Execute gate
    gate_passed, issues = gate_2_claim_marker_validity.execute_gate(
        temp_run_dir, "local"
    )

    assert gate_passed is True
    assert len(issues) == 0


def test_gate_2_fail_invalid_claims(temp_run_dir):
    """Gate 2 fails when claim markers reference non-existent claim_ids."""
    # Create product_facts.json with limited claims
    product_facts = {
        "product_name": "TestLib",
        "claim_groups": [{"claim_id": "claim_001", "claim": "Valid claim"}],
    }

    with open(temp_run_dir / "artifacts" / "product_facts.json", "w") as f:
        json.dump(product_facts, f)

    # Create markdown with invalid claim marker
    md_content = """---
title: Test
---

This references [claim:claim_999] which doesn't exist.
"""

    site_dir = temp_run_dir / "work" / "site"
    (site_dir / "test.md").write_text(md_content)

    # Execute gate
    gate_passed, issues = gate_2_claim_marker_validity.execute_gate(
        temp_run_dir, "local"
    )

    assert gate_passed is False
    assert len(issues) == 1
    assert issues[0]["error_code"] == "GATE_CLAIM_MARKER_INVALID"


# =============================================================================
# Gate 3: Snippet References
# =============================================================================


def test_gate_3_pass_valid_snippets(temp_run_dir):
    """Gate 3 passes when all snippet references are valid."""
    # Create snippet_catalog.json
    snippet_catalog = {
        "snippets": [
            {"snippet_id": "snippet_001", "language": "python"},
            {"snippet_id": "snippet_002", "language": "bash"},
        ]
    }

    with open(temp_run_dir / "artifacts" / "snippet_catalog.json", "w") as f:
        json.dump(snippet_catalog, f)

    # Create markdown with valid snippet references
    md_content = """---
title: Test
---

See [snippet:snippet_001] and {{snippet:snippet_002}}.
"""

    site_dir = temp_run_dir / "work" / "site"
    (site_dir / "test.md").write_text(md_content)

    # Execute gate
    gate_passed, issues = gate_3_snippet_references.execute_gate(temp_run_dir, "local")

    assert gate_passed is True
    assert len(issues) == 0


def test_gate_3_fail_invalid_snippets(temp_run_dir):
    """Gate 3 fails when snippet references don't exist."""
    # Create snippet_catalog.json
    snippet_catalog = {"snippets": [{"snippet_id": "snippet_001", "language": "python"}]}

    with open(temp_run_dir / "artifacts" / "snippet_catalog.json", "w") as f:
        json.dump(snippet_catalog, f)

    # Create markdown with invalid snippet reference
    md_content = """---
title: Test
---

Invalid [snippet:snippet_999].
"""

    site_dir = temp_run_dir / "work" / "site"
    (site_dir / "test.md").write_text(md_content)

    # Execute gate
    gate_passed, issues = gate_3_snippet_references.execute_gate(temp_run_dir, "local")

    assert gate_passed is False
    assert len(issues) == 1
    assert issues[0]["error_code"] == "GATE_SNIPPET_NOT_IN_CATALOG"


# =============================================================================
# Gate 4: Frontmatter Required Fields
# =============================================================================


def test_gate_4_pass_all_fields_present(temp_run_dir):
    """Gate 4 passes when all required frontmatter fields are present."""
    md_content = """---
title: Test Page
layout: default
permalink: /test/
---

Content here.
"""

    site_dir = temp_run_dir / "work" / "site"
    (site_dir / "test.md").write_text(md_content)

    # Execute gate
    gate_passed, issues = gate_4_frontmatter_required_fields.execute_gate(
        temp_run_dir, "local"
    )

    assert gate_passed is True
    assert len(issues) == 0


def test_gate_4_fail_missing_fields(temp_run_dir):
    """Gate 4 fails when required frontmatter fields are missing."""
    md_content = """---
title: Test Page
---

Missing layout and permalink.
"""

    site_dir = temp_run_dir / "work" / "site"
    (site_dir / "test.md").write_text(md_content)

    # Execute gate
    gate_passed, issues = gate_4_frontmatter_required_fields.execute_gate(
        temp_run_dir, "local"
    )

    assert gate_passed is False
    assert len(issues) == 2  # Missing layout and permalink
    assert all(
        issue["error_code"] == "GATE_FRONTMATTER_REQUIRED_FIELD_MISSING"
        for issue in issues
    )


# =============================================================================
# Gate 5: Cross-Page Link Validity
# =============================================================================


def test_gate_5_pass_valid_links(temp_run_dir):
    """Gate 5 passes when all internal links are valid."""
    site_dir = temp_run_dir / "work" / "site"

    # Create two linked pages
    page1 = """---
title: Page 1
---

Link to [page 2](page2.md).
"""

    page2 = """---
title: Page 2
---

Content.
"""

    (site_dir / "page1.md").write_text(page1)
    (site_dir / "page2.md").write_text(page2)

    # Execute gate
    gate_passed, issues = gate_5_cross_page_link_validity.execute_gate(
        temp_run_dir, "local"
    )

    assert gate_passed is True
    assert len(issues) == 0


def test_gate_5_fail_broken_links(temp_run_dir):
    """Gate 5 fails when internal links are broken."""
    site_dir = temp_run_dir / "work" / "site"

    md_content = """---
title: Test
---

Link to [missing page](missing.md).
"""

    (site_dir / "test.md").write_text(md_content)

    # Execute gate
    gate_passed, issues = gate_5_cross_page_link_validity.execute_gate(
        temp_run_dir, "local"
    )

    assert gate_passed is False
    assert len(issues) == 1
    assert issues[0]["error_code"] == "GATE_LINK_BROKEN_INTERNAL"


# =============================================================================
# Gate 6: Accessibility
# =============================================================================


def test_gate_6_pass_good_accessibility(temp_run_dir):
    """Gate 6 passes with proper heading hierarchy and alt text."""
    md_content = """---
title: Test
---

# Heading 1

## Heading 2

### Heading 3

![Alt text here](image.png)
"""

    site_dir = temp_run_dir / "work" / "site"
    (site_dir / "test.md").write_text(md_content)

    # Execute gate
    gate_passed, issues = gate_6_accessibility.execute_gate(temp_run_dir, "local")

    assert gate_passed is True
    assert len(issues) == 0


def test_gate_6_warn_accessibility_issues(temp_run_dir):
    """Gate 6 warns on accessibility issues (but still passes)."""
    md_content = """---
title: Test
---

# Heading 1

### Heading 3 (skipped level 2)

![](image-no-alt.png)
"""

    site_dir = temp_run_dir / "work" / "site"
    (site_dir / "test.md").write_text(md_content)

    # Execute gate
    gate_passed, issues = gate_6_accessibility.execute_gate(temp_run_dir, "local")

    assert gate_passed is True  # Warnings don't fail gate
    assert len(issues) == 2  # Heading skip + missing alt text
    assert all(issue["severity"] == "warn" for issue in issues)


# =============================================================================
# Gate 7: Content Quality
# =============================================================================


def test_gate_7_pass_good_content(temp_run_dir):
    """Gate 7 passes with sufficient content and no placeholders."""
    md_content = """---
title: Test
---

This is a well-written page with plenty of content that exceeds the minimum
length requirement of one hundred characters. It contains useful information
without any placeholder dummy text. This content is substantial enough to
pass the quality gate requirements and demonstrates real documentation value.
"""

    site_dir = temp_run_dir / "work" / "site"
    (site_dir / "test.md").write_text(md_content)

    # Execute gate
    gate_passed, issues = gate_7_content_quality.execute_gate(temp_run_dir, "local")

    assert gate_passed is True
    assert len(issues) == 0


def test_gate_7_fail_lorem_ipsum(temp_run_dir):
    """Gate 7 fails when Lorem Ipsum placeholder text is found."""
    md_content = """---
title: Test
---

Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor
incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis
nostrud exercitation ullamco laboris.
"""

    site_dir = temp_run_dir / "work" / "site"
    (site_dir / "test.md").write_text(md_content)

    # Execute gate
    gate_passed, issues = gate_7_content_quality.execute_gate(temp_run_dir, "local")

    assert gate_passed is False
    # Should have Lorem Ipsum error (content length is now adequate)
    assert any(
        issue["error_code"] == "GATE_CONTENT_QUALITY_LOREM_IPSUM" for issue in issues
    )


# =============================================================================
# Gate 8: Claim Coverage
# =============================================================================


def test_gate_8_pass_all_claims_covered(temp_run_dir):
    """Gate 8 passes when all claims have evidence in content."""
    # Create product_facts with claims
    product_facts = {
        "claim_groups": [
            {"claim_id": "claim_001", "claim": "Claim 1"},
            {"claim_id": "claim_002", "claim": "Claim 2"},
        ]
    }

    with open(temp_run_dir / "artifacts" / "product_facts.json", "w") as f:
        json.dump(product_facts, f)

    # Create content referencing all claims
    md_content = """---
title: Test
---

Evidence for [claim:claim_001] and [claim:claim_002].
"""

    site_dir = temp_run_dir / "work" / "site"
    (site_dir / "test.md").write_text(md_content)

    # Execute gate
    gate_passed, issues = gate_8_claim_coverage.execute_gate(temp_run_dir, "local")

    assert gate_passed is True
    assert len(issues) == 0


def test_gate_8_warn_uncovered_claims(temp_run_dir):
    """Gate 8 warns when claims lack evidence (but still passes)."""
    # Create product_facts with claims
    product_facts = {
        "claim_groups": [
            {"claim_id": "claim_001", "claim": "Covered"},
            {"claim_id": "claim_002", "claim": "Uncovered"},
        ]
    }

    with open(temp_run_dir / "artifacts" / "product_facts.json", "w") as f:
        json.dump(product_facts, f)

    # Create content referencing only one claim
    md_content = """---
title: Test
---

Evidence for [claim:claim_001] only.
"""

    site_dir = temp_run_dir / "work" / "site"
    (site_dir / "test.md").write_text(md_content)

    # Execute gate
    gate_passed, issues = gate_8_claim_coverage.execute_gate(temp_run_dir, "local")

    assert gate_passed is True  # Warnings don't fail gate
    assert len(issues) == 1
    assert issues[0]["severity"] == "warn"
    assert issues[0]["error_code"] == "GATE_CLAIM_COVERAGE_MISSING"


# =============================================================================
# Gate 9: Navigation Integrity
# =============================================================================


def test_gate_9_pass_all_pages_planned(temp_run_dir):
    """Gate 9 passes when all pages match page_plan."""
    # Create page_plan
    page_plan = {
        "pages": [
            {"output_path": "test.md"},
            {"output_path": "about.md"},
        ]
    }

    with open(temp_run_dir / "artifacts" / "page_plan.json", "w") as f:
        json.dump(page_plan, f)

    # Create matching pages
    site_dir = temp_run_dir / "work" / "site"
    (site_dir / "test.md").write_text("---\ntitle: Test\n---\n\nContent")
    (site_dir / "about.md").write_text("---\ntitle: About\n---\n\nContent")

    # Execute gate
    gate_passed, issues = gate_9_navigation_integrity.execute_gate(temp_run_dir, "local")

    assert gate_passed is True
    assert len(issues) == 0


def test_gate_9_fail_missing_pages(temp_run_dir):
    """Gate 9 fails when planned pages are missing."""
    # Create page_plan with expected pages
    page_plan = {
        "pages": [
            {"output_path": "test.md"},
            {"output_path": "missing.md"},
        ]
    }

    with open(temp_run_dir / "artifacts" / "page_plan.json", "w") as f:
        json.dump(page_plan, f)

    # Create only one page
    site_dir = temp_run_dir / "work" / "site"
    (site_dir / "test.md").write_text("---\ntitle: Test\n---\n\nContent")

    # Execute gate
    gate_passed, issues = gate_9_navigation_integrity.execute_gate(temp_run_dir, "local")

    assert gate_passed is False
    assert len(issues) == 1
    assert issues[0]["error_code"] == "GATE_NAVIGATION_MISSING_PAGE"


# =============================================================================
# Gate 12: Patch Conflicts
# =============================================================================


def test_gate_12_pass_no_conflicts(temp_run_dir):
    """Gate 12 passes when no merge conflicts exist."""
    # Create patch_bundle without conflicts
    patch_bundle = {
        "patches": [
            {
                "patch_id": "patch_001",
                "target_file": "test.md",
                "content": "Clean content",
            }
        ]
    }

    with open(temp_run_dir / "artifacts" / "patch_bundle.json", "w") as f:
        json.dump(patch_bundle, f)

    # Create clean file
    site_dir = temp_run_dir / "work" / "site"
    (site_dir / "test.md").write_text("---\ntitle: Test\n---\n\nClean content")

    # Execute gate
    gate_passed, issues = gate_12_patch_conflicts.execute_gate(temp_run_dir, "local")

    assert gate_passed is True
    assert len(issues) == 0


def test_gate_12_fail_conflict_markers(temp_run_dir):
    """Gate 12 fails when merge conflict markers are found."""
    # Create file with conflict markers
    site_dir = temp_run_dir / "work" / "site"
    conflict_content = """---
title: Test
---

<<<<<<< HEAD
Version A
=======
Version B
>>>>>>> branch
"""

    (site_dir / "test.md").write_text(conflict_content)

    # Execute gate
    gate_passed, issues = gate_12_patch_conflicts.execute_gate(temp_run_dir, "local")

    assert gate_passed is False
    assert len(issues) >= 1
    assert all(issue["error_code"] == "GATE_PATCH_CONFLICT_MARKER" for issue in issues)
    assert all(issue["severity"] == "blocker" for issue in issues)


# =============================================================================
# Gate 13: Hugo Build
# =============================================================================


def test_gate_13_skip_no_hugo(temp_run_dir):
    """Gate 13 handles missing Hugo gracefully."""
    # Execute gate (Hugo not available or fails)
    gate_passed, issues = gate_13_hugo_build.execute_gate(temp_run_dir, "local")

    # Gate should fail if Hugo is missing or fails
    assert gate_passed is False
    assert len(issues) >= 1
    # Should have either tool missing or build failed error
    assert any(
        issue["error_code"]
        in ["GATE_HUGO_BUILD_TOOL_MISSING", "GATE_HUGO_BUILD_FAILED", "GATE_HUGO_BUILD_ERROR"]
        for issue in issues
    )


def test_gate_13_skip_no_site(temp_run_dir):
    """Gate 13 passes when no site directory exists."""
    # Remove site directory
    import shutil

    site_dir = temp_run_dir / "work" / "site"
    if site_dir.exists():
        shutil.rmtree(site_dir)

    # Execute gate
    gate_passed, issues = gate_13_hugo_build.execute_gate(temp_run_dir, "local")

    assert gate_passed is True
    assert len(issues) == 0


# =============================================================================
# Determinism Tests
# =============================================================================


def test_deterministic_issue_ordering(temp_run_dir):
    """Test that issues are returned in deterministic order."""
    # Create product_facts with multiple invalid claims
    product_facts = {"claim_groups": [{"claim_id": "claim_001", "claim": "Valid"}]}

    with open(temp_run_dir / "artifacts" / "product_facts.json", "w") as f:
        json.dump(product_facts, f)

    # Create markdown with multiple invalid references in random order
    md_content = """---
title: Test
---

Reference [claim:claim_zzz] and [claim:claim_aaa] and [claim:claim_mmm].
"""

    site_dir = temp_run_dir / "work" / "site"
    (site_dir / "test.md").write_text(md_content)

    # Execute gate multiple times
    results = [
        gate_2_claim_marker_validity.execute_gate(temp_run_dir, "local")
        for _ in range(3)
    ]

    # All results should be identical (deterministic)
    issue_ids_1 = [issue["issue_id"] for issue in results[0][1]]
    issue_ids_2 = [issue["issue_id"] for issue in results[1][1]]
    issue_ids_3 = [issue["issue_id"] for issue in results[2][1]]

    assert issue_ids_1 == issue_ids_2 == issue_ids_3
