"""Google Gemini client for SEO tasks.

Provides keyword analysis, slug refinement, and meta description
generation using the Gemini free tier (gemini-2.5-flash).

All calls are rate-limited and cached.  When the API key is missing,
all methods degrade gracefully to empty/passthrough results.

TC-3807: Created for v2 SEO module.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
import urllib.error
import urllib.request
from typing import Any

from launcher.shared.api_rate_limiter import APIRateLimiter, create_gemini_limiter
from launcher.shared.seo_cache import SEOCache, make_cache_key

logger = logging.getLogger(__name__)

_GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

_KEYWORD_PROMPT = """\
You are an SEO specialist for developer documentation sites.

Product: {product_name}
Family: {family} (e.g. cells=spreadsheets, words=documents, pdf=pdf-files)
Platform: {platform}

Existing keywords: {existing}

Generate 10-15 additional high-intent developer search keywords and phrases \
that someone would type into Google when looking for this product or similar \
open-source libraries. Consider:
- Installation and setup queries
- Tutorial and how-to queries
- Format conversion queries (e.g. "convert xlsx to pdf python")
- API reference queries
- Comparison queries (e.g. "openpyxl vs aspose cells python")
- Error/troubleshooting queries
- Performance and benchmark queries

Return ONLY a JSON array of strings. No explanation, no markdown.
Example: ["python excel library", "convert xlsx to csv python", ...]"""

_SLUG_PROMPT = """\
For each slug below, extract the core 2-5 word topic. \
Remove filler words (you, can, this, that, allows, enables, etc.). \
Keep action verbs and nouns. Return one cleaned slug per line, same order. \
Use only lowercase and hyphens.

{slugs}"""

_DESCRIPTION_PROMPT = """\
Write a meta description (120-150 characters) for a developer documentation page.

Product: {product_name}
Page title: {title}
Key facts: {claims_summary}

The description must:
- Be 120-150 characters (STRICT limit)
- Mention the product name once
- Include a clear value proposition
- Be suitable for Google search results
- NOT start with "This page" or "Learn how"

