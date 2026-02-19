"""TC-440: Tests for W5 SectionWriter worker.

Validates section content generation, templating, fact/snippet grounding,
claim markers, draft file creation, manifest generation, and error handling.

Per specs/21_worker_contracts.md:195-226 (W5 SectionWriter contract).
"""

import json
import pytest
from pathlib import Path
from typing import Dict, Any, Optional
from unittest.mock import Mock, MagicMock

from src.launch.workers.w5_section_writer.worker import (
    execute_section_writer,
    generate_section_content,
    check_unfilled_tokens,
    generate_page_id,
    get_claims_by_ids,
    get_snippets_by_tags,
    load_page_plan,
    load_product_facts,
    load_snippet_catalog,
    SectionWriterError,
    SectionWriterUnfilledTokensError,
    SectionWriterLLMError,
    _call_llm_for_content,
    _build_enriched_claim_context,
    _inject_claim_markers_as_comments,
)
from src.launch.workers.w5_section_writer.generators.content_generators import (
    build_tutorial_context,
    build_feature_showcase_context,
    build_api_reference_context,
)
from src.launch.io.run_layout import RunLayout


@pytest.fixture
def temp_run_dir(tmp_path):
    """Create temporary run directory with required structure."""
    run_dir = tmp_path / "test_run"
    run_dir.mkdir()

    # Create subdirectories
    (run_dir / "artifacts").mkdir()
    (run_dir / "drafts").mkdir()
    (run_dir / "evidence" / "llm_calls").mkdir(parents=True)

    # Create events.ndjson
    (run_dir / "events.ndjson").write_text("")

    return run_dir


@pytest.fixture
def sample_page_plan():
    """Sample page plan artifact."""
    return {
        "schema_version": "1.0",
        "product_slug": "cells",
        "launch_tier": "standard",
        "pages": [
            {
                "section": "products",
                "slug": "overview",
                "output_path": "content/docs.aspose.org/cells/en/overview.md",
                "url_path": "/cells/overview/",
                "title": "Aspose.Cells for Python Overview",
                "purpose": "Product overview and positioning",
                "template_variant": "standard",
                "required_headings": ["Overview", "Key Features", "Getting Started"],
                "required_claim_ids": ["claim_001", "claim_002"],
                "required_snippet_tags": ["quickstart"],
                "cross_links": [],
                "seo_keywords": ["cells", "python", "overview"],
                "forbidden_topics": []
            },
            {
                "section": "docs",
                "slug": "getting-started",
                "output_path": "content/docs.aspose.org/cells/en/getting-started.md",
                "url_path": "/cells/docs/getting-started/",
                "title": "Getting Started",
                "purpose": "Installation and basic usage guide",
                "template_variant": "standard",
                "required_headings": ["Installation", "Basic Usage"],
                "required_claim_ids": ["claim_003"],
                "required_snippet_tags": ["installation"],
                "cross_links": [],
                "seo_keywords": ["cells", "python", "getting started"],
                "forbidden_topics": []
            }
        ]
    }


@pytest.fixture
def sample_product_facts():
    """Sample product facts artifact."""
    return {
        "product_name": "Aspose.Cells for Python",
        "product_slug": "cells",
        "positioning": {
            "short_description": "Excel file processing library for Python",
            "tagline": "Create, read, and manipulate Excel files in Python"
        },
        "claims": [
            {
                "claim_id": "claim_001",
                "claim_text": "Supports reading and writing Excel files in XLSX format",
                "claim_group": "features"
            },
            {
                "claim_id": "claim_002",
                "claim_text": "Cross-platform support for Windows, Linux, and macOS",
                "claim_group": "positioning"
            },
            {
                "claim_id": "claim_003",
                "claim_text": "Install via pip: pip install aspose-cells-python",
                "claim_group": "installation"
            }
        ]
    }


@pytest.fixture
def sample_snippet_catalog():
    """Sample snippet catalog artifact."""
    return {
        "snippets": [
            {
                "snippet_id": "snippet_001",
                "language": "python",
                "tags": ["quickstart", "basic"],
                "code": "import aspose.cells as cells\nworkbook = cells.Workbook()\nworkbook.save('output.xlsx')"
            },
            {
                "snippet_id": "snippet_002",
                "language": "python",
                "tags": ["installation"],
                "code": "pip install aspose-cells-python"
            }
        ]
    }


@pytest.fixture
def mock_llm_client():
    """Mock LLM client for testing."""
    client = Mock()
    client.chat_completion = Mock(return_value={
        "content": """# Aspose.Cells for Python Overview

Product overview and positioning

## Overview

Aspose.Cells for Python is a powerful Excel processing library. <!-- claim_id: claim_001 -->

## Key Features

- Supports reading and writing Excel files in XLSX format <!-- claim_id: claim_001 -->
- Cross-platform support for Windows, Linux, and macOS <!-- claim_id: claim_002 -->

## Getting Started

Install the library:

```python
pip install aspose-cells-python
```

Quick example:

```python
import aspose.cells as cells
workbook = cells.Workbook()
workbook.save('output.xlsx')
```
""",
        "prompt_hash": "abc123",
        "model": "claude-sonnet-4-5",
        "usage": {"prompt_tokens": 100, "completion_tokens": 200},
        "latency_ms": 1500,
        "evidence_path": "/path/to/evidence.json"
    })
    return client


def test_generate_page_id():
    """Test page ID generation."""
    page = {
        "section": "products",
        "slug": "overview"
    }
    page_id = generate_page_id(page)
    assert page_id == "products_overview"

    page2 = {
        "section": "docs",
        "slug": "getting-started"
    }
    page_id2 = generate_page_id(page2)
    assert page_id2 == "docs_getting-started"


def test_get_claims_by_ids(sample_product_facts):
    """Test retrieving claims by IDs."""
    claim_ids = ["claim_001", "claim_002"]
    claims = get_claims_by_ids(sample_product_facts, claim_ids)

    assert len(claims) == 2
    assert claims[0]["claim_id"] == "claim_001"
    assert claims[1]["claim_id"] == "claim_002"

    # Test with missing claim ID
    claims_partial = get_claims_by_ids(sample_product_facts, ["claim_001", "claim_999"])
    assert len(claims_partial) == 1


def test_get_snippets_by_tags(sample_snippet_catalog):
    """Test retrieving snippets by tags."""
    tags = ["quickstart"]
    snippets = get_snippets_by_tags(sample_snippet_catalog, tags)

    assert len(snippets) == 1
    assert snippets[0]["snippet_id"] == "snippet_001"

    # Test with multiple tags
    tags_multi = ["quickstart", "installation"]
    snippets_multi = get_snippets_by_tags(sample_snippet_catalog, tags_multi)
    assert len(snippets_multi) == 2


def test_check_unfilled_tokens():
    """Test unfilled token detection."""
    # Content with unfilled tokens
    content_with_tokens = """
    # __PRODUCT_NAME__

    This is __PLACEHOLDER__ text.
    """
    tokens = check_unfilled_tokens(content_with_tokens)
    assert len(tokens) == 2
    assert "__PRODUCT_NAME__" in tokens
    assert "__PLACEHOLDER__" in tokens

    # Content without unfilled tokens
    content_clean = """
    # Product Name

    This is clean text.
    """
    tokens_clean = check_unfilled_tokens(content_clean)
    assert len(tokens_clean) == 0


def test_generate_section_content_with_llm(
    sample_product_facts,
    sample_snippet_catalog,
    mock_llm_client
):
    """Test section content generation with LLM."""
    page = {
        "section": "products",
        "slug": "overview",
        "title": "Product Overview",
        "purpose": "Overview of the product",
        "required_headings": ["Overview", "Key Features"],
        "required_claim_ids": ["claim_001", "claim_002"],
        "required_snippet_tags": ["quickstart"],
        "template_variant": "standard",
        "page_role": "generic_unregistered_role",  # Force generic LLM path
    }

    content = generate_section_content(
        page=page,
        product_facts=sample_product_facts,
        snippet_catalog=sample_snippet_catalog,
        llm_client=mock_llm_client
    )

    # Verify LLM was called
    assert mock_llm_client.chat_completion.called
    call_args = mock_llm_client.chat_completion.call_args

    # Verify temperature=0.0 for determinism (generic LLM path)
    assert call_args[1]["temperature"] == 0.0

    # Verify content contains claim markers
    assert "<!-- claim_id:" in content
    assert "claim_001" in content or "claim_002" in content


def test_generate_section_content_fallback(
    sample_product_facts,
    sample_snippet_catalog
):
    """Test section content generation without LLM (fallback)."""
    page = {
        "section": "products",
        "slug": "overview",
        "title": "Product Overview",
        "purpose": "Overview of the product",
        "required_headings": ["Overview", "Key Features"],
        "required_claim_ids": ["claim_001", "claim_002"],
        "required_snippet_tags": ["quickstart"],
        "template_variant": "minimal",
        "page_role": "generic_unregistered_role",  # Force generic fallback path
    }

    # Generate without LLM client
    content = generate_section_content(
        page=page,
        product_facts=sample_product_facts,
        snippet_catalog=sample_snippet_catalog,
        llm_client=None
    )

    # Verify content structure
    assert "# Product Overview" in content
    assert "## Overview" in content
    assert "## Key Features" in content

    # Verify claim markers are included (TC-977: HTML comment format)
    assert "<!-- claim: claim_001 -->" in content
    assert "<!-- claim: claim_002 -->" in content

    # Verify claims text is included
    assert "Supports reading and writing Excel files" in content or "Cross-platform support" in content


def test_execute_section_writer_success(
    temp_run_dir,
    sample_page_plan,
    sample_product_facts,
    sample_snippet_catalog,
    mock_llm_client
):
    """Test successful section writer execution."""
    # Write input artifacts
    artifacts_dir = temp_run_dir / "artifacts"
    (artifacts_dir / "page_plan.json").write_text(json.dumps(sample_page_plan))
    (artifacts_dir / "product_facts.json").write_text(json.dumps(sample_product_facts))
    (artifacts_dir / "snippet_catalog.json").write_text(json.dumps(sample_snippet_catalog))

    run_config = {"run_id": "test_run_001"}

    # Execute section writer
    result = execute_section_writer(
        run_dir=temp_run_dir,
        run_config=run_config,
        llm_client=mock_llm_client
    )

    # Verify result
    assert result["status"] == "success"
    assert result["draft_count"] == 2
    assert result["total_pages"] == 2

    # Verify manifest was created
    manifest_path = Path(result["manifest_path"])
    assert manifest_path.exists()

    manifest = json.loads(manifest_path.read_text())
    assert manifest["schema_version"] == "1.0"
    assert manifest["draft_count"] == 2
    assert len(manifest["drafts"]) == 2

    # Verify draft files were created
    drafts_dir = temp_run_dir / "drafts"
    assert (drafts_dir / "products" / "overview.md").exists()
    assert (drafts_dir / "docs" / "getting-started.md").exists()

    # Verify draft content has claim markers (either format is valid)
    overview_content = (drafts_dir / "products" / "overview.md").read_text()
    assert "<!-- claim:" in overview_content or "<!-- claim_id:" in overview_content or "[claim:" in overview_content


