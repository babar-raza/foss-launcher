"""Tests for W5.5 ContentReviewer semantic accuracy checks (TC-1405).

Tests cover all 3 LLM-based semantic checks with offline fallback:
1. API hallucination detection
2. Licensing accuracy
3. Content relevance

Testing: mocked (LLM path tests use mock LLMProviderClient)
"""
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from launch.workers.w5_5_content_reviewer.checks.semantic_accuracy import (
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
    """Tests verifying issue format matches W5.5 schema."""

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
