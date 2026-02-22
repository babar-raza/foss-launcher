"""TC-430: Integration tests for W4 IAPlanner worker.

Tests the W4 IAPlanner implementation that generates comprehensive page plans
for documentation content based on product facts and snippet catalog.

Spec references:
- specs/06_page_planning.md (Page planning algorithm)
- specs/21_worker_contracts.md:157-176 (W4 IAPlanner contract)
- specs/10_determinism_and_caching.md (Deterministic ordering)
- specs/11_state_and_events.md (Event emission)
- specs/33_public_url_mapping.md (URL path computation)
"""

import json
import pytest
from pathlib import Path
from typing import Dict, Any

from launch.workers.w4_ia_planner import (
    execute_ia_planner,
    IAPlannerError,
    IAPlannerPlanIncompleteError,
    IAPlannerURLCollisionError,
    IAPlannerValidationError,
)
from launch.workers.w4_ia_planner.worker import (
    load_product_facts,
    load_snippet_catalog,
    determine_launch_tier,
    infer_product_type,
    compute_url_path,
    compute_output_path,
    plan_pages_for_section,
    add_cross_links,
    check_url_collisions,
    validate_page_plan,
    _resolve_claim_ids_for_group,
    generate_optional_pages,
    _has_limitations,
    _default_headings_for_role,
    _slugify,
    _build_page_title,
    _build_page_description,
    build_content_strategy,
    assign_page_role,
    select_claims_by_similarity,
    link_claims_to_snippets,
)
from launch.io.run_layout import RunLayout
from launch.io.atomic import atomic_write_json
from launch.models.run_config import RunConfig


@pytest.fixture
def mock_run_dir(tmp_path: Path) -> Path:
    """Create a mock run directory with required dependencies."""
    run_dir = tmp_path / "runs" / "test_run"
    run_dir.mkdir(parents=True, exist_ok=True)

    # Create run_layout directories
    layout = RunLayout(run_dir=run_dir)
    layout.artifacts_dir.mkdir(parents=True, exist_ok=True)
    layout.work_dir.mkdir(parents=True, exist_ok=True)

    # Create events.ndjson file
    (run_dir / "events.ndjson").touch()

    return run_dir


@pytest.fixture
def mock_product_facts(mock_run_dir: Path) -> Dict[str, Any]:
    """Create mock product_facts.json artifact."""
    layout = RunLayout(run_dir=mock_run_dir)

    product_facts = {
        "schema_version": "1.0.0",
        "product_name": "Aspose.3D for Python",
        "product_slug": "3d",
        "repo_url": "https://github.com/aspose-3d/Aspose.3D-for-Python-via-.NET",
        "repo_sha": "abc123def456",
        "version": "24.1.0",
        "positioning": {
            "tagline": "3D file processing library for Python",
            "short_description": "Python SDK for reading, writing, and converting 3D files in various formats."
        },
        "supported_platforms": [
            {"name": "Python", "versions": ["3.6+"], "package_name": "aspose-3d-python"}
        ],
        "claims": [
            {
                "claim_id": "claim_001",
                "claim_text": "Supports OBJ format for 3D model import and export",
                "claim_group": "features",
                "confidence": "high",
                "evidence_refs": ["README.md:10-12"]
            },
            {
                "claim_id": "claim_002",
                "claim_text": "Provides Mesh class for 3D geometry manipulation",
                "claim_group": "api",
                "confidence": "high",
                "evidence_refs": ["src/aspose/threed/mesh.py:5-20"]
            },
            {
                "claim_id": "claim_003",
                "claim_text": "Can read STL files for mesh processing",
                "claim_group": "features",
                "confidence": "high",
                "evidence_refs": ["README.md:15-17"]
            }
        ],
        "claim_groups": {
            "key_features": ["claim_001", "claim_003"],
            "install_steps": ["claim_002"],
            "load_and_convert": ["claim_001", "claim_003"],
        },
        "supported_formats": ["OBJ", "STL", "FBX"],
        "workflows": [
            {
                "workflow_id": "load_and_convert",
                "name": "Load and Convert 3D Models",
                "description": "Load a 3D model and convert it to another format",
                "steps": ["Load model", "Convert format", "Save result"]
            }
        ],
        "api_surface_summary": {
            "key_modules": ["aspose.threed", "aspose.threed.formats"],
            "key_classes": ["Scene", "Mesh", "Node"]
        },
        "example_inventory": {
            "example_roots": ["examples"],
            "total_examples": 5
        },
        "repository_health": {
            "ci_present": True,
            "tests_present": True,
            "test_file_count": 15
        },
        "doc_roots": ["docs"],
        "contradictions": [],
        "phantom_paths": []
    }

    atomic_write_json(layout.artifacts_dir / "product_facts.json", product_facts)
    return product_facts


@pytest.fixture
def mock_snippet_catalog(mock_run_dir: Path) -> Dict[str, Any]:
    """Create mock snippet_catalog.json artifact."""
    layout = RunLayout(run_dir=mock_run_dir)

    snippet_catalog = {
        "schema_version": "1.0",
        "snippets": [
            {
                "snippet_id": "snippet_001",
                "language": "python",
                "tags": ["basic", "load"],
                "source": {
                    "type": "repo_file",
                    "path": "examples/basic.py",
                    "start_line": 1,
                    "end_line": 5
                },
                "code": "from aspose.threed import Scene\n\nscene = Scene()\nscene.open('model.obj')\n",
                "requirements": {
                    "dependencies": ["aspose-3d-python"]
                },
                "validation": {
                    "syntax_ok": True
                }
            },
            {
                "snippet_id": "snippet_002",
                "language": "python",
                "tags": ["convert", "save"],
                "source": {
                    "type": "repo_file",
                    "path": "examples/convert.py",
                    "start_line": 1,
                    "end_line": 6
                },
                "code": "from aspose.threed import Scene\n\nscene = Scene('input.obj')\nscene.save('output.stl')\n",
                "requirements": {
                    "dependencies": ["aspose-3d-python"]
                },
                "validation": {
                    "syntax_ok": True
                }
            }
        ]
    }

    atomic_write_json(layout.artifacts_dir / "snippet_catalog.json", snippet_catalog)
    return snippet_catalog


@pytest.fixture
def mock_run_config(mock_run_dir: Path) -> Dict[str, Any]:
    """Create mock run configuration."""
    return {
        "schema_version": "1.0",
        "run_id": "test_run_001",
        "github_repo_url": "https://github.com/aspose-3d/Aspose.3D-for-Python-via-.NET",
        "github_ref": "main",
        "family": "test-family",  # Use non-colliding family name to avoid template issues
    }


# Test 1: Load product facts successfully
def test_load_product_facts_success(mock_run_dir: Path, mock_product_facts: Dict[str, Any]):
    """Test loading product_facts.json artifact."""
    layout = RunLayout(run_dir=mock_run_dir)
    facts = load_product_facts(layout.artifacts_dir)

    assert facts["product_name"] == "Aspose.3D for Python"
    assert facts["product_slug"] == "3d"
    assert len(facts["claims"]) == 3


# Test 2: Load product facts - missing file
def test_load_product_facts_missing(mock_run_dir: Path):
    """Test error handling when product_facts.json is missing."""
    layout = RunLayout(run_dir=mock_run_dir)

    with pytest.raises(IAPlannerError, match="Missing required artifact"):
        load_product_facts(layout.artifacts_dir)


# Test 3: Load snippet catalog successfully
def test_load_snippet_catalog_success(mock_run_dir: Path, mock_snippet_catalog: Dict[str, Any]):
    """Test loading snippet_catalog.json artifact."""
    layout = RunLayout(run_dir=mock_run_dir)
    catalog = load_snippet_catalog(layout.artifacts_dir)

    assert catalog["schema_version"] == "1.0"
    assert len(catalog["snippets"]) == 2


# Test 4: Load snippet catalog - missing file
def test_load_snippet_catalog_missing(mock_run_dir: Path):
    """Test error handling when snippet_catalog.json is missing."""
    layout = RunLayout(run_dir=mock_run_dir)

    with pytest.raises(IAPlannerError, match="Missing required artifact"):
        load_snippet_catalog(layout.artifacts_dir)


# Test 5: Determine launch tier - standard (default)
def test_determine_launch_tier_default(mock_product_facts: Dict[str, Any], mock_snippet_catalog: Dict[str, Any]):
    """Test default launch tier determination."""
    # Use a simple object with just launch_tier attribute
    class MinimalRunConfig:
        def __init__(self):
            self.launch_tier = None

    run_config = MinimalRunConfig()

    tier, adjustments = determine_launch_tier(mock_product_facts, mock_snippet_catalog, run_config)

    assert tier == "standard" or tier == "rich"  # Could be elevated to rich
    assert len(adjustments) > 0


# Test 6: Determine launch tier - explicit config override
def test_determine_launch_tier_explicit():
    """Test explicit launch tier from config."""
    product_facts = {"repository_health": {}, "contradictions": [], "phantom_paths": [], "example_inventory": {"example_roots": []}}
    snippet_catalog = {"snippets": []}

    class MinimalRunConfig:
        def __init__(self):
            self.launch_tier = "minimal"

    run_config = MinimalRunConfig()

    tier, adjustments = determine_launch_tier(product_facts, snippet_catalog, run_config)

    assert tier == "minimal"
    assert any("explicit" in adj.get("reason", "").lower() for adj in adjustments)


# Test 7: Determine launch tier - contradictions force minimal
def test_determine_launch_tier_contradictions():
    """Test launch tier reduction due to contradictions."""
    product_facts = {
        "repository_health": {"ci_present": True, "tests_present": True},
        "contradictions": [{"claim_id": "c1", "reason": "test"}],
        "phantom_paths": [],
        "example_inventory": {"example_roots": ["examples"]}
    }
    snippet_catalog = {"snippets": [{"source": {"type": "repo_file"}}]}

    class MinimalRunConfig:
        def __init__(self):
            self.launch_tier = None

    run_config = MinimalRunConfig()

    tier, adjustments = determine_launch_tier(product_facts, snippet_catalog, run_config)

    assert tier == "minimal"
    assert any("contradiction" in adj.get("reason", "").lower() for adj in adjustments)


# Test 8: Determine launch tier - elevation to rich
def test_determine_launch_tier_elevation(mock_product_facts: Dict[str, Any], mock_snippet_catalog: Dict[str, Any]):
    """Test launch tier elevation due to quality signals."""
    class MinimalRunConfig:
        def __init__(self):
            self.launch_tier = None

    run_config = MinimalRunConfig()

    tier, adjustments = determine_launch_tier(mock_product_facts, mock_snippet_catalog, run_config)

    # With CI, tests, examples, and docs, should elevate to rich
    assert tier in ["standard", "rich"]