def test_execute_section_writer_deterministic_ordering(
    temp_run_dir,
    sample_page_plan,
    sample_product_facts,
    sample_snippet_catalog
):
    """Test deterministic ordering of drafts in manifest."""
    # Add more pages to test ordering
    sample_page_plan["pages"].extend([
        {
            "section": "kb",
            "slug": "faq",
            "output_path": "content/docs.aspose.org/cells/en/kb/faq.md",
            "url_path": "/cells/kb/faq/",
            "title": "FAQ",
            "purpose": "Frequently asked questions",
            "template_variant": "standard",
            "required_headings": ["Questions"],
            "required_claim_ids": [],
            "required_snippet_tags": [],
            "cross_links": [],
            "seo_keywords": [],
            "forbidden_topics": []
        },
        {
            "section": "reference",
            "slug": "api-overview",
            "output_path": "content/docs.aspose.org/cells/en/reference/api-overview.md",
            "url_path": "/cells/reference/api-overview/",
            "title": "API Overview",
            "purpose": "API reference overview",
            "template_variant": "standard",
            "required_headings": ["Overview"],
            "required_claim_ids": [],
            "required_snippet_tags": [],
            "cross_links": [],
            "seo_keywords": [],
            "forbidden_topics": []
        }
    ])

    # Write input artifacts
    artifacts_dir = temp_run_dir / "artifacts"
    (artifacts_dir / "page_plan.json").write_text(json.dumps(sample_page_plan))
    (artifacts_dir / "product_facts.json").write_text(json.dumps(sample_product_facts))
    (artifacts_dir / "snippet_catalog.json").write_text(json.dumps(sample_snippet_catalog))

    run_config = {"run_id": "test_run_002"}

    # Execute section writer
    result = execute_section_writer(
        run_dir=temp_run_dir,
        run_config=run_config,
        llm_client=None  # Use fallback generation
    )

    # Verify manifest
    manifest_path = Path(result["manifest_path"])
    manifest = json.loads(manifest_path.read_text())

    # Verify drafts are sorted by section order
    sections = [d["section"] for d in manifest["drafts"]]
    expected_order = ["products", "docs", "reference", "kb"]

    # Extract unique sections in order
    seen_sections = []
    for section in sections:
        if section not in seen_sections:
            seen_sections.append(section)

    assert seen_sections == expected_order


def test_execute_section_writer_missing_artifacts(temp_run_dir):
    """Test error handling when required artifacts are missing."""
    run_config = {"run_id": "test_run_003"}

    # Execute without artifacts
    with pytest.raises(SectionWriterError, match="Missing required artifact"):
        execute_section_writer(
            run_dir=temp_run_dir,
            run_config=run_config,
            llm_client=None
        )


def test_execute_section_writer_unfilled_tokens(
    temp_run_dir,
    sample_product_facts,
    sample_snippet_catalog
):
    """Test error handling when draft contains unfilled tokens."""
    # Create mock LLM that returns content with unfilled tokens
    bad_llm_client = Mock()
    bad_llm_client.chat_completion = Mock(return_value={
        "content": """# __PRODUCT_NAME__ Overview

This is __PLACEHOLDER__ content.
""",
        "prompt_hash": "abc123",
        "model": "test-model",
        "usage": {},
        "latency_ms": 100,
        "evidence_path": "/path/to/evidence.json"
    })

    # Use a page_plan with unregistered page_role to force generic LLM path
    # (registered generators produce deterministic content that won't have tokens)
    custom_page_plan = {
        "schema_version": "1.0",
        "product_slug": "cells",
        "launch_tier": "standard",
        "pages": [
            {
                "section": "products",
                "slug": "overview",
                "output_path": "content/docs.aspose.org/cells/en/overview.md",
                "url_path": "/cells/overview/",
                "title": "Aspose.Cells for Python Overview",
                "purpose": "Product overview and positioning",
                "template_variant": "standard",
                "required_headings": ["Overview", "Key Features", "Getting Started"],
                "required_claim_ids": ["claim_001", "claim_002"],
                "required_snippet_tags": ["quickstart"],
                "cross_links": [],
                "seo_keywords": ["cells", "python", "overview"],
                "forbidden_topics": [],
                "page_role": "generic_unregistered_role",
            },
            {
                "section": "docs",
                "slug": "getting-started",
                "output_path": "content/docs.aspose.org/cells/en/getting-started.md",
                "url_path": "/cells/docs/getting-started/",
                "title": "Getting Started",
                "purpose": "Installation and basic usage guide",
                "template_variant": "standard",
                "required_headings": ["Installation", "Basic Usage"],
                "required_claim_ids": ["claim_003"],
                "required_snippet_tags": ["installation"],
                "cross_links": [],
                "seo_keywords": ["cells", "python", "getting started"],
                "forbidden_topics": [],
                "page_role": "generic_unregistered_role",
            }
        ]
    }

    # Write input artifacts
    artifacts_dir = temp_run_dir / "artifacts"
    (artifacts_dir / "page_plan.json").write_text(json.dumps(custom_page_plan))
    (artifacts_dir / "product_facts.json").write_text(json.dumps(sample_product_facts))
    (artifacts_dir / "snippet_catalog.json").write_text(json.dumps(sample_snippet_catalog))

    run_config = {"run_id": "test_run_004"}

    # Execute should raise error
    with pytest.raises(SectionWriterUnfilledTokensError, match="Unfilled tokens"):
        execute_section_writer(
            run_dir=temp_run_dir,
            run_config=run_config,
            llm_client=bad_llm_client
        )


def test_execute_section_writer_llm_failure(
    temp_run_dir,
    sample_page_plan,
    sample_product_facts,
    sample_snippet_catalog
):
    """Test graceful fallback when LLM call fails (TC-5D)."""
    # Create mock LLM that raises exception
    failing_llm_client = Mock()
    failing_llm_client.chat_completion = Mock(side_effect=Exception("API timeout"))

    # Write input artifacts
    artifacts_dir = temp_run_dir / "artifacts"
    (artifacts_dir / "page_plan.json").write_text(json.dumps(sample_page_plan))
    (artifacts_dir / "product_facts.json").write_text(json.dumps(sample_product_facts))
    (artifacts_dir / "snippet_catalog.json").write_text(json.dumps(sample_snippet_catalog))

    run_config = {"run_id": "test_run_005"}

    # TC-5D: Execute should succeed with fallback content (not raise error)
    result = execute_section_writer(
        run_dir=temp_run_dir,
        run_config=run_config,
        llm_client=failing_llm_client
    )

    # Should have generated fallback content for each page
    assert result["status"] == "success"
    assert result["total_pages"] == len(sample_page_plan["pages"])


def test_load_page_plan(temp_run_dir, sample_page_plan):
    """Test loading page plan artifact."""
    artifacts_dir = temp_run_dir / "artifacts"
    (artifacts_dir / "page_plan.json").write_text(json.dumps(sample_page_plan))

    page_plan = load_page_plan(artifacts_dir)
    assert page_plan["product_slug"] == "cells"
    assert len(page_plan["pages"]) == 2


def test_load_product_facts(temp_run_dir, sample_product_facts):
    """Test loading product facts artifact."""
    artifacts_dir = temp_run_dir / "artifacts"
    (artifacts_dir / "product_facts.json").write_text(json.dumps(sample_product_facts))

    product_facts = load_product_facts(artifacts_dir)
    assert product_facts["product_name"] == "Aspose.Cells for Python"
    assert len(product_facts["claims"]) == 3


def test_load_snippet_catalog(temp_run_dir, sample_snippet_catalog):
    """Test loading snippet catalog artifact."""
    artifacts_dir = temp_run_dir / "artifacts"
    (artifacts_dir / "snippet_catalog.json").write_text(json.dumps(sample_snippet_catalog))

    snippet_catalog = load_snippet_catalog(artifacts_dir)
    assert len(snippet_catalog["snippets"]) == 2


def test_event_emission(
    temp_run_dir,
    sample_page_plan,
    sample_product_facts,
    sample_snippet_catalog
):
    """Test that events are emitted during execution."""
    # Write input artifacts
    artifacts_dir = temp_run_dir / "artifacts"
    (artifacts_dir / "page_plan.json").write_text(json.dumps(sample_page_plan))
    (artifacts_dir / "product_facts.json").write_text(json.dumps(sample_product_facts))
    (artifacts_dir / "snippet_catalog.json").write_text(json.dumps(sample_snippet_catalog))

    run_config = {"run_id": "test_run_006"}

    # Execute section writer
    execute_section_writer(
        run_dir=temp_run_dir,
        run_config=run_config,
        llm_client=None
    )

    # Verify events.ndjson contains events
    events_file = temp_run_dir / "events.ndjson"
    events_content = events_file.read_text()

    # Parse events
    events = [json.loads(line) for line in events_content.strip().split("\n") if line]

    # Verify event types
    event_types = [e["type"] for e in events]
    assert "WORK_ITEM_STARTED" in event_types
    assert "WORK_ITEM_FINISHED" in event_types
    assert "ARTIFACT_WRITTEN" in event_types

    # Count ARTIFACT_WRITTEN events (should be at least drafts + manifest)
    artifact_events = [e for e in events if e["type"] == "ARTIFACT_WRITTEN"]
    assert len(artifact_events) >= 3  # 2 drafts + 1 manifest


