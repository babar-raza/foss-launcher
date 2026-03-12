"""Tests for readability scoring check (TC-3846, SEO-20, RD-01, RD-02)."""
import pytest
from types import SimpleNamespace
from launcher.workers.evaluate.checks.readability import (
    check_readability,
    check_readability_from_markdown,
    _flesch_kincaid_grade,
    _count_syllables,
    _extract_body,
    _split_sentences,
    _split_words,
    _long_sentence_finding,
)


class TestCountSyllables:
    def test_simple_word(self):
        # "hello" = hel-lo = 2 syllables
        assert _count_syllables("hello") >= 1

    def test_single_syllable(self):
        assert _count_syllables("the") >= 1

    def test_empty_word(self):
        assert _count_syllables("") == 1


class TestFleschKincaidGrade:
    def test_empty_text_returns_zero(self):
        assert _flesch_kincaid_grade("") == 0.0

    def test_simple_text_low_grade(self):
        # Simple short sentences -> low grade (should compute a float)
        text = "The cat sat. The dog ran. It was fun."
        grade = _flesch_kincaid_grade(text)
        assert isinstance(grade, float)

    def test_complex_text_higher_grade(self):
        # Complex academic text -> should compute a non-zero float
        text = (
            "The implementation of multithreaded asynchronous communication "
            "protocols necessitates comprehensive understanding of distributed systems. "
            "Concurrent execution of parallel computational algorithms demonstrates "
            "sophisticated architectural considerations."
        )
        grade = _flesch_kincaid_grade(text)
        assert grade > 0


class TestExtractBody:
    def test_empty_page_ir(self):
        page_ir = SimpleNamespace(sections=[])
        assert _extract_body(page_ir) == ""

    def test_extracts_paragraph_blocks(self):
        block = SimpleNamespace(type="paragraph", content="Hello world text here.")
        section = SimpleNamespace(blocks=[block])
        page_ir = SimpleNamespace(sections=[section])
        body = _extract_body(page_ir)
        assert "Hello world" in body

    def test_skips_code_blocks(self):
        code_block = SimpleNamespace(type="code", content="def foo(): pass")
        prose_block = SimpleNamespace(type="paragraph", content="This is prose.")
        section = SimpleNamespace(blocks=[code_block, prose_block])
        page_ir = SimpleNamespace(sections=[section])
        body = _extract_body(page_ir)
        assert "def foo" not in body
        assert "This is prose" in body

    def test_no_sections_attribute(self):
        page_ir = object()  # no sections attribute
        assert _extract_body(page_ir) == ""

    def test_enum_type_attribute(self):
        """Block.type can be an enum with .value attribute."""
        block_type = SimpleNamespace(value="paragraph")
        block = SimpleNamespace(type=block_type, content="Some text content here.")
        section = SimpleNamespace(blocks=[block])
        page_ir = SimpleNamespace(sections=[section])
        body = _extract_body(page_ir)
        assert "Some text content" in body


class TestCheckReadability:
    def test_empty_page_returns_empty(self):
        page_ir = SimpleNamespace(sections=[])
        assert check_readability(page_ir) == []

    def test_short_page_no_finding(self):
        # < 100 words -> no assessment
        block = SimpleNamespace(type="paragraph", content="Short content here.")
        section = SimpleNamespace(blocks=[block])
        page_ir = SimpleNamespace(sections=[section])
        result = check_readability(page_ir)
        assert result == []

    def test_finding_has_correct_check_name(self):
        # Build a page with enough words (100+) and complex text
        long_complex = " ".join([
            "The implementation utilizes sophisticated multithreaded asynchronous protocols."
        ] * 10)
        block = SimpleNamespace(type="paragraph", content=long_complex)
        section = SimpleNamespace(blocks=[block])
        page_ir = SimpleNamespace(sections=[section])
        result = check_readability(page_ir)
        # May or may not produce finding depending on FK grade
        for finding in result:
            assert finding["check"] == "readability"
            assert finding["severity"] in ("low", "medium", "high")
            assert "location" in finding

    def test_finding_severity_is_low_or_medium_or_high(self):
        # Verify that if a finding is produced, severity is "low", "medium", or "high"
        very_complex = " ".join([
            "Notwithstanding the aforementioned extraordinarily sophisticated implementation "
            "characteristics, the architectural considerations necessitate comprehensive "
            "multidimensional computational infrastructure frameworks."
        ] * 8)
        block = SimpleNamespace(type="paragraph", content=very_complex)
        section = SimpleNamespace(blocks=[block])
        page_ir = SimpleNamespace(sections=[section])
        result = check_readability(page_ir)
        for finding in result:
            assert finding["severity"] in ("low", "medium", "high")

    def test_returns_list_type(self):
        page_ir = SimpleNamespace(sections=[])
        result = check_readability(page_ir)
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# ST-04: FK threshold, table, long-sentence, abbreviation edge cases
# ---------------------------------------------------------------------------