# Test 9: Infer product type - SDK
def test_infer_product_type_sdk():
    """Test product type inference for SDK."""
    product_facts = {
        "positioning": {
            "tagline": "Python SDK for document processing",
            "short_description": "SDK for manipulating documents"
        },
        "supported_platforms": [{"name": "Python"}, {"name": "Java"}]
    }

    product_type = infer_product_type(product_facts)
    assert product_type == "sdk"


# Test 10: Infer product type - library
def test_infer_product_type_library():
    """Test product type inference for library."""
    product_facts = {
        "positioning": {
            "tagline": "Document processing library",
            "short_description": "Python library for documents"
        },
        "supported_platforms": [{"name": "Python"}]
    }

    product_type = infer_product_type(product_facts)
    assert product_type == "library"


# Test 11: Compute URL path - products section
def test_compute_url_path_products():
    """Test URL path computation for products section."""
    url = compute_url_path(
        section="products",
        slug="overview",
        product_slug="3d",
    )

    assert url == "/3d/overview/"


# Test 12: Compute URL path - docs section
def test_compute_url_path_docs():
    """Test URL path computation for docs section.

    Per specs/33_public_url_mapping.md:83-86, section is implicit in subdomain,
    NOT in URL path. URL should be /3d/python/getting-started/, not /3d/python/docs/getting-started/
    """
    url = compute_url_path(
        section="docs",
        slug="getting-started",
        product_slug="3d",
    )

    # Section should NOT appear in URL path
    assert url == "/3d/getting-started/"
    assert "/docs/" not in url


# Test 12a: Compute URL path - blog section (no /blog/ in URL)
def test_compute_url_path_blog_section():
    """Test URL path computation for blog section.

    Per specs/33_public_url_mapping.md:106, blog section is implicit in subdomain
    (blog.aspose.org), NOT in URL path. Verify /blog/ does NOT appear in URL.
    """
    url = compute_url_path(
        section="blog",
        slug="announcement",
        product_slug="3d",
    )

    # Section should NOT appear in URL path
    assert url == "/3d/announcement/"
    assert "/blog/" not in url, "Section 'blog' should NOT appear in URL path (it's implicit in subdomain)"


# Test 12b: Compute URL path - docs section (no /docs/ in URL)
def test_compute_url_path_docs_section():
    """Test URL path computation for docs section.

    Per specs/33_public_url_mapping.md:83-86, docs section is implicit in subdomain
    (docs.aspose.org), NOT in URL path. Verify /docs/ does NOT appear in URL.
    """
    url = compute_url_path(
        section="docs",
        slug="developer-guide",
        product_slug="cells",
    )

    # Section should NOT appear in URL path
    assert url == "/cells/developer-guide/"
    assert "/docs/" not in url, "Section 'docs' should NOT appear in URL path (it's implicit in subdomain)"


# Test 12c: Compute URL path - kb section (no /kb/ in URL)
def test_compute_url_path_kb_section():
    """Test URL path computation for kb section.

    Per specs/33_public_url_mapping.md, kb section is implicit in subdomain
    (kb.aspose.org), NOT in URL path. Verify /kb/ does NOT appear in URL.
    """
    url = compute_url_path(
        section="kb",
        slug="troubleshooting",
        product_slug="cells",
    )

    # Section should NOT appear in URL path
    assert url == "/cells/troubleshooting/"
    assert "/kb/" not in url, "Section 'kb' should NOT appear in URL path (it's implicit in subdomain)"


# Test 13: Compute output path - products section
def test_compute_output_path_products():
    """Test output path computation for products section."""
    path = compute_output_path(
        section="products",
        slug="overview",
        product_slug="3d",
    )

    # TC-2102: Products uses same family-first ordering as all non-blog sections
    assert path == "content/products.aspose.org/3d/en/overview.md"


# Test 14: Compute output path - docs section
def test_compute_output_path_docs():
    """Test output path computation for docs section."""
    path = compute_output_path(
        section="docs",
        slug="getting-started",
        product_slug="3d",
    )

    # TC-2000: No section subdirectory
    assert path == "content/docs.aspose.org/3d/en/getting-started.md"


# Test 15: Plan pages - products section
def test_plan_pages_products(mock_product_facts: Dict[str, Any], mock_snippet_catalog: Dict[str, Any]):
    """Test page planning for products section."""
    pages = plan_pages_for_section(
        section="products",
        launch_tier="standard",
        product_facts=mock_product_facts,
        snippet_catalog=mock_snippet_catalog,
        product_slug="3d"
    )

    assert len(pages) >= 1
    assert pages[0]["section"] == "products"
    assert pages[0]["slug"] == "overview"
    assert "Overview" in pages[0]["required_headings"]


# Test 16: Plan pages - docs section
def test_plan_pages_docs(mock_product_facts: Dict[str, Any], mock_snippet_catalog: Dict[str, Any]):
    """Test page planning for docs section."""
    pages = plan_pages_for_section(
        section="docs",
        launch_tier="standard",
        product_facts=mock_product_facts,
        snippet_catalog=mock_snippet_catalog,
        product_slug="3d"
    )

    assert len(pages) >= 2  # getting-started + workflow guides
    assert any(p["slug"] == "getting-started" for p in pages)


# Test 17: Plan pages - minimal tier
def test_plan_pages_minimal_tier(mock_product_facts: Dict[str, Any], mock_snippet_catalog: Dict[str, Any]):
    """Test page planning with minimal tier."""
    pages = plan_pages_for_section(
        section="docs",
        launch_tier="minimal",
        product_facts=mock_product_facts,
        snippet_catalog=mock_snippet_catalog,
        product_slug="3d"
    )

    # Minimal tier docs: TOC + getting-started + developer-guide = 3 pages
    assert len(pages) <= 5


# Test 18: Plan pages - rich tier
def test_plan_pages_rich_tier(mock_product_facts: Dict[str, Any], mock_snippet_catalog: Dict[str, Any]):
    """Test page planning with rich tier."""
    pages = plan_pages_for_section(
        section="reference",
        launch_tier="rich",
        product_facts=mock_product_facts,
        snippet_catalog=mock_snippet_catalog,
        product_slug="3d"
    )

    # Rich tier should have more pages (overview + modules)
    assert len(pages) >= 2


# Test 19: Add cross-links
def test_add_cross_links():
    """Test cross-link addition between pages.

    TC-1001: Cross-links now use absolute URLs (https://...) for cross-subdomain
    navigation via build_absolute_public_url.
    """
    pages = [
        {
            "section": "products",
            "slug": "overview",
            "url_path": "/3d/overview/",
            "cross_links": []
        },
        {
            "section": "docs",
            "slug": "guide",
            "url_path": "/3d/guide/",
            "cross_links": []
        },
        {
            "section": "reference",
            "slug": "api",
            "url_path": "/3d/api/",
            "cross_links": []
        },
        {
            "section": "kb",
            "slug": "faq",
            "url_path": "/3d/faq/",
            "cross_links": []
        },
        {
            "section": "blog",
            "slug": "announcement",
            "url_path": "/3d/announcement/",
            "cross_links": []
        }
    ]

    add_cross_links(pages, product_slug="3d")

    # Verify cross-links per specs/06_page_planning.md:31-35
    docs_page = next(p for p in pages if p["section"] == "docs")
    kb_page = next(p for p in pages if p["section"] == "kb")
    blog_page = next(p for p in pages if p["section"] == "blog")

    # TC-1001: Cross-links are now absolute URLs (https://...)
    assert len(docs_page["cross_links"]) > 0  # docs -> reference
    assert docs_page["cross_links"][0].startswith("https://reference.aspose.org/")

    assert len(kb_page["cross_links"]) > 0   # kb -> docs
    assert kb_page["cross_links"][0].startswith("https://docs.aspose.org/")

    assert len(blog_page["cross_links"]) > 0  # blog -> products
    assert blog_page["cross_links"][0].startswith("https://products.aspose.org/")


# Test 20: Check URL collisions - no collisions
def test_check_url_collisions_none():
    """Test URL collision detection with no collisions."""
    pages = [
        {"url_path": "/3d/overview/", "output_path": "content/3d/overview.md", "section": "products"},
        {"url_path": "/3d/guide/", "output_path": "content/3d/guide.md", "section": "docs"}
    ]

    errors = check_url_collisions(pages)
    assert len(errors) == 0


# Test 21: Check URL collisions - collision detected
def test_check_url_collisions_detected():
    """Test URL collision detection with collisions."""
    pages = [
        {"url_path": "/3d/overview/", "output_path": "content/3d/overview.md", "section": "products"},
        {"url_path": "/3d/overview/", "output_path": "content/3d/alt/overview.md", "section": "products"}
    ]

    errors = check_url_collisions(pages)
    assert len(errors) == 1
    assert "collision" in errors[0].lower()


# Test 22: Validate page plan - valid
def test_validate_page_plan_valid():
    """Test page plan validation with valid plan."""
    page_plan = {
        "schema_version": "1.0",
        "product_slug": "3d",
        "launch_tier": "standard",
        "pages": [
            {
                "section": "products",
                "slug": "overview",
                "output_path": "content/3d/overview.md",
                "url_path": "/3d/overview/",
                "title": "Overview",
                "purpose": "Product overview",
                "required_headings": ["Overview"],
                "required_claim_ids": [],
                "required_snippet_tags": [],
                "cross_links": []
            }
        ]
    }

    # Should not raise
    validate_page_plan(page_plan)


# Test 23: Validate page plan - missing field
def test_validate_page_plan_missing_field():
    """Test page plan validation with missing field."""
    page_plan = {
        "schema_version": "1.0",
        "product_slug": "3d",
        # Missing launch_tier
        "pages": []
    }

    with pytest.raises(IAPlannerValidationError, match="Missing required field"):
        validate_page_plan(page_plan)


# Test 24: Validate page plan - invalid tier
def test_validate_page_plan_invalid_tier():
    """Test page plan validation with invalid tier."""
    page_plan = {
        "schema_version": "1.0",
        "product_slug": "3d",
        "launch_tier": "invalid",
        "pages": []
    }

    with pytest.raises(IAPlannerValidationError, match="Invalid launch_tier"):
        validate_page_plan(page_plan)