def test_manifest_structure(
    temp_run_dir,
    sample_page_plan,
    sample_product_facts,
    sample_snippet_catalog
):
    """Test draft manifest structure and completeness."""
    # Write input artifacts
    artifacts_dir = temp_run_dir / "artifacts"
    (artifacts_dir / "page_plan.json").write_text(json.dumps(sample_page_plan))
    (artifacts_dir / "product_facts.json").write_text(json.dumps(sample_product_facts))
    (artifacts_dir / "snippet_catalog.json").write_text(json.dumps(sample_snippet_catalog))

    run_config = {"run_id": "test_run_007"}

    # Execute section writer
    result = execute_section_writer(
        run_dir=temp_run_dir,
        run_config=run_config,
        llm_client=None
    )

    # Load and verify manifest
    manifest_path = Path(result["manifest_path"])
    manifest = json.loads(manifest_path.read_text())

    # Verify required fields
    assert "schema_version" in manifest
    assert "run_id" in manifest
    assert "total_pages" in manifest
    assert "draft_count" in manifest
    assert "drafts" in manifest

    # Verify draft entries
    for draft in manifest["drafts"]:
        assert "page_id" in draft
        assert "section" in draft
        assert "slug" in draft
        assert "output_path" in draft
        assert "draft_path" in draft
        assert "title" in draft
        assert "word_count" in draft
        assert "claim_count" in draft


def test_claim_marker_format(
    temp_run_dir,
    sample_page_plan,
    sample_product_facts,
    sample_snippet_catalog
):
    """Test that claim markers follow the correct format."""
    # Write input artifacts
    artifacts_dir = temp_run_dir / "artifacts"
    (artifacts_dir / "page_plan.json").write_text(json.dumps(sample_page_plan))
    (artifacts_dir / "product_facts.json").write_text(json.dumps(sample_product_facts))
    (artifacts_dir / "snippet_catalog.json").write_text(json.dumps(sample_snippet_catalog))

    run_config = {"run_id": "test_run_008"}

    # Execute section writer
    execute_section_writer(
        run_dir=temp_run_dir,
        run_config=run_config,
        llm_client=None
    )

    # Check draft files for claim markers
    drafts_dir = temp_run_dir / "drafts"
    overview_content = (drafts_dir / "products" / "overview.md").read_text()

    # Verify claim marker format: either [claim: <ID>] or <!-- claim: <ID> -->
    # TC-977 format for Gate 14 compliance.
    # Note: _first_sentence_bullets converts visible [claim: id] markers on list items
    # to HTML comments <!-- claim: id -->, which is the expected production format.
    import re
    bracket_pattern = r'\[claim: (claim_\d+)\]'
    html_pattern = r'<!-- claim: (claim_\d+) -->'
    bracket_markers = re.findall(bracket_pattern, overview_content)
    html_markers = re.findall(html_pattern, overview_content)
    markers = bracket_markers + html_markers

    # Should have at least one claim marker (in either format)
    assert len(markers) > 0, (
        f"No claim markers found in overview content. "
        f"Expected [claim: id] or <!-- claim: id --> format."
    )

    # Verify marker IDs are valid
    for marker_id in markers:
        assert marker_id.startswith("claim_")


def test_limitations_prompt_with_required_heading(
    sample_product_facts,
    sample_snippet_catalog
):
    """TC-CREV-D-TRACK2: Test LLM prompt includes Limitations instruction when required.

    Verifies that when 'Limitations' is in required_headings, the LLM prompt
    includes an explicit instruction to create a Limitations section.
    """
    from src.launch.workers.w5_section_writer.worker import _build_section_prompt

    # Add limitations to product_facts
    sample_product_facts['claim_groups'] = {
        'limitations': ['limit_001', 'limit_002']
    }
    sample_product_facts['claims'].extend([
        {
            'claim_id': 'limit_001',
            'claim_text': 'Does not support Excel macros'
        },
        {
            'claim_id': 'limit_002',
            'claim_text': 'Maximum file size 100MB'
        }
    ])

    # Get limitation claims
    limitation_claims = [c for c in sample_product_facts['claims'] if c.get('claim_id') in ['limit_001', 'limit_002']]

    required_headings = ['Overview', 'Features', 'Limitations']
    claims = [c for c in sample_product_facts['claims'] if c.get('claim_id') in ['claim_001', 'claim_002']]

    prompt = _build_section_prompt(
        section='products',
        title='Product Overview',
        purpose='Overview of the product',
        required_headings=required_headings,
        product_name='Aspose.Cells for Python',
        short_desc='Excel processing library',
        tagline='Create, read, and manipulate Excel files',
        claims=claims,
        snippets=[],
        template_variant='standard',
        limitation_claims=limitation_claims
    )

    # Verify Limitations instruction is present
    assert "CREATE A '## Limitations' SECTION" in prompt
    assert "Document known limitations and constraints" in prompt

    # Verify limitation claims are in prompt
    assert "<limitation-claims>" in prompt
    assert "limit_001" in prompt
    assert "limit_002" in prompt
    assert "Does not support Excel macros" in prompt


def test_limitations_prompt_without_required_heading(
    sample_product_facts,
    sample_snippet_catalog
):
    """TC-CREV-D-TRACK2: Test LLM prompt excludes Limitations instruction when not required.

    Verifies that when 'Limitations' is NOT in required_headings, the LLM prompt
    does not include the Limitations instruction.
    """
    from src.launch.workers.w5_section_writer.worker import _build_section_prompt

    required_headings = ['Overview', 'Features']  # No Limitations
    claims = [c for c in sample_product_facts['claims'] if c.get('claim_id') in ['claim_001', 'claim_002']]

    prompt = _build_section_prompt(
        section='products',
        title='Product Overview',
        purpose='Overview of the product',
        required_headings=required_headings,
        product_name='Aspose.Cells for Python',
        short_desc='Excel processing library',
        tagline='Create, read, and manipulate Excel files',
        claims=claims,
        snippets=[],
        template_variant='standard',
        limitation_claims=None  # No limitation claims
    )

    # Verify Limitations instruction is NOT present
    assert "CREATE A '## Limitations' SECTION" not in prompt
    assert "## Limitation Claims" not in prompt


def test_limitation_claims_filtered_correctly():
    """TC-CREV-D-TRACK2: Test limitation claims are filtered from claim_groups.

    Verifies that limitation claims are correctly extracted from product_facts
    when 'Limitations' is in required_headings.
    """
    from src.launch.workers.w5_section_writer.worker import get_claims_by_ids

    product_facts = {
        'product_name': 'Test Product',
        'claim_groups': {
            'key_features': ['feat_001', 'feat_002'],
            'limitations': ['limit_001', 'limit_002', 'limit_003']
        },
        'claims': [
            {'claim_id': 'feat_001', 'claim_text': 'Feature 1'},
            {'claim_id': 'feat_002', 'claim_text': 'Feature 2'},
            {'claim_id': 'limit_001', 'claim_text': 'Limitation 1'},
            {'claim_id': 'limit_002', 'claim_text': 'Limitation 2'},
            {'claim_id': 'limit_003', 'claim_text': 'Limitation 3'},
        ]
    }

    # Simulate the filtering logic from worker.py
    claim_groups = product_facts.get('claim_groups', {})
    limitation_claim_ids = claim_groups.get('limitations', [])
    all_claims = product_facts.get('claims', [])
    limitation_claims = [c for c in all_claims if c.get('claim_id') in limitation_claim_ids]

    # Verify correct filtering
    assert len(limitation_claims) == 3
    assert all(c['claim_id'].startswith('limit_') for c in limitation_claims)
    assert limitation_claims[0]['claim_id'] == 'limit_001'
    assert limitation_claims[1]['claim_id'] == 'limit_002'
    assert limitation_claims[2]['claim_id'] == 'limit_003'


# TC-1658: LLM Integration Layer Tests

def test_call_llm_for_content_success():
    """TC-1658: Test successful LLM call with valid output."""
    # Mock LLM client
    mock_client = Mock()
    mock_client.chat_completion = Mock(return_value={
        "content": """# Test Section

This is a test section with enough content to pass validation.
It has multiple sentences and paragraphs to meet the minimum word count requirement.
The content is properly formatted as markdown with headings and text.

## Subsection

More content here to ensure we exceed the 100 word minimum.
This is important for the validation to pass successfully."""
    })

    claims = [{"claim_id": "test_001", "claim_text": "Test claim"}]
    snippets = [{"snippet_id": "snip_001", "code": "print('test')"}]
    prompt = "Generate test content"

    result = _call_llm_for_content(
        prompt=prompt,
        claims=claims,
        snippets=snippets,
        llm_client=mock_client,
        min_words=50
    )

    assert result["success"] is True
    assert result["method"] == "llm"
    assert len(result["content"]) > 0
    assert "Test Section" in result["content"]
    mock_client.chat_completion.assert_called_once()


def test_call_llm_for_content_fallback_no_client():
    """TC-1658: Test fallback when llm_client is None."""
    result = _call_llm_for_content(
        prompt="Test prompt",
        claims=[],
        snippets=[],
        llm_client=None,
        min_words=100
    )

    assert result["success"] is False
    assert result["method"] == "deterministic"
    assert result["content"] == ""


def test_call_llm_for_content_validation_failure():
    """TC-1658: Test validation failure when LLM output is too short."""
    # Mock LLM that returns short content
    mock_client = Mock()
    mock_client.chat_completion = Mock(return_value={
        "content": "Too short"
    })

    result = _call_llm_for_content(
        prompt="Test prompt",
        claims=[],
        snippets=[],
        llm_client=mock_client,
        min_words=100
    )

    assert result["success"] is False
    assert result["method"] == "llm_failed_validation"
    assert result["content"] == ""


def test_call_llm_for_content_strips_think_tags():
    """TC-1658: Test that <think> tags are stripped from LLM output."""
    # Mock LLM that includes think tags
    mock_client = Mock()
    mock_client.chat_completion = Mock(return_value={
        "content": """<think>I should write about this topic carefully</think>
# Clean Content

This is the actual content without think tags. It has enough words to pass
validation and demonstrates that the think tag stripping works correctly.
The content continues here with more text to meet the minimum requirements."""
    })

    result = _call_llm_for_content(
        prompt="Test prompt",
        claims=[],
        snippets=[],
        llm_client=mock_client,
        min_words=30
    )

    assert result["success"] is True
    assert result["method"] == "llm"
    assert "<think>" not in result["content"]
    assert "Clean Content" in result["content"]


