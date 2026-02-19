"""Tests for W2 split: W2a Extractor + W2b Synthesizer.

Validates:
- execute_extraction_phase() runs deterministic extraction without LLM
- execute_synthesis_phase() enhances W2a outputs with LLM
- Both phases produce expected artifacts
- execute_facts_builder() backward compat calls both phases
- W2a/W2b registered in worker dispatch map
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from launch.workers.w2_facts_builder import (
    execute_extraction_phase,
    execute_synthesis_phase,
    execute_facts_builder,
    FactsBuilderError,
)


MINIMAL_RUN_CONFIG = {
    "schema_version": "1.0",
    "product_slug": "testlib",
    "product_name": "TestLib",
    "family": "test",
    "github_repo_url": "https://github.com/test/test-lib",
    "github_ref": "main",
    "required_sections": ["overview"],
    "site_layout": {"content_dir": "content", "output_dir": "public"},
    "allowed_paths": ["content/"],
    "llm": {"provider": "test", "model": "test-model"},
    "mcp": {"enabled": False},
    "telemetry": {"enabled": False},
    "commit_service": {"mode": "test"},
    "templates_version": "1.0",
    "ruleset_version": "1.0",
    "allow_inference": False,
    "max_fix_attempts": 3,
    "budgets": {"max_tokens": 10000},
    "target_platform": "python",
    "platform_family": "test",
}


@pytest.fixture
def w2_run_dir(tmp_path):
    """Set up a minimal W2 run directory with required W1 artifacts."""
    run_dir = tmp_path / "run"
    artifacts_dir = run_dir / "artifacts"
    work_dir = run_dir / "work"
    repo_dir = work_dir / "repo"

    artifacts_dir.mkdir(parents=True)
    work_dir.mkdir(parents=True)
    repo_dir.mkdir(parents=True)

    # Create minimal repo_inventory.json (W1 output)
    repo_inventory = {
        "repo_url": "https://github.com/test/test-lib",
        "repo_sha": "abc123",
        "product_name": "TestLib",
        "files": [],
    }
    (artifacts_dir / "repo_inventory.json").write_text(
        json.dumps(repo_inventory), encoding="utf-8"
    )

    # Create minimal discovered_docs.json (W1 output)
    readme_path = repo_dir / "README.md"
    readme_path.write_text(
        "# TestLib\n\nA powerful testing library.\n\n"
        "## Installation\n\npip install testlib\n\n"
        "## Features\n\n- Fast testing\n- Easy setup\n- Cross-platform support\n",
        encoding="utf-8",
    )

    discovered_docs = {
        "doc_entrypoint_details": [
            {
                "path": "README.md",
                "relevance_score": 90,
                "evidence_priority": "high",
            }
        ]
    }
    (artifacts_dir / "discovered_docs.json").write_text(
        json.dumps(discovered_docs), encoding="utf-8"
    )

    # Create minimal discovered_examples.json
    (artifacts_dir / "discovered_examples.json").write_text(
        json.dumps({"examples": []}), encoding="utf-8"
    )

    return run_dir


class TestExtractionPhase:
    """Tests for W2a: execute_extraction_phase()."""

    def test_produces_extracted_claims(self, w2_run_dir):
        result = execute_extraction_phase(
            run_dir=w2_run_dir,
            run_config={"product_name": "TestLib"},
        )
        assert result["status"] == "success"
        assert "extracted_claims" in result["artifacts"]

        # Verify extracted_claims.json exists on disk
        claims_path = w2_run_dir / "artifacts" / "extracted_claims.json"
        assert claims_path.exists()

        claims_data = json.loads(claims_path.read_text(encoding="utf-8"))
        assert "claims" in claims_data
        assert "metadata" in claims_data

    def test_produces_evidence_map(self, w2_run_dir):
        result = execute_extraction_phase(
            run_dir=w2_run_dir,
            run_config={"product_name": "TestLib"},
        )
        assert "evidence_map" in result["artifacts"]

        evidence_path = w2_run_dir / "artifacts" / "evidence_map.json"
        assert evidence_path.exists()

    def test_produces_code_analysis(self, w2_run_dir):
        result = execute_extraction_phase(
            run_dir=w2_run_dir,
            run_config={"product_name": "TestLib"},
        )
        assert "code_analysis" in result["artifacts"]

        code_analysis_path = w2_run_dir / "artifacts" / "code_analysis.json"
        assert code_analysis_path.exists()

    def test_no_llm_calls(self, w2_run_dir):
        """W2a must never use LLM — verify no LLM client is created."""
        with patch(
            "launch.workers.w2_facts_builder.extract_claims.extract_claims_with_llm"
        ) as mock_llm:
            result = execute_extraction_phase(
                run_dir=w2_run_dir,
                run_config={"product_name": "TestLib"},
            )
            mock_llm.assert_not_called()

    def test_metadata_populated(self, w2_run_dir):
        result = execute_extraction_phase(
            run_dir=w2_run_dir,
            run_config={"product_name": "TestLib"},
        )
        assert "total_claims" in result["metadata"]
        assert "fact_claims" in result["metadata"]
        assert "inference_claims" in result["metadata"]
        assert "contradictions_detected" in result["metadata"]

    def test_deterministic(self, w2_run_dir):
        """Same inputs should produce identical outputs."""
        result1 = execute_extraction_phase(
            run_dir=w2_run_dir,
            run_config={"product_name": "TestLib"},
        )

        # Read claims from first run
        claims_path = w2_run_dir / "artifacts" / "extracted_claims.json"
        claims1 = json.loads(claims_path.read_text(encoding="utf-8"))

        # Run again (re-creates artifacts)
        result2 = execute_extraction_phase(
            run_dir=w2_run_dir,
            run_config={"product_name": "TestLib"},
        )
        claims2 = json.loads(claims_path.read_text(encoding="utf-8"))

        assert result1["metadata"]["total_claims"] == result2["metadata"]["total_claims"]
        assert len(claims1["claims"]) == len(claims2["claims"])

    def test_fails_without_repo_dir(self, tmp_path):
        """Should raise if repo directory doesn't exist."""
        run_dir = tmp_path / "run"
        (run_dir / "artifacts").mkdir(parents=True)
        (run_dir / "work").mkdir(parents=True)
        # Note: NOT creating work/repo

        with pytest.raises(FactsBuilderError, match="Repository directory not found"):
            execute_extraction_phase(
                run_dir=run_dir,
                run_config={"product_name": "TestLib"},
            )


