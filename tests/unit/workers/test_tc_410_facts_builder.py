"""TC-410: Integration tests for W2 FactsBuilder worker.

Tests the complete W2 FactsBuilder pipeline (TC-410) that integrates:
- TC-411: Claims extraction
- TC-412: Evidence mapping
- TC-413: Contradiction detection

Spec references:
- specs/21_worker_contracts.md:98-125 (W2 FactsBuilder contract)
- specs/28_coordination_and_handoffs.md (Worker coordination)
- specs/11_state_and_events.md (Event emission)
"""

import json
import pytest
from pathlib import Path
from typing import Dict, Any

from launch.workers.w2_facts_builder import (
    execute_facts_builder,
    FactsBuilderError,
    FactsBuilderClaimsError,
    FactsBuilderEvidenceError,
    FactsBuilderContradictionError,
    FactsBuilderAssemblyError,
)
from launch.io.run_layout import RunLayout
from launch.io.atomic import atomic_write_json


@pytest.fixture
def mock_run_dir(tmp_path: Path) -> Path:
    """Create a mock run directory with required dependencies."""
    run_dir = tmp_path / "runs" / "test_run"
    run_dir.mkdir(parents=True, exist_ok=True)

    # Create run_layout directories
    layout = RunLayout(run_dir=run_dir)
    layout.artifacts_dir.mkdir(parents=True, exist_ok=True)
    layout.work_dir.mkdir(parents=True, exist_ok=True)

    return run_dir


@pytest.fixture
def mock_repo_dir(tmp_path: Path) -> Path:
    """Create a mock repository directory with sample documentation."""
    repo_dir = tmp_path / "runs" / "test_run" / "work" / "repo"
    repo_dir.mkdir(parents=True, exist_ok=True)

    # Create README with claims
    readme = repo_dir / "README.md"
    readme.write_text("""# Test Product

Test Product supports OBJ format for 3D model import and export.
The library can read STL files for mesh processing.
It provides a Mesh class for 3D geometry manipulation.

## Installation

Install via pip install test-product.

## Usage

The API includes functions for loading and saving 3D models.
""", encoding='utf-8')

    # Create a sample Python file
    src_dir = repo_dir / "src" / "test_product"
    src_dir.mkdir(parents=True, exist_ok=True)
    (src_dir / "__init__.py").write_text("""
class Mesh:
    '''Mesh class for 3D geometry.'''
    def load(self, path):
        '''Load mesh from file.'''
        pass
""", encoding='utf-8')

    # Create examples directory
    examples_dir = repo_dir / "examples"
    examples_dir.mkdir(parents=True, exist_ok=True)
    (examples_dir / "basic.py").write_text("""
from test_product import Mesh

mesh = Mesh()
mesh.load('model.obj')
""", encoding='utf-8')

    return repo_dir


@pytest.fixture
def mock_repo_inventory(mock_run_dir: Path, mock_repo_dir: Path) -> Dict[str, Any]:
    """Create mock repo_inventory.json artifact."""
    layout = RunLayout(run_dir=mock_run_dir)

    inventory = {
        "schema_version": "1.0.0",
        "repo_url": "https://github.com/test/test-product",
        "repo_sha": "abc123def456",
        "product_name": "test-product",
        "supported_platforms": ["Linux", "Windows", "macOS"],
        "fingerprint": {
            "adapter_id": "python",
            "language": "Python",
            "default_branch": "main",
        },
        "file_count": 3,
        "repo_fingerprint": "test_fingerprint_123",
    }

    atomic_write_json(layout.artifacts_dir / "repo_inventory.json", inventory)
    return inventory


@pytest.fixture
def mock_discovered_docs(mock_run_dir: Path, mock_repo_dir: Path) -> Dict[str, Any]:
    """Create mock discovered_docs.json artifact."""
    layout = RunLayout(run_dir=mock_run_dir)

    docs = {
        "schema_version": "1.0.0",
        "doc_roots": ["README.md", "docs/"],
        "doc_entrypoints": ["README.md"],
        "doc_entrypoint_details": [
            {
                "path": "README.md",
                "type": "readme",
                "size_bytes": 500,
            }
        ],
    }

    atomic_write_json(layout.artifacts_dir / "discovered_docs.json", docs)
    return docs