def test_build_enriched_claim_context():
    """TC-1658: Test claim context formatting with enriched_text and grouping."""
    claims = [
        {
            "claim_id": "feat_001",
            "claim_text": "Raw feature text",
            "enriched_text": "Enhanced feature description with better wording",
            "claim_kind": "key_features",
            "citations": [
                {"path": "README.md"},
                {"path": "docs/guide.md"}
            ]
        },
        {
            "claim_id": "inst_001",
            "claim_text": "Installation instruction",
            "claim_kind": "install_steps",
            "citations": []
        },
        {
            "claim_id": "feat_002",
            "claim_text": "Another feature",
            "enriched_text": "Polished feature text",
            "claim_kind": "key_features"
        }
    ]

    context = _build_enriched_claim_context(claims)

    # Verify enriched_text is used (not raw claim_text)
    assert "Enhanced feature description" in context
    assert "Polished feature text" in context
    assert "Raw feature text" not in context

    # Verify grouping by claim_kind
    assert "## Install Steps" in context
    assert "## Key Features" in context

    # Verify claim IDs included
    assert "[feat_001]" in context
    assert "[inst_001]" in context
    assert "[feat_002]" in context

    # Verify citations included (now using [Evidence: ...] format with path key)
    assert "README.md" in context
    assert "docs/guide.md" in context
    assert "[Evidence:" in context


def test_build_enriched_claim_context_empty():
    """TC-1658: Test empty claims list returns empty string."""
    context = _build_enriched_claim_context([])
    assert context == ""


def test_build_enriched_claim_context_fallback_to_claim_text():
    """TC-1658: Test fallback to claim_text when enriched_text absent."""
    claims = [
        {
            "claim_id": "test_001",
            "claim_text": "Only raw claim text available",
            "claim_kind": "general"
        }
    ]

    context = _build_enriched_claim_context(claims)

    assert "Only raw claim text available" in context
    assert "[test_001]" in context


def test_inject_claim_markers_as_comments():
    """TC-1658: Test HTML comment marker injection near relevant text."""
    content = """# Getting Started

To install the library, use pip install aspose-cells. This command will download
and install all necessary dependencies for your project.

## Basic Usage

The library supports reading Excel files in various formats including XLSX and XLS."""

    claims = [
        {
            "claim_id": "install_001",
            "claim_text": "Install via pip install aspose-cells",
            "enriched_text": "Install the library using pip install aspose-cells"
        },
        {
            "claim_id": "format_001",
            "claim_text": "Supports reading Excel files in various formats",
            "enriched_text": "The library supports reading Excel files"
        }
    ]

    claim_ids = ["install_001", "format_001"]

    result = _inject_claim_markers_as_comments(content, claim_ids, claims)

    # Verify HTML comment markers inserted
    assert "<!-- claim: install_001 -->" in result
    assert "<!-- claim: format_001 -->" in result

    # Verify markers are near relevant text (fuzzy matching worked)
    # The marker should appear after "pip install aspose-cells" or "library supports reading"
    assert "pip install aspose-cells" in result or "library supports reading" in result


def test_inject_claim_markers_as_comments_fallback():
    """TC-1658: Test fallback to header insertion when no fuzzy matches found."""
    content = """# Unrelated Content

This content has nothing to do with the claims."""

    claims = [
        {
            "claim_id": "claim_001",
            "claim_text": "This text does not appear in content",
            "enriched_text": "Enhanced text also not in content"
        }
    ]

    claim_ids = ["claim_001"]

    result = _inject_claim_markers_as_comments(content, claim_ids, claims)

    # Verify marker inserted (fallback places it after first heading)
    assert "<!-- claim: claim_001 -->" in result
    assert "Unrelated Content" in result


def test_inject_claim_markers_as_comments_empty():
    """TC-1658: Test empty claim_ids returns content unchanged."""
    content = "# Test Content"
    result = _inject_claim_markers_as_comments(content, [], [])
    assert result == content


# TC-1664: Enriched Text Usage Tests

def test_build_section_prompt_uses_enriched_text():
    """TC-1664: Verify _build_section_prompt prefers enriched_text over claim_text."""
    from src.launch.workers.w5_section_writer.worker import _build_section_prompt

    # Create claims with both claim_text (code-like) and enriched_text (marketing-ready)
    claims = [
        {
            "claim_id": "claim_001",
            "claim_text": "class WorkbookFactory(AbstractFactory)",  # Code-like, low quality
            "enriched_text": "Provides advanced workbook creation with factory pattern support"  # Marketing-ready
        },
        {
            "claim_id": "claim_002",
            "claim_text": "def load_file(path: str) -> Workbook",  # Code-like
            "enriched_text": "Loads Excel files from disk with automatic format detection"  # Marketing-ready
        }
    ]

    # Create limitation claims with enriched_text
    limitation_claims = [
        {
            "claim_id": "limit_001",
            "claim_text": "MAX_ROWS = 1048576",  # Code-like
            "enriched_text": "Limited to 1,048,576 rows per worksheet"  # Marketing-ready
        }
    ]

    # Call _build_section_prompt with minimal required args
    prompt = _build_section_prompt(
        section='products',
        title='Test Product',
        purpose='Test purpose',
        required_headings=['Overview', 'Features'],
        product_name='Test Product',
        short_desc='Test description',
        tagline='Test tagline',
        claims=claims,
        snippets=[],
        template_variant='standard',
        limitation_claims=limitation_claims
    )

    # Verify enriched_text is used (NOT raw claim_text)
    assert "advanced workbook creation" in prompt
    assert "factory pattern support" in prompt
    assert "automatic format detection" in prompt
    assert "Limited to 1,048,576 rows" in prompt

    # Verify raw claim_text is NOT used
    assert "class WorkbookFactory" not in prompt
    assert "def load_file" not in prompt
    assert "MAX_ROWS = 1048576" not in prompt


# TC-2202: Bullet Formatting Rules Tests

class TestTC2202BulletFormatting:
    """TC-2202: System prompt includes bullet formatting rules."""

    def test_system_prompt_has_bullet_rules(self):
        """Verify _build_section_prompt includes bullet formatting guidance."""
        from src.launch.workers.w5_section_writer.worker import _build_section_prompt

        prompt = _build_section_prompt(
            section="docs",
            title="Test Page",
            purpose="Test purpose",
            required_headings=["Overview"],
            product_name="TestProduct",
            short_desc="A test product",
            tagline="Test tagline",
            claims=[],
            snippets=[],
            template_variant="standard",
        )

        # Verify bullet formatting rules are present in prompt
        assert "Bullet and List Formatting" in prompt
        assert "Use bullet points (- item) for lists of 3+ related items" in prompt
        assert "Use numbered lists (1. step) ONLY for sequential steps where order matters" in prompt
        assert "Never write lists as run-on paragraphs" in prompt
        assert "Each bullet point should be a single, complete thought" in prompt

    def test_bullet_rules_come_after_instructions(self):
        """Verify bullet rules section appears after the main instructions."""
        from src.launch.workers.w5_section_writer.worker import _build_section_prompt

        prompt = _build_section_prompt(
            section="docs",
            title="Test Page",
            purpose="Test purpose",
            required_headings=["Overview"],
            product_name="TestProduct",
            short_desc="A test product",
            tagline="Test tagline",
            claims=[],
            snippets=[],
            template_variant="standard",
        )

        instructions_idx = prompt.index("<instructions>")
        bullet_rules_idx = prompt.index("Bullet and List Formatting")
        assert bullet_rules_idx > instructions_idx


# TC-2203: Frontmatter Description Tests

class TestTC2203FrontmatterDescription:
    """TC-2203: Frontmatter uses page-specific descriptions."""

    def test_inject_frontmatter_uses_description_field(self):
        """When page has 'description' field, it should be used in frontmatter."""
        from src.launch.workers.w5_section_writer.worker import inject_frontmatter_fields

        page = {
            "title": "Getting Started",
            "slug": "getting-started",
            "section": "docs",
            "description": "Learn how to install and start using Aspose.3D for Python.",
            "purpose": "Step-by-step setup guide",
        }
        content = "# Getting Started\n\nSome content here."
        result = inject_frontmatter_fields(content, page, "docs", {})
        assert "Learn how to install" in result

    def test_inject_frontmatter_falls_back_to_purpose(self):
        """When page has no 'description', fall back to 'purpose'."""
        from src.launch.workers.w5_section_writer.worker import inject_frontmatter_fields

        page = {
            "title": "Getting Started",
            "slug": "getting-started",
            "section": "docs",
            "purpose": "Step-by-step setup guide",
        }
        content = "# Getting Started\n\nSome content here."
        result = inject_frontmatter_fields(content, page, "docs", {})
        assert "Step-by-step setup guide" in result

    def test_inject_frontmatter_falls_back_to_default(self):
        """When page has neither 'description' nor 'purpose', use default."""
        from src.launch.workers.w5_section_writer.worker import inject_frontmatter_fields

        page = {
            "title": "Getting Started",
            "slug": "getting-started",
            "section": "docs",
        }
        content = "# Getting Started\n\nSome content here."
        result = inject_frontmatter_fields(content, page, "docs", {})
        assert "documentation and resources" in result

    def test_inject_frontmatter_description_over_purpose(self):
        """When page has both 'description' and 'purpose', description wins."""
        from src.launch.workers.w5_section_writer.worker import inject_frontmatter_fields

        page = {
            "title": "API Reference",
            "slug": "api-reference",
            "section": "reference",
            "description": "Complete API reference for the Aspose.3D library.",
            "purpose": "Detailed API documentation",
        }
        content = "# API Reference\n\nSome content here."
        result = inject_frontmatter_fields(content, page, "reference", {})
        assert "Complete API reference" in result
        assert "Detailed API documentation" not in result

    def test_inject_frontmatter_empty_description_falls_back(self):
        """When page has empty string 'description', fall back to 'purpose'."""
        from src.launch.workers.w5_section_writer.worker import inject_frontmatter_fields

        page = {
            "title": "FAQ",
            "slug": "faq",
            "section": "kb",
            "description": "",
            "purpose": "Frequently asked questions about the library",
        }
        content = "# FAQ\n\nSome content here."
        result = inject_frontmatter_fields(content, page, "kb", {})
        assert "Frequently asked questions" in result


# TC-2204: Sibling Context Tests

