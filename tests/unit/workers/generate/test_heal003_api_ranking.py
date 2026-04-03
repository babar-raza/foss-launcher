"""TC-HEAL-003: Tests for heading-relevance ranking in _prioritize_class_briefs()."""
from __future__ import annotations

import pytest

from launcher.models.claims import Claim
from launcher.models.product import ClassBrief
from launcher.workers.generate.section_prompt import _prioritize_class_briefs


def _brief(name: str) -> ClassBrief:
    return ClassBrief(name=name, methods=[], properties=[])


def _claim(text: str) -> Claim:
    return Claim(claim_id=f"c_{text[:8]}", text=text, kind="feature", confidence=0.9)


# ---------------------------------------------------------------------------
# Test 1: Heading-relevant classes ranked first
# ---------------------------------------------------------------------------


def test_heading_relevant_classes_ranked_first() -> None:
    """A class whose PascalCase words match the section heading ranks first."""
    briefs = [
        _brief("FileFormatUtils"),   # "file format" = strong heading match
        _brief("Presentation"),      # no overlap with "file format"
        _brief("Shape"),             # no overlap
    ]
    result = _prioritize_class_briefs(
        briefs,
        [],
        heading="File Format Support",
    )
    assert result[0].name == "FileFormatUtils"


# ---------------------------------------------------------------------------
# Test 2: content_hint used as secondary scoring source
# ---------------------------------------------------------------------------


def test_content_hint_secondary_scoring() -> None:
    """content_hint words break ties when heading matches are equal."""
    briefs = [
        _brief("LoadOptions"),    # 'load' in content_hint
        _brief("SaveOptions"),    # no overlap
    ]
    result = _prioritize_class_briefs(
        briefs,
        [],
        heading="",
        content_hint="Loading documents and load options",
    )
    assert result[0].name == "LoadOptions"


# ---------------------------------------------------------------------------
# Test 3: Claim-mentioned classes rank above non-mentioned when heading equal
# ---------------------------------------------------------------------------


def test_claim_mentioned_classes_ranked_above_non_mentioned() -> None:
    """When heading score is 0 for all, claim-mentioned class ranks above others."""
    briefs = [
        _brief("Presentation"),    # mentioned in claim
        _brief("SlideLayout"),     # not mentioned
    ]
    claims = [_claim("The Presentation class supports loading.")]
    result = _prioritize_class_briefs(
        briefs,
        claims,
        heading="",
        content_hint="",
    )
    assert result[0].name == "Presentation"


# ---------------------------------------------------------------------------
# Test 4: Empty heading and content_hint falls back to claim-text ranking
# ---------------------------------------------------------------------------


def test_empty_heading_falls_back_to_claim_text_ranking() -> None:
    """When heading and content_hint are empty, claim-mention order is preserved."""
    briefs = [
        _brief("SlideLayout"),
        _brief("Presentation"),
    ]
    claims = [_claim("Presentation enables slide rendering.")]
    result = _prioritize_class_briefs(
        briefs,
        claims,
        heading="",
        content_hint="",
    )
    # Presentation is claim-mentioned, should rank first
    assert result[0].name == "Presentation"