@pytest.fixture
def mock_discovered_examples(mock_run_dir: Path, mock_repo_dir: Path) -> Dict[str, Any]:
    """Create mock discovered_examples.json artifact."""
    layout = RunLayout(run_dir=mock_run_dir)

    examples = {
        "schema_version": "1.0.0",
        "example_roots": ["examples/"],
        "example_paths": ["examples/basic.py"],
        "example_file_details": [
            {
                "path": "examples/basic.py",
                "language": "python",
                "tags": ["basic", "quickstart"],
            }
        ],
    }

    atomic_write_json(layout.artifacts_dir / "discovered_examples.json", examples)
    return examples


@pytest.fixture
def mock_run_config(mock_run_dir: Path) -> Dict[str, Any]:
    """Create mock run_config.yaml."""
    run_config = {
        "schema_version": "1.0",
        "product_slug": "test-product",
        "product_name": "test-product",
        "family": "test",
        "github_repo_url": "https://github.com/test/test-product",
        "github_ref": "main",
        "required_sections": ["overview", "features"],
        "site_layout": {"content_dir": "content", "output_dir": "public"},
        "allowed_paths": ["content/", "data/"],
        "llm": {"provider": "test", "model": "test-model"},
        "mcp": {"enabled": False},
        "telemetry": {"enabled": False},
        "commit_service": {"mode": "test"},
        "templates_version": "1.0",
        "ruleset_version": "1.0",
        "allow_inference": False,
        "max_fix_attempts": 3,
        "budgets": {"max_tokens": 10000},
    }

    return run_config


# ========== Integration Tests ==========


def test_facts_builder_happy_path(
    mock_run_dir: Path,
    mock_repo_dir: Path,
    mock_repo_inventory: Dict[str, Any],
    mock_discovered_docs: Dict[str, Any],
    mock_discovered_examples: Dict[str, Any],
    mock_run_config: Dict[str, Any],
):
    """Test full FactsBuilder pipeline (happy path).

    Verifies:
    - All sub-workers execute successfully
    - All artifacts are produced
    - Event sequence is correct
    - product_facts.json is valid
    """
    layout = RunLayout(run_dir=mock_run_dir)

    # Execute FactsBuilder
    result = execute_facts_builder(
        run_dir=mock_run_dir,
        run_config=mock_run_config,
        run_id="test_run_001",
        trace_id="trace_001",
        span_id="span_001",
        llm_client=None,  # Use heuristic extraction
    )

    # Verify result structure
    assert result["status"] == "success"
    assert result["error"] is None
    assert "artifacts" in result
    assert "metadata" in result

    # Verify all artifacts produced
    assert "extracted_claims" in result["artifacts"]
    assert "evidence_map" in result["artifacts"]
    assert "product_facts" in result["artifacts"]

    # Verify artifact files exist
    assert (layout.artifacts_dir / "extracted_claims.json").exists()
    assert (layout.artifacts_dir / "evidence_map.json").exists()
    assert (layout.artifacts_dir / "product_facts.json").exists()

    # Verify metadata
    assert result["metadata"]["total_claims"] >= 0
    assert result["metadata"]["fact_claims"] >= 0
    assert result["metadata"]["inference_claims"] >= 0

    # Verify product_facts.json structure
    with open(layout.artifacts_dir / "product_facts.json", 'r', encoding='utf-8') as f:
        product_facts = json.load(f)

    assert product_facts["schema_version"] == "1.0.0"
    assert product_facts["product_name"] == "test-product"
    assert "product_slug" in product_facts
    assert "claims" in product_facts
    assert "claim_groups" in product_facts
    assert "supported_formats" in product_facts
    assert "workflows" in product_facts
    assert "api_surface_summary" in product_facts
    assert "example_inventory" in product_facts

    # Verify events.ndjson was written
    events_file = mock_run_dir / "events.ndjson"
    assert events_file.exists()

    # Parse events
    events = []
    with open(events_file, 'r', encoding='utf-8') as f:
        for line in f:
            events.append(json.loads(line))

    # Verify event sequence
    event_types = [e["type"] for e in events]
    assert "WORK_ITEM_STARTED" in event_types
    assert "WORK_ITEM_FINISHED" in event_types
    assert "ARTIFACT_WRITTEN" in event_types
    assert "FACTS_BUILDER_STARTED" in event_types
    assert "FACTS_BUILDER_COMPLETED" in event_types

    # Verify ARTIFACT_WRITTEN events for all artifacts
    artifact_events = [e for e in events if e["type"] == "ARTIFACT_WRITTEN"]
    artifact_names = [e["payload"]["name"] for e in artifact_events]
    assert "extracted_claims.json" in artifact_names
    assert "evidence_map.json" in artifact_names
    assert "product_facts.json" in artifact_names