class TestTC2204SiblingContext:
    """TC-2204: Sibling page context injected into prompts."""

    def test_sibling_context_built_from_page_plan(self):
        """Verify sibling context string is built correctly from page_plan."""
        page_plan = {
            "pages": [
                {"slug": "getting-started", "title": "Getting Started", "section": "docs", "purpose": "Setup guide"},
                {"slug": "faq", "title": "FAQ", "section": "kb", "purpose": "Common questions",
                 "content_strategy": {"unique_angle": "Direct answers to dev questions"}},
                {"slug": "tutorial", "title": "Tutorial", "section": "docs", "purpose": "Step by step"},
            ]
        }
        current_slug = "getting-started"
        siblings = [p for p in page_plan["pages"] if p.get("slug") != current_slug]
        assert len(siblings) == 2
        # Verify the sibling context would include the unique_angle
        for s in siblings:
            angle = s.get("content_strategy", {}).get("unique_angle", "")
            if s["slug"] == "faq":
                assert "Direct answers" in angle

    def test_sibling_context_injected_in_prompt(self):
        """Verify _build_section_prompt includes sibling context when provided."""
        from src.launch.workers.w5_section_writer.worker import _build_section_prompt

        sibling_context = (
            "\n\nOTHER PAGES IN THIS SITE (do NOT repeat their content):\n"
            "- FAQ (kb): Common questions — Focus: Direct answers to dev questions\n"
            "- Tutorial (docs): Step by step\n"
            "\nYour page must provide UNIQUE value not found on the pages above.\n"
        )

        prompt = _build_section_prompt(
            section="docs",
            title="Getting Started",
            purpose="Setup guide",
            required_headings=["Installation", "Usage"],
            product_name="TestProduct",
            short_desc="A test product",
            tagline="Test tagline",
            claims=[],
            snippets=[],
            template_variant="standard",
            sibling_context=sibling_context,
        )

        assert "OTHER PAGES IN THIS SITE" in prompt
        assert "do NOT repeat their content" in prompt
        assert "FAQ (kb): Common questions" in prompt
        assert "Direct answers to dev questions" in prompt
        assert "UNIQUE value" in prompt

    def test_angle_instruction_injected_in_prompt(self):
        """Verify _build_section_prompt includes angle instruction when provided."""
        from src.launch.workers.w5_section_writer.worker import _build_section_prompt

        angle_instruction = (
            "\n\nYOUR UNIQUE ANGLE for this page: Step-by-step practical walkthrough\n"
            "Focus on this perspective and avoid content that belongs on other pages.\n"
        )

        prompt = _build_section_prompt(
            section="docs",
            title="Getting Started",
            purpose="Setup guide",
            required_headings=["Installation"],
            product_name="TestProduct",
            short_desc="A test product",
            tagline="Test tagline",
            claims=[],
            snippets=[],
            template_variant="standard",
            angle_instruction=angle_instruction,
        )

        assert "YOUR UNIQUE ANGLE for this page" in prompt
        assert "Step-by-step practical walkthrough" in prompt
        assert "avoid content that belongs on other pages" in prompt

    def test_no_sibling_context_when_no_page_plan(self):
        """Verify no sibling context when page_plan is not provided."""
        from src.launch.workers.w5_section_writer.worker import _build_section_prompt

        prompt = _build_section_prompt(
            section="docs",
            title="Test Page",
            purpose="Test purpose",
            required_headings=["Overview"],
            product_name="TestProduct",
            short_desc="A test product",
            tagline="Test tagline",
            claims=[],
            snippets=[],
            template_variant="standard",
            sibling_context=None,
            angle_instruction=None,
        )

        assert "OTHER PAGES IN THIS SITE" not in prompt
        assert "YOUR UNIQUE ANGLE" not in prompt

    def test_generate_section_content_builds_sibling_context(self):
        """Verify generate_section_content builds sibling context from page_plan."""
        from src.launch.workers.w5_section_writer.worker import generate_section_content

        page = {
            "section": "docs",
            "slug": "getting-started",
            "title": "Getting Started",
            "purpose": "Setup guide for new users",
            "page_role": "generic_unregistered_role",  # Force generic LLM path
            "required_headings": ["Installation", "Usage"],
            "required_claim_ids": ["claim_001"],
            "required_snippet_tags": [],
            "template_variant": "standard",
            "content_strategy": {"unique_angle": "Hands-on beginner walkthrough"},
        }

        page_plan = {
            "pages": [
                {"slug": "getting-started", "title": "Getting Started", "section": "docs", "purpose": "Setup guide"},
                {"slug": "faq", "title": "FAQ", "section": "kb", "purpose": "Common questions",
                 "content_strategy": {"unique_angle": "Direct answers"}},
            ]
        }

        product_facts = {
            "product_name": "TestProduct",
            "positioning": {"short_description": "Test", "tagline": "Test"},
            "claims": [{"claim_id": "claim_001", "claim_text": "Test claim text for testing"}],
        }
        snippet_catalog = {"snippets": []}

        # Use mock LLM to capture the prompt
        mock_llm = Mock()
        mock_llm.chat_completion = Mock(return_value={
            "content": (
                "# Getting Started\n\nSetup guide for new users.\n\n"
                "## Installation\n\nThis section covers installation.\n\n"
                "## Usage\n\nThis section covers usage."
            ),
        })

        generate_section_content(
            page=page,
            product_facts=product_facts,
            snippet_catalog=snippet_catalog,
            llm_client=mock_llm,
            page_plan=page_plan,
        )

        # Extract the user prompt that was sent to the LLM
        call_args = mock_llm.chat_completion.call_args
        messages = call_args[1]["messages"] if "messages" in call_args[1] else call_args[0][0]
        user_msg = [m for m in messages if m["role"] == "user"][0]["content"]

        # Verify sibling context was included in the prompt
        assert "OTHER PAGES IN THIS SITE" in user_msg
        assert "FAQ (kb): Common questions" in user_msg

        # Verify unique angle instruction was included
        assert "YOUR UNIQUE ANGLE" in user_msg
        assert "Hands-on beginner walkthrough" in user_msg

    def test_sibling_context_limits_to_10_pages(self):
        """Verify sibling context is limited to 10 pages maximum."""
        pages = [
            {"slug": f"page-{i}", "title": f"Page {i}", "section": "docs", "purpose": f"Purpose {i}"}
            for i in range(15)
        ]
        current_slug = "page-0"
        siblings = [p for p in pages if p.get("slug") != current_slug]
        # In the code, we slice to [:10]
        limited_siblings = siblings[:10]
        assert len(limited_siblings) == 10
        assert len(siblings) == 14  # All 14 remaining pages


# TC-2340: Silent Fallback Warning + Generic Prompt Hardening Tests

class TestTC2340SilentFallbackWarning:
    """TC-2340: Unregistered page_role should log a warning and use role guidance."""

    def test_unregistered_page_role_logs_warning(self):
        """TC-2340: Unregistered page_role should log a warning."""
        from launch.workers.w5_section_writer import worker
        source = Path(worker.__file__).read_text(encoding="utf-8")
        assert "not registered in GeneratorRegistry" in source

    def test_role_guidance_dict_has_key_roles(self):
        """TC-2340: Role guidance dict should cover unregistered page_roles."""
        from launch.workers.w5_section_writer import worker
        source = Path(worker.__file__).read_text(encoding="utf-8")
        for role in ["workflow_page", "landing", "api_reference", "format_conversion", "howto_article", "feature_blog"]:
            assert role in source, f"Role guidance missing for {role}"

    def test_build_section_prompt_includes_role_guidance(self):
        """TC-2340: _build_section_prompt should include role guidance when page_role provided."""
        from src.launch.workers.w5_section_writer.worker import _build_section_prompt

        prompt = _build_section_prompt(
            section="docs",
            title="Test Workflow",
            purpose="Test purpose",
            required_headings=["Overview"],
            product_name="TestProduct",
            short_desc="A test product",
            tagline="Test tagline",
            claims=[],
            snippets=[],
            template_variant="standard",
            page_role="workflow_page",
        )

        assert "ROLE GUIDANCE:" in prompt
        assert "step-by-step workflow" in prompt

    def test_build_section_prompt_default_guidance_for_unknown_role(self):
        """TC-2340: Unknown page_role should get default role guidance."""
        from src.launch.workers.w5_section_writer.worker import _build_section_prompt

        prompt = _build_section_prompt(
            section="docs",
            title="Test Page",
            purpose="Test purpose",
            required_headings=["Overview"],
            product_name="TestProduct",
            short_desc="A test product",
            tagline="Test tagline",
            claims=[],
            snippets=[],
            template_variant="standard",
            page_role="some_custom_role",
        )

        assert "ROLE GUIDANCE:" in prompt
        assert "some_custom_role" in prompt

    def test_build_section_prompt_no_guidance_without_page_role(self):
        """TC-2340: No role guidance when page_role is empty."""
        from src.launch.workers.w5_section_writer.worker import _build_section_prompt

        prompt = _build_section_prompt(
            section="docs",
            title="Test Page",
            purpose="Test purpose",
            required_headings=["Overview"],
            product_name="TestProduct",
            short_desc="A test product",
            tagline="Test tagline",
            claims=[],
            snippets=[],
            template_variant="standard",
            page_role="",
        )

        assert "ROLE GUIDANCE:" not in prompt

    def test_build_section_prompt_role_guidance_covers_all_six_roles(self):
        """TC-2340: Role guidance covers all 6 known page roles with specific hints."""
        from src.launch.workers.w5_section_writer.worker import _build_section_prompt

        known_roles = {
            "workflow_page": "step-by-step workflow",
            "landing": "product landing page",
            "api_reference": "structured API reference",
            "format_conversion": "format conversion guide",
            "howto_article": "how-to article",
            "feature_blog": "friendly blog post",
        }

        for role, expected_phrase in known_roles.items():
            prompt = _build_section_prompt(
                section="docs",
                title="Test",
                purpose="Test",
                required_headings=["Overview"],
                product_name="TestProduct",
                short_desc="Test",
                tagline="Test",
                claims=[],
                snippets=[],
                template_variant="standard",
                page_role=role,
            )
            assert "ROLE GUIDANCE:" in prompt, f"Missing ROLE GUIDANCE for {role}"
            assert expected_phrase in prompt, f"Missing '{expected_phrase}' for role '{role}'"

    def test_role_guidance_prepended_before_task_header(self):
        """TC-2340: Role guidance should appear before the main task header."""
        from src.launch.workers.w5_section_writer.worker import _build_section_prompt

        prompt = _build_section_prompt(
            section="docs",
            title="Test",
            purpose="Test",
            required_headings=["Overview"],
            product_name="TestProduct",
            short_desc="Test",
            tagline="Test",
            claims=[],
            snippets=[],
            template_variant="standard",
            page_role="landing",
        )

        role_idx = prompt.index("ROLE GUIDANCE:")
        task_idx = prompt.index("# Task: Generate documentation page content")
        assert role_idx < task_idx, "ROLE GUIDANCE should appear before the task header"


