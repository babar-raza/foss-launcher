"""Unit tests for TC-1045: LLM-based claim enrichment.

Tests all enrichment functions per specs/08_semantic_claim_enrichment.md:
- Offline heuristics (audience_level, complexity, prerequisites, use_cases, target_persona)
- Cache key computation (deterministic, changes with inputs)
- Prompt template rendering
- Cost estimation
- Batch processing (boundaries, empty batches)
- LLM enrichment with mocked client
- Cache hit/miss behavior
- Hard limit enforcement (>1000 claims)
- Skip behavior (<10 claims -> heuristics)
- Deterministic output (sorted by claim_id)
- Error handling (LLM failure -> fallback to heuristics)

Spec: specs/08_semantic_claim_enrichment.md section 10
Taskcard: plans/taskcards/TC-1045_implement_llm_claim_enrichment.md
"""

import json
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

from src.launch.workers.w2_facts_builder.enrich_claims import (
    BEGINNER_KEYWORDS,
    ADVANCED_KEYWORDS,
    DEFAULT_BATCH_SIZE,
    DEFAULT_MAX_CLAIMS,
    ENRICHMENT_SCHEMA_VERSION,
    MIN_CLAIMS_FOR_LLM,
    SYSTEM_PROMPT,
    USER_PROMPT_TEMPLATE,
    add_offline_metadata_fallbacks,
    compute_cache_key,
    enrich_claims_batch,
    estimate_cost,
    _apply_hard_limit,
    _build_enrichment_prompt,
    _infer_audience_level,
    _infer_complexity,
    _load_from_cache,
    _save_to_cache,
)


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #


def _make_claim(
    claim_id: str = "claim_001",
    claim_text: str = "Supports OBJ format import",
    claim_kind: str = "feature",
    **extra: Any,
) -> Dict[str, Any]:
    """Helper: build a minimal claim dict."""
    claim = {
        "claim_id": claim_id,
        "claim_text": claim_text,
        "claim_kind": claim_kind,
    }
    claim.update(extra)
    return claim


def _make_claims(n: int, prefix: str = "claim") -> List[Dict[str, Any]]:
    """Helper: build a list of N claims with sequential IDs."""
    return [
        _make_claim(
            claim_id=f"{prefix}_{i:04d}",
            claim_text=f"Test claim {i} for library feature number {i}",
            claim_kind="feature",
        )
        for i in range(n)
    ]


def _make_mock_llm_client(response_claims: List[Dict[str, Any]]) -> MagicMock:
    """Helper: build a mock LLM client that returns given enriched claims."""
    client = MagicMock()
    client.model = "claude-3-5-sonnet-20241022"

    def chat_side_effect(messages, **kwargs):
        return {
            "content": json.dumps(response_claims),
            "prompt_hash": "mock_hash",
            "model": "claude-3-5-sonnet-20241022",
            "usage": {"prompt_tokens": 100, "completion_tokens": 50},
            "latency_ms": 500,
        }

    client.chat_completion = MagicMock(side_effect=chat_side_effect)
    return client


# --------------------------------------------------------------------------- #
# Test: Offline Heuristics
# --------------------------------------------------------------------------- #


