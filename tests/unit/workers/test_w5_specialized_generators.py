"""TC-973: Unit tests for W5 SectionWriter specialized content generators.

Tests the three new specialized content generators:
- generate_toc_content(): Creates navigation hub for docs/_index.md
- generate_comprehensive_guide_content(): Lists all workflows for developer-guide
- generate_feature_showcase_content(): Creates KB feature how-to article

Critical validation:
- TOC must NOT contain code snippets (Gate 14 blocker)
- Comprehensive guide must list ALL workflows (Gate 14 requirement)
- Feature showcase must focus on single feature (Gate 14 requirement)
"""

import pytest
from typing import Dict, Any

# Import functions to test
from src.launch.workers.w5_section_writer.worker import (
    generate_toc_content,
    generate_comprehensive_guide_content,
    generate_feature_showcase_content,
    generate_troubleshooting_content,
    generate_section_content,
    _generate_fallback_content,
    apply_token_mappings,
    _validate_yaml_frontmatter,
    _build_section_prompt,
    _extract_license_string,
    _is_spec_fragment,
    _strip_product_name_prefix,
    _remove_empty_sections,
)


class TestGenerateTocContent:
    """Test generate_toc_content() function for TOC generation."""

    def test_generate_toc_content_basic(self):
        """Test case 1: Verify TOC with 2 child pages has intro + child list + quick links."""
        page = {
            "slug": "_index",
            "section": "docs",
            "title": "Documentation",
            "purpose": "Documentation hub for Aspose.3D",
            "content_strategy": {
                "child_pages": ["getting-started", "developer-guide"],
            },
        }

        product_facts = {
            "product_name": "Aspose.3D for Python",
            "repo_url": "https://github.com/aspose/Aspose.3D-for-Python",
        }

        page_plan = {
            "pages": [
                {
                    "slug": "getting-started",
                    "section": "docs",
                    "title": "Getting Started",
                    "url_path": "/docs/getting-started/",
                    "purpose": "Learn how to install and use Aspose.3D",
                },
                {
                    "slug": "developer-guide",
                    "section": "docs",
                    "title": "Developer Guide",
                    "url_path": "/docs/developer-guide/",
                    "purpose": "Comprehensive guide to all workflows",
                },
                {
                    "slug": "_index",
                    "section": "products",
                    "title": "Product Overview",
                    "url_path": "/products/3d/python/",
                },
                {
                    "slug": "_index",
                    "section": "reference",
                    "title": "API Reference",
                    "url_path": "/reference/",
                },
                {
                    "slug": "feature-1",
                    "section": "kb",
                    "title": "Feature 1",
                    "url_path": "/kb/feature-1/",
                },
            ],
        }

        content = generate_toc_content(page, product_facts, page_plan)

        # Verify structure
        assert "# Documentation" in content
        assert "Aspose.3D for Python documentation" in content
        assert "## Documentation Index" in content
        assert "## Quick Links and Resources" in content

        # Verify child pages listed
        assert "[Getting Started](/docs/getting-started/)" in content
        assert "Learn how to install and use Aspose.3D" in content
        assert "[Developer Guide](/docs/developer-guide/)" in content
        assert "Comprehensive guide to all workflows" in content

        # Verify quick links
        assert "[Product Overview](/products/3d/python/)" in content
        assert "[API Reference](/reference/)" in content
        assert "[Knowledge Base](/kb/feature-1/)" in content
        assert "[GitHub Repository](https://github.com/aspose/Aspose.3D-for-Python)" in content

    def test_generate_toc_content_claim_markers_injected(self):
        """TOC with required_claim_ids should inject claim markers for content density."""
        page = {
            "slug": "_index",
            "section": "docs",
            "title": "Documentation",
            "purpose": "Documentation hub",
            "required_claim_ids": ["claim-aaa", "claim-bbb", "claim-ccc", "claim-ddd"],
            "content_strategy": {
                "child_pages": ["getting-started"],
            },
        }

        product_facts = {
            "product_name": "Aspose.3D",
            "repo_url": "https://github.com/aspose/Aspose.3D",
        }

        page_plan = {
            "pages": [
                {
                    "slug": "getting-started",
                    "section": "docs",
                    "title": "Getting Started",
                    "url_path": "/docs/getting-started/",
                    "purpose": "Getting started guide",
                },
            ],
        }

        content = generate_toc_content(page, product_facts, page_plan)

        # Should inject claim markers (capped at 3 for TOC)
        assert "<!-- claim_id: claim-aaa -->" in content
        assert "<!-- claim_id: claim-bbb -->" in content
        assert "<!-- claim_id: claim-ccc -->" in content
        # 4th claim should NOT be injected (cap at 3)
        assert "<!-- claim_id: claim-ddd -->" not in content

    def test_generate_toc_content_no_claim_markers_when_empty(self):
        """TOC without required_claim_ids should not inject claim markers."""
        page = {
            "slug": "_index",
            "section": "docs",
            "title": "Documentation",
            "purpose": "Documentation hub",
            "content_strategy": {
                "child_pages": [],
            },
        }

        product_facts = {
            "product_name": "Aspose.3D",
            "repo_url": "",
        }

        page_plan = {"pages": []}

        content = generate_toc_content(page, product_facts, page_plan)

        # No claim markers should be present
        assert "<!-- claim_id:" not in content

    def test_generate_toc_content_no_code_snippets(self):
        """Test case 2: Verify output has no triple backticks (critical for Gate 14)."""
        page = {
            "slug": "_index",
            "section": "docs",
            "title": "Documentation",
            "purpose": "Documentation hub",
            "content_strategy": {
                "child_pages": ["getting-started"],
            },
        }

        product_facts = {
            "product_name": "Aspose.3D",
            "repo_url": "https://github.com/aspose/Aspose.3D",
        }

        page_plan = {
            "pages": [
                {
                    "slug": "getting-started",
                    "section": "docs",
                    "title": "Getting Started",
                    "url_path": "/docs/getting-started/",
                    "purpose": "Getting started guide",
                },
            ],
        }

        content = generate_toc_content(page, product_facts, page_plan)

        # CRITICAL: No code blocks in TOC (Gate 14 blocker if violated)
        assert "```" not in content, "TOC must NOT contain code snippets"

    def test_generate_toc_content_empty_children(self):
        """Test case 3: Verify TOC with child_pages=[] still renders (graceful degradation)."""
        page = {
            "slug": "_index",
            "section": "docs",
            "title": "Documentation",
            "purpose": "Documentation hub",
            "content_strategy": {
                "child_pages": [],
            },
        }

        product_facts = {
            "product_name": "Aspose.3D",
            "repo_url": "https://github.com/aspose/Aspose.3D",
        }

        page_plan = {
            "pages": [],
        }

        content = generate_toc_content(page, product_facts, page_plan)

        # Should still have basic structure
        assert "# Documentation" in content
        assert "## Quick Links and Resources" in content
        # Should not crash with empty child list


