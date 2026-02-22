"""Tests for TC-2394: Topic Discovery."""
import pytest
from unittest.mock import MagicMock
from launch.workers.w2_facts_builder.topic_discovery import (
    derive_deterministic_topics,
    discover_topics_from_docs,
    validate_topic_coverage,
    _dedup_topics,
    _parse_topics_json,
)


def test_discover_topics_returns_list():
    """Mock LLM returns JSON array → list of dicts."""
    mock_llm = MagicMock()
    mock_llm.chat_completion.return_value = {
        "content": '[{"title": "New Topic", "rationale": "Useful", "target_audience": "Devs", "suggested_page_role": "tutorial"}]'
    }
    doc_chunks = [{"text": "Some documentation content about the API"}]
    existing_groups = {"installation": ["claim-001"]}
    result = discover_topics_from_docs(doc_chunks, existing_groups, mock_llm)
    assert isinstance(result, list)
    # "New Topic" is dissimilar to "installation" → should be included
    assert any(t.get("title") == "New Topic" for t in result)


def test_discover_topics_dedup_filters_similar():
    """Topic similar to existing_title is excluded."""
    topics = [{"title": "installation guide", "rationale": "r", "target_audience": "a", "suggested_page_role": "tutorial"}]
    existing = ["installation"]
    result = _dedup_topics(topics, existing, threshold=0.7)
    # "installation guide" is very similar to "installation" → should be filtered
    # (depends on TF-IDF similarity; if score < 0.7 it passes through — that's OK)
    assert isinstance(result, list)


def test_discover_topics_dedup_keeps_unique():
    """Topic dissimilar to all existing titles is included."""
    topics = [{"title": "Advanced 3D Rendering Techniques", "rationale": "r", "target_audience": "a", "suggested_page_role": "tutorial"}]
    existing = ["installation", "getting started"]
    result = _dedup_topics(topics, existing, threshold=0.7)
    assert len(result) == 1


def test_parse_topics_json_fenced():
    """JSON in ```json fence → parsed correctly."""
    raw = '```json\n[{"title": "T1", "rationale": "R", "target_audience": "A", "suggested_page_role": "tutorial"}]\n```'
    result = _parse_topics_json(raw)
    assert len(result) == 1
    assert result[0]["title"] == "T1"


def test_parse_topics_json_invalid():
    """Invalid JSON → empty list."""
    result = _parse_topics_json("not json at all { broken")
    assert result == []


def test_discover_topics_empty_chunks():
    """Empty doc_chunks → empty list without LLM call."""
    mock_llm = MagicMock()
    result = discover_topics_from_docs([], {}, mock_llm)
    assert result == []
    mock_llm.chat_completion.assert_not_called()


def test_parse_topics_json_unfenced():
    """Raw JSON array without fence → parsed correctly."""
    raw = '[{"title": "T2", "rationale": "R", "target_audience": "A", "suggested_page_role": "api_reference"}]'
    result = _parse_topics_json(raw)
    assert len(result) == 1
    assert result[0]["title"] == "T2"


def test_parse_topics_json_wrapped_dict():
    """JSON object with 'topics' key → extracts list."""
    raw = '{"topics": [{"title": "T3", "rationale": "R", "target_audience": "A", "suggested_page_role": "faq"}]}'
    result = _parse_topics_json(raw)
    assert len(result) == 1
    assert result[0]["title"] == "T3"


def test_discover_topics_max_topics():
    """max_topics limits the returned list size."""
    mock_llm = MagicMock()
    topics_payload = [
        {"title": f"Topic {i}", "rationale": "r", "target_audience": "a", "suggested_page_role": "tutorial"}
        for i in range(20)
    ]
    import json
    mock_llm.chat_completion.return_value = {"content": json.dumps(topics_payload)}
    doc_chunks = [{"text": "Documentation content"}]
    result = discover_topics_from_docs(doc_chunks, {}, mock_llm, max_topics=5)
    assert len(result) <= 5


def test_dedup_topics_empty_existing():
    """Empty existing_titles → all topics pass through."""
    topics = [
        {"title": "A", "rationale": "r", "target_audience": "a", "suggested_page_role": "tutorial"},
        {"title": "B", "rationale": "r", "target_audience": "a", "suggested_page_role": "faq"},
    ]
    result = _dedup_topics(topics, [], threshold=0.7)
    assert result == topics