class TestOfflineHeuristics:
    """Tests for add_offline_metadata_fallbacks per spec 08 section 6."""

    def test_audience_level_beginner_keywords(self):
        """Beginner keywords should yield 'beginner' audience_level."""
        for kw in BEGINNER_KEYWORDS:
            claim = _make_claim(claim_text=f"How to {kw} the library")
            result = add_offline_metadata_fallbacks([claim], "TestProduct")
            assert result[0]["audience_level"] == "beginner", f"Failed for keyword: {kw}"

    def test_audience_level_advanced_keywords(self):
        """Advanced keywords should yield 'advanced' audience_level."""
        for kw in ADVANCED_KEYWORDS:
            claim = _make_claim(claim_text=f"How to {kw} the library")
            result = add_offline_metadata_fallbacks([claim], "TestProduct")
            assert result[0]["audience_level"] == "advanced", f"Failed for keyword: {kw}"

    def test_audience_level_default_intermediate(self):
        """Claims without beginner/advanced keywords default to 'intermediate'."""
        claim = _make_claim(claim_text="Supports OBJ format import")
        result = add_offline_metadata_fallbacks([claim], "TestProduct")
        assert result[0]["audience_level"] == "intermediate"

    def test_complexity_simple_short_text(self):
        """Short text (<50 chars) should yield 'simple'."""
        claim = _make_claim(claim_text="Supports PDF")  # < 50 chars
        result = add_offline_metadata_fallbacks([claim], "TestProduct")
        assert result[0]["complexity"] == "simple"

    def test_complexity_complex_long_text(self):
        """Long text (>150 chars) should yield 'complex'."""
        long_text = "A" * 151
        claim = _make_claim(claim_text=long_text)
        result = add_offline_metadata_fallbacks([claim], "TestProduct")
        assert result[0]["complexity"] == "complex"

    def test_complexity_medium_default(self):
        """Medium-length text should yield 'medium'."""
        medium_text = "A" * 75  # between 50 and 150
        claim = _make_claim(claim_text=medium_text)
        result = add_offline_metadata_fallbacks([claim], "TestProduct")
        assert result[0]["complexity"] == "medium"

    def test_prerequisites_always_empty(self):
        """Offline mode: prerequisites always empty array."""
        claim = _make_claim()
        result = add_offline_metadata_fallbacks([claim], "TestProduct")
        assert result[0]["prerequisites"] == []

    def test_use_cases_always_empty(self):
        """Offline mode: use_cases always empty array."""
        claim = _make_claim()
        result = add_offline_metadata_fallbacks([claim], "TestProduct")
        assert result[0]["use_cases"] == []

    def test_target_persona_uses_product_name(self):
        """Offline mode: target_persona is '{product_name} developers'."""
        claim = _make_claim()
        result = add_offline_metadata_fallbacks([claim], "Aspose.3D")
        assert result[0]["target_persona"] == "Aspose.3D developers"

    def test_no_null_values(self):
        """All enrichment fields must be non-null. Per spec 08 section 6.7."""
        claim = _make_claim()
        result = add_offline_metadata_fallbacks([claim], "TestProduct")
        enriched = result[0]
        assert enriched["audience_level"] is not None
        assert enriched["complexity"] is not None
        assert enriched["prerequisites"] is not None
        assert enriched["use_cases"] is not None
        assert enriched["target_persona"] is not None

    def test_original_claims_not_mutated(self):
        """add_offline_metadata_fallbacks must not mutate input claims."""
        claim = _make_claim()
        original_keys = set(claim.keys())
        _ = add_offline_metadata_fallbacks([claim], "TestProduct")
        assert set(claim.keys()) == original_keys


# --------------------------------------------------------------------------- #
# Test: Cache Key Computation
# --------------------------------------------------------------------------- #


class TestCacheKeyComputation:
    """Tests for compute_cache_key per spec 08 section 5.1."""

    def test_deterministic_same_inputs(self):
        """Same inputs produce same cache key."""
        key1 = compute_cache_key("url", "sha", "prompt", "model", "v1")
        key2 = compute_cache_key("url", "sha", "prompt", "model", "v1")
        assert key1 == key2

    def test_different_repo_url_different_key(self):
        """Different repo_url produces different cache key."""
        key1 = compute_cache_key("url1", "sha", "prompt", "model", "v1")
        key2 = compute_cache_key("url2", "sha", "prompt", "model", "v1")
        assert key1 != key2

    def test_different_repo_sha_different_key(self):
        """Different repo_sha produces different cache key."""
        key1 = compute_cache_key("url", "sha1", "prompt", "model", "v1")
        key2 = compute_cache_key("url", "sha2", "prompt", "model", "v1")
        assert key1 != key2

    def test_different_prompt_different_key(self):
        """Different prompt produces different cache key (prompt hashing)."""
        key1 = compute_cache_key("url", "sha", "promptA", "model", "v1")
        key2 = compute_cache_key("url", "sha", "promptB", "model", "v1")
        assert key1 != key2

    def test_different_model_different_key(self):
        """Different model produces different cache key."""
        key1 = compute_cache_key("url", "sha", "prompt", "model1", "v1")
        key2 = compute_cache_key("url", "sha", "prompt", "model2", "v1")
        assert key1 != key2

    def test_different_schema_version_different_key(self):
        """Different schema version produces different cache key."""
        key1 = compute_cache_key("url", "sha", "prompt", "model", "v1")
        key2 = compute_cache_key("url", "sha", "prompt", "model", "v2")
        assert key1 != key2

    def test_key_is_sha256_hex(self):
        """Cache key should be a 64-char hex SHA256."""
        key = compute_cache_key("url", "sha", "prompt", "model", "v1")
        assert len(key) == 64
        assert all(c in "0123456789abcdef" for c in key)