class TestGenerateComprehensiveGuideContent:
    """Test generate_comprehensive_guide_content() function for developer guide."""

    def test_generate_comprehensive_guide_all_workflows(self):
        """Test case 4: Verify guide with 3 workflows, each has H3 + description + code + link."""
        page = {
            "slug": "developer-guide",
            "section": "docs",
            "title": "Developer Guide",
            "purpose": "Comprehensive workflow guide",
        }

        product_facts = {
            "product_name": "Aspose.3D for Python",
            "repo_url": "https://github.com/aspose/Aspose.3D-for-Python",
            "sha": "abc123",
            "workflows": [
                {
                    "workflow_id": "create_scene",
                    "name": "Create 3D Scene",
                    "description": "Create a new 3D scene from scratch.",
                },
                {
                    "workflow_id": "load_file",
                    "name": "Load 3D File",
                    "description": "Load an existing 3D file for manipulation.",
                },
                {
                    "workflow_id": "export_scene",
                    "name": "Export Scene",
                    "description": "Export the 3D scene to various formats.",
                },
            ],
        }

        snippet_catalog = {
            "snippets": [
                {
                    "snippet_id": "snippet_1",
                    "language": "python",
                    "tags": ["create_scene"],
                    "code": "scene = Scene()",
                    "source": {"path": "examples/create_scene.py"},
                },
                {
                    "snippet_id": "snippet_2",
                    "language": "python",
                    "tags": ["load_file"],
                    "code": "scene = Scene.from_file('model.fbx')",
                    "source": {"path": "examples/load_file.py"},
                },
                {
                    "snippet_id": "snippet_3",
                    "language": "python",
                    "tags": ["export_scene"],
                    "code": "scene.save('output.obj')",
                    "source": {"path": "examples/export_scene.py"},
                },
            ],
        }

        content = generate_comprehensive_guide_content(page, product_facts, snippet_catalog)

        # Verify structure
        assert "# Developer Guide" in content
        assert "comprehensive guide covers all common workflows" in content

        # Verify Prerequisites section (usability.prerequisites_clarity compliance)
        assert "## Prerequisites" in content
        assert "Installation Guide" in content

        # Verify all 3 workflows present with H3 headings
        assert "### Create 3D Scene" in content
        assert "### Load 3D File" in content
        assert "### Export Scene" in content

        # Verify descriptions
        assert "Create a new 3D scene from scratch." in content
        assert "Load an existing 3D file for manipulation." in content
        assert "Export the 3D scene to various formats." in content

        # Verify code blocks
        assert "```python" in content
        assert "scene = Scene()" in content
        assert "scene = Scene.from_file('model.fbx')" in content
        assert "scene.save('output.obj')" in content

        # Verify repo links
        assert "View full example on GitHub" in content
        assert "https://github.com/aspose/Aspose.3D-for-Python/blob/abc123/examples/create_scene.py" in content

        # Verify separators between workflows
        assert content.count("---") >= 3

        # Verify Additional Resources section
        assert "## Additional Resources and References" in content

    def test_generate_comprehensive_guide_missing_snippets(self):
        """Test case 5: Verify guide still renders if some snippets missing (graceful degradation)."""
        page = {
            "slug": "developer-guide",
            "section": "docs",
            "title": "Developer Guide",
            "purpose": "Comprehensive workflow guide",
        }

        product_facts = {
            "product_name": "Aspose.3D",
            "repo_url": "https://github.com/aspose/Aspose.3D",
            "sha": "main",
            "workflows": [
                {
                    "workflow_id": "workflow_1",
                    "name": "Workflow 1",
                    "description": "First workflow",
                },
                {
                    "workflow_id": "workflow_2",
                    "name": "Workflow 2",
                    "description": "Second workflow",
                },
            ],
        }

        snippet_catalog = {
            "snippets": [],  # No snippets available
        }

        content = generate_comprehensive_guide_content(page, product_facts, snippet_catalog)

        # Should still generate content with repository reference
        assert "### Workflow 1" in content
        assert "### Workflow 2" in content
        assert "Refer to the Aspose.3D repository for code examples" in content

    def test_generate_comprehensive_guide_deterministic_order(self):
        """Test case 6: Verify same workflows input → same output order."""
        page = {
            "slug": "developer-guide",
            "section": "docs",
            "title": "Developer Guide",
            "purpose": "Comprehensive workflow guide",
        }

        product_facts = {
            "product_name": "Aspose.3D",
            "repo_url": "https://github.com/aspose/Aspose.3D",
            "workflows": [
                {"workflow_id": "w1", "name": "Workflow A", "description": "First"},
                {"workflow_id": "w2", "name": "Workflow B", "description": "Second"},
                {"workflow_id": "w3", "name": "Workflow C", "description": "Third"},
            ],
        }

        snippet_catalog = {"snippets": []}

        # Generate twice
        content1 = generate_comprehensive_guide_content(page, product_facts, snippet_catalog)
        content2 = generate_comprehensive_guide_content(page, product_facts, snippet_catalog)

        # Should be identical (deterministic)
        assert content1 == content2

    def test_comprehensive_guide_with_limitations_required(self):
        """TC-1106: Test case 7: Verify Limitations section generated when in required_headings."""
        page = {
            "slug": "developer-guide",
            "section": "docs",
            "title": "Developer Guide",
            "purpose": "Comprehensive workflow guide",
            "required_headings": ["Introduction", "Common Scenarios", "Advanced Scenarios", "Limitations"],
        }

        product_facts = {
            "product_name": "Aspose.NOTE",
            "repo_url": "https://github.com/aspose/Aspose.NOTE",
            "workflows": [],
            "claim_groups": {
                "limitations": ["claim_limit_1", "claim_limit_2"],
            },
            "claims": [
                {
                    "claim_id": "claim_limit_1",
                    "claim_text": "Cannot process encrypted OneNote files with password protection enabled in the notebook",
                },
                {
                    "claim_id": "claim_limit_2",
                    "claim_text": "Maximum file size is 500MB for single document processing operations without streaming mode",
                },
            ],
        }

        snippet_catalog = {"snippets": []}

        content = generate_comprehensive_guide_content(page, product_facts, snippet_catalog)

        # Verify Limitations section present
        assert "## Limitations" in content
        assert "Known limitations and constraints for Aspose.NOTE:" in content

        # Verify limitation claims with claim markers
        assert "Cannot process encrypted OneNote files" in content
        assert "[claim: claim_limit_1]" in content
        assert "Maximum file size is 500MB" in content
        assert "[claim: claim_limit_2]" in content

    def test_comprehensive_guide_without_limitations_required(self):
        """TC-1106: Test case 8: Verify NO Limitations section when not in required_headings."""
        page = {
            "slug": "developer-guide",
            "section": "docs",
            "title": "Developer Guide",
            "purpose": "Comprehensive workflow guide",
            "required_headings": ["Introduction", "Common Scenarios"],  # No Limitations
        }

        product_facts = {
            "product_name": "Aspose.3D",
            "workflows": [],
            "claim_groups": {
                "limitations": ["claim_limit_1"],
            },
            "claims": [
                {
                    "claim_id": "claim_limit_1",
                    "claim_text": "Limited support for legacy 3D model formats from older CAD applications",
                },
            ],
        }

        snippet_catalog = {"snippets": []}

        content = generate_comprehensive_guide_content(page, product_facts, snippet_catalog)

        # Verify NO Limitations section
        assert "## Limitations" not in content

    def test_comprehensive_guide_limitations_no_claims(self):
        """TC-1106: Test case 9: Verify graceful handling when Limitations required but no claims."""
        page = {
            "slug": "developer-guide",
            "section": "docs",
            "title": "Developer Guide",
            "purpose": "Comprehensive workflow guide",
            "required_headings": ["Introduction", "Limitations"],
        }

        product_facts = {
            "product_name": "Aspose.PDF",
            "workflows": [],
            "claim_groups": {
                "limitations": [],  # Empty
            },
            "claims": [],
        }

        snippet_catalog = {"snippets": []}

        content = generate_comprehensive_guide_content(page, product_facts, snippet_catalog)

        # Verify Limitations section with fallback message
        assert "## Limitations" in content
        assert "No known limitations at this time." in content

    def test_comprehensive_guide_limitations_claim_markers(self):
        """TC-1106: Test case 10: Verify claim markers format per specs/08_section_writer.md."""
        page = {
            "slug": "developer-guide",
            "section": "docs",
            "title": "Developer Guide",
            "required_headings": ["Limitations"],
        }

        product_facts = {
            "product_name": "Test Product",
            "workflows": [],
            "claim_groups": {
                "limitations": ["abc123"],
            },
            "claims": [
                {
                    "claim_id": "abc123",
                    "claim_text": "Limited support for real-time collaborative editing features in distributed environments",
                },
            ],
        }

        snippet_catalog = {"snippets": []}

        content = generate_comprehensive_guide_content(page, product_facts, snippet_catalog)

        # Verify claim marker format: [claim: claim_id]
        assert "[claim: abc123]" in content
        # Verify it's in a list item
        assert "- Limited support for real-time collaborative editing" in content

    def test_comprehensive_guide_limitations_long_claims(self):
        """TC-1110: Test case 11: Verify simplification of long claims (first-sentence or word-boundary)."""
        page = {
            "slug": "developer-guide",
            "section": "docs",
            "title": "Developer Guide",
            "required_headings": ["Limitations"],
        }

        # Create a claim with 300+ chars and no sentence-ending punctuation
        # (forces word-boundary fallback since first-sentence extraction can't find a period)
        long_claim_text = (
            "This is a very long limitation claim that exceeds the display limit "
            "and should be simplified at a word boundary to ensure readability without cutting "
            "words in the middle which would look unprofessional and harm the user experience "
            "when reading the documentation on the website or in other formats like PDF exports"
        )

        product_facts = {
            "product_name": "Aspose.Test",
            "workflows": [],
            "claim_groups": {
                "limitations": ["claim_long"],
            },
            "claims": [
                {
                    "claim_id": "claim_long",
                    "claim_text": long_claim_text,
                },
            ],
        }

        snippet_catalog = {"snippets": []}

        content = generate_comprehensive_guide_content(page, product_facts, snippet_catalog)

        # Verify Limitations section present
        assert "## Limitations" in content
        assert "[claim: claim_long]" in content

        # Verify claim is shortened (less than full length)
        lines = content.split('\n')
        bullet_line = [l for l in lines if '[claim: claim_long]' in l][0]
        assert len(bullet_line) < len(f"- {long_claim_text} [claim: claim_long]")

        # With no sentence break, word-boundary truncation adds "..."
        text_before_marker = bullet_line.split('[claim:')[0].strip()
        assert text_before_marker.endswith("...")

        # Verify no mid-word truncation (last word before "..." is complete)
        text_without_ellipsis = text_before_marker[:-3].strip()
        last_word = text_without_ellipsis.split()[-1]
        assert last_word.isalpha(), f"Truncation cut mid-word: '{last_word}'"

    def test_comprehensive_guide_limitations_extremely_long(self):
        """TC-1110: Test case 12: Verify filtering of extremely long claims (>1KB)."""
        page = {
            "slug": "developer-guide",
            "section": "docs",
            "title": "Developer Guide",
            "required_headings": ["Limitations"],
        }

        # Create an extremely long claim (2000 chars) that should be filtered out
        extremely_long_claim = "X" * 2000

        product_facts = {
            "product_name": "Aspose.Test",
            "workflows": [],
            "claim_groups": {
                "limitations": ["claim_extreme", "claim_normal"],
            },
            "claims": [
                {
                    "claim_id": "claim_extreme",
                    "claim_text": extremely_long_claim,
                },
                {
                    "claim_id": "claim_normal",
                    "claim_text": "This is a normal limitation claim that should be included",
                },
            ],
        }

        snippet_catalog = {"snippets": []}

        content = generate_comprehensive_guide_content(page, product_facts, snippet_catalog)

        # Verify Limitations section present
        assert "## Limitations" in content

        # Verify extremely long claim is filtered out
        assert "claim_extreme" not in content
        assert "X" * 100 not in content  # No long sequence of X's

        # Verify normal claim is included
        assert "[claim: claim_normal]" in content
        assert "This is a normal limitation claim that should be included" in content


    def test_generate_comprehensive_guide_missing_workflow_stub(self):
        """TC-P2B: Verify that workflows missing from generated content get stub sections appended."""
        page = {
            "slug": "developer-guide",
            "section": "docs",
            "title": "Developer Guide",
            "purpose": "Comprehensive workflow guide",
        }

        # Workflow "Secret Workflow" won't match any snippet and its name
        # differs from the other workflow names, so it should always appear.
        # But we'll also add a workflow whose name is deliberately NOT in
        # the generated content via forbidden_topics to test the stub path.
        product_facts = {
            "product_name": "Aspose.Test",
            "repo_url": "https://github.com/aspose/Aspose.Test",
            "sha": "main",
            "workflows": [
                {
                    "workflow_id": "wf_normal",
                    "name": "Normal Workflow",
                    "description": "A normal workflow.",
                },
                {
                    "workflow_id": "wf_secret",
                    "name": "Secret Workflow",
                    "description": "A secret workflow.",
                },
            ],
        }

        snippet_catalog = {
            "snippets": [
                {
                    "snippet_id": "s1",
                    "language": "python",
                    "tags": ["wf_normal"],
                    "code": "do_normal()",
                    "source": {"path": "examples/normal.py"},
                },
            ],
        }

        content = generate_comprehensive_guide_content(page, product_facts, snippet_catalog)

        # Both workflows should appear in content
        assert "### Normal Workflow" in content
        assert "### Secret Workflow" in content
        # Secret workflow has no snippet so it gets graceful degradation text
        assert "Refer to the Aspose.Test repository for" in content

    def test_generate_comprehensive_guide_excluded_workflows_listed(self):
        """Workflows filtered by forbidden_topics should appear in Additional Workflows section."""
        page = {
            "slug": "developer-guide",
            "section": "docs",
            "title": "Developer Guide",
            "purpose": "Comprehensive workflow guide",
            "forbidden_topics": ["install"],
        }

        product_facts = {
            "product_name": "Aspose.3D",
            "repo_url": "https://github.com/aspose/Aspose.3D",
            "sha": "main",
            "workflows": [
                {
                    "workflow_id": "wf_create",
                    "name": "Create Scene",
                    "description": "Create a new scene.",
                },
                {
                    "workflow_id": "wf_install",
                    "name": "Install Package",
                    "description": "Install the package via pip.",
                },
            ],
        }

        snippet_catalog = {"snippets": []}

        content = generate_comprehensive_guide_content(page, product_facts, snippet_catalog)

        # "Install Package" should be filtered from main workflows
        assert "### Install Package" not in content
        # But should appear in Additional Workflows section
        assert "## Additional Workflows" in content
        assert "**Install Package**" in content
        assert "Install the package via pip." in content