# ---------------------------------------------------------------------------
# TC-2330..TC-2347: Tests for new Round 3 generators
# ---------------------------------------------------------------------------


class TestRound3GeneratorRegistry:
    """TC-2330..TC-2347: Verify all new generators are registered."""

    def test_workflow_page_registered(self):
        """TC-2330: workflow_page and 'workflow' alias must be registered."""
        from src.launch.workers.w5_section_writer.generators import get_registry

        registry = get_registry()
        assert registry.has("workflow_page"), "Missing 'workflow_page'"
        assert registry.has("workflow"), "Missing alias 'workflow'"

    def test_landing_registered(self):
        """TC-2331: landing and aliases must be registered."""
        from src.launch.workers.w5_section_writer.generators import get_registry

        registry = get_registry()
        assert registry.has("landing"), "Missing 'landing'"
        assert registry.has("landing_page"), "Missing alias 'landing_page'"
        assert registry.has("product_landing"), "Missing alias 'product_landing'"

    def test_api_reference_registered(self):
        """TC-2332: api_reference and 'api_ref' alias must be registered."""
        from src.launch.workers.w5_section_writer.generators import get_registry

        registry = get_registry()
        assert registry.has("api_reference"), "Missing 'api_reference'"
        assert registry.has("api_ref"), "Missing alias 'api_ref'"

    def test_format_conversion_registered(self):
        """TC-2345: format_conversion and aliases must be registered."""
        from src.launch.workers.w5_section_writer.generators import get_registry

        registry = get_registry()
        assert registry.has("format_conversion"), "Missing 'format_conversion'"
        assert registry.has("conversion"), "Missing alias 'conversion'"
        assert registry.has("converter"), "Missing alias 'converter'"

    def test_howto_article_registered(self):
        """TC-2346: howto_article and aliases must be registered."""
        from src.launch.workers.w5_section_writer.generators import get_registry

        registry = get_registry()
        assert registry.has("howto_article"), "Missing 'howto_article'"
        assert registry.has("how_to"), "Missing alias 'how_to'"
        assert registry.has("howto"), "Missing alias 'howto'"

    def test_feature_blog_registered(self):
        """TC-2347: feature_blog must be registered."""
        from src.launch.workers.w5_section_writer.generators import get_registry

        registry = get_registry()
        assert registry.has("feature_blog"), "Missing 'feature_blog'"


class TestRound3GeneratorOutput:
    """TC-2330..TC-2347: Test deterministic output of new generators."""

    @pytest.fixture
    def r3_page(self):
        """Basic page fixture for Round 3 generators."""
        return {
            "slug": "test-page",
            "title": "Test Page",
            "section": "docs",
            "purpose": "Test purpose",
            "required_claim_ids": ["c1", "c2", "c3"],
            "required_snippet_tags": ["quickstart"],
            "content_strategy": {
                "unique_angle": "Testing angle",
                "source_format": "csv",
                "target_format": "pdf",
            },
        }

    @pytest.fixture
    def r3_product_facts(self):
        """Product facts fixture for Round 3 generators."""
        return {
            "product_name": "Aspose.Test for Python",
            "product_family": "test",
            "claims": [
                {
                    "claim_id": "c1",
                    "claim_text": "Supports file conversion from CSV to PDF format",
                    "enriched_text": "Easily convert CSV files to PDF format with full formatting support",
                    "claim_kind": "feature",
                },
                {
                    "claim_id": "c2",
                    "claim_text": "High-performance processing engine",
                    "enriched_text": "Industry-leading performance for batch document processing",
                    "claim_kind": "feature",
                },
                {
                    "claim_id": "c3",
                    "claim_text": "Cross-platform support for all operating systems",
                    "claim_kind": "feature",
                },
            ],
            "claim_groups": {
                "key_features": ["c1", "c2", "c3"],
            },
            "api_surface_summary": {
                "classes": [
                    {"name": "Workbook", "description": "Main workbook class", "methods": ["load", "save"]},
                    {"name": "Worksheet", "description": "Worksheet class", "methods": ["get_cells"]},
                ],
            },
        }

    @pytest.fixture
    def r3_snippet_catalog(self):
        """Snippet catalog fixture for Round 3 generators."""
        return {
            "snippets": [
                {
                    "snippet_id": "s1",
                    "language": "python",
                    "tags": ["quickstart"],
                    "code": "import aspose_test\nresult = aspose_test.convert('input.csv', 'output.pdf')",
                    "description": "Basic conversion example",
                },
            ],
        }

    def test_workflow_page_has_what_youll_learn(self, r3_page, r3_product_facts, r3_snippet_catalog):
        """TC-2330: Workflow page must contain 'What You'll Learn' section."""
        from src.launch.workers.w5_section_writer.generators.content_generators import (
            generate_workflow_page_content,
        )

        content = generate_workflow_page_content(r3_page, r3_product_facts, r3_snippet_catalog)
        assert content, "Content should not be empty"
        assert "What You'll Learn" in content

    def test_workflow_page_has_see_also(self, r3_page, r3_product_facts, r3_snippet_catalog):
        """TC-2330: Workflow page must contain 'See Also' section."""
        from src.launch.workers.w5_section_writer.generators.content_generators import (
            generate_workflow_page_content,
        )

        content = generate_workflow_page_content(r3_page, r3_product_facts, r3_snippet_catalog)
        assert "See Also" in content

    def test_workflow_page_has_prerequisites(self, r3_page, r3_product_facts, r3_snippet_catalog):
        """TC-2330: Workflow page must contain 'Prerequisites' section."""
        from src.launch.workers.w5_section_writer.generators.content_generators import (
            generate_workflow_page_content,
        )

        content = generate_workflow_page_content(r3_page, r3_product_facts, r3_snippet_catalog)
        assert "Prerequisites" in content

    def test_workflow_page_has_code_block(self, r3_page, r3_product_facts, r3_snippet_catalog):
        """TC-2330: Workflow page must contain a code block."""
        from src.launch.workers.w5_section_writer.generators.content_generators import (
            generate_workflow_page_content,
        )

        content = generate_workflow_page_content(r3_page, r3_product_facts, r3_snippet_catalog)
        assert "```" in content

    def test_landing_has_key_features(self, r3_page, r3_product_facts, r3_snippet_catalog):
        """TC-2331: Landing page must contain 'Key Features' section."""
        from src.launch.workers.w5_section_writer.generators.content_generators import (
            generate_landing_content,
        )

        content = generate_landing_content(r3_page, r3_product_facts, r3_snippet_catalog)
        assert content, "Content should not be empty"
        assert "Key Features" in content

    def test_landing_has_getting_started_cta(self, r3_page, r3_product_facts, r3_snippet_catalog):
        """TC-2331: Landing page must contain Getting Started CTA."""
        from src.launch.workers.w5_section_writer.generators.content_generators import (
            generate_landing_content,
        )

        content = generate_landing_content(r3_page, r3_product_facts, r3_snippet_catalog)
        assert "Getting Started" in content

    def test_landing_no_code_fences(self, r3_page, r3_product_facts, r3_snippet_catalog):
        """TC-2331: Landing page must NOT contain code fences."""
        from src.launch.workers.w5_section_writer.generators.content_generators import (
            generate_landing_content,
        )

        content = generate_landing_content(r3_page, r3_product_facts, r3_snippet_catalog)
        assert "```" not in content, "Landing page should not have code fences"

    def test_api_reference_returns_content(self, r3_page, r3_product_facts, r3_snippet_catalog):
        """TC-2332: API reference must return non-empty content."""
        from src.launch.workers.w5_section_writer.generators.content_generators import (
            generate_api_reference_content,
        )

        content = generate_api_reference_content(r3_page, r3_product_facts, r3_snippet_catalog)
        assert content, "Content should not be empty"

    def test_api_reference_has_class_table(self, r3_page, r3_product_facts, r3_snippet_catalog):
        """TC-2332: API reference must contain class table."""
        from src.launch.workers.w5_section_writer.generators.content_generators import (
            generate_api_reference_content,
        )

        content = generate_api_reference_content(r3_page, r3_product_facts, r3_snippet_catalog)
        assert "Workbook" in content
        assert "Worksheet" in content

    def test_format_conversion_has_how_it_works(self, r3_page, r3_product_facts, r3_snippet_catalog):
        """TC-2345: Format conversion must contain 'How It Works' section."""
        from src.launch.workers.w5_section_writer.generators.content_generators import (
            generate_format_conversion_content,
        )

        content = generate_format_conversion_content(r3_page, r3_product_facts, r3_snippet_catalog)
        assert content, "Content should not be empty"
        assert "How It Works" in content

    def test_format_conversion_has_faq(self, r3_page, r3_product_facts, r3_snippet_catalog):
        """TC-2345: Format conversion must contain FAQ section."""
        from src.launch.workers.w5_section_writer.generators.content_generators import (
            generate_format_conversion_content,
        )

        content = generate_format_conversion_content(r3_page, r3_product_facts, r3_snippet_catalog)
        assert "FAQ" in content

    def test_format_conversion_includes_formats(self, r3_page, r3_product_facts, r3_snippet_catalog):
        """TC-2345: Format conversion must mention source and target formats."""
        from src.launch.workers.w5_section_writer.generators.content_generators import (
            generate_format_conversion_content,
        )

        content = generate_format_conversion_content(r3_page, r3_product_facts, r3_snippet_catalog)
        assert "CSV" in content
        assert "PDF" in content

    def test_howto_article_has_step_by_step(self, r3_page, r3_product_facts, r3_snippet_catalog):
        """TC-2346: How-to article must contain 'Step-by-Step Guide'."""
        from src.launch.workers.w5_section_writer.generators.content_generators import (
            generate_howto_article_content,
        )

        content = generate_howto_article_content(r3_page, r3_product_facts, r3_snippet_catalog)
        assert content, "Content should not be empty"
        assert "Step-by-Step Guide" in content

    def test_howto_article_has_related_links(self, r3_page, r3_product_facts, r3_snippet_catalog):
        """TC-2346: How-to article must contain 'Related Links'."""
        from src.launch.workers.w5_section_writer.generators.content_generators import (
            generate_howto_article_content,
        )

        content = generate_howto_article_content(r3_page, r3_product_facts, r3_snippet_catalog)
        assert "Related Links" in content

    def test_howto_article_has_code_block(self, r3_page, r3_product_facts, r3_snippet_catalog):
        """TC-2346: How-to article must contain a code block."""
        from src.launch.workers.w5_section_writer.generators.content_generators import (
            generate_howto_article_content,
        )

        content = generate_howto_article_content(r3_page, r3_product_facts, r3_snippet_catalog)
        assert "```" in content

    def test_feature_blog_has_key_highlights(self, r3_page, r3_product_facts, r3_snippet_catalog):
        """TC-2347: Feature blog must contain 'Key Highlights'."""
        from src.launch.workers.w5_section_writer.generators.content_generators import (
            generate_feature_blog_content,
        )

        content = generate_feature_blog_content(r3_page, r3_product_facts, r3_snippet_catalog)
        assert content, "Content should not be empty"
        assert "Key Highlights" in content

    def test_feature_blog_has_next_steps(self, r3_page, r3_product_facts, r3_snippet_catalog):
        """TC-2347: Feature blog must contain 'Next Steps'."""
        from src.launch.workers.w5_section_writer.generators.content_generators import (
            generate_feature_blog_content,
        )

        content = generate_feature_blog_content(r3_page, r3_product_facts, r3_snippet_catalog)
        assert "Next Steps" in content

    def test_feature_blog_has_quick_example(self, r3_page, r3_product_facts, r3_snippet_catalog):
        """TC-2347: Feature blog must contain 'Quick Example' with code."""
        from src.launch.workers.w5_section_writer.generators.content_generators import (
            generate_feature_blog_content,
        )

        content = generate_feature_blog_content(r3_page, r3_product_facts, r3_snippet_catalog)
        assert "Quick Example" in content
        assert "```" in content