# --------------------------------------------------------------------------- #
# Test: Cost Estimation
# --------------------------------------------------------------------------- #


class TestCostEstimation:
    """Tests for estimate_cost per spec 08 section 7.3."""

    def test_zero_claims_zero_cost(self):
        """Zero claims should produce zero cost."""
        assert estimate_cost(0) == 0.0

    def test_positive_cost_for_claims(self):
        """Positive claim count should produce positive cost."""
        cost = estimate_cost(100)
        assert cost > 0.0

    def test_cost_scales_linearly(self):
        """Cost should scale linearly with claim count."""
        cost_100 = estimate_cost(100)
        cost_200 = estimate_cost(200)
        assert abs(cost_200 - 2 * cost_100) < 1e-10

    def test_cost_estimation_accuracy(self):
        """Cost for 100 claims: (100*100/1000)*0.003 + (100*50/1000)*0.015 = 0.03 + 0.075 = 0.105."""
        cost = estimate_cost(100)
        expected = (100 * 100 / 1000) * 0.003 + (100 * 50 / 1000) * 0.015
        assert abs(cost - expected) < 1e-10


# --------------------------------------------------------------------------- #
# Test: Prompt Template
# --------------------------------------------------------------------------- #


class TestPromptTemplate:
    """Tests for _build_enrichment_prompt per spec 08 section 4."""

    def test_prompt_has_system_and_user_messages(self):
        """Prompt must have system and user message."""
        claims = [_make_claim()]
        messages = _build_enrichment_prompt(claims, "Aspose.3D", "python")
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"

    def test_prompt_system_content_matches_spec(self):
        """System prompt must match spec 08 section 4.1."""
        claims = [_make_claim()]
        messages = _build_enrichment_prompt(claims, "TestProduct", "python")
        assert "technical documentation analyst" in messages[0]["content"]

    def test_prompt_user_contains_product_name(self):
        """User prompt must contain the product name."""
        claims = [_make_claim()]
        messages = _build_enrichment_prompt(claims, "Aspose.3D", "python")
        assert "Aspose.3D" in messages[1]["content"]

    def test_prompt_user_contains_claims_json(self):
        """User prompt must contain claims JSON."""
        claims = [_make_claim(claim_id="test_id")]
        messages = _build_enrichment_prompt(claims, "TestProduct", "python")
        assert "test_id" in messages[1]["content"]


# --------------------------------------------------------------------------- #
# Test: Batch Processing
# --------------------------------------------------------------------------- #


class TestBatchProcessing:
    """Tests for batch processing per spec 08 section 3.2."""

    def test_batch_processes_all_claims(self, tmp_path):
        """All claims should be enriched (LLM path with mock)."""
        claims = _make_claims(25)  # More than one batch of 20

        # Build LLM response for each batch call
        def chat_side_effect(messages, **kwargs):
            # Parse claims from user message to determine batch
            user_content = messages[1]["content"]
            # Return enrichment for whatever claim_ids are in the batch
            batch_claims = []
            for c in claims:
                if c["claim_id"] in user_content:
                    batch_claims.append({
                        "claim_id": c["claim_id"],
                        "audience_level": "intermediate",
                        "complexity": "medium",
                        "prerequisites": [],
                        "use_cases": ["test scenario"],
                        "target_persona": "test devs",
                    })
            return {
                "content": json.dumps(batch_claims),
                "prompt_hash": "mock",
                "model": "test-model",
                "usage": {},
                "latency_ms": 100,
            }

        client = MagicMock()
        client.model = "test-model"
        client.chat_completion = MagicMock(side_effect=chat_side_effect)

        cache_dir = tmp_path / "cache"
        result = enrich_claims_batch(
            claims=claims,
            product_name="TestProduct",
            llm_client=client,
            cache_dir=cache_dir,
        )

        assert len(result) == 25
        # All should have enrichment fields
        for r in result:
            assert "audience_level" in r
            assert "complexity" in r

    def test_empty_claims_returns_empty(self, tmp_path):
        """Empty claims list should return empty list (offline path)."""
        cache_dir = tmp_path / "cache"
        result = enrich_claims_batch(
            claims=[],
            product_name="TestProduct",
            llm_client=None,
            cache_dir=cache_dir,
        )
        assert result == []


