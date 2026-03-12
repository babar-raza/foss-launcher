"""Unit tests for cache telemetry (TC-3791)."""
from __future__ import annotations

import logging
import threading

from launcher.shared.cache_telemetry import (
    CACHE_OUTCOMES,
    CACHE_REASONS,
    CacheEvent,
    emit_cache_event,
    get_cache_stats,
    reset_cache_stats,
)


class TestConstants:
    def test_cache_outcomes_contains_expected(self):
        assert CACHE_OUTCOMES == frozenset({"hit", "miss", "bypass", "saved"})

    def test_cache_reasons_contains_expected(self):
        assert CACHE_REASONS == frozenset(
            {"ok", "not_found", "corrupt", "nondet", "fallback", "disabled"}
        )


class TestCacheEvent:
    def test_basic_construction(self):
        evt = CacheEvent(outcome="hit", reason="ok")
        assert evt.outcome == "hit"
        assert evt.reason == "ok"
        assert evt.model == ""
        assert evt.key_prefix == ""
        assert evt.call_id == ""
        assert evt.duration_ms == 0
        assert evt.extra == {}

    def test_full_construction(self):
        evt = CacheEvent(
            outcome="miss",
            reason="not_found",
            model="qwen3-next",
            key_prefix="a1b2c3d4",
            call_id="test_001",
            duration_ms=42,
            extra={"custom": "value"},
        )
        assert evt.model == "qwen3-next"
        assert evt.duration_ms == 42
        assert evt.extra == {"custom": "value"}


class TestCounters:
    def setup_method(self):
        reset_cache_stats()

    def test_initial_stats_are_zero(self):
        stats = get_cache_stats()
        assert all(v == 0 for v in stats.values())
        assert set(stats.keys()) == {"bypass", "hit", "miss", "saved"}

    def test_emit_increments_counter(self):
        log = logging.getLogger("test")
        emit_cache_event(log, "hit", "ok")
        stats = get_cache_stats()
        assert stats["hit"] == 1
        assert stats["miss"] == 0

    def test_multiple_emits(self):
        log = logging.getLogger("test")
        emit_cache_event(log, "hit", "ok")
        emit_cache_event(log, "hit", "ok")
        emit_cache_event(log, "miss", "not_found")
        stats = get_cache_stats()
        assert stats["hit"] == 2
        assert stats["miss"] == 1

    def test_reset_zeros_all(self):
        log = logging.getLogger("test")
        emit_cache_event(log, "hit", "ok")
        emit_cache_event(log, "saved", "ok")
        reset_cache_stats()
        stats = get_cache_stats()
        assert all(v == 0 for v in stats.values())

    def test_get_stats_returns_copy(self):
        stats1 = get_cache_stats()
        stats1["hit"] = 999
        stats2 = get_cache_stats()
        assert stats2["hit"] == 0  # original unchanged

    def test_unknown_outcome_does_not_crash(self):
        log = logging.getLogger("test")
        emit_cache_event(log, "unknown_outcome", "ok")
        stats = get_cache_stats()
        assert "unknown_outcome" not in stats


class TestNonFatal:
    def setup_method(self):
        reset_cache_stats()

    def test_broken_logger_does_not_crash(self):
        class BrokenLogger:
            def debug(self, *a, **kw):
                raise RuntimeError("logger exploded")

        emit_cache_event(BrokenLogger(), "hit", "ok")
        # Counter still incremented (before logger call)
        stats = get_cache_stats()
        assert stats["hit"] == 1

    def test_none_logger_does_not_crash(self):
        emit_cache_event(None, "miss", "not_found")
        # Should not raise


class TestThreadSafety:
    def setup_method(self):
        reset_cache_stats()

    def test_concurrent_emits(self):
        log = logging.getLogger("test")
        n_threads = 10
        n_per_thread = 100
        barrier = threading.Barrier(n_threads)

        def worker():
            barrier.wait()
            for _ in range(n_per_thread):
                emit_cache_event(log, "hit", "ok")

        threads = [threading.Thread(target=worker) for _ in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        stats = get_cache_stats()
        assert stats["hit"] == n_threads * n_per_thread


class TestSignatureCompat:
    """Verify the function signature matches what llm_provider.py calls."""

    def setup_method(self):
        reset_cache_stats()

    def test_full_keyword_call(self):
        log = logging.getLogger("test")
        emit_cache_event(
            log, "hit", "ok",
            key_prefix="a1b2c3d4",
            call_id="sect_write_001",
            model="gemma3:12b",
            duration_ms=2,
        )
        assert get_cache_stats()["hit"] == 1

    def test_minimal_call(self):
        log = logging.getLogger("test")
        emit_cache_event(log, "miss", "not_found")
        assert get_cache_stats()["miss"] == 1

    def test_extra_kwargs(self):
        log = logging.getLogger("test")
        emit_cache_event(log, "bypass", "nondet", custom_field="value")
        assert get_cache_stats()["bypass"] == 1
