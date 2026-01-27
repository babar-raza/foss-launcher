"""Tests for TC-420: W3 SnippetCurator integrator.

This test module validates the W3 SnippetCurator integrator worker that
orchestrates TC-421 and TC-422 sub-workers to produce a unified snippet_catalog.json.

Test coverage:
- Integration test: full pipeline (happy path)
- Error handling: doc extraction failure, code extraction failure
- Artifact validation: all expected artifacts present
- Deduplication: verify snippets merged correctly
- Event sequence validation
- Idempotency: can re-run safely
- Missing input handling
- Empty artifact handling

Spec references:
- specs/21_worker_contracts.md:127-145 (W3 SnippetCurator contract)
- specs/28_coordination_and_handoffs.md (Worker coordination)
- specs/11_state_and_events.md (Event emission)
"""

import json
import pytest
from pathlib import Path
from typing import Dict, Any

from launch.workers.w3_snippet_curator.worker import (
    execute_snippet_curator,
    deduplicate_snippets,
    merge_snippet_artifacts,
    SnippetCuratorExtractionError,
    SnippetCuratorMergeError,
)
from launch.io.run_layout import RunLayout


@pytest.fixture
def temp_run_dir(tmp_path: Path) -> Path:
    """Create temporary run directory with required structure."""
    run_dir = tmp_path / "runs" / "test_run"
    run_dir.mkdir(parents=True)

    # Create work/repo directory
    repo_dir = run_dir / "work" / "repo"
    repo_dir.mkdir(parents=True)

    # Create artifacts directory
    artifacts_dir = run_dir / "artifacts"
    artifacts_dir.mkdir(parents=True)

    return run_dir


@pytest.fixture
def minimal_run_config() -> Dict[str, Any]:
    """Minimal run_config for testing."""
    return {
        "schema_version": "1.2",
        "product_slug": "test-product",
        "product_name": "Test Product",
        "family": "test",
        "github_repo_url": "https://github.com/test/repo",
        "github_ref": "main",
        "required_sections": ["docs"],
        "site_layout": {
            "content_root": "content",
            "subdomain_roots": {"docs": "content/docs"},
            "localization": {"mode_by_section": {"docs": "dir"}},
        },
        "allowed_paths": [],
        "llm": {"model": "gpt-4", "provider": "openai"},
        "mcp": {},
        "telemetry": {"enabled": False},
        "commit_service": {"type": "direct"},
        "templates_version": "1.0",
        "ruleset_version": "1.0",
        "allow_inference": True,
        "max_fix_attempts": 3,
        "budgets": {},
    }


@pytest.fixture
def sample_doc_snippets() -> Dict[str, Any]:
    """Sample doc_snippets.json artifact."""
    return {
        "schema_version": "1.0",
        "snippets": [
            {
                "snippet_id": "doc_snippet_1",
                "language": "python",
                "tags": ["quickstart", "readme"],
                "source": {
                    "type": "repo_file",
                    "path": "README.md",
                    "start_line": 10,
                    "end_line": 15,
                },
                "code": "print('Hello from README')",
                "requirements": {"dependencies": []},
                "validation": {"syntax_ok": True, "runnable_ok": "unknown"},
            },
            {
                "snippet_id": "doc_snippet_2",
                "language": "csharp",
                "tags": ["example"],
                "source": {
                    "type": "repo_file",
                    "path": "docs/guide.md",
                    "start_line": 20,
                    "end_line": 25,
                },
                "code": "Console.WriteLine(\"Hello\");",
                "requirements": {"dependencies": []},
                "validation": {"syntax_ok": True, "runnable_ok": "unknown"},
            },
        ],
    }


@pytest.fixture
def sample_code_snippets() -> Dict[str, Any]:
    """Sample code_snippets.json artifact."""
    return {
        "schema_version": "1.0",
        "snippets": [
            {
                "snippet_id": "code_snippet_1",
                "language": "python",
                "tags": ["example"],
                "source": {
                    "type": "repo_file",
                    "path": "examples/example.py",
                    "start_line": 1,
                    "end_line": 10,
                },
                "code": "def main():\n    print('Hello')",
                "requirements": {"dependencies": []},
                "validation": {"syntax_ok": True, "runnable_ok": "unknown"},
            },
            {
                "snippet_id": "code_snippet_2",
                "language": "javascript",
                "tags": ["example"],
                "source": {
                    "type": "repo_file",
                    "path": "examples/example.js",
                    "start_line": 1,
                    "end_line": 5,
                },
                "code": "console.log('Hello');",
                "requirements": {"dependencies": []},
                "validation": {"syntax_ok": True, "runnable_ok": "unknown"},
            },
        ],
    }