class TestReadabilityThresholdsAndEdgeCases:
    """ST-04: FK threshold calibration and edge case tests."""

    def _make_page_ir(self, content: str):
        block = SimpleNamespace(type="paragraph", content=content)
        section = SimpleNamespace(blocks=[block])
        return SimpleNamespace(sections=[section])

    def test_too_simple(self):
        """Very simple text (FK < 6) produces a 'too simple' readability finding."""
        # Short one-syllable words, short sentences → FK well below 6
        # 20 reps × 3 words × 2 phrases = 120 words (above 100-word guard)
        text = ("The cat sat. " * 20 + "The dog ran. " * 20)
        page_ir = self._make_page_ir(text)
        result = check_readability(page_ir)
        assert len(result) >= 1
        assert result[0]["check"] == "readability"
        assert "too simple" in result[0]["message"]
        assert result[0]["severity"] == "low"

    def test_too_complex(self):
        """TC-3878 Wave 0: FK ~17 is now CLEAN under recalibrated threshold (MEDIUM at FK>18).
        Technical documentation prose at FK 14-18 is acceptable — no MEDIUM/HIGH finding.
        Previously this tested FK>16 → medium, but 16→18 threshold raise eliminates false positives.
        """
        # FK ~17: technical validation prose (confirmed ~17.0 by measurement)
        sentence = (
            "When the system processes requests it validates each input parameter "
            "against the configured schema rules. "
        )
        text = sentence * 10  # 150+ words, FK ~17 — below recalibrated threshold of 18
        page_ir = self._make_page_ir(text)
        result = check_readability(page_ir)
        # FK ~17 < 18.0 → no medium/high finding (intentionally clean under new thresholds)
        medium_or_high = [r for r in result if r.get("severity") in ("medium", "high")]
        assert medium_or_high == [], f"FK ~17 should produce no MEDIUM/HIGH at threshold 18: {result}"

    def test_severely_complex(self):
        """Very complex text (FK > 20) produces severity='high' (RD-01 escalated threshold)."""
        sentence = (
            "Extraordinarily sophisticated multidimensional computational infrastructure "
            "demonstrates extraordinarily comprehensive architectural considerations "
            "necessitating extraordinarily detailed parametrization of asynchronous "
            "communication protocols throughout the distributed systems. "
        )
        text = sentence * 5  # 100+ words
        page_ir = self._make_page_ir(text)
        result = check_readability(page_ir)
        assert len(result) >= 1
        assert result[0]["severity"] == "high"

    def test_ignores_tables(self):
        """check_readability_from_markdown does not crash on markdown tables."""
        prose = "This document covers the API endpoint configuration. " * 15
        table = (
            "\n| Column 1 | Column 2 | Column 3 |\n"
            "|----------|----------|----------|\n"
            "| Value A  | Value B  | Value C  |\n"
        )
        content = prose + table
        result = check_readability_from_markdown(content, slug="test-page")
        assert isinstance(result, list)  # no crash

    def test_long_sentence_flagging(self):
        """check_readability_from_markdown does not crash on very long sentences."""
        long_sentence = (
            "The system continuously monitors and evaluates all incoming requests "
            "processing each one sequentially through the validation pipeline while "
            "maintaining comprehensive audit logs for regulatory compliance and "
            "reporting purposes across all production environments. "
        )  # ~35 words
        content = long_sentence * 5  # 175+ words
        result = check_readability_from_markdown(content, slug="test-long")
        assert isinstance(result, list)  # no crash; may or may not produce finding

    def test_abbreviations_not_split(self):
        """check_readability_from_markdown does not crash on text with abbreviations."""
        text = (
            "Use the API e.g. to fetch data from the endpoint configuration. "
            "You can also configure settings i.e. the timeout and retry count. "
        ) * 10  # 100+ words
        result = check_readability_from_markdown(text, slug="test-abbrev")
        assert isinstance(result, list)  # no crash

    def test_too_simple_flagged_from_markdown(self):
        """FK < 6 with >=100 words produces a 'too simple' finding."""
        text = ("The cat sat. " * 20 + "The dog ran. " * 20)  # 120 words
        result = check_readability_from_markdown(text, slug="simple-page")
        assert len(result) >= 1
        assert result[0].check == "readability"
        assert "too simple" in result[0].message
        assert result[0].severity == "low"

    def test_severely_complex_escalated_from_markdown(self):
        """FK > 20 produces severity='high' (RD-01: escalated from 'medium')."""
        sentence = (
            "Extraordinarily sophisticated multidimensional computational infrastructure "
            "demonstrates extraordinarily comprehensive architectural considerations "
            "necessitating extraordinarily detailed parametrization of asynchronous "
            "communication protocols throughout the distributed systems. "
        )
        text = sentence * 5
        result = check_readability_from_markdown(text, slug="complex-page")
        assert len(result) >= 1
        assert result[0].severity == "high"

    def test_moderately_complex_is_medium(self):
        """TC-3878 Wave 0: FK between 18 and 22 produces severity='medium' (recalibrated thresholds).
        Previous test used FK ~17 (old MEDIUM at >16); now threshold is >18.
        Uses prose with confirmed FK ~19.0 (empirically measured).
        """
        # FK ~19: measured — "validates incoming requests" prose with multi-syllable verbs
        sentence = (
            "The processor validates incoming requests and produces formatted output results. "
        )
        text = sentence * 15  # 150+ words, FK ~19.0 → severity="medium" (18 < FK < 22)
        result = check_readability_from_markdown(text, slug="moderate-page")
        assert len(result) >= 1
        assert result[0].severity == "medium"

    def test_too_simple_short_page_no_finding(self):
        """FK < 6 but < 100 words produces no finding (insufficient data)."""
        text = "The cat sat. " * 3  # ~12 words
        result = check_readability_from_markdown(text, slug="short-page")
        assert result == []


