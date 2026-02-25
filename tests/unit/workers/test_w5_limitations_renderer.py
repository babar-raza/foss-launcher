"""Tests for limitations_renderer.py -- TC-2444, TC-2446."""
import pytest
from launch.workers.w5_section_writer.renderers.limitations_renderer import (
    parse_limitations_json,
    render_limitations_to_markdown,
    is_structured_mode,
)


# ---- Raw JSON payloads (LLM output simulation) ----
RAW_BARE = '[{"title": "Memory Usage", "description": "High memory consumption at scale.", "workaround": null}]'
_NL = chr(10)
_BT = chr(96) * 3
RAW_FENCE_JSON = (_BT + "json" + _NL
    + '[{"title": "Limit A", "description": "Description of limit A here.", "workaround": "Use option B"}]'
    + _NL + _BT)
RAW_FENCE_PLAIN = (_BT + _NL
    + '[{"title": "Limit B", "description": "Another limitation description.", "workaround": null}]'
    + _NL + _BT)
RAW_PROSE = ("Here are the limitations:" + _NL
    + '[{"title": "API Rate Limit", "description": "Rate limits apply to all endpoints.", "workaround": null}]')
RAW_NO_TITLE = '[{"description": "Some description here that is long enough.", "workaround": null}]'
RAW_SHORT_TITLE = '[{"title": "AB", "description": "Some description that is long enough.", "workaround": null}]'
RAW_SHORT_DESC = '[{"title": "Memory Usage", "description": "Short", "workaround": null}]'
RAW_NULL_WA = '[{"title": "Memory Usage", "description": "Memory usage can be high for large files.", "workaround": null}]'
RAW_MULTI = ('[{"title": "Memory Limit", "description": "High memory at large scale.", "workaround": "Use streaming"}, '
    '{"title": "Thread Safety", "description": "Not thread-safe by default.", "workaround": null}]')
RAW_BAD_GOOD = ('[{"title": "AB", "description": "Too short desc.", "workaround": null}, '
    '{"title": "Valid Title", "description": "This is a valid description that is long enough.", "workaround": null}]')
RAW_EMPTY_WA = '[{"title": "Memory Usage", "description": "High memory for large files.", "workaround": ""}]'


class TestParseLimitationsJson:
    def test_bare_json_array(self):
        result = parse_limitations_json(RAW_BARE)
        assert result is not None
        assert len(result) == 1
        assert result[0]["title"] == "Memory Usage"

    def test_json_inside_json_fence(self):
        result = parse_limitations_json(RAW_FENCE_JSON)
        assert result is not None
        assert result[0]["title"] == "Limit A"

    def test_json_inside_plain_fence(self):
        result = parse_limitations_json(RAW_FENCE_PLAIN)
        assert result is not None

    def test_strips_preamble_prose(self):
        result = parse_limitations_json(RAW_PROSE)
        assert result is not None
        assert result[0]["title"] == "API Rate Limit"

    def test_rejects_missing_title(self):
        result = parse_limitations_json(RAW_NO_TITLE)
        assert result is None

    def test_rejects_short_title(self):
        result = parse_limitations_json(RAW_SHORT_TITLE)
        assert result is None

    def test_rejects_short_description(self):
        result = parse_limitations_json(RAW_SHORT_DESC)
        assert result is None

    def test_null_workaround_accepted(self):
        result = parse_limitations_json(RAW_NULL_WA)
        assert result is not None
        assert result[0]["workaround"] is None

    def test_returns_none_on_invalid_json(self):
        result = parse_limitations_json("This is not JSON at all!")
        assert result is None

    def test_returns_none_on_empty_input(self):
        assert parse_limitations_json("") is None
        assert parse_limitations_json(None) is None
        assert parse_limitations_json("   ") is None

    def test_multiple_items_all_validated(self):
        result = parse_limitations_json(RAW_MULTI)
        assert result is not None
        assert len(result) == 2

    def test_filters_invalid_items_keeps_valid(self):
        result = parse_limitations_json(RAW_BAD_GOOD)
        assert result is not None
        assert len(result) == 1
        assert result[0]["title"] == "Valid Title"

    def test_workaround_empty_string_becomes_none(self):
        result = parse_limitations_json(RAW_EMPTY_WA)
        assert result is not None
        assert result[0]["workaround"] is None


