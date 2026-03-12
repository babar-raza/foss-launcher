"""Tests for launcher.clients.gemini_client."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import urllib.error

import pytest

from launcher.clients.gemini_client import GeminiSEOClient, _parse_json_array
from launcher.shared.api_rate_limiter import APIRateLimiter
from launcher.shared.seo_cache import SEOCache


@pytest.fixture()
def cache(tmp_path: Path) -> SEOCache:
    return SEOCache(tmp_path / "cache", default_ttl=3600)


@pytest.fixture()
def limiter() -> APIRateLimiter:
    return APIRateLimiter(
        requests_per_minute=600,
        min_interval_seconds=0.0,
        max_retries=2,
        base_backoff_seconds=0.01,
        max_backoff_seconds=0.1,
        name="test_gemini",
    )


@pytest.fixture()
def client(cache: SEOCache, limiter: APIRateLimiter) -> GeminiSEOClient:
    return GeminiSEOClient(
        api_key="test-key-123",
        cache=cache,
        model="gemini-2.0-flash",
        rate_limiter=limiter,
    )


@pytest.fixture()
def no_key_client(cache: SEOCache, limiter: APIRateLimiter) -> GeminiSEOClient:
    return GeminiSEOClient(
        api_key="",
        cache=cache,
        model="gemini-2.0-flash",
        rate_limiter=limiter,
    )


def _mock_gemini_response(text: str) -> bytes:
    """Build a Gemini API response body."""
    return json.dumps({
        "candidates": [{
            "content": {"parts": [{"text": text}]},
        }],
    }).encode("utf-8")


# ------------------------------------------------------------------
# Availability
# ------------------------------------------------------------------


class TestAvailability:
    def test_available_with_key(self, client: GeminiSEOClient) -> None:
        assert client.available is True

    def test_not_available_without_key(self, no_key_client: GeminiSEOClient) -> None:
        assert no_key_client.available is False


# ------------------------------------------------------------------
# No API key — graceful degradation
# ------------------------------------------------------------------


class TestNoApiKey:
    def test_analyze_keywords_returns_empty(self, no_key_client: GeminiSEOClient) -> None:
        result = no_key_client.analyze_keywords("cells", "python", "Aspose.Cells", ["excel"])
        assert result == []

    def test_refine_slugs_returns_input(self, no_key_client: GeminiSEOClient) -> None:
        slugs = ["getting-started", "installation"]
        result = no_key_client.refine_slugs(slugs, "cells", "python")
        assert result == slugs

    def test_generate_description_returns_empty(self, no_key_client: GeminiSEOClient) -> None:
        result = no_key_client.generate_description("Title", "Product", "claims")
        assert result == ""


# ------------------------------------------------------------------
# analyze_keywords
# ------------------------------------------------------------------


class TestAnalyzeKeywords:
    @patch("urllib.request.urlopen")
    def test_returns_new_keywords(self, mock_urlopen: MagicMock, client: GeminiSEOClient) -> None:
        mock_resp = MagicMock()
        mock_resp.read.return_value = _mock_gemini_response(
            '["python excel library", "convert xlsx python", "openpyxl alternative"]'
        )
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        result = client.analyze_keywords("cells", "python", "Aspose.Cells", ["excel"])
        assert "python excel library" in result
        assert "convert xlsx python" in result

    @patch("urllib.request.urlopen")
    def test_deduplicates_against_existing(self, mock_urlopen: MagicMock, client: GeminiSEOClient) -> None:
        mock_resp = MagicMock()
        mock_resp.read.return_value = _mock_gemini_response('["excel", "new keyword"]')
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        result = client.analyze_keywords("cells", "python", "Aspose.Cells", ["excel"])
        assert "excel" not in result
        assert "new keyword" in result

    @patch("urllib.request.urlopen")
    def test_caches_result(self, mock_urlopen: MagicMock, client: GeminiSEOClient) -> None:
        mock_resp = MagicMock()
        mock_resp.read.return_value = _mock_gemini_response('["cached keyword"]')
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        # First call — API hit.
        result1 = client.analyze_keywords("cells", "python", "Aspose.Cells", [])
        # Second call — cache hit, no API call.
        result2 = client.analyze_keywords("cells", "python", "Aspose.Cells", [])
        assert result1 == result2
        assert mock_urlopen.call_count == 1


# ------------------------------------------------------------------
# refine_slugs
# ------------------------------------------------------------------


class TestRefineSlugs:
    @patch("urllib.request.urlopen")
    def test_refines_slugs(self, mock_urlopen: MagicMock, client: GeminiSEOClient) -> None:
        mock_resp = MagicMock()
        mock_resp.read.return_value = _mock_gemini_response("spreadsheet-creation\ndata-export")
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        result = client.refine_slugs(
            ["you-can-create-spreadsheets", "allows-data-export"],
            "cells", "python",
        )
        assert result == ["spreadsheet-creation", "data-export"]

    @patch("urllib.request.urlopen")
    def test_wrong_line_count_returns_original(self, mock_urlopen: MagicMock, client: GeminiSEOClient) -> None:
        mock_resp = MagicMock()
        mock_resp.read.return_value = _mock_gemini_response("only-one-line")
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        originals = ["slug-one", "slug-two"]
        result = client.refine_slugs(originals, "cells", "python")
        assert result == originals

    def test_empty_slugs_returns_empty(self, client: GeminiSEOClient) -> None:
        assert client.refine_slugs([], "cells", "python") == []

    @patch("urllib.request.urlopen")
    def test_invalid_refined_slug_keeps_original(self, mock_urlopen: MagicMock, client: GeminiSEOClient) -> None:
        mock_resp = MagicMock()
        # Second slug is only special chars — strips to empty string.
        mock_resp.read.return_value = _mock_gemini_response("valid-slug\n---")
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        result = client.refine_slugs(["original-one", "original-two"], "cells", "python")
        assert result[0] == "valid-slug"
        assert result[1] == "original-two"  # Kept original (empty after cleaning)


# ------------------------------------------------------------------
# generate_description
# ------------------------------------------------------------------


class TestGenerateDescription:
    @patch("urllib.request.urlopen")
    def test_generates_description(self, mock_urlopen: MagicMock, client: GeminiSEOClient) -> None:
        desc = "Aspose.Cells FOSS for Python enables developers to create and manipulate Excel spreadsheets without Microsoft Office dependencies."
        mock_resp = MagicMock()
        mock_resp.read.return_value = _mock_gemini_response(desc)
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        result = client.generate_description("Getting Started", "Aspose.Cells FOSS", "Excel library")
        assert len(result) >= 50
        assert len(result) <= 160

    @patch("urllib.request.urlopen")
    def test_strips_quotes(self, mock_urlopen: MagicMock, client: GeminiSEOClient) -> None:
        mock_resp = MagicMock()
        mock_resp.read.return_value = _mock_gemini_response(
            '"A great description that is long enough to be useful for SEO and search engine results pages."'
        )
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        result = client.generate_description("Title", "Product", "claims")
        assert not result.startswith('"')
        assert not result.endswith('"')

    @patch("urllib.request.urlopen")
    def test_too_short_returns_empty(self, mock_urlopen: MagicMock, client: GeminiSEOClient) -> None:
        mock_resp = MagicMock()
        mock_resp.read.return_value = _mock_gemini_response("Too short")
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        result = client.generate_description("Title", "Product", "claims")
        assert result == ""

    @patch("urllib.request.urlopen")
    def test_caches_description(self, mock_urlopen: MagicMock, client: GeminiSEOClient) -> None:
        desc = "A cached description that meets the minimum length requirement for SEO meta descriptions in search results."
        mock_resp = MagicMock()
        mock_resp.read.return_value = _mock_gemini_response(desc)
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        r1 = client.generate_description("Same Title", "Product", "claims")
        r2 = client.generate_description("Same Title", "Product", "claims")
        assert r1 == r2
        assert mock_urlopen.call_count == 1


# ------------------------------------------------------------------
# Error handling
# ------------------------------------------------------------------


class TestErrorHandling:
    @patch("urllib.request.urlopen")
    def test_http_429_retries(self, mock_urlopen: MagicMock, client: GeminiSEOClient) -> None:
        # First call: 429, second call: success.
        error_resp = urllib.error.HTTPError(
            "url", 429, "Too Many Requests", {}, None,
        )
        success_resp = MagicMock()
        success_resp.read.return_value = _mock_gemini_response('["retried keyword"]')
        success_resp.__enter__ = lambda s: s
        success_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.side_effect = [error_resp, success_resp]

        result = client.analyze_keywords("cells", "python", "Aspose.Cells", [])
        assert "retried keyword" in result
        assert mock_urlopen.call_count == 2

    @patch("urllib.request.urlopen")
    def test_http_400_no_retry(self, mock_urlopen: MagicMock, client: GeminiSEOClient) -> None:
        mock_urlopen.side_effect = urllib.error.HTTPError(
            "url", 400, "Bad Request", {}, None,
        )
        result = client.analyze_keywords("cells", "python", "Aspose.Cells", [])
        assert result == []
        assert mock_urlopen.call_count == 1

    @patch("urllib.request.urlopen")
    def test_network_error_returns_empty(self, mock_urlopen: MagicMock, client: GeminiSEOClient) -> None:
        mock_urlopen.side_effect = urllib.error.URLError("Connection refused")
        result = client.analyze_keywords("cells", "python", "Aspose.Cells", [])
        assert result == []


# ------------------------------------------------------------------
# Gemini 2.5 thinking-part parsing (SEO-09)
# ------------------------------------------------------------------


class TestThinkingPartParsing:
    """Tests for Gemini 2.5+ response format with thinking parts."""

    def _mock_thinking_response(self, parts: list[dict]) -> bytes:
        """Build a Gemini response with custom parts list."""
        return json.dumps({
            "candidates": [{
                "content": {"parts": parts},
            }],
        }).encode("utf-8")

    @patch("urllib.request.urlopen")
    def test_response_with_thought_and_text_parts(
        self, mock_urlopen: MagicMock, client: GeminiSEOClient,
    ) -> None:
        """Non-thought text returned; thought parts excluded."""
        parts = [
            {"text": "Let me think about this...", "thought": True},
            {"text": '["python excel", "xlsx library"]'},
        ]
        mock_resp = MagicMock()
        mock_resp.read.return_value = self._mock_thinking_response(parts)
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        result = client.analyze_keywords("cells", "python", "Aspose.Cells", [])
        assert "python excel" in result
        assert "xlsx library" in result

    @patch("urllib.request.urlopen")
    def test_response_with_only_thought_parts(
        self, mock_urlopen: MagicMock, client: GeminiSEOClient,
    ) -> None:
        """Fallback: when all parts are thoughts, use any text part."""
        parts = [
            {"text": '["fallback keyword"]', "thought": True},
        ]
        mock_resp = MagicMock()
        mock_resp.read.return_value = self._mock_thinking_response(parts)
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        result = client.analyze_keywords("cells", "python", "Aspose.Cells", [])
        assert "fallback keyword" in result

    @patch("urllib.request.urlopen")
    def test_response_without_thought_flag(
        self, mock_urlopen: MagicMock, client: GeminiSEOClient,
    ) -> None:
        """Standard response without thought key (gemini-2.0 compat)."""
        parts = [{"text": '["standard keyword"]'}]
        mock_resp = MagicMock()
        mock_resp.read.return_value = self._mock_thinking_response(parts)
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        result = client.analyze_keywords("cells", "python", "Aspose.Cells", [])
        assert "standard keyword" in result

    @patch("urllib.request.urlopen")
    def test_multiple_text_parts_concatenated(
        self, mock_urlopen: MagicMock, client: GeminiSEOClient,
    ) -> None:
        """Multiple non-thought text parts are concatenated."""
        parts = [
            {"text": '["part1"'},
            {"text": ', "part2"]'},
        ]
        mock_resp = MagicMock()
        mock_resp.read.return_value = self._mock_thinking_response(parts)
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        result = client.analyze_keywords("cells", "python", "Aspose.Cells", [])
        assert "part1" in result
        assert "part2" in result

    @patch("urllib.request.urlopen")
    def test_keyword_analysis_with_thinking_response(
        self, mock_urlopen: MagicMock, client: GeminiSEOClient,
    ) -> None:
        """End-to-end: thinking + real JSON array output parsed correctly."""
        parts = [
            {"text": "I'll generate relevant developer keywords for Excel...", "thought": True},
            {"text": "Considering the product family 'cells' and platform 'python'...", "thought": True},
            {"text": '["convert xlsx python", "python spreadsheet api", "excel automation"]'},
        ]
        mock_resp = MagicMock()
        mock_resp.read.return_value = self._mock_thinking_response(parts)
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        result = client.analyze_keywords("cells", "python", "Aspose.Cells", [])
        assert len(result) == 3
        assert "convert xlsx python" in result
        assert "python spreadsheet api" in result
        assert "excel automation" in result


# ------------------------------------------------------------------
# JSON parsing helper
# ------------------------------------------------------------------


class TestParseJsonArray:
    def test_clean_json(self) -> None:
        assert _parse_json_array('["a", "b", "c"]') == ["a", "b", "c"]

    def test_with_markdown_fences(self) -> None:
        text = '```json\n["a", "b"]\n```'
        assert _parse_json_array(text) == ["a", "b"]

    def test_trailing_comma(self) -> None:
        assert _parse_json_array('["a", "b",]') == ["a", "b"]

    def test_invalid_json_returns_empty(self) -> None:
        assert _parse_json_array("not json at all") == []

    def test_non_string_items_converted(self) -> None:
        assert _parse_json_array("[1, 2.5, \"str\"]") == ["1", "2.5", "str"]

    def test_empty_array(self) -> None:
        assert _parse_json_array("[]") == []


# ------------------------------------------------------------------
# Model deprecation fallback (SEO-14)
# ------------------------------------------------------------------


class TestModelFallback:
    @patch("urllib.request.urlopen")
    def test_quota_zero_triggers_fallback(
        self, mock_urlopen: MagicMock, client: GeminiSEOClient,
    ) -> None:
        """429 with quota=0 body triggers fallback to next model."""
        import io
        # First call: 429 with quota=0 body (deprecation).
        error_body = b'{"error": {"message": "Quota exceeded for limit: 0, model: gemini-2.0-flash"}}'
        error_resp = urllib.error.HTTPError(
            "url", 429, "Too Many Requests", {},
            io.BytesIO(error_body),
        )
        # Fallback call: success.
        success_resp = MagicMock()
        success_resp.read.return_value = _mock_gemini_response('["fallback keyword"]')
        success_resp.__enter__ = lambda s: s
        success_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.side_effect = [error_resp, success_resp]

        result = client.analyze_keywords("cells", "python", "Aspose.Cells", [])
        assert "fallback keyword" in result

    @patch("urllib.request.urlopen")
    def test_deprecated_model_cached_in_session(
        self, mock_urlopen: MagicMock, client: GeminiSEOClient,
    ) -> None:
        """Once a model is marked deprecated, subsequent calls skip it."""
        import io
        error_body = b'{"error": {"message": "Quota exceeded for limit: 0"}}'
        error_resp = urllib.error.HTTPError(
            "url", 429, "Too Many Requests", {},
            io.BytesIO(error_body),
        )
        success_resp = MagicMock()
        success_resp.read.return_value = _mock_gemini_response('["kw1"]')
        success_resp.__enter__ = lambda s: s
        success_resp.__exit__ = MagicMock(return_value=False)
        # First call: deprecation + fallback success.
        mock_urlopen.side_effect = [error_resp, success_resp]
        client.analyze_keywords("cells", "python", "Aspose.Cells", [])

        # Verify model is marked deprecated.
        assert client._model in client._deprecated_models

    @patch("urllib.request.urlopen")
    def test_all_models_deprecated_returns_empty(
        self, mock_urlopen: MagicMock, client: GeminiSEOClient,
    ) -> None:
        """When all models are deprecated, returns empty result."""
        # Mark primary and all fallbacks as deprecated.
        client._deprecated_models.add(client._model)
        for fb in client._FALLBACK_MODELS:
            client._deprecated_models.add(fb)

        result = client.analyze_keywords("cells", "python", "Aspose.Cells", [])
        assert result == []
        # No API call should have been made.
        assert mock_urlopen.call_count == 0


# ------------------------------------------------------------------
# Per-method token budgets (SEO-15)
# ------------------------------------------------------------------


class TestTokenBudgets:
    @patch("urllib.request.urlopen")
    def test_keyword_analysis_uses_4096_tokens(
        self, mock_urlopen: MagicMock, client: GeminiSEOClient,
    ) -> None:
        """analyze_keywords sends maxOutputTokens=4096."""
        mock_resp = MagicMock()
        mock_resp.read.return_value = _mock_gemini_response('["kw"]')
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        client.analyze_keywords("cells", "python", "Aspose.Cells", [])
        # Extract the payload sent to urlopen.
        call_args = mock_urlopen.call_args
        req = call_args[0][0]
        payload = json.loads(req.data.decode("utf-8"))
        assert payload["generationConfig"]["maxOutputTokens"] == 4096

    @patch("urllib.request.urlopen")
    def test_slug_refinement_uses_2048_tokens(
        self, mock_urlopen: MagicMock, client: GeminiSEOClient,
    ) -> None:
        """refine_slugs sends maxOutputTokens=2048."""
        mock_resp = MagicMock()
        mock_resp.read.return_value = _mock_gemini_response("refined-slug")
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        client.refine_slugs(["original-slug"], "cells", "python")
        call_args = mock_urlopen.call_args
        req = call_args[0][0]
        payload = json.loads(req.data.decode("utf-8"))
        assert payload["generationConfig"]["maxOutputTokens"] == 2048

    @patch("urllib.request.urlopen")
    def test_description_uses_1024_tokens(
        self, mock_urlopen: MagicMock, client: GeminiSEOClient,
    ) -> None:
        """generate_description sends maxOutputTokens=1024."""
        desc = "A sufficiently long description for testing purposes that meets the minimum length requirement."
        mock_resp = MagicMock()
        mock_resp.read.return_value = _mock_gemini_response(desc)
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        client.generate_description("Title", "Product", "claims summary")
        call_args = mock_urlopen.call_args
        req = call_args[0][0]
        payload = json.loads(req.data.decode("utf-8"))
        assert payload["generationConfig"]["maxOutputTokens"] == 1024