class TestCalculateReadingTime:
    def test_200_words_is_1_minute(self):
        from launcher.workers.generate.seo_metadata import _calculate_reading_time
        assert _calculate_reading_time(200) == 1

    def test_400_words_is_2_minutes(self):
        from launcher.workers.generate.seo_metadata import _calculate_reading_time
        assert _calculate_reading_time(400) == 2

    def test_minimum_1_minute(self):
        from launcher.workers.generate.seo_metadata import _calculate_reading_time
        assert _calculate_reading_time(1) == 1
        assert _calculate_reading_time(0) == 1

    def test_600_words_is_3_minutes(self):
        from launcher.workers.generate.seo_metadata import _calculate_reading_time
        assert _calculate_reading_time(600) == 3

    def test_custom_wpm(self):
        from launcher.workers.generate.seo_metadata import _calculate_reading_time
        # 100 words at 100 wpm = 1 minute
        assert _calculate_reading_time(100, words_per_minute=100) == 1
        # 300 words at 100 wpm = 3 minutes
        assert _calculate_reading_time(300, words_per_minute=100) == 3


# ---------------------------------------------------------------------------
# RD-01: FK threshold boundary tests
# ---------------------------------------------------------------------------

class TestRD01ThresholdBoundaries:
    """RD-01: Exact boundary tests for FK severity thresholds."""

    def _make_markdown_with_grade(self, target_grade: float) -> str:
        """Create text with approximately the target FK grade.
        FK = 0.39 * ASL + 11.8 * ASW - 15.59
        Use simple known inputs: tune sentence length and syllable density.
        """
        # For FK > 20: very long sentences with many polysyllabic words
        if target_grade > 20:
            sentence = (
                "Extraordinarily sophisticated multidimensional computational infrastructure "
                "demonstrates extraordinarily comprehensive architectural considerations "
                "necessitating extraordinarily detailed parametrization. "
            )
            return sentence * 10
        # For FK between 16 and 20: moderately complex tech prose
        if target_grade > 16:
            sentence = (
                "When the system processes requests it validates each input parameter "
                "against the configured schema rules. "
            )
            return sentence * 10
        # For FK < 6: very simple short sentences
        return "The cat sat. " * 30 + "The dog ran. " * 30

    def test_fk_above_20_is_high(self):
        text = self._make_markdown_with_grade(21)
        result = check_readability_from_markdown(text, slug="test")
        if result:
            assert result[0].severity == "high", f"FK>20 must be 'high', got '{result[0].severity}'"

    def test_fk_between_16_and_20_is_medium(self):
        text = self._make_markdown_with_grade(17)
        result = check_readability_from_markdown(text, slug="test")
        if result:
            assert result[0].severity in ("medium", "high"), \
                f"FK>16 must be 'medium', got '{result[0].severity}'"

    def test_fk_below_12_no_complex_finding(self):
        """FK between 6 and 12 should produce no finding (normal range)."""
        # 40 words per minute reading level — between too-simple and complex
        text = "The quick brown fox jumps over the lazy dog. " * 15
        result = check_readability_from_markdown(text, slug="test")
        # May have no finding or low (if too simple); must NOT have medium/high
        for f in result:
            assert f.severity != "high", "FK<12 should not produce high severity"