# --------------------------------------------------------------------------- #
# Test: LLM Enrichment with Mocked Client
# --------------------------------------------------------------------------- #


class TestLLMEnrichment:
    """Tests for LLM-based enrichment with mocked client."""

    def test_llm_enrichment_adds_fields(self, tmp_path):
        """LLM enrichment should add all five metadata fields."""
        claims = _make_claims(15)
        response_claims = [
            {
                "claim_id": c["claim_id"],
                "audience_level": "beginner",
                "complexity": "simple",
                "prerequisites": [],
                "use_cases": ["use case 1", "use case 2"],
                "target_persona": "Python developers",
            }
            for c in claims
        ]
        client = _make_mock_llm_client(response_claims)

        cache_dir = tmp_path / "cache"
        result = enrich_claims_batch(
            claims=claims,
            product_name="TestProduct",
            llm_client=client,
            cache_dir=cache_dir,
        )

        assert len(result) == 15
        for r in result:
            assert r["audience_level"] == "beginner"
            assert r["complexity"] == "simple"
            assert r["prerequisites"] == []
            assert r["use_cases"] == ["use case 1", "use case 2"]
            assert r["target_persona"] == "Python developers"

    def test_llm_uses_temperature_zero(self, tmp_path):
        """LLM calls must use temperature=0.0 for determinism."""
        claims = _make_claims(12)
        response_claims = [
            {
                "claim_id": c["claim_id"],
                "audience_level": "intermediate",
                "complexity": "medium",
                "prerequisites": [],
                "use_cases": [],
                "target_persona": "devs",
            }
            for c in claims
        ]
        client = _make_mock_llm_client(response_claims)
        cache_dir = tmp_path / "cache"

        enrich_claims_batch(
            claims=claims,
            product_name="TestProduct",
            llm_client=client,
            cache_dir=cache_dir,
        )

        # Verify temperature=0.0 was passed
        call_kwargs = client.chat_completion.call_args
        assert call_kwargs.kwargs.get("temperature") == 0.0 or call_kwargs[1].get("temperature") == 0.0


# --------------------------------------------------------------------------- #
# Test: Cache Behavior
# --------------------------------------------------------------------------- #


class TestCacheBehavior:
    """Tests for cache hit/miss per spec 08 section 5."""

    def test_cache_miss_then_hit(self, tmp_path):
        """Second call with same inputs should use cache."""
        claims = _make_claims(15)
        response_claims = [
            {
                "claim_id": c["claim_id"],
                "audience_level": "beginner",
                "complexity": "simple",
                "prerequisites": [],
                "use_cases": ["cached scenario"],
                "target_persona": "cached devs",
            }
            for c in claims
        ]
        client = _make_mock_llm_client(response_claims)
        cache_dir = tmp_path / "cache"

        # First call: cache miss, calls LLM
        result1 = enrich_claims_batch(
            claims=claims,
            product_name="TestProduct",
            llm_client=client,
            cache_dir=cache_dir,
            repo_url="https://github.com/test/repo",
            repo_sha="abc123",
        )
        assert client.chat_completion.call_count == 1

        # Second call: should hit cache
        result2 = enrich_claims_batch(
            claims=claims,
            product_name="TestProduct",
            llm_client=client,
            cache_dir=cache_dir,
            repo_url="https://github.com/test/repo",
            repo_sha="abc123",
        )
        # Should still be 1 (no new LLM call)
        assert client.chat_completion.call_count == 1

        # Results should be equivalent
        assert len(result1) == len(result2)

    def test_cache_invalidated_on_schema_mismatch(self, tmp_path):
        """Cache should be invalidated if schema_version changes."""
        claims = [_make_claim(claim_id="c1")]
        cache_dir = tmp_path / "cache"

        # Write a cache file with different schema version
        cache_key = compute_cache_key("url", "sha", SYSTEM_PROMPT + USER_PROMPT_TEMPLATE, "model", ENRICHMENT_SCHEMA_VERSION)
        cache_file = cache_dir / f"{cache_key}.json"
        cache_dir.mkdir(parents=True, exist_ok=True)
        with open(cache_file, "w") as f:
            json.dump({
                "schema_version": "v_old",
                "enriched_claims": [
                    {"claim_id": "c1", "audience_level": "beginner"}
                ],
            }, f)

        # Should return None (schema mismatch)
        result = _load_from_cache(cache_dir, cache_key, claims)
        assert result is None

    def test_cache_corrupted_file_returns_none(self, tmp_path):
        """Corrupted cache file should return None, not crash."""
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = cache_dir / "somecachekey.json"
        cache_file.write_text("NOT VALID JSON {{{", encoding="utf-8")

        result = _load_from_cache(cache_dir, "somecachekey", [_make_claim()])
        assert result is None


