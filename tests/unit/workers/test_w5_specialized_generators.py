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
    generate_section_content,
    _generate_fallback_content,
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
        assert "## Quick Links" in content

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
        assert "## Quick Links" in content
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
        assert "## Additional Resources" in content

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

        # Should still generate content with placeholder code
        assert "### Workflow 1" in content
        assert "### Workflow 2" in content
        assert "```python" in content
        assert "# TODO: Add example" in content

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
                    "claim_text": "Cannot process encrypted OneNote files",
                },
                {
                    "claim_id": "claim_limit_2",
                    "claim_text": "Maximum file size is 500MB",
                },
            ],
        }

        snippet_catalog = {"snippets": []}

        content = generate_comprehensive_guide_content(page, product_facts, snippet_catalog)

        # Verify Limitations section present
        assert "## Limitations" in content
        assert "Known limitations and constraints for Aspose.NOTE:" in content

        # Verify limitation claims with claim markers
        assert "Cannot process encrypted OneNote files [claim: claim_limit_1]" in content
        assert "Maximum file size is 500MB [claim: claim_limit_2]" in content

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
                    "claim_text": "Some limitation",
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
                    "claim_text": "Test limitation",
                },
            ],
        }

        snippet_catalog = {"snippets": []}

        content = generate_comprehensive_guide_content(page, product_facts, snippet_catalog)

        # Verify claim marker format: [claim: claim_id]
        assert "[claim: abc123]" in content
        # Verify it's in a list item
        assert "- Test limitation [claim: abc123]" in content


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
        assert "## When to Use" in content
        assert "## Step-by-Step Guide" in content
        assert "## Code Example" in content
        assert "## Related Links" in content

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

        # Should render placeholder code
        assert "```python" in content
        assert "# Code example for this feature" in content
        assert "# TODO: Add example" in content


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
        assert "## Quick Links" in content
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
        assert "## Additional Resources" in content

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
        assert len(sections) >= 5, f"Expected 5+ sections, got {len(sections)}"

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

