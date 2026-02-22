"""Tests for Plan A3: LLM-synthesized claim validation gate."""
from launch.workers.w2_facts_builder.worker import _validate_synthesized_claims


def _make_claim(text, kind="feature", source_type="extracted", citations=None, confidence="high"):
    """Helper to create a claim dict."""
    return {
        "claim_id": f"test_{abs(hash(text)) % 10**8}",
        "claim_text": text,
        "claim_kind": kind,
        "source_type": source_type,
        "truth_status": "fact" if source_type != "llm_synthesized" else "inference",
        "confidence": confidence,
        "citations": citations or [],
    }


class TestValidateSynthesizedClaims:
    """Test the synthesized claim validation gate."""

    def test_preserves_grounded_claims(self):
        """Grounded claims (with real source_type) are never filtered."""
        validate = _validate_synthesized_claims
        grounded = [
            _make_claim("Feature A", source_type="source_code", citations=[{"path": "a.py"}]),
            _make_claim("Feature B", source_type="documentation", citations=[{"path": "b.md"}]),
        ]
        result = validate(grounded, grounded_count=2)
        assert len(result) == 2

    def test_caps_synthesized_per_kind(self):
        """Synthesized claims are capped at max(5, grounded * 0.2) per kind."""
        validate = _validate_synthesized_claims
        grounded = [_make_claim(f"Grounded {i}") for i in range(10)]
        # 10 grounded → cap = max(5, 2) = 5 per kind
        synthesized = [
            _make_claim(f"FAQ {i}", kind="faq", source_type="llm_synthesized")
            for i in range(10)
        ]
        result = validate(grounded + synthesized, grounded_count=10)
        faq_claims = [c for c in result if c["claim_kind"] == "faq"]
        assert len(faq_claims) <= 5

    def test_rejects_fabricated_metrics(self):
        """Claims with fabricated metrics (e.g., '10x faster') and no citations are dropped."""
        validate = _validate_synthesized_claims
        grounded = [_make_claim("Feature A")]
        fabricated = [
            _make_claim(
                "Processing is 10x faster for large files",
                kind="performance",
                source_type="llm_synthesized",
            ),
            _make_claim(
                "AssetInfo loading takes approximately 1ms per 1KB of metadata",
                kind="performance",
                source_type="llm_synthesized",
            ),
        ]
        result = validate(grounded + fabricated, grounded_count=1)
        perf_claims = [c for c in result if c["claim_kind"] == "performance"]
        assert len(perf_claims) == 0

    def test_forces_low_confidence(self):
        """All retained synthesized claims get confidence='low'."""
        validate = _validate_synthesized_claims
        grounded = [_make_claim("Feature A")]
        synthesized = [
            _make_claim("FAQ Q1", kind="faq", source_type="llm_synthesized", confidence="medium"),
        ]
        result = validate(grounded + synthesized, grounded_count=1)
        synth_result = [c for c in result if c["source_type"] == "llm_synthesized"]
        assert all(c["confidence"] == "low" for c in synth_result)

    def test_no_synthesized_returns_unchanged(self):
        """No synthesized claims → returns all claims unchanged."""
        validate = _validate_synthesized_claims
        grounded = [_make_claim("Feature A"), _make_claim("Feature B")]
        result = validate(grounded, grounded_count=2)
        assert len(result) == 2

    def test_large_grounded_allows_more_synthesized(self):
        """With 100 grounded, cap per kind = max(5, 20) = 20."""
        validate = _validate_synthesized_claims
        grounded = [_make_claim(f"Grounded {i}") for i in range(100)]
        synthesized = [
            _make_claim(f"Best practice {i}", kind="best_practice", source_type="llm_synthesized")
            for i in range(25)
        ]
        result = validate(grounded + synthesized, grounded_count=100)
        bp_claims = [c for c in result if c["claim_kind"] == "best_practice"]
        assert len(bp_claims) == 20  # cap = max(5, 100*0.2) = 20