def test_facts_builder_zero_claims(
    mock_run_dir: Path,
    mock_repo_dir: Path,
    mock_repo_inventory: Dict[str, Any],
    mock_run_config: Dict[str, Any],
):
    """Test FactsBuilder handles zero claims gracefully.

    Per specs/21_worker_contracts.md:119:
    If no claims can be extracted, emit FACTS_BUILDER_ZERO_CLAIMS and proceed
    with empty ProductFacts.
    """
    layout = RunLayout(run_dir=mock_run_dir)

    # Create empty discovered_docs (no documentation)
    docs = {
        "schema_version": "1.0.0",
        "doc_roots": [],
        "doc_entrypoints": [],
        "doc_entrypoint_details": [],
    }
    atomic_write_json(layout.artifacts_dir / "discovered_docs.json", docs)

    # Create empty discovered_examples
    examples = {
        "schema_version": "1.0.0",
        "example_roots": [],
        "example_paths": [],
        "example_file_details": [],
    }
    atomic_write_json(layout.artifacts_dir / "discovered_examples.json", examples)

    # Execute FactsBuilder
    result = execute_facts_builder(
        run_dir=mock_run_dir,
        run_config=mock_run_config,
        run_id="test_run_zero_claims",
        trace_id="trace_002",
        span_id="span_002",
        llm_client=None,
    )

    # Verify result
    assert result["status"] == "success"
    assert result["metadata"]["total_claims"] == 0

    # Verify FACTS_BUILDER_ZERO_CLAIMS event was emitted
    events_file = mock_run_dir / "events.ndjson"
    events = []
    with open(events_file, 'r', encoding='utf-8') as f:
        for line in f:
            events.append(json.loads(line))

    event_types = [e["type"] for e in events]
    assert "FACTS_BUILDER_ZERO_CLAIMS" in event_types


def test_facts_builder_sparse_claims(
    mock_run_dir: Path,
    mock_repo_dir: Path,
    mock_repo_inventory: Dict[str, Any],
    mock_run_config: Dict[str, Any],
):
    """Test FactsBuilder handles sparse claims (< 5).

    Per specs/21_worker_contracts.md:123:
    If fewer than 5 claims are extracted, emit FACTS_BUILDER_SPARSE_CLAIMS.
    """
    layout = RunLayout(run_dir=mock_run_dir)

    # Create minimal docs with only 2-3 claims
    minimal_readme = mock_repo_dir / "README.md"
    minimal_readme.write_text("""# Minimal Product

This product supports OBJ format.
Install via pip install minimal-product.
""", encoding='utf-8')

    docs = {
        "schema_version": "1.0.0",
        "doc_roots": ["README.md"],
        "doc_entrypoints": ["README.md"],
        "doc_entrypoint_details": [
            {
                "path": "README.md",
                "type": "readme",
                "size_bytes": 100,
            }
        ],
    }
    atomic_write_json(layout.artifacts_dir / "discovered_docs.json", docs)

    examples = {
        "schema_version": "1.0.0",
        "example_roots": [],
        "example_paths": [],
        "example_file_details": [],
    }
    atomic_write_json(layout.artifacts_dir / "discovered_examples.json", examples)

    # Execute FactsBuilder
    result = execute_facts_builder(
        run_dir=mock_run_dir,
        run_config=mock_run_config,
        run_id="test_run_sparse",
        trace_id="trace_003",
        span_id="span_003",
        llm_client=None,
    )

    # Verify result
    assert result["status"] == "success"

    # If claims < 5, should emit FACTS_BUILDER_SPARSE_CLAIMS
    if result["metadata"]["total_claims"] < 5 and result["metadata"]["total_claims"] > 0:
        events_file = mock_run_dir / "events.ndjson"
        events = []
        with open(events_file, 'r', encoding='utf-8') as f:
            for line in f:
                events.append(json.loads(line))

        event_types = [e["type"] for e in events]
        assert "FACTS_BUILDER_SPARSE_CLAIMS" in event_types


