"""Stage 1 W2 hardening tests.

Tests covering the new/modified behaviors introduced in the Stage 1 hardening plan:
- topic_discovery.py: section-scoped output, mandatory section fallbacks, dedup behaviour,
  claims-as-primary-signal
- extract_claims.py: LLM topic clustering, backward-compat clustering without llm_topics,
  detect_format_conversions without llm_client, multi-statement code detection

Spec: specs/21_worker_contracts.md (W2 FactsBuilder contract)
"""

import json
import pytest
from unittest.mock import MagicMock

from launch.workers.w2_facts_builder.topic_discovery import (
    discover_topics_from_docs,
    _fallback_topics_for_section,
    _dedup_topics,
    _parse_topics_json,
)
from launch.workers.w2_facts_builder.extract_claims import (
    _is_code_like,
    _cluster_claims_by_topic,
    detect_format_conversions,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_llm_returning(topics: list) -> MagicMock:
    """Build a mock LLM client that returns *topics* as a JSON string."""
    mock_llm = MagicMock()
    mock_llm.chat_completion.return_value = {"content": json.dumps(topics)}
    return mock_llm


def _make_topic(section: str, title: str) -> dict:
    """Minimal topic dict that passes _parse_topics_json and section checks."""
    return {
        "section": section,
        "title": title,
        "intent": "test intent",
        "source_evidence": [],
        "keywords": [title.lower().split()[0]],
        "slug_seed": title.lower().replace(" ", "-")[:40],
        "rationale": "test rationale",
        "target_audience": "Developer",
        "suggested_page_role": "howto_article",
    }


def _make_claim(claim_id: str, claim_text: str) -> dict:
    return {"claim_id": claim_id, "claim_text": claim_text}


# ---------------------------------------------------------------------------
# T1.1 — section-scoped output
# ---------------------------------------------------------------------------

def test_t1_1_section_scoped_output():
    """LLM returns topics with section='kb' and section='products' → both sections present.

    Verifies that discover_topics_from_docs preserves the section field returned by
    the LLM rather than overwriting it with a default.
    """
    topics_payload = [
        _make_topic("kb", "How to Load a Scene"),
        _make_topic("products", "Aspose 3D Product Overview"),
    ]
    mock_llm = _make_llm_returning(topics_payload)
    doc_chunks = [{"text": "Sample documentation content about loading scenes"}]

    result = discover_topics_from_docs(
        doc_chunks,
        {},
        mock_llm,
        mandatory_sections=[],  # disable mandatory fallbacks for this test
    )

    sections = {t.get("section") for t in result}
    assert "kb" in sections, f"Expected 'kb' in sections, got {sections}"
    assert "products" in sections, f"Expected 'products' in sections, got {sections}"


# ---------------------------------------------------------------------------
# T1.2 — mandatory fallback for products
# ---------------------------------------------------------------------------

def test_t1_2_mandatory_fallback_products():
    """LLM returns only kb+docs topics → products fallback fires → products in output."""
    topics_payload = [
        _make_topic("kb", "How to Load a Scene"),
        _make_topic("docs", "API Usage Guide"),
    ]
    mock_llm = _make_llm_returning(topics_payload)
    doc_chunks = [{"text": "Documentation content"}]

    result = discover_topics_from_docs(
        doc_chunks,
        {},
        mock_llm,
        product_name="Aspose.3D",
        mandatory_sections=["products"],
    )

    sections = {t.get("section") for t in result}
    assert "products" in sections, (
        f"Expected mandatory fallback to add 'products' topic, got sections: {sections}"
    )
    # Verify the fallback title format
    products_topics = [t for t in result if t.get("section") == "products"]
    assert any("Aspose.3D" in t.get("title", "") for t in products_topics), (
        f"Expected product name in fallback title, got: {[t.get('title') for t in products_topics]}"
    )


# ---------------------------------------------------------------------------
# T1.3 — mandatory fallback for blog
# ---------------------------------------------------------------------------

def test_t1_3_mandatory_fallback_blog():
    """LLM returns only kb+docs topics → blog fallback fires → blog in output."""
    topics_payload = [
        _make_topic("kb", "How to Load a Scene"),
        _make_topic("docs", "API Usage Guide"),
    ]
    mock_llm = _make_llm_returning(topics_payload)
    doc_chunks = [{"text": "Documentation content"}]

    result = discover_topics_from_docs(
        doc_chunks,
        {},
        mock_llm,
        product_name="Aspose.Note",
        mandatory_sections=["blog"],
    )

    sections = {t.get("section") for t in result}
    assert "blog" in sections, (
        f"Expected mandatory fallback to add 'blog' topic, got sections: {sections}"
    )
    blog_topics = [t for t in result if t.get("section") == "blog"]
    assert any("Aspose.Note" in t.get("title", "") for t in blog_topics), (
        f"Expected product name in blog fallback title, got: {[t.get('title') for t in blog_topics]}"
    )


# ---------------------------------------------------------------------------
# T1.4 — short claim_group keys don't block topics
# ---------------------------------------------------------------------------

def test_t1_4_short_claim_group_keys_dont_block_dedup():
    """claim_groups with keys like 'key_features' don't trigger dedup for real topics.

    The dedup gate only considers title-like strings (> 2 words). Short keys such as
    'key_features' and 'install_steps' must NOT block genuinely new topics.
    """
    # These keys have <= 2 words when split by spaces (underscores are not spaces)
    existing_claim_groups = {
        "key_features": ["id1", "id2"],
        "install_steps": ["id3"],
        "api_surface": ["id4"],
    }
    topics_payload = [
        _make_topic("kb", "How to Convert OBJ to STL"),
        _make_topic("docs", "Mesh Rendering Walkthrough"),
    ]
    mock_llm = _make_llm_returning(topics_payload)
    doc_chunks = [{"text": "Documentation about converting 3D files"}]

    result = discover_topics_from_docs(
        doc_chunks,
        existing_claim_groups,
        mock_llm,
        mandatory_sections=[],
    )

    # All topics should pass through because none of the claim_group keys are
    # title-like strings (> 2 words)
    result_titles = {t.get("title") for t in result}
    assert "How to Convert OBJ to STL" in result_titles, (
        f"Topic should not have been deduped by short claim_group key. Got: {result_titles}"
    )


# ---------------------------------------------------------------------------
# T1.5 — claims used as primary input
# ---------------------------------------------------------------------------

def test_t1_5_claims_used_as_primary_input():
    """When claims provided with 5 items, LLM called with those claims in prompt."""
    mock_llm = MagicMock()
    mock_llm.chat_completion.return_value = {"content": "[]"}

    claims = [
        _make_claim(f"claim-{i:03d}", f"The library can perform operation {i} on mesh data")
        for i in range(5)
    ]
    doc_chunks = [{"text": "Some generic documentation"}]

    discover_topics_from_docs(
        doc_chunks,
        {},
        mock_llm,
        claims=claims,
        mandatory_sections=[],
    )

    assert mock_llm.chat_completion.called, "LLM should have been called"
    call_args = mock_llm.chat_completion.call_args
    # Extract messages from call args (could be positional or keyword)
    if call_args.kwargs.get("messages"):
        messages = call_args.kwargs["messages"]
    else:
        messages = call_args.args[0] if call_args.args else call_args.kwargs["messages"]

    prompt_text = messages[0]["content"]
    # The prompt must contain text from the claims (claims used as primary signal)
    assert "operation 0 on mesh data" in prompt_text, (
        f"Expected claim text in prompt, got prompt start: {prompt_text[:500]}"
    )


# ---------------------------------------------------------------------------
# T1.6 — LLM topic clustering replaces hardcoded keywords
# ---------------------------------------------------------------------------

def test_t1_6_llm_topic_clustering_replaces_hardcoded():
    """_cluster_claims_by_topic with llm_topics=[{slug, keywords}] groups mesh claims.

    When llm_topics is provided, the function should use those keyword sets for
    clustering rather than the hardcoded topic_keywords dict.
    """
    claims = [
        _make_claim("c-001", "The library handles mesh vertex data efficiently"),
        _make_claim("c-002", "Mesh normals can be computed automatically from vertex positions"),
        _make_claim("c-003", "Convert mesh data between different vertex formats"),
    ]
    llm_topics = [{"slug": "mesh-operations", "keywords": ["mesh", "vertex"]}]

    result = _cluster_claims_by_topic(claims, llm_topics=llm_topics)

    assert "mesh-operations" in result, (
        f"Expected 'mesh-operations' cluster from llm_topics, got clusters: {list(result.keys())}"
    )
    cluster = result["mesh-operations"]
    assert "c-001" in cluster, "Claim c-001 contains 'mesh' keyword — should be in cluster"
    assert "c-002" in cluster, "Claim c-002 contains 'mesh'/'vertex' — should be in cluster"
    assert "c-003" in cluster, "Claim c-003 contains 'mesh'/'vertex' — should be in cluster"


# ---------------------------------------------------------------------------
# T1.7 — backward compat without llm_topics
# ---------------------------------------------------------------------------

def test_t1_7_backward_compat_without_llm_topics():
    """_cluster_claims_by_topic(claims) without llm_topics → hardcoded keywords used.

    When llm_topics is not supplied, the function falls back to the hardcoded
    topic_keywords dict (pdf-operations, formatting, chart-operations, etc.).
    """
    claims = [
        _make_claim("c-pdf-1", "Export the document as a PDF file for distribution"),
        _make_claim("c-pdf-2", "Save the chart as PDF with vector rendering"),
        _make_claim("c-pdf-3", "Render the spreadsheet to PDF with high fidelity"),
    ]

    # Call WITHOUT llm_topics — uses hardcoded keywords
    result = _cluster_claims_by_topic(claims)

    # pdf-operations cluster keyword set includes "pdf", "export", "save", "render"
    assert "pdf-operations" in result, (
        f"Expected 'pdf-operations' cluster from hardcoded keywords, got: {list(result.keys())}"
    )
    assert len(result["pdf-operations"]) == 3


# ---------------------------------------------------------------------------
# T1.8 — detect_format_conversions no LLM → no crash
# ---------------------------------------------------------------------------

def test_t1_8_detect_format_conversions_no_llm_client():
    """detect_format_conversions(claims=[], api_surface={}) works without llm_client.

    Ensures backward compatibility: when llm_client is None (default), the function
    should use the regex path only and not crash.
    """
    result = detect_format_conversions(claims=[], api_surface={})

    assert isinstance(result, dict), "Result must be a dict"
    assert "format_conversions" in result
    assert "conversion_pairs" in result
    assert "how_to_clusters" in result
    assert result["format_conversions"] == []
    assert result["conversion_pairs"] == []


# ---------------------------------------------------------------------------
# T1.9 — multi-statement code rejected as claim
# ---------------------------------------------------------------------------

def test_t1_9_multi_statement_code_rejected():
    """text with 'has_normals = True\\nprint(has_normals)' → _is_code_like returns True.

    The _MULTI_STMT_RE regex must detect at least 2 statement-like patterns in
    the text (assignment + print) and reject it as a code block, not a claim.
    """
    text = "has_normals = True\nprint(has_normals)"
    assert _is_code_like(text) is True, (
        f"Expected _is_code_like to return True for multi-statement code: {text!r}"
    )


def test_t1_9b_prose_not_rejected_as_code():
    """Normal prose text is not rejected as code by _is_code_like."""
    text = "The library supports converting 3D mesh files between different formats."
    # Prose should not be flagged as code
    assert _is_code_like(text) is False, (
        f"Expected _is_code_like to return False for prose: {text!r}"
    )