class TestRenderLimitationsToMarkdown:
    def test_empty_items_returns_fallback_message(self):
        result = render_limitations_to_markdown([], "Aspose.3D")
        assert "Aspose.3D" in result
        assert result.strip()

    def test_renders_title_and_description(self):
        items = [{"title": "Memory Usage", "description": "High memory at scale.", "workaround": None}]
        result = render_limitations_to_markdown(items, "Aspose.3D")
        assert "Memory Usage" in result
        assert "High memory at scale." in result

    def test_renders_workaround_when_present(self):
        items = [{"title": "Memory Usage", "description": "High memory at scale.", "workaround": "Use streaming"}]
        result = render_limitations_to_markdown(items, "Aspose.3D")
        assert "Workaround" in result
        assert "Use streaming" in result

    def test_skips_workaround_when_none(self):
        items = [{"title": "Memory Usage", "description": "High memory at scale.", "workaround": None}]
        result = render_limitations_to_markdown(items, "Aspose.3D")
        assert "Workaround" not in result

    def test_embeds_claim_ids_as_comments(self):
        items = [{"title": "Memory Usage", "description": "High memory at scale.", "workaround": None}]
        result = render_limitations_to_markdown(items, "Aspose.3D", claim_ids=["claim_abc123"])
        assert "<!-- claim: claim_abc123 -->" in result

    def test_deterministic_same_output_twice(self):
        items = [
            {"title": "Limit A", "description": "Description for limit A.", "workaround": None},
            {"title": "Limit B", "description": "Description for limit B.", "workaround": "Use C"},
        ]
        result1 = render_limitations_to_markdown(items, "MyProduct")
        result2 = render_limitations_to_markdown(items, "MyProduct")
        assert result1 == result2

    def test_claim_ids_shorter_than_items_no_error(self):
        items = [
            {"title": "Limit A", "description": "Description A enough text.", "workaround": None},
            {"title": "Limit B", "description": "Description B enough text.", "workaround": None},
        ]
        result = render_limitations_to_markdown(items, "Prod", claim_ids=["only_one"])
        assert "Limit A" in result
        assert "Limit B" in result

    def test_product_name_appears_in_intro(self):
        items = [{"title": "Some Limit", "description": "A limitation description here.", "workaround": None}]
        result = render_limitations_to_markdown(items, "Aspose.Cells")
        assert "Aspose.Cells" in result

    def test_no_claim_ids_no_comment_markers(self):
        items = [{"title": "Memory Usage", "description": "High memory at scale.", "workaround": None}]
        result = render_limitations_to_markdown(items, "Aspose.3D")
        assert "<!-- claim:" not in result

    def test_title_rendered_as_bold(self):
        items = [{"title": "Thread Safety", "description": "Not thread safe by default.", "workaround": None}]
        result = render_limitations_to_markdown(items, "MyProd")
        assert "**Thread Safety**" in result


class TestIsStructuredMode:
    def test_returns_true_when_json(self):
        import launch.workers.w5_section_writer.renderers.limitations_renderer as m
        original = m._STRUCTURED_MODE
        m._STRUCTURED_MODE = "json"
        assert m.is_structured_mode() is True
        m._STRUCTURED_MODE = original

    def test_returns_false_when_freeform(self):
        import launch.workers.w5_section_writer.renderers.limitations_renderer as m
        original = m._STRUCTURED_MODE
        m._STRUCTURED_MODE = "freeform"
        assert m.is_structured_mode() is False
        m._STRUCTURED_MODE = original

    def test_returns_false_for_unknown_value(self):
        import launch.workers.w5_section_writer.renderers.limitations_renderer as m
        original = m._STRUCTURED_MODE
        m._STRUCTURED_MODE = "something_else"
        assert m.is_structured_mode() is False
        m._STRUCTURED_MODE = original


class TestFeatureFlagEnvVar:
    def test_freeform_mode_when_env_not_set(self, monkeypatch):
        """Default (env var absent) → is_structured_mode() returns False."""
        monkeypatch.delenv("LAUNCH_STRUCTURED_LIMITATIONS", raising=False)
        import launch.workers.w5_section_writer.renderers.limitations_renderer as m
        m._STRUCTURED_MODE = "freeform"
        assert m.is_structured_mode() is False

    def test_json_mode_when_mode_set_to_json(self, monkeypatch):
        """When _STRUCTURED_MODE patched to 'json' → is_structured_mode() returns True."""
        import launch.workers.w5_section_writer.renderers.limitations_renderer as m
        original = m._STRUCTURED_MODE
        m._STRUCTURED_MODE = "json"
        assert m.is_structured_mode() is True
        m._STRUCTURED_MODE = original

    def test_structured_output_passes_content_sanitizer(self):
        """Structured markdown output is clean — key sanitizers leave content unchanged."""
        from launch.workers.w5_section_writer.renderers.limitations_renderer import (
            render_limitations_to_markdown,
        )
        from launch.workers._shared.content_sanitizer import (
            strip_llm_scaffolding,
            fix_heading_missing_space,
        )
        items = [{"title": "Memory Usage", "description": "High memory for large files.", "workaround": None}]
        md = render_limitations_to_markdown(items, "Aspose.3D")
        # Structured output should not be modified by these sanitizers
        assert strip_llm_scaffolding(md) == md
        assert fix_heading_missing_space(md) == md
        assert "Memory Usage" in md