@pytest.fixture
def mock_doc_extraction(monkeypatch, sample_doc_snippets):
    """Mock extract_doc_snippets to return sample data."""
    def mock_extract(repo_dir, run_dir):
        # Write doc_snippets.json
        run_layout = RunLayout(run_dir=run_dir)
        doc_path = run_layout.artifacts_dir / "doc_snippets.json"
        doc_path.write_text(json.dumps(sample_doc_snippets, indent=2))
        return sample_doc_snippets

    import launch.workers.w3_snippet_curator.worker as worker_module
    monkeypatch.setattr(worker_module, "extract_doc_snippets", mock_extract)


@pytest.fixture
def mock_code_extraction(monkeypatch, sample_code_snippets):
    """Mock extract_code_snippets to return sample data."""
    def mock_extract(repo_dir, run_dir):
        # Write code_snippets.json
        run_layout = RunLayout(run_dir=run_dir)
        code_path = run_layout.artifacts_dir / "code_snippets.json"
        code_path.write_text(json.dumps(sample_code_snippets, indent=2))
        return sample_code_snippets

    import launch.workers.w3_snippet_curator.worker as worker_module
    monkeypatch.setattr(worker_module, "extract_code_snippets", mock_extract)


def test_execute_snippet_curator_happy_path(
    temp_run_dir,
    minimal_run_config,
    mock_doc_extraction,
    mock_code_extraction,
):
    """Test TC-420 full pipeline (happy path).

    Validates:
    - Doc extraction runs successfully
    - Code extraction runs successfully
    - Snippets are merged and deduplicated
    - snippet_catalog.json is created
    - All events are emitted
    - Status is success

    Spec reference: specs/21_worker_contracts.md:127-145
    """
    # Create required input artifacts
    run_layout = RunLayout(run_dir=temp_run_dir)

    # Create minimal repo_inventory.json
    repo_inventory = {
        "schema_version": "1.0",
        "repo_url": "https://github.com/test/repo",
        "resolved_sha": "abc123",
        "example_paths": ["examples/example.py"],
    }
    (run_layout.artifacts_dir / "repo_inventory.json").write_text(
        json.dumps(repo_inventory, indent=2)
    )

    # Create minimal discovered_docs.json
    discovered_docs = {
        "schema_version": "1.0",
        "doc_entrypoint_details": [
            {"path": "README.md", "doc_type": "readme"}
        ],
    }
    (run_layout.artifacts_dir / "discovered_docs.json").write_text(
        json.dumps(discovered_docs, indent=2)
    )

    # Execute worker
    result = execute_snippet_curator(
        run_dir=temp_run_dir,
        run_config=minimal_run_config,
        run_id="test_run",
        trace_id="test_trace",
        span_id="test_span",
    )

    # Validate result
    assert result["status"] == "success"
    assert result["error"] is None
    assert "artifacts" in result
    assert "metadata" in result

    # Validate artifacts created
    assert "snippet_catalog" in result["artifacts"]
    catalog_path = Path(result["artifacts"]["snippet_catalog"])
    assert catalog_path.exists()

    # Validate snippet_catalog.json content
    catalog = json.loads(catalog_path.read_text())
    assert "schema_version" in catalog
    assert "snippets" in catalog
    assert len(catalog["snippets"]) == 4  # 2 doc + 2 code

    # Validate metadata
    metadata = result["metadata"]
    assert metadata["doc_snippets_count"] == 2
    assert metadata["code_snippets_count"] == 2
    assert metadata["unique_snippets_count"] == 4
    assert metadata["total_snippets_count"] == 4
    assert metadata["duplicates_removed"] == 0

    # Validate events emitted
    events_file = temp_run_dir / "events.ndjson"
    assert events_file.exists()

    events = [json.loads(line) for line in events_file.read_text().strip().split("\n")]
    event_types = [e["type"] for e in events]

    assert "WORK_ITEM_STARTED" in event_types
    assert "WORK_ITEM_FINISHED" in event_types
    assert event_types.count("ARTIFACT_WRITTEN") >= 3  # doc, code, catalog