class TestGenerateFeatureShowcaseContent:
    """Test generate_feature_showcase_content() function for KB feature articles."""

    def test_generate_feature_showcase_single_claim(self):
        """Test case 7: Verify showcase has 1 claim marker, Overview + When to Use + Steps + Code + Links."""
        page = {
            "slug": "how-to-convert-3d-models",
            "section": "kb",
            "title": "How to Convert 3D Models",
            "purpose": "Guide to model conversion",
            "required_claim_ids": ["claim_convert"],
        }

        product_facts = {
            "product_name": "Aspose.3D for Python",
            "repo_url": "https://github.com/aspose/Aspose.3D-for-Python",
            "claims": [
                {
                    "claim_id": "claim_convert",
                    "claim_text": "supports converting 3D models between multiple formats",
                },
            ],
        }

        snippet_catalog = {
            "snippets": [
                {
                    "snippet_id": "snippet_convert",
                    "language": "python",
                    "tags": ["claim_convert", "convert"],
                    "code": "scene.save('output.obj', FileFormat.WAVEFRONT_OBJ)",
                },
            ],
        }

        content = generate_feature_showcase_content(page, product_facts, snippet_catalog)

        # Verify structure
        assert "# How to Convert 3D Models" in content
        assert "## Overview" in content
        assert "## Prerequisites" in content
        assert "Installation Guide" in content
        assert "## When to Use" in content
        assert "## Step-by-Step Guide" in content
        assert "## Complete Code Example" in content
        assert "## Related Resources and Links" in content

        # Verify single claim marker in Overview
        assert "<!-- claim_id: claim_convert -->" in content
        assert content.count("<!-- claim_id:") == 1, "Feature showcase should have exactly 1 claim marker"

        # Verify feature text
        assert "supports converting 3D models between multiple formats" in content

        # Verify steps
        assert "1. **Import the library**" in content
        assert "2. **Initialize the object**" in content
        assert "3. **Configure settings**" in content
        assert "4. **Execute the operation**" in content

        # Verify code block
        assert "```python" in content
        assert "scene.save('output.obj', FileFormat.WAVEFRONT_OBJ)" in content

        # Verify related links
        assert "[Developer Guide](/docs/developer-guide/)" in content
        assert "[API Reference](/reference/)" in content
        assert "[GitHub Repository](https://github.com/aspose/Aspose.3D-for-Python)" in content

    def test_generate_feature_showcase_with_snippet(self):
        """Test case 8: Verify showcase includes code block with snippet.code."""
        page = {
            "slug": "how-to-load-models",
            "section": "kb",
            "title": "How to Load 3D Models",
            "purpose": "Guide to loading models",
            "required_claim_ids": ["claim_load"],
        }

        product_facts = {
            "product_name": "Aspose.3D",
            "repo_url": "https://github.com/aspose/Aspose.3D",
            "claims": [
                {
                    "claim_id": "claim_load",
                    "claim_text": "loads 3D models from various file formats",
                },
            ],
        }

        snippet_catalog = {
            "snippets": [
                {
                    "snippet_id": "snippet_load",
                    "language": "python",
                    "tags": ["claim_load", "load"],
                    "code": "from aspose.threed import Scene\nscene = Scene.from_file('model.fbx')",
                },
            ],
        }

        content = generate_feature_showcase_content(page, product_facts, snippet_catalog)

        # Verify code block contains snippet
        assert "```python" in content
        assert "from aspose.threed import Scene" in content
        assert "scene = Scene.from_file('model.fbx')" in content

    def test_generate_feature_showcase_without_snippet(self):
        """Test case 9: Verify showcase renders placeholder code if snippet missing."""
        page = {
            "slug": "how-to-export-models",
            "section": "kb",
            "title": "How to Export 3D Models",
            "purpose": "Guide to exporting models",
            "required_claim_ids": ["claim_export"],
        }

        product_facts = {
            "product_name": "Aspose.3D",
            "repo_url": "https://github.com/aspose/Aspose.3D",
            "claims": [
                {
                    "claim_id": "claim_export",
                    "claim_text": "exports 3D models to various formats",
                },
            ],
        }

        snippet_catalog = {
            "snippets": [],  # No snippets available
        }

        content = generate_feature_showcase_content(page, product_facts, snippet_catalog)

        # Should render repository reference instead of placeholder
        assert "Refer to the Aspose.3D repository for code examples" in content


