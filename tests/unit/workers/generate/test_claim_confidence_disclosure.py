"""TC-5160: Tests for claim confidence tier disclosure in _format_claims()."""
from __future__ import annotations

import pytest

from launcher.models.claims import Claim, EvidenceAnchor
from launcher.workers.generate.section_prompt import _confidence_tag, _format_claims


def _make_claim(
    claim_id: str = "CLM-001",
    kind: str = "feature",
    text: str = "Test claim text",
    confidence: float = 1.0,
    claim_source: str = "docstring",
    evidence: list | None = None,
) -> Claim:
    return Claim(
        claim_id=claim_id,
        text=text,
        kind=kind,
        confidence=confidence,
        claim_source=claim_source,
        evidence=evidence or [],
    )


# ─── _confidence_tag() ───────────────────────────────────────────────────────

class TestConfidenceTag:
    def test_docstring_claim_gets_ast_tag(self):
        claim = _make_claim(claim_source="docstring", confidence=1.0)
        assert _confidence_tag(claim) == "[AST]"

    def test_llm_claim_gets_ver_tag(self):
        claim = _make_claim(claim_source="llm", confidence=0.75)
        assert _confidence_tag(claim) == "[VER]"

    def test_deterministic_claim_gets_det_tag(self):
        claim = _make_claim(claim_source="deterministic", confidence=0.5)
        assert _confidence_tag(claim) == "[DET]"

    def test_docstring_with_sub_1_confidence_gets_ver_tag(self):
        # docstring source but confidence slightly below 1.0 → [VER] not [AST]
        claim = _make_claim(claim_source="docstring", confidence=0.9)
        assert _confidence_tag(claim) == "[VER]"

    def test_missing_claim_source_defaults_to_det(self):
        """Claims without claim_source field (old bundles) get conservative [DET] tag."""
        claim = _make_claim(claim_source="deterministic", confidence=0.5)
        # Simulate missing attribute via object without claim_source
        class _MinimalClaim:
            confidence = 0.5
        assert _confidence_tag(_MinimalClaim()) == "[DET]"  # type: ignore[arg-type]

    def test_high_confidence_llm_fallback_gets_det(self):
        """llm_fallback source at 0.5 edge case → [DET] not [VER]."""
        claim = _make_claim(claim_source="llm_fallback", confidence=0.5)
        assert _confidence_tag(claim) == "[DET]"


# ─── _format_claims() ────────────────────────────────────────────────────────

class TestFormatClaims:
    def test_docstring_claim_has_ast_tag_in_output(self):
        claim = _make_claim(claim_id="CLM-001", claim_source="docstring", confidence=1.0)
        result = _format_claims([claim])
        assert "[CLM-001][AST]" in result

    def test_llm_claim_has_ver_tag_in_output(self):
        claim = _make_claim(claim_id="CLM-002", claim_source="llm", confidence=0.75)
        result = _format_claims([claim])
        assert "[CLM-002][VER]" in result

    def test_deterministic_claim_has_det_tag_in_output(self):
        claim = _make_claim(claim_id="CLM-003", claim_source="deterministic", confidence=0.5)
        result = _format_claims([claim])
        assert "[CLM-003][DET]" in result

    def test_empty_list_returns_empty_string(self):
        assert _format_claims([]) == ""

    def test_evidence_source_line_still_present(self):
        """TC-3876 evidence Source line must still appear alongside the new tag."""
        anchor = EvidenceAnchor(source_file="src/workbook.py", line_start=42, snippet="def save(self)")
        claim = _make_claim(
            claim_id="CLM-010",
            text="Different claim text",
            evidence=[anchor],
        )
        result = _format_claims([claim])
        assert "[CLM-010][AST]" in result
        assert "Source: src/workbook.py:42" in result

    def test_tag_does_not_break_existing_format(self):
        """Basic structure: - [CLM-001][AST] (kind): text."""
        claim = _make_claim(claim_id="CLM-001", kind="api", text="Some text")
        result = _format_claims([claim])
        assert result.startswith("- [CLM-001][AST] (api): Some text")

    def test_multiple_claims_each_have_correct_tag(self):
        claims = [
            _make_claim("CLM-A", claim_source="docstring", confidence=1.0),
            _make_claim("CLM-B", claim_source="llm", confidence=0.75),
            _make_claim("CLM-C", claim_source="deterministic", confidence=0.5),
        ]
        result = _format_claims(claims)
        assert "[CLM-A][AST]" in result
        assert "[CLM-B][VER]" in result
        assert "[CLM-C][DET]" in result