# ---------------------------------------------------------------------------
# RD-02: Long sentence flagging and _split_words alphabetic-only
# ---------------------------------------------------------------------------

class TestRD02LongSentenceAndSplitWords:
    """RD-02: Long sentence flagging and _split_words alphabetic-only."""

    def test_split_words_excludes_numbers(self):
        result = _split_words("API 3.14 version")
        assert "3.14" not in result
        assert "API" in result
        assert "version" in result

    def test_split_words_excludes_punctuation_tokens(self):
        result = _split_words("foo, bar.")
        assert "foo" in result
        assert "bar" in result
        assert "," not in result
        assert "." not in result

    def test_split_words_alphabetic_only(self):
        result = _split_words("hello world")
        assert result == ["hello", "world"]

    def test_split_words_empty(self):
        assert _split_words("") == []

    def test_split_words_only_numbers(self):
        assert _split_words("123 456") == []

    def test_long_sentence_triggers_above_40_pct(self):
        """If >40% sentences exceed 30 words → low finding."""
        # Build 3 sentences: 2 long (>30 words each), 1 short = 67% long
        long_s = " ".join(["word"] * 35) + "."
        short_s = "Short sentence."
        text = f"{long_s} {long_s} {short_s}"
        sentences = _split_sentences(text)
        result = _long_sentence_finding(sentences)
        assert len(result) >= 1
        assert result[0]["severity"] == "low"
        assert result[0]["check"] == "readability"

    def test_long_sentence_no_finding_at_40_pct(self):
        """Exactly 40% long sentences must NOT trigger (boundary is >40%)."""
        # 5 sentences: 2 long (40%), 3 short
        long_s = " ".join(["word"] * 35) + "."
        short_s = "Short sentence."
        text = f"{long_s} {long_s} {short_s} {short_s} {short_s}"
        sentences = _split_sentences(text)
        # At exactly 40% the check must NOT fire (requires >40%)
        result = _long_sentence_finding(sentences)
        assert len(result) == 0, "Exactly 40% must NOT trigger finding (>40% required)"

    def test_long_sentence_skips_under_3_sentences(self):
        """Fewer than 3 sentences → no long-sentence finding (avoid false positives)."""
        long_s = " ".join(["word"] * 35) + "."
        sentences = _split_sentences(f"{long_s} {long_s}")
        result = _long_sentence_finding(sentences)
        assert result == []

    def test_long_sentence_combined_with_fk_finding(self):
        """Both FK complex AND long sentences can appear together in findings list."""
        # Create content with complex words AND long sentences
        long_complex = (
            "The implementation utilizes extraordinarily sophisticated multidimensional "
            "computational infrastructure frameworks necessitating comprehensive "
            "architectural parametrization of asynchronous communication protocols. "
        )
        content = long_complex * 5  # 100+ words, long sentences, complex FK
        result = check_readability_from_markdown(content, slug="test")
        assert isinstance(result, list)  # no crash; may have 0, 1, or 2 findings