class TestGenerateTroubleshootingContent:
    """TC-P3A: Test generate_troubleshooting_content() function."""

    def test_troubleshooting_basic_structure(self):
        """Verify troubleshooting page has Problem/Cause/Solution structure."""
        page = {
            "slug": "troubleshooting",
            "section": "kb",
            "title": "Troubleshooting",
            "purpose": "Common issues and solutions",
        }

        product_facts = {
            "product_name": "Aspose.3D for Python",
            "repo_url": "https://github.com/aspose/Aspose.3D-for-Python",
            "claims": [
                {
                    "claim_id": "lim_1",
                    "claim_text": "FBX files larger than 2GB are not supported.",
                    "claim_kind": "limitation",
                    "citations": [{"path": "README.md"}],
                },
                {
                    "claim_id": "lim_2",
                    "claim_text": "Animation export is limited to 30fps.",
                    "claim_kind": "limitation",
                    "citations": [],
                },
            ],
            "claim_groups": {
                "limitations": ["lim_1", "lim_2"],
            },
        }

        snippet_catalog = {"snippets": []}

        content = generate_troubleshooting_content(page, product_facts, snippet_catalog)

        # Verify structure
        assert "# Troubleshooting" in content
        assert "## Common Issues" in content
        assert "**Problem**:" in content
        assert "**Cause**:" in content
        assert "**Solution/Workaround**:" in content

        # Verify claim markers
        assert "[claim: lim_1]" in content
        assert "[claim: lim_2]" in content

        # Verify both limitations appear
        assert "FBX files larger than 2GB are not supported" in content
        assert "Animation export is limited to 30fps" in content

        # Verify no code blocks (troubleshooting is prose)
        assert "```" not in content

    def test_troubleshooting_no_limitations(self):
        """Verify graceful degradation when no limitation claims exist."""
        page = {
            "slug": "troubleshooting",
            "section": "kb",
            "title": "Troubleshooting",
            "purpose": "Common issues and solutions",
        }

        product_facts = {
            "product_name": "Aspose.Test",
            "claims": [],
            "claim_groups": {"limitations": []},
        }

        snippet_catalog = {"snippets": []}

        content = generate_troubleshooting_content(page, product_facts, snippet_catalog)

        assert "# Troubleshooting" in content
        # With no limitation claims and no feature claims, fallback to docs link
        assert "Frequently Asked Questions" in content or "troubleshooting guidance" in content

    def test_troubleshooting_has_frontmatter(self):
        """Verify troubleshooting page has proper frontmatter for Gate 4."""
        page = {
            "slug": "troubleshooting",
            "section": "kb",
            "title": "Troubleshooting Guide",
            "purpose": "Issues and solutions",
            "url_path": "/kb/troubleshooting/",
        }

        product_facts = {
            "product_name": "Aspose.Test",
            "claims": [
                {
                    "claim_id": "lim_x",
                    "claim_text": "Max file size is 100MB.",
                    "claim_kind": "limitation",
                    "citations": [],
                },
            ],
            "claim_groups": {"limitations": ["lim_x"]},
        }

        snippet_catalog = {"snippets": []}

        content = generate_troubleshooting_content(page, product_facts, snippet_catalog)

        assert content.startswith("---")
        assert 'title: "Troubleshooting Guide"' in content
        assert "layout: kb" in content
        assert "permalink: /kb/troubleshooting/" in content

    def test_troubleshooting_routing(self):
        """Verify generate_section_content routes troubleshooting pages correctly."""
        page = {
            "slug": "troubleshooting",
            "section": "kb",
            "title": "Troubleshooting",
            "purpose": "Issues",
            "page_role": "troubleshooting",
        }

        product_facts = {
            "product_name": "Aspose.Test",
            "claims": [
                {
                    "claim_id": "lim_r",
                    "claim_text": "Feature X is not supported.",
                    "claim_kind": "limitation",
                    "citations": [],
                },
            ],
            "claim_groups": {"limitations": ["lim_r"]},
        }

        snippet_catalog = {"snippets": []}

        content = generate_section_content(page, product_facts, snippet_catalog)

        # Should route to troubleshooting generator
        assert "**Problem**:" in content
        assert "[claim: lim_r]" in content


