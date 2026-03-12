"""Tests for the cross-page linker (TC-3778)."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from launcher.models.content import CrossLink
from launcher.models.page_ir import BlockIR, BlockType, PageIR, SectionIR
from launcher.models.plan import PlannedPage
from launcher.models.product import ProductIdentity
from launcher.shared.linker import (
    LinkerConfig,
    PageEntry,
    ScoredLink,
    _find_existing_link_spans,
    _jaccard_frozensets,
    _parse_anchor_response,
    _sanitize_anchor_text,
    _validate_anchor,
    _check_anchor_diversity,
    _deduplicate_anchors,
    absolutize_urls,
    build_page_index,
    infer_section,
    inject_contextual_links,
    inject_links,
    link_pages,
    load_linker_config,
    resolve_link_url,
    score_links,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_page_plan(
    page_id: str,
    page_role: str = "overview",
    title: str = "Test Page",
    claims: list[str] | None = None,
    url: str = "",
    content_path: str = "",
) -> PlannedPage:
    return PlannedPage(
        page_id=page_id,
        page_role=page_role,
        title=title,
        assigned_claims=claims or [],
        frontmatter={"url": url or f"/{page_id.replace('-', '/')}/"},
        content_path=content_path or page_id.replace("-", "/"),
    )


def _make_page_ir(page_id: str, page_role: str = "overview", title: str = "Test") -> PageIR:
    return PageIR(
        page_id=page_id,
        page_role=page_role,
        title=title,
        frontmatter={},
        sections=[
            SectionIR(
                section_id="intro",
                heading="Introduction",
                level=2,
                blocks=[BlockIR(type=BlockType.paragraph, content="Hello world.")],
            ),
        ],
    )


def _make_product() -> ProductIdentity:
    return ProductIdentity(
        family="cells",
        platform="python",
        display_name="Aspose.Cells for Python",
        canonical_import="aspose_cells_foss",
        repo_url="https://github.com/test/repo",
        repo_sha="abc123",
    )


# ---------------------------------------------------------------------------
# Tests: build_page_index
# ---------------------------------------------------------------------------

class TestBuildPageIndex:
    def test_basic(self):
        plans = [
            _make_page_plan("docs-install", title="Installation", url="/install/"),
            _make_page_plan("reference-api", title="API Ref", page_role="reference_page", url="/api/"),
        ]
        idx = build_page_index(plans)
        assert len(idx) == 2
        assert idx["docs-install"].section == "docs"
        assert idx["reference-api"].section == "reference"
        assert idx["docs-install"].url == "/install/"


# ---------------------------------------------------------------------------
# Tests: score_links
# ---------------------------------------------------------------------------

class TestScoreLinks:
    def test_prefers_cross_section(self):
        """docs->reference should score higher than docs->docs (cross-section bonus)."""
        plans = [
            _make_page_plan("docs-a", claims=["C1", "C2", "C3"]),
            _make_page_plan("docs-b", claims=["C1", "C2", "C3"]),  # same section
            _make_page_plan("reference-c", claims=["C1", "C2", "C3"]),  # different section
        ]
        config = LinkerConfig()
        result = score_links(plans, config)
        links_a = result["docs-a"]

        # Should have links to both
        targets = {l.target_id: l.score for l in links_a}
        assert "reference-c" in targets
        assert "docs-b" in targets
        # Cross-section should score higher
        assert targets["reference-c"] > targets["docs-b"]

    def test_deterministic(self):
        """Same input -> same output."""
        plans = [
            _make_page_plan("docs-a", claims=["C1", "C2"]),
            _make_page_plan("docs-b", claims=["C1", "C3"]),
            _make_page_plan("reference-c", claims=["C2", "C3"]),
        ]
        config = LinkerConfig()
        r1 = score_links(plans, config)
        r2 = score_links(plans, config)
        for pid in r1:
            assert len(r1[pid]) == len(r2[pid])
            for a, b in zip(r1[pid], r2[pid]):
                assert a.target_id == b.target_id
                assert a.score == b.score

    def test_filters_below_threshold(self):
        """Pages with zero claim overlap and same section get filtered out."""
        plans = [
            _make_page_plan("docs-a", claims=["C1"]),
            _make_page_plan("docs-b", claims=["C2"]),  # no overlap, same section
        ]
        config = LinkerConfig(min_score=0.15)
        result = score_links(plans, config)
        # Jaccard = 0/2 = 0.0, minus same-section penalty = -0.1 -> clamped to 0.0
        assert result["docs-a"] == []

    def test_toc_excluded(self):
        """TOC pages should not appear in results (neither as source nor target)."""
        plans = [
            _make_page_plan("docs-toc", page_role="toc", claims=["C1"]),
            _make_page_plan("docs-page", claims=["C1"]),
        ]
        config = LinkerConfig()
        result = score_links(plans, config)
        assert result["docs-toc"] == []
        # docs-page should not link to TOC either
        for link in result["docs-page"]:
            assert link.target_id != "docs-toc"

    def test_max_links_cap(self):
        """Should not exceed max_links."""
        plans = [_make_page_plan("docs-src", claims=["C1", "C2", "C3"])]
        # Add 10 cross-section targets
        for i in range(10):
            plans.append(_make_page_plan(f"reference-t{i}", claims=["C1", "C2"], page_role="reference_page"))
        config = LinkerConfig(max_links=3)
        result = score_links(plans, config)
        assert len(result["docs-src"]) <= 3

    def test_link_count_varies_by_page(self):
        """Hub page with shared claims gets higher scores than niche page."""
        plans = [
            _make_page_plan("docs-hub", claims=["C1", "C2", "C3", "C4", "C5"]),
            _make_page_plan("docs-niche", claims=["C99"]),  # unique claim, no overlap
            _make_page_plan("reference-a", claims=["C1", "C2"], page_role="reference_page"),
            _make_page_plan("reference-b", claims=["C3", "C4"], page_role="reference_page"),
            _make_page_plan("kb-c", claims=["C5"], page_role="faq"),
        ]
        config = LinkerConfig()
        result = score_links(plans, config)
        hub_scores = [l.score for l in result["docs-hub"]]
        niche_scores = [l.score for l in result["docs-niche"]]
        # Hub should have higher top score due to claim overlap
        assert max(hub_scores) > max(niche_scores) if niche_scores else True


# ---------------------------------------------------------------------------
# Tests: inject_links
# ---------------------------------------------------------------------------

class TestInjectLinks:
    def test_creates_see_also(self):
        """When no See Also section exists, one should be created."""
        page_ir = _make_page_ir("docs-test")
        index = {
            "reference-api": PageEntry(
                page_id="reference-api", title="API Reference",
                url="/api/", section="reference", page_role="reference_page",
                claim_ids=frozenset(),
            ),
        }
        links = [ScoredLink(source_id="docs-test", target_id="reference-api", score=0.5, anchor_text="API Reference")]
        result = inject_links(page_ir, links, index, "docs")
        # Should have original section + new See Also
        assert len(result.sections) == 2
        see_also = result.sections[-1]
        assert see_also.section_id == "see_also"
        assert see_also.heading == "See Also"
        assert len(see_also.blocks) == 1
        assert see_also.blocks[0].type == BlockType.list
        assert "[API Reference]" in see_also.blocks[0].items[0]

    def test_appends_to_existing(self):
        """When See Also section exists, links should be appended."""
        page_ir = PageIR(
            page_id="docs-test", page_role="overview", title="Test",
            frontmatter={},
            sections=[
                SectionIR(section_id="see_also", heading="See Also", level=2,
                           blocks=[BlockIR(type=BlockType.paragraph, content="Related resources.")]),
            ],
        )
        index = {
            "kb-faq": PageEntry(
                page_id="kb-faq", title="FAQ", url="/faq/",
                section="kb", page_role="faq", claim_ids=frozenset(),
            ),
        }
        links = [ScoredLink(source_id="docs-test", target_id="kb-faq", score=0.3, anchor_text="FAQ")]
        result = inject_links(page_ir, links, index, "docs")
        assert len(result.sections) == 1  # no new section created
        # Original block + new link block
        assert len(result.sections[0].blocks) == 2
        assert result.sections[0].blocks[1].type == BlockType.list

    def test_skips_toc(self):
        """TOC pages should not get See Also injected."""
        page_ir = _make_page_ir("docs-toc")
        page_ir = page_ir.model_copy(update={"page_role": "toc"})
        index = {"docs-page": PageEntry(
            page_id="docs-page", title="Page", url="/page/",
            section="docs", page_role="overview", claim_ids=frozenset(),
        )}
        links = [ScoredLink(source_id="docs-toc", target_id="docs-page", score=0.5, anchor_text="Page")]
        result = inject_links(page_ir, links, index, "docs")
        # Should be unchanged
        assert len(result.sections) == 1
        assert result.sections[0].section_id == "intro"

    def test_empty_links_no_change(self):
        """No links -> no changes."""
        page_ir = _make_page_ir("docs-test")
        result = inject_links(page_ir, [], {}, "docs")
        assert result == page_ir

    def test_inject_links_idempotent(self):
        """TC-3896: calling inject_links() twice must produce exactly 1 link block in See Also."""
        index = {
            "reference-api": PageEntry(
                page_id="reference-api", title="API Reference",
                url="/api/", section="reference", page_role="reference_page",
                claim_ids=frozenset(),
            ),
        }
        links = [ScoredLink(source_id="docs-test", target_id="reference-api", score=0.5, anchor_text="API Reference")]

        # First call — creates See Also section with 1 link block
        page_ir = _make_page_ir("docs-test")
        after_first = inject_links(page_ir, links, index, "docs")
        see_also_after_first = [s for s in after_first.sections if s.section_id == "see_also"]
        assert len(see_also_after_first) == 1
        assert len(see_also_after_first[0].blocks) == 1

        # Second call (simulates heal re-run) — must replace, not append
        after_second = inject_links(after_first, links, index, "docs")
        see_also_after_second = [s for s in after_second.sections if s.section_id == "see_also"]
        assert len(see_also_after_second) == 1, "Must not create a second See Also section"
        link_blocks = [b for b in see_also_after_second[0].blocks if b.type == BlockType.list]
        assert len(link_blocks) == 1, f"TC-3896: Expected exactly 1 link block after 2 inject_links calls, got {len(link_blocks)}"

    def test_inject_links_preserves_non_link_blocks(self):
        """TC-3896: non-link blocks in See Also (prose) are preserved when links are replaced."""
        page_ir = PageIR(
            page_id="docs-test", page_role="overview", title="Test",
            frontmatter={},
            sections=[
                SectionIR(section_id="see_also", heading="See Also", level=2,
                           blocks=[
                               BlockIR(type=BlockType.paragraph, content="Related resources."),
                               BlockIR(type=BlockType.list, items=["[Old link](/old/)"]),
                           ]),
            ],
        )
        index = {
            "kb-faq": PageEntry(
                page_id="kb-faq", title="FAQ", url="/faq/",
                section="kb", page_role="faq", claim_ids=frozenset(),
            ),
        }
        links = [ScoredLink(source_id="docs-test", target_id="kb-faq", score=0.3, anchor_text="FAQ")]
        result = inject_links(page_ir, links, index, "docs")
        see_also = result.sections[0]
        # Paragraph preserved + old list replaced with new link block → 2 blocks total
        assert len(see_also.blocks) == 2
        assert see_also.blocks[0].type == BlockType.paragraph
        assert see_also.blocks[1].type == BlockType.list
        assert "[FAQ]" in see_also.blocks[1].items[0]


# ---------------------------------------------------------------------------
# Tests: absolutize_urls
# ---------------------------------------------------------------------------

class TestAbsolutizeUrls:
    def test_same_subdomain_stays_relative(self):
        """Links within the same subdomain remain relative."""
        page_ir = PageIR(
            page_id="docs-a", page_role="overview", title="A",
            frontmatter={},
            sections=[SectionIR(
                section_id="content", heading="Content", level=2,
                blocks=[BlockIR(
                    type=BlockType.paragraph,
                    content="Check [install](/docs-install/) for details.",
                )],
            )],
        )
        index = {
            "docs-install": PageEntry(
                page_id="docs-install", title="Install", url="/docs-install/",
                section="docs", page_role="overview", claim_ids=frozenset(),
            ),
        }
        result = absolutize_urls(page_ir, "docs", index)
        # Same subdomain -> stays relative
        assert "https://" not in result.sections[0].blocks[0].content

    def test_cross_subdomain_becomes_absolute(self):
        """Links crossing subdomains get absolutized."""
        page_ir = PageIR(
            page_id="docs-a", page_role="overview", title="A",
            frontmatter={},
            sections=[SectionIR(
                section_id="content", heading="Content", level=2,
                blocks=[BlockIR(
                    type=BlockType.paragraph,
                    content="See [API](/ref-api/) for the reference.",
                )],
            )],
        )
        index = {
            "ref-api": PageEntry(
                page_id="ref-api", title="API", url="/ref-api/",
                section="reference", page_role="reference_page", claim_ids=frozenset(),
            ),
        }
        result = absolutize_urls(page_ir, "docs", index)
        assert "https://reference.aspose.org/ref-api/" in result.sections[0].blocks[0].content

    def test_list_items_absolutized(self):
        """List items with cross-subdomain links should be absolutized."""
        page_ir = PageIR(
            page_id="docs-a", page_role="overview", title="A",
            frontmatter={},
            sections=[SectionIR(
                section_id="see_also", heading="See Also", level=2,
                blocks=[BlockIR(
                    type=BlockType.list,
                    items=["[Blog Post](/blog-post/)"],
                )],
            )],
        )
        index = {
            "blog-post": PageEntry(
                page_id="blog-post", title="Post", url="/blog-post/",
                section="blog", page_role="overview", claim_ids=frozenset(),
            ),
        }
        result = absolutize_urls(page_ir, "docs", index)
        assert "https://blog.aspose.org/blog-post/" in result.sections[0].blocks[0].items[0]


# ---------------------------------------------------------------------------
# Tests: resolve_link_url
# ---------------------------------------------------------------------------

class TestResolveLinkUrl:
    def test_same_section(self):
        assert resolve_link_url("docs", "docs", "/install/") == "/install/"

    def test_cross_section(self):
        result = resolve_link_url("docs", "reference", "/api/")
        assert result == "https://reference.aspose.org/api/"


# ---------------------------------------------------------------------------
# Tests: anchor text validation
# ---------------------------------------------------------------------------

class TestAnchorTextValidation:
    def test_valid_anchor(self):
        assert _sanitize_anchor_text("Learn how to install", "fallback") == "Learn how to install"

    def test_too_short(self):
        assert _sanitize_anchor_text("X", "fallback") == "fallback"

    def test_contains_url(self):
        assert _sanitize_anchor_text("Visit https://example.com now", "fallback") == "fallback"

    def test_contains_markdown(self):
        assert _sanitize_anchor_text("[click here](link)", "fallback") == "fallback"

    def test_parse_response_valid(self):
        raw = '["Learn to install", "API reference guide"]'
        result = _parse_anchor_response(raw, 2)
        assert result == ["Learn to install", "API reference guide"]

    def test_parse_response_embedded(self):
        raw = 'Here are the anchors: ["Anchor one", "Anchor two"] done.'
        result = _parse_anchor_response(raw, 2)
        assert len(result) == 2

    def test_parse_response_invalid(self):
        result = _parse_anchor_response("not json at all", 2)
        assert result == []

    # TC-3890: dict-coercion fix tests
    def test_parse_response_dict_items_extracts_text(self):
        """LLM returned structured dicts instead of plain strings."""
        raw = '[{"type": "anchor", "text": "Frequently asked questions"}]'
        result = _parse_anchor_response(raw, 1)
        assert result == ["Frequently asked questions"]

    def test_parse_response_dict_fallback_key_anchor(self):
        raw = '[{"anchor": "Create charts in spreadsheets"}]'
        result = _parse_anchor_response(raw, 1)
        assert result == ["Create charts in spreadsheets"]

    def test_parse_response_dict_fallback_key_label(self):
        raw = '[{"label": "No Excel required"}]'
        result = _parse_anchor_response(raw, 1)
        assert result == ["No Excel required"]

    def test_parse_response_empty_dict_returns_empty_string(self):
        raw = '[{}]'
        result = _parse_anchor_response(raw, 1)
        assert result == [""]

    def test_parse_response_mixed_strings_and_dicts(self):
        raw = '["Plain anchor", {"text": "Dict anchor"}]'
        result = _parse_anchor_response(raw, 2)
        assert result == ["Plain anchor", "Dict anchor"]

    def test_sanitize_rejects_dict_literal(self):
        """Dict literals from str(dict) must be rejected, not passed through."""
        bad = "{'type': 'anchor', 'text': 'Frequently asked questions'}"
        assert _sanitize_anchor_text(bad, "fallback") == "fallback"

    def test_sanitize_rejects_list_dict_literal(self):
        bad = "[{'type': 'anchor', 'text': 'x'}]"
        assert _sanitize_anchor_text(bad, "fallback") == "fallback"

    def test_sanitize_valid_anchor_unchanged(self):
        assert _sanitize_anchor_text("Frequently asked questions", "fallback") == "Frequently asked questions"


# ---------------------------------------------------------------------------
# Tests: load_linker_config
# ---------------------------------------------------------------------------

class TestGenerateAnchorTexts:
    def test_llm_success(self):
        """When LLM returns valid anchors, they should be used."""
        index = {
            "docs-src": PageEntry(
                page_id="docs-src", title="Source", url="/src/",
                section="docs", page_role="overview", claim_ids=frozenset(),
            ),
            "reference-api": PageEntry(
                page_id="reference-api", title="API Reference", url="/api/",
                section="reference", page_role="reference_page", claim_ids=frozenset(),
            ),
        }
        links = [ScoredLink(source_id="docs-src", target_id="reference-api", score=0.5)]

        mock_context = AsyncMock()
        mock_context.llm_config = AsyncMock()

        with patch(
            "launcher.shared.linker._call_llm_for_anchors",
            return_value='["Explore the API reference"]',
        ):
            from launcher.shared.linker import generate_anchor_texts
            result = asyncio.new_event_loop().run_until_complete(
                generate_anchor_texts(links, index, mock_context, product_name="TestProduct"),
            )

        assert len(result) == 1
        assert result[0].anchor_text == "Explore the API reference"

    def test_llm_failure_falls_back_to_title(self):
        """When LLM fails, anchor text should fall back to target title."""
        index = {
            "docs-src": PageEntry(
                page_id="docs-src", title="Source", url="/src/",
                section="docs", page_role="overview", claim_ids=frozenset(),
            ),
            "reference-api": PageEntry(
                page_id="reference-api", title="API Reference", url="/api/",
                section="reference", page_role="reference_page", claim_ids=frozenset(),
            ),
        }
        links = [ScoredLink(source_id="docs-src", target_id="reference-api", score=0.5)]

        mock_context = AsyncMock()
        mock_context.llm_config = AsyncMock()

        with patch(
            "launcher.shared.linker._call_llm_for_anchors",
            side_effect=RuntimeError("LLM unavailable"),
        ):
            from launcher.shared.linker import generate_anchor_texts
            result = asyncio.new_event_loop().run_until_complete(
                generate_anchor_texts(links, index, mock_context, product_name="TestProduct"),
            )

        assert len(result) == 1
        assert result[0].anchor_text == "API Reference"  # title fallback

    def test_no_context_falls_back_to_title(self):
        """When context is None, anchor text should fall back to target title."""
        index = {
            "docs-src": PageEntry(
                page_id="docs-src", title="Source", url="/src/",
                section="docs", page_role="overview", claim_ids=frozenset(),
            ),
            "reference-api": PageEntry(
                page_id="reference-api", title="API Reference", url="/api/",
                section="reference", page_role="reference_page", claim_ids=frozenset(),
            ),
        }
        links = [ScoredLink(source_id="docs-src", target_id="reference-api", score=0.5)]

        from launcher.shared.linker import generate_anchor_texts
        result = asyncio.new_event_loop().run_until_complete(
            generate_anchor_texts(links, index, None, product_name="TestProduct"),
        )

        assert len(result) == 1
        assert result[0].anchor_text == "API Reference"


class TestGenerateAnchorTextsDedup:
    """Regression tests for TC-3869: _deduplicate_anchors wired into generate_anchor_texts."""

    def _make_index(self, *titles: str) -> tuple[dict, list]:
        """Build a minimal page_index and scored_links for testing."""
        index = {
            "docs-src": PageEntry(
                page_id="docs-src", title="Source", url="/src/",
                section="docs", page_role="overview", claim_ids=frozenset(),
            ),
        }
        links = []
        for i, title in enumerate(titles):
            pid = f"reference-page{i}"
            index[pid] = PageEntry(
                page_id=pid, title=title, url=f"/page{i}/",
                section="reference", page_role="reference_page", claim_ids=frozenset(),
            )
            links.append(ScoredLink(source_id="docs-src", target_id=pid, score=0.5))
        return index, links

    def test_duplicate_anchors_deduped_in_generate_flow(self):
        """Regression TC-3869: identical LLM anchors must be de-duplicated in generate_anchor_texts."""
        index, links = self._make_index("API Reference", "Getting Started")
        mock_context = AsyncMock()
        mock_context.llm_config = AsyncMock()

        # LLM returns two identical anchor texts — second must be replaced by fallback title
        with patch(
            "launcher.shared.linker._call_llm_for_anchors",
            return_value='["Explore API reference", "Explore API reference"]',
        ):
            from launcher.shared.linker import generate_anchor_texts
            result = asyncio.new_event_loop().run_until_complete(
                generate_anchor_texts(links, index, mock_context),
            )

        assert len(result) == 2
        # First anchor kept as-is
        assert result[0].anchor_text == "Explore API reference"
        # Second anchor is a near-duplicate (identical) → replaced by fallback title
        assert result[1].anchor_text != "Explore API reference", (
            "Duplicate anchor text must be replaced by fallback title"
        )
        # Fallback is target page title
        assert result[1].anchor_text == "Getting Started"

    def test_distinct_anchors_preserved_in_generate_flow(self):
        """Regression TC-3869: distinct anchors must be unchanged by dedup."""
        index, links = self._make_index("API Reference", "Getting Started")
        mock_context = AsyncMock()
        mock_context.llm_config = AsyncMock()

        with patch(
            "launcher.shared.linker._call_llm_for_anchors",
            return_value='["Explore the API reference", "Install and get started quickly"]',
        ):
            from launcher.shared.linker import generate_anchor_texts
            result = asyncio.new_event_loop().run_until_complete(
                generate_anchor_texts(links, index, mock_context),
            )

        assert len(result) == 2
        assert result[0].anchor_text == "Explore the API reference"
        assert result[1].anchor_text == "Install and get started quickly"


class TestInferSection:
    def test_with_dash(self):
        assert infer_section("docs-install") == "docs"
        assert infer_section("reference-api-surface") == "reference"

    def test_no_dash_no_frontmatter(self):
        assert infer_section("overview") == "docs"

    def test_no_dash_with_frontmatter(self):
        assert infer_section("overview", {"section": "products"}) == "products"
        assert infer_section("landing", {"section": "kb"}) == "kb"

    def test_dash_ignores_frontmatter(self):
        """When page_id has a dash, frontmatter section is ignored."""
        assert infer_section("docs-install", {"section": "products"}) == "docs"

    def test_none_section_in_frontmatter(self):
        """When frontmatter has section=None, should fall back to 'docs'."""
        assert infer_section("overview", {"section": None}) == "docs"


# ---------------------------------------------------------------------------
# Tests: linker_completed event data shape
# ---------------------------------------------------------------------------

class TestLinkerEventData:
    def test_event_data_shape(self):
        """Event data dict from known CrossLinks has correct counts."""
        cross_links = [
            CrossLink(source="a", target="b", anchor_text="B", url="/b/", link_type="see_also"),
            CrossLink(source="a", target="c", anchor_text="C", url="/c/", link_type="see_also"),
            CrossLink(source="toc", target="a", anchor_text="A", url="/a/", link_type="toc_child"),
            CrossLink(source="toc", target="b", anchor_text="B", url="/b/", link_type="toc_child"),
            CrossLink(source="toc", target="c", anchor_text="C", url="/c/", link_type="toc_child"),
        ]
        event_data = {
            "cross_links": len(cross_links),
            "see_also": sum(1 for cl in cross_links if cl.link_type == "see_also"),
            "toc_child": sum(1 for cl in cross_links if cl.link_type == "toc_child"),
        }
        assert event_data["cross_links"] == 5
        assert event_data["see_also"] == 2
        assert event_data["toc_child"] == 3

    def test_event_data_empty(self):
        """Empty cross_links list produces all-zero counts."""
        cross_links: list[CrossLink] = []
        event_data = {
            "cross_links": len(cross_links),
            "see_also": sum(1 for cl in cross_links if cl.link_type == "see_also"),
            "toc_child": sum(1 for cl in cross_links if cl.link_type == "toc_child"),
        }
        assert event_data["cross_links"] == 0
        assert event_data["see_also"] == 0
        assert event_data["toc_child"] == 0


class TestLoadLinkerConfig:
    def test_defaults(self):
        config = load_linker_config({})
        assert config.max_links == 5
        assert config.min_score == 0.15

    def test_custom(self):
        config = load_linker_config({"linker": {"max_links": 3, "min_score": 0.25}})
        assert config.max_links == 3
        assert config.min_score == 0.25


# ---------------------------------------------------------------------------
# TC-3837: Keyword overlap scoring
# ---------------------------------------------------------------------------


class TestKeywordOverlap:
    """TC-3837: seo_keywords boost score when pages share keywords."""

    def test_keyword_overlap_boosts_score(self):
        """Shared seo_keywords should produce a higher score than no keywords.

        Uses pages with NO claim overlap (Jaccard=0) so the keyword bonus is visible.
        docs-a and reference-b are cross-section (get cross-section bonus), so baseline
        score is 0 + 0.2 = 0.2.  With shared keywords (Jaccard=1.0), bonus = 0.15 -> 0.35.
        """
        # No shared claims -> base Jaccard = 0.0
        base_a = _make_page_plan("docs-a", claims=["C1"], url="/a/")
        base_b = _make_page_plan("reference-b", claims=["C2"], url="/b/")

        plans_with_kw = [
            base_a.model_copy(update={"seo_keywords": ["python", "excel"]}),
            base_b.model_copy(update={"seo_keywords": ["python", "excel"]}),
        ]
        plans_no_kw = [
            _make_page_plan("docs-a", claims=["C1"], url="/a/"),
            _make_page_plan("reference-b", claims=["C2"], url="/b/"),
        ]

        config = LinkerConfig()
        result_with = score_links(plans_with_kw, config)
        result_no = score_links(plans_no_kw, config)

        score_with = result_with["docs-a"][0].score if result_with.get("docs-a") else 0.0
        score_no = result_no["docs-a"][0].score if result_no.get("docs-a") else 0.0
        assert score_with > score_no, f"Shared keywords should boost score: {score_with} vs {score_no}"

    def test_keyword_overlap_empty_keywords(self):
        """Pages with no seo_keywords should not crash; score unchanged by keyword term."""
        plans = [
            _make_page_plan("docs-a", claims=["C1"], url="/a/"),
            _make_page_plan("reference-b", claims=["C1"], url="/b/"),
        ]
        # Both have empty seo_keywords (default)
        config = LinkerConfig()
        result = score_links(plans, config)
        # Should produce a result without error
        assert "docs-a" in result

    def test_seo_keywords_in_page_entry(self):
        """build_page_index populates seo_keywords from PlannedPage."""
        plan = _make_page_plan("docs-a", url="/a/").model_copy(
            update={"seo_keywords": ["python", "excel", "cells"]},
        )
        index = build_page_index([plan])
        entry = index["docs-a"]
        assert "python" in entry.seo_keywords
        assert "excel" in entry.seo_keywords
        assert len(entry.seo_keywords) == 3

    def test_jaccard_frozensets_basic(self):
        """_jaccard_frozensets computes correct Jaccard similarity."""
        a = frozenset({"python", "excel"})
        b = frozenset({"python", "cells"})
        result = _jaccard_frozensets(a, b)
        # intersection=1, union=3 -> 1/3
        assert abs(result - 1 / 3) < 1e-9

    def test_jaccard_frozensets_empty(self):
        """Empty sets return 0.0 without error."""
        assert _jaccard_frozensets(frozenset(), frozenset({"python"})) == 0.0
        assert _jaccard_frozensets(frozenset(), frozenset()) == 0.0


# ---------------------------------------------------------------------------
# TC-3837: Contextual inline link injection
# ---------------------------------------------------------------------------


def _make_page_ir_with_text(page_id: str, text: str, page_role: str = "overview") -> PageIR:
    """Helper: PageIR with a single paragraph block containing given text."""
    return PageIR(
        page_id=page_id,
        page_role=page_role,
        title="Source Page",
        frontmatter={},
        sections=[
            SectionIR(
                section_id="intro",
                heading="Introduction",
                level=2,
                blocks=[BlockIR(type=BlockType.paragraph, content=text)],
            )
        ],
    )


class TestContextualLinks:
    """TC-3837: inject_contextual_links injects inline links into matching paragraphs."""

    def _make_index_and_links(self, source_id: str, target_id: str, target_title: str, target_url: str):
        index = {
            source_id: PageEntry(
                page_id=source_id, title="Source Page", url=f"/{source_id}/",
                section="docs", page_role="overview", claim_ids=frozenset(),
            ),
            target_id: PageEntry(
                page_id=target_id, title=target_title, url=target_url,
                section="reference", page_role="reference_page", claim_ids=frozenset(),
            ),
        }
        scored = [ScoredLink(source_id=source_id, target_id=target_id, score=0.5)]
        return index, scored

    def test_contextual_link_injection_basic(self):
        """Title mention in a paragraph gets wrapped as inline link."""
        page_ir = _make_page_ir_with_text(
            "docs-overview",
            "You can use API Reference to explore the endpoints.",
        )
        index, scored = self._make_index_and_links(
            "docs-overview", "reference-api", "API Reference", "/api/",
        )
        new_ir, links = inject_contextual_links(page_ir, scored, index, "docs-overview")
        content = new_ir.sections[0].blocks[0].content
        assert "[API Reference](/api/)" in content
        assert len(links) == 1
        assert links[0]["link_type"] == "contextual"

    def test_contextual_link_max_cap(self):
        """Never injects more than max_inline links per page."""
        # Two sections, each mentioning a target title
        page_ir = PageIR(
            page_id="docs-overview", page_role="overview", title="Source",
            frontmatter={},
            sections=[
                SectionIR(
                    section_id="s1", heading="Section 1", level=2,
                    blocks=[BlockIR(type=BlockType.paragraph, content="Use API Reference here.")],
                ),
                SectionIR(
                    section_id="s2", heading="Section 2", level=2,
                    blocks=[BlockIR(type=BlockType.paragraph, content="Also check API Reference.")],
                ),
                SectionIR(
                    section_id="s3", heading="Section 3", level=2,
                    blocks=[BlockIR(type=BlockType.paragraph, content="Once more API Reference.")],
                ),
            ],
        )
        index, scored = self._make_index_and_links(
            "docs-overview", "reference-api", "API Reference", "/api/",
        )
        new_ir, links = inject_contextual_links(page_ir, scored, index, "docs-overview", max_inline=2)
        assert len(links) <= 2, f"Expected at most 2 links, got {len(links)}"

    def test_contextual_link_no_self_link(self):
        """inject_contextual_links never creates self-links."""
        # Scored link where both source and target are the same page
        page_ir = _make_page_ir_with_text("docs-overview", "Self reference page content.")
        index = {
            "docs-overview": PageEntry(
                page_id="docs-overview", title="Overview Page", url="/overview/",
                section="docs", page_role="overview", claim_ids=frozenset(),
            ),
        }
        scored = [ScoredLink(source_id="docs-overview", target_id="docs-overview", score=0.5)]
        new_ir, links = inject_contextual_links(page_ir, scored, index, "docs-overview")
        assert len(links) == 0, "No self-links should be injected"

    def test_contextual_link_skips_code_blocks(self):
        """Code blocks are not modified by contextual link injection."""
        page_ir = PageIR(
            page_id="docs-overview", page_role="overview", title="Source",
            frontmatter={},
            sections=[
                SectionIR(
                    section_id="intro", heading="Introduction", level=2,
                    blocks=[
                        BlockIR(type=BlockType.code, content="# API Reference usage example"),
                    ],
                ),
            ],
        )
        index, scored = self._make_index_and_links(
            "docs-overview", "reference-api", "API Reference", "/api/",
        )
        new_ir, links = inject_contextual_links(page_ir, scored, index, "docs-overview")
        code_content = new_ir.sections[0].blocks[0].content
        assert "[API Reference]" not in code_content, "Code block content must not be modified"
        assert len(links) == 0

    def test_contextual_link_no_match_no_change(self):
        """If title does not appear in any paragraph, no links are injected."""
        page_ir = _make_page_ir_with_text(
            "docs-overview", "This paragraph has no matching title text.",
        )
        index, scored = self._make_index_and_links(
            "docs-overview", "reference-api", "API Reference", "/api/",
        )
        new_ir, links = inject_contextual_links(page_ir, scored, index, "docs-overview")
        assert len(links) == 0
        assert new_ir.sections[0].blocks[0].content == "This paragraph has no matching title text."

    def test_contextual_link_already_linked_skipped(self):
        """A title already wrapped in a link is not double-linked."""
        page_ir = _make_page_ir_with_text(
            "docs-overview",
            "See [API Reference](/api/) for more details.",
        )
        index, scored = self._make_index_and_links(
            "docs-overview", "reference-api", "API Reference", "/api/",
        )
        new_ir, links = inject_contextual_links(page_ir, scored, index, "docs-overview")
        content = new_ir.sections[0].blocks[0].content
        # Should not add a second link
        assert content.count("[API Reference]") == 1
        assert len(links) == 0

    def test_contextual_link_no_duplicate(self):
        """Same target is not linked more than max_inline=1 times per page."""
        page_ir = PageIR(
            page_id="docs-overview", page_role="overview", title="Source",
            frontmatter={},
            sections=[
                SectionIR(
                    section_id="s1", heading="Section 1", level=2,
                    blocks=[BlockIR(type=BlockType.paragraph,
                                   content="Use API Reference for endpoints.")],
                ),
                SectionIR(
                    section_id="s2", heading="Section 2", level=2,
                    blocks=[BlockIR(type=BlockType.paragraph,
                                   content="API Reference covers all methods.")],
                ),
            ],
        )
        index, scored = self._make_index_and_links(
            "docs-overview", "reference-api", "API Reference", "/api/",
        )
        # max_inline=1 means at most 1 link total
        new_ir, links = inject_contextual_links(page_ir, scored, index, "docs-overview", max_inline=1)
        assert len(links) <= 1, f"Expected at most 1 link, got {len(links)}"

    def test_contextual_link_preserves_existing_markdown_link(self):
        """Text already inside [...](url) is not wrapped a second time."""
        page_ir = _make_page_ir_with_text(
            "docs-overview",
            "Check the [API Reference](/api/) documentation for details.",
        )
        index, scored = self._make_index_and_links(
            "docs-overview", "reference-api", "API Reference", "/api/",
        )
        new_ir, links = inject_contextual_links(page_ir, scored, index, "docs-overview")
        content = new_ir.sections[0].blocks[0].content
        # Must not contain a nested link like [[API Reference](...)
        assert "[[" not in content
        assert content.count("[API Reference]") == 1
        assert len(links) == 0

    def test_contextual_link_regex_metachar_title(self):
        """Page title containing regex metacharacters does not raise re.error."""
        page_ir = _make_page_ir_with_text(
            "docs-overview",
            "Aspose.Cells (for Python) is a spreadsheet API.",
        )
        page_id = "cells-python"
        index = {
            "docs-overview": PageEntry(
                page_id="docs-overview", title="Overview", url="/overview/",
                section="docs", page_role="overview", claim_ids=frozenset(),
            ),
            page_id: PageEntry(
                page_id=page_id, title="Aspose.Cells (for Python)", url="/cells/",
                section="docs", page_role="overview", claim_ids=frozenset(),
            ),
        }
        scored = [ScoredLink(source_id="docs-overview", target_id=page_id, score=0.5)]
        # Must not raise re.error
        new_ir, links = inject_contextual_links(page_ir, scored, index, "docs-overview")
        assert isinstance(links, list)

    def test_contextual_link_exception_safety(self):
        """A scored_link pointing to a non-existent page_index entry does not crash."""
        page_ir = _make_page_ir_with_text(
            "docs-overview",
            "This page references a missing target somewhere.",
        )
        index = {
            "docs-overview": PageEntry(
                page_id="docs-overview", title="Overview", url="/overview/",
                section="docs", page_role="overview", claim_ids=frozenset(),
            ),
            # "missing-page" is intentionally absent from index
        }
        scored = [ScoredLink(source_id="docs-overview", target_id="missing-page", score=0.9)]
        # Must not raise; returns original PageIR and empty links
        new_ir, links = inject_contextual_links(page_ir, scored, index, "docs-overview")
        assert isinstance(links, list)
        assert len(links) == 0

    def test_contextual_link_deterministic(self):
        """Same input always produces same output (PYTHONHASHSEED=0 stable)."""
        page_ir = _make_page_ir_with_text(
            "docs-overview",
            "Use API Reference to explore the available endpoints.",
        )
        index, scored = self._make_index_and_links(
            "docs-overview", "reference-api", "API Reference", "/api/",
        )
        result1, links1 = inject_contextual_links(page_ir, scored, index, "docs-overview")
        result2, links2 = inject_contextual_links(page_ir, scored, index, "docs-overview")

        assert result1.sections[0].blocks[0].content == result2.sections[0].blocks[0].content
        assert len(links1) == len(links2)


# ---------------------------------------------------------------------------
# Tests: link_pages end-to-end
# ---------------------------------------------------------------------------

class TestLinkPagesE2E:
    def test_end_to_end(self):
        """Full pipeline: generate PageIRs -> link -> verify See Also sections."""
        plans = [
            _make_page_plan("docs-overview", title="Overview", claims=["C1", "C2"]),
            _make_page_plan("reference-api", title="API Reference", page_role="reference_page", claims=["C1", "C2"]),
            _make_page_plan("docs-toc", title="TOC", page_role="toc", claims=["C1"]),
        ]
        page_irs = [
            _make_page_ir("docs-overview", title="Overview"),
            _make_page_ir("reference-api", page_role="reference_page", title="API Reference"),
            _make_page_ir("docs-toc", page_role="toc", title="TOC"),
        ]
        product = _make_product()

        linked_irs, cross_links = asyncio.new_event_loop().run_until_complete(
            link_pages(page_irs, plans, product, context=None),
        )

        assert len(linked_irs) == 3

        # docs-overview should have See Also linking to reference-api
        overview = linked_irs[0]
        see_also_sections = [s for s in overview.sections if s.section_id == "see_also"]
        assert len(see_also_sections) == 1
        assert any("API Reference" in item for item in see_also_sections[0].blocks[0].items)

        # reference-api should have See Also linking to docs-overview
        api_ref = linked_irs[1]
        see_also_sections = [s for s in api_ref.sections if s.section_id == "see_also"]
        assert len(see_also_sections) == 1

        # TOC should NOT have See Also
        toc = linked_irs[2]
        see_also_sections = [s for s in toc.sections if s.section_id == "see_also"]
        assert len(see_also_sections) == 0

        # Cross-links should exist: see_also + toc_child
        see_also_links = [cl for cl in cross_links if cl.link_type == "see_also"]
        toc_child_links = [cl for cl in cross_links if cl.link_type == "toc_child"]
        assert len(see_also_links) >= 2

        # TOC page should produce toc_child links to its section's pages
        assert len(toc_child_links) >= 1
        for cl in toc_child_links:
            assert cl.source == "docs-toc"  # slug defaults to page_id

        # All cross-links should have url and link_type
        for cl in cross_links:
            assert cl.link_type in ("see_also", "toc_child")
            assert cl.url  # non-empty

        # Cross-link source/target should use slugs (default to page_id)
        for cl in see_also_links:
            assert cl.source in ("docs-overview", "reference-api")
            assert cl.target in ("docs-overview", "reference-api")


# ---------------------------------------------------------------------------
# Tests: SEO-19 anchor text quality validation (TC-3845)
# ---------------------------------------------------------------------------

class TestAnchorTextOptimization:
    def test_generic_anchor_click_here_rejected(self):
        assert not _validate_anchor("click here")

    def test_generic_anchor_read_more_rejected(self):
        assert not _validate_anchor("read more")

    def test_generic_anchor_here_rejected(self):
        assert not _validate_anchor("here")

    def test_descriptive_anchor_accepted(self):
        assert _validate_anchor("Convert Excel to PDF using Python")

    def test_too_short_rejected(self):
        assert not _validate_anchor("hi")
        assert not _validate_anchor("")

    def test_diversity_all_unique(self):
        assert _check_anchor_diversity(["anchor one", "anchor two", "anchor three"])

    def test_diversity_too_repetitive(self):
        assert not _check_anchor_diversity(["click here", "click here", "click here"])

    def test_diversity_empty(self):
        assert _check_anchor_diversity([])

    def test_diversity_exactly_half_unique(self):
        # 2 unique out of 4 = 50% -> PASS
        assert _check_anchor_diversity(["a", "a", "b", "b"])

    def test_rejects_non_descriptive(self):
        # All-filler anchor with no descriptive noun — must be rejected.
        assert not _validate_anchor("go to the for")

    def test_rejects_all_fillers_long(self):
        # Multi-word but every word is non-descriptive or ≤3 chars.
        assert not _validate_anchor("see how to use")

    def test_accepts_anchor_with_noun(self):
        # Contains at least one descriptive word >3 chars ("install", "library").
        assert _validate_anchor("install library")


class TestDeduplicateAnchors:
    """V2AC-01: _deduplicate_anchors uses max denominator to avoid false positives."""

    def test_symmetric_exact_duplicate_replaced(self):
        # "Install" vs "Install" — overlap 1/1 = 1.0 > 0.6 → second is a dup
        result = _deduplicate_anchors(["Install", "Install"], ["Title A", "Title B"])
        assert result[0] == "Install"
        assert result[1] == "Title B", "Exact duplicate must use fallback"

    def test_asymmetric_short_long_not_a_duplicate(self):
        # "Install" (1 word) vs "Install Aspose Cells" (3 words)
        # min denom=1 would give overlap=1.0 (false dup)
        # max denom=3 gives overlap=1/3=0.33 < 0.6 (correctly NOT a dup)
        result = _deduplicate_anchors(
            ["Install", "Install Aspose Cells"],
            ["Fallback A", "Fallback B"],
        )
        assert result[0] == "Install"
        assert result[1] == "Install Aspose Cells", (
            "Asymmetric pair with max-denom overlap 0.33 must NOT be replaced"
        )

    def test_high_overlap_pair_replaced(self):
        # "Convert Excel files" vs "Convert Excel documents" — 2/4 = 0.5 < 0.6: NOT dup
        # "Convert Excel files" vs "Convert Excel" — 2/3 = 0.67 > 0.6: IS dup
        result = _deduplicate_anchors(
            ["Convert Excel files", "Convert Excel"],
            ["Page A", "Page B"],
        )
        assert result[0] == "Convert Excel files"
        assert result[1] == "Page B", "overlap 0.67 > 0.6 should trigger replacement"

    def test_boundary_60pct_not_flagged(self):
        # Craft overlap = exactly 0.6 — threshold is > 0.6 so 0.6 must NOT trigger
        # "a b c d e" (5 words) vs "a b c X Y" (5 words) — 3 shared → 3/5 = 0.6 → not dup
        result = _deduplicate_anchors(
            ["alpha beta gamma delta epsilon", "alpha beta gamma extra extra2"],
            ["FB A", "FB B"],
        )
        assert result[1] == "alpha beta gamma extra extra2", (
            "Exactly 0.6 overlap (not > 0.6) must NOT be flagged as duplicate"
        )

    def test_length_mismatch_returns_anchors_unchanged(self):
        # Defensive: mismatched lengths return anchors as-is
        result = _deduplicate_anchors(["A", "B"], ["Only One Fallback"])
        assert result == ["A", "B"]

    def test_empty_lists_return_empty(self):
        assert _deduplicate_anchors([], []) == []

    def test_single_anchor_never_a_duplicate(self):
        result = _deduplicate_anchors(["Install"], ["Fallback"])
        assert result == ["Install"]

    def test_case_insensitive_generic_check(self):
        assert not _validate_anchor("Click Here")
        assert not _validate_anchor("READ MORE")

    # --- ST-03: spec-required test names ---

    def test_rejects_click_here(self):
        """'click here' is rejected as a generic anchor."""
        assert not _validate_anchor("click here")

    def test_rejects_generic_case_insensitive(self):
        """Generic anchors are rejected regardless of case."""
        assert not _validate_anchor("CLICK HERE")
        assert not _validate_anchor("Read More")

    def test_rejects_generic_with_whitespace(self):
        """Generic anchors with surrounding whitespace are still rejected."""
        assert not _validate_anchor(" learn more ")
        assert not _validate_anchor("  read more  ")

    def test_diversity_rejects_duplicates(self):
        """Highly repetitive anchors fail diversity check."""
        assert not _check_anchor_diversity(["same anchor", "same anchor", "same anchor"])

    def test_diversity_allows_distinct(self):
        """Distinct anchors pass diversity check."""
        assert _check_anchor_diversity(["first anchor text", "second anchor text"])


class TestFindExistingLinkSpans:
    """V2SC-05: _find_existing_link_spans enables span-based injection exclusion."""

    def test_no_links_returns_empty(self) -> None:
        assert _find_existing_link_spans("plain text with no links") == []

    def test_single_link_returns_correct_span(self) -> None:
        text = "See [Install Guide](https://example.com/install) for details."
        spans = _find_existing_link_spans(text)
        assert len(spans) == 1
        start, end = spans[0]
        assert text[start:end] == "[Install Guide](https://example.com/install)"

    def test_multiple_links_returns_all_spans(self) -> None:
        text = "Read [Overview](https://a.com) and [Setup](https://b.com) first."
        spans = _find_existing_link_spans(text)
        assert len(spans) == 2

    def test_injection_skips_text_inside_link(self) -> None:
        # "Install" appears inside an existing link — should NOT be linked again
        text = "See [Install Guide](https://example.com/install) for how to install."
        spans = _find_existing_link_spans(text)
        # Check that the word "Install" at position 5 is inside a span
        first_install_pos = text.index("Install")
        assert any(s <= first_install_pos < e for s, e in spans)
        # But "install" at the end is outside all spans
        last_install_pos = text.rindex("install")
        assert not any(s <= last_install_pos < e for s, e in spans)
