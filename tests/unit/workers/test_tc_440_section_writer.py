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
                "output_path": "content/docs.aspose.org/cells/en/python/overview.md",
                "url_path": "/cells/python/overview/",
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
                "output_path": "content/docs.aspose.org/cells/en/python/docs/getting-started.md",
                "url_path": "/cells/python/docs/getting-started/",
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
        "template_variant": "standard"
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

    # Verify temperature=0.0 for determinism
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
        "template_variant": "minimal"
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

    # Verify claim markers are included
    assert "<!-- claim_id: claim_001 -->" in content
    assert "<!-- claim_id: claim_002 -->" in content

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

    # Verify draft content has claim markers
    overview_content = (drafts_dir / "products" / "overview.md").read_text()
    assert "<!-- claim_id:" in overview_content


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
            "output_path": "content/docs.aspose.org/cells/en/python/kb/faq.md",
            "url_path": "/cells/python/kb/faq/",
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
            "output_path": "content/docs.aspose.org/cells/en/python/reference/api-overview.md",
            "url_path": "/cells/python/reference/api-overview/",
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
    sample_page_plan,
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

    # Write input artifacts
    artifacts_dir = temp_run_dir / "artifacts"
    (artifacts_dir / "page_plan.json").write_text(json.dumps(sample_page_plan))
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
    """Test error handling when LLM call fails."""
    # Create mock LLM that raises exception
    failing_llm_client = Mock()
    failing_llm_client.chat_completion = Mock(side_effect=Exception("API timeout"))

    # Write input artifacts
    artifacts_dir = temp_run_dir / "artifacts"
    (artifacts_dir / "page_plan.json").write_text(json.dumps(sample_page_plan))
    (artifacts_dir / "product_facts.json").write_text(json.dumps(sample_product_facts))
    (artifacts_dir / "snippet_catalog.json").write_text(json.dumps(sample_snippet_catalog))

    run_config = {"run_id": "test_run_005"}

    # Execute should raise error
    with pytest.raises(SectionWriterLLMError, match="LLM call failed"):
        execute_section_writer(
            run_dir=temp_run_dir,
            run_config=run_config,
            llm_client=failing_llm_client
        )


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

    # Verify claim marker format: <!-- claim_id: <ID> -->
    import re
    marker_pattern = r'<!-- claim_id: (claim_\d+) -->'
    markers = re.findall(marker_pattern, overview_content)

    # Should have at least one claim marker
    assert len(markers) > 0

    # Verify marker IDs are valid
    for marker_id in markers:
        assert marker_id.startswith("claim_")