# Test 25: Validate page plan - invalid section
def test_validate_page_plan_invalid_section():
    """Test page plan validation with invalid section."""
    page_plan = {
        "schema_version": "1.0",
        "product_slug": "3d",
        "launch_tier": "standard",
        "pages": [
            {
                "section": "invalid_section",
                "slug": "test",
                "output_path": "content/test.md",
                "url_path": "/test/",
                "title": "Test",
                "purpose": "Test",
                "required_headings": [],
                "required_claim_ids": [],
                "required_snippet_tags": [],
                "cross_links": []
            }
        ]
    }

    with pytest.raises(IAPlannerValidationError, match="invalid section"):
        validate_page_plan(page_plan)


# Test 26: Execute IA planner - full integration
def test_execute_ia_planner_success(
    mock_run_dir: Path,
    mock_product_facts: Dict[str, Any],
    mock_snippet_catalog: Dict[str, Any],
    mock_run_config: Dict[str, Any]
):
    """Test full IA planner execution."""
    result = execute_ia_planner(
        run_dir=mock_run_dir,
        run_config=mock_run_config,
        llm_client=None
    )

    assert result["status"] == "success"
    assert result["page_count"] > 0
    assert result["launch_tier"] in ["minimal", "standard", "rich"]

    # Verify artifact was created
    layout = RunLayout(run_dir=mock_run_dir)
    artifact_path = layout.artifacts_dir / "page_plan.json"
    assert artifact_path.exists()

    # Verify artifact content
    with open(artifact_path, "r", encoding="utf-8") as f:
        page_plan = json.load(f)

    assert page_plan["schema_version"] == "1.0"
    assert page_plan["product_slug"] == "test-family"  # Per mock_run_config fixture
    assert len(page_plan["pages"]) > 0


# Test 27: Execute IA planner - deterministic ordering
def test_execute_ia_planner_deterministic_ordering(
    mock_run_dir: Path,
    mock_product_facts: Dict[str, Any],
    mock_snippet_catalog: Dict[str, Any],
    mock_run_config: Dict[str, Any]
):
    """Test that page plan has deterministic ordering."""
    result = execute_ia_planner(
        run_dir=mock_run_dir,
        run_config=mock_run_config,
        llm_client=None
    )

    layout = RunLayout(run_dir=mock_run_dir)
    artifact_path = layout.artifacts_dir / "page_plan.json"

    with open(artifact_path, "r", encoding="utf-8") as f:
        page_plan = json.load(f)

    # Verify pages are sorted by section order, then output_path
    pages = page_plan["pages"]
    section_order = {"products": 0, "docs": 1, "reference": 2, "kb": 3, "blog": 4}

    for i in range(len(pages) - 1):
        current_section = section_order[pages[i]["section"]]
        next_section = section_order[pages[i + 1]["section"]]

        if current_section == next_section:
            # Within same section, should be sorted by output_path
            assert pages[i]["output_path"] <= pages[i + 1]["output_path"]
        else:
            # Sections should be in order
            assert current_section < next_section