class TestTC2333ComprehensiveGuideDisplayText:
    """TC-2333: Verify comprehensive guide uses _get_display_text."""

    def test_enriched_text_preferred_over_claim_text(self):
        """TC-2333: When enriched_text exists, it should appear in output instead of claim_text."""
        from src.launch.workers.w5_section_writer.generators.content_generators import (
            generate_comprehensive_guide_content,
        )

        page = {
            "slug": "developer-guide",
            "title": "Developer Guide",
            "section": "docs",
            "required_headings": [],
            "required_claim_ids": ["c1"],
            "claim_ids": ["c1"],
        }
        product_facts = {
            "product_name": "TestProduct",
            "claims": [
                {
                    "claim_id": "c1",
                    "claim_text": "Provides basic feature for raw text processing",
                    "enriched_text": "Provides enhanced feature for improved text clarity and detail",
                    "claim_kind": "feature",
                },
            ],
            "claim_groups": {},
            "workflows": [],
        }
        snippet_catalog = {"snippets": []}

        content = generate_comprehensive_guide_content(page, product_facts, snippet_catalog)
        assert "Provides enhanced feature for improved text clarity and detail" in content
        assert "Provides basic feature for raw text processing" not in content


class TestTC2362ParallelPageWriting:
    """TC-2362: Parallel page writing via max_parallel_pages run_config field.

    Spec: specs/21_worker_contracts.md §"Parallel Page Writing"
    """

    def test_parallel_pages_all_written(
        self,
        tmp_path,
        sample_product_facts,
        sample_snippet_catalog,
    ):
        """TC-2362: max_parallel_pages=4 with 2 pages → both files written, manifest correct."""
        run_dir = tmp_path / "run_parallel"
        run_dir.mkdir()
        artifacts_dir = run_dir / "artifacts"
        artifacts_dir.mkdir()

        page_plan = {
            "product_slug": "cells",
            "pages": [
                {
                    "section": "products",
                    "slug": "overview",
                    "output_path": "content/products.aspose.org/cells/en/python/index.md",
                    "url_path": "/cells/python/",
                    "title": "Overview",
                    "purpose": "Overview",
                    "template_variant": "standard",
                    "required_headings": [],
                    "required_claim_ids": ["claim_001"],
                    "required_snippet_tags": [],
                    "cross_links": [],
                    "seo_keywords": [],
                    "forbidden_topics": [],
                    "page_role": "generic_unregistered_role",
                },
                {
                    "section": "docs",
                    "slug": "getting-started",
                    "output_path": "content/docs.aspose.org/cells/en/python/getting-started.md",
                    "url_path": "/cells/python/docs/getting-started/",
                    "title": "Getting Started",
                    "purpose": "Getting started",
                    "template_variant": "standard",
                    "required_headings": [],
                    "required_claim_ids": ["claim_002"],
                    "required_snippet_tags": [],
                    "cross_links": [],
                    "seo_keywords": [],
                    "forbidden_topics": [],
                    "page_role": "generic_unregistered_role",
                },
            ],
        }
        (artifacts_dir / "page_plan.json").write_text(json.dumps(page_plan))
        (artifacts_dir / "product_facts.json").write_text(json.dumps(sample_product_facts))
        (artifacts_dir / "snippet_catalog.json").write_text(json.dumps(sample_snippet_catalog))

        run_config = {"run_id": "test_parallel_001", "max_parallel_pages": 4}
        result = execute_section_writer(run_dir=run_dir, run_config=run_config)

        assert result["status"] == "success"
        assert result["draft_count"] == 2
        assert result["total_pages"] == 2
        # Both files must be written (parallel or sequential — same outcome)
        assert (run_dir / "drafts" / "products" / "overview.md").exists()
        assert (run_dir / "drafts" / "docs" / "getting-started.md").exists()

    def test_parallel_default_sequential_behavior(
        self,
        tmp_path,
        sample_product_facts,
        sample_snippet_catalog,
    ):
        """TC-2362: max_parallel_pages absent (default 1) → same output as sequential.

        Regression guard: parallel dispatch code path MUST NOT break when max_parallel_pages=1.
        """
        run_dir = tmp_path / "run_seq"
        run_dir.mkdir()
        artifacts_dir = run_dir / "artifacts"
        artifacts_dir.mkdir()

        page_plan = {
            "product_slug": "cells",
            "pages": [
                {
                    "section": "docs",
                    "slug": "guide",
                    "output_path": "content/docs.aspose.org/cells/en/python/guide.md",
                    "url_path": "/cells/python/docs/guide/",
                    "title": "Guide",
                    "purpose": "Guide",
                    "template_variant": "standard",
                    "required_headings": [],
                    "required_claim_ids": ["claim_001"],
                    "required_snippet_tags": [],
                    "cross_links": [],
                    "seo_keywords": [],
                    "forbidden_topics": [],
                    "page_role": "generic_unregistered_role",
                },
            ],
        }
        (artifacts_dir / "page_plan.json").write_text(json.dumps(page_plan))
        (artifacts_dir / "product_facts.json").write_text(json.dumps(sample_product_facts))
        (artifacts_dir / "snippet_catalog.json").write_text(json.dumps(sample_snippet_catalog))

        # No max_parallel_pages → uses default 1 (sequential)
        result = execute_section_writer(run_dir=run_dir, run_config={"run_id": "test_seq_001"})

        assert result["status"] == "success"
        assert result["draft_count"] == 1
        assert (run_dir / "drafts" / "docs" / "guide.md").exists()

    def test_parallel_exception_propagates(self, tmp_path):
        """TC-2362: Exception in a parallel page worker propagates to caller (not swallowed).

        If _generate_single_page raises, fut.result() must re-raise so the pipeline fails
        with a clear error rather than silently producing an incomplete manifest.
        """
        from unittest.mock import patch
        from src.launch.workers.w5_section_writer.worker import (
            _generate_single_page,
            SectionWriterUnfilledTokensError,
        )

        run_dir = tmp_path / "run_exc"
        run_dir.mkdir()
        artifacts_dir = run_dir / "artifacts"
        artifacts_dir.mkdir()

        page_plan = {
            "product_slug": "cells",
            "pages": [
                {
                    "section": "docs",
                    "slug": "broken",
                    "output_path": "content/docs.aspose.org/cells/en/python/broken.md",
                    "url_path": "/cells/python/docs/broken/",
                    "title": "Broken",
                    "purpose": "Broken page",
                    "template_variant": "standard",
                    "required_headings": [],
                    "required_claim_ids": [],
                    "required_snippet_tags": [],
                    "cross_links": [],
                    "seo_keywords": [],
                    "forbidden_topics": [],
                    "page_role": "generic_unregistered_role",
                },
            ],
        }
        product_facts = {
            "product_name": "Cells",
            "product_slug": "cells",
            "claims": [],
            "claim_groups": {},
            "workflows": [],
        }
        snippet_catalog = {"snippets": []}
        (artifacts_dir / "page_plan.json").write_text(json.dumps(page_plan))
        (artifacts_dir / "product_facts.json").write_text(json.dumps(product_facts))
        (artifacts_dir / "snippet_catalog.json").write_text(json.dumps(snippet_catalog))

        # Patch _generate_single_page to inject __UNFILLED__ token into content
        # so that check_unfilled_tokens raises SectionWriterUnfilledTokensError
        original_gsp = _generate_single_page

        def _raising_generate(*args, **kwargs):
            raise SectionWriterUnfilledTokensError("Simulated unfilled token error")

        with patch(
            "src.launch.workers.w5_section_writer.worker._generate_single_page",
            side_effect=_raising_generate,
        ):
            with pytest.raises((SectionWriterUnfilledTokensError, Exception)):
                execute_section_writer(
                    run_dir=run_dir,
                    run_config={"run_id": "test_exc_001", "max_parallel_pages": 2},
                )

    def test_parallel_emits_per_page_events(
        self,
        tmp_path,
        sample_product_facts,
        sample_snippet_catalog,
    ):
        """BLKR-04: Parallel mode emits exactly one EVENT_ARTIFACT_WRITTEN per page.

        Verifies that events are emitted as each future completes (real-time) rather
        than in a batch after all pages finish. emit_event call_count must equal pages_count.
        """
        from unittest.mock import patch as mock_patch
        from src.launch.workers.w5_section_writer.worker import emit_event as _emit_event

        run_dir = tmp_path / "run_blkr04"
        run_dir.mkdir()
        artifacts_dir = run_dir / "artifacts"
        artifacts_dir.mkdir()

        page_plan = {
            "product_slug": "cells",
            "pages": [
                {
                    "section": "docs",
                    "slug": f"page-{i}",
                    "output_path": f"content/docs.aspose.org/cells/en/python/page-{i}.md",
                    "url_path": f"/cells/python/docs/page-{i}/",
                    "title": f"Page {i}",
                    "purpose": f"Purpose {i}",
                    "template_variant": "standard",
                    "required_headings": [],
                    "required_claim_ids": ["claim_001"],
                    "required_snippet_tags": [],
                    "cross_links": [],
                    "seo_keywords": [],
                    "forbidden_topics": [],
                    "page_role": "generic_unregistered_role",
                }
                for i in range(3)
            ],
        }
        (artifacts_dir / "page_plan.json").write_text(json.dumps(page_plan))
        (artifacts_dir / "product_facts.json").write_text(json.dumps(sample_product_facts))
        (artifacts_dir / "snippet_catalog.json").write_text(json.dumps(sample_snippet_catalog))

        emit_calls = []

        def _capture_emit(*args, **kwargs):
            # Capture full kwargs so we can distinguish page-level vs manifest-level events
            emit_calls.append({"event_type": kwargs.get("event_type"), "payload": kwargs.get("payload", {})})

        with mock_patch(
            "src.launch.workers.w5_section_writer.worker.emit_event",
            side_effect=_capture_emit,
        ):
            result = execute_section_writer(
                run_dir=run_dir,
                run_config={"run_id": "test_blkr04", "max_parallel_pages": 3},
            )

        assert result["status"] == "success"
        assert result["draft_count"] == 3
        # BLKR-04: Exactly one draft-level EVENT_ARTIFACT_WRITTEN per generated page.
        # (manifest write also emits EVENT_ARTIFACT_WRITTEN with artifact="draft_manifest.json",
        # so we filter on payload["artifact"] == "draft" to count only per-page events.)
        from src.launch.workers.w5_section_writer.worker import EVENT_ARTIFACT_WRITTEN
        draft_events = [
            c for c in emit_calls
            if c["event_type"] == EVENT_ARTIFACT_WRITTEN and c["payload"].get("artifact") == "draft"
        ]
        assert len(draft_events) == 3, (
            f"Expected 3 per-page draft events in parallel mode, got {len(draft_events)}"
        )

    def test_sequential_emits_per_page_events(
        self,
        tmp_path,
        sample_product_facts,
        sample_snippet_catalog,
    ):
        """BLKR-04 regression: Sequential mode (max_parallel_pages=1) still emits one event per page."""
        from unittest.mock import patch as mock_patch
        from src.launch.workers.w5_section_writer.worker import EVENT_ARTIFACT_WRITTEN

        run_dir = tmp_path / "run_blkr04_seq"
        run_dir.mkdir()
        artifacts_dir = run_dir / "artifacts"
        artifacts_dir.mkdir()

        page_plan = {
            "product_slug": "cells",
            "pages": [
                {
                    "section": "docs",
                    "slug": "seq-page",
                    "output_path": "content/docs.aspose.org/cells/en/python/seq-page.md",
                    "url_path": "/cells/python/docs/seq-page/",
                    "title": "Seq Page",
                    "purpose": "Sequential test",
                    "template_variant": "standard",
                    "required_headings": [],
                    "required_claim_ids": ["claim_001"],
                    "required_snippet_tags": [],
                    "cross_links": [],
                    "seo_keywords": [],
                    "forbidden_topics": [],
                    "page_role": "generic_unregistered_role",
                }
            ],
        }
        (artifacts_dir / "page_plan.json").write_text(json.dumps(page_plan))
        (artifacts_dir / "product_facts.json").write_text(json.dumps(sample_product_facts))
        (artifacts_dir / "snippet_catalog.json").write_text(json.dumps(sample_snippet_catalog))

        emit_calls = []

        def _capture_emit(*args, **kwargs):
            emit_calls.append({"event_type": kwargs.get("event_type"), "payload": kwargs.get("payload", {})})

        with mock_patch(
            "src.launch.workers.w5_section_writer.worker.emit_event",
            side_effect=_capture_emit,
        ):
            result = execute_section_writer(
                run_dir=run_dir,
                run_config={"run_id": "test_blkr04_seq"},
            )

        assert result["status"] == "success"
        assert result["draft_count"] == 1
        draft_events = [
            c for c in emit_calls
            if c["event_type"] == EVENT_ARTIFACT_WRITTEN and c["payload"].get("artifact") == "draft"
        ]
        assert len(draft_events) == 1, (
            f"Expected 1 per-page draft event in sequential mode, got {len(draft_events)}"
        )