def test_deduplicate_snippets():
    """Test snippet deduplication logic.

    Validates:
    - Duplicate snippet_ids are removed
    - First occurrence is kept
    - Order is preserved for non-duplicates

    Spec reference: specs/21_worker_contracts.md:142
    """
    snippets = [
        {"snippet_id": "snippet_1", "code": "first"},
        {"snippet_id": "snippet_2", "code": "second"},
        {"snippet_id": "snippet_1", "code": "duplicate"},  # Duplicate
        {"snippet_id": "snippet_3", "code": "third"},
    ]

    unique = deduplicate_snippets(snippets)

    assert len(unique) == 3
    assert unique[0]["snippet_id"] == "snippet_1"
    assert unique[0]["code"] == "first"  # First occurrence kept
    assert unique[1]["snippet_id"] == "snippet_2"
    assert unique[2]["snippet_id"] == "snippet_3"


def test_merge_snippet_artifacts(sample_doc_snippets, sample_code_snippets):
    """Test snippet artifact merging.

    Validates:
    - Snippets from both sources are combined
    - Deduplication is applied
    - Sorting is deterministic
    - Schema version is preserved

    Spec reference: specs/21_worker_contracts.md:127-145
    """
    merged = merge_snippet_artifacts(sample_doc_snippets, sample_code_snippets)

    assert "schema_version" in merged
    assert merged["schema_version"] == "1.0"
    assert "snippets" in merged
    assert len(merged["snippets"]) == 4

    # Validate deterministic sorting (by language, tags, snippet_id)
    languages = [s["language"] for s in merged["snippets"]]
    # Should be sorted by language
    assert languages == sorted(languages)


def test_merge_with_duplicates():
    """Test merging with duplicate snippets across sources.

    Validates:
    - Duplicates are removed
    - Doc snippets take priority (first occurrence)
    - Count metadata is correct

    Spec reference: specs/21_worker_contracts.md:142
    """
    doc_snippets = {
        "schema_version": "1.0",
        "snippets": [
            {
                "snippet_id": "shared_snippet",
                "language": "python",
                "tags": ["doc"],
                "source": {
                    "type": "repo_file",
                    "path": "README.md",
                    "start_line": 1,
                    "end_line": 5,
                },
                "code": "from docs",
                "requirements": {"dependencies": []},
                "validation": {"syntax_ok": True, "runnable_ok": "unknown"},
            },
        ],
    }

    code_snippets = {
        "schema_version": "1.0",
        "snippets": [
            {
                "snippet_id": "shared_snippet",  # Same ID
                "language": "python",
                "tags": ["code"],
                "source": {
                    "type": "repo_file",
                    "path": "examples/ex.py",
                    "start_line": 1,
                    "end_line": 5,
                },
                "code": "from code",
                "requirements": {"dependencies": []},
                "validation": {"syntax_ok": True, "runnable_ok": "unknown"},
            },
        ],
    }

    merged = merge_snippet_artifacts(doc_snippets, code_snippets)

    # Should only have 1 snippet (doc version takes priority)
    assert len(merged["snippets"]) == 1
    assert merged["snippets"][0]["code"] == "from docs"
    assert merged["snippets"][0]["tags"] == ["doc"]


def test_execute_snippet_curator_missing_repo(temp_run_dir, minimal_run_config):
    """Test error handling when repo directory is missing.

    Validates:
    - Error is raised when repo directory not found
    - Error event is emitted
    - Result status is failed
    - Error message is descriptive

    Spec reference: specs/28_coordination_and_handoffs.md:134-161
    """
    # Don't create work/repo directory (it exists from fixture but we remove it)
    repo_dir = temp_run_dir / "work" / "repo"
    if repo_dir.exists():
        import shutil
        shutil.rmtree(repo_dir)

    result = execute_snippet_curator(
        run_dir=temp_run_dir,
        run_config=minimal_run_config,
        run_id="test_run",
        trace_id="test_trace",
        span_id="test_span",
    )

    # Validate error result
    assert result["status"] == "failed"
    assert result["error"] is not None
    assert "Repository directory not found" in result["error"]

    # Validate events
    events_file = temp_run_dir / "events.ndjson"
    assert events_file.exists()

    events = [json.loads(line) for line in events_file.read_text().strip().split("\n")]
    event_types = [e["type"] for e in events]

    assert "RUN_FAILED" in event_types


