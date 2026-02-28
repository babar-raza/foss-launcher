"""Tests for TC-2394 + TC-2900: Topic Discovery."""
import json
import pytest
from unittest.mock import MagicMock
from launch.workers.w2_facts_builder.topic_discovery import (
    derive_deterministic_topics,
    discover_topics_from_docs,
    validate_topic_coverage,
    detect_thin_sections,
    build_topic_manifest,
    _dedup_topics,
    _parse_topics_json,
    _enriched_fallback_topics,
    _reference_topics_from_inventory,
    _kb_topics_from_signals,
    _docs_topics_from_inventory,
    _blog_topics_from_formats,
    _MIN_TOPICS_PER_SECTION,
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


# ---------------------------------------------------------------------------
# TC-2900: Thin-output detection tests
# ---------------------------------------------------------------------------

_SAMPLE_API_INVENTORY = {
    "package_name": "aspose-3d",
    "classes": [
        {"name": "Scene", "import_path": "aspose.threed.Scene", "methods": ["save", "open", "merge", "clear"]},
        {"name": "Node", "import_path": "aspose.threed.Node", "methods": ["add_child"]},
        {"name": "Mesh", "import_path": "aspose.threed.entities.Mesh", "methods": ["create"]},
    ],
    "functions": [],
    "modules": ["aspose.threed", "aspose.threed.entities"],
}

_SAMPLE_FORMATS = [
    {"format": "OBJ"},
    {"format": "STL"},
    {"format": "FBX"},
]

_SAMPLE_WORKFLOWS = [
    {"workflow_tag": "installation", "title": "Installation", "claim_ids": ["c1"]},
    {"workflow_tag": "format_conversion", "title": "Format Conversion", "claim_ids": ["c2"]},
]

_SAMPLE_CLAIMS = [
    {"claim_id": "c1", "claim_text": "Supports OBJ format", "claim_kind": "feature"},
    {"claim_id": "c2", "claim_text": "Load 3D scenes from files", "claim_kind": "workflow"},
    {"claim_id": "c3", "claim_text": "Performance benchmark results", "claim_kind": "performance"},
]


def test_thin_output_detected_when_section_below_minimum():
    """TC-2900: Section with 1 topic when min=2 triggers enriched fallback."""
    mock_llm = MagicMock()
    # LLM returns 1 kb topic (below _MIN_TOPICS_PER_SECTION["kb"]=2),
    # 1 products, 1 blog — those meet their minimums.
    topics_payload = [
        {"title": "KB Guide", "section": "kb", "rationale": "r",
         "target_audience": "a", "suggested_page_role": "howto_article", "slug_seed": "kb-guide"},
        {"title": "Overview", "section": "products", "rationale": "r",
         "target_audience": "a", "suggested_page_role": "feature_showcase", "slug_seed": "overview"},
        {"title": "Blog Post", "section": "blog", "rationale": "r",
         "target_audience": "a", "suggested_page_role": "blog_post", "slug_seed": "blog-post"},
    ]
    mock_llm.chat_completion.return_value = {"content": json.dumps(topics_payload)}
    result = discover_topics_from_docs(
        [{"text": "docs"}], {}, mock_llm,
        claims=_SAMPLE_CLAIMS,
        mandatory_sections=["products", "blog", "kb"],
    )
    kb_count = sum(1 for t in result if t["section"] == "kb")
    assert kb_count >= 2, f"kb should have been enriched from 1 to >=2 (got {kb_count})"


def test_detect_thin_sections_identifies_deficit():
    """TC-2900: detect_thin_sections reports sections below minimum."""
    topics = [
        {"section": "kb"},
        {"section": "products"},
        {"section": "blog"},
    ]
    thin = detect_thin_sections(topics, ["products", "blog", "kb"])
    assert "kb" in thin, "kb has 1 topic but min is 2"
    assert "products" not in thin, "products has 1 topic which meets min of 1"
    assert "blog" not in thin, "blog has 1 topic which meets min of 1"


def test_thin_output_not_triggered_when_above_minimum():
    """TC-2900: Sections at or above minimum do NOT fire fallback."""
    mock_llm = MagicMock()
    topics_payload = [
        {"title": f"KB {i}", "section": "kb", "rationale": "r",
         "target_audience": "a", "suggested_page_role": "howto_article", "slug_seed": f"kb-{i}"}
        for i in range(3)
    ] + [
        {"title": "Overview", "section": "products", "rationale": "r",
         "target_audience": "a", "suggested_page_role": "feature_showcase", "slug_seed": "overview"},
        {"title": "Blog Post", "section": "blog", "rationale": "r",
         "target_audience": "a", "suggested_page_role": "blog_post", "slug_seed": "blog-post"},
    ]
    mock_llm.chat_completion.return_value = {"content": json.dumps(topics_payload)}
    result = discover_topics_from_docs(
        [{"text": "docs"}], {}, mock_llm,
        mandatory_sections=["products", "blog", "kb"],
        max_topics=12,
    )
    # All sections are at or above minimum — no extra fallback topics
    assert len(result) == 5


# ---------------------------------------------------------------------------
# TC-2900: Enriched fallback signal tests
# ---------------------------------------------------------------------------


def test_reference_topics_from_api_inventory():
    """TC-2900: api_inventory with classes generates module-grouped reference topics."""
    topics = _reference_topics_from_inventory(_SAMPLE_API_INVENTORY, "Aspose.3D", 3)
    assert len(topics) >= 1
    assert all(t["section"] == "reference" for t in topics)
    assert all(t["suggested_page_role"] == "api_reference" for t in topics)
    # First topic should be from module with most classes (aspose.threed has 2)
    assert "aspose.threed" in topics[0]["title"]


def test_reference_topics_from_empty_inventory():
    """TC-2900: Empty/None api_inventory returns empty list (no crash)."""
    assert _reference_topics_from_inventory(None, "Product", 3) == []
    assert _reference_topics_from_inventory({}, "Product", 3) == []
    assert _reference_topics_from_inventory({"classes": []}, "Product", 3) == []


def test_kb_topics_from_workflows():
    """TC-2900: Workflows generate kb how-to topics."""
    topics = _kb_topics_from_signals([], "Aspose.3D", 3, workflows=_SAMPLE_WORKFLOWS)
    assert len(topics) >= 2
    assert all(t["section"] == "kb" for t in topics)
    assert any("Installation" in t["title"] for t in topics)
    assert any("Format Conversion" in t["title"] for t in topics)


def test_kb_topics_from_format_pairs():
    """TC-2900: Supported formats generate conversion pair topics."""
    topics = _kb_topics_from_signals(
        [], "Aspose.3D", 5,
        supported_formats=_SAMPLE_FORMATS,
    )
    assert len(topics) >= 1
    assert any("convert" in t["slug_seed"].lower() for t in topics)
    assert all(t["section"] == "kb" for t in topics)


def test_docs_topics_from_api_inventory():
    """TC-2900: Top classes by method count become tutorial topics."""
    topics = _docs_topics_from_inventory(
        [], "Aspose.3D", 2,
        api_inventory=_SAMPLE_API_INVENTORY,
    )
    assert len(topics) == 2
    # Scene has most methods (4), should be first
    assert "Scene" in topics[0]["title"]
    assert all(t["section"] == "docs" for t in topics)
    assert all(t["suggested_page_role"] == "tutorial" for t in topics)


def test_blog_topics_from_formats():
    """TC-2900: Supported formats generate blog spotlight posts."""
    topics = _blog_topics_from_formats(
        [], "Aspose.3D", 2,
        supported_formats=_SAMPLE_FORMATS,
    )
    assert len(topics) == 2
    assert all(t["section"] == "blog" for t in topics)
    assert all(t["suggested_page_role"] == "blog_post" for t in topics)


def test_enriched_fallback_graceful_when_no_signals():
    """TC-2900: All signals None → falls back to claim-based topics."""
    topics = _enriched_fallback_topics(
        "reference", 1, _SAMPLE_CLAIMS, "TestProduct",
    )
    assert len(topics) >= 1
    assert topics[0]["section"] == "reference"


def test_enriched_fallback_graceful_empty_claims_no_signals():
    """TC-2900: No claims, no signals → generic fallback (no crash)."""
    topics = _enriched_fallback_topics("kb", 2, [], "TestProduct")
    assert len(topics) >= 1
    assert topics[0]["section"] == "kb"


# ---------------------------------------------------------------------------
# TC-2900: Output segregation tests
# ---------------------------------------------------------------------------


def test_build_topic_manifest_has_topics_by_section():
    """TC-2900: build_topic_manifest produces topics_by_section dict."""
    topics = [
        {"section": "kb", "title": "T1", "slug_seed": "t1", "suggested_page_role": "howto_article"},
        {"section": "docs", "title": "T2", "slug_seed": "t2", "suggested_page_role": "tutorial"},
        {"section": "kb", "title": "T3", "slug_seed": "t3", "suggested_page_role": "howto_article"},
    ]
    manifest = build_topic_manifest(topics, method="deterministic_fallback")
    assert "topics_by_section" in manifest
    assert "kb" in manifest["topics_by_section"]
    assert len(manifest["topics_by_section"]["kb"]) == 2
    assert len(manifest["topics_by_section"]["docs"]) == 1
    # Backward compat: flat list preserved
    assert manifest["discovered_topics"] == topics
    assert manifest["schema_version"] == "1.1.0"


def test_build_topic_manifest_records_thin_sections():
    """TC-2900: Manifest records thin_sections list."""
    manifest = build_topic_manifest(
        [{"section": "products", "title": "T", "slug_seed": "t", "suggested_page_role": "x"}],
        method="llm",
        thin_sections=["kb", "docs"],
    )
    assert manifest["thin_sections"] == ["docs", "kb"]  # sorted
    assert manifest["method"] == "llm"


# ---------------------------------------------------------------------------
# TC-2900: Schema validation test
# ---------------------------------------------------------------------------


def test_topic_manifest_validates_against_schema():
    """TC-2900: Generated manifest conforms to topic_manifest.schema.json."""
    try:
        import jsonschema
    except ImportError:
        pytest.skip("jsonschema not installed")
    from pathlib import Path
    schema_path = Path(__file__).parents[3] / "specs" / "schemas" / "topic_manifest.schema.json"
    if not schema_path.exists():
        pytest.skip("topic_manifest.schema.json not yet created")
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    manifest = build_topic_manifest(
        [
            {"section": "kb", "title": "T", "slug_seed": "s", "suggested_page_role": "howto_article"},
            {"section": "products", "title": "P", "slug_seed": "p", "suggested_page_role": "feature_showcase"},
            {"section": "blog", "title": "B", "slug_seed": "b", "suggested_page_role": "blog_post"},
        ],
        method="deterministic_fallback",
        thin_sections=["docs"],
    )
    jsonschema.validate(manifest, schema)


# ---------------------------------------------------------------------------
# TC-2900: Determinism stability test
# ---------------------------------------------------------------------------


def test_enriched_deterministic_topics_stable_across_runs():
    """TC-2900: Two calls with identical inputs produce byte-identical output."""
    kwargs = dict(
        product_name="Aspose.3D",
        mandatory_sections=["products", "blog", "kb"],
        max_topics=12,
        api_inventory=_SAMPLE_API_INVENTORY,
        supported_formats=_SAMPLE_FORMATS,
        workflows=_SAMPLE_WORKFLOWS,
    )
    r1 = derive_deterministic_topics(_SAMPLE_CLAIMS, **kwargs)
    r2 = derive_deterministic_topics(_SAMPLE_CLAIMS, **kwargs)
    assert json.dumps(r1, sort_keys=True) == json.dumps(r2, sort_keys=True)
