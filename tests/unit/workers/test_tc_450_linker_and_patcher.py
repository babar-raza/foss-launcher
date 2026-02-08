"""TC-450: W6 LinkerAndPatcher worker tests.

This module tests the W6 LinkerAndPatcher worker implementation per
specs/08_patch_engine.md and specs/21_worker_contracts.md:228-251.

Test coverage:
1. Patch generation from drafts
2. Patch application (create_file, update_by_anchor, update_frontmatter_keys)
3. Idempotency (re-running produces same result)
4. Deterministic ordering (stable patch order)
5. Event emission
6. Artifact validation
7. Error handling (missing drafts, conflicts, allowed_paths violations)
8. Navigation generation (placeholder)
9. Diff report generation
10. Content hash verification
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from src.launch.workers.w6_linker_and_patcher import (
    execute_linker_and_patcher,
    LinkerAndPatcherError,
    LinkerNoDraftsError,
    LinkerPatchConflictError,
    LinkerAllowedPathsViolationError,
)
from src.launch.workers.w6_linker_and_patcher.worker import (
    compute_content_hash,
    validate_allowed_path,
    parse_frontmatter,
    update_frontmatter,
    find_anchor_in_content,
    insert_content_at_anchor,
    generate_patches_from_drafts,
    apply_patch,
    generate_diff_report,
)


@pytest.fixture
def temp_run_dir():
    """Create temporary run directory with required structure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = Path(tmpdir) / "run"
        run_dir.mkdir()

        # Create required subdirectories
        (run_dir / "artifacts").mkdir()
        (run_dir / "reports").mkdir()
        (run_dir / "drafts").mkdir()
        (run_dir / "work" / "site" / "content").mkdir(parents=True)

        # Create events.ndjson
        (run_dir / "events.ndjson").write_text("")

        yield run_dir


@pytest.fixture
def sample_page_plan():
    """Sample page plan for testing."""
    return {
        "schema_version": "1.0",
        "product_slug": "test-product",
        "launch_tier": "standard",
        "pages": [
            {
                "section": "docs",
                "slug": "getting-started",
                "output_path": "content/docs.aspose.org/test-product/en/python/docs/getting-started.md",
                "url_path": "/test-product/python/getting-started/",
                "title": "Getting Started",
                "purpose": "Installation and basic usage guide",
            },
            {
                "section": "products",
                "slug": "overview",
                "output_path": "content/docs.aspose.org/test-product/en/python/overview.md",
                "url_path": "/test-product/python/overview/",
                "title": "Product Overview",
                "purpose": "Product overview and positioning",
            },
        ],
    }


@pytest.fixture
def sample_draft_manifest(temp_run_dir):
    """Sample draft manifest for testing."""
    # Create draft files
    docs_dir = temp_run_dir / "drafts" / "docs"
    docs_dir.mkdir(parents=True)

    products_dir = temp_run_dir / "drafts" / "products"
    products_dir.mkdir(parents=True)

    getting_started_content = """# Getting Started

## Installation

Install the package using pip:

```python
pip install test-product
```

## Basic Usage

Import and use the library:

```python
from test_product import Client

client = Client()
client.do_something()
```
"""

    overview_content = """# Product Overview

Test Product is a powerful library for document processing.

## Key Features

- Fast and efficient
- Easy to use
- Well documented
"""

    (docs_dir / "getting-started.md").write_text(getting_started_content)
    (products_dir / "overview.md").write_text(overview_content)

    return {
        "schema_version": "1.0",
        "run_id": "test-run-001",
        "total_pages": 2,
        "draft_count": 2,
        "drafts": [
            {
                "page_id": "docs_getting-started",
                "section": "docs",
                "slug": "getting-started",
                "output_path": "content/docs.aspose.org/test-product/en/python/docs/getting-started.md",
                "draft_path": "drafts/docs/getting-started.md",
                "title": "Getting Started",
                "word_count": 30,
                "claim_count": 0,
            },
            {
                "page_id": "products_overview",
                "section": "products",
                "slug": "overview",
                "output_path": "content/docs.aspose.org/test-product/en/python/overview.md",
                "draft_path": "drafts/products/overview.md",
                "title": "Product Overview",
                "word_count": 20,
                "claim_count": 0,
            },
        ],
    }


# Test 1: Content hash computation
def test_compute_content_hash():
    """Test SHA256 content hash computation."""
    content = "Hello, world!"
    hash1 = compute_content_hash(content)
    hash2 = compute_content_hash(content)

    # Hash should be deterministic
    assert hash1 == hash2
    assert len(hash1) == 64  # SHA256 hex is 64 chars
    assert hash1 == "315f5bdb76d078c43b8ac0064e4a0164612b1fce77c869345bfc94c75894edd3"