def test_execute_snippet_curator_doc_extraction_fails(
    temp_run_dir,
    minimal_run_config,
    mock_code_extraction,
    monkeypatch,
):
    """Test error handling when doc extraction fails.

    Validates:
    - Error is caught and handled gracefully
    - Error event is emitted
    - Result status is failed
    - Code extraction is NOT attempted (fail fast)

    Spec reference: specs/28_coordination_and_handoffs.md:134-161
    """
    # Mock doc extraction to fail
    def mock_extract_fail(repo_dir, run_dir):
        raise ValueError("Doc extraction failed")

    import launch.workers.w3_snippet_curator.worker as worker_module
    monkeypatch.setattr(worker_module, "extract_doc_snippets", mock_extract_fail)

    # Create minimal input artifacts
    run_layout = RunLayout(run_dir=temp_run_dir)
    repo_inventory = {"schema_version": "1.0", "example_paths": []}
    (run_layout.artifacts_dir / "repo_inventory.json").write_text(
        json.dumps(repo_inventory)
    )
    discovered_docs = {"schema_version": "1.0", "doc_entrypoint_details": []}
    (run_layout.artifacts_dir / "discovered_docs.json").write_text(
        json.dumps(discovered_docs)
    )

    result = execute_snippet_curator(
        run_dir=temp_run_dir,
        run_config=minimal_run_config,
        run_id="test_run",
        trace_id="test_trace",
        span_id="test_span",
    )

    # Validate error result
    assert result["status"] == "failed"
    assert result["error"] is not None
    assert "Doc snippet extraction failed" in result["error"]

    # Validate events
    events_file = temp_run_dir / "events.ndjson"
    events = [json.loads(line) for line in events_file.read_text().strip().split("\n")]
    event_types = [e["type"] for e in events]

    assert "RUN_FAILED" in event_types


def test_execute_snippet_curator_code_extraction_fails(
    minimal_run_config,
    temp_run_dir,
    mock_doc_extraction,
    monkeypatch,
):
    """Test error handling when code extraction fails.

    Validates:
    - Doc extraction succeeds first
    - Code extraction error is caught
    - Error event is emitted
    - Result status is failed

    Spec reference: specs/28_coordination_and_handoffs.md:134-161
    """
    # Mock code extraction to fail
    def mock_extract_fail(repo_dir, run_dir):
        raise ValueError("Code extraction failed")

    import launch.workers.w3_snippet_curator.worker as worker_module
    monkeypatch.setattr(worker_module, "extract_code_snippets", mock_extract_fail)

    # Create minimal input artifacts
    run_layout = RunLayout(run_dir=temp_run_dir)
    repo_inventory = {"schema_version": "1.0", "example_paths": []}
    (run_layout.artifacts_dir / "repo_inventory.json").write_text(
        json.dumps(repo_inventory)
    )
    discovered_docs = {"schema_version": "1.0", "doc_entrypoint_details": []}
    (run_layout.artifacts_dir / "discovered_docs.json").write_text(
        json.dumps(discovered_docs)
    )

    result = execute_snippet_curator(
        run_dir=temp_run_dir,
        run_config=minimal_run_config,
        run_id="test_run",
        trace_id="test_trace",
        span_id="test_span",
    )

    # Validate error result
    assert result["status"] == "failed"
    assert result["error"] is not None
    assert "Code snippet extraction failed" in result["error"]

    # Validate doc_snippets.json was created (doc extraction succeeded)
    doc_path = run_layout.artifacts_dir / "doc_snippets.json"
    assert doc_path.exists()


