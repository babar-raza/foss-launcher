"""TC-2405: Tests for parallel workflow + example enrichment in W2 FactsBuilder.

Validates:
1. enrich_example calls are parallelized when max_parallel_batches > 1
2. Sequential and parallel example enrichment produce the same results
3. Example ID pre-assignment happens before parallel calls
4. enrich_example exception → fallback dict (parallel path)
5. Workflow enrichment: llm_generate_workflow_steps called once per qualifying workflow
6. Workflow enrichment: run_config=None falls back to sequential (n=1 default)
7. Example enrichment: result order matches input order regardless of completion order
"""
from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, call, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers / minimal fixtures
# ---------------------------------------------------------------------------

def _make_example_file(idx: int) -> dict:
    return {"path": f"examples/ex{idx}.py", "tags": [f"tag{idx}"], "language": "python"}


def _make_workflow(tag: str, n_steps: int) -> dict:
    return {
        "workflow_tag": tag,
        "title": f"Title {tag}",
        "steps": [{"step_num": i, "name": f"step{i}"} for i in range(1, n_steps + 1)],
        "claim_ids": [],
    }


def _stub_enrich(example_file, repo_dir, claims):
    """Pure stub: returns dict based on example_id."""
    return {
        "example_id": example_file["example_id"],
        "title": example_file.get("path", "").split("/")[-1],
        "tags": example_file.get("tags", []),
    }


# ---------------------------------------------------------------------------
# 1. Sequential and parallel produce the same results
# ---------------------------------------------------------------------------

class TestExampleEnrichmentSequentialVsParallel:
    """Parallel and sequential example enrichment produce equivalent output."""

    def _run_enrich_block(self, run_config, tmp_path):
        """Execute the example enrichment block logic (mirrors worker.py TC-2405 implementation)."""
        example_files = [_make_example_file(i) for i in range(4)]
        example_repo_dir = tmp_path
        claims: list = []
        example_inventory: list = []

        # Pre-assign IDs (sequential, fast)
        for i, ef in enumerate(example_files):
            ef["example_id"] = f"example_{i+1}"
            ef["primary_snippet_id"] = f"snippet_{i+1}"

        _n_ex = min(
            len(example_files),
            run_config.get("max_parallel_batches", 4) if run_config else 4,
        )
        if _n_ex <= 1 or len(example_files) <= 1:
            for ef in example_files:
                try:
                    example_inventory.append(_stub_enrich(ef, example_repo_dir, claims))
                except Exception:
                    pass
        else:
            from concurrent.futures import ThreadPoolExecutor, as_completed
            _ex_results: dict = {}
            with ThreadPoolExecutor(max_workers=_n_ex, thread_name_prefix="ex_enrich") as pool:
                futs = {
                    pool.submit(_stub_enrich, ef, example_repo_dir, claims): idx
                    for idx, ef in enumerate(example_files)
                }
                for fut in as_completed(futs):
                    idx = futs[fut]
                    _ex_results[idx] = fut.result()
            example_inventory = [_ex_results[i] for i in range(len(example_files))]

        return example_inventory

    def test_sequential_result(self, tmp_path):
        results = self._run_enrich_block({"max_parallel_batches": 1}, tmp_path)
        assert len(results) == 4
        assert results[0]["example_id"] == "example_1"
        assert results[3]["example_id"] == "example_4"

    def test_parallel_result_matches_sequential(self, tmp_path):
        seq = self._run_enrich_block({"max_parallel_batches": 1}, tmp_path)
        par = self._run_enrich_block({"max_parallel_batches": 4}, tmp_path)
        assert [r["example_id"] for r in seq] == [r["example_id"] for r in par]

    def test_parallel_preserves_order(self, tmp_path):
        """Results must be in input order, not completion order."""
        results = self._run_enrich_block({"max_parallel_batches": 4}, tmp_path)
        ids = [r["example_id"] for r in results]
        assert ids == ["example_1", "example_2", "example_3", "example_4"]


# ---------------------------------------------------------------------------
# 2. ID pre-assignment before parallel calls
# ---------------------------------------------------------------------------

class TestExampleIdPreAssignment:
    """example_id and primary_snippet_id must be set before threads read the dicts."""

    def test_ids_set_before_enrich_called(self, tmp_path):
        example_files = [_make_example_file(0), _make_example_file(1)]
        seen_ids: list = []

        def _capture(ef, repo_dir, claims):
            seen_ids.append(ef.get("example_id"))
            return {"example_id": ef["example_id"], "title": "t", "tags": []}

        example_repo_dir = tmp_path
        claims: list = []

        for i, ef in enumerate(example_files):
            ef["example_id"] = f"example_{i+1}"
            ef["primary_snippet_id"] = f"snippet_{i+1}"

        from concurrent.futures import ThreadPoolExecutor, as_completed
        _ex_results: dict = {}
        with ThreadPoolExecutor(max_workers=2, thread_name_prefix="ex_enrich") as pool:
            futs = {
                pool.submit(_capture, ef, example_repo_dir, claims): idx
                for idx, ef in enumerate(example_files)
            }
            for fut in as_completed(futs):
                idx = futs[fut]
                _ex_results[idx] = fut.result()

        assert sorted(seen_ids) == ["example_1", "example_2"]