# Test 2: Allowed path validation
def test_validate_allowed_path():
    """Test allowed path validation logic."""
    site_worktree = Path("/tmp/site")
    target_path = Path("/tmp/site/content/docs/page.md")

    # No restrictions - should allow
    assert validate_allowed_path(target_path, site_worktree, None) is True

    # With allowed_paths matching
    assert validate_allowed_path(
        target_path, site_worktree, ["content/docs", "content/products"]
    ) is True

    # With allowed_paths not matching
    assert validate_allowed_path(
        target_path, site_worktree, ["content/kb"]
    ) is False

    # Path outside site_worktree
    outside_path = Path("/tmp/other/file.md")
    assert validate_allowed_path(outside_path, site_worktree, None) is False


# Test 3: Frontmatter parsing
def test_parse_frontmatter():
    """Test YAML frontmatter parsing."""
    content_with_fm = """---
title: Test Page
weight: 10
---

# Content here
"""

    frontmatter, body = parse_frontmatter(content_with_fm)
    assert frontmatter is not None
    assert "title: Test Page" in frontmatter
    assert "# Content here" in body

    # Content without frontmatter
    content_without_fm = "# Just content"
    frontmatter, body = parse_frontmatter(content_without_fm)
    assert frontmatter is None
    assert body == content_without_fm


# Test 4: Frontmatter update
def test_update_frontmatter():
    """Test frontmatter key updates."""
    import yaml

    content = """---
title: Original Title
weight: 5
---

Body content
"""

    # Update existing key
    updated = update_frontmatter(content, {"weight": 10})
    fm, _ = parse_frontmatter(updated)
    fm_dict = yaml.safe_load(fm)
    assert fm_dict["weight"] == 10
    assert fm_dict["title"] == "Original Title"

    # Add new key
    updated = update_frontmatter(content, {"author": "Test Author"})
    fm, _ = parse_frontmatter(updated)
    fm_dict = yaml.safe_load(fm)
    assert fm_dict["author"] == "Test Author"


# Test 5: Anchor finding
def test_find_anchor_in_content():
    """Test markdown anchor heading detection."""
    content = """# Main Title

## Installation

Some content here.

## Usage

More content.

### Subsection

Details.
"""

    # Find existing anchors
    assert find_anchor_in_content(content, "## Installation") == 2
    assert find_anchor_in_content(content, "Installation") == 2
    assert find_anchor_in_content(content, "## Usage") == 6

    # Non-existent anchor
    assert find_anchor_in_content(content, "## Not Found") is None


# Test 6: Content insertion at anchor
def test_insert_content_at_anchor():
    """Test content insertion under anchor heading."""
    content = """# Title

## Section 1

Existing content.

## Section 2

More content.
"""

    new_content = "New paragraph here."
    updated = insert_content_at_anchor(content, "Section 1", new_content)

    assert "New paragraph here." in updated
    # Should be after Section 1 heading
    lines = updated.split("\n")
    section1_idx = next(i for i, line in enumerate(lines) if "Section 1" in line)
    new_content_idx = next(i for i, line in enumerate(lines) if "New paragraph here." in line)
    assert new_content_idx > section1_idx

    # Test anchor not found
    with pytest.raises(LinkerPatchConflictError):
        insert_content_at_anchor(content, "Non Existent", new_content)


# Test 7: Patch generation from drafts
def test_generate_patches_from_drafts(temp_run_dir, sample_draft_manifest, sample_page_plan):
    """Test patch generation from draft files."""
    site_worktree = temp_run_dir / "work" / "site"

    patches = generate_patches_from_drafts(
        draft_manifest=sample_draft_manifest,
        page_plan=sample_page_plan,
        run_dir=temp_run_dir,
        site_worktree=site_worktree,
    )

    # Should generate 2 create_file patches (files don't exist)
    assert len(patches) == 2

    # Check patch structure
    for patch in patches:
        assert "patch_id" in patch
        assert "type" in patch
        assert patch["type"] == "create_file"
        assert "path" in patch
        assert "new_content" in patch
        assert "content_hash" in patch

    # Check deterministic ordering (by output_path)
    assert patches[0]["path"] < patches[1]["path"]