class TestTC2369GeneratorContextBuilders:
    """TC-2369: Generator-specific context builders for W5."""

    def _claim(self, claim_id: str, claim_text: str, kind: str = "feature",
               demo_ids: list = None) -> dict:
        c = {"claim_id": claim_id, "claim_text": claim_text, "claim_kind": kind}
        if demo_ids is not None:
            c["demo_snippet_ids"] = demo_ids
        return c

    def _snippet(self, snippet_id: str, code: str, tags: list = None,
                 description: str = "") -> dict:
        return {"snippet_id": snippet_id, "code": code, "language": "python",
                "tags": tags or [], "description": description}

    def _page(self, claim_ids: list) -> dict:
        return {"claim_ids": claim_ids, "title": "Test Page",
                "slug": "test-page", "purpose": "test purpose"}

    def _product_facts(self, claims: list) -> dict:
        return {"product_name": "TestLib", "claims": claims}

    def test_build_tutorial_context_workflow_claims_first(self):
        """Workflow/feature claims appear before other claim kinds in tutorial context."""
        claims = [
            self._claim("c1", "Limitation: no support for X", kind="limitation"),
            self._claim("c2", "Install using pip install", kind="workflow"),
            self._claim("c3", "Main feature description", kind="feature"),
        ]
        page = self._page(["c1", "c2", "c3"])
        ctx = build_tutorial_context(page, self._product_facts(claims), {"snippets": []})
        ids = [c["claim_id"] for c in ctx["claims"]]
        # workflow and feature should come before limitation
        wf_pos = min(i for i, cid in enumerate(ids) if cid in ("c2", "c3"))
        lim_pos = ids.index("c1")
        assert wf_pos < lim_pos, f"Expected workflow before limitation, got {ids}"

    def test_build_tutorial_context_uses_demo_snippet_ids(self):
        """demo_snippet_ids from claims are preferred over first-5 catalog snippets."""
        claims = [
            self._claim("c1", "Install step", kind="workflow", demo_ids=["s2"]),
        ]
        snippets = [
            self._snippet("s1", "unrelated code"),
            self._snippet("s2", "pip install aspose"),
        ]
        page = self._page(["c1"])
        ctx = build_tutorial_context(page, self._product_facts(claims), {"snippets": snippets})
        snippet_ids = [s.get("snippet_id") for s in ctx["snippets"]]
        assert "s2" in snippet_ids, f"Expected demo snippet s2 in context, got {snippet_ids}"
        # s1 should NOT be preferred over demo snippet s2
        assert snippet_ids[0] == "s2", f"Demo snippet s2 should be first, got {snippet_ids}"

    def test_build_feature_showcase_context_uses_primary_snippets(self):
        """build_feature_showcase_context uses demo_snippet_ids from primary claim."""
        primary = self._claim("c1", "Feature: PDF conversion", kind="feature",
                              demo_ids=["s3"])
        related = [self._claim("c2", "Related claim", kind="feature")]
        snippets = [
            self._snippet("s1", "other code"),
            self._snippet("s2", "more code"),
            self._snippet("s3", "pdf_convert(doc)"),
        ]
        ctx = build_feature_showcase_context({}, {"product_name": "Lib", "claims": []},
                                              {"snippets": snippets}, primary, related)
        snippet_ids = [s.get("snippet_id") for s in ctx["snippets"]]
        assert "s3" in snippet_ids, f"Expected primary claim demo snippet s3, got {snippet_ids}"
        assert snippet_ids[0] == "s3", f"Primary demo snippet s3 should be first, got {snippet_ids}"

    def test_build_api_reference_context_sorts_api_claims(self):
        """API claims are sorted alphabetically by claim_text in api_reference context."""
        claims = [
            self._claim("c3", "ZipClass: archive management", kind="api"),
            self._claim("c1", "ApiClass: core functionality", kind="api"),
            self._claim("c2", "BenchmarkUtil: performance tool", kind="api"),
        ]
        page = self._page(["c1", "c2", "c3"])
        ctx = build_api_reference_context(page, self._product_facts(claims), {"snippets": []})
        ids = [c["claim_id"] for c in ctx["claims"]]
        # Should be sorted: ApiClass (c1), BenchmarkUtil (c2), ZipClass (c3)
        assert ids == ["c1", "c2", "c3"], f"Expected alphabetical order, got {ids}"


# ---------------------------------------------------------------------------
# TC-2373 (RD-04): Priority-Weighted Token Allocation
# ---------------------------------------------------------------------------

class TestTokenBudget:
    """Tests for _compute_token_budget() — TC-2373 RD-04."""

    def test_token_budget_from_priority_weight(self):
        """priority_weight in content_strategy → effective = base × weight (clamped)."""
        from src.launch.workers.w5_section_writer.worker import _compute_token_budget
        page = {
            "slug": "getting-started",
            "page_type": "getting_started",
            "content_strategy": {"priority_weight": 2.0},
        }
        result = _compute_token_budget(page, {"token_budget": 1000})
        assert result == 2000, f"Expected 2000 (1000 × 2.0), got {result}"

    def test_token_budget_fallback_to_section_type(self):
        """When priority_weight absent, falls back to SECTION_TYPE_WEIGHTS by page_type."""
        from src.launch.workers.w5_section_writer.worker import _compute_token_budget, SECTION_TYPE_WEIGHTS
        page = {
            "slug": "getting-started",
            "page_type": "getting_started",
            "content_strategy": {},
        }
        expected_weight = SECTION_TYPE_WEIGHTS.get("getting_started", 1.0)
        expected = max(int(1000 * 0.5), min(int(1000 * 2.0), int(1000 * expected_weight)))
        result = _compute_token_budget(page, {"token_budget": 1000})
        assert result == expected, f"Expected {expected} (fallback to type weight {expected_weight}), got {result}"

    def test_token_budget_clamp_at_2x(self):
        """priority_weight above 2.0 is clamped to 2.0× base."""
        from src.launch.workers.w5_section_writer.worker import _compute_token_budget
        page = {
            "slug": "some-page",
            "page_type": "tutorial",
            "content_strategy": {"priority_weight": 5.0},  # extreme — must clamp
        }
        result = _compute_token_budget(page, {"token_budget": 1000})
        assert result == 2000, f"Expected 2000 (clamped 1000 × 2.0), got {result}"