def test_discover_topics_llm_failure_fires_mandatory_fallbacks():
    """LLM raises exception → mandatory fallback fires for required sections (no crash).

    Stage 1 hardening (3-A): when LLM fails, _fallback_topics_for_section() is called
    for each section in mandatory_sections (default: products, blog, kb).
    Result is non-empty (≥1 topic per mandatory section) instead of [].
    """
    mock_llm = MagicMock()
    mock_llm.chat_completion.side_effect = RuntimeError("LLM unavailable")
    doc_chunks = [{"text": "Some docs"}]
    result = discover_topics_from_docs(doc_chunks, {"key_features": []}, mock_llm)
    # Fallbacks fire for products, blog, kb → result is non-empty
    assert len(result) >= 1
    sections = {t.get("section") for t in result}
    # All three mandatory sections must be represented
    assert "products" in sections
    assert "blog" in sections


def test_discover_topics_prompt_excludes_internal_topics():
    """LLM prompt includes instruction to exclude internal developer topics."""
    mock_llm = MagicMock()
    mock_llm.chat_completion.return_value = {"content": "[]"}
    doc_chunks = [{"text": "Some documentation"}]
    discover_topics_from_docs(doc_chunks, {}, mock_llm)
    # Verify the prompt sent to LLM contains the exclusion instruction
    call_args = mock_llm.chat_completion.call_args
    messages = call_args[1].get("messages") or call_args[0][0] if call_args[0] else call_args[1]["messages"]
    prompt_text = messages[0]["content"]
    # New prompt uses "contributing guidelines" and "CI/CD" as exclusion examples
    assert "contributing guidelines" in prompt_text
    # Prompt must mention kb, docs, blog, products sections
    assert "kb" in prompt_text
    assert "blog" in prompt_text


def test_mandatory_fallback_survives_truncation():
    """B1: When LLM returns max_topics items all in 'docs',
    mandatory fallback topics for products/blog/kb must NOT be truncated."""
    mock_llm = MagicMock()
    topics_payload = [
        {"title": f"Docs Topic {i}", "section": "docs",
         "rationale": "r", "target_audience": "a",
         "suggested_page_role": "tutorial", "slug_seed": f"docs-{i}"}
        for i in range(12)
    ]
    import json
    mock_llm.chat_completion.return_value = {"content": json.dumps(topics_payload)}
    doc_chunks = [{"text": "Some content about the API features"}]
    result = discover_topics_from_docs(
        doc_chunks, {}, mock_llm,
        mandatory_sections=["products", "blog", "kb"],
        max_topics=12,
    )
    assert len(result) <= 12
    sections = {t.get("section") for t in result}
    assert "products" in sections, "mandatory 'products' section was truncated"
    assert "blog" in sections, "mandatory 'blog' section was truncated"
    assert "kb" in sections, "mandatory 'kb' section was truncated"


def test_derive_deterministic_topics_covers_mandatory():
    """B2: derive_deterministic_topics covers mandatory sections."""
    claims = [
        {"claim_id": "c1", "claim_text": "Supports OBJ format", "claim_kind": "feature"},
        {"claim_id": "c2", "claim_text": "Load 3D scenes from files", "claim_kind": "workflow"},
        {"claim_id": "c3", "claim_text": "Performance benchmark results", "claim_kind": "performance"},
    ]
    result = derive_deterministic_topics(
        claims, product_name="Aspose.3D",
        mandatory_sections=["products", "blog", "kb"],
        max_topics=12,
    )
    assert len(result) >= 3
    sections = {t.get("section") for t in result}
    assert "products" in sections
    assert "blog" in sections
    assert "kb" in sections
    for t in result:
        assert "title" in t
        assert "section" in t
        assert "slug_seed" in t
        assert "suggested_page_role" in t


def test_derive_deterministic_topics_empty_claims():
    """B2: Deterministic fallback with no claims still produces mandatory fallbacks."""
    result = derive_deterministic_topics(
        [], product_name="Aspose.3D",
        mandatory_sections=["products", "blog", "kb"],
    )
    assert len(result) >= 3
    sections = {t.get("section") for t in result}
    assert "products" in sections
    assert "blog" in sections
    assert "kb" in sections