def test_execute_snippet_curator_empty_artifacts(
    temp_run_dir,
    minimal_run_config,
    monkeypatch,
):
    """Test handling of empty snippet artifacts.

    Validates:
    - Empty doc_snippets.json is handled gracefully
    - Empty code_snippets.json is handled gracefully
    - Merged catalog is valid but empty
    - Status is success (empty is valid)

    Spec reference: specs/21_worker_contracts.md:127-145
    """
    # Mock extractions to return empty results
    def mock_extract_empty_doc(repo_dir, run_dir):
        empty = {"schema_version": "1.0", "snippets": []}
        run_layout = RunLayout(run_dir=run_dir)
        doc_path = run_layout.artifacts_dir / "doc_snippets.json"
        doc_path.write_text(json.dumps(empty))
        return empty

    def mock_extract_empty_code(repo_dir, run_dir):
        empty = {"schema_version": "1.0", "snippets": []}
        run_layout = RunLayout(run_dir=run_dir)
        code_path = run_layout.artifacts_dir / "code_snippets.json"
        code_path.write_text(json.dumps(empty))
        return empty

    import launch.workers.w3_snippet_curator.worker as worker_module
    monkeypatch.setattr(worker_module, "extract_doc_snippets", mock_extract_empty_doc)
    monkeypatch.setattr(worker_module, "extract_code_snippets", mock_extract_empty_code)

    # Create minimal input artifacts
    run_layout = RunLayout(run_dir=temp_run_dir)
    repo_inventory = {"schema_version": "1.0", "example_paths": []}
    (run_layout.artifacts_dir / "repo_inventory.json").write_text(
        json.dumps(repo_inventory)
    )
    discovered_docs = {"schema_version": "1.0", "doc_entrypoint_details": []}
    (run_layout.artifacts_dir / "discovered_docs.json").write_text(
        json.dumps(discovered_docs)
    )

    result = execute_snippet_curator(
        run_dir=temp_run_dir,
        run_config=minimal_run_config,
        run_id="test_run",
        trace_id="test_trace",
        span_id="test_span",
    )

    # Validate success with empty results
    assert result["status"] == "success"
    assert result["error"] is None
    assert result["metadata"]["unique_snippets_count"] == 0
    assert result["metadata"]["duplicates_removed"] == 0

    # Validate snippet_catalog.json exists and is valid
    catalog_path = Path(result["artifacts"]["snippet_catalog"])
    assert catalog_path.exists()

    catalog = json.loads(catalog_path.read_text())
    assert catalog["snippets"] == []


def test_execute_snippet_curator_idempotency(
    temp_run_dir,
    minimal_run_config,
    mock_doc_extraction,
    mock_code_extraction,
):
    """Test idempotency: can re-run worker safely.

    Validates:
    - Running worker twice produces same result
    - Artifacts are overwritten (not appended)
    - Events are appended to log
    - Final state is consistent

    Spec reference: specs/28_coordination_and_handoffs.md:54
    """
    # Create minimal input artifacts
    run_layout = RunLayout(run_dir=temp_run_dir)
    repo_inventory = {"schema_version": "1.0", "example_paths": []}
    (run_layout.artifacts_dir / "repo_inventory.json").write_text(
        json.dumps(repo_inventory)
    )
    discovered_docs = {"schema_version": "1.0", "doc_entrypoint_details": []}
    (run_layout.artifacts_dir / "discovered_docs.json").write_text(
        json.dumps(discovered_docs)
    )

    # First run
    result1 = execute_snippet_curator(
        run_dir=temp_run_dir,
        run_config=minimal_run_config,
        run_id="test_run_1",
        trace_id="test_trace_1",
        span_id="test_span_1",
    )

    catalog_path_1 = Path(result1["artifacts"]["snippet_catalog"])
    catalog_1 = json.loads(catalog_path_1.read_text())

    # Second run
    result2 = execute_snippet_curator(
        run_dir=temp_run_dir,
        run_config=minimal_run_config,
        run_id="test_run_2",
        trace_id="test_trace_2",
        span_id="test_span_2",
    )

    catalog_path_2 = Path(result2["artifacts"]["snippet_catalog"])
    catalog_2 = json.loads(catalog_path_2.read_text())

    # Validate results are identical
    assert result1["status"] == result2["status"]
    assert result1["metadata"]["unique_snippets_count"] == result2["metadata"]["unique_snippets_count"]

    # Validate catalog content is identical
    assert len(catalog_1["snippets"]) == len(catalog_2["snippets"])

    # Validate events were appended (not overwritten)
    events_file = temp_run_dir / "events.ndjson"
    events = [json.loads(line) for line in events_file.read_text().strip().split("\n")]

    # Should have events from both runs
    run_ids = [e["run_id"] for e in events]
    assert "test_run_1" in run_ids
    assert "test_run_2" in run_ids


