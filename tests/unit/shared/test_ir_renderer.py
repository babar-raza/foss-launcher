"""Tests for ir_renderer.render_page() frontmatter validation (TC-3824)."""
from __future__ import annotations

import pytest

from launcher.models.page_ir import BlockIR, BlockType, PageIR, SectionIR
from launcher.shared.ir_renderer import render_page
from launcher.util.errors import FrontmatterError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_FM: dict = {
    "title": "Convert Excel Files",
    "slug": "convert-excel-files",
    "type": "how_to",
    "url": "/cells/python/convert-excel-files/",
    "weight": 3,
    "family": "cells",
    "platform": "python",
    "page_role": "how_to",
}


def _make_page(frontmatter: dict, *, page_id: str = "cells/python/convert") -> PageIR:
    return PageIR(
        page_id=page_id,
        page_role=frontmatter.get("page_role", "how_to"),
        title=frontmatter.get("title", "Test Page"),
        frontmatter=frontmatter,
        sections=[
            SectionIR(
                section_id="intro",
                heading="Introduction",
                level=2,
                blocks=[BlockIR(type=BlockType.paragraph, content="Hello world.")],
            )
        ],
    )


# ---------------------------------------------------------------------------
# Valid frontmatter (regression)
# ---------------------------------------------------------------------------

class TestValidFrontmatter:
    def test_renders_yaml_block(self) -> None:
        page = _make_page(_VALID_FM)
        md = render_page(page)
        assert md.startswith("---\n")
        assert "title: Convert Excel Files" in md
        assert "slug: convert-excel-files" in md

    def test_renders_section_heading(self) -> None:
        page = _make_page(_VALID_FM)
        md = render_page(page)
        assert "## Introduction" in md

    def test_extra_fields_allowed(self) -> None:
        """Fields beyond the required set are silently passed through."""
        fm = {**_VALID_FM, "seoTitle": "SEO Title", "robots": "index, follow"}
        page = _make_page(fm)
        md = render_page(page)
        assert "seoTitle: SEO Title" in md


# ---------------------------------------------------------------------------
# None value rejection
# ---------------------------------------------------------------------------

class TestNoneValueRejection:
    def test_none_value_raises(self) -> None:
        fm = {**_VALID_FM, "seoTitle": None}
        page = _make_page(fm)
        with pytest.raises(FrontmatterError) as exc_info:
            render_page(page)
        err = exc_info.value
        assert "seoTitle" in err.invalid_keys

    def test_none_value_error_has_page_id(self) -> None:
        fm = {**_VALID_FM, "robots": None}
        page = _make_page(fm, page_id="cells/python/robots-page")
        with pytest.raises(FrontmatterError) as exc_info:
            render_page(page)
        assert exc_info.value.page_id == "cells/python/robots-page"

    def test_multiple_none_values_all_reported(self) -> None:
        fm = {**_VALID_FM, "seoTitle": None, "canonical": None}
        page = _make_page(fm)
        with pytest.raises(FrontmatterError) as exc_info:
            render_page(page)
        err = exc_info.value
        assert "seoTitle" in err.invalid_keys
        assert "canonical" in err.invalid_keys


# ---------------------------------------------------------------------------
# Missing required key rejection
# ---------------------------------------------------------------------------

class TestMissingRequiredKeys:
    @pytest.mark.parametrize("missing_key", [
        "title", "slug", "type", "url", "weight", "family", "platform", "page_role",
    ])
    def test_missing_required_key_raises(self, missing_key: str) -> None:
        fm = {k: v for k, v in _VALID_FM.items() if k != missing_key}
        page = _make_page(fm)
        with pytest.raises(FrontmatterError) as exc_info:
            render_page(page)
        err = exc_info.value
        assert missing_key in err.missing_keys

    def test_empty_frontmatter_raises(self) -> None:
        page = _make_page({})
        with pytest.raises(FrontmatterError) as exc_info:
            render_page(page)
        err = exc_info.value
        # All 8 required keys should be listed
        assert len(err.missing_keys) == 8

    def test_missing_keys_error_message_informative(self) -> None:
        fm = {k: v for k, v in _VALID_FM.items() if k not in ("slug", "url")}
        page = _make_page(fm)
        with pytest.raises(FrontmatterError) as exc_info:
            render_page(page)
        err = exc_info.value
        assert "slug" in err.missing_keys
        assert "url" in err.missing_keys


# ---------------------------------------------------------------------------
# Non-serialisable value rejection
# ---------------------------------------------------------------------------

class TestNonSerialisableValues:
    def test_custom_object_raises(self) -> None:
        class _Unserializable:
            pass

        fm = {**_VALID_FM, "bad_field": _Unserializable()}
        page = _make_page(fm)
        with pytest.raises(FrontmatterError):
            render_page(page)


# ---------------------------------------------------------------------------
# YAML round-trip verification
# ---------------------------------------------------------------------------

class TestYAMLRoundTrip:
    def test_valid_fm_round_trips_cleanly(self) -> None:
        """Valid frontmatter must round-trip without raising."""
        page = _make_page(_VALID_FM)
        md = render_page(page)  # must not raise
        assert "---" in md

    def test_integer_weight_round_trips(self) -> None:
        """Integer weight must survive YAML round-trip as an int."""
        fm = {**_VALID_FM, "weight": 42}
        page = _make_page(fm)
        md = render_page(page)
        assert "weight: 42" in md


# ---------------------------------------------------------------------------
# FrontmatterError string representation
# ---------------------------------------------------------------------------

class TestFrontmatterErrorStr:
    def test_str_includes_page_id(self) -> None:
        err = FrontmatterError("oops", page_id="cells/python/test")
        assert "cells/python/test" in str(err)

    def test_str_includes_missing_keys(self) -> None:
        err = FrontmatterError("oops", missing_keys=["slug", "url"])
        s = str(err)
        assert "slug" in s
        assert "url" in s

    def test_str_includes_invalid_keys(self) -> None:
        err = FrontmatterError("oops", invalid_keys=["robots"])
        assert "robots" in str(err)