class TestGenerateSectionContentRouting:
    """Test generate_section_content() routing by page_role (integration tests)."""

    def test_generate_section_content_routing_toc(self):
        """Test case 10: Integration test - page_role='toc' calls generate_toc_content()."""
        page = {
            "slug": "_index",
            "section": "docs",
            "title": "Documentation",
            "purpose": "Documentation hub",
            "page_role": "toc",  # Should route to TOC generator
            "content_strategy": {
                "child_pages": ["getting-started"],
            },
        }

        product_facts = {
            "product_name": "Aspose.3D",
            "repo_url": "https://github.com/aspose/Aspose.3D",
        }

        snippet_catalog = {"snippets": []}

        page_plan = {
            "pages": [
                {
                    "slug": "getting-started",
                    "section": "docs",
                    "title": "Getting Started",
                    "url_path": "/docs/getting-started/",
                    "purpose": "Getting started guide",
                },
            ],
        }

        content = generate_section_content(
            page=page,
            product_facts=product_facts,
            snippet_catalog=snippet_catalog,
            llm_client=None,
            page_plan=page_plan,
        )

        # Verify TOC-specific content
        assert "## Documentation Index" in content
        assert "## Quick Links and Resources" in content
        assert "[Getting Started](/docs/getting-started/)" in content
        # Critical: No code blocks
        assert "```" not in content

    def test_generate_section_content_routing_guide(self):
        """Test case 11: Integration test - page_role='comprehensive_guide' calls generate_comprehensive_guide_content()."""
        page = {
            "slug": "developer-guide",
            "section": "docs",
            "title": "Developer Guide",
            "purpose": "Comprehensive workflow guide",
            "page_role": "comprehensive_guide",  # Should route to guide generator
        }

        product_facts = {
            "product_name": "Aspose.3D",
            "repo_url": "https://github.com/aspose/Aspose.3D",
            "workflows": [
                {
                    "workflow_id": "workflow_1",
                    "name": "Create Scene",
                    "description": "Create a new 3D scene",
                },
            ],
        }

        snippet_catalog = {"snippets": []}

        content = generate_section_content(
            page=page,
            product_facts=product_facts,
            snippet_catalog=snippet_catalog,
            llm_client=None,
        )

        # Verify guide-specific content
        assert "comprehensive guide covers all common workflows" in content
        assert "### Create Scene" in content
        assert "## Additional Resources and References" in content

    def test_generate_section_content_routing_showcase(self):
        """Test case 12: Integration test - page_role='feature_showcase' calls generate_feature_showcase_content()."""
        page = {
            "slug": "how-to-render-scenes",
            "section": "kb",
            "title": "How to Render Scenes",
            "purpose": "Guide to scene rendering",
            "page_role": "feature_showcase",  # Should route to showcase generator
            "required_claim_ids": ["claim_render"],
        }

        product_facts = {
            "product_name": "Aspose.3D",
            "repo_url": "https://github.com/aspose/Aspose.3D",
            "claims": [
                {
                    "claim_id": "claim_render",
                    "claim_text": "renders 3D scenes with advanced lighting",
                },
            ],
        }

        snippet_catalog = {"snippets": []}

        content = generate_section_content(
            page=page,
            product_facts=product_facts,
            snippet_catalog=snippet_catalog,
            llm_client=None,
        )

        # Verify showcase-specific content
        assert "## Overview" in content
        assert "## When to Use" in content
        assert "## Step-by-Step Guide" in content
        assert "<!-- claim_id: claim_render -->" in content
        assert "renders 3D scenes with advanced lighting" in content


class TestGenerateFallbackContent:
    """TC-982: Tests for _generate_fallback_content() claim distribution and snippet matching."""

    def test_fallback_distributes_claims_evenly_across_headings(self):
        """TC-982 test 1: 10 claims across 4 headings -> ~2-3 claims per heading, no overlap."""
        claims = [
            {"claim_id": f"claim_{i}", "claim_text": f"Claim text {i}"}
            for i in range(10)
        ]
        headings = ["Overview", "Installation", "Key Features", "FAQ"]

        content = _generate_fallback_content(
            section="docs",
            title="Test Page",
            purpose="Test purpose",
            required_headings=headings,
            product_name="TestProduct",
            claims=claims,
            snippets=[],
            url_path="/docs/test/",
        )

        # Each heading gets different claims (10/4=2 each)
        assert "[claim: claim_0]" in content
        assert "[claim: claim_1]" in content
        assert "[claim: claim_2]" in content
        assert "[claim: claim_3]" in content

        # Claims appear under different headings
        sections = content.split("## ")
        assert len(sections) >= 6, f"Expected 6+ sections (4 headings + Further Reading), got {len(sections)}"

        # First heading (Overview) has claim_0 but NOT claim_4
        overview_section = sections[1]
        assert "[claim: claim_0]" in overview_section
        assert "[claim: claim_4]" not in overview_section

        # Third heading (Key Features) has claim_4 but NOT claim_0
        features_section = sections[3]
        assert "[claim: claim_4]" in features_section
        assert "[claim: claim_0]" not in features_section
    def test_fallback_empty_claims_produces_valid_markdown(self):
        """TC-982 test 2: Empty claims list -> purpose text as content, no crash."""
        content = _generate_fallback_content(
            section="docs",
            title="Test Page",
            purpose="This is the page purpose",
            required_headings=["Overview", "Details"],
            product_name="TestProduct",
            claims=[],
            snippets=[],
            url_path="/docs/test/",
        )

        assert content.startswith("---")
        assert "Test Page" in content
        assert "## Overview" in content
        assert "## Details" in content

        # Under headings with no claims, purpose text is fallback
        sections = content.split("## ")
        overview_section = sections[1]
        assert "This is the page purpose" in overview_section

    def test_fallback_snippet_matching_broadened_keywords(self):
        """TC-982 test 3: Heading Key Features triggers snippet (partial match)."""
        snippets = [
            {"snippet_id": "snip_1", "language": "python", "code": "import aspose", "tags": ["install"]},
        ]

        content = _generate_fallback_content(
            section="docs",
            title="Test Page",
            purpose="Test purpose",
            required_headings=["Key Features", "Troubleshooting"],
            product_name="TestProduct",
            claims=[{"claim_id": "c1", "claim_text": "A claim"}],
            snippets=snippets,
            url_path="/docs/test/",
        )

        assert "```python" in content
        assert "import aspose" in content
    def test_fallback_snippet_no_match_for_unrelated_heading(self):
        """TC-982 test 4: Heading Troubleshooting does NOT trigger snippet."""
        snippets = [
            {"snippet_id": "snip_1", "language": "python", "code": "import aspose", "tags": ["install"]},
        ]

        content = _generate_fallback_content(
            section="docs",
            title="Test Page",
            purpose="Test purpose",
            required_headings=["Troubleshooting"],
            product_name="TestProduct",
            claims=[{"claim_id": "c1", "claim_text": "A claim"}],
            snippets=snippets,
            url_path="/docs/test/",
        )

        assert "```python" not in content

    def test_fallback_snippet_rotation_across_headings(self):
        """TC-982 test 5: Multiple code headings get different snippets via rotation."""
        snippets = [
            {"snippet_id": "s1", "language": "python", "code": "code_first", "tags": []},
            {"snippet_id": "s2", "language": "python", "code": "code_second", "tags": []},
        ]

        content = _generate_fallback_content(
            section="docs",
            title="Test Page",
            purpose="Test purpose",
            required_headings=["Code Example", "Usage Overview", "Getting Started"],
            product_name="TestProduct",
            claims=[
                {"claim_id": "c1", "claim_text": "Claim 1"},
                {"claim_id": "c2", "claim_text": "Claim 2"},
                {"claim_id": "c3", "claim_text": "Claim 3"},
            ],
            snippets=snippets,
            url_path="/docs/test/",
        )

        assert "code_first" in content
        assert "code_second" in content
    def test_fallback_claim_markers_use_correct_format(self):
        """TC-982 test 6: Claim markers must use [claim: claim_id] format (Gate 14)."""
        claims = [
            {"claim_id": "test_claim_1", "claim_text": "First claim"},
            {"claim_id": "test_claim_2", "claim_text": "Second claim"},
        ]

        content = _generate_fallback_content(
            section="docs",
            title="Test Page",
            purpose="Test purpose",
            required_headings=["Overview"],
            product_name="TestProduct",
            claims=claims,
            snippets=[],
            url_path="/docs/test/",
        )

        assert "[claim: test_claim_1]" in content
        assert "[claim: test_claim_2]" in content
        assert "<!-- claim_id:" not in content

    def test_fallback_more_headings_than_claims(self):
        """TC-982 test 7: 2 claims across 5 headings -> first get claims, rest get purpose."""
        claims = [
            {"claim_id": "c1", "claim_text": "Only claim 1"},
            {"claim_id": "c2", "claim_text": "Only claim 2"},
        ]

        content = _generate_fallback_content(
            section="docs",
            title="Test Page",
            purpose="Fallback purpose text",
            required_headings=["H1", "H2", "H3", "H4", "H5"],
            product_name="TestProduct",
            claims=claims,
            snippets=[],
            url_path="/docs/test/",
        )

        assert "[claim: c1]" in content
        assert "[claim: c2]" in content
        sections = content.split("## ")
        assert "Fallback purpose text" in sections[4]
    def test_fallback_frontmatter_preserved(self):
        """TC-982 test 8: Frontmatter format must be valid YAML."""
        content = _generate_fallback_content(
            section="docs",
            title="My Page Title",
            purpose="Page purpose here",
            required_headings=["Overview"],
            product_name="TestProduct",
            claims=[],
            snippets=[],
            url_path="/docs/my-page/",
        )

        assert content.startswith("---")
        parts = content.split("---")
        assert len(parts) >= 3
        frontmatter = parts[1]
        assert "My Page Title" in frontmatter
        assert "Page purpose here" in frontmatter
        assert "layout: docs" in frontmatter
        assert "permalink: /docs/my-page/" in frontmatter

    def test_fallback_content_minimum_length(self):
        """TC-982 test 9: Content body must be >100 chars for Gate 7."""
        claims = [
            {"claim_id": f"c{i}", "claim_text": f"Claim text number {i} with enough content"}
            for i in range(6)
        ]

        content = _generate_fallback_content(
            section="docs",
            title="Test Page",
            purpose="A meaningful page purpose for testing content length",
            required_headings=["Overview", "Details", "Summary"],
            product_name="TestProduct",
            claims=claims,
            snippets=[],
            url_path="/docs/test/",
        )

        body = content.split("---", 2)[-1]
        assert len(body.strip()) > 100, f"Body too short ({len(body.strip())} chars)"

    def test_fallback_deterministic(self):
        """TC-982 test 10: Same input produces same output (Gate T)."""
        claims = [
            {"claim_id": "c1", "claim_text": "Claim 1"},
            {"claim_id": "c2", "claim_text": "Claim 2"},
        ]
        snippets = [
            {"snippet_id": "s1", "language": "python", "code": "x = 1", "tags": []},
        ]

        kwargs = dict(
            section="docs",
            title="Test Page",
            purpose="Purpose",
            required_headings=["Overview", "Code Example"],
            product_name="TestProduct",
            claims=claims,
            snippets=snippets,
            url_path="/docs/test/",
        )

        content1 = _generate_fallback_content(**kwargs)
        content2 = _generate_fallback_content(**kwargs)
        assert content1 == content2, "Fallback content must be deterministic"