# Test 8: Patch application - create_file
def test_apply_patch_create_file(temp_run_dir):
    """Test create_file patch application."""
    site_worktree = temp_run_dir / "work" / "site"
    target_path = site_worktree / "content" / "test.md"

    content = "# Test Page\n\nContent here."
    patch = {
        "patch_id": "create_test",
        "type": "create_file",
        "path": "content/test.md",
        "new_content": content,
        "content_hash": compute_content_hash(content),
    }

    result = apply_patch(patch, site_worktree)

    assert result["status"] == "applied"
    assert target_path.exists()
    assert target_path.read_text(encoding="utf-8") == content

    # Test idempotency - re-applying should skip
    result2 = apply_patch(patch, site_worktree)
    assert result2["status"] == "skipped"


# Test 9: Patch application - update_frontmatter_keys
def test_apply_patch_update_frontmatter(temp_run_dir):
    """Test update_frontmatter_keys patch application."""
    site_worktree = temp_run_dir / "work" / "site"
    target_path = site_worktree / "content" / "test.md"

    # Create initial file with frontmatter
    initial_content = """---
title: Original
weight: 5
---

Body content
"""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(initial_content)

    patch = {
        "patch_id": "update_fm_test",
        "type": "update_frontmatter_keys",
        "path": "content/test.md",
        "frontmatter_updates": {"weight": 10, "author": "Test"},
        "content_hash": "placeholder",
    }

    result = apply_patch(patch, site_worktree)

    assert result["status"] == "applied"

    # Verify frontmatter updated
    import yaml
    updated_content = target_path.read_text(encoding="utf-8")
    fm, _ = parse_frontmatter(updated_content)
    fm_dict = yaml.safe_load(fm)
    assert fm_dict["weight"] == 10
    assert fm_dict["author"] == "Test"


# Test 10: Patch application - update_by_anchor
def test_apply_patch_update_by_anchor(temp_run_dir):
    """Test update_by_anchor patch application."""
    site_worktree = temp_run_dir / "work" / "site"
    target_path = site_worktree / "content" / "test.md"

    # Create initial file
    initial_content = """# Test Page

## Installation

Initial installation instructions.

## Usage

Usage instructions.
"""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(initial_content)

    new_content = "Additional installation step."
    patch = {
        "patch_id": "update_anchor_test",
        "type": "update_by_anchor",
        "path": "content/test.md",
        "anchor": "Installation",
        "new_content": new_content,
        "content_hash": "placeholder",
    }

    result = apply_patch(patch, site_worktree)

    assert result["status"] == "applied"

    # Verify content inserted
    updated_content = target_path.read_text(encoding="utf-8")
    assert new_content in updated_content

    # Test idempotency - re-applying should skip
    result2 = apply_patch(patch, site_worktree)
    assert result2["status"] == "skipped"


# Test 11: Error handling - missing drafts
def test_error_missing_drafts(temp_run_dir):
    """Test error when no drafts are found."""
    # Create minimal run config
    run_config = {
        "run_id": "test-run-001",
    }

    # Create empty draft_manifest
    draft_manifest = {
        "schema_version": "1.0",
        "run_id": "test-run-001",
        "total_pages": 0,
        "draft_count": 0,
        "drafts": [],
    }

    (temp_run_dir / "artifacts" / "draft_manifest.json").write_text(
        json.dumps(draft_manifest)
    )

    # Create minimal page_plan
    page_plan = {
        "schema_version": "1.0",
        "product_slug": "test-product",
        "launch_tier": "minimal",
        "pages": [],
    }

    (temp_run_dir / "artifacts" / "page_plan.json").write_text(
        json.dumps(page_plan)
    )

    with pytest.raises(LinkerNoDraftsError):
        execute_linker_and_patcher(temp_run_dir, run_config)


# Test 12: Error handling - allowed_paths violation
def test_error_allowed_paths_violation(temp_run_dir):
    """Test error when patch targets file outside allowed_paths."""
    site_worktree = temp_run_dir / "work" / "site"

    patch = {
        "patch_id": "test_violation",
        "type": "create_file",
        "path": "etc/passwd",  # Outside allowed paths
        "new_content": "evil content",
        "content_hash": "placeholder",
    }

    allowed_paths = ["content/docs", "content/products"]

    with pytest.raises(LinkerAllowedPathsViolationError):
        apply_patch(patch, site_worktree, allowed_paths)


# Test 13: Deterministic ordering
def test_deterministic_patch_ordering(temp_run_dir, sample_draft_manifest, sample_page_plan):
    """Test that patch generation produces deterministic ordering."""
    site_worktree = temp_run_dir / "work" / "site"

    patches1 = generate_patches_from_drafts(
        draft_manifest=sample_draft_manifest,
        page_plan=sample_page_plan,
        run_dir=temp_run_dir,
        site_worktree=site_worktree,
    )

    patches2 = generate_patches_from_drafts(
        draft_manifest=sample_draft_manifest,
        page_plan=sample_page_plan,
        run_dir=temp_run_dir,
        site_worktree=site_worktree,
    )

    # Should produce same order
    assert len(patches1) == len(patches2)
    for p1, p2 in zip(patches1, patches2):
        assert p1["patch_id"] == p2["patch_id"]
        assert p1["path"] == p2["path"]


