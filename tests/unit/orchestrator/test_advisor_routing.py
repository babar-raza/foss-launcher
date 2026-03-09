"""TC-3919: Tests for advisor routing in the LangGraph pipeline."""
import pytest
from langgraph.constants import END

from launcher.orchestrator.graph_builder import (
    _make_post_evaluate_router,
    _make_advisor_route,
)


# ---------------------------------------------------------------------------
# TestPostEvaluateRouter
# ---------------------------------------------------------------------------

class TestPostEvaluateRouter:

    def test_go_routes_to_publish(self):
        router = _make_post_evaluate_router(2)
        state = {"verdict": "GO", "re_run_count": 0}
        assert router(state) == "publish"

    def test_no_go_below_ceiling_routes_to_advisor(self):
        router = _make_post_evaluate_router(2)
        state = {"verdict": "NO_GO", "re_run_count": 0}
        assert router(state) == "__advisor__"

    def test_no_go_at_ceiling_routes_to_end(self):
        router = _make_post_evaluate_router(2)
        state = {"verdict": "NO_GO", "re_run_count": 2}
        assert router(state) == END

    def test_max_re_runs_zero_always_end(self):
        router = _make_post_evaluate_router(0)
        state = {"verdict": "NO_GO", "re_run_count": 0}
        assert router(state) == END


# ---------------------------------------------------------------------------
# TestAdvisorRoute
# ---------------------------------------------------------------------------

class TestAdvisorRoute:

    def test_heal_generate_routes_to_re_run(self):
        route = _make_advisor_route({"publish": "publish_worker"})
        state = {"advisor_decision": {"routing": "heal_generate"}}
        assert route(state) == "__re_run__"

    def test_publish_with_publish_worker(self):
        route = _make_advisor_route({"publish": "publish_worker"})
        state = {"advisor_decision": {"routing": "publish"}}
        assert route(state) == "publish"

    def test_publish_without_publish_worker(self):
        route = _make_advisor_route({})  # no publish worker
        state = {"advisor_decision": {"routing": "publish"}}
        assert route(state) == END

    def test_stop_routes_to_end(self):
        route = _make_advisor_route({"publish": "p"})
        state = {"advisor_decision": {"routing": "stop"}}
        assert route(state) == END

    def test_empty_advisor_decision_routes_to_end(self):
        route = _make_advisor_route({"publish": "p"})
        state = {"advisor_decision": {}}
        assert route(state) == END


# ---------------------------------------------------------------------------
# TestPipelineYamlReRunConfig (reads actual file)
# ---------------------------------------------------------------------------

class TestPipelineYamlReRunConfig:

    def _load_pipeline_yaml(self):
        import yaml
        from pathlib import Path
        p = Path("configs/pipeline.yaml")
        return yaml.safe_load(p.read_text(encoding="utf-8"))

    def test_re_run_targets_is_generate_only(self):
        data = self._load_pipeline_yaml()
        workers = data.get("pipeline", [])
        evaluate_entry = next(
            (w for w in workers if w.get("worker") == "evaluate"), None
        )
        assert evaluate_entry is not None, "evaluate worker not found in pipeline.yaml"
        assert evaluate_entry.get("re_run_targets") == ["generate"]

    def test_max_re_runs_is_two(self):
        data = self._load_pipeline_yaml()
        workers = data.get("pipeline", [])
        evaluate_entry = next(
            (w for w in workers if w.get("worker") == "evaluate"), None
        )
        assert evaluate_entry is not None
        assert evaluate_entry.get("max_re_runs") == 2