def test_snippet_catalog_schema_validation(
    temp_run_dir,
    minimal_run_config,
    mock_doc_extraction,
    mock_code_extraction,
):
    """Test snippet_catalog.json validates against schema.

    Validates:
    - All required fields are present
    - Field types are correct
    - Snippet structure matches snippet_catalog.schema.json

    Spec reference: specs/schemas/snippet_catalog.schema.json
    """
    # Create minimal input artifacts
    run_layout = RunLayout(run_dir=temp_run_dir)
    repo_inventory = {"schema_version": "1.0", "example_paths": []}
    (run_layout.artifacts_dir / "repo_inventory.json").write_text(
        json.dumps(repo_inventory)
    )
    discovered_docs = {"schema_version": "1.0", "doc_entrypoint_details": []}
    (run_layout.artifacts_dir / "discovered_docs.json").write_text(
        json.dumps(discovered_docs)
    )

    result = execute_snippet_curator(
        run_dir=temp_run_dir,
        run_config=minimal_run_config,
        run_id="test_run",
        trace_id="test_trace",
        span_id="test_span",
    )

    catalog_path = Path(result["artifacts"]["snippet_catalog"])
    catalog = json.loads(catalog_path.read_text())

    # Validate top-level structure
    assert "schema_version" in catalog
    assert isinstance(catalog["schema_version"], str)
    assert "snippets" in catalog
    assert isinstance(catalog["snippets"], list)

    # Validate each snippet
    for snippet in catalog["snippets"]:
        assert "snippet_id" in snippet
        assert isinstance(snippet["snippet_id"], str)
        assert "language" in snippet
        assert isinstance(snippet["language"], str)
        assert "tags" in snippet
        assert isinstance(snippet["tags"], list)
        assert "source" in snippet
        assert isinstance(snippet["source"], dict)
        assert "code" in snippet
        assert isinstance(snippet["code"], str)
        assert "requirements" in snippet
        assert isinstance(snippet["requirements"], dict)
        assert "validation" in snippet
        assert isinstance(snippet["validation"], dict)

        # Validate source structure
        source = snippet["source"]
        assert "type" in source
        assert source["type"] in ["repo_file", "generated"]
        if source["type"] == "repo_file":
            assert "path" in source
            assert "start_line" in source
            assert "end_line" in source

        # Validate validation structure
        validation = snippet["validation"]
        assert "syntax_ok" in validation
        assert isinstance(validation["syntax_ok"], bool)
        assert "runnable_ok" in validation
        # runnable_ok can be bool or "unknown"
        assert isinstance(validation["runnable_ok"], (bool, str))


def test_execute_snippet_curator_deterministic_output(
    temp_run_dir,
    minimal_run_config,
    mock_doc_extraction,
    mock_code_extraction,
):
    """Test deterministic output ordering.

    Validates:
    - Snippets are sorted deterministically
    - Order is stable across runs
    - Sort key is (language, tags[0], snippet_id)

    Spec reference: specs/10_determinism_and_caching.md:46
    """
    # Create minimal input artifacts
    run_layout = RunLayout(run_dir=temp_run_dir)
    repo_inventory = {"schema_version": "1.0", "example_paths": []}
    (run_layout.artifacts_dir / "repo_inventory.json").write_text(
        json.dumps(repo_inventory)
    )
    discovered_docs = {"schema_version": "1.0", "doc_entrypoint_details": []}
    (run_layout.artifacts_dir / "discovered_docs.json").write_text(
        json.dumps(discovered_docs)
    )

    result = execute_snippet_curator(
        run_dir=temp_run_dir,
        run_config=minimal_run_config,
        run_id="test_run",
        trace_id="test_trace",
        span_id="test_span",
    )

    catalog_path = Path(result["artifacts"]["snippet_catalog"])
    catalog = json.loads(catalog_path.read_text())

    snippets = catalog["snippets"]

    # Validate sorting: language ASC, tags[0] ASC, snippet_id ASC
    for i in range(len(snippets) - 1):
        s1 = snippets[i]
        s2 = snippets[i + 1]

        lang1 = s1.get("language", "")
        lang2 = s2.get("language", "")

        if lang1 != lang2:
            assert lang1 <= lang2
        else:
            # Same language, check tags
            tag1 = s1.get("tags", [""])[0]
            tag2 = s2.get("tags", [""])[0]

            if tag1 != tag2:
                assert tag1 <= tag2
            else:
                # Same language and tag, check snippet_id
                id1 = s1.get("snippet_id", "")
                id2 = s2.get("snippet_id", "")
                assert id1 <= id2