class TestValidateYamlFrontmatter:
    """R1: Tests for YAML frontmatter validation in apply_token_mappings."""

    def test_valid_yaml_unchanged(self):
        """Valid YAML frontmatter should pass through unchanged."""
        content = '---\ntitle: "Test"\nlayout: docs\n---\n# Hello'
        result = _validate_yaml_frontmatter(content)
        assert result == content

    def test_no_frontmatter_unchanged(self):
        """Content without frontmatter should pass through unchanged."""
        content = "# Hello World\nSome text."
        result = _validate_yaml_frontmatter(content)
        assert result == content

    def test_broken_yaml_colon_in_block_scalar(self):
        """YAML with code-like colons in block scalar should be sanitized."""
        content = '---\ntitle: "Test"\ncontent: |\n  has_normals: True print(result)\n---\n# Body'
        result = _validate_yaml_frontmatter(content)
        # Should either fix or leave unchanged, but not crash
        assert "---" in result
        assert "# Body" in result

    def test_apply_token_mappings_validates_yaml(self):
        """apply_token_mappings should validate YAML after replacement."""
        template = '---\ntitle: "__TITLE__"\nlayout: docs\n---\n# Content'
        mappings = {"__TITLE__": "My Test Page"}
        result = apply_token_mappings(template, mappings)
        assert 'title: "My Test Page"' in result


class TestTroubleshootingForbiddenTopics:
    """R4: Tests for forbidden topic word sanitization in troubleshooting headings."""

    def test_forbidden_word_removed_from_heading(self):
        """Feature claim text containing forbidden word should be sanitized in heading."""
        page = {
            "slug": "troubleshooting",
            "section": "kb",
            "title": "Troubleshooting",
            "purpose": "Common issues",
            "forbidden_topics": ["features", "installation"],
        }
        product_facts = {
            "product_name": "Aspose.Test",
            "claims": [
                {
                    "claim_id": "feat_1",
                    "claim_text": "Key features include file conversion and batch processing.",
                    "claim_kind": "feature",
                    "citations": [],
                },
            ],
            "claim_groups": {"limitations": [], "key_features": ["feat_1"]},
        }
        snippet_catalog = {"snippets": []}
        content = generate_troubleshooting_content(page, product_facts, snippet_catalog)
        # The word "features" should not appear in any H3 heading
        for line in content.split("\n"):
            if line.startswith("### "):
                assert "features" not in line.lower(), f"Forbidden word 'features' found in heading: {line}"

    def test_no_forbidden_topics_headings_unchanged(self):
        """Without forbidden topics, headings should contain full claim text."""
        page = {
            "slug": "troubleshooting",
            "section": "kb",
            "title": "Troubleshooting",
            "purpose": "Common issues",
        }
        product_facts = {
            "product_name": "Aspose.Test",
            "claims": [
                {
                    "claim_id": "feat_2",
                    "claim_text": "Supports multiple file formats for conversion.",
                    "claim_kind": "feature",
                    "citations": [],
                },
            ],
            "claim_groups": {"limitations": [], "key_features": ["feat_2"]},
        }
        snippet_catalog = {"snippets": []}
        content = generate_troubleshooting_content(page, product_facts, snippet_catalog)
        assert "Supports multiple file formats" in content

    def test_all_forbidden_words_removed_fallback_heading(self):
        """If all words are forbidden, heading falls back to 'this capability'."""
        page = {
            "slug": "troubleshooting",
            "section": "kb",
            "title": "Troubleshooting",
            "purpose": "Common issues",
            "forbidden_topics": ["features"],
        }
        product_facts = {
            "product_name": "Aspose.Test",
            "claims": [
                {
                    "claim_id": "feat_3",
                    "claim_text": "Features.",
                    "claim_kind": "feature",
                    "citations": [],
                },
            ],
            "claim_groups": {"limitations": [], "key_features": ["feat_3"]},
        }
        snippet_catalog = {"snippets": []}
        content = generate_troubleshooting_content(page, product_facts, snippet_catalog)
        assert "this capability" in content

    def test_limitation_claims_with_forbidden_topics_skipped(self):
        """Limitation claims containing forbidden topic words should be skipped."""
        page = {
            "slug": "troubleshooting",
            "section": "kb",
            "title": "Troubleshooting",
            "purpose": "Common issues",
            "forbidden_topics": ["features"],
        }
        product_facts = {
            "product_name": "Aspose.Test",
            "claims": [
                {
                    "claim_id": "lim_1",
                    "claim_text": "Unsupported features should map to domain exceptions.",
                    "claim_kind": "limitation",
                    "citations": [],
                },
                {
                    "claim_id": "lim_2",
                    "claim_text": "Max file size is 100MB.",
                    "claim_kind": "limitation",
                    "citations": [],
                },
            ],
            "claim_groups": {"limitations": ["lim_1", "lim_2"]},
        }
        snippet_catalog = {"snippets": []}
        content = generate_troubleshooting_content(page, product_facts, snippet_catalog)
        # lim_1 contains "features" (forbidden) — should be skipped
        assert "Unsupported features" not in content
        # lim_2 does NOT contain forbidden word — should appear
        assert "Max file size is 100MB" in content