def test_facts_builder_contradictions_detected(
    mock_run_dir: Path,
    mock_repo_dir: Path,
    mock_repo_inventory: Dict[str, Any],
    mock_discovered_docs: Dict[str, Any],
    mock_discovered_examples: Dict[str, Any],
    mock_run_config: Dict[str, Any],
):
    """Test FactsBuilder detects and resolves contradictions.

    Per specs/21_worker_contracts.md:120:
    If contradictions are detected, emit FACTS_BUILDER_CONTRADICTION_DETECTED
    and apply resolution algorithm.
    """
    layout = RunLayout(run_dir=mock_run_dir)

    # Create README with contradictory claims
    contradictory_readme = mock_repo_dir / "README.md"
    contradictory_readme.write_text("""# Contradictory Product

This product supports FBX format for import and export.
Note: FBX format is not yet supported in the current version.

It can read OBJ files.
The library does not support OBJ format reading.
""", encoding='utf-8')

    # Execute FactsBuilder
    result = execute_facts_builder(
        run_dir=mock_run_dir,
        run_config=mock_run_config,
        run_id="test_run_contradiction",
        trace_id="trace_004",
        span_id="span_004",
        llm_client=None,
    )

    # Verify result
    assert result["status"] == "success"

    # Verify evidence_map contains contradictions
    with open(layout.artifacts_dir / "evidence_map.json", 'r', encoding='utf-8') as f:
        evidence_map = json.load(f)

    # Check if contradictions were detected
    if "contradictions" in evidence_map and len(evidence_map["contradictions"]) > 0:
        # Verify FACTS_BUILDER_CONTRADICTION_DETECTED event was emitted
        events_file = mock_run_dir / "events.ndjson"
        events = []
        with open(events_file, 'r', encoding='utf-8') as f:
            for line in f:
                events.append(json.loads(line))

        event_types = [e["type"] for e in events]
        assert "FACTS_BUILDER_CONTRADICTION_DETECTED" in event_types

        # Verify metadata
        assert result["metadata"]["contradictions_detected"] > 0


def test_facts_builder_missing_repo_inventory(
    mock_run_dir: Path,
    mock_repo_dir: Path,
    mock_run_config: Dict[str, Any],
):
    """Test FactsBuilder fails gracefully when repo_inventory.json is missing.

    Note: extract_claims (TC-411) also depends on repo_inventory.json, so the error
    will be raised during claims extraction, not assembly. This is correct behavior.
    """
    # Don't create repo_inventory.json

    # Create minimal dependencies
    layout = RunLayout(run_dir=mock_run_dir)
    docs = {
        "schema_version": "1.0.0",
        "doc_roots": [],
        "doc_entrypoints": [],
        "doc_entrypoint_details": [],
    }
    atomic_write_json(layout.artifacts_dir / "discovered_docs.json", docs)

    examples = {
        "schema_version": "1.0.0",
        "example_roots": [],
        "example_paths": [],
        "example_file_details": [],
    }
    atomic_write_json(layout.artifacts_dir / "discovered_examples.json", examples)

    # Execute FactsBuilder (should fail)
    # Error will be raised by either TC-411 (extract_claims) or assembly phase
    with pytest.raises((FactsBuilderAssemblyError, FactsBuilderClaimsError, FactsBuilderError)) as exc_info:
        execute_facts_builder(
            run_dir=mock_run_dir,
            run_config=mock_run_config,
            run_id="test_run_missing_inventory",
            trace_id="trace_005",
            span_id="span_005",
            llm_client=None,
        )

    # Verify error message mentions repo_inventory.json
    assert "repo_inventory.json" in str(exc_info.value)


def test_facts_builder_missing_repo_directory(
    mock_run_dir: Path,
    mock_run_config: Dict[str, Any],
):
    """Test FactsBuilder fails gracefully when repo directory is missing."""
    # Don't create repo directory

    # Execute FactsBuilder (should fail)
    with pytest.raises(FactsBuilderError) as exc_info:
        execute_facts_builder(
            run_dir=mock_run_dir,
            run_config=mock_run_config,
            run_id="test_run_missing_repo",
            trace_id="trace_006",
            span_id="span_006",
            llm_client=None,
        )

    # Verify error message
    assert "Repository directory not found" in str(exc_info.value)