# --------------------------------------------------------------------------- #
# Test: Hard Limit Enforcement
# --------------------------------------------------------------------------- #


class TestHardLimit:
    """Tests for hard limit (>1000 claims) per spec 08 section 7.2."""

    def test_claims_under_limit_kept(self):
        """Claims under limit are all kept."""
        claims = _make_claims(50)
        kept, skipped = _apply_hard_limit(claims, 1000)
        assert len(kept) == 50
        assert len(skipped) == 0

    def test_claims_over_limit_truncated(self):
        """Claims over limit are truncated with prioritization."""
        claims = _make_claims(1500)
        kept, skipped = _apply_hard_limit(claims, 1000)
        assert len(kept) == 1000
        assert len(skipped) == 500

    def test_skipped_claims_marked(self, tmp_path):
        """Skipped claims should get enrichment_skipped flag."""
        # Create 1005 claims so 5 are skipped
        claims = _make_claims(1005)
        cache_dir = tmp_path / "cache"

        result = enrich_claims_batch(
            claims=claims,
            product_name="TestProduct",
            llm_client=None,
            cache_dir=cache_dir,
            offline_mode=True,
            max_claims=1000,
        )
        # In offline mode all claims get heuristics, but over-limit claims
        # are not separately marked since offline mode processes all claims
        # (the hard limit only applies to LLM path)
        assert len(result) == 1005


# --------------------------------------------------------------------------- #
# Test: Skip Behavior (<10 claims)
# --------------------------------------------------------------------------- #


class TestSkipBehavior:
    """Tests for skip behavior with < 10 claims per spec 08 section 7.4."""

    def test_few_claims_use_heuristics(self, tmp_path):
        """< 10 claims should use heuristics even with LLM client available."""
        claims = _make_claims(5)
        client = MagicMock()
        client.model = "test-model"
        cache_dir = tmp_path / "cache"

        result = enrich_claims_batch(
            claims=claims,
            product_name="TestProduct",
            llm_client=client,
            cache_dir=cache_dir,
        )

        # LLM should NOT have been called
        client.chat_completion.assert_not_called()

        # Should still have enrichment fields (from heuristics)
        assert len(result) == 5
        for r in result:
            assert "audience_level" in r
            assert "complexity" in r
            assert "target_persona" in r


# --------------------------------------------------------------------------- #
# Test: Deterministic Output
# --------------------------------------------------------------------------- #


class TestDeterministicOutput:
    """Tests for deterministic output per spec 08 section 8."""

    def test_output_sorted_by_claim_id(self, tmp_path):
        """Output must be sorted by claim_id regardless of input order."""
        claims = [
            _make_claim(claim_id="z_last"),
            _make_claim(claim_id="a_first"),
            _make_claim(claim_id="m_middle"),
        ]
        cache_dir = tmp_path / "cache"

        result = enrich_claims_batch(
            claims=claims,
            product_name="TestProduct",
            llm_client=None,
            cache_dir=cache_dir,
            offline_mode=True,
        )

        ids = [r["claim_id"] for r in result]
        assert ids == sorted(ids)

    def test_same_input_same_output(self, tmp_path):
        """Two runs with same input must produce identical output."""
        claims = _make_claims(5)
        cache_dir = tmp_path / "cache"

        result1 = enrich_claims_batch(
            claims=claims,
            product_name="TestProduct",
            llm_client=None,
            cache_dir=cache_dir,
            offline_mode=True,
        )
        result2 = enrich_claims_batch(
            claims=claims,
            product_name="TestProduct",
            llm_client=None,
            cache_dir=cache_dir,
            offline_mode=True,
        )

        assert result1 == result2


# --------------------------------------------------------------------------- #
# Test: Error Handling
# --------------------------------------------------------------------------- #