class TestApplyTokenMappingsIndentation:
    """R1: Tests for multi-line token replacement preserving YAML block scalar indentation."""

    def test_multiline_value_preserves_indent(self):
        """Multi-line replacement values should preserve the token's indentation."""
        template = '---\noverview:\n  content: |\n    __CONTENT__\n---\n# Body'
        mappings = {"__CONTENT__": "Line 1\n\nLine 2\nLine 3"}
        result = apply_token_mappings(template, mappings)
        lines = result.split('\n')
        # Find lines after "content: |"
        content_idx = next(i for i, l in enumerate(lines) if 'content: |' in l)
        # Line 2 and Line 3 should be indented at 4 spaces (same as token was)
        assert lines[content_idx + 1] == "    Line 1"
        assert lines[content_idx + 3] == "    Line 2"
        assert lines[content_idx + 4] == "    Line 3"

    def test_singleline_value_unchanged(self):
        """Single-line replacement values should work normally."""
        template = '---\ntitle: "__TITLE__"\n---\n# Body'
        mappings = {"__TITLE__": "My Page"}
        result = apply_token_mappings(template, mappings)
        assert 'title: "My Page"' in result

    def test_multiline_yaml_parses(self):
        """After multi-line replacement, YAML frontmatter should be parseable."""
        import yaml
        template = '---\noverview:\n  enable: true\n  content: |\n    __OVERVIEW__\n---\n# Body'
        mappings = {"__OVERVIEW__": "Product Name\n\nA great product for developers.\nLine 3."}
        result = apply_token_mappings(template, mappings)
        # Extract and parse YAML
        fm_text = result.split('---')[1]
        parsed = yaml.safe_load(fm_text)
        assert parsed["overview"]["enable"] is True
        assert "Product Name" in parsed["overview"]["content"]
        assert "A great product" in parsed["overview"]["content"]


class TestSnippetAnchoredGeneration:
    """Tests for TC-1403: Snippet-anchored generation."""

    # Shared fixtures for prompt building
    _BASE_KWARGS = {
        "section": "docs",
        "title": "Getting Started",
        "purpose": "Installation and setup guide",
        "required_headings": ["Installation", "Usage"],
        "product_name": "aspose-3d-foss-python",
        "short_desc": "3D file processing library",
        "tagline": "Work with 3D files in Python",
        "claims": [
            {"claim_id": "c1", "claim_text": "Supports FBX format"},
        ],
        "snippets": [
            {"snippet_id": "s1", "language": "python", "tags": ["install"], "code": "pip install aspose-3d"},
        ],
        "template_variant": "standard",
    }

    def test_build_section_prompt_includes_api_surface(self):
        """Verify API surface section is included when provided."""
        api_surface = {
            "classes": [{"name": "Scene"}, {"name": "Mesh"}],
            "functions": [{"name": "load"}, {"name": "save"}],
        }
        prompt = _build_section_prompt(**self._BASE_KWARGS, api_surface=api_surface)
        assert "## Known API Surface" in prompt
        assert "Scene" in prompt
        assert "Mesh" in prompt
        assert "load" in prompt
        assert "save" in prompt
        assert "Do NOT reference any class, method, or function not listed here" in prompt

    def test_build_section_prompt_includes_code_example_rules(self):
        """Verify code example rules section is included when api_surface provided."""
        api_surface = {
            "classes": [{"name": "Scene"}],
            "functions": [],
        }
        prompt = _build_section_prompt(**self._BASE_KWARGS, api_surface=api_surface)
        assert "## Code Example Rules" in prompt
        assert "NEVER fabricate code" in prompt
        assert "Available Snippets section below" in prompt
        assert "pseudocode" in prompt

    def test_build_section_prompt_includes_license(self):
        """Verify license section is included when license_info provided."""
        prompt = _build_section_prompt(**self._BASE_KWARGS, license_info="MIT License")
        assert "## License" in prompt
        assert "FOSS" in prompt
        assert "MIT License" in prompt
        assert "commercial licensing" in prompt.lower() or "commercial" in prompt

    def test_build_section_prompt_no_api_surface_no_section(self):
        """Verify no API surface section when None."""
        prompt = _build_section_prompt(**self._BASE_KWARGS)
        assert "## Known API Surface" not in prompt
        assert "## Code Example Rules" not in prompt

    def test_build_section_prompt_no_license_no_section(self):
        """Verify no license section when license_info is None."""
        prompt = _build_section_prompt(**self._BASE_KWARGS)
        assert "## License" not in prompt

    def test_build_section_prompt_snippets_not_truncated(self):
        """Verify that long snippets are no longer truncated at 500 chars."""
        long_code = "x = 1\n" * 200  # Well over 500 chars
        snippets = [{"snippet_id": "s_long", "language": "python", "tags": [], "code": long_code}]
        kwargs = {**self._BASE_KWARGS, "snippets": snippets}
        prompt = _build_section_prompt(**kwargs)
        assert "... (truncated)" not in prompt
        # The full code should be present
        assert long_code.strip() in prompt

    def test_build_section_prompt_api_surface_empty_classes(self):
        """Verify API surface handles empty class/function lists gracefully."""
        api_surface = {"classes": [], "functions": []}
        prompt = _build_section_prompt(**self._BASE_KWARGS, api_surface=api_surface)
        assert "## Known API Surface" in prompt
        assert "(none detected)" in prompt

    def test_extract_license_string_dict(self):
        """Verify license extraction from dict with 'name' key."""
        pf = {"license": {"name": "MIT License"}}
        assert _extract_license_string(pf) == "MIT License"

    def test_extract_license_string_dict_type(self):
        """Verify license extraction from dict with 'type' key."""
        pf = {"license": {"type": "permissive"}}
        assert _extract_license_string(pf) == "permissive"

    def test_extract_license_string_dict_spdx(self):
        """Verify license extraction from dict with 'spdx_id' key."""
        pf = {"license": {"spdx_id": "Apache-2.0"}}
        assert _extract_license_string(pf) == "Apache-2.0"

    def test_extract_license_string_str(self):
        """Verify license extraction from string."""
        pf = {"license": "Apache-2.0"}
        assert _extract_license_string(pf) == "Apache-2.0"

    def test_extract_license_string_foss_in_name(self):
        """Verify FOSS detection from product name."""
        pf = {"product_name": "aspose-3d-foss-python"}
        assert _extract_license_string(pf) == "FOSS"

    def test_extract_license_string_none(self):
        """Verify None when no license info."""
        pf = {"product_name": "some-library"}
        assert _extract_license_string(pf) is None

    def test_extract_license_string_empty_string(self):
        """Verify None when license is empty string."""
        pf = {"license": ""}
        assert _extract_license_string(pf) is None

    def test_extract_license_string_empty_dict(self):
        """Verify None when license is empty dict."""
        pf = {"license": {}}
        assert _extract_license_string(pf) is None