def test_facts_builder_idempotency(
    mock_run_dir: Path,
    mock_repo_dir: Path,
    mock_repo_inventory: Dict[str, Any],
    mock_discovered_docs: Dict[str, Any],
    mock_discovered_examples: Dict[str, Any],
    mock_run_config: Dict[str, Any],
):
    """Test FactsBuilder is idempotent (can re-run safely).

    Per specs/28_coordination_and_handoffs.md:54-56:
    Workers must be re-runnable without changing their meaning.
    """
    layout = RunLayout(run_dir=mock_run_dir)

    # First execution
    result1 = execute_facts_builder(
        run_dir=mock_run_dir,
        run_config=mock_run_config,
        run_id="test_run_idempotent_1",
        trace_id="trace_007",
        span_id="span_007",
        llm_client=None,
    )

    # Read first product_facts
    with open(layout.artifacts_dir / "product_facts.json", 'r', encoding='utf-8') as f:
        product_facts_1 = json.load(f)

    # Second execution (should produce identical result)
    result2 = execute_facts_builder(
        run_dir=mock_run_dir,
        run_config=mock_run_config,
        run_id="test_run_idempotent_2",
        trace_id="trace_008",
        span_id="span_008",
        llm_client=None,
    )

    # Read second product_facts
    with open(layout.artifacts_dir / "product_facts.json", 'r', encoding='utf-8') as f:
        product_facts_2 = json.load(f)

    # Verify results are consistent
    assert result1["status"] == result2["status"]
    assert result1["metadata"]["total_claims"] == result2["metadata"]["total_claims"]

    # Verify claim IDs are stable (same claims produce same IDs)
    claim_ids_1 = {c["claim_id"] for c in product_facts_1["claims"]}
    claim_ids_2 = {c["claim_id"] for c in product_facts_2["claims"]}
    assert claim_ids_1 == claim_ids_2


def test_facts_builder_artifact_validation(
    mock_run_dir: Path,
    mock_repo_dir: Path,
    mock_repo_inventory: Dict[str, Any],
    mock_discovered_docs: Dict[str, Any],
    mock_discovered_examples: Dict[str, Any],
    mock_run_config: Dict[str, Any],
):
    """Test all FactsBuilder artifacts are valid and complete."""
    layout = RunLayout(run_dir=mock_run_dir)

    # Execute FactsBuilder
    result = execute_facts_builder(
        run_dir=mock_run_dir,
        run_config=mock_run_config,
        run_id="test_run_validation",
        trace_id="trace_009",
        span_id="span_009",
        llm_client=None,
    )

    # Validate extracted_claims.json
    with open(layout.artifacts_dir / "extracted_claims.json", 'r', encoding='utf-8') as f:
        extracted_claims = json.load(f)

    assert "schema_version" in extracted_claims
    assert "repo_url" in extracted_claims
    assert "repo_sha" in extracted_claims
    assert "product_name" in extracted_claims
    assert "claims" in extracted_claims
    assert "metadata" in extracted_claims

    # Validate each claim structure
    for claim in extracted_claims["claims"]:
        assert "claim_id" in claim
        assert "claim_text" in claim
        assert "claim_kind" in claim
        assert "truth_status" in claim
        assert claim["truth_status"] in ["fact", "inference"]
        assert "citations" in claim
        assert len(claim["citations"]) > 0

    # Validate evidence_map.json
    with open(layout.artifacts_dir / "evidence_map.json", 'r', encoding='utf-8') as f:
        evidence_map = json.load(f)

    assert "schema_version" in evidence_map
    assert "repo_url" in evidence_map
    assert "repo_sha" in evidence_map
    assert "claims" in evidence_map
    assert "contradictions" in evidence_map
    assert "metadata" in evidence_map

    # Validate product_facts.json
    with open(layout.artifacts_dir / "product_facts.json", 'r', encoding='utf-8') as f:
        product_facts = json.load(f)

    # Validate required fields per product_facts.schema.json
    required_fields = [
        "schema_version",
        "product_name",
        "product_slug",
        "repo_url",
        "repo_sha",
        "positioning",
        "supported_platforms",
        "claims",
        "claim_groups",
        "supported_formats",
        "workflows",
        "api_surface_summary",
        "example_inventory",
    ]

    for field in required_fields:
        assert field in product_facts, f"Missing required field: {field}"

    # Validate positioning structure
    assert "tagline" in product_facts["positioning"]
    assert "short_description" in product_facts["positioning"]

    # Validate claim_groups structure
    claim_groups = product_facts["claim_groups"]
    assert "key_features" in claim_groups
    assert "install_steps" in claim_groups
    assert "quickstart_steps" in claim_groups
    assert "workflow_claims" in claim_groups
    assert "limitations" in claim_groups
    assert "compatibility_notes" in claim_groups
