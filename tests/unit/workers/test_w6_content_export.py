"""TC-952: W6 Content Export tests.

This module tests the content preview export functionality added to W6 LinkerAndPatcher
per TC-952: Export Content Preview for .md Visibility.

Test coverage:
1. Content export creates correct directory structure
2. Export preserves subdomain paths
3. Export includes all applied patches
4. Export covers multiple subdomains (docs, reference, products, kb, blog)
5. Export count matches applied patches
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from src.launch.workers.w6_linker_and_patcher import execute_linker_and_patcher


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
def multi_subdomain_page_plan():
    """Page plan covering all 5 subdomains."""
    return {
        "schema_version": "1.0",
        "product_slug": "3d",
        "launch_tier": "standard",
        "pages": [
            {
                "section": "docs",
                "slug": "installation",
                "output_path": "content/docs.aspose.org/3d/en/python/installation/index.md",
                "url_path": "/3d/python/installation/",
                "title": "Installation Guide",
                "purpose": "Installation instructions",
            },
            {
                "section": "reference",
                "slug": "scene",
                "output_path": "content/reference.aspose.org/3d/en/python/aspose.threed/scene.md",
                "url_path": "/3d/python/aspose.threed/scene/",
                "title": "Scene Class",
                "purpose": "API reference for Scene class",
            },
            {
                "section": "products",
                "slug": "overview",
                "output_path": "content/products.aspose.org/3d/en/python/overview.md",
                "url_path": "/3d/python/overview/",
                "title": "Product Overview",
                "purpose": "Product overview page",
            },
            {
                "section": "kb",
                "slug": "how-to-install",
                "output_path": "content/kb.aspose.org/3d/en/python/how-to-install.md",
                "url_path": "/3d/python/how-to-install/",
                "title": "How to Install",
                "purpose": "Knowledge base article",
            },
            {
                "section": "blog",
                "slug": "release-notes",
                "output_path": "content/blog.aspose.org/3d/python/release-notes/index.md",
                "url_path": "/3d/python/release-notes/",
                "title": "Release Notes",
                "purpose": "Blog post about release",
            },
        ],
    }


@pytest.fixture
def multi_subdomain_draft_manifest(temp_run_dir):
    """Draft manifest with 5 drafts across different subdomains."""
    # Create draft files
    drafts_dir = temp_run_dir / "drafts"

    # Docs draft
    docs_dir = drafts_dir / "docs"
    docs_dir.mkdir(parents=True)
    (docs_dir / "installation.md").write_text("""---
title: Installation Guide
weight: 10
---

# Installation

Install Aspose.3D for Python via pip:

```bash
pip install aspose-3d-python
```
""")

    # Reference draft
    reference_dir = drafts_dir / "reference"
    reference_dir.mkdir(parents=True)
    (reference_dir / "scene.md").write_text("""---
title: Scene Class
api_type: class
---

# Scene

The Scene class represents a 3D scene.

## Methods

- `save()` - Save the scene to file
""")

    # Products draft
    products_dir = drafts_dir / "products"
    products_dir.mkdir(parents=True)
    (products_dir / "overview.md").write_text("""---
title: Product Overview
weight: 1
---

# Aspose.3D for Python

A powerful 3D file processing library for Python.

## Key Features

- Load and save 3D files
- Convert between formats
""")

    # KB draft
    kb_dir = drafts_dir / "kb"
    kb_dir.mkdir(parents=True)
    (kb_dir / "how-to-install.md").write_text("""---
title: How to Install
category: installation
---

# How to Install Aspose.3D for Python

This guide shows you how to install the library.

## Prerequisites

- Python 3.7 or higher
- pip package manager
""")

    # Blog draft
    blog_dir = drafts_dir / "blog"
    blog_dir.mkdir(parents=True)
    (blog_dir / "release-notes.md").write_text("""---
title: Release Notes - January 2026
date: 2026-01-15
---

# Aspose.3D for Python - January 2026 Release

We are excited to announce the latest release.

## New Features

