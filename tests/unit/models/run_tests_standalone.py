"""Standalone test runner for model tests (no pytest required).

This validates the core functionality without pytest dependency.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from launch.models.base import Artifact, BaseModel
from launch.models.event import EVENT_RUN_CREATED, Event
from launch.models.state import (
    RUN_STATE_CREATED,
    RUN_STATE_DONE,
    WORK_ITEM_STATUS_QUEUED,
    ArtifactIndexEntry,
    Snapshot,
    WorkItem,
)
from launch.models.product_facts import EvidenceMap, ProductFacts
from launch.models.run_config import RunConfig


def test_event_serialization():
    """Test Event serialization."""
    event = Event(
        event_id="evt-001",
        run_id="run-123",
        ts="2026-01-28T00:00:00Z",
        type=EVENT_RUN_CREATED,
        payload={"data": "value"},
        trace_id="trace-abc",
        span_id="span-123",
    )

    data = event.to_dict()
    restored = Event.from_dict(data)

    assert restored.event_id == event.event_id
    assert restored.type == event.type
    print("[PASS] Event serialization test passed")


def test_snapshot_serialization():
    """Test Snapshot serialization."""
    entry = ArtifactIndexEntry(
        path="artifacts/test.json",
        sha256="a" * 64,
        schema_id="test.schema.json",
        writer_worker="W1",
    )

    item = WorkItem(
        work_item_id="wi-001",
        worker="W1",
        attempt=1,
        status=WORK_ITEM_STATUS_QUEUED,
        inputs=["input.json"],
        outputs=["output.json"],
    )

    snapshot = Snapshot(
        schema_version="v1.0",
        run_id="run-123",
        run_state=RUN_STATE_CREATED,
        artifacts_index={"test": entry},
        work_items=[item],
        issues=[],
    )

    data = snapshot.to_dict()
    restored = Snapshot.from_dict(data)

    assert restored.run_id == snapshot.run_id
    assert len(restored.artifacts_index) == 1
    assert len(restored.work_items) == 1
    print("[PASS] Snapshot serialization test passed")


def test_product_facts_serialization():
    """Test ProductFacts serialization."""
    facts = ProductFacts(
        schema_version="v1.0",
        product_name="Test Product",
        product_slug="test-product",
        repo_url="https://github.com/test/repo",
        repo_sha="a" * 40,
        positioning={"tagline": "Test", "short_description": "Desc"},
        supported_platforms=["python"],
        claims=[],
        claim_groups={
            "key_features": [],
            "install_steps": [],
            "quickstart_steps": [],
            "workflow_claims": [],
            "limitations": [],
            "compatibility_notes": [],
        },
        supported_formats=[],
        workflows=[],
        api_surface_summary={},
        example_inventory=[],
    )

    data = facts.to_dict()
    restored = ProductFacts.from_dict(data)

    assert restored.product_name == facts.product_name
    assert restored.product_slug == facts.product_slug
    print("[PASS] ProductFacts serialization test passed")


def test_evidence_map_serialization():
    """Test EvidenceMap serialization."""
    emap = EvidenceMap(
        schema_version="v1.0",
        repo_url="https://github.com/test/repo",
        repo_sha="b" * 40,
        claims=[],
    )

    data = emap.to_dict()
    restored = EvidenceMap.from_dict(data)

    assert restored.repo_url == emap.repo_url
    assert restored.repo_sha == emap.repo_sha
    print("[PASS] EvidenceMap serialization test passed")


def test_json_determinism():
    """Test that JSON serialization is deterministic."""
    event1 = Event(
        event_id="evt-test",
        run_id="run-test",
        ts="2026-01-28T00:00:00Z",
        type="TEST",
        payload={"a": 1, "b": 2},
        trace_id="trace",
        span_id="span",
    )

    event2 = Event(
        event_id="evt-test",
        run_id="run-test",
        ts="2026-01-28T00:00:00Z",
        type="TEST",
        payload={"a": 1, "b": 2},
        trace_id="trace",
        span_id="span",
    )

    json1 = event1.to_json()
    json2 = event2.to_json()

    assert json1 == json2, "JSON serialization should be deterministic"
    print("[PASS] JSON determinism test passed")


def test_run_config_serialization():
    """Test RunConfig serialization."""
    config = RunConfig(
        schema_version="v1.0",
        product_slug="test",
        product_name="Test Product",
        family="test-family",
        github_repo_url="https://github.com/test/repo",
        github_ref="a" * 40,
        required_sections=["products"],
        site_layout={
            "content_root": "content",
            "subdomain_roots": {
                "products": "content/products",
                "docs": "content/docs",
                "kb": "content/kb",
                "reference": "content/reference",
                "blog": "content/blog",
            },
            "localization": {"mode_by_section": {"products": "dir", "docs": "dir", "kb": "dir", "reference": "dir", "blog": "filename"}},
        },
        allowed_paths=["content/products/test"],
        llm={"api_base_url": "http://localhost", "model": "test", "decoding": {"temperature": 0.0}},
        mcp={"enabled": True, "listen_host": "127.0.0.1", "listen_port": 8787},
        telemetry={"endpoint_url": "http://localhost", "project": "test"},
        commit_service={
            "endpoint_url": "http://localhost",
            "github_token_env": "TOKEN",
            "commit_message_template": "test",
            "commit_body_template": "test",
        },
        templates_version="v1",
        ruleset_version="v1",
        allow_inference=False,
        max_fix_attempts=3,
        budgets={
            "max_runtime_s": 3600,
            "max_llm_calls": 100,
            "max_llm_tokens": 100000,
            "max_file_writes": 50,
            "max_patch_attempts": 10,
            "max_lines_per_file": 500,
            "max_files_changed": 100,
        },
        locale="en",
    )

    data = config.to_dict()
    restored = RunConfig.from_dict(data)

    assert restored.product_slug == config.product_slug
    assert restored.product_name == config.product_name
    assert restored.github_ref == config.github_ref
    print("[PASS] RunConfig serialization test passed")


def main():
    """Run all tests."""
    print("Running model validation tests...\n")

    try:
        test_event_serialization()
        test_snapshot_serialization()
        test_product_facts_serialization()
        test_evidence_map_serialization()
        test_json_determinism()
        test_run_config_serialization()

        print("\n" + "=" * 50)
        print("ALL TESTS PASSED [PASS]")
        print("=" * 50)
        return 0

    except AssertionError as e:
        print(f"\n[FAIL] Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n[FAIL] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
