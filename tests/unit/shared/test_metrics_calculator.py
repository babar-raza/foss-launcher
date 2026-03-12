"""Unit tests for pipeline metrics calculator (TC-3794)."""
from __future__ import annotations

import json
from pathlib import Path

from launcher.shared.metrics_calculator import calculate_pipeline_metrics


def _write_events(path: Path, events: list[dict]) -> None:
    """Write events as NDJSON."""
    with open(path, "w", encoding="utf-8") as f:
        for evt in events:
            f.write(json.dumps(evt) + "\n")


class TestEmptyEvents:
    def test_missing_file(self, tmp_path):
        metrics = calculate_pipeline_metrics(tmp_path / "nonexistent.ndjson")
        assert metrics["total_duration_s"] == 0.0
        assert metrics["llm_call_count"] == 0
        assert metrics["re_run_count"] == 0

    def test_empty_file(self, tmp_path):
        events_file = tmp_path / "events.ndjson"
        events_file.write_text("")
        metrics = calculate_pipeline_metrics(events_file)
        assert metrics["total_duration_s"] == 0.0


class TestDuration:
    def test_total_duration(self, tmp_path):
        events_file = tmp_path / "events.ndjson"
        _write_events(events_file, [
            {"event_type": "run_created", "timestamp": "2026-03-07T10:00:00+00:00", "data": {}},
            {"event_type": "worker_started", "timestamp": "2026-03-07T10:00:01+00:00", "data": {"worker": "understand"}},
            {"event_type": "worker_completed", "timestamp": "2026-03-07T10:00:05+00:00", "data": {"worker": "understand"}},
            {"event_type": "worker_started", "timestamp": "2026-03-07T10:00:06+00:00", "data": {"worker": "generate"}},
            {"event_type": "worker_completed", "timestamp": "2026-03-07T10:00:10+00:00", "data": {"worker": "generate"}},
        ])
        metrics = calculate_pipeline_metrics(events_file)
        assert metrics["total_duration_s"] == 10.0

    def test_worker_durations(self, tmp_path):
        events_file = tmp_path / "events.ndjson"
        _write_events(events_file, [
            {"event_type": "run_created", "timestamp": "2026-03-07T10:00:00+00:00", "data": {}},
            {"event_type": "worker_started", "timestamp": "2026-03-07T10:00:00+00:00", "data": {"worker": "understand"}},
            {"event_type": "worker_completed", "timestamp": "2026-03-07T10:00:03+00:00", "data": {"worker": "understand"}},
        ])
        metrics = calculate_pipeline_metrics(events_file)
        assert "understand" in metrics["worker_durations"]
        assert metrics["worker_durations"]["understand"] == 3000.0  # ms


class TestLLMMetrics:
    def test_llm_call_count_and_tokens(self, tmp_path):
        events_file = tmp_path / "events.ndjson"
        _write_events(events_file, [
            {"event_type": "run_created", "timestamp": "2026-03-07T10:00:00+00:00", "data": {}},
            {
                "event_type": "llm_call_completed",
                "timestamp": "2026-03-07T10:00:01+00:00",
                "data": {"token_usage": {"total_tokens": 1500}},
            },
            {
                "event_type": "llm_call_completed",
                "timestamp": "2026-03-07T10:00:02+00:00",
                "data": {"token_usage": {"total_tokens": 2000}},
            },
        ])
        metrics = calculate_pipeline_metrics(events_file)
        assert metrics["llm_call_count"] == 2
        assert metrics["llm_total_tokens"] == 3500


class TestGateMetrics:
    def test_gate_pass_rate(self, tmp_path):
        events_file = tmp_path / "events.ndjson"
        _write_events(events_file, [
            {"event_type": "run_created", "timestamp": "2026-03-07T10:00:00+00:00", "data": {}},
            {"event_type": "gate_executed", "timestamp": "2026-03-07T10:00:01+00:00", "data": {"gate_id": "g1", "passed": True}},
            {"event_type": "gate_executed", "timestamp": "2026-03-07T10:00:02+00:00", "data": {"gate_id": "g2", "passed": True}},
            {"event_type": "gate_executed", "timestamp": "2026-03-07T10:00:03+00:00", "data": {"gate_id": "g3", "passed": False}},
        ])
        metrics = calculate_pipeline_metrics(events_file)
        assert metrics["gate_pass_rate"] == round(2 / 3, 4)

    def test_no_gates(self, tmp_path):
        events_file = tmp_path / "events.ndjson"
        _write_events(events_file, [
            {"event_type": "run_created", "timestamp": "2026-03-07T10:00:00+00:00", "data": {}},
        ])
        metrics = calculate_pipeline_metrics(events_file)
        assert metrics["gate_pass_rate"] == 0.0


class TestReRunCount:
    def test_re_run_count(self, tmp_path):
        events_file = tmp_path / "events.ndjson"
        _write_events(events_file, [
            {"event_type": "run_created", "timestamp": "2026-03-07T10:00:00+00:00", "data": {}},
            {"event_type": "re_run_triggered", "timestamp": "2026-03-07T10:00:01+00:00", "data": {}},
            {"event_type": "re_run_triggered", "timestamp": "2026-03-07T10:00:02+00:00", "data": {}},
        ])
        metrics = calculate_pipeline_metrics(events_file)
        assert metrics["re_run_count"] == 2


class TestAllMetricsKeys:
    def test_all_8_keys_present(self, tmp_path):
        events_file = tmp_path / "events.ndjson"
        events_file.write_text("")
        metrics = calculate_pipeline_metrics(events_file)
        expected_keys = {
            "total_duration_s", "worker_durations", "llm_call_count",
            "llm_total_tokens", "fallback_count", "cache_hit_rate",
            "gate_pass_rate", "re_run_count",
        }
        assert set(metrics.keys()) == expected_keys
