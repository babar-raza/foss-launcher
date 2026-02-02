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
        "claim_groups": [
            {"group_id": "features", "claims": ["claim_001", "claim_003"]},
            {"group_id": "api", "claims": ["claim_002"]}
        ],
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
        platform="python"
    )

    assert url == "/3d/python/overview/"


# Test 12: Compute URL path - docs section
def test_compute_url_path_docs():
    """Test URL path computation for docs section."""
    url = compute_url_path(
        section="docs",
        slug="getting-started",
        product_slug="3d",
        platform="python"
    )

    assert url == "/3d/python/docs/getting-started/"


# Test 13: Compute output path - products section
def test_compute_output_path_products():
    """Test output path computation for products section."""
    path = compute_output_path(
        section="products",
        slug="overview",
        product_slug="3d",
        platform="python"
    )

    # TC-681: Products section should use products.aspose.org subdomain
    assert path == "content/products.aspose.org/3d/en/python/overview.md"


# Test 14: Compute output path - docs section
def test_compute_output_path_docs():
    """Test output path computation for docs section."""
    path = compute_output_path(
        section="docs",
        slug="getting-started",
        product_slug="3d",
        platform="python"
    )

    assert path == "content/docs.aspose.org/3d/en/python/docs/getting-started.md"


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

    # Minimal tier should have fewer pages
    assert len(pages) <= 2


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
    """Test cross-link addition between pages."""
    pages = [
        {
            "section": "products",
            "url_path": "/3d/python/overview/",
            "cross_links": []
        },
        {
            "section": "docs",
            "url_path": "/3d/python/docs/guide/",
            "cross_links": []
        },
        {
            "section": "reference",
            "url_path": "/3d/python/reference/api/",
            "cross_links": []
        },
        {
            "section": "kb",
            "url_path": "/3d/python/kb/faq/",
            "cross_links": []
        },
        {
            "section": "blog",
            "url_path": "/3d/python/blog/announcement/",
            "cross_links": []
        }
    ]

    add_cross_links(pages)

    # Verify cross-links per specs/06_page_planning.md:31-35
    docs_page = next(p for p in pages if p["section"] == "docs")
    kb_page = next(p for p in pages if p["section"] == "kb")
    blog_page = next(p for p in pages if p["section"] == "blog")

    assert len(docs_page["cross_links"]) > 0  # docs -> reference
    assert len(kb_page["cross_links"]) > 0   # kb -> docs
    assert len(blog_page["cross_links"]) > 0  # blog -> products


# Test 20: Check URL collisions - no collisions
def test_check_url_collisions_none():
    """Test URL collision detection with no collisions."""
    pages = [
        {"url_path": "/3d/python/overview/", "output_path": "content/3d/overview.md"},
        {"url_path": "/3d/python/docs/guide/", "output_path": "content/3d/guide.md"}
    ]

    errors = check_url_collisions(pages)
    assert len(errors) == 0


# Test 21: Check URL collisions - collision detected
def test_check_url_collisions_detected():
    """Test URL collision detection with collisions."""
    pages = [
        {"url_path": "/3d/python/overview/", "output_path": "content/3d/overview.md"},
        {"url_path": "/3d/python/overview/", "output_path": "content/3d/alt/overview.md"}
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
                "url_path": "/3d/python/overview/",
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
    assert page_plan["product_slug"] == "3d"
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
