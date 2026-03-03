"""Tests for W7 ContentReviewer semantic accuracy checks (TC-1405).

Tests cover all 3 LLM-based semantic checks with offline fallback:
1. API hallucination detection
2. Licensing accuracy
3. Content relevance

Testing: mocked (LLM path tests use mock LLMProviderClient)
"""
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from launch.workers.w7_content_reviewer.checks.semantic_accuracy import (
    check_all,
    check_api_hallucination,
    check_licensing_accuracy,
    check_content_relevance,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def drafts_dir(tmp_path):
    """Create a temporary drafts directory."""
    d = tmp_path / "drafts"
    d.mkdir()
    return d


@pytest.fixture
def product_facts_foss():
    """Product facts for a FOSS product with API surface."""
    return {
        "product_name": "Aspose.Note FOSS Python",
        "license": "MIT",
        "api_surface_summary": {
            "classes": ["Scene", "Document", "Notebook"],
            "functions": ["load_file", "save_file"],
            "class_details": [
                {
                    "name": "Scene",
                    "methods": ["save", "load", "render", "export"],
                },
                {
                    "name": "Document",
                    "methods": ["open", "close", "get_pages"],
                },
                {
                    "name": "Notebook",
                    "methods": ["create", "add_section"],
                },
            ],
        },
    }


@pytest.fixture
def product_facts_non_foss():
    """Product facts for a non-FOSS product."""
    return {
        "product_name": "Aspose.Note Enterprise",
        "license": "Commercial",
        "api_surface_summary": {
            "classes": ["Scene"],
            "functions": [],
            "class_details": [
                {
                    "name": "Scene",
                    "methods": ["save", "load"],
                },
            ],
        },
    }


# ---------------------------------------------------------------------------
# Test 1: API hallucination - offline detects unknown method
# ---------------------------------------------------------------------------

class TestAPIHallucinationOffline:
    """Tests for offline API hallucination detection."""

    def test_detects_unknown_method(self, drafts_dir, product_facts_foss):
        """Code block with Scene.nonexistent_method() should be flagged
        when API surface only has Scene with save, load, render, export."""
        md_file = drafts_dir / "test_page.md"
        md_file.write_text(
            "---\ntitle: Test\n---\n\n"
            "# Example\n\n"
            "```python\n"
            "scene = Scene()\n"
            "scene.nonexistent_method()\n"
            "```\n",
            encoding="utf-8",
        )

        issues = check_api_hallucination(
            content=md_file.read_text(encoding="utf-8"),
            product_facts=product_facts_foss,
            llm_client=None,
            page_slug="test_page.md",
        )

        assert len(issues) >= 1
        assert issues[0]["check"] == "semantic_accuracy.api_hallucination"
        assert issues[0]["severity"] == "warn"  # Offline heuristic → warn
        assert issues[0]["auto_fixable"] is False
        assert "nonexistent_method" in issues[0]["message"]

    def test_passes_known_methods(self, drafts_dir, product_facts_foss):
        """No issues when code uses known methods (Scene.save, Scene.load)."""
        md_file = drafts_dir / "test_page.md"
        md_file.write_text(
            "---\ntitle: Test\n---\n\n"
            "# Example\n\n"
            "```python\n"
            "scene = Scene()\n"
            "scene.save()\n"
            "scene.load()\n"
            "```\n",
            encoding="utf-8",
        )

        issues = check_api_hallucination(
            content=md_file.read_text(encoding="utf-8"),
            product_facts=product_facts_foss,
            llm_client=None,
            page_slug="test_page.md",
        )

        assert len(issues) == 0

    def test_no_code_blocks_returns_empty(self, product_facts_foss):
        """Content without code blocks should produce no issues."""
        content = "---\ntitle: Test\n---\n\n# Hello\n\nSome text."

        issues = check_api_hallucination(
            content=content,
            product_facts=product_facts_foss,
            llm_client=None,
            page_slug="test_page.md",
        )

        assert issues == []

    def test_unknown_class_not_flagged(self, product_facts_foss):
        """Methods on unknown classes should NOT be flagged (we only flag
        when the class IS known but the method is NOT)."""
        content = (
            "---\ntitle: Test\n---\n\n"
            "```python\n"
            "obj = UnknownClass()\n"
            "obj.some_method()\n"
            "```\n"
        )

        issues = check_api_hallucination(
            content=content,
            product_facts=product_facts_foss,
            llm_client=None,
            page_slug="test_page.md",
        )

        assert len(issues) == 0


# ---------------------------------------------------------------------------
# Test 2: Licensing accuracy - offline detects commercial language
# ---------------------------------------------------------------------------

class TestLicensingAccuracyOffline:
    """Tests for offline licensing accuracy check."""

    def test_detects_commercial_language(self, product_facts_foss):
        """Content with 'commercial license' in a licensing section should be flagged."""
        content = (
            "---\ntitle: Licensing\n---\n\n"
            "# Licensing\n\n"
            "This product requires a commercial license for production use.\n"
            "Please contact sales for pricing.\n"
        )

        issues = check_licensing_accuracy(
            content=content,
            product_facts=product_facts_foss,
            llm_client=None,
            page_slug="licensing.md",
        )

        assert len(issues) >= 1
        assert issues[0]["check"] == "semantic_accuracy.licensing_accuracy"
        assert issues[0]["severity"] == "warn"  # Offline heuristic → warn
        assert issues[0]["auto_fixable"] is True  # TC-1407: BLOCKER-1 fix

    def test_skipped_for_non_foss(self, product_facts_non_foss):
        """No issues when product is not FOSS (even with commercial language)."""
        content = (
            "---\ntitle: Licensing\n---\n\n"
            "# Licensing\n\n"
            "This product requires a commercial license.\n"
        )

        issues = check_licensing_accuracy(
            content=content,
            product_facts=product_facts_non_foss,
            llm_client=None,
            page_slug="licensing.md",
        )

        assert len(issues) == 0

    def test_no_licensing_section_returns_empty(self, product_facts_foss):
        """Content without licensing sections should produce no issues."""
        content = (
            "---\ntitle: Overview\n---\n\n"
            "# Overview\n\n"
            "This is a great product.\n"
        )

        issues = check_licensing_accuracy(
            content=content,
            product_facts=product_facts_foss,
            llm_client=None,
            page_slug="overview.md",
        )

        assert len(issues) == 0

    def test_detects_multiple_commercial_terms(self, product_facts_foss):
        """Multiple commercial terms should each generate an issue."""
        content = (
            "---\ntitle: Plans\n---\n\n"
            "# Pricing Plans\n\n"
            "This requires a commercial license.\n"
            "A trial version is available.\n"
            "Enterprise edition includes premium features.\n"
        )

        issues = check_licensing_accuracy(
            content=content,
            product_facts=product_facts_foss,
            llm_client=None,
            page_slug="plans.md",
        )

        assert len(issues) >= 2

    def test_foss_in_license_field_activates_check(self):
        """Check activates when 'foss' is in license field, not product_name."""
        product_facts = {
            "product_name": "Aspose.Note Python",
            "license": "FOSS (MIT)",
            "api_surface_summary": {},
        }
        content = (
            "---\ntitle: License\n---\n\n"
            "# License Info\n\n"
            "Subscription required for advanced features.\n"
        )

        issues = check_licensing_accuracy(
            content=content,
            product_facts=product_facts,
            llm_client=None,
            page_slug="license.md",
        )

        assert len(issues) >= 1


# ---------------------------------------------------------------------------
# Test 3: Content relevance - offline detects hex constants
# ---------------------------------------------------------------------------

class TestContentRelevanceOffline:
    """Tests for offline content relevance check."""

    def test_detects_hex_constants_in_features(self):
        """Hex constants in Features section should be flagged."""
        content = (
            "---\ntitle: Features\n---\n\n"
            "# Key Features\n\n"
            "- Supports format 0xDEADBEEF\n"
            "- Fast processing\n"
        )

        issues = check_content_relevance(
            content=content,
            product_facts={},
            llm_client=None,
            page_slug="features.md",
        )

        assert len(issues) >= 1
        assert issues[0]["check"] == "semantic_accuracy.content_relevance"
        assert issues[0]["severity"] == "warn"
        assert "Hex constant" in issues[0]["message"]

    def test_passes_clean_content(self):
        """Normal content in features section should pass."""
        content = (
            "---\ntitle: Features\n---\n\n"
            "# Key Features\n\n"
            "- Easy document conversion\n"
            "- Fast PDF processing\n"
            "- Multi-format support\n"
        )

        issues = check_content_relevance(
            content=content,
            product_facts={},
            llm_client=None,
            page_slug="features.md",
        )

        assert len(issues) == 0

    def test_detects_jcid_identifiers(self):
        """jcid-prefixed identifiers in feature sections should be flagged."""
        content = (
            "---\ntitle: Capabilities\n---\n\n"
            "# Capabilities\n\n"
            "- Processes jcidSectionNode elements\n"
            "- Handles all notebook types\n"
        )

        issues = check_content_relevance(
            content=content,
            product_facts={},
            llm_client=None,
            page_slug="capabilities.md",
        )

        assert len(issues) >= 1
        assert "jcid" in issues[0]["message"]

    def test_detects_binary_format_references(self):
        """CompactID/FileNode in feature sections should be flagged."""
        content = (
            "---\ntitle: Features\n---\n\n"
            "# Features\n\n"
            "- Parses CompactID structures\n"
            "- Reads FileNode hierarchies\n"
        )

        issues = check_content_relevance(
            content=content,
            product_facts={},
            llm_client=None,
            page_slug="features.md",
        )

        assert len(issues) >= 2

    def test_non_feature_section_not_flagged(self):
        """Hex constants outside feature sections should NOT be flagged."""
        content = (
            "---\ntitle: Internals\n---\n\n"
            "# Technical Details\n\n"
            "The format uses 0xDEADBEEF as magic bytes.\n"
        )

        issues = check_content_relevance(
            content=content,
            product_facts={},
            llm_client=None,
            page_slug="internals.md",
        )

        assert len(issues) == 0


# ---------------------------------------------------------------------------
# Test 4: check_all integrates all three checks
# ---------------------------------------------------------------------------

class TestCheckAllIntegration:
    """Tests for the check_all integration function."""

    def test_integrates_all_three(self, drafts_dir, product_facts_foss):
        """check_all should run all 3 checks and return combined issues."""
        # Create a draft with issues for all 3 checks
        md_file = drafts_dir / "combined.md"
        md_file.write_text(
            "---\ntitle: Test\n---\n\n"
            "# Key Features\n\n"
            "- Processes 0xDEADBEEF format\n\n"
            "# Licensing\n\n"
            "Requires commercial license.\n\n"
            "# Example\n\n"
            "```python\n"
            "scene = Scene()\n"
            "scene.nonexistent_method()\n"
            "```\n",
            encoding="utf-8",
        )

        issues = check_all(
            drafts_dir=drafts_dir,
            product_facts=product_facts_foss,
            llm_client=None,
        )

        # Should have issues from at least 2 checks (API hallucination + content relevance)
        # Licensing might also fire since product is FOSS
        checks_found = set(i["check"] for i in issues)
        assert "semantic_accuracy.api_hallucination" in checks_found
        assert "semantic_accuracy.content_relevance" in checks_found

    def test_empty_drafts_dir(self, tmp_path, product_facts_foss):
        """check_all with no drafts should return empty list."""
        empty_dir = tmp_path / "drafts"
        empty_dir.mkdir()

        issues = check_all(
            drafts_dir=empty_dir,
            product_facts=product_facts_foss,
        )

        assert issues == []

    def test_nonexistent_drafts_dir(self, tmp_path, product_facts_foss):
        """check_all with non-existent drafts dir should return empty list."""
        issues = check_all(
            drafts_dir=tmp_path / "nonexistent",
            product_facts=product_facts_foss,
        )

        assert issues == []


# ---------------------------------------------------------------------------
# Test 5: LLM path (mocked)
# ---------------------------------------------------------------------------

class TestLLMPathMocked:
    """Tests for LLM-based checks using mock LLM client.

    Testing: mocked
    """

    def test_llm_api_hallucination_generates_issues(self, product_facts_foss):
        """Mock LLM client returning hallucinated API should generate issues."""
        mock_client = MagicMock()
        mock_client.chat_completion.return_value = {
            "content": "HALLUCINATED: Scene.fabricated_api()\nHALLUCINATED: Scene.fake_method()",
        }

        content = (
            "---\ntitle: Test\n---\n\n"
            "```python\n"
            "scene = Scene()\n"
            "scene.fabricated_api()\n"
            "```\n"
        )

        issues = check_api_hallucination(
            content=content,
            product_facts=product_facts_foss,
            llm_client=mock_client,
            page_slug="test.md",
        )

        assert len(issues) >= 1
        assert issues[0]["check"] == "semantic_accuracy.api_hallucination"
        assert issues[0]["severity"] == "error"
        mock_client.chat_completion.assert_called_once()

    def test_llm_licensing_generates_issues(self, product_facts_foss):
        """Mock LLM client returning commercial terms should generate issues."""
        mock_client = MagicMock()
        mock_client.chat_completion.return_value = {
            "content": "COMMERCIAL: commercial license requirement",
        }

        content = (
            "---\ntitle: License\n---\n\n"
            "# Licensing\n\n"
            "This product has a commercial license.\n"
        )

        issues = check_licensing_accuracy(
            content=content,
            product_facts=product_facts_foss,
            llm_client=mock_client,
            page_slug="license.md",
        )

        assert len(issues) >= 1
        assert issues[0]["check"] == "semantic_accuracy.licensing_accuracy"
        mock_client.chat_completion.assert_called_once()

    def test_llm_content_relevance_generates_issues(self):
        """Mock LLM client returning internal details should generate issues."""
        mock_client = MagicMock()
        mock_client.chat_completion.return_value = {
            "content": "INTERNAL: hex constant 0xDEADBEEF used as magic bytes",
        }

        content = (
            "---\ntitle: Features\n---\n\n"
            "# Features\n\n"
            "Supports 0xDEADBEEF format.\n"
        )

        issues = check_content_relevance(
            content=content,
            product_facts={},
            llm_client=mock_client,
            page_slug="features.md",
        )

        assert len(issues) >= 1
        assert issues[0]["check"] == "semantic_accuracy.content_relevance"
        mock_client.chat_completion.assert_called_once()

    def test_llm_none_response_no_issues(self, product_facts_foss):
        """LLM returning 'NONE' should produce no issues."""
        mock_client = MagicMock()
        mock_client.chat_completion.return_value = {
            "content": "NONE",
        }

        content = (
            "---\ntitle: Test\n---\n\n"
            "```python\n"
            "scene = Scene()\n"
            "scene.save()\n"
            "```\n"
        )

        issues = check_api_hallucination(
            content=content,
            product_facts=product_facts_foss,
            llm_client=mock_client,
            page_slug="test.md",
        )

        assert len(issues) == 0

    def test_llm_exception_falls_through(self, product_facts_foss):
        """LLM exception should be caught (no crash), returning empty issues."""
        mock_client = MagicMock()
        mock_client.chat_completion.side_effect = Exception("LLM unavailable")

        content = (
            "---\ntitle: Test\n---\n\n"
            "```python\n"
            "scene = Scene()\n"
            "scene.nonexistent()\n"
            "```\n"
        )

        issues = check_api_hallucination(
            content=content,
            product_facts=product_facts_foss,
            llm_client=mock_client,
            page_slug="test.md",
        )

        # LLM path should silently fail, returning no issues (not crash)
        assert isinstance(issues, list)


# ---------------------------------------------------------------------------
# Test 6: No LLM falls back to offline
# ---------------------------------------------------------------------------

class TestOfflineFallback:
    """Tests verifying that None llm_client uses offline heuristics."""

    def test_no_llm_falls_back_to_offline(self, drafts_dir, product_facts_foss):
        """None llm_client should use offline heuristics and still detect issues."""
        md_file = drafts_dir / "test.md"
        md_file.write_text(
            "---\ntitle: Test\n---\n\n"
            "# Example\n\n"
            "```python\n"
            "scene = Scene()\n"
            "scene.nonexistent_method()\n"
            "```\n",
            encoding="utf-8",
        )

        issues = check_all(
            drafts_dir=drafts_dir,
            product_facts=product_facts_foss,
            llm_client=None,  # Explicitly None = offline
        )

        # Offline fallback should still detect the hallucinated API
        api_issues = [i for i in issues if i["check"] == "semantic_accuracy.api_hallucination"]
        assert len(api_issues) >= 1

    def test_offline_uses_heuristics_not_llm(self, product_facts_foss):
        """Verify that with llm_client=None, no LLM calls are made."""
        content = (
            "---\ntitle: Test\n---\n\n"
            "```python\n"
            "scene = Scene()\n"
            "scene.nonexistent_method()\n"
            "```\n"
        )

        # If this tried to use LLM, it would crash since None has no methods
        issues = check_api_hallucination(
            content=content,
            product_facts=product_facts_foss,
            llm_client=None,
            page_slug="test.md",
        )

        assert len(issues) >= 1
        assert "nonexistent_method" in issues[0]["message"]


# ---------------------------------------------------------------------------
# Test 7: Issue format validation
# ---------------------------------------------------------------------------

class TestIssueFormat:
    """Tests verifying issue format matches W7 schema."""

    def test_issue_has_required_fields(self, product_facts_foss):
        """Every issue must have issue_id, check, severity, auto_fixable, message, location."""
        content = (
            "---\ntitle: Test\n---\n\n"
            "```python\n"
            "scene = Scene()\n"
            "scene.nonexistent()\n"
            "```\n"
        )

        issues = check_api_hallucination(
            content=content,
            product_facts=product_facts_foss,
            llm_client=None,
            page_slug="test.md",
        )

        assert len(issues) >= 1
        for issue in issues:
            assert "issue_id" in issue
            assert "check" in issue
            assert "severity" in issue
            assert "auto_fixable" in issue
            assert "message" in issue
            assert "location" in issue
            assert "path" in issue["location"]
            assert "line" in issue["location"]

    def test_issue_id_is_uuid(self, product_facts_foss):
        """issue_id should be a valid UUID string."""
        import uuid as uuid_mod
        content = (
            "---\ntitle: Test\n---\n\n"
            "```python\n"
            "scene = Scene()\n"
            "scene.nonexistent()\n"
            "```\n"
        )

        issues = check_api_hallucination(
            content=content,
            product_facts=product_facts_foss,
            llm_client=None,
            page_slug="test.md",
        )

        assert len(issues) >= 1
        # Should not raise ValueError
        uuid_mod.UUID(issues[0]["issue_id"])


# ---------------------------------------------------------------------------
# TC-3617 B2: Semantic cache tests
# ---------------------------------------------------------------------------


class TestSemanticCache:
    """TC-3617 B2: Content-hash-keyed cache tests."""

    def test_cache_hit_skips_llm(self, drafts_dir, product_facts_foss, tmp_path):
        """Prepopulated cache should result in 0 LLM calls."""
        import json
        from launch.workers.w7_content_reviewer.checks.semantic_accuracy import (
            _cache_key,
        )

        # Create a draft file
        content = "# Test\n\nSome content.\n"
        (drafts_dir / "page.md").write_text(content, encoding="utf-8")

        # Pre-populate cache
        run_dir = tmp_path / "run"
        artifacts = run_dir / "artifacts"
        artifacts.mkdir(parents=True)
        key = _cache_key("page.md", content, None)
        cached_issues = [{"check": "cached", "severity": "info", "message": "cached"}]
        (artifacts / "semantic_cache.json").write_text(
            json.dumps({key: cached_issues}), encoding="utf-8",
        )

        mock_llm = MagicMock()
        issues = check_all(
            drafts_dir, product_facts_foss, llm_client=mock_llm,
            run_dir=run_dir, max_parallel_files=1,
        )

        # LLM should NOT have been called (cache hit)
        assert mock_llm.chat_completion.call_count == 0
        assert issues == cached_issues

    def test_cache_miss_stores_result(self, drafts_dir, product_facts_foss, tmp_path):
        """First run stores result; second run hits cache."""
        import json

        content = "# Test\n\nSome content.\n"
        (drafts_dir / "page.md").write_text(content, encoding="utf-8")

        run_dir = tmp_path / "run"
        (run_dir / "artifacts").mkdir(parents=True)

        mock_llm = MagicMock()
        mock_llm.chat_completion.return_value = {
            "content": json.dumps({
                "api_hallucinations": [],
                "licensing_issues": [],
                "internal_details": [],
            }),
        }

        # First run — cache miss, calls LLM
        check_all(
            drafts_dir, product_facts_foss, llm_client=mock_llm,
            run_dir=run_dir, max_parallel_files=1,
        )
        assert mock_llm.chat_completion.call_count == 1

        # Second run — cache hit, skips LLM
        mock_llm.reset_mock()
        check_all(
            drafts_dir, product_facts_foss, llm_client=mock_llm,
            run_dir=run_dir, max_parallel_files=1,
        )
        assert mock_llm.chat_completion.call_count == 0

    def test_cache_invalidated_by_content_change(
        self, drafts_dir, product_facts_foss, tmp_path,
    ):
        """Changed content should cause cache miss and new LLM call."""
        import json

        page = drafts_dir / "page.md"
        page.write_text("# Test v1\n\nOriginal.\n", encoding="utf-8")

        run_dir = tmp_path / "run"
        (run_dir / "artifacts").mkdir(parents=True)

        mock_llm = MagicMock()
        mock_llm.chat_completion.return_value = {
            "content": json.dumps({
                "api_hallucinations": [],
                "licensing_issues": [],
                "internal_details": [],
            }),
        }

        # First run
        check_all(
            drafts_dir, product_facts_foss, llm_client=mock_llm,
            run_dir=run_dir, max_parallel_files=1,
        )
        assert mock_llm.chat_completion.call_count == 1

        # Change content
        page.write_text("# Test v2\n\nModified.\n", encoding="utf-8")

        # Second run — content changed, cache miss
        mock_llm.reset_mock()
        check_all(
            drafts_dir, product_facts_foss, llm_client=mock_llm,
            run_dir=run_dir, max_parallel_files=1,
        )
        assert mock_llm.chat_completion.call_count == 1

    def test_cache_key_uses_excerpt_text_not_metadata(self) -> None:
        """Metadata-only evidence changes should not invalidate the cache key."""
        from launch.workers.w7_content_reviewer.checks.semantic_accuracy import _cache_key

        content = "# Test\n\nStable content.\n"
        excerpts_a = [
            {"claim_id": "c-2", "excerpt": "Second excerpt", "score": 0.2},
            {"claim_id": "c-1", "excerpt": "First excerpt", "line": 10},
        ]
        excerpts_b = [
            {"claim_id": "c-2", "excerpt": "Second excerpt", "score": 0.9, "source": "docs"},
            {"claim_id": "c-1", "excerpt": "First excerpt", "line": 999, "note": "changed"},
        ]
        excerpts_c = [
            {"claim_id": "c-2", "excerpt": "Second excerpt updated", "score": 0.2},
            {"claim_id": "c-1", "excerpt": "First excerpt", "line": 10},
        ]

        key_a = _cache_key("page.md", content, excerpts_a)
        key_b = _cache_key("page.md", content, excerpts_b)
        key_c = _cache_key("page.md", content, excerpts_c)

        assert key_a == key_b
        assert key_a != key_c

    # -----------------------------------------------------------------------
    # TC-3617 SR-02: Observability tests
    # -----------------------------------------------------------------------

    def test_bundle_fallback_emits_info_log(
        self, drafts_dir, product_facts_foss, tmp_path, caplog,
    ):
        """Bundle fallback must emit an INFO-level log with slug and exception type."""
        import logging
        import json

        (drafts_dir / "page.md").write_text(
            "# Test\n\n```python\nscene.fake()\n```\n", encoding="utf-8",
        )

        mock_llm = MagicMock()
        mock_llm.chat_completion.side_effect = TimeoutError("endpoint timeout")

        with caplog.at_level(
            logging.INFO,
            logger="launch.workers.w7_content_reviewer.checks.semantic_accuracy",
        ):
            check_all(
                drafts_dir, product_facts_foss,
                llm_client=mock_llm, max_parallel_files=1,
            )

        fallback_logs = [
            r for r in caplog.records
            if "fallback" in r.message.lower() and r.levelno == logging.INFO
        ]
        assert len(fallback_logs) >= 1, (
            "Expected at least one INFO log mentioning 'fallback'"
        )
        assert "TimeoutError" in fallback_logs[0].message

    def test_cache_hit_emits_debug_log(
        self, drafts_dir, product_facts_foss, tmp_path, caplog,
    ):
        """Cache hit must emit a DEBUG-level log mentioning the page path."""
        import logging
        import json

        content = "# Test\n\nStable content.\n"
        (drafts_dir / "page.md").write_text(content, encoding="utf-8")

        run_dir = tmp_path / "run"
        (run_dir / "artifacts").mkdir(parents=True)

        mock_llm = MagicMock()
        mock_llm.chat_completion.return_value = {
            "content": json.dumps({
                "api_hallucinations": [],
                "licensing_issues": [],
                "internal_details": [],
            }),
        }

        # First run — populate cache
        check_all(
            drafts_dir, product_facts_foss,
            llm_client=mock_llm, run_dir=run_dir, max_parallel_files=1,
        )
        mock_llm.reset_mock()

        # Second run — should emit DEBUG cache hit
        with caplog.at_level(
            logging.DEBUG,
            logger="launch.workers.w7_content_reviewer.checks.semantic_accuracy",
        ):
            check_all(
                drafts_dir, product_facts_foss,
                llm_client=mock_llm, run_dir=run_dir, max_parallel_files=1,
            )

        hit_logs = [
            r for r in caplog.records
            if "cache hit" in r.message.lower() and r.levelno == logging.DEBUG
        ]
        assert len(hit_logs) >= 1, "Expected at least one DEBUG 'cache hit' log"

    def test_cache_write_failure_emits_warning(
        self, drafts_dir, product_facts_foss, tmp_path, caplog,
    ):
        """_save_cache() write failure must emit WARNING and not raise."""
        import logging
        import json
        from unittest.mock import patch

        (drafts_dir / "page.md").write_text("# Test\n\nContent.\n", encoding="utf-8")

        run_dir = tmp_path / "run"
        (run_dir / "artifacts").mkdir(parents=True)

        mock_llm = MagicMock()
        mock_llm.chat_completion.return_value = {
            "content": json.dumps({
                "api_hallucinations": [],
                "licensing_issues": [],
                "internal_details": [],
            }),
        }

        with caplog.at_level(
            logging.WARNING,
            logger="launch.workers.w7_content_reviewer.checks.semantic_accuracy",
        ):
            with patch(
                "launch.workers.w7_content_reviewer.checks.semantic_accuracy.os.replace",
                side_effect=OSError("Permission denied"),
            ):
                # Must not raise
                issues = check_all(
                    drafts_dir, product_facts_foss,
                    llm_client=mock_llm, run_dir=run_dir, max_parallel_files=1,
                )

        # Results still returned despite write failure
        assert isinstance(issues, list)

        warning_logs = [
            r for r in caplog.records
            if "cache" in r.message.lower() and r.levelno == logging.WARNING
        ]
        assert len(warning_logs) >= 1, (
            "Expected at least one WARNING log about cache write failure"
        )

    def test_cache_write_failure_does_not_lose_results(
        self, drafts_dir, product_facts_foss, tmp_path,
    ):
        """If _save_cache() raises OSError, check_all still returns correct issues.

        TC-3617 SR-03: Data-correctness under failure — orthogonal to observability test.
        """
        import json
        from unittest.mock import patch

        (drafts_dir / "page.md").write_text(
            "# Test\n\n```python\nscene.fake()\n```\n", encoding="utf-8",
        )

        run_dir = tmp_path / "run"
        (run_dir / "artifacts").mkdir(parents=True)

        mock_llm = MagicMock()
        # Return one API hallucination
        mock_llm.chat_completion.return_value = {
            "content": json.dumps({
                "api_hallucinations": [{"name": "Scene.fake", "line": 3, "reason": "not in API"}],
                "licensing_issues": [],
                "internal_details": [],
            }),
        }

        with patch(
            "launch.workers.w7_content_reviewer.checks.semantic_accuracy.os.replace",
            side_effect=OSError("Disk full"),
        ):
            issues = check_all(
                drafts_dir, product_facts_foss,
                llm_client=mock_llm, run_dir=run_dir, max_parallel_files=1,
            )

        # Issues must be returned correctly despite write failure
        assert isinstance(issues, list)
        api_issues = [i for i in issues if "api_hallucination" in i.get("check", "")]
        assert len(api_issues) == 1, (
            "API hallucination issue must be present even when cache write fails"
        )