- Improved performance
- New file format support
""")

    return {
        "schema_version": "1.0",
        "run_id": "test-run-tc952",
        "total_pages": 5,
        "draft_count": 5,
        "drafts": [
            {
                "page_id": "docs_installation",
                "section": "docs",
                "slug": "installation",
                "output_path": "content/docs.aspose.org/3d/en/python/installation/index.md",
                "draft_path": "drafts/docs/installation.md",
                "title": "Installation Guide",
                "word_count": 20,
                "claim_count": 0,
            },
            {
                "page_id": "reference_scene",
                "section": "reference",
                "slug": "scene",
                "output_path": "content/reference.aspose.org/3d/en/python/aspose.threed/scene.md",
                "draft_path": "drafts/reference/scene.md",
                "title": "Scene Class",
                "word_count": 25,
                "claim_count": 0,
            },
            {
                "page_id": "products_overview",
                "section": "products",
                "slug": "overview",
                "output_path": "content/products.aspose.org/3d/en/python/overview.md",
                "draft_path": "drafts/products/overview.md",
                "title": "Product Overview",
                "word_count": 30,
                "claim_count": 0,
            },
            {
                "page_id": "kb_how_to_install",
                "section": "kb",
                "slug": "how-to-install",
                "output_path": "content/kb.aspose.org/3d/en/python/how-to-install.md",
                "draft_path": "drafts/kb/how-to-install.md",
                "title": "How to Install",
                "word_count": 35,
                "claim_count": 0,
            },
            {
                "page_id": "blog_release_notes",
                "section": "blog",
                "slug": "release-notes",
                "output_path": "content/blog.aspose.org/3d/python/release-notes/index.md",
                "draft_path": "drafts/blog/release-notes.md",
                "title": "Release Notes",
                "word_count": 40,
                "claim_count": 0,
            },
        ],
    }


def test_content_export_multiple_subdomains(temp_run_dir, multi_subdomain_draft_manifest, multi_subdomain_page_plan):
    """Test that content export creates correct file tree across all 5 subdomains.

    TC-952 Acceptance Criteria:
    - Content preview folder created in run_dir
    - Real .md files organized by subdomain
    - Export is deterministic
    - Covers ALL subdomains (docs, reference, products, kb, blog)
    """
    run_config = {
        "run_id": "test-run-tc952",
    }

    # Save artifacts
    (temp_run_dir / "artifacts" / "page_plan.json").write_text(
        json.dumps(multi_subdomain_page_plan)
    )
    (temp_run_dir / "artifacts" / "draft_manifest.json").write_text(
        json.dumps(multi_subdomain_draft_manifest)
    )

    # Execute W6
    result = execute_linker_and_patcher(temp_run_dir, run_config)

    # Verify result includes new fields
    assert result["status"] == "success"
    assert "content_preview_dir" in result, "content_preview_dir missing from result"
    assert "exported_files_count" in result, "exported_files_count missing from result"
    assert result["exported_files_count"] == 5, f"Expected 5 exported files, got {result['exported_files_count']}"

    # Verify content_preview directory exists
    content_preview_dir = temp_run_dir / result["content_preview_dir"]
    assert content_preview_dir.exists(), f"Content preview dir does not exist: {content_preview_dir}"
    assert content_preview_dir.is_dir(), "Content preview dir is not a directory"

    # Verify all 5 subdomain files exist with correct paths
    docs_file = content_preview_dir / "content/docs.aspose.org/3d/en/python/installation/index.md"
    reference_file = content_preview_dir / "content/reference.aspose.org/3d/en/python/aspose.threed/scene.md"
    products_file = content_preview_dir / "content/products.aspose.org/3d/en/python/overview.md"
    kb_file = content_preview_dir / "content/kb.aspose.org/3d/en/python/how-to-install.md"
    blog_file = content_preview_dir / "content/blog.aspose.org/3d/python/release-notes/index.md"

    assert docs_file.exists(), f"Docs file missing: {docs_file}"
    assert reference_file.exists(), f"Reference file missing: {reference_file}"
    assert products_file.exists(), f"Products file missing: {products_file}"
    assert kb_file.exists(), f"KB file missing: {kb_file}"
    assert blog_file.exists(), f"Blog file missing: {blog_file}"

    # Verify file contents are correct (not empty)
    assert "Installation" in docs_file.read_text(encoding="utf-8"), "Docs file content incorrect"
    assert "Scene" in reference_file.read_text(encoding="utf-8"), "Reference file content incorrect"
    assert "Product Overview" in products_file.read_text(encoding="utf-8"), "Products file content incorrect"
    assert "Prerequisites" in kb_file.read_text(encoding="utf-8"), "KB file content incorrect"
    assert "Release Notes" in blog_file.read_text(encoding="utf-8"), "Blog file content incorrect"

    # Verify subdomain structure is preserved
    assert (content_preview_dir / "content/docs.aspose.org").is_dir(), "docs.aspose.org subdomain dir missing"
    assert (content_preview_dir / "content/reference.aspose.org").is_dir(), "reference.aspose.org subdomain dir missing"
    assert (content_preview_dir / "content/products.aspose.org").is_dir(), "products.aspose.org subdomain dir missing"
    assert (content_preview_dir / "content/kb.aspose.org").is_dir(), "kb.aspose.org subdomain dir missing"
    assert (content_preview_dir / "content/blog.aspose.org").is_dir(), "blog.aspose.org subdomain dir missing"


def test_content_export_only_applied_patches(temp_run_dir):
    """Test that content export only includes patches with status='applied'.

    When a patch is skipped (idempotent, already applied), it should NOT be exported.
    Note: In current implementation, idempotent files are skipped during patch generation
    (no patch created), not during patch application.
    """
    run_config = {
        "run_id": "test-run-applied-only",
    }

    # Create a setup with two files: one new, one already exists
    page_plan = {
        "schema_version": "1.0",
        "product_slug": "test",
        "launch_tier": "minimal",
        "pages": [
            {
                "section": "docs",
                "slug": "new-file",
                "output_path": "content/docs.aspose.org/test/en/python/new-file.md",
                "url_path": "/test/python/new-file/",
                "title": "New File",
                "purpose": "Test new file",
            },
            {
                "section": "docs",
                "slug": "existing-file",
                "output_path": "content/docs.aspose.org/test/en/python/existing-file.md",
                "url_path": "/test/python/existing-file/",
                "title": "Existing File",
                "purpose": "Test existing file",
            },
        ],
    }

    # Create drafts
    drafts_dir = temp_run_dir / "drafts"
    drafts_dir.mkdir(parents=True, exist_ok=True)

    new_content = "# New File\n\nThis is new."
    existing_content = "# Existing File\n\nThis already exists."

    (drafts_dir / "new-file.md").write_text(new_content)
    (drafts_dir / "existing-file.md").write_text(existing_content)

    # Pre-create the existing file in site worktree with same content
    # This will be skipped during patch generation (no patch created)
    site_worktree = temp_run_dir / "work" / "site"
    existing_path = site_worktree / "content/docs.aspose.org/test/en/python/existing-file.md"
    existing_path.parent.mkdir(parents=True, exist_ok=True)
    existing_path.write_text(existing_content)  # Same content = no patch generated

    draft_manifest = {
        "schema_version": "1.0",
        "run_id": "test-run-applied-only",
        "total_pages": 2,
        "draft_count": 2,
        "drafts": [
            {
                "page_id": "docs_new_file",
                "section": "docs",
                "slug": "new-file",
                "output_path": "content/docs.aspose.org/test/en/python/new-file.md",
                "draft_path": "drafts/new-file.md",
                "title": "New File",
                "word_count": 5,
                "claim_count": 0,
            },
            {
                "page_id": "docs_existing_file",
                "section": "docs",
                "slug": "existing-file",
                "output_path": "content/docs.aspose.org/test/en/python/existing-file.md",
                "draft_path": "drafts/existing-file.md",
                "title": "Existing File",
                "word_count": 5,
                "claim_count": 0,
            },
        ],
    }

    # Save artifacts
    (temp_run_dir / "artifacts" / "page_plan.json").write_text(json.dumps(page_plan))
    (temp_run_dir / "artifacts" / "draft_manifest.json").write_text(json.dumps(draft_manifest))

    # Execute W6
    result = execute_linker_and_patcher(temp_run_dir, run_config)

    # One patch applied (new file), existing file skipped during generation (no patch created)
    assert result["patches_applied"] == 1, f"Expected 1 applied, got {result['patches_applied']}"
    # patches_skipped counts patches with status='skipped', not files skipped during generation
    assert result["patches_skipped"] == 0, f"Expected 0 skipped (file was skipped during generation), got {result['patches_skipped']}"

    # Content export should have 1 file (only the applied patch)
    assert result["exported_files_count"] == 1, f"Expected 1 exported file, got {result['exported_files_count']}"

    # Verify the new file was exported
    content_preview_dir = temp_run_dir / result["content_preview_dir"]
    new_file_export = content_preview_dir / "content/docs.aspose.org/test/en/python/new-file.md"

    assert new_file_export.exists(), "New file should be exported"
    assert "This is new" in new_file_export.read_text(encoding="utf-8"), "Exported file should have correct content"


def test_content_export_deterministic_paths(temp_run_dir, multi_subdomain_draft_manifest, multi_subdomain_page_plan):
    """Test that content export paths are deterministic (relative to run_dir)."""
    run_config = {
        "run_id": "test-run-deterministic",
    }

    # Save artifacts
    (temp_run_dir / "artifacts" / "page_plan.json").write_text(
        json.dumps(multi_subdomain_page_plan)
    )
    (temp_run_dir / "artifacts" / "draft_manifest.json").write_text(
        json.dumps(multi_subdomain_draft_manifest)
    )

    # Execute W6
    result = execute_linker_and_patcher(temp_run_dir, run_config)

    # Check that content_preview_dir is a relative path
    content_preview_dir = result["content_preview_dir"]
    assert not Path(content_preview_dir).is_absolute(), "content_preview_dir should be relative path"
    # Normalize path separators for Windows/Linux compatibility
    normalized_path = content_preview_dir.replace("\\", "/")
    assert normalized_path == "content_preview/content", f"Expected 'content_preview/content', got '{normalized_path}'"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
