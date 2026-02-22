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

from launch.workers.w9_validator.gates import (
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
    gate_15_api_hallucination,
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
    # claims[] is the list of claim objects; claim_groups is a dict mapping group->IDs
    product_facts = {
        "product_name": "TestLib",
        "claims": [
            {"claim_id": "claim_001", "claim_text": "Supports Python 3.8+"},
            {"claim_id": "claim_002", "claim_text": "Cross-platform"},
        ],
        "claim_groups": {"key_features": ["claim_001", "claim_002"]},
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
        "claims": [{"claim_id": "claim_001", "claim_text": "Valid claim"}],
        "claim_groups": {"key_features": ["claim_001"]},
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
description: A short description that is well within the 160-character SEO limit.
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
    # No errors or SEO warnings expected when all required + SEO fields are present
    error_issues = [i for i in issues if i["severity"] in ("error", "blocker")]
    seo_issues = [i for i in issues if i.get("error_code", "").startswith("G4-SEO")]
    assert len(error_issues) == 0
    assert len(seo_issues) == 0


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
    # 2 required field errors (missing layout and permalink) + 1 SEO warn (missing description)
    error_issues = [
        i for i in issues if i["error_code"] == "GATE_FRONTMATTER_REQUIRED_FIELD_MISSING"
    ]
    assert len(error_issues) == 2
    assert all(
        issue["error_code"] == "GATE_FRONTMATTER_REQUIRED_FIELD_MISSING"
        for issue in error_issues
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
    """Gate 7 passes with sufficient content (300+ words, H2 heading) and no placeholders."""
    # Generate 300+ words of real-looking documentation content with an H2 heading
    body_sentences = (
        "This library provides comprehensive support for processing documents in Python. "
        "Developers can use it to load, manipulate, and export documents in many formats. "
        "The API follows standard Python conventions and is well documented throughout. "
        "Installation is straightforward using pip and works on all major operating platforms. "
        "The library handles large files efficiently without excessive memory or CPU usage. "
        "Error handling is built-in and all exceptions are descriptive and actionable. "
        "Unit tests are provided for all public APIs to ensure long-term correctness. "
        "The library integrates with popular frameworks and tools in the Python ecosystem. "
        "Performance benchmarks show significant speed improvements over alternative solutions. "
        "Comprehensive examples are included to help developers get started quickly and easily. "
        "The project is actively maintained by a dedicated team and receives regular security updates. "
        "Community support is available through the official GitHub repository issue tracker. "
        "Documentation covers all major use cases with fully annotated and runnable code examples. "
        "The API surface is minimal and easy to learn within a few hours of focused study. "
        "Configuration options allow fine-grained control over all processing and rendering steps. "
        "The library supports both synchronous and asynchronous operation modes depending on context. "
        "Output formats include JSON, XML, PDF, and several standard document exchange formats. "
        "Logging integration makes debugging production issues straightforward and predictable. "
        "The library has no required third-party dependencies beyond the Python standard library. "
        "Type annotations are provided for all public functions, classes, and module-level constants. "
        "The changelog is maintained in a structured format to communicate breaking changes clearly. "
        "Platform-specific workarounds are documented and tested on Windows, macOS, and Linux alike. "
        "The library follows semantic versioning so that consumers can upgrade with confidence. "
        "Contribution guidelines describe how to submit bug reports and pull requests effectively. "
        "Release artifacts are published to PyPI on a regular cadence aligned with the roadmap. "
    )
    md_content = f"""---
title: Test
---

## Overview

{body_sentences}
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
    """Gate 8 passes when all claims are assigned in page_plan.json."""
    # Create product_facts with claims (TC-1629: claim_groups is dict[str, list[str]])
    product_facts = {
        "claim_groups": {
            "key_features": ["claim_001", "claim_002"]
        }
    }

    with open(temp_run_dir / "artifacts" / "product_facts.json", "w") as f:
        json.dump(product_facts, f)

    # Create page_plan.json assigning all claims to pages
    page_plan = {
        "pages": [
            {
                "slug": "getting-started",
                "output_path": "getting-started/index.md",
                "required_claim_ids": ["claim_001", "claim_002"],
            }
        ]
    }

    with open(temp_run_dir / "artifacts" / "page_plan.json", "w") as f:
        json.dump(page_plan, f)

    # Execute gate
    gate_passed, issues = gate_8_claim_coverage.execute_gate(temp_run_dir, "local")

    assert gate_passed is True
    assert len(issues) == 0


def test_gate_8_warn_uncovered_claims(temp_run_dir):
    """Gate 8 warns when claims are not assigned in page_plan (but still passes)."""
    # Create product_facts with claims (TC-1629: claim_groups is dict[str, list[str]])
    product_facts = {
        "claim_groups": {
            "key_features": ["claim_001", "claim_002"]
        }
    }

    with open(temp_run_dir / "artifacts" / "product_facts.json", "w") as f:
        json.dump(product_facts, f)

    # Create page_plan.json assigning only one claim
    page_plan = {
        "pages": [
            {
                "slug": "getting-started",
                "output_path": "getting-started/index.md",
                "required_claim_ids": ["claim_001"],
            }
        ]
    }

    with open(temp_run_dir / "artifacts" / "page_plan.json", "w") as f:
        json.dump(page_plan, f)

    # Execute gate
    gate_passed, issues = gate_8_claim_coverage.execute_gate(temp_run_dir, "local")

    assert gate_passed is True  # Warnings don't fail gate
    assert len(issues) == 1
    assert issues[0]["severity"] == "warn"
    assert issues[0]["error_code"] == "GATE_CLAIM_COVERAGE_MISSING"
    assert "page_plan" in issues[0]["message"]


def test_gate_8_page_plan_multiple_fields(temp_run_dir):
    """Gate 8 collects claim IDs from all page_plan fields (required_claim_ids,
    claim_ids, assigned_claims, content_strategy.claim_ids)."""
    product_facts = {
        "claim_groups": {
            "key_features": ["c1", "c2", "c3", "c4"]
        }
    }

    with open(temp_run_dir / "artifacts" / "product_facts.json", "w") as f:
        json.dump(product_facts, f)

    page_plan = {
        "pages": [
            {"slug": "page-a", "required_claim_ids": ["c1"]},
            {"slug": "page-b", "claim_ids": ["c2"]},
            {"slug": "page-c", "assigned_claims": ["c3"]},
            {"slug": "page-d", "content_strategy": {"claim_ids": ["c4"]}},
        ]
    }

    with open(temp_run_dir / "artifacts" / "page_plan.json", "w") as f:
        json.dump(page_plan, f)

    gate_passed, issues = gate_8_claim_coverage.execute_gate(temp_run_dir, "local")

    assert gate_passed is True
    assert len(issues) == 0


def test_gate_8_legacy_fallback_no_page_plan(temp_run_dir):
    """Gate 8 falls back to marker scanning when page_plan.json is absent."""
    product_facts = {
        "claim_groups": {
            "key_features": ["claim_001", "claim_002"]
        }
    }

    with open(temp_run_dir / "artifacts" / "product_facts.json", "w") as f:
        json.dump(product_facts, f)

    # No page_plan.json - should fall back to marker scanning
    md_content = """---
title: Test
---

Evidence for [claim:claim_001] and [claim:claim_002].
"""

    site_dir = temp_run_dir / "work" / "site"
    (site_dir / "test.md").write_text(md_content)

    gate_passed, issues = gate_8_claim_coverage.execute_gate(temp_run_dir, "local")

    assert gate_passed is True
    assert len(issues) == 0


def test_gate_8_legacy_fallback_empty_page_plan(temp_run_dir):
    """Gate 8 falls back to marker scanning when page_plan has no claim assignments."""
    product_facts = {
        "claim_groups": {
            "key_features": ["claim_001"]
        }
    }

    with open(temp_run_dir / "artifacts" / "product_facts.json", "w") as f:
        json.dump(product_facts, f)

    # page_plan exists but pages have no claim_id fields
    page_plan = {
        "pages": [
            {"slug": "page-a", "output_path": "page-a/index.md"}
        ]
    }

    with open(temp_run_dir / "artifacts" / "page_plan.json", "w") as f:
        json.dump(page_plan, f)

    # Provide marker-based content for fallback
    md_content = """---
title: Test
---

Evidence for <!-- claim: claim_001 -->.
"""

    site_dir = temp_run_dir / "work" / "site"
    (site_dir / "test.md").write_text(md_content)

    gate_passed, issues = gate_8_claim_coverage.execute_gate(temp_run_dir, "local")

    assert gate_passed is True
    assert len(issues) == 0


def test_gate_8_page_plan_partial_coverage_warns(temp_run_dir):
    """Gate 8 warns only for truly uncovered claims when page_plan covers most."""
    product_facts = {
        "claim_groups": {
            "key_features": ["c1", "c2", "c3"],
            "limitations": ["c4"],
        }
    }

    with open(temp_run_dir / "artifacts" / "product_facts.json", "w") as f:
        json.dump(product_facts, f)

    # page_plan covers c1, c2, c4 but NOT c3
    page_plan = {
        "pages": [
            {"slug": "features", "required_claim_ids": ["c1", "c2"]},
            {"slug": "limits", "required_claim_ids": ["c4"]},
        ]
    }

    with open(temp_run_dir / "artifacts" / "page_plan.json", "w") as f:
        json.dump(page_plan, f)

    gate_passed, issues = gate_8_claim_coverage.execute_gate(temp_run_dir, "local")

    assert gate_passed is True  # Warnings don't block
    assert len(issues) == 1
    assert "c3" in issues[0]["message"]
    assert "page_plan" in issues[0]["message"]


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
# Gate 6: Accessibility — Link Trailing Whitespace (TC-1833)
# =============================================================================


def test_gate_6_trailing_whitespace_detected(temp_run_dir):
    """Gate 6 detects trailing whitespace in markdown link URLs."""
    md_content = """---
title: Test
---

# Test

Visit [Example](https://example.com ) for more info.
"""

    site_dir = temp_run_dir / "work" / "site"
    (site_dir / "test.md").write_text(md_content)

    gate_passed, issues = gate_6_accessibility.execute_gate(temp_run_dir, "local")

    trailing_ws_issues = [
        i for i in issues if i.get("error_code") == "GATE_LINK_TRAILING_WHITESPACE"
    ]

    assert len(trailing_ws_issues) == 1
    assert trailing_ws_issues[0]["severity"] == "warn"
    assert "trailing whitespace" in trailing_ws_issues[0]["message"].lower()
    # Gate still passes (warnings only)
    assert gate_passed is True


def test_gate_6_clean_links_no_trailing_ws(temp_run_dir):
    """Gate 6 does not flag links without trailing whitespace."""
    md_content = """---
title: Test
---

# Test

Visit [Example](https://example.com) for more info.
See [Docs](/docs/api/) for reference.
"""

    site_dir = temp_run_dir / "work" / "site"
    (site_dir / "test.md").write_text(md_content)

    gate_passed, issues = gate_6_accessibility.execute_gate(temp_run_dir, "local")

    trailing_ws_issues = [
        i for i in issues if i.get("error_code") == "GATE_LINK_TRAILING_WHITESPACE"
    ]

    assert len(trailing_ws_issues) == 0
    assert gate_passed is True


# =============================================================================
# Gate 15: API Hallucination Detection (TC-1832)
# =============================================================================


def test_gate_15_pass_known_api(temp_run_dir):
    """Gate 15 passes when API references match known API surface."""
    product_facts = {
        "product_name": "TestLib",
        "api_surface_summary": {
            "classes": ["Scene", "Mesh", "Material"],
            "modules": [],
            "functions": [],
        },
    }

    with open(temp_run_dir / "artifacts" / "product_facts.json", "w") as f:
        json.dump(product_facts, f)

    md_content = """---
title: Test
---

# Test

Use `Scene` to create a 3D scene. Then add a `Mesh` and `Material`.
"""

    site_dir = temp_run_dir / "work" / "site"
    (site_dir / "test.md").write_text(md_content)

    gate_passed, issues = gate_15_api_hallucination.execute_gate(
        temp_run_dir, "local"
    )

    unrecognized = [
        i for i in issues if i.get("error_code") == "GATE15_UNRECOGNIZED_API"
    ]
    assert len(unrecognized) == 0
    assert gate_passed is True


def test_gate_15_detect_unknown_api(temp_run_dir):
    """Gate 15 detects unrecognized API references."""
    product_facts = {
        "product_name": "TestLib",
        "api_surface_summary": {
            "classes": ["Scene", "Mesh"],
            "modules": [],
            "functions": [],
        },
    }

    with open(temp_run_dir / "artifacts" / "product_facts.json", "w") as f:
        json.dump(product_facts, f)

    md_content = """---
title: Test
---

# Test

Use `Scene` to create a scene. Then use `FabricatedClass.nonexistent` method.
Also try `UnknownWidget` for rendering.
"""

    site_dir = temp_run_dir / "work" / "site"
    (site_dir / "test.md").write_text(md_content)

    gate_passed, issues = gate_15_api_hallucination.execute_gate(
        temp_run_dir, "local"
    )

    unrecognized = [
        i for i in issues if i.get("error_code") == "GATE15_UNRECOGNIZED_API"
    ]
    # Should detect FabricatedClass and UnknownWidget
    assert len(unrecognized) >= 2
    # Gate still passes (warnings only)
    assert gate_passed is True


def test_gate_15_skip_stdlib(temp_run_dir):
    """Gate 15 does not flag standard library types."""
    product_facts = {
        "product_name": "TestLib",
        "api_surface_summary": {
            "classes": ["Scene"],
            "modules": [],
            "functions": [],
        },
    }

    with open(temp_run_dir / "artifacts" / "product_facts.json", "w") as f:
        json.dump(product_facts, f)

    md_content = """---
title: Test
---

# Test

Use `Path` from pathlib. Handle `ValueError` and `TypeError` properly.
"""

    site_dir = temp_run_dir / "work" / "site"
    (site_dir / "test.md").write_text(md_content)

    gate_passed, issues = gate_15_api_hallucination.execute_gate(
        temp_run_dir, "local"
    )

    unrecognized = [
        i for i in issues if i.get("error_code") == "GATE15_UNRECOGNIZED_API"
    ]
    assert len(unrecognized) == 0
    assert gate_passed is True


def test_gate_15_no_api_surface_skips(temp_run_dir):
    """Gate 15 skips gracefully when no api_surface_summary exists."""
    product_facts = {
        "product_name": "TestLib",
    }

    with open(temp_run_dir / "artifacts" / "product_facts.json", "w") as f:
        json.dump(product_facts, f)

    gate_passed, issues = gate_15_api_hallucination.execute_gate(
        temp_run_dir, "local"
    )

    assert gate_passed is True
    # Should have an info-level message about missing API surface
    info_issues = [i for i in issues if i.get("severity") == "info"]
    assert len(info_issues) == 1
    assert "GATE15_API_SURFACE_MISSING" in info_issues[0].get("error_code", "")


def test_gate_15_no_product_facts_skips(temp_run_dir):
    """Gate 15 skips gracefully when product_facts.json is missing."""
    gate_passed, issues = gate_15_api_hallucination.execute_gate(
        temp_run_dir, "local"
    )

    assert gate_passed is True
    info_issues = [i for i in issues if i.get("severity") == "info"]
    assert len(info_issues) == 1


def test_gate_15_skips_code_blocks(temp_run_dir):
    """Gate 15 does not flag API references inside code blocks."""
    product_facts = {
        "product_name": "TestLib",
        "api_surface_summary": {
            "classes": ["Scene"],
            "modules": [],
            "functions": [],
        },
    }

    with open(temp_run_dir / "artifacts" / "product_facts.json", "w") as f:
        json.dump(product_facts, f)

    md_content = """---
title: Test
---

# Test

```python
# This code block references unknown APIs but should be skipped
widget = UnknownWidget()
result = FabricatedClass.method()
```

Only `Scene` is used in prose.
"""

    site_dir = temp_run_dir / "work" / "site"
    (site_dir / "test.md").write_text(md_content)

    gate_passed, issues = gate_15_api_hallucination.execute_gate(
        temp_run_dir, "local"
    )

    unrecognized = [
        i for i in issues if i.get("error_code") == "GATE15_UNRECOGNIZED_API"
    ]
    assert len(unrecognized) == 0
    assert gate_passed is True


# =============================================================================
# Gate 15: code_analysis.json Merge (TC-1900)
# =============================================================================


def test_gate_15_merges_code_analysis_symbols(temp_run_dir):
    """Gate 15 merges code_analysis.json symbols into the allowlist (TC-1900).

    ClassA comes from api_surface_summary, ClassB from code_analysis.json.
    Neither should trigger a warning.
    """
    product_facts = {
        "product_name": "TestLib",
        "api_surface_summary": {
            "classes": ["ClassA"],
            "modules": [],
            "functions": [],
        },
    }

    with open(temp_run_dir / "artifacts" / "product_facts.json", "w") as f:
        json.dump(product_facts, f)

    code_analysis = {
        "classes": [{"name": "ClassB"}],
        "functions": [{"name": "helper_func"}],
    }

    with open(temp_run_dir / "artifacts" / "code_analysis.json", "w") as f:
        json.dump(code_analysis, f)

    md_content = """---
title: Test
---

# Test

Use `ClassA` from the main API. Also use `ClassB` from AST parsing.
"""

    site_dir = temp_run_dir / "work" / "site"
    (site_dir / "test.md").write_text(md_content)

    gate_passed, issues = gate_15_api_hallucination.execute_gate(
        temp_run_dir, "local"
    )

    unrecognized = [
        i for i in issues if i.get("error_code") == "GATE15_UNRECOGNIZED_API"
    ]
    assert len(unrecognized) == 0
    assert gate_passed is True


def test_gate_15_works_without_code_analysis(temp_run_dir):
    """Gate 15 works when code_analysis.json is missing (backward compat, TC-1900).

    Only api_surface_summary symbols are in the allowlist. An unknown symbol
    not in either source should still be flagged.
    """
    product_facts = {
        "product_name": "TestLib",
        "api_surface_summary": {
            "classes": ["ClassA"],
            "modules": [],
            "functions": [],
        },
    }

    with open(temp_run_dir / "artifacts" / "product_facts.json", "w") as f:
        json.dump(product_facts, f)

    # No code_analysis.json — should not crash

    md_content = """---
title: Test
---

# Test

Use `ClassA` (known). But `UnknownWidget` is not in any source.
"""

    site_dir = temp_run_dir / "work" / "site"
    (site_dir / "test.md").write_text(md_content)

    gate_passed, issues = gate_15_api_hallucination.execute_gate(
        temp_run_dir, "local"
    )

    unrecognized = [
        i for i in issues if i.get("error_code") == "GATE15_UNRECOGNIZED_API"
    ]
    # ClassA is known, UnknownWidget is not
    assert len(unrecognized) == 1
    assert "UnknownWidget" in unrecognized[0]["message"]
    assert gate_passed is True


# =============================================================================
# Gate 14: Cross-Section Overlap Threshold (TC-1905)
# =============================================================================


def test_gate_14_no_warn_two_section_overlap():
    """Gate 14 does not warn when a claim appears in exactly 2 sections (TC-1905).

    By design, 2-section overlap is acceptable.
    """
    from launch.workers.w9_validator.worker import validate_content_distribution

    page_plan = {
        "pages": [
            {
                "slug": "page-a",
                "section": "products",
                "required_claim_ids": ["claim_001"],
            },
            {
                "slug": "page-b",
                "section": "docs",
                "required_claim_ids": ["claim_001"],
            },
        ]
    }

    product_facts = {"product_name": "TestLib"}

    with tempfile.TemporaryDirectory() as tmpdir:
        site_dir = Path(tmpdir) / "site"
        site_dir.mkdir()

        issues = validate_content_distribution(
            page_plan, product_facts, site_dir, profile="local"
        )

    cross_section = [
        i for i in issues if i.get("error_code") == "GATE14_CLAIM_CROSS_SECTION"
    ]
    assert len(cross_section) == 0


def test_gate_14_warns_three_section_overlap():
    """Gate 14 warns when a claim appears in 3+ sections (TC-1905).

    3-section overlap is suspicious and should produce a warning.
    """
    from launch.workers.w9_validator.worker import validate_content_distribution

    page_plan = {
        "pages": [
            {
                "slug": "page-a",
                "section": "products",
                "required_claim_ids": ["claim_001"],
            },
            {
                "slug": "page-b",
                "section": "docs",
                "required_claim_ids": ["claim_001"],
            },
            {
                "slug": "page-c",
                "section": "tutorials",
                "required_claim_ids": ["claim_001"],
            },
        ]
    }

    product_facts = {"product_name": "TestLib"}

    with tempfile.TemporaryDirectory() as tmpdir:
        site_dir = Path(tmpdir) / "site"
        site_dir.mkdir()

        issues = validate_content_distribution(
            page_plan, product_facts, site_dir, profile="local"
        )

    cross_section = [
        i for i in issues if i.get("error_code") == "GATE14_CLAIM_CROSS_SECTION"
    ]
    assert len(cross_section) == 1
    assert "claim_001" in cross_section[0]["message"]


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
