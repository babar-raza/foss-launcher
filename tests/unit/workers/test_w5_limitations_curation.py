"""Tests for TC-2910: curated freeform limitations rendering."""
import pytest
from launch.workers.w5_section_writer.renderers.limitations_renderer import (
    curate_freeform_limitations,
    _dedup_bullets,
    _group_by_prefix,
    _enforce_caps,
    MAX_CURATED_BULLETS,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _claim(cid: str, text: str, enriched: str = "") -> dict:
    d = {"claim_id": cid, "claim_text": text}
    if enriched:
        d["enriched_text"] = enriched
    return d


def _count_bullets(text: str) -> int:
    """Count bullet lines (lines starting with '- ')."""
    return sum(1 for line in text.split("\n") if line.startswith("- "))


PRODUCT = "Aspose.3D FOSS for Python"


class TestCurateFreeformLimitations:
    """End-to-end tests for curate_freeform_limitations()."""

    def test_zero_claims(self):
        result = curate_freeform_limitations([], PRODUCT)
        assert "No known limitations" in result

    def test_single_claim(self):
        claims = [_claim("c1", f"{PRODUCT} does not yet support export.")]
        result = curate_freeform_limitations(claims, PRODUCT)
        assert _count_bullets(result) == 1
        assert "<!-- claim: c1 -->" in result

    def test_three_diverse_claims(self):
        claims = [
            _claim("c1", "Maximum file size is limited to 500MB for single document processing."),
            _claim("c2", "The library does not support concurrent thread access by default."),
            _claim("c3", "Performance degrades when the library processes files with over 10000 elements."),
        ]
        result = curate_freeform_limitations(claims, PRODUCT)
        assert _count_bullets(result) == 3

    def test_deduplicates_near_identical(self):
        claims = [
            _claim("c1", f"{PRODUCT} does not yet support export."),
            _claim("c2", f"{PRODUCT} does not yet support export."),
        ]
        result = curate_freeform_limitations(claims, PRODUCT)
        assert _count_bullets(result) == 1
        assert "<!-- claim: c1 -->" in result
        assert "<!-- claim: c2 -->" in result

    def test_groups_not_yet_support_claims(self):
        methods = ["export", "do_boolean", "clear", "get_bounding_box"]
        claims = [
            _claim(f"c{i}", f"{PRODUCT} does not yet support {m}.")
            for i, m in enumerate(methods)
        ]
        result = curate_freeform_limitations(claims, PRODUCT)
        assert "Several API methods" in result
        assert _count_bullets(result) == 1
        for i in range(4):
            assert f"<!-- claim: c{i} -->" in result

    def test_mixed_group_and_individual(self):
        claims = [
            _claim("c0", f"{PRODUCT} does not yet support export."),
            _claim("c1", f"{PRODUCT} does not yet support do_boolean."),
            _claim("c2", f"{PRODUCT} does not yet support clear."),
            _claim("c3", "Maximum file size is limited to 500MB for large files."),
        ]
        result = curate_freeform_limitations(claims, PRODUCT)
        assert "Several API methods" in result
        assert "500MB" in result
        assert _count_bullets(result) == 2

    def test_caps_at_max_bullets(self):
        claims = [
            _claim(f"c{i}", f"Limitation number {i} is a real problem that affects many users.")
            for i in range(10)
        ]
        result = curate_freeform_limitations(claims, PRODUCT)
        assert _count_bullets(result) <= MAX_CURATED_BULLETS

    def test_respects_char_limit(self):
        claims = [
            _claim(f"c{i}", f"This is limitation {i} with a moderately long description that matters.")
            for i in range(10)
        ]
        result = curate_freeform_limitations(claims, PRODUCT, max_section_chars=300)
        bullet_count = _count_bullets(result)
        assert bullet_count >= 1
        assert bullet_count < 10

    def test_filters_non_user_facing(self):
        claims = [
            _claim("c1", "def _internal_method(self, x): raise NotImplementedError()"),
            _claim("c2", "Cannot process encrypted OneNote files with password protection."),
        ]
        result = curate_freeform_limitations(claims, "Aspose.NOTE")
        assert "_internal_method" not in result
        assert "encrypted" in result.lower() or "No verified" in result

    def test_prefers_enriched_text(self):
        claims = [
            _claim(
                "c1",
                f"{PRODUCT} does not yet support get_entity_renderer_key.",
                enriched="Camera rendering via get_entity_renderer_key is not available.",
            )
        ]
        result = curate_freeform_limitations(claims, PRODUCT)
        assert "Camera rendering" in result

    def test_real_world_8_claim_scenario(self):
        """Exact scenario from the bug report: 8 repetitive 'does not yet support' claims."""
        methods = [
            "get_entity_renderer_key", "do_boolean", "height_map constructor",
            "set_indices", "clear", "get_bounding_box", "export", "FBX export",
        ]
        claims = [
            _claim(f"lim_{m.replace(' ', '_')}", f"{PRODUCT} does not yet support {m}.")
            for m in methods
        ]
        result = curate_freeform_limitations(claims, PRODUCT)
        assert "Several API methods" in result
        assert _count_bullets(result) <= 3

    def test_deterministic(self):
        claims = [
            _claim("c1", f"{PRODUCT} does not yet support export."),
            _claim("c2", "Maximum file size is limited to 500MB for processing."),
        ]
        r1 = curate_freeform_limitations(claims, PRODUCT)
        r2 = curate_freeform_limitations(claims, PRODUCT)
        assert r1 == r2

    def test_no_json_in_output(self):
        """Rendered bullet lines must not contain JSON-like braces."""
        claims = [
            _claim("c1", "The library does not support concurrent thread access by default."),
        ]
        result = curate_freeform_limitations(claims, PRODUCT)
        for line in result.split("\n"):
            if line.startswith("<!--"):
                continue
            assert "{" not in line and "}" not in line

    def test_intro_line_format(self):
        claims = [_claim("c1", "The library does not support concurrent thread access by default.")]
        result = curate_freeform_limitations(claims, PRODUCT)
        assert result.startswith(f"Known limitations and constraints for {PRODUCT}:")


class TestDedupBullets:
    """Unit tests for _dedup_bullets()."""

    def test_exact_duplicates_merged(self):
        bullets = [("Export is not available.", "c1"), ("Export is not available.", "c2")]
        result = _dedup_bullets(bullets, PRODUCT)
        assert len(result) == 1
        assert sorted(result[0][1]) == ["c1", "c2"]

    def test_diverse_bullets_kept(self):
        bullets = [
            ("Export is not available.", "c1"),
            ("Thread safety is not guaranteed.", "c2"),
        ]
        result = _dedup_bullets(bullets, PRODUCT)
        assert len(result) == 2

    def test_empty_input(self):
        assert _dedup_bullets([], PRODUCT) == []


class TestGroupByPrefix:
    """Unit tests for _group_by_prefix()."""

    def test_groups_three_support_claims(self):
        bullets = [
            (f"{PRODUCT} does not yet support export.", "c1"),
            (f"{PRODUCT} does not yet support clear.", "c2"),
            (f"{PRODUCT} does not yet support render.", "c3"),
        ]
        grouped, remaining = _group_by_prefix(bullets, PRODUCT)
        assert len(grouped) == 1
        assert "Several API methods" in grouped[0][0]
        assert len(grouped[0][1]) == 3
        assert remaining == []

    def test_fewer_than_three_kept_as_remaining(self):
        bullets = [
            (f"{PRODUCT} does not yet support export.", "c1"),
            (f"{PRODUCT} does not yet support clear.", "c2"),
        ]
        grouped, remaining = _group_by_prefix(bullets, PRODUCT)
        assert len(grouped) == 0
        assert len(remaining) == 2

    def test_many_methods_uses_others(self):
        bullets = [
            (f"{PRODUCT} does not yet support method_{i}.", f"c{i}")
            for i in range(8)
        ]
        grouped, remaining = _group_by_prefix(bullets, PRODUCT)
        assert len(grouped) == 1
        assert "others" in grouped[0][0]

    def test_mixed_preserves_other_bullets(self):
        bullets = [
            (f"{PRODUCT} does not yet support export.", "c1"),
            (f"{PRODUCT} does not yet support clear.", "c2"),
            (f"{PRODUCT} does not yet support render.", "c3"),
            ("Thread safety is not guaranteed.", "c4"),
        ]
        grouped, remaining = _group_by_prefix(bullets, PRODUCT)
        assert len(grouped) == 1
        assert "Several" in grouped[0][0]
        assert len(remaining) == 1
        assert remaining[0][0] == "Thread safety is not guaranteed."


class TestEnforceCaps:
    """Unit tests for _enforce_caps()."""

    def test_respects_bullet_cap(self):
        items = [(f"Bullet {i}.", [f"c{i}"]) for i in range(10)]
        result = _enforce_caps(items, max_bullets=3, max_section_chars=10000)
        assert len(result) == 3

    def test_respects_char_cap(self):
        items = [("A" * 200 + ".", [f"c{i}"]) for i in range(10)]
        result = _enforce_caps(items, max_bullets=10, max_section_chars=300)
        assert len(result) >= 1
        assert len(result) < 10

    def test_always_includes_at_least_one(self):
        items = [("A" * 500 + ".", ["c1"])]
        result = _enforce_caps(items, max_bullets=6, max_section_chars=10)
        assert len(result) == 1

    def test_empty_input(self):
        assert _enforce_caps([], max_bullets=6, max_section_chars=1200) == []