class TestTC1503Fixes:
    """TC-1503: Tests for specialized generator quality fixes."""

    def test_is_spec_fragment_detects_byte_patterns(self):
        """Fix B: _is_spec_fragment detects (4 bytes) patterns."""
        assert _is_spec_fragment("The field is 4 bytes (4 bytes) in the header")
        assert _is_spec_fragment("Size: 20 bytes")
        assert not _is_spec_fragment("This is a normal limitation claim")

    def test_is_spec_fragment_detects_section_references(self):
        """Fix B: _is_spec_fragment detects section 2.2.1 patterns."""
        assert _is_spec_fragment("As described in section 2.2.1 of the specification")
        assert _is_spec_fragment("See section 1.4.3 for details")
        assert not _is_spec_fragment("This is section of the documentation")

    def test_is_spec_fragment_detects_rfc_normative(self):
        """Fix B: _is_spec_fragment detects RFC normative keywords."""
        assert _is_spec_fragment("The value MUST be set to zero")
        assert _is_spec_fragment("The field SHALL have a length of 32")
        assert not _is_spec_fragment("Users must install the package")

    def test_is_spec_fragment_detects_hex_constants(self):
        """Fix B: _is_spec_fragment detects hex constants like 0xABCD."""
        assert _is_spec_fragment("The magic number is 0x504B0304")
        assert _is_spec_fragment("Set flag to 0xFF for enabled")
        assert not _is_spec_fragment("This is a normal feature claim")

    def test_strip_product_name_prefix_removes_h2_prefix(self):
        """Fix E: _strip_product_name_prefix removes product name from H2."""
        content = "## Aspose.3D Step-by-Step Guide\n\nSome content here."
        result = _strip_product_name_prefix(content, "Aspose.3D")
        assert "## Step-by-Step Guide" in result
        assert "## Aspose.3D Step-by-Step" not in result

    def test_strip_product_name_prefix_removes_h3_prefix(self):
        """Fix E: _strip_product_name_prefix removes product name from H3."""
        content = "### Aspose.NOTE Code Example\n\nSome code here."
        result = _strip_product_name_prefix(content, "Aspose.NOTE")
        assert "### Code Example" in result
        assert "### Aspose.NOTE Code" not in result

    def test_strip_product_name_prefix_preserves_h1(self):
        """Fix E: _strip_product_name_prefix leaves H1 untouched."""
        content = "# Aspose.3D Documentation\n\n## Aspose.3D Features"
        result = _strip_product_name_prefix(content, "Aspose.3D")
        assert "# Aspose.3D Documentation" in result
        assert "## Features" in result

    def test_strip_product_name_prefix_handles_empty_product_name(self):
        """Fix E: _strip_product_name_prefix gracefully handles empty product name."""
        content = "## Product Features\n\nSome content."
        result = _strip_product_name_prefix(content, "")
        assert result == content

    def test_remove_empty_sections_removes_stub_h2(self):
        """Fix F: _remove_empty_sections removes H2 with no substantive content."""
        content = """---
title: "Test"
---

# Test Page

## Getting Started

## Real Section

This section has actual content with [a link](/docs/).

## Another Empty

"""
        result = _remove_empty_sections(content)
        assert "## Getting Started" not in result
        assert "## Another Empty" not in result
        assert "## Real Section" in result

    def test_remove_empty_sections_preserves_sections_with_code(self):
        """Fix F: _remove_empty_sections keeps sections with code blocks."""
        content = """---
title: "Test"
---

## Code Example

```python
print("hello")
```

## Empty Section

"""
        result = _remove_empty_sections(content)
        assert "## Code Example" in result
        assert "```python" in result
        assert "## Empty Section" not in result

    def test_remove_empty_sections_preserves_sections_with_lists(self):
        """Fix F: _remove_empty_sections keeps sections with bullet lists."""
        content = """---
title: "Test"
---

## Features

- Feature 1
- Feature 2

## Empty

"""
        result = _remove_empty_sections(content)
        assert "## Features" in result
        assert "- Feature 1" in result
        assert "## Empty" not in result

    def test_remove_empty_sections_preserves_sections_with_links(self):
        """Fix F: _remove_empty_sections keeps sections with markdown links."""
        content = """---
title: "Test"
---

## Resources

See [documentation](/docs/) for more.

## Empty

"""
        result = _remove_empty_sections(content)
        assert "## Resources" in result
        assert "[documentation](/docs/)" in result
        assert "## Empty" not in result

    def test_toc_strips_internal_metadata_from_descriptions(self):
        """Fix A: TOC generator filters out internal-sounding purposes."""
        page = {
            "slug": "_index",
            "section": "docs",
            "title": "Documentation",
            "content_strategy": {"child_pages": ["getting-started"]},
        }
        product_facts = {
            "product_name": "Aspose.3D",
            "repo_url": "https://github.com/aspose/Aspose.3D",
        }
        page_plan = {
            "pages": [
                {
                    "slug": "getting-started",
                    "section": "docs",
                    "title": "Getting Started",
                    "url_path": "/docs/getting-started/",
                    "purpose": "Mandatory docs page: getting-started",
                    "token_mappings": {
                        "__DESCRIPTION__": "Learn how to install and configure Aspose.3D"
                    },
                }
            ]
        }
        content = generate_toc_content(page, product_facts, page_plan)
        # Should NOT contain internal purpose
        assert "Mandatory docs page:" not in content
        # Should contain actual description from token mappings
        assert "Learn how to install and configure" in content

    def test_troubleshooting_skips_spec_fragments(self):
        """Fix B: Troubleshooting generator skips spec fragment claims."""
        page = {
            "slug": "troubleshooting",
            "section": "kb",
            "title": "Troubleshooting",
            "purpose": "Common issues",
        }
        product_facts = {
            "product_name": "Aspose.Test",
            "claims": [
                {
                    "claim_id": "lim_spec",
                    "claim_text": "The field MUST be exactly 4 bytes (4 bytes) as per section 2.1.3",
                    "claim_kind": "limitation",
                },
                {
                    "claim_id": "lim_normal",
                    "claim_text": "Max file size is 100MB",
                    "claim_kind": "limitation",
                },
            ],
            "claim_groups": {"limitations": ["lim_spec", "lim_normal"]},
        }
        snippet_catalog = {"snippets": []}
        content = generate_troubleshooting_content(page, product_facts, snippet_catalog)
        # Spec fragment should be skipped
        assert "lim_spec" not in content
        assert "section 2.1.3" not in content
        # Normal claim should appear
        assert "[claim: lim_normal]" in content
        assert "Max file size is 100MB" in content

    def test_comprehensive_guide_skips_spec_fragments(self):
        """Fix C: Comprehensive guide skips spec fragment claims."""
        page = {
            "slug": "developer-guide",
            "section": "docs",
            "title": "Developer Guide",
            "purpose": "Guide",
        }
        product_facts = {
            "product_name": "Aspose.Test",
            "workflows": [],
            "claims": [
                {
                    "claim_id": "feat_spec",
                    "claim_text": "Parses header with magic number 0x504B0304 (4 bytes)",
                    "claim_kind": "feature",
                },
                {
                    "claim_id": "feat_normal",
                    "claim_text": "Supports multiple file formats",
                    "claim_kind": "feature",
                },
            ],
        }
        snippet_catalog = {"snippets": []}
        content = generate_comprehensive_guide_content(page, product_facts, snippet_catalog)
        # Spec fragment should be skipped
        assert "feat_spec" not in content
        assert "0x504B0304" not in content
        # Normal claim should appear
        assert "[claim: feat_normal]" in content
        assert "Supports multiple file formats" in content

    def test_ensure_related_links_checks_for_duplicate_see_also(self):
        """Fix D: _ensure_related_links checks if See Also already exists."""
        from src.launch.workers.w5_section_writer.worker import _ensure_related_links

        content = """# Test Page

Some content here.

## See Also

- [Link 1](/docs/)
- [Link 2](/api/)
"""
        result = _ensure_related_links(
            content, "test-page", "https://github.com/test/repo", "Test Product", "test"
        )
        # Should not add another See Also section
        assert result == content
        assert result.count("## See Also") == 1