Return ONLY the description text, no quotes, no explanation."""


class GeminiSEOClient:
    """Google Gemini client for SEO keyword analysis and slug refinement.

    Free tier limits (gemini-2.5-flash):
    - 15 RPM, 1M TPM, 1500 RPD
    - Rate limiting enforced at client level

    Parameters
    ----------
    api_key:
        Gemini API key.  Empty string disables all API calls.
    cache:
        SEO cache instance for storing responses.
    model:
        Gemini model identifier.
    rate_limiter:
        Optional custom rate limiter.  Uses ``create_gemini_limiter()``
        if not provided.
    """

    # Per-method token budgets (SEO-15).
    _TOKEN_BUDGET_KEYWORDS: int = 4096   # JSON array of 10-15 strings + thinking
    _TOKEN_BUDGET_SLUGS: int = 2048      # One slug per line
    _TOKEN_BUDGET_DESCRIPTION: int = 1024  # Single 150-char string

    # Fallback models when primary model has quota=0 (SEO-14).
    _FALLBACK_MODELS: list[str] = ["gemini-2.5-flash", "gemini-2.0-flash-lite"]

    def __init__(
        self,
        api_key: str,
        cache: SEOCache,
        model: str = "gemini-2.5-flash",
        rate_limiter: APIRateLimiter | None = None,
    ) -> None:
        self._api_key = api_key
        self._cache = cache
        self._model = model
        self._limiter = rate_limiter or create_gemini_limiter()
        self._warned_no_key = False
        self._deprecated_models: set[str] = set()  # Session-scoped (SEO-14).

    @property
    def available(self) -> bool:
        """Whether the client has an API key configured."""
        return bool(self._api_key)

    def analyze_keywords(
        self,
        family: str,
        platform: str,
        product_name: str,
        existing_keywords: list[str],
    ) -> list[str]:
        """Expand/refine keyword list for a product via Gemini.

        Returns additional keywords not in the existing list.
        Cached per family:platform (TTL from cache default).
        """
        if not self._api_key:
            self._warn_no_key()
            return []

        cache_key = make_cache_key(family, platform, "gemini_keywords")
        cached = self._cache.get("gemini_keywords", cache_key)
        if cached is not None:
            return cached

        prompt = _KEYWORD_PROMPT.format(
            product_name=product_name,
            family=family,
            platform=platform,
            existing=", ".join(existing_keywords[:20]),
        )

        raw = self._call_api(prompt, max_tokens=self._TOKEN_BUDGET_KEYWORDS)
        if not raw:
            return []

        keywords = _parse_json_array(raw)
        if not keywords:
            return []

        # Deduplicate against existing.
        existing_lower = {k.lower() for k in existing_keywords}
        new_keywords = [k for k in keywords if k.lower() not in existing_lower]

        self._cache.set("gemini_keywords", cache_key, new_keywords)
        logger.info(
            "[Gemini] Keyword analysis: %d new keywords for %s/%s",
            len(new_keywords), family, platform,
        )
        return new_keywords

    def refine_slugs(
        self,
        slugs: list[str],
        family: str,
        platform: str,
    ) -> list[str]:
        """Extract core 2-5 word topic per slug via Gemini.

        Returns refined slug list (same length as input).
        Falls back to input slugs on failure.
        Cached per slug batch hash.
        """
        if not self._api_key or not slugs:
            if not self._api_key:
                self._warn_no_key()
            return list(slugs)

        batch_hash = hashlib.sha256(
            "\n".join(sorted(slugs)).encode("utf-8"),
        ).hexdigest()[:16]
        cache_key = make_cache_key(family, platform, "gemini_slugs", batch_hash)
        cached = self._cache.get("gemini_slugs", cache_key)
        if cached is not None and len(cached) == len(slugs):
            return cached

        prompt = _SLUG_PROMPT.format(slugs="\n".join(slugs))
        raw = self._call_api(prompt, max_tokens=self._TOKEN_BUDGET_SLUGS)
        if not raw:
            return list(slugs)

        lines = [line.strip() for line in raw.strip().splitlines() if line.strip()]
        if len(lines) != len(slugs):
            logger.warning(
                "[Gemini] Slug refinement returned %d lines for %d slugs; ignoring",
                len(lines), len(slugs),
            )
            return list(slugs)

        # Validate each refined slug.
        import re
        valid_re = re.compile(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$")
        result: list[str] = []
        for original, refined in zip(slugs, lines):
            cleaned = refined.lower().strip()
            cleaned = re.sub(r"[^a-z0-9-]", "", cleaned)
            cleaned = re.sub(r"-{2,}", "-", cleaned).strip("-")
            if cleaned and valid_re.match(cleaned):
                result.append(cleaned)
            else:
                result.append(original)

        self._cache.set("gemini_slugs", cache_key, result)
        changed = sum(1 for a, b in zip(slugs, result) if a != b)
        logger.info("[Gemini] Slug refinement: %d/%d changed", changed, len(slugs))
        return result

    def generate_description(
        self,
        title: str,
        product_name: str,
        claims_summary: str,
    ) -> str:
        """Generate a 120-150 char meta description via Gemini.

        Returns empty string on failure.
        Cached per title hash.
        """
        if not self._api_key:
            self._warn_no_key()
            return ""

        title_hash = hashlib.sha256(title.encode("utf-8")).hexdigest()[:16]
        cache_key = make_cache_key("global", "global", "gemini_desc", title_hash)
        cached = self._cache.get("gemini_descs", cache_key)
        if cached is not None:
            return cached

        prompt = _DESCRIPTION_PROMPT.format(
            product_name=product_name,
            title=title,
            claims_summary=claims_summary[:500],
        )

        raw = self._call_api(prompt, max_tokens=self._TOKEN_BUDGET_DESCRIPTION)
        if not raw:
            return ""

        # Clean up: remove quotes, trim whitespace.
        desc = raw.strip().strip('"').strip("'").strip()

        # Enforce length.
        if len(desc) > 160:
            # Truncate at word boundary.
            truncated = desc[:157]
            last_space = truncated.rfind(" ")
            if last_space > 100:
                desc = truncated[:last_space] + "..."
            else:
                desc = truncated + "..."

        if len(desc) < 50:
            logger.debug("[Gemini] Description too short (%d chars), discarding", len(desc))
            return ""

        self._cache.set("gemini_descs", cache_key, desc)
        return desc

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _call_api(self, prompt: str, *, max_tokens: int = 2048) -> str:
        """Make a rate-limited Gemini API call.  Returns response text or empty string.

        Parameters
        ----------
        prompt:
            The text prompt to send.
        max_tokens:
            Maximum output tokens (per-method budgets via SEO-15).
        """
        return self._call_api_with_model(prompt, self._model, max_tokens=max_tokens)

    def _call_api_with_model(
        self, prompt: str, model: str, *, max_tokens: int = 2048,
    ) -> str:
        """Internal: call a specific model with fallback on deprecation (SEO-14)."""
        if model in self._deprecated_models:
            return self._try_fallback_models(prompt, max_tokens=max_tokens)

        url = _GEMINI_API_URL.format(model=model) + f"?key={self._api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.0, "maxOutputTokens": max_tokens},
        }

        for attempt in range(self._limiter.max_retries + 1):
            self._limiter.acquire()
            try:
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = json.loads(resp.read().decode("utf-8"))

                self._limiter.record_success()

                # Extract text from Gemini response.
                # Gemini 2.5+ may return thinking parts before the actual output.
                try:
                    parts = data["candidates"][0]["content"]["parts"]
                    # Concatenate only non-thought text parts.
                    text_parts = [
                        p["text"] for p in parts
                        if "text" in p and not p.get("thought")
                    ]
                    if text_parts:
                        return "".join(text_parts)
                    # Fallback: any text part at all.
                    for p in parts:
                        if "text" in p:
                            return p["text"]
                    logger.warning("[Gemini] No text in response parts: %s", parts)
                    return ""
                except (KeyError, IndexError, TypeError):
                    logger.warning("[Gemini] Unexpected response structure: %s", data)
                    return ""

            except urllib.error.HTTPError as exc:
                status = exc.code
                # Detect model deprecation: quota=0 in error body (SEO-14).
                if status == 429 and self._is_quota_zero(exc):
                    logger.warning(
                        "[Gemini] Model %s appears deprecated (quota=0), "
                        "trying fallback models",
                        model,
                    )
                    self._deprecated_models.add(model)
                    return self._try_fallback_models(prompt, max_tokens=max_tokens)

                if self._limiter.should_retry(status):
                    backoff = self._limiter.record_error(status)
                    logger.info(
                        "[Gemini] HTTP %d on attempt %d, backing off %.1fs",
                        status, attempt + 1, backoff,
                    )
                    time.sleep(backoff)
                    continue
                else:
                    logger.warning("[Gemini] Non-retryable HTTP %d", status)
                    self._limiter.record_error(status)
                    return ""

            except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
                logger.warning("[Gemini] Request failed: %s", exc)
                return ""

        logger.warning("[Gemini] Exhausted retries")
        return ""

    def _is_quota_zero(self, exc: urllib.error.HTTPError) -> bool:
        """Check if a 429 error indicates model deprecation (quota=0)."""
        try:
            body = exc.read().decode("utf-8", errors="replace").lower()
            return "limit: 0" in body or "quota exceeded" in body
        except Exception:
            return False

    def _try_fallback_models(self, prompt: str, *, max_tokens: int = 2048) -> str:
        """Try fallback models when primary is deprecated (SEO-14)."""
        for fallback in self._FALLBACK_MODELS:
            if fallback in self._deprecated_models or fallback == self._model:
                continue
            logger.info("[Gemini] Trying fallback model: %s", fallback)
            result = self._call_api_with_model(
                prompt, fallback, max_tokens=max_tokens,
            )
            if result:
                return result
        logger.warning("[Gemini] All models exhausted, no fallback available")
        return ""

    def _warn_no_key(self) -> None:
        if not self._warned_no_key:
            logger.warning(
                "[Gemini] GEMINI_API_KEY not set — Gemini SEO features disabled. "
                "Set the env var to enable keyword analysis, slug refinement, "
                "and description generation.",
            )
            self._warned_no_key = True


def _parse_json_array(text: str) -> list[str]:
    """Parse a JSON array of strings from LLM output.

    Handles common LLM quirks: markdown fences, trailing commas.
    """
    # Strip markdown code fences.
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        # Remove first and last lines (fences).
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()

    # Try direct parse.
    try:
        result = json.loads(text)
        if isinstance(result, list):
            return [str(item) for item in result if isinstance(item, (str, int, float))]
    except json.JSONDecodeError:
        pass

    # Try removing trailing commas (common LLM mistake).
    import re
    cleaned = re.sub(r",\s*]", "]", text)
    try:
        result = json.loads(cleaned)
        if isinstance(result, list):
            return [str(item) for item in result if isinstance(item, (str, int, float))]
    except json.JSONDecodeError:
        pass

    logger.warning("[Gemini] Could not parse JSON array from response")
    return []