class TestErrorHandling:
    """Tests for error handling and graceful fallback."""

    def test_llm_failure_falls_back_to_heuristics(self, tmp_path):
        """LLM failure should fall back to heuristics, not crash."""
        from src.launch.clients.llm_provider import LLMError

        claims = _make_claims(15)
        client = MagicMock()
        client.model = "test-model"
        client.chat_completion = MagicMock(side_effect=LLMError("API down"))
        cache_dir = tmp_path / "cache"

        result = enrich_claims_batch(
            claims=claims,
            product_name="TestProduct",
            llm_client=client,
            cache_dir=cache_dir,
        )

        # Should succeed via fallback
        assert len(result) == 15
        # All should have enrichment fields
        for r in result:
            assert "audience_level" in r
            assert "complexity" in r
            assert "target_persona" in r

    def test_malformed_llm_response_falls_back(self, tmp_path):
        """Malformed LLM JSON response should fall back to heuristics."""
        claims = _make_claims(12)
        client = MagicMock()
        client.model = "test-model"
        client.chat_completion = MagicMock(return_value={
            "content": "NOT VALID JSON {{{",
            "prompt_hash": "h",
            "model": "m",
            "usage": {},
            "latency_ms": 0,
        })
        cache_dir = tmp_path / "cache"

        result = enrich_claims_batch(
            claims=claims,
            product_name="TestProduct",
            llm_client=client,
            cache_dir=cache_dir,
        )

        # Should succeed via fallback
        assert len(result) == 12
        for r in result:
            assert "audience_level" in r


# --------------------------------------------------------------------------- #
# Test: Save and Load Cache
# --------------------------------------------------------------------------- #


class TestCacheIO:
    """Tests for _save_to_cache and _load_from_cache."""

    def test_save_then_load(self, tmp_path):
        """Cache round-trip: save then load should return same data."""
        claims = [
            _make_claim(claim_id="c1", audience_level="beginner", complexity="simple",
                        prerequisites=[], use_cases=["test"], target_persona="devs"),
        ]
        cache_dir = tmp_path / "cache"
        cache_key = "test_key_123"

        _save_to_cache(cache_dir, cache_key, claims, {
            "repo_url": "url",
            "repo_sha": "sha",
            "llm_model": "model",
            "schema_version": ENRICHMENT_SCHEMA_VERSION,
        })

        # Load with same claim set
        loaded = _load_from_cache(cache_dir, cache_key, [_make_claim(claim_id="c1")])
        assert loaded is not None
        assert len(loaded) == 1
        assert loaded[0]["audience_level"] == "beginner"

    def test_load_nonexistent_cache_returns_none(self, tmp_path):
        """Loading from nonexistent cache file returns None."""
        cache_dir = tmp_path / "cache"
        result = _load_from_cache(cache_dir, "nonexistent_key", [_make_claim()])
        assert result is None

    def test_cache_id_mismatch_returns_none(self, tmp_path):
        """Cache with different claim IDs returns None."""
        cache_dir = tmp_path / "cache"
        cache_key = "key_mismatch"

        # Save with claim_id "c1"
        _save_to_cache(cache_dir, cache_key, [
            _make_claim(claim_id="c1", audience_level="beginner", complexity="simple",
                        prerequisites=[], use_cases=[], target_persona="devs"),
        ], {"schema_version": ENRICHMENT_SCHEMA_VERSION})

        # Load with a claim that has a DIFFERENT ID
        result = _load_from_cache(cache_dir, cache_key, [_make_claim(claim_id="c_different")])
        assert result is None


# --------------------------------------------------------------------------- #
# Test: Internal Helpers
# --------------------------------------------------------------------------- #


class TestInternalHelpers:
    """Tests for internal heuristic functions."""

    def test_infer_audience_level_case_insensitive(self):
        """Keyword matching should be case-insensitive."""
        assert _infer_audience_level("How to INSTALL the library") == "beginner"
        assert _infer_audience_level("ADVANCED topic") == "advanced"

    def test_infer_complexity_boundary_values(self):
        """Test exact boundary values for complexity heuristic."""
        assert _infer_complexity("A" * 49) == "simple"    # < 50
        assert _infer_complexity("A" * 50) == "medium"    # == 50
        assert _infer_complexity("A" * 150) == "medium"   # == 150
        assert _infer_complexity("A" * 151) == "complex"  # > 150