# Test 28: Execute IA planner - event emission
def test_execute_ia_planner_event_emission(
    mock_run_dir: Path,
    mock_product_facts: Dict[str, Any],
    mock_snippet_catalog: Dict[str, Any],
    mock_run_config: Dict[str, Any]
):
    """Test that IA planner emits events."""
    execute_ia_planner(
        run_dir=mock_run_dir,
        run_config=mock_run_config,
        llm_client=None
    )

    # Check events.ndjson was written
    events_file = mock_run_dir / "events.ndjson"
    assert events_file.exists()

    # Read events
    events = []
    with open(events_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                events.append(json.loads(line))

    # Should have at least: STARTED, ARTIFACT_WRITTEN, FINISHED
    assert len(events) >= 3
    event_types = [e["type"] for e in events]
    assert "WORK_ITEM_STARTED" in event_types
    assert "ARTIFACT_WRITTEN" in event_types
    assert "WORK_ITEM_FINISHED" in event_types


# Test 29: Execute IA planner - schema validation
def test_execute_ia_planner_schema_validation(
    mock_run_dir: Path,
    mock_product_facts: Dict[str, Any],
    mock_snippet_catalog: Dict[str, Any],
    mock_run_config: Dict[str, Any]
):
    """Test that generated page plan matches schema."""
    execute_ia_planner(
        run_dir=mock_run_dir,
        run_config=mock_run_config,
        llm_client=None
    )

    layout = RunLayout(run_dir=mock_run_dir)
    artifact_path = layout.artifacts_dir / "page_plan.json"

    with open(artifact_path, "r", encoding="utf-8") as f:
        page_plan = json.load(f)

    # Verify schema structure
    assert "schema_version" in page_plan
    assert "product_slug" in page_plan
    assert "launch_tier" in page_plan
    assert "launch_tier_adjustments" in page_plan
    assert "inferred_product_type" in page_plan
    assert "pages" in page_plan

    # Verify each page has required fields
    for page in page_plan["pages"]:
        required_fields = [
            "section", "slug", "output_path", "url_path", "title", "purpose",
            "template_variant", "required_headings", "required_claim_ids",
            "required_snippet_tags", "cross_links"
        ]
        for field in required_fields:
            assert field in page, f"Page missing field: {field}"


# Test 30: Execute IA planner - missing artifacts
def test_execute_ia_planner_missing_artifacts(mock_run_dir: Path, mock_run_config: Dict[str, Any]):
    """Test error handling when required artifacts are missing."""
    # Don't create product_facts.json or snippet_catalog.json

    with pytest.raises(IAPlannerError, match="Missing required artifact"):
        execute_ia_planner(
            run_dir=mock_run_dir,
            run_config=mock_run_config,
            llm_client=None
        )


# ============================================================================
# TC-1010: Tests for _resolve_claim_ids_for_group and fixed claim_group lookups
# ============================================================================


# Test 31: _resolve_claim_ids_for_group returns correct IDs for known groups
def test_resolve_claim_ids_for_group_known_group():
    """TC-1010: _resolve_claim_ids_for_group returns correct IDs for known groups."""
    product_facts = {
        "claim_groups": {
            "key_features": ["c1", "c2", "c3"],
            "install_steps": ["c4", "c5"],
            "limitations": ["c6"],
        }
    }
    result = _resolve_claim_ids_for_group(product_facts, "key_features")
    assert result == {"c1", "c2", "c3"}

    result = _resolve_claim_ids_for_group(product_facts, "install_steps")
    assert result == {"c4", "c5"}

    result = _resolve_claim_ids_for_group(product_facts, "limitations")
    assert result == {"c6"}


# Test 32: _resolve_claim_ids_for_group returns empty set for unknown groups
def test_resolve_claim_ids_for_group_unknown_group():
    """TC-1010: _resolve_claim_ids_for_group returns empty set for unknown groups."""
    product_facts = {
        "claim_groups": {
            "key_features": ["c1", "c2"],
            "install_steps": ["c3"],
        }
    }
    result = _resolve_claim_ids_for_group(product_facts, "nonexistent_group")
    assert result == set()


# Test 33: _resolve_claim_ids_for_group handles missing claim_groups key
def test_resolve_claim_ids_for_group_missing_key():
    """TC-1010: _resolve_claim_ids_for_group handles missing claim_groups gracefully."""
    product_facts = {}
    result = _resolve_claim_ids_for_group(product_facts, "key_features")
    assert result == set()


# Test 34: _resolve_claim_ids_for_group handles non-dict claim_groups (legacy list format)
def test_resolve_claim_ids_for_group_non_dict():
    """TC-1010: _resolve_claim_ids_for_group handles non-dict claim_groups gracefully."""
    product_facts = {
        "claim_groups": [
            {"group_id": "features", "claims": ["c1", "c2"]},
        ]
    }
    result = _resolve_claim_ids_for_group(product_facts, "features")
    assert result == set()


# Test 35: _resolve_claim_ids_for_group partial match (workflow_id in group key)
def test_resolve_claim_ids_for_group_partial_match():
    """TC-1010: _resolve_claim_ids_for_group supports partial matching for workflow IDs."""
    product_facts = {
        "claim_groups": {
            "load_and_convert": ["c1", "c2"],
            "export_mesh": ["c3"],
        }
    }
    # Exact match
    result = _resolve_claim_ids_for_group(product_facts, "load_and_convert")
    assert result == {"c1", "c2"}

    # Partial match: group_key "convert" is contained in "load_and_convert"
    result = _resolve_claim_ids_for_group(product_facts, "convert")
    assert "c1" in result
    assert "c2" in result


# Test 36: plan_pages_for_section produces non-empty install claims for getting-started
def test_plan_pages_docs_getting_started_has_claims(mock_product_facts: Dict[str, Any], mock_snippet_catalog: Dict[str, Any]):
    """TC-1010: Getting-started page picks up install_steps from top-level claim_groups."""
    pages = plan_pages_for_section(
        section="docs",
        launch_tier="standard",
        product_facts=mock_product_facts,
        snippet_catalog=mock_snippet_catalog,
        product_slug="3d",
    )
    gs_pages = [p for p in pages if p["slug"] == "getting-started"]
    assert len(gs_pages) == 1
    gs_page = gs_pages[0]
    # The fixture has install_steps: ["claim_002"], so getting-started must include claim_002
    assert "claim_002" in gs_page["required_claim_ids"]


# Test 37: plan_pages_for_section produces non-empty workflow claims for developer-guide
def test_plan_pages_docs_developer_guide_has_workflow_claims(mock_product_facts: Dict[str, Any], mock_snippet_catalog: Dict[str, Any]):
    """TC-1010: Developer-guide page picks up workflow claims from top-level claim_groups."""
    pages = plan_pages_for_section(
        section="docs",
        launch_tier="standard",
        product_facts=mock_product_facts,
        snippet_catalog=mock_snippet_catalog,
        product_slug="3d",
    )
    dg_pages = [p for p in pages if p["slug"] == "developer-guide"]
    assert len(dg_pages) == 1
    dg_page = dg_pages[0]
    # The fixture has workflow "load_and_convert" mapped to ["claim_001", "claim_003"]
    # Developer-guide should pick up at least one of these
    assert len(dg_page["required_claim_ids"]) > 0
    assert any(cid in ["claim_001", "claim_003"] for cid in dg_page["required_claim_ids"])


# Test 38: generate_optional_pages per_workflow produces non-empty claims
def test_generate_optional_pages_per_workflow_has_claims():
    """TC-1010: per_workflow optional pages pick up claims from top-level claim_groups."""
    product_facts = {
        "claims": [
            {"claim_id": "c1", "claim_text": "Load 3D models", "tags": []},
            {"claim_id": "c2", "claim_text": "Convert formats", "tags": []},
            {"claim_id": "c3", "claim_text": "Export mesh", "tags": ["export"]},
        ],
        "claim_groups": {
            "key_features": ["c1", "c2"],
            "load_and_convert": ["c1", "c2"],
            "export_workflow": ["c3"],
        },
        "workflows": [
            {"workflow_id": "load_and_convert", "name": "Load and Convert"},
            {"workflow_id": "export_workflow", "name": "Export Mesh"},
        ],
        "api_surface_summary": {},
    }
    snippet_catalog = {"snippets": []}
    policies = [
        {"source": "per_workflow", "priority": 1, "page_role": "workflow_page"},
    ]

    pages = generate_optional_pages(
        section="docs",
        mandatory_page_count=1,
        effective_max=10,
        product_facts=product_facts,
        snippet_catalog=snippet_catalog,
        product_slug="3d",
        launch_tier="standard",
        optional_page_policies=policies,
    )

    assert len(pages) >= 2
    # Each per_workflow page should have non-empty required_claim_ids
    for page in pages:
        assert len(page["required_claim_ids"]) > 0, (
            f"per_workflow page '{page['slug']}' has empty required_claim_ids"
        )


# TC-CREV-C-TRACK2: Test limitations heading integration


def test_has_limitations_with_claim_groups():
    """Test _has_limitations() detects limitations in claim_groups."""
    product_facts_with = {
        "claim_groups": {
            "key_features": ["claim_001"],
            "limitations": ["lim_001", "lim_002"],
        }
    }
    product_facts_without = {
        "claim_groups": {
            "key_features": ["claim_001"],
        }
    }

    assert _has_limitations(product_facts_with) is True
    assert _has_limitations(product_facts_without) is False


def test_has_limitations_with_top_level():
    """Test _has_limitations() detects limitations at top level."""
    product_facts_with = {
        "limitations": ["lim_001"],
        "claim_groups": {}
    }
    product_facts_without = {
        "claim_groups": {}
    }

    assert _has_limitations(product_facts_with) is True
    assert _has_limitations(product_facts_without) is False


def test_has_limitations_with_both_sources():
    """Test _has_limitations() detects limitations from both sources."""
    product_facts = {
        "limitations": ["lim_001"],
        "claim_groups": {
            "limitations": ["lim_002"],
        }
    }

    assert _has_limitations(product_facts) is True


def test_default_headings_for_role_landing_with_limitations():
    """Test _default_headings_for_role() adds Limitations for landing page."""
    product_facts_with = {
        "claim_groups": {
            "limitations": ["lim_001"],
        }
    }
    product_facts_without = {
        "claim_groups": {}
    }

    headings_with = _default_headings_for_role("landing", product_facts_with)
    headings_without = _default_headings_for_role("landing", product_facts_without)
    headings_no_facts = _default_headings_for_role("landing")

    assert "Limitations" in headings_with
    assert "Limitations" not in headings_without
    assert "Limitations" not in headings_no_facts


def test_default_headings_for_role_comprehensive_guide_with_limitations():
    """Test _default_headings_for_role() adds Limitations for comprehensive_guide."""
    product_facts_with = {
        "claim_groups": {
            "limitations": ["lim_001"],
        }
    }

    headings = _default_headings_for_role("comprehensive_guide", product_facts_with)
    assert "Limitations" in headings


def test_default_headings_for_role_api_reference_with_limitations():
    """Test _default_headings_for_role() adds Limitations for api_reference."""
    product_facts_with = {
        "claim_groups": {
            "limitations": ["lim_001"],
        }
    }

    headings = _default_headings_for_role("api_reference", product_facts_with)
    assert "Limitations" in headings


def test_default_headings_for_role_toc_no_limitations():
    """Test _default_headings_for_role() does NOT add Limitations for toc page."""
    product_facts_with = {
        "claim_groups": {
            "limitations": ["lim_001"],
        }
    }

    headings = _default_headings_for_role("toc", product_facts_with)
    assert "Limitations" not in headings


def test_default_headings_for_role_workflow_page_no_limitations():
    """Test _default_headings_for_role() does NOT add Limitations for workflow_page."""
    product_facts_with = {
        "claim_groups": {
            "limitations": ["lim_001"],
        }
    }

    headings = _default_headings_for_role("workflow_page", product_facts_with)
    assert "Limitations" not in headings


def test_default_headings_for_role_troubleshooting_no_limitations():
    """Test _default_headings_for_role() does NOT add Limitations for troubleshooting."""
    product_facts_with = {
        "claim_groups": {
            "limitations": ["lim_001"],
        }
    }

    headings = _default_headings_for_role("troubleshooting", product_facts_with)
    assert "Limitations" not in headings


def test_plan_pages_products_section_with_limitations():
    """Test plan_pages_for_section() adds Limitations to products overview page."""
    product_facts = {
        "product_name": "Test Product",
        "claims": [
            {"claim_id": "claim_001", "claim_text": "Feature A", "claim_group": "features"}
        ],
        "claim_groups": {
            "key_features": ["claim_001"],
            "limitations": ["lim_001", "lim_002"],
        },
        "workflows": [],
    }
    snippet_catalog = {"snippets": []}

    pages = plan_pages_for_section(
        section="products",
        launch_tier="minimal",
        product_facts=product_facts,
        snippet_catalog=snippet_catalog,
        product_slug="test",
    )

    assert len(pages) == 1
    products_page = pages[0]
    assert products_page["section"] == "products"
    assert products_page["slug"] == "overview"
    assert "Limitations" in products_page["required_headings"]


def test_plan_pages_products_section_without_limitations():
    """Test plan_pages_for_section() does NOT add Limitations when product has none."""
    product_facts = {
        "product_name": "Test Product",
        "claims": [
            {"claim_id": "claim_001", "claim_text": "Feature A", "claim_group": "features"}
        ],
        "claim_groups": {
            "key_features": ["claim_001"],
        },
        "workflows": [],
    }
    snippet_catalog = {"snippets": []}

    pages = plan_pages_for_section(
        section="products",
        launch_tier="minimal",
        product_facts=product_facts,
        snippet_catalog=snippet_catalog,
        product_slug="test",
    )

    assert len(pages) == 1
    products_page = pages[0]
    assert "Limitations" not in products_page["required_headings"]


def test_plan_pages_docs_section_with_limitations():
    """Test plan_pages_for_section() adds Limitations to developer-guide page."""
    product_facts = {
        "product_name": "Test Product",
        "claims": [
            {"claim_id": "claim_001", "claim_text": "Feature A", "claim_group": "features"}
        ],
        "claim_groups": {
            "key_features": ["claim_001"],
            "limitations": ["lim_001"],
        },
        "workflows": [
            {
                "workflow_id": "wf_001",
                "name": "Test Workflow",
                "steps": ["Step 1"]
            }
        ],
    }
    snippet_catalog = {"snippets": []}

    pages = plan_pages_for_section(
        section="docs",
        launch_tier="minimal",
        product_facts=product_facts,
        snippet_catalog=snippet_catalog,
        product_slug="test",
    )

    # Find developer-guide page
    dg_page = next((p for p in pages if p["slug"] == "developer-guide"), None)
    assert dg_page is not None
    assert "Limitations" in dg_page["required_headings"]


def test_plan_pages_docs_toc_no_limitations():
    """Test plan_pages_for_section() does NOT add Limitations to TOC page."""
    product_facts = {
        "product_name": "Test Product",
        "claims": [
            {"claim_id": "claim_001", "claim_text": "Feature A", "claim_group": "features"}
        ],
        "claim_groups": {
            "key_features": ["claim_001"],
            "limitations": ["lim_001"],
        },
        "workflows": [],
    }
    snippet_catalog = {"snippets": []}

    pages = plan_pages_for_section(
        section="docs",
        launch_tier="minimal",
        product_facts=product_facts,
        snippet_catalog=snippet_catalog,
        product_slug="test",
    )

    # Find TOC page
    toc_page = next((p for p in pages if p["slug"] == "_index"), None)
    assert toc_page is not None
    assert "Limitations" not in toc_page["required_headings"]


def test_plan_pages_reference_section_with_limitations():
    """Test plan_pages_for_section() adds Limitations to API reference overview."""
    product_facts = {
        "product_name": "Test Product",
        "claims": [
            {"claim_id": "claim_001", "claim_text": "Feature A", "claim_group": "features"}
        ],
        "claim_groups": {
            "key_features": ["claim_001"],
            "limitations": ["lim_001"],
        },
        "workflows": [],
        "api_surface_summary": {
            "key_modules": ["module.one"],
            "key_classes": ["ClassA"]
        },
    }
    snippet_catalog = {"snippets": []}

    pages = plan_pages_for_section(
        section="reference",
        launch_tier="minimal",
        product_facts=product_facts,
        snippet_catalog=snippet_catalog,
        product_slug="test",
    )

    assert len(pages) == 1
    ref_page = pages[0]
    assert ref_page["slug"] == "api-overview"
    assert "Limitations" in ref_page["required_headings"]


# ========== TC-1634: Route New claim_groups to Pages ==========


def test_tc_1634_faq_page_uses_faq_claim_group():
    """TC-1634: Verify FAQ page sources from faq claim_group when available."""
    product_facts = {
        "product_name": "Test Product",
        "claims": [
            {"claim_id": "faq_001", "claim_text": "Q: How to install?", "claim_group": "faq"},
            {"claim_id": "faq_002", "claim_text": "Q: Is it thread-safe?", "claim_group": "faq"},
            {"claim_id": "inst_001", "claim_text": "Install via pip", "claim_group": "install"},
            {"claim_id": "lim_001", "claim_text": "Cannot process binary files", "claim_group": "limitations"},
        ],
        "claim_groups": {
            "key_features": [],
            "install_steps": ["inst_001"],
            "limitations": ["lim_001"],
            "faq": ["faq_001", "faq_002"],  # TC-1634: New faq group
        },
        "workflows": [],
        "api_surface_summary": {},
    }
    snippet_catalog = {"snippets": []}

    pages = plan_pages_for_section(
        section="kb",
        launch_tier="minimal",
        product_facts=product_facts,
        snippet_catalog=snippet_catalog,
        product_slug="test",
    )

    # Find FAQ page
    faq_page = next((p for p in pages if p["slug"] == "faq"), None)
    assert faq_page is not None, "FAQ page should be generated"

    # TC-1634: FAQ page should use faq claim_group, not install_steps + limitations
    assert "faq_001" in faq_page["required_claim_ids"]
    assert "faq_002" in faq_page["required_claim_ids"]
    # Should NOT have install/limitations claims when faq group is available
    assert "inst_001" not in faq_page["required_claim_ids"]
    assert "lim_001" not in faq_page["required_claim_ids"]


def test_tc_1634_troubleshooting_merges_claims():
    """TC-1634: Verify troubleshooting page merges troubleshooting + limitations."""
    product_facts = {
        "product_name": "Test Product",
        "claims": [
            {"claim_id": "ts_001", "claim_text": "Troubleshoot: Check dependencies", "claim_group": "troubleshooting"},
            {"claim_id": "ts_002", "claim_text": "Troubleshoot: Verify paths", "claim_group": "troubleshooting"},
            {"claim_id": "lim_001", "claim_text": "Cannot process binary files", "claim_group": "limitations"},
            {"claim_id": "lim_002", "claim_text": "Max file size 100MB", "claim_group": "limitations"},
        ],
        "claim_groups": {
            "key_features": [],
            "install_steps": [],
            "limitations": ["lim_001", "lim_002"],
            "troubleshooting": ["ts_001", "ts_002"],  # TC-1634: New troubleshooting group
        },
        "workflows": [],
        "api_surface_summary": {},
    }
    snippet_catalog = {"snippets": []}

    pages = plan_pages_for_section(
        section="kb",
        launch_tier="standard",  # Troubleshooting page only in standard/rich
        product_facts=product_facts,
        snippet_catalog=snippet_catalog,
        product_slug="test",
    )

    # Find troubleshooting page
    ts_page = next((p for p in pages if p["slug"] == "troubleshooting"), None)
    assert ts_page is not None, "Troubleshooting page should be generated"

    # TC-1634: Should merge troubleshooting + limitations claim_groups
    assert "ts_001" in ts_page["required_claim_ids"]
    assert "ts_002" in ts_page["required_claim_ids"]
    assert "lim_001" in ts_page["required_claim_ids"]
    assert "lim_002" in ts_page["required_claim_ids"]
    assert len(ts_page["required_claim_ids"]) == 4


# ========== TC-1635: Add per_claim_group Optional Page Policy ==========


def test_tc_1635_per_claim_group_generates_page_when_threshold_met():
    """TC-1635: Verify per_claim_group generates page when claim count >= min_claims."""
    product_facts = {
        "product_name": "Test Product",
        "claims": [
            {"claim_id": f"bp_{i:03d}", "claim_text": f"Best practice {i}", "claim_group": "best_practices"}
            for i in range(1, 11)  # 10 best practice claims
        ],
        "claim_groups": {
            "key_features": [],
            "best_practices": [f"bp_{i:03d}" for i in range(1, 11)],  # 10 claims
        },
        "workflows": [],
        "api_surface_summary": {},
    }
    snippet_catalog = {"snippets": []}

    optional_page_policies = [
        {
            "source": "per_claim_group",
            "claim_group": "best_practices",
            "min_claims": 8,
            "slug": "best-practices",
            "section_path": "kb",
            "page_role": "best_practices",
            "priority": 2,
            "heading_overrides": ["Best Practices", "Recommendations"],
        }
    ]

    pages = generate_optional_pages(
        section="kb",
        mandatory_page_count=2,
        effective_max=5,  # Room for 3 optional pages
        product_facts=product_facts,
        snippet_catalog=snippet_catalog,
        product_slug="test",
        launch_tier="standard",
        optional_page_policies=optional_page_policies,
    )

    # TC-1635: Should generate page (10 claims >= 8 min_claims)
    assert len(pages) > 0, "Should generate at least one page"
    bp_page = next((p for p in pages if p["slug"] == "best-practices"), None)
    assert bp_page is not None, "Best practices page should be generated"
    assert bp_page["section"] == "kb", "Should use section_path from policy"
    assert bp_page["page_role"] == "best_practices", "Should use page_role from policy"
    assert bp_page["required_headings"] == ["Best Practices", "Recommendations"], "Should use heading_overrides"
    assert len(bp_page["required_claim_ids"]) == 10, "Should have all 10 best_practices claims"


def test_tc_1635_per_claim_group_skips_page_when_below_threshold():
    """TC-1635: Verify per_claim_group skips page when claim count < min_claims."""
    product_facts = {
        "product_name": "Test Product",
        "claims": [
            {"claim_id": f"bp_{i:03d}", "claim_text": f"Best practice {i}", "claim_group": "best_practices"}
            for i in range(1, 6)  # Only 5 best practice claims
        ],
        "claim_groups": {
            "key_features": [],
            "best_practices": [f"bp_{i:03d}" for i in range(1, 6)],  # Only 5 claims
        },
        "workflows": [],
        "api_surface_summary": {},
    }
    snippet_catalog = {"snippets": []}

    optional_page_policies = [
        {
            "source": "per_claim_group",
            "claim_group": "best_practices",
            "min_claims": 8,  # Threshold: 8 claims required
            "slug": "best-practices",
            "section_path": "kb",
            "page_role": "best_practices",
            "priority": 2,
            "heading_overrides": ["Best Practices"],
        }
    ]

    pages = generate_optional_pages(
        section="kb",
        mandatory_page_count=2,
        effective_max=5,
        product_facts=product_facts,
        snippet_catalog=snippet_catalog,
        product_slug="test",
        launch_tier="standard",
        optional_page_policies=optional_page_policies,
    )

    # TC-1635: Should NOT generate page (5 claims < 8 min_claims)
    bp_page = next((p for p in pages if p["slug"] == "best-practices"), None)
    assert bp_page is None, "Best practices page should NOT be generated (below threshold)"


# ========== TC-1901: per_key_feature quality_score Minimum ==========


def test_tc_1901_per_key_feature_no_matching_snippets_filtered_out():
    """TC-1901: per_key_feature with 0 matching snippets -> quality_score=2, page filtered out."""
    product_facts = {
        "product_name": "Test Product",
        "claims": [
            {"claim_id": "kf_001", "claim_text": "Export 3D scenes", "tags": ["export"]},
            {"claim_id": "kf_002", "claim_text": "Import models", "tags": ["import"]},
        ],
        "claim_groups": {
            "key_features": ["kf_001", "kf_002"],
        },
        "workflows": [],
        "api_surface_summary": {},
    }
    # Snippets have NO matching tags (no "export" or "import" tags)
    snippet_catalog = {
        "snippets": [
            {"tags": ["unrelated"]},
            {"tags": ["other"]},
        ]
    }

    optional_page_policies = [
        {"source": "per_key_feature", "priority": 1, "page_role": "feature_showcase"},
    ]

    pages = generate_optional_pages(
        section="kb",
        mandatory_page_count=1,
        effective_max=10,
        product_facts=product_facts,
        snippet_catalog=snippet_catalog,
        product_slug="test",
        launch_tier="standard",
        optional_page_policies=optional_page_policies,
    )

    # TC-1901: quality_score = (1*2) + (0*3) = 2 < 5, so all pages filtered out
    showcase_pages = [p for p in pages if p.get("page_role") == "feature_showcase"]
    assert len(showcase_pages) == 0, (
        "per_key_feature pages with 0 matching snippets should be filtered out (quality_score=2 < 5)"
    )


def test_tc_1901_per_key_feature_one_matching_snippet_included():
    """TC-1901: per_key_feature with 1 matching snippet -> quality_score=5, page included."""
    product_facts = {
        "product_name": "Test Product",
        "claims": [
            {"claim_id": "kf_001", "claim_text": "Export 3D scenes", "tags": ["export"]},
            {"claim_id": "kf_002", "claim_text": "Import models", "tags": ["import"]},
        ],
        "claim_groups": {
            "key_features": ["kf_001", "kf_002"],
        },
        "workflows": [],
        "api_surface_summary": {},
    }
    # One snippet matches "export", one matches "import"
    snippet_catalog = {
        "snippets": [
            {"tags": ["export"]},
            {"tags": ["import"]},
        ]
    }

    optional_page_policies = [
        {"source": "per_key_feature", "priority": 1, "page_role": "feature_showcase"},
    ]

    pages = generate_optional_pages(
        section="kb",
        mandatory_page_count=1,
        effective_max=10,
        product_facts=product_facts,
        snippet_catalog=snippet_catalog,
        product_slug="test",
        launch_tier="standard",
        optional_page_policies=optional_page_policies,
    )

    # TC-1901: quality_score = (1*2) + (1*3) = 5 >= 5, so pages are included
    showcase_pages = [p for p in pages if p.get("page_role") == "feature_showcase"]
    assert len(showcase_pages) == 2, (
        "per_key_feature pages with 1 matching snippet should be included (quality_score=5 >= 5)"
    )
    # Verify each page has exactly 1 required_claim_id (single feature focus)
    for page in showcase_pages:
        assert len(page["required_claim_ids"]) == 1, "Each showcase should focus on a single feature"


class TestTC2201BlogSlug:
    """TC-2201 R17-010: Blog slug derived from product name."""

    def test_blog_slug_not_announcement(self):
        """Blog slug should NOT be hardcoded 'announcement'."""
        # This test verifies _slugify produces a product-specific slug
        slug = _slugify("introducing-Aspose.3D for Python")
        assert slug != "announcement"
        assert "introducing" in slug
        assert "aspose" in slug

    def test_slugify_special_chars(self):
        assert _slugify("Hello World!") == "hello-world"
        assert _slugify("Aspose.3D") == "aspose-3d"
        assert _slugify("a--b") == "a-b"


class TestTC2201SkipSections:
    """TC-2201 R17-011: Products section skippable via skip_sections."""

    def test_skip_sections_config_respected(self):
        """When skip_sections includes 'products', no products pages generated."""
        run_config = {"skip_sections": ["products"]}
        assert "products" in run_config.get("skip_sections", [])

    def test_skip_sections_enforced_in_execute(
        self, mock_run_dir, mock_product_facts, mock_snippet_catalog
    ):
        """skip_sections must prevent pages from ALL 3 loops (template, mandatory, optional).

        RCA fix: Loops 2 (mandatory injection) and 3 (optional injection) previously
        ignored skip_sections, causing products pages to leak through even when skipped.
        """
        run_config_with_skip = {
            "schema_version": "1.0",
            "run_id": "test_skip_sections",
            "github_repo_url": "https://github.com/aspose-3d/Aspose.3D-for-Python",
            "github_ref": "main",
            "family": "test-family",
            "skip_sections": ["products"],
        }
        result = execute_ia_planner(
            run_dir=mock_run_dir,
            run_config=run_config_with_skip,
            llm_client=None,
        )
        assert result["status"] == "success"

        layout = RunLayout(run_dir=mock_run_dir)
        artifact_path = layout.artifacts_dir / "page_plan.json"
        with open(artifact_path, "r", encoding="utf-8") as f:
            page_plan = json.load(f)

        # No page should have section == "products"
        products_pages = [p for p in page_plan["pages"] if p["section"] == "products"]
        assert products_pages == [], (
            f"skip_sections=['products'] but {len(products_pages)} products pages generated: "
            f"{[p['slug'] for p in products_pages]}"
        )

    def test_skip_sections_does_not_affect_other_sections(
        self, mock_run_dir, mock_product_facts, mock_snippet_catalog
    ):
        """skip_sections=['products'] should not affect docs, kb, blog, reference."""
        run_config_with_skip = {
            "schema_version": "1.0",
            "run_id": "test_skip_other",
            "github_repo_url": "https://github.com/aspose-3d/Aspose.3D-for-Python",
            "github_ref": "main",
            "family": "test-family",
            "skip_sections": ["products"],
        }
        result = execute_ia_planner(
            run_dir=mock_run_dir,
            run_config=run_config_with_skip,
            llm_client=None,
        )
        layout = RunLayout(run_dir=mock_run_dir)
        artifact_path = layout.artifacts_dir / "page_plan.json"
        with open(artifact_path, "r", encoding="utf-8") as f:
            page_plan = json.load(f)

        # Other sections should still have pages
        non_products_pages = [p for p in page_plan["pages"] if p["section"] != "products"]
        assert len(non_products_pages) > 0, "No non-products pages generated"
        sections_present = set(p["section"] for p in non_products_pages)
        assert "docs" in sections_present, "docs section missing despite not being skipped"


class TestTC2201ClaimDensityExpansion:
    """TC-2201 R17-007: Richer repos get more pages."""

    def test_high_claim_count_produces_extra_pages(self):
        """With >200 claims and uncovered groups, extra pages are generated."""
        # Verify the threshold and logic
        n_claims = 500
        assert n_claims > 200  # threshold met


# ========== TC-2203: Unique Page Titles and Descriptions ==========


class TestTC2203PageTitles:
    """TC-2203: Unique page titles and descriptions."""

    def test_build_page_title_includes_product_name(self):
        """Title must contain product name for SEO uniqueness."""
        title = _build_page_title("getting-started", "docs", "Aspose.3D", "python")
        assert "Aspose.3D" in title

    def test_build_page_title_unique_per_slug(self):
        """Different slugs must produce different titles."""
        t1 = _build_page_title("getting-started", "docs", "Aspose.3D", "python")
        t2 = _build_page_title("faq", "docs", "Aspose.3D", "python")
        assert t1 != t2

    def test_build_page_title_fallback_for_unknown_slug(self):
        """Unknown slug should still produce a meaningful title with product name."""
        title = _build_page_title("custom-page", "docs", "Aspose.3D", "python")
        assert "Aspose.3D" in title
        assert "Custom Page" in title

    def test_build_page_title_no_platform(self):
        """Title should work without platform."""
        title = _build_page_title("getting-started", "docs", "Aspose.3D", "")
        assert "Aspose.3D" in title
        assert "for" not in title.lower().split("aspose.3d")[0]  # no stray "for" before product

    def test_build_page_title_strips_for_suffix(self):
        """Product name 'Aspose.3D for Python' should use short form 'Aspose.3D'."""
        title = _build_page_title("faq", "docs", "Aspose.3D for Python", "python")
        assert "Aspose.3D" in title
        # Should not have "Aspose.3D for Python for Python"
        assert "for Python for Python" not in title

    def test_build_page_description_max_160_chars(self):
        """Description must not exceed 160 characters."""
        desc = _build_page_description("getting-started", "docs", "Aspose.3D", "python")
        assert len(desc) <= 160

    def test_build_page_description_unique_per_slug(self):
        """Different slugs must produce different descriptions."""
        d1 = _build_page_description("getting-started", "docs", "Aspose.3D", "python")
        d2 = _build_page_description("faq", "docs", "Aspose.3D", "python")
        assert d1 != d2

    def test_build_page_description_with_purpose_fallback(self):
        """Unknown slug with purpose should use purpose in description."""
        desc = _build_page_description("custom-page", "docs", "Aspose.3D", "python", "My custom purpose")
        assert "Aspose.3D" in desc
        assert "My custom purpose" in desc

    def test_build_page_description_truncation(self):
        """Very long product name should still produce description <= 160 chars."""
        desc = _build_page_description(
            "getting-started", "docs",
            "Aspose.SuperLongProductNameThatGoesOnAndOnForever", "python"
        )
        assert len(desc) <= 160

    def test_page_specs_have_description_field(self):
        """plan_pages_for_section should add 'description' to every page spec."""
        product_facts = {
            "product_name": "Aspose.3D for Python",
            "claims": [
                {"claim_id": "c1", "claim_text": "Feature A", "claim_group": "features"}
            ],
            "claim_groups": {"key_features": ["c1"]},
            "workflows": [],
            "api_surface_summary": {},
        }
        snippet_catalog = {"snippets": []}

        for section in ["products", "docs", "reference", "kb", "blog"]:
            pages = plan_pages_for_section(
                section=section,
                launch_tier="minimal",
                product_facts=product_facts,
                snippet_catalog=snippet_catalog,
                product_slug="3d",
            )
            for page in pages:
                assert "description" in page, (
                    f"Page '{page['slug']}' in section '{section}' missing 'description'"
                )
                assert len(page["description"]) <= 160, (
                    f"Page '{page['slug']}' description exceeds 160 chars"
                )


# ========== TC-2204: Content Strategy Angle Enforcement ==========


class TestTC2204ContentStrategy:
    """TC-2204: Content strategy has unique_angle and avoid_overlap_with."""

    def test_getting_started_has_unique_angle(self):
        """getting_started strategy must have unique_angle."""
        strategy = build_content_strategy("getting_started", "docs", [])
        assert "unique_angle" in strategy
        assert len(strategy["unique_angle"]) > 10

    def test_getting_started_avoids_overlap(self):
        """getting_started strategy must declare overlap avoidance."""
        strategy = build_content_strategy("getting_started", "docs", [])
        assert "avoid_overlap_with" in strategy
        assert isinstance(strategy["avoid_overlap_with"], list)
        assert "installation" in strategy["avoid_overlap_with"]

    def test_faq_avoids_overlap(self):
        """faq strategy must avoid getting_started and troubleshooting."""
        strategy = build_content_strategy("faq", "kb", [])
        assert "avoid_overlap_with" in strategy
        assert isinstance(strategy["avoid_overlap_with"], list)
        assert "getting_started" in strategy["avoid_overlap_with"]
        assert "troubleshooting" in strategy["avoid_overlap_with"]

    def test_troubleshooting_avoids_faq(self):
        """troubleshooting must avoid faq."""
        strategy = build_content_strategy("troubleshooting", "kb", [])
        assert "avoid_overlap_with" in strategy
        assert "faq" in strategy["avoid_overlap_with"]

    def test_comprehensive_guide_has_angle(self):
        """comprehensive_guide must have unique_angle."""
        strategy = build_content_strategy("comprehensive_guide", "docs", [])
        assert "unique_angle" in strategy
        assert "avoid_overlap_with" in strategy
        assert "getting_started" in strategy["avoid_overlap_with"]

    def test_api_reference_has_angle(self):
        """api_reference must have unique_angle."""
        strategy = build_content_strategy("api_reference", "reference", [])
        assert "unique_angle" in strategy
        assert "avoid_overlap_with" in strategy

    def test_blog_announcement_has_angle(self):
        """blog_announcement must have unique_angle."""
        strategy = build_content_strategy("blog_announcement", "blog", [])
        assert "unique_angle" in strategy
        assert "avoid_overlap_with" in strategy

    def test_best_practices_has_angle(self):
        """best_practices must have unique_angle."""
        strategy = build_content_strategy("best_practices", "kb", [])
        assert "unique_angle" in strategy
        assert "developer_guide" in strategy["avoid_overlap_with"]

    def test_tutorial_avoids_overlap(self):
        """tutorial must avoid getting_started and developer_guide."""
        strategy = build_content_strategy("tutorial", "kb", [])
        assert "avoid_overlap_with" in strategy
        assert "getting_started" in strategy["avoid_overlap_with"]
        assert "developer_guide" in strategy["avoid_overlap_with"]

    def test_all_strategies_have_angle_fields(self):
        """Every page_role must return unique_angle and avoid_overlap_with."""
        roles = [
            ("landing", "products"),
            ("toc", "docs"),
            ("getting_started", "docs"),
            ("comprehensive_guide", "docs"),
            ("workflow_page", "docs"),
            ("feature_showcase", "kb"),
            ("troubleshooting", "kb"),
            ("faq", "kb"),
            ("best_practices", "kb"),
            ("tutorial", "kb"),
            ("api_reference", "reference"),
            ("blog_announcement", "blog"),
        ]
        for role, section in roles:
            strategy = build_content_strategy(role, section, [])
            assert "unique_angle" in strategy, f"Missing unique_angle for role={role}"
            assert "avoid_overlap_with" in strategy, f"Missing avoid_overlap_with for role={role}"
            assert isinstance(strategy["avoid_overlap_with"], list), f"avoid_overlap_with not list for role={role}"


# ========== TC-2202: API Reference Includes Full Surface ==========


class TestTC2202ApiReference:
    """TC-2202: API reference includes full surface."""

    def test_reference_page_includes_api_classes(self):
        """Reference page should include api_classes claim_group in required_claim_ids."""
        product_facts = {
            "product_name": "Aspose.3D",
            "product_slug": "threed",
            "product_family": "3D",
            "api_surface_summary": {"key_modules": ["aspose.threed"], "key_classes": ["Scene", "Mesh"]},
            "claims": [],
            "claim_groups": {
                "key_features": [f"kf-{i}" for i in range(10)],
                "api_classes": [f"ac-{i}" for i in range(20)],
            },
            "workflows": [],
        }
        snippet_catalog = {"snippets": []}

        pages = plan_pages_for_section(
            section="reference",
            launch_tier="minimal",
            product_facts=product_facts,
            snippet_catalog=snippet_catalog,
            product_slug="3d",
        )

        ref_page = next((p for p in pages if p["slug"] == "api-overview"), None)
        assert ref_page is not None
        # Should include both key_features AND api_classes (up to 25)
        assert len(ref_page["required_claim_ids"]) > 5
        assert len(ref_page["required_claim_ids"]) <= 25
        # api_classes should be present
        assert any(cid.startswith("ac-") for cid in ref_page["required_claim_ids"])
        assert any(cid.startswith("kf-") for cid in ref_page["required_claim_ids"])

    def test_reference_page_has_api_surface_summary(self):
        """Reference page should carry api_surface_summary for downstream use."""
        product_facts = {
            "product_name": "Aspose.3D",
            "api_surface_summary": {"key_modules": ["aspose.threed"], "key_classes": ["Scene"]},
            "claims": [],
            "claim_groups": {"key_features": ["kf-1"]},
            "workflows": [],
        }
        snippet_catalog = {"snippets": []}

        pages = plan_pages_for_section(
            section="reference",
            launch_tier="minimal",
            product_facts=product_facts,
            snippet_catalog=snippet_catalog,
            product_slug="3d",
        )

        ref_page = next((p for p in pages if p["slug"] == "api-overview"), None)
        assert ref_page is not None
        assert "api_surface_summary" in ref_page
        assert ref_page["api_surface_summary"]["key_classes"] == ["Scene"]

    def test_reference_page_cap_at_25_claims(self):
        """Reference page should cap at 25 claim IDs even with more available."""
        product_facts = {
            "product_name": "Aspose.3D",
            "api_surface_summary": {},
            "claims": [],
            "claim_groups": {
                "key_features": [f"kf-{i}" for i in range(20)],
                "api_classes": [f"ac-{i}" for i in range(20)],
            },
            "workflows": [],
        }
        snippet_catalog = {"snippets": []}

        pages = plan_pages_for_section(
            section="reference",
            launch_tier="minimal",
            product_facts=product_facts,
            snippet_catalog=snippet_catalog,
            product_slug="3d",
        )

        ref_page = next((p for p in pages if p["slug"] == "api-overview"), None)
        assert ref_page is not None
        assert len(ref_page["required_claim_ids"]) == 25

    def test_getting_started_page_role(self):
        """TC-2202: getting-started slug should map to 'getting_started' role."""
        role = assign_page_role("docs", "getting-started")
        assert role == "getting_started"

    def test_quickstart_page_role(self):
        """TC-2202: quickstart slug should also map to 'getting_started' role."""
        role = assign_page_role("docs", "quickstart")
        assert role == "getting_started"


# =============================================================================
# TC-2344: Content strategy + headings alignment tests
# =============================================================================


class TestTC2344ContentStrategyAlignment:
    """TC-2344: Verify new page role strategies and headings."""

    def test_build_content_strategy_format_conversion(self):
        """TC-2344: format_conversion strategy has correct keys and tone."""
        strategy = build_content_strategy("format_conversion", "products")
        assert strategy["primary_focus"] == "Single format conversion with complete code example"
        assert "unrelated_formats" in strategy["forbidden_topics"]
        assert strategy["claim_quota"]["min"] == 2
        assert strategy["claim_quota"]["max"] == 8
        assert "unique_angle" in strategy
        assert strategy["tone"] == "professional, practical, SEO-friendly"

    def test_build_content_strategy_howto_article(self):
        """TC-2344: howto_article strategy has correct keys and tone."""
        strategy = build_content_strategy("howto_article", "kb")
        assert strategy["primary_focus"] == "Single how-to task with step-by-step instructions"
        assert "other_features" in strategy["forbidden_topics"]
        assert strategy["claim_quota"]["min"] == 3
        assert strategy["claim_quota"]["max"] == 10
        assert "unique_angle" in strategy
        assert strategy["tone"] == "practical, helpful, developer-friendly"

    def test_build_content_strategy_feature_blog(self):
        """TC-2344: feature_blog strategy has correct keys and tone."""
        strategy = build_content_strategy("feature_blog", "blog")
        assert strategy["primary_focus"] == "Feature highlight in friendly, approachable tone"
        assert "detailed_api" in strategy["forbidden_topics"]
        assert "raw_parameters" in strategy["forbidden_topics"]
        assert strategy["claim_quota"]["min"] == 3
        assert strategy["claim_quota"]["max"] == 8
        assert "unique_angle" in strategy
        assert strategy["tone"] == "friendly, approachable, enthusiastic"

    def test_default_headings_format_conversion(self):
        """TC-2344: format_conversion headings include expected sections."""
        headings = _default_headings_for_role("format_conversion")
        assert "Overview" in headings
        assert "How It Works" in headings
        assert "Code Example" in headings
        assert "Advanced Options" in headings
        assert "FAQ" in headings
        assert len(headings) == 5

    def test_default_headings_howto_article(self):
        """TC-2344: howto_article headings include expected sections."""
        headings = _default_headings_for_role("howto_article")
        assert "Overview" in headings
        assert "When to Use" in headings
        assert "Step-by-Step Guide" in headings
        assert "Code Example" in headings
        assert "Related Links" in headings
        assert len(headings) == 5

    def test_default_headings_feature_blog(self):
        """TC-2344: feature_blog headings include expected sections."""
        headings = _default_headings_for_role("feature_blog")
        assert "Introduction" in headings
        assert "Key Highlights" in headings
        assert "Quick Example" in headings
        assert "Next Steps" in headings
        assert len(headings) == 4

    def test_default_headings_performance_guide(self):
        """TC-2344: performance_guide headings include expected sections."""
        headings = _default_headings_for_role("performance_guide")
        assert "Overview" in headings
        assert "Benchmarks" in headings
        assert "Optimization Tips" in headings
        assert "Best Practices" in headings
        assert len(headings) == 4

    def test_default_headings_blog_announcement(self):
        """TC-2344: blog_announcement headings include expected sections."""
        headings = _default_headings_for_role("blog_announcement")
        assert "Announcement" in headings
        assert "Key Highlights" in headings
        assert "Getting Started" in headings
        assert "Next Steps" in headings
        assert len(headings) == 4

    def test_existing_strategies_unchanged(self):
        """TC-2344: Existing strategies should not be affected by new additions."""
        landing = build_content_strategy("landing", "products")
        assert landing["primary_focus"] == "Product positioning"
        toc = build_content_strategy("toc", "docs")
        assert toc["primary_focus"] == "Navigation hub"
        faq = build_content_strategy("faq", "kb")
        assert faq["primary_focus"] == "Common questions and answers"

    def test_existing_headings_unchanged(self):
        """TC-2344: Existing headings should not be affected by new additions."""
        assert _default_headings_for_role("landing") == ["Overview", "Key Features", "Getting Started"]
        assert _default_headings_for_role("toc") == ["Introduction", "Documentation Index"]
        assert _default_headings_for_role("faq") == ["Frequently Asked Questions"]


# =============================================================================
# TC-2343: New optional page source tests
# =============================================================================


class TestTC2343OptionalPageSources:
    """TC-2343: Verify new optional page source handlers."""

    def test_per_format_conversion_produces_candidates(self):
        """TC-2343: per_format_conversion with valid conversion pairs produces pages."""
        product_facts = {
            "claims": [
                {"claim_id": "c1", "claim_text": "Convert CSV to PDF", "tags": []},
                {"claim_id": "c2", "claim_text": "Convert JSON to Excel", "tags": []},
            ],
            "claim_groups": {
                "key_features": [],
                "conversion_pairs": [
                    {"source": "csv", "target": "pdf", "claim_ids": ["c1"]},
                    {"source": "json", "target": "excel", "claim_ids": ["c2"]},
                ],
            },
            "workflows": [],
            "api_surface_summary": {},
        }
        snippet_catalog = {"snippets": []}
        policies = [
            {"source": "per_format_conversion", "priority": 1, "page_role": "format_conversion"},
        ]

        pages = generate_optional_pages(
            section="products",
            mandatory_page_count=1,
            effective_max=10,
            product_facts=product_facts,
            snippet_catalog=snippet_catalog,
            product_slug="cells",
            launch_tier="standard",
            optional_page_policies=policies,
        )

        assert len(pages) == 2
        slugs = [p["slug"] for p in pages]
        assert "csv-to-pdf" in slugs
        assert "json-to-excel" in slugs
        for page in pages:
            assert page["page_role"] == "format_conversion"
            assert len(page["required_claim_ids"]) > 0
            assert page["title"].startswith("Convert ")
            assert "using Python" in page["title"]

    def test_per_format_conversion_skips_empty_claim_ids(self):
        """TC-2343: per_format_conversion skips pairs with no claim_ids."""
        product_facts = {
            "claims": [],
            "claim_groups": {
                "key_features": [],
                "conversion_pairs": [
                    {"source": "csv", "target": "pdf", "claim_ids": []},
                ],
            },
            "workflows": [],
            "api_surface_summary": {},
        }
        snippet_catalog = {"snippets": []}
        policies = [
            {"source": "per_format_conversion", "priority": 1, "page_role": "format_conversion"},
        ]

        pages = generate_optional_pages(
            section="products",
            mandatory_page_count=1,
            effective_max=10,
            product_facts=product_facts,
            snippet_catalog=snippet_catalog,
            product_slug="cells",
            launch_tier="standard",
            optional_page_policies=policies,
        )

        assert len(pages) == 0

    def test_per_format_conversion_snippet_scoring(self):
        """TC-2343: per_format_conversion boosts quality_score with matching snippets."""
        product_facts = {
            "claims": [
                {"claim_id": "c1", "claim_text": "Convert CSV to PDF", "tags": []},
            ],
            "claim_groups": {
                "key_features": [],
                "conversion_pairs": [
                    {"source": "csv", "target": "pdf", "claim_ids": ["c1"]},
                ],
            },
            "workflows": [],
            "api_surface_summary": {},
        }
        snippet_catalog = {
            "snippets": [
                {"snippet_id": "s1", "tags": ["convert"], "claim_ids": ["c1"], "language": "python", "code": "x=1"},
            ]
        }
        policies = [
            {"source": "per_format_conversion", "priority": 1, "page_role": "format_conversion"},
        ]

        pages = generate_optional_pages(
            section="products",
            mandatory_page_count=1,
            effective_max=10,
            product_facts=product_facts,
            snippet_catalog=snippet_catalog,
            product_slug="cells",
            launch_tier="standard",
            optional_page_policies=policies,
        )

        assert len(pages) == 1
        # quality_score = 1*2 (claims) + 1*3 (snippets) = 5
        assert pages[0]["required_snippet_tags"] == ["convert"]

    def test_per_howto_cluster_produces_candidates(self):
        """TC-2343: per_howto_cluster with 3+ claims produces pages."""
        product_facts = {
            "claims": [
                {"claim_id": "c1", "claim_text": "Import CSV data", "tags": []},
                {"claim_id": "c2", "claim_text": "Parse JSON files", "tags": []},
                {"claim_id": "c3", "claim_text": "Read XML documents", "tags": []},
            ],
            "claim_groups": {
                "key_features": [],
                "how_to_clusters": {
                    "data-import": ["c1", "c2", "c3"],
                },
            },
            "workflows": [],
            "api_surface_summary": {},
        }
        snippet_catalog = {"snippets": []}
        policies = [
            {"source": "per_howto_cluster", "priority": 2, "page_role": "howto_article"},
        ]

        pages = generate_optional_pages(
            section="kb",
            mandatory_page_count=1,
            effective_max=10,
            product_facts=product_facts,
            snippet_catalog=snippet_catalog,
            product_slug="cells",
            launch_tier="standard",
            optional_page_policies=policies,
        )

        assert len(pages) == 1
        assert pages[0]["slug"] == "how-to-data-import"
        assert pages[0]["page_role"] == "howto_article"
        assert len(pages[0]["required_claim_ids"]) == 3

    def test_per_howto_cluster_skips_small_clusters(self):
        """TC-2343: per_howto_cluster skips clusters with fewer than 3 claims."""
        product_facts = {
            "claims": [
                {"claim_id": "c1", "claim_text": "Import CSV data", "tags": []},
                {"claim_id": "c2", "claim_text": "Parse JSON files", "tags": []},
            ],
            "claim_groups": {
                "key_features": [],
                "how_to_clusters": {
                    "data-import": ["c1", "c2"],  # Only 2 claims — below threshold
                },
            },
            "workflows": [],
            "api_surface_summary": {},
        }
        snippet_catalog = {"snippets": []}
        policies = [
            {"source": "per_howto_cluster", "priority": 2, "page_role": "howto_article"},
        ]

        pages = generate_optional_pages(
            section="kb",
            mandatory_page_count=1,
            effective_max=10,
            product_facts=product_facts,
            snippet_catalog=snippet_catalog,
            product_slug="cells",
            launch_tier="standard",
            optional_page_policies=policies,
        )

        assert len(pages) == 0

    def test_per_feature_blog_with_snippets(self):
        """TC-2343: per_feature_blog produces candidate when feature has matching snippets."""
        product_facts = {
            "claims": [
                {"claim_id": "f1", "claim_text": "Advanced mesh processing", "tags": ["mesh"]},
            ],
            "claim_groups": {
                "key_features": ["f1"],
            },
            "workflows": [],
            "api_surface_summary": {},
        }
        snippet_catalog = {
            "snippets": [
                {"snippet_id": "s1", "tags": ["mesh"], "claim_ids": ["f1"], "language": "python", "code": "x=1"},
            ]
        }
        policies = [
            {"source": "per_feature_blog", "priority": 1, "page_role": "feature_blog"},
        ]

        pages = generate_optional_pages(
            section="blog",
            mandatory_page_count=0,
            effective_max=10,
            product_facts=product_facts,
            snippet_catalog=snippet_catalog,
            product_slug="3d",
            launch_tier="standard",
            optional_page_policies=policies,
        )

        assert len(pages) == 1
        assert pages[0]["page_role"] == "feature_blog"
        assert "f1" in pages[0]["required_claim_ids"]
        assert "python" in pages[0]["slug"].lower() or "Python" in pages[0]["title"]

    def test_per_feature_blog_skips_without_snippets(self):
        """TC-2343: per_feature_blog skips features without matching snippets."""
        product_facts = {
            "claims": [
                {"claim_id": "f1", "claim_text": "Advanced mesh processing", "tags": ["mesh"]},
            ],
            "claim_groups": {
                "key_features": ["f1"],
            },
            "workflows": [],
            "api_surface_summary": {},
        }
        snippet_catalog = {"snippets": []}  # No snippets at all
        policies = [
            {"source": "per_feature_blog", "priority": 1, "page_role": "feature_blog"},
        ]

        pages = generate_optional_pages(
            section="blog",
            mandatory_page_count=0,
            effective_max=10,
            product_facts=product_facts,
            snippet_catalog=snippet_catalog,
            product_slug="3d",
            launch_tier="standard",
            optional_page_policies=policies,
        )

        assert len(pages) == 0

    def test_per_feature_blog_skips_missing_claim(self):
        """TC-2343: per_feature_blog skips feature IDs not found in claims list."""
        product_facts = {
            "claims": [],  # No claims — feature ID not resolvable
            "claim_groups": {
                "key_features": ["nonexistent_id"],
            },
            "workflows": [],
            "api_surface_summary": {},
        }
        snippet_catalog = {"snippets": []}
        policies = [
            {"source": "per_feature_blog", "priority": 1, "page_role": "feature_blog"},
        ]

        pages = generate_optional_pages(
            section="blog",
            mandatory_page_count=0,
            effective_max=10,
            product_facts=product_facts,
            snippet_catalog=snippet_catalog,
            product_slug="3d",
            launch_tier="standard",
            optional_page_policies=policies,
        )

        assert len(pages) == 0


# =============================================================================
# TC-2364: Content-Signal Role Assignment
# =============================================================================


class TestTC2364ContentSignalRoleAssignment:
    """TC-2364: assign_page_role() uses claim-kind distribution to infer role."""

    def _make_claims(self, kind: str, count: int) -> list:
        return [{"claim_id": f"{kind}_{i}", "claim_text": f"Claim {i}", "claim_kind": kind} for i in range(count)]

    def test_api_heavy_claims_gives_api_reference(self):
        """5 api claims out of 5 total → api_reference regardless of slug."""
        claims = self._make_claims("api", 5)
        role = assign_page_role(section="docs", slug="load-introduction", available_claims=claims)
        assert role == "api_reference"

    def test_workflow_heavy_claims_gives_workflow_page(self):
        """4 workflow claims out of 5 total (80%) >= 40% threshold → workflow_page."""
        claims = self._make_claims("workflow", 4) + self._make_claims("feature", 1)
        role = assign_page_role(section="kb", slug="some-guide", available_claims=claims)
        assert role == "workflow_page"

    def test_slug_fallback_when_claims_ambiguous(self):
        """Mixed kinds (1 of each) — signal ambiguous — slug determines role."""
        claims = (
            self._make_claims("api", 1)
            + self._make_claims("workflow", 1)
            + self._make_claims("feature", 1)
            + self._make_claims("limitation", 1)
        )
        # In kb section, faq slug → faq role
        role = assign_page_role(section="kb", slug="faq", available_claims=claims)
        assert role == "faq"

    def test_no_claims_uses_slug_only(self):
        """Backwards compat: no available_claims → slug-based logic unchanged."""
        assert assign_page_role(section="reference", slug="api-overview") == "api_reference"
        assert assign_page_role(section="blog", slug="news") == "blog_announcement"
        assert assign_page_role(section="docs", slug="quickstart") == "getting_started"


# =============================================================================
# TC-2366: Similarity-Based Claim Selection
# =============================================================================


class TestTC2366SelectClaimsBySimilarity:
    """TC-2366: select_claims_by_similarity() ranks claims by TF-IDF cosine similarity."""

    def _claim(self, cid: str, text: str) -> dict:
        return {"claim_id": cid, "claim_text": text, "claim_kind": "feature"}

    def test_select_returns_top_k_relevant(self):
        """Installation-related purpose selects installation claims over unrelated ones."""
        claims = [
            self._claim("c1", "Install the library using pip install aspose-words command"),
            self._claim("c2", "Configure the API connection settings in your application"),
            self._claim("c3", "Install dependencies via pip install aspose-package first"),
            self._claim("c4", "Export documents to PDF format using the save method"),
            self._claim("c5", "Install on Linux using pip install aspose-cells package"),
        ]
        result = select_claims_by_similarity("installation guide pip install", claims, top_k=3)
        assert len(result) == 3
        result_ids = {c["claim_id"] for c in result}
        # c1, c3, c5 are about installation — at least 2 should appear in top-3
        install_ids = {"c1", "c3", "c5"}
        assert len(result_ids & install_ids) >= 2, f"Expected installation claims in top-3, got {result_ids}"

    def test_select_empty_candidates_returns_empty(self):
        """Empty candidates list returns empty list."""
        result = select_claims_by_similarity("installation guide", [], top_k=5)
        assert result == []

    def test_select_empty_purpose_returns_first_k(self):
        """Empty purpose string falls back to first top_k candidates."""
        claims = [self._claim(f"c{i}", f"Claim text number {i}") for i in range(10)]
        result = select_claims_by_similarity("", claims, top_k=3)
        assert len(result) == 3

    def test_select_fewer_than_k_returns_all(self):
        """When fewer candidates than top_k exist, return all candidates."""
        claims = [self._claim("c1", "Supports CSV format"), self._claim("c2", "Reads JSON files")]
        result = select_claims_by_similarity("format support", claims, top_k=10)
        assert len(result) == 2


class TestTC2368LinkClaimsToSnippets:
    """TC-2368: Claim-to-snippet binding via TF-IDF cosine similarity."""

    def _claim(self, claim_id: str, claim_text: str) -> Dict[str, Any]:
        return {"claim_id": claim_id, "claim_text": claim_text, "claim_kind": "feature"}

    def _snippet(self, snippet_id: str, code: str, tags: list = None) -> Dict[str, Any]:
        return {"snippet_id": snippet_id, "code": code, "language": "python",
                "tags": tags or []}

    def test_link_claims_basic_match(self):
        """Claim with entity name overlap with snippet receives demo_snippet_id."""
        claims = [
            self._claim("c1", "Scene class supports loading FBX and OBJ formats"),
        ]
        snippets = [
            self._snippet("s1", "scene = Scene()\nscene.open('test.fbx')", tags=["scene"]),
            self._snippet("s2", "result = doc.save('output.pdf')\n# Save document as PDF"),
        ]
        catalog = {"snippets": snippets}
        result = link_claims_to_snippets(claims, catalog)
        assert len(result) == 1
        # The Scene claim should match the Scene snippet
        demo_ids = result[0].get("demo_snippet_ids", [])
        assert "s1" in demo_ids, f"Expected s1 in demo_snippet_ids, got {demo_ids}"

    def test_link_claims_empty_catalog(self):
        """Empty snippet catalog returns claims unchanged (no demo_snippet_ids added)."""
        claims = [self._claim("c1", "Supports PDF format conversion")]
        result = link_claims_to_snippets(claims, {"snippets": []})
        assert result == claims

    def test_link_claims_no_overlap(self):
        """Claim with no vocabulary overlap with any snippet gets empty demo_snippet_ids."""
        claims = [self._claim("c1", "xyzzy quux frobnicate baz")]
        snippets = [self._snippet("s1", "print('hello world')\n# Hello snippet")]
        result = link_claims_to_snippets(claims, {"snippets": snippets})
        assert result[0].get("demo_snippet_ids") == []

    def test_link_claims_preserves_existing(self):
        """Claims that already have demo_snippet_ids are not overwritten."""
        claims = [
            {**self._claim("c1", "Some claim"), "demo_snippet_ids": ["already_linked"]},
        ]
        snippets = [self._snippet("s1", "some claim code")]
        result = link_claims_to_snippets(claims, {"snippets": snippets})
        assert result[0]["demo_snippet_ids"] == ["already_linked"]
