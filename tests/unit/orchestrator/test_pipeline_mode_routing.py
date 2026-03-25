"""Unit tests for _derive_effective_stop_after() — SR-01 (TC-5168).

Tests the pipeline_mode → stop_after routing logic extracted from execute_run().
All tests are pure unit tests (no I/O, no async, no mocking required).
"""
from __future__ import annotations

from launcher.models.run_config import RunConfig
from launcher.orchestrator.run_loop import _derive_effective_stop_after


def _cfg(pipeline_mode: str = "create") -> RunConfig:
    return RunConfig(
        family="3d",
        platform="python",
        repo_url="https://example.com",
        pipeline_mode=pipeline_mode,
    )


# ---------------------------------------------------------------------------
# Happy path — verify mode derives stop_after="verify"
# ---------------------------------------------------------------------------


def test_verify_mode_derives_stop_after_verify() -> None:
    """pipeline_mode=verify with no explicit stop_after → 'verify'."""
    result = _derive_effective_stop_after(_cfg("verify"), stop_after="")
    assert result == "verify"


# ---------------------------------------------------------------------------
# Happy path — maintain mode passes stop_after="" (full pipeline)
# ---------------------------------------------------------------------------


def test_maintain_mode_does_not_set_stop_after() -> None:
    """pipeline_mode=maintain → stop_after unchanged (empty = full run)."""
    result = _derive_effective_stop_after(_cfg("maintain"), stop_after="")
    assert result == ""


# ---------------------------------------------------------------------------
# Happy path — create mode passes stop_after="" (full pipeline)
# ---------------------------------------------------------------------------


def test_create_mode_does_not_set_stop_after() -> None:
    """pipeline_mode=create (default) → stop_after unchanged (empty = full run)."""
    result = _derive_effective_stop_after(_cfg("create"), stop_after="")
    assert result == ""


# ---------------------------------------------------------------------------
# Regression — explicit stop_after wins over pipeline_mode
# ---------------------------------------------------------------------------


def test_explicit_stop_after_takes_precedence() -> None:
    """Explicit stop_after='understand' with pipeline_mode='verify' → 'understand'."""
    result = _derive_effective_stop_after(_cfg("verify"), stop_after="understand")
    assert result == "understand"


# ---------------------------------------------------------------------------
# TC-5175 — seed mode derives stop_after="intake"
# ---------------------------------------------------------------------------


def test_seed_mode_derives_stop_after_intake() -> None:
    """TC-5175: pipeline_mode=seed with no explicit stop_after → 'intake'."""
    result = _derive_effective_stop_after(_cfg("seed"), stop_after="")
    assert result == "intake"


def test_seed_mode_explicit_stop_after_wins() -> None:
    """TC-5175: explicit stop_after wins even in seed mode."""
    result = _derive_effective_stop_after(_cfg("seed"), stop_after="understand")
    assert result == "understand"