class TestSynthesisPhase:
    """Tests for W2b: execute_synthesis_phase()."""

    def test_requires_w2a_artifacts(self, tmp_path):
        """Should fail if W2a artifacts don't exist."""
        run_dir = tmp_path / "run"
        (run_dir / "artifacts").mkdir(parents=True)
        (run_dir / "work" / "repo").mkdir(parents=True)

        with pytest.raises(FactsBuilderError, match="extraction artifacts not found"):
            execute_synthesis_phase(
                run_dir=run_dir,
                run_config={"product_name": "TestLib"},
            )

    def test_produces_product_facts(self, w2_run_dir):
        """W2b should produce product_facts.json from W2a outputs."""
        # First run W2a
        execute_extraction_phase(
            run_dir=w2_run_dir,
            run_config={"product_name": "TestLib", "family": "test"},
        )

        # Then run W2b (no LLM — will use offline fallbacks)
        result = execute_synthesis_phase(
            run_dir=w2_run_dir,
            run_config={"product_name": "TestLib", "family": "test"},
            llm_client=None,
        )

        assert result["status"] == "success"
        assert "product_facts" in result["artifacts"]

        product_facts_path = w2_run_dir / "artifacts" / "product_facts.json"
        assert product_facts_path.exists()

        pf = json.loads(product_facts_path.read_text(encoding="utf-8"))
        assert "claims" in pf
        assert "claim_groups" in pf

    def test_offline_fallback(self, w2_run_dir):
        """W2b should work without LLM (offline mode)."""
        execute_extraction_phase(
            run_dir=w2_run_dir,
            run_config={"product_name": "TestLib", "family": "test"},
        )

        result = execute_synthesis_phase(
            run_dir=w2_run_dir,
            run_config={"product_name": "TestLib", "family": "test"},
            llm_client=None,
        )
        assert result["status"] == "success"

    def test_classify_enrichment(self, w2_run_dir):
        """W2b should classify and enrich claims even in offline mode."""
        execute_extraction_phase(
            run_dir=w2_run_dir,
            run_config={"product_name": "TestLib", "family": "test"},
        )

        result = execute_synthesis_phase(
            run_dir=w2_run_dir,
            run_config={"product_name": "TestLib", "family": "test", "enrich_claims": True},
            llm_client=None,
        )
        # Should not crash even without LLM
        assert result["status"] == "success"


class TestFullPipeline:
    """Tests for execute_facts_builder() backward compatibility."""

    def test_full_pipeline_produces_all_artifacts(self, w2_run_dir):
        """Monolithic execute_facts_builder should still work."""
        result = execute_facts_builder(
            run_dir=w2_run_dir,
            run_config=MINIMAL_RUN_CONFIG,
        )
        assert result["status"] == "success"
        assert "product_facts" in result["artifacts"]
        assert "extracted_claims" in result["artifacts"]
        assert "evidence_map" in result["artifacts"]


class TestWorkerDispatch:
    """Tests for W2a/W2b registration in worker dispatch map."""

    def test_w2a_registered(self):
        from launch.orchestrator.worker_invoker import WORKER_DISPATCH

        assert "W2a.Extractor" in WORKER_DISPATCH
        assert WORKER_DISPATCH["W2a.Extractor"] is execute_extraction_phase

    def test_w2b_registered(self):
        from launch.orchestrator.worker_invoker import WORKER_DISPATCH

        assert "W2b.Synthesizer" in WORKER_DISPATCH
        assert WORKER_DISPATCH["W2b.Synthesizer"] is execute_synthesis_phase

    def test_w2_still_registered(self):
        from launch.orchestrator.worker_invoker import WORKER_DISPATCH

        assert "W2.FactsBuilder" in WORKER_DISPATCH

    def test_all_workers_present(self):
        """Sanity: all expected workers should be in dispatch."""
        from launch.orchestrator.worker_invoker import WORKER_DISPATCH

        expected = [
            "W1.RepoScout",
            "W2.FactsBuilder",
            "W2a.Extractor",
            "W2b.Synthesizer",
            "W3.SnippetCurator",
            "W4.IAPlanner",
            "W5.SectionWriter",
            "W7.ContentReviewer",
            "W8.LinkerAndPatcher",
            "W9.Validator",
            "W10.Fixer",
            "W11.PRManager",
        ]
        for worker in expected:
            assert worker in WORKER_DISPATCH, f"{worker} not in WORKER_DISPATCH"