# Test 14: Event emission
def test_event_emission(temp_run_dir, sample_draft_manifest, sample_page_plan):
    """Test that worker emits required events."""
    run_config = {
        "run_id": "test-run-001",
    }

    # Save artifacts
    (temp_run_dir / "artifacts" / "page_plan.json").write_text(
        json.dumps(sample_page_plan)
    )
    (temp_run_dir / "artifacts" / "draft_manifest.json").write_text(
        json.dumps(sample_draft_manifest)
    )

    result = execute_linker_and_patcher(temp_run_dir, run_config)

    assert result["status"] == "success"

    # Check events.ndjson
    events_file = temp_run_dir / "events.ndjson"
    assert events_file.exists()

    events = []
    for line in events_file.read_text().strip().split("\n"):
        if line:
            events.append(json.loads(line))

    # Should have at least: STARTED, ARTIFACT_WRITTEN (patch_bundle), FINISHED
    event_types = [e["type"] for e in events]
    assert "WORK_ITEM_STARTED" in event_types
    assert "WORK_ITEM_FINISHED" in event_types
    assert "ARTIFACT_WRITTEN" in event_types


# Test 15: Artifact validation
def test_artifact_validation(temp_run_dir, sample_draft_manifest, sample_page_plan):
    """Test that generated artifacts validate against schema."""
    run_config = {
        "run_id": "test-run-001",
    }

    # Save artifacts
    (temp_run_dir / "artifacts" / "page_plan.json").write_text(
        json.dumps(sample_page_plan)
    )
    (temp_run_dir / "artifacts" / "draft_manifest.json").write_text(
        json.dumps(sample_draft_manifest)
    )

    result = execute_linker_and_patcher(temp_run_dir, run_config)

    # Check patch_bundle.json
    patch_bundle_path = Path(result["patch_bundle_path"])
    assert patch_bundle_path.exists()

    patch_bundle = json.loads(patch_bundle_path.read_text())
    assert "schema_version" in patch_bundle
    assert "patches" in patch_bundle
    assert isinstance(patch_bundle["patches"], list)

    # Each patch should have required fields
    for patch in patch_bundle["patches"]:
        assert "patch_id" in patch
        assert "type" in patch
        assert "path" in patch
        assert "content_hash" in patch


# Test 16: Diff report generation
def test_diff_report_generation(temp_run_dir, sample_draft_manifest, sample_page_plan):
    """Test diff report generation."""
    run_config = {
        "run_id": "test-run-001",
    }

    # Save artifacts
    (temp_run_dir / "artifacts" / "page_plan.json").write_text(
        json.dumps(sample_page_plan)
    )
    (temp_run_dir / "artifacts" / "draft_manifest.json").write_text(
        json.dumps(sample_draft_manifest)
    )

    result = execute_linker_and_patcher(temp_run_dir, run_config)

    # Check diff_report.md
    diff_report_path = Path(result["diff_report_path"])
    assert diff_report_path.exists()

    diff_report = diff_report_path.read_text()
    assert "# Patch Application Report" in diff_report
    assert "Total Patches" in diff_report
    assert "Applied" in diff_report


# Test 17: Full worker execution
def test_full_worker_execution(temp_run_dir, sample_draft_manifest, sample_page_plan):
    """Test complete worker execution end-to-end."""
    run_config = {
        "run_id": "test-run-001",
    }

    # Save artifacts
    (temp_run_dir / "artifacts" / "page_plan.json").write_text(
        json.dumps(sample_page_plan)
    )
    (temp_run_dir / "artifacts" / "draft_manifest.json").write_text(
        json.dumps(sample_draft_manifest)
    )

    result = execute_linker_and_patcher(temp_run_dir, run_config)

    # Verify result
    assert result["status"] == "success"
    assert "patch_bundle_path" in result
    assert "diff_report_path" in result
    assert result["patches_applied"] == 2  # 2 new files created
    assert result["patches_skipped"] == 0

    # Verify files created in site worktree
    site_worktree = temp_run_dir / "work" / "site"
    for draft in sample_draft_manifest["drafts"]:
        target_path = site_worktree / draft["output_path"]
        assert target_path.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