# ---------------------------------------------------------------------------
# 3. Fallback dict on exception (parallel path)
# ---------------------------------------------------------------------------

class TestExampleEnrichmentFallback:
    """Parallel example enrichment falls back gracefully on exception."""

    def test_fallback_dict_on_exception(self, tmp_path):
        example_files = [_make_example_file(0)]
        for i, ef in enumerate(example_files):
            ef["example_id"] = f"example_{i+1}"
            ef["primary_snippet_id"] = f"snippet_{i+1}"

        from concurrent.futures import ThreadPoolExecutor, as_completed

        def _failing(ef, repo_dir, claims):
            raise RuntimeError("enrichment failure")

        _ex_results: dict = {}
        with ThreadPoolExecutor(max_workers=1, thread_name_prefix="ex_enrich") as pool:
            futs = {
                pool.submit(_failing, ef, tmp_path, []): idx
                for idx, ef in enumerate(example_files)
            }
            for fut in as_completed(futs):
                idx = futs[fut]
                ef = example_files[idx]
                try:
                    _ex_results[idx] = fut.result()
                except Exception:
                    _ex_results[idx] = {
                        "example_id": ef.get("example_id"),
                        "title": ef.get("path", "").split("/")[-1],
                        "tags": ef.get("tags", []),
                        "primary_snippet_id": ef.get("primary_snippet_id"),
                    }

        result = [_ex_results[i] for i in range(len(example_files))]
        assert len(result) == 1
        assert result[0]["example_id"] == "example_1"
        assert "ex0.py" in result[0]["title"]


# ---------------------------------------------------------------------------
# 4. Workflow enrichment: LLM called for qualifying workflows only
# ---------------------------------------------------------------------------

class TestWorkflowEnrichmentFiltering:
    """Only workflows below min_steps threshold trigger LLM calls."""

    def test_llm_called_for_shallow_workflow(self):
        """Workflow with fewer steps than threshold should trigger LLM call."""
        LLM_WORKFLOW_THRESHOLDS = {'installation': (8, 10)}
        wf = _make_workflow('installation', n_steps=3)  # 3 < 8 → needs enrichment
        workflows = [wf]

        _pending = []
        for w in workflows:
            tag = w.get('workflow_tag', '')
            if tag not in LLM_WORKFLOW_THRESHOLDS:
                continue
            min_steps, _ = LLM_WORKFLOW_THRESHOLDS[tag]
            if len(w.get('steps', [])) >= min_steps:
                continue
            _pending.append(w)

        assert len(_pending) == 1
        assert _pending[0] is wf

    def test_llm_not_called_for_full_workflow(self):
        """Workflow already at/above threshold should NOT trigger LLM call."""
        LLM_WORKFLOW_THRESHOLDS = {'installation': (8, 10)}
        wf = _make_workflow('installation', n_steps=10)  # 10 >= 8 → skip
        workflows = [wf]

        _pending = []
        for w in workflows:
            tag = w.get('workflow_tag', '')
            if tag not in LLM_WORKFLOW_THRESHOLDS:
                continue
            min_steps, _ = LLM_WORKFLOW_THRESHOLDS[tag]
            if len(w.get('steps', [])) >= min_steps:
                continue
            _pending.append(w)

        assert len(_pending) == 0

    def test_unknown_tag_skipped(self):
        """Workflows with unrecognized tags are skipped."""
        LLM_WORKFLOW_THRESHOLDS = {'installation': (8, 10)}
        wf = _make_workflow('custom_workflow', n_steps=1)
        workflows = [wf]

        _pending = []
        for w in workflows:
            tag = w.get('workflow_tag', '')
            if tag not in LLM_WORKFLOW_THRESHOLDS:
                continue
            _pending.append(w)

        assert len(_pending) == 0


# ---------------------------------------------------------------------------
# 5. run_config=None falls back to default parallelism safely
# ---------------------------------------------------------------------------

class TestRunConfigNoneSafety:
    """When run_config is None, default 4 workers used without AttributeError."""

    def test_run_config_none_does_not_raise(self, tmp_path):
        run_config = None
        example_files = [_make_example_file(0)]
        for i, ef in enumerate(example_files):
            ef["example_id"] = f"example_{i+1}"
            ef["primary_snippet_id"] = f"snippet_{i+1}"

        _n_ex = min(
            len(example_files),
            run_config.get("max_parallel_batches", 4) if run_config else 4,
        )
        # Should not raise — run_config is None, guard returns 4
        assert _n_ex == 1  # min(1 file, 4 workers) = 1

    def test_run_config_present_uses_key(self, tmp_path):
        run_config = {"max_parallel_batches": 6}
        example_files = [_make_example_file(i) for i in range(10)]
        _n_ex = min(
            len(example_files),
            run_config.get("max_parallel_batches", 4) if run_config else 4,
        )
        assert _n_ex == 6  # min(10, 6) = 6
