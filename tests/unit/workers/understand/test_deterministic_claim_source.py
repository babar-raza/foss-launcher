"""Tests for claim_source tagging on direct Claim() constructors — IUH-01."""
from __future__ import annotations
from launcher.workers.understand.extract._deterministic import _extract_error_messages


class TestErrorMessageClaimSource:
    def test_raise_statement_claims_tagged_deterministic(self, tmp_path):
        """Claims from raise statements must have claim_source='deterministic'."""
        src_file = tmp_path / "example.py"
        src_file.write_text(
            'class Processor:\n'
            '    def run(self):\n'
            '        raise ValueError("Input must not be None")\n',
            encoding="utf-8",
        )
        code = src_file.read_text(encoding="utf-8")
        claims = _extract_error_messages(code, "example.py")
        assert claims, "Expected at least one claim from raise statement"
        for c in claims:
            assert c.claim_source == "deterministic", (
                f"Expected claim_source='deterministic', got {c.claim_source!r} for {c.text!r}"
            )

    def test_custom_error_class_claims_tagged_deterministic(self, tmp_path):
        """Claims from custom Error class definitions must have claim_source='deterministic'."""
        src_file = tmp_path / "errors.py"
        src_file.write_text(
            'class ProcessingError(Exception):\n'
            '    """Raised when processing fails due to invalid input."""\n'
            '    pass\n',
            encoding="utf-8",
        )
        code = src_file.read_text(encoding="utf-8")
        claims = _extract_error_messages(code, "errors.py")
        assert claims, "Expected at least one claim from error class"
        for c in claims:
            assert c.claim_source == "deterministic", (
                f"Expected claim_source='deterministic', got {c.claim_source!r}"
            )

    def test_no_claims_from_empty_file(self):
        """Empty source produces no claims."""
        claims = _extract_error_messages("", "empty.py")
        assert claims == []

    def test_no_claim_source_llm_on_deterministic_path(self, tmp_path):
        """No deterministic Claim() constructor should carry claim_source='llm'."""
        code = (
            'raise RuntimeError("critical system error occurred")\n'
            'class DataError(Exception): pass\n'
        )
        claims = _extract_error_messages(code, "module.py")
        for c in claims:
            assert c.claim_source != "llm", (
                f"Deterministic claim must not be tagged 'llm': {c.text!r}"
            )