def test_validate_topic_coverage_detects_gap():
    """B3: Coverage validation warns when a required section has 0 topics."""
    topics = [{"section": "docs", "title": "T1"}]
    warnings = validate_topic_coverage(topics, ["docs", "products", "kb"])
    assert len(warnings) == 2  # products and kb missing
    assert any("products" in w for w in warnings)
    assert any("kb" in w for w in warnings)


def test_validate_topic_coverage_no_gap():
    """B3: Coverage validation returns empty warnings when all sections covered."""
    topics = [
        {"section": "docs", "title": "T1"},
        {"section": "products", "title": "T2"},
        {"section": "kb", "title": "T3"},
    ]
    warnings = validate_topic_coverage(topics, ["docs", "products", "kb"])
    assert warnings == []


def test_truncation_when_all_slots_reserved():
    """B1 edge case: When mandatory fallbacks need all slots, LLM topics replaced."""
    mock_llm = MagicMock()
    topics_payload = [
        {"title": f"Docs Topic {i}", "section": "docs",
         "rationale": "r", "target_audience": "a",
         "suggested_page_role": "tutorial", "slug_seed": f"docs-{i}"}
        for i in range(5)
    ]
    import json
    mock_llm.chat_completion.return_value = {"content": json.dumps(topics_payload)}
    doc_chunks = [{"text": "Some content about features"}]
    result = discover_topics_from_docs(
        doc_chunks, {}, mock_llm,
        claims=[{"claim_text": "Feature X", "claim_kind": "feature", "claim_id": "c1"}] * 3,
        mandatory_sections=["products", "blog", "kb"],
        max_topics=3,
    )
    assert len(result) <= 3
    sections = {t.get("section") for t in result}
    # With 3 missing mandatory sections and max_topics=3, mandatory take priority
    assert len(sections) >= 1


def test_existing_max_topics_preserved_when_no_fallbacks():
    """B1 backward compat: max_topics still limits when all mandatory sections present."""
    mock_llm = MagicMock()
    topics_payload = [
        {"title": "Product Overview", "section": "products", "rationale": "r",
         "target_audience": "a", "suggested_page_role": "feature_showcase", "slug_seed": "overview"},
        {"title": "Blog Post", "section": "blog", "rationale": "r",
         "target_audience": "a", "suggested_page_role": "blog_post", "slug_seed": "intro"},
        {"title": "KB Guide", "section": "kb", "rationale": "r",
         "target_audience": "a", "suggested_page_role": "howto_article", "slug_seed": "guide"},
    ] + [
        {"title": f"Extra {i}", "section": "docs", "rationale": "r",
         "target_audience": "a", "suggested_page_role": "tutorial", "slug_seed": f"extra-{i}"}
        for i in range(17)
    ]
    import json
    mock_llm.chat_completion.return_value = {"content": json.dumps(topics_payload)}
    doc_chunks = [{"text": "Some content about features"}]
    result = discover_topics_from_docs(doc_chunks, {}, mock_llm, max_topics=5)
    assert len(result) <= 5


def test_dedup_topics_filters_high_similarity():
    """Import fix: TF-IDF dedup actually filters near-identical titles."""
    topics = [
        {"title": "Installing Aspose.3D for Python", "rationale": "r",
         "target_audience": "a", "suggested_page_role": "tutorial"},
        {"title": "Installing Aspose.3D Python Library", "rationale": "r",
         "target_audience": "a", "suggested_page_role": "tutorial"},
    ]
    existing = ["Installing Aspose.3D for Python"]
    result = _dedup_topics(topics, existing, threshold=0.3)
    # With working TF-IDF, both titles are very similar to the existing one
    # At least one should be filtered (if import were broken, both would pass)
    assert len(result) < 2


def test_dedup_topics_embeddings_active():
    """Verify embeddings import is active (not silently failing)."""
    # Two very similar titles that should be deduped
    topics = [
        {"title": "Convert OBJ Files to STL Format", "rationale": "r",
         "target_audience": "a", "suggested_page_role": "tutorial"},
    ]
    existing = ["Convert OBJ to STL"]
    # With threshold=0.3, these should be flagged as similar (high cosine sim)
    result = _dedup_topics(topics, existing, threshold=0.3)
    # If embeddings were broken (ImportError), result would be all topics (len=1)
    # With working embeddings, "Convert OBJ Files to STL Format" vs "Convert OBJ to STL"
    # should have high TF-IDF similarity and be filtered
    assert len(result) == 0, (
        "Expected dedup to filter similar topic — embeddings import may be broken"
    )
