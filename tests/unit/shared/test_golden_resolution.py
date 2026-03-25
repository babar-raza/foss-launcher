"""Tests for GoldenResolution and resolve methods (TC-OBS-001)."""
from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest

from launcher.shared.golden_loader import (
    GoldenIndex,
    GoldenResolution,
    GoldenSection,
    _clear_golden_cache,
    _parse_sections,
    resolve_golden_for_section,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_GOLDEN_MD = textwrap.dedent("""\
    <!-- GOLDEN REFERENCE | howto_article | variant-standard -->
    ---
    grade: A
    ---

    ## Overview

    This is an overview section with enough words to pass the minimum threshold
    for parsing. It introduces the topic clearly and concisely.

    ## Code Examples

    Here is a code example section with prose and code blocks.

    ```python
    import aspose_cells_foss
    wb = aspose_cells_foss.Workbook()
    print(wb)
    ```

    - Use case: creating a workbook
    - Use case: reading existing files

    ## Getting Started Guide

    A getting started section with sufficient word count to be parsed and
    included in the golden page sections list properly.
""")


def _build_golden_dir(tmp_path: Path, content: str = _GOLDEN_MD) -> Path:
    """Write a golden file and return golden_dir."""
    golden_dir = tmp_path / "golden" / "kb.aspose.org" / "__FAMILY__" / "__PLATFORM__"
    golden_dir.mkdir(parents=True)
    (golden_dir / "howto.variant-standard.md").write_text(content, encoding="utf-8")
    return tmp_path / "golden"


@pytest.fixture(autouse=True)
def _clear_cache():
    """Clear golden LRU cache before each test."""
    _clear_golden_cache()
    yield
    _clear_golden_cache()


# ---------------------------------------------------------------------------
# GoldenResolution dataclass
# ---------------------------------------------------------------------------

class TestGoldenResolution:
    """Test GoldenResolution dataclass and to_dict."""

    def test_to_dict_contains_all_fields(self):
        res = GoldenResolution(
            match_level="exact",
            matched_heading="Code Examples",
            query_heading="Code Examples",
            page_role="howto_article",
            variant="standard",
            jaccard_score=0.0,
            golden_page_path="/golden/test.md",
            golden_word_count=100,
            has_structural_spec=True,
        )
        d = res.to_dict()
        assert d["match_level"] == "exact"
        assert d["matched_heading"] == "Code Examples"
        assert d["query_heading"] == "Code Examples"
        assert d["page_role"] == "howto_article"
        assert d["variant"] == "standard"
        assert d["jaccard_score"] == 0.0
        assert d["golden_page_path"] == "/golden/test.md"
        assert d["golden_word_count"] == 100
        assert d["has_structural_spec"] is True
        assert len(d) == 9

    def test_to_dict_json_serializable(self):
        res = GoldenResolution(
            match_level="miss",
            matched_heading="",
            query_heading="Test",
            page_role="howto_article",
            variant="standard",
            jaccard_score=0.0,
            golden_page_path="",
            golden_word_count=0,
            has_structural_spec=False,
        )
        serialized = json.dumps(res.to_dict())
        assert isinstance(serialized, str)


# ---------------------------------------------------------------------------
# GoldenIndex.resolve_section
# ---------------------------------------------------------------------------

class TestResolveSection:
    """Test GoldenIndex.resolve_section match levels."""

    def test_exact_match(self, tmp_path):
        golden_dir = _build_golden_dir(tmp_path)
        index = GoldenIndex.load(golden_dir)
        section, res = index.resolve_section("howto_article", "standard", "Code Examples")
        assert section is not None
        assert res.match_level == "exact"
        assert res.matched_heading == "Code Examples"
        assert res.jaccard_score == 0.0
        assert res.golden_word_count > 0

    def test_exact_match_case_insensitive(self, tmp_path):
        golden_dir = _build_golden_dir(tmp_path)
        index = GoldenIndex.load(golden_dir)
        section, res = index.resolve_section("howto_article", "standard", "code examples")
        assert section is not None
        assert res.match_level == "exact"

    def test_substring_match(self, tmp_path):
        golden_dir = _build_golden_dir(tmp_path)
        index = GoldenIndex.load(golden_dir)
        # "Code" is a substring of "Code Examples"
        section, res = index.resolve_section("howto_article", "standard", "Code")
        assert section is not None
        assert res.match_level == "substring"

    def test_jaccard_match(self, tmp_path):
        golden_dir = _build_golden_dir(tmp_path)
        index = GoldenIndex.load(golden_dir)
        # "Started Guide Getting" has Jaccard overlap with "Getting Started Guide"
        section, res = index.resolve_section("howto_article", "standard", "Started Guide Getting")
        assert section is not None
        assert res.match_level == "jaccard"
        assert res.jaccard_score >= 0.5

    def test_miss_no_page(self, tmp_path):
        golden_dir = _build_golden_dir(tmp_path)
        index = GoldenIndex.load(golden_dir)
        section, res = index.resolve_section("nonexistent_role", "standard", "Overview")
        assert section is None
        assert res.match_level == "miss"
        assert res.matched_heading == ""
        assert res.golden_word_count == 0
        assert res.golden_page_path == ""

    def test_miss_no_section(self, tmp_path):
        golden_dir = _build_golden_dir(tmp_path)
        index = GoldenIndex.load(golden_dir)
        section, res = index.resolve_section("howto_article", "standard", "Completely Unrelated Heading That Does Not Match")
        assert section is None
        assert res.match_level == "miss"

    def test_resolution_has_page_path(self, tmp_path):
        golden_dir = _build_golden_dir(tmp_path)
        index = GoldenIndex.load(golden_dir)
        _, res = index.resolve_section("howto_article", "standard", "Overview")
        assert res.golden_page_path != ""

    def test_resolution_has_structural_spec(self, tmp_path):
        golden_dir = _build_golden_dir(tmp_path)
        index = GoldenIndex.load(golden_dir)
        # Code Examples has code and list → has_structural_spec=True
        _, res = index.resolve_section("howto_article", "standard", "Code Examples")
        assert res.has_structural_spec is True


# ---------------------------------------------------------------------------
# get_section backward compat
# ---------------------------------------------------------------------------

class TestGetSectionBackwardCompat:
    """Ensure get_section() still returns GoldenSection | None after refactor."""

    def test_returns_section_on_match(self, tmp_path):
        golden_dir = _build_golden_dir(tmp_path)
        index = GoldenIndex.load(golden_dir)
        result = index.get_section("howto_article", "standard", "Overview")
        assert isinstance(result, GoldenSection)

    def test_returns_none_on_miss(self, tmp_path):
        golden_dir = _build_golden_dir(tmp_path)
        index = GoldenIndex.load(golden_dir)
        result = index.get_section("nonexistent", "standard", "Foo")
        assert result is None


# ---------------------------------------------------------------------------
# resolve_golden_for_section (module-level convenience)
# ---------------------------------------------------------------------------

class TestResolveGoldenForSection:
    """Test the module-level resolve_golden_for_section function."""

    def test_returns_exact_match(self, tmp_path):
        golden_dir = _build_golden_dir(tmp_path)
        res = resolve_golden_for_section("howto_article", golden_dir, "Code Examples")
        assert res.match_level == "exact"
        assert res.page_role == "howto_article"

    def test_role_fallback(self, tmp_path):
        golden_dir = _build_golden_dir(tmp_path)
        # Heading that doesn't match any section, but role exists
        res = resolve_golden_for_section(
            "howto_article", golden_dir, "Totally Unique Heading That Will Never Match Any Golden Section At All"
        )
        assert res.match_level == "role_fallback"
        assert res.page_role == "howto_article"

    def test_miss_when_golden_disabled(self):
        res = resolve_golden_for_section("howto_article", None, "Overview")
        assert res.match_level == "miss"

    def test_miss_when_dir_not_exists(self, tmp_path):
        res = resolve_golden_for_section("howto_article", tmp_path / "nonexistent", "Overview")
        assert res.match_level == "miss"

    def test_always_returns_resolution(self, tmp_path):
        """resolve_golden_for_section never returns None."""
        res = resolve_golden_for_section("fake_role", tmp_path / "nonexistent", "Anything")
        assert isinstance(res, GoldenResolution)
        assert res.match_level == "miss"


# ---------------------------------------------------------------------------
# Metrics integration (golden resolution events → metrics)
# ---------------------------------------------------------------------------

class TestGoldenMetrics:
    """Test calculate_golden_metrics from event log."""

    def test_match_rate(self, tmp_path):
        from launcher.shared.metrics_calculator import calculate_golden_metrics
        events_path = tmp_path / "events.ndjson"
        events = [
            {"event_id": "e1", "event_type": "golden_resolution", "run_id": "r1", "timestamp": "2026-03-17T00:00:00Z", "worker": "generate", "data": {"match_level": "exact", "page_role": "howto", "page_slug": "p1", "query_heading": "h1", "is_heal_mode": False, "heal_attempt": 0}},
            {"event_id": "e2", "event_type": "golden_resolution", "run_id": "r1", "timestamp": "2026-03-17T00:00:01Z", "worker": "generate", "data": {"match_level": "substring", "page_role": "howto", "page_slug": "p1", "query_heading": "h2", "is_heal_mode": False, "heal_attempt": 0}},
            {"event_id": "e3", "event_type": "golden_resolution", "run_id": "r1", "timestamp": "2026-03-17T00:00:02Z", "worker": "generate", "data": {"match_level": "miss", "page_role": "api_ref", "page_slug": "p2", "query_heading": "h3", "is_heal_mode": False, "heal_attempt": 0}},
            {"event_id": "e4", "event_type": "golden_resolution", "run_id": "r1", "timestamp": "2026-03-17T00:00:03Z", "worker": "generate", "data": {"match_level": "role_fallback", "page_role": "howto", "page_slug": "p1", "query_heading": "h4", "is_heal_mode": False, "heal_attempt": 0}},
        ]
        with events_path.open("w", encoding="utf-8") as f:
            for evt in events:
                f.write(json.dumps(evt) + "\n")

        metrics = calculate_golden_metrics(events_path)
        assert metrics["golden_total_sections"] == 4
        assert metrics["golden_match_rate"] == 0.5  # 2 of 4
        assert metrics["golden_fallback_rate"] == 0.25  # 1 of 4
        assert metrics["golden_miss_rate"] == 0.25  # 1 of 4

    def test_level_distribution(self, tmp_path):
        from launcher.shared.metrics_calculator import calculate_golden_metrics
        events_path = tmp_path / "events.ndjson"
        events = [
            {"event_id": "e1", "event_type": "golden_resolution", "run_id": "r1", "timestamp": "2026-03-17T00:00:00Z", "worker": "generate", "data": {"match_level": "exact", "is_heal_mode": False, "heal_attempt": 0}},
            {"event_id": "e2", "event_type": "golden_resolution", "run_id": "r1", "timestamp": "2026-03-17T00:00:01Z", "worker": "generate", "data": {"match_level": "jaccard", "is_heal_mode": False, "heal_attempt": 0}},
            {"event_id": "e3", "event_type": "golden_resolution", "run_id": "r1", "timestamp": "2026-03-17T00:00:02Z", "worker": "generate", "data": {"match_level": "jaccard", "is_heal_mode": False, "heal_attempt": 0}},
        ]
        with events_path.open("w", encoding="utf-8") as f:
            for evt in events:
                f.write(json.dumps(evt) + "\n")

        metrics = calculate_golden_metrics(events_path)
        dist = metrics["golden_match_level_distribution"]
        assert dist["exact"] == 1
        assert dist["jaccard"] == 2

    def test_miss_by_role(self, tmp_path):
        from launcher.shared.metrics_calculator import calculate_golden_metrics
        events_path = tmp_path / "events.ndjson"
        events = [
            {"event_id": "e1", "event_type": "golden_resolution", "run_id": "r1", "timestamp": "2026-03-17T00:00:00Z", "worker": "generate", "data": {"match_level": "miss", "page_role": "api_ref", "page_slug": "p1", "query_heading": "h1", "is_heal_mode": False, "heal_attempt": 0}},
            {"event_id": "e2", "event_type": "golden_resolution", "run_id": "r1", "timestamp": "2026-03-17T00:00:01Z", "worker": "generate", "data": {"match_level": "miss", "page_role": "api_ref", "page_slug": "p2", "query_heading": "h2", "is_heal_mode": False, "heal_attempt": 0}},
            {"event_id": "e3", "event_type": "golden_resolution", "run_id": "r1", "timestamp": "2026-03-17T00:00:02Z", "worker": "generate", "data": {"match_level": "miss", "page_role": "howto", "page_slug": "p3", "query_heading": "h3", "is_heal_mode": False, "heal_attempt": 0}},
        ]
        with events_path.open("w", encoding="utf-8") as f:
            for evt in events:
                f.write(json.dumps(evt) + "\n")

        metrics = calculate_golden_metrics(events_path)
        assert metrics["golden_miss_by_role"]["api_ref"] == 2
        assert metrics["golden_miss_by_role"]["howto"] == 1

    def test_heal_escalation_rate(self, tmp_path):
        from launcher.shared.metrics_calculator import calculate_golden_metrics
        events_path = tmp_path / "events.ndjson"
        events = [
            {"event_id": "e1", "event_type": "golden_resolution", "run_id": "r1", "timestamp": "2026-03-17T00:00:00Z", "worker": "generate", "data": {"match_level": "exact", "is_heal_mode": True, "heal_attempt": 1}},
            {"event_id": "e2", "event_type": "golden_resolution", "run_id": "r1", "timestamp": "2026-03-17T00:00:01Z", "worker": "generate", "data": {"match_level": "exact", "is_heal_mode": True, "heal_attempt": 2}},
            {"event_id": "e3", "event_type": "golden_resolution", "run_id": "r1", "timestamp": "2026-03-17T00:00:02Z", "worker": "generate", "data": {"match_level": "exact", "is_heal_mode": True, "heal_attempt": 3}},
        ]
        with events_path.open("w", encoding="utf-8") as f:
            for evt in events:
                f.write(json.dumps(evt) + "\n")

        metrics = calculate_golden_metrics(events_path)
        assert metrics["golden_heal_sections"] == 3
        # 2 of 3 have attempt > 1
        assert metrics["golden_heal_escalation_rate"] == round(2 / 3, 4)

    def test_empty_events(self, tmp_path):
        from launcher.shared.metrics_calculator import calculate_golden_metrics
        events_path = tmp_path / "events.ndjson"
        events_path.write_text("", encoding="utf-8")
        metrics = calculate_golden_metrics(events_path)
        assert metrics["golden_total_sections"] == 0
        assert metrics["golden_match_rate"] == 0.0

    def test_no_golden_events(self, tmp_path):
        from launcher.shared.metrics_calculator import calculate_golden_metrics
        events_path = tmp_path / "events.ndjson"
        events = [
            {"event_id": "e1", "event_type": "worker_started", "run_id": "r1", "timestamp": "2026-03-17T00:00:00Z", "worker": "generate", "data": {}},
        ]
        with events_path.open("w", encoding="utf-8") as f:
            for evt in events:
                f.write(json.dumps(evt) + "\n")

        metrics = calculate_golden_metrics(events_path)
        assert metrics["golden_total_sections"] == 0


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------

class TestSchemaValidation:
    """Validate event payloads against golden_resolution.schema.json."""

    @staticmethod
    def _load_schema():
        schema_path = Path(__file__).resolve().parents[3].joinpath(
            "specs", "schemas", "event_schemas", "golden_resolution.schema.json"
        )
        return json.loads(schema_path.read_text(encoding="utf-8"))

    def test_valid_exact_match_event(self):
        """A well-formed exact match event validates against the schema."""
        import jsonschema
        schema = self._load_schema()
        res = GoldenResolution(
            match_level="exact",
            matched_heading="Code Examples",
            query_heading="Code Examples",
            page_role="howto_article",
            variant="standard",
            jaccard_score=0.0,
            golden_page_path="golden/test.md",
            golden_word_count=150,
            has_structural_spec=True,
        )
        payload = {
            **res.to_dict(),
            "page_slug": "test-page",
            "section_index": 0,
            "is_heal_mode": False,
            "heal_attempt": 0,
        }
        jsonschema.validate(payload, schema)  # raises on failure

    def test_valid_miss_event(self):
        """A miss event validates against the schema."""
        import jsonschema
        schema = self._load_schema()
        payload = {
            "match_level": "miss",
            "matched_heading": "",
            "query_heading": "Unknown Section",
            "page_role": "api_reference",
            "page_slug": "api-page",
            "section_index": 3,
            "variant": "standard",
            "jaccard_score": 0.0,
            "golden_page_path": "",
            "golden_word_count": 0,
            "has_structural_spec": False,
            "is_heal_mode": False,
            "heal_attempt": 0,
        }
        jsonschema.validate(payload, schema)

    def test_invalid_match_level_rejected(self):
        """An invalid match_level is rejected by the schema."""
        import jsonschema
        schema = self._load_schema()
        payload = {
            "match_level": "invalid_level",
            "matched_heading": "",
            "query_heading": "Test",
            "page_role": "howto",
            "page_slug": "p",
            "section_index": 0,
            "variant": "standard",
            "jaccard_score": 0.0,
            "is_heal_mode": False,
            "heal_attempt": 0,
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(payload, schema)
