"""Regression guard for TC-FIX-02: deterministic claim confidence must be 0.65.

These tests ensure the TC-4225 confidence threshold (>= 0.5) is never reintroduced
as a fragile boundary for deterministic claims.  If deterministic confidence ever
drops back to 0.50, deterministic claims would sit at the exact cut-off and any
secondary downgrade would cause a near-total claim collapse (the Java regression).
"""
from __future__ import annotations

import pytest

from launcher.workers.understand.extract._validation import (
    _CONFIDENCE_BY_SOURCE,
)

# TC-4225 filter threshold — claims below this are dropped
_TC4225_THRESHOLD = 0.5


class TestLlmCorroboratedConfidenceValue:
    """TC-UND-210: llm_corroborated must be 0.85 (between docstring=1.0 and llm=0.75)."""

    def test_llm_corroborated_value(self) -> None:
        assert _CONFIDENCE_BY_SOURCE["llm_corroborated"] == 0.85

    def test_llm_corroborated_between_docstring_and_llm(self) -> None:
        assert (
            _CONFIDENCE_BY_SOURCE["docstring"]
            > _CONFIDENCE_BY_SOURCE["llm_corroborated"]
            > _CONFIDENCE_BY_SOURCE["llm"]
        )


class TestDeterministicConfidenceValue:
    """TC-FIX-02 regression guard: deterministic confidence must be 0.65."""

    def test_deterministic_confidence_is_0_65(self):
        """_CONFIDENCE_BY_SOURCE['deterministic'] must equal 0.65 (TC-FIX-02)."""
        assert _CONFIDENCE_BY_SOURCE["deterministic"] == 0.65, (
            "TC-FIX-02 regression: deterministic confidence was raised from 0.50 to 0.65 "
            "to give margin above the TC-4225 threshold. Reverting it causes Java claim collapse."
        )

    def test_deterministic_confidence_above_tc4225_threshold(self):
        """Deterministic confidence must be strictly above the TC-4225 drop threshold."""
        det_conf = _CONFIDENCE_BY_SOURCE["deterministic"]
        assert det_conf > _TC4225_THRESHOLD, (
            f"deterministic confidence {det_conf} must be > TC-4225 threshold {_TC4225_THRESHOLD}. "
            "Claims at exactly 0.50 survive TC-4225 but have zero margin against secondary downgrades."
        )

    def test_all_non_fallback_sources_above_tc4225_threshold(self):
        """All claim sources except llm_fallback must be above TC-4225 threshold."""
        for source, conf in _CONFIDENCE_BY_SOURCE.items():
            if source == "llm_fallback":
                # llm_fallback is intentionally below threshold — it gets dropped
                assert conf < _TC4225_THRESHOLD, (
                    f"llm_fallback confidence {conf} should be below TC-4225 threshold {_TC4225_THRESHOLD}"
                )
            else:
                assert conf > _TC4225_THRESHOLD, (
                    f"source={source!r} confidence {conf} must be > TC-4225 threshold {_TC4225_THRESHOLD}"
                )

    def test_confidence_ordering_is_correct(self):
        """docstring > llm > deterministic > llm_fallback."""
        assert _CONFIDENCE_BY_SOURCE["docstring"] > _CONFIDENCE_BY_SOURCE["llm"]
        assert _CONFIDENCE_BY_SOURCE["llm"] > _CONFIDENCE_BY_SOURCE["deterministic"]
        assert _CONFIDENCE_BY_SOURCE["deterministic"] > _CONFIDENCE_BY_SOURCE["llm_fallback"]

    def test_deterministic_confidence_margin_from_threshold(self):
        """Deterministic confidence must have at least 0.10 margin above TC-4225 threshold.

        A 0.10 margin means secondary downgrades (e.g. weak-evidence filter) do not
        instantly push deterministic claims below the drop boundary.
        """
        margin = _CONFIDENCE_BY_SOURCE["deterministic"] - _TC4225_THRESHOLD
        assert margin >= 0.10, (
            f"deterministic confidence margin from TC-4225 threshold is {margin:.2f} — "
            "must be >= 0.10 to survive secondary downgrades"
        )
