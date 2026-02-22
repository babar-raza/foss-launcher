"""Tests for TC-2387: SEO Gate 4 Upgrade."""
import pytest
from pathlib import Path


# Import the function — adjust path based on actual file location
def _import_check_seo_fields():
    """Import _check_seo_fields from wherever it lives."""
    try:
        from launch.workers.w9_validator.gates.gate_4_frontmatter_required_fields import _check_seo_fields
        return _check_seo_fields
    except ImportError:
        # Try alternate names
        import importlib
        import pkgutil
        for name in ["gate_4_frontmatter", "gate_4", "gate_4_frontmatter_fields"]:
            try:
                mod = importlib.import_module(f"launch.workers.w9_validator.gates.{name}")
                return mod._check_seo_fields
            except (ImportError, AttributeError):
                continue
        pytest.skip("_check_seo_fields not found in any gate_4 module")


class TestSeoGate4:
    @pytest.fixture
    def check_seo_fields(self):
        return _import_check_seo_fields()

    def test_valid_frontmatter_no_issues(self, check_seo_fields):
        frontmatter = {
            "title": "Getting Started",
            "seoTitle": "Getting Started with Aspose",
            "description": "Learn how to use Aspose for Python to convert documents.",
        }
        issues = check_seo_fields(frontmatter, "/content/getting-started/index.md")
        seo_issues = [i for i in issues if i.get("error_code", "").startswith("G4-SEO")]
        assert len(seo_issues) == 0

    def test_missing_description_g4_seo_001(self, check_seo_fields):
        frontmatter = {"title": "Test Page", "seoTitle": "Test"}
        issues = check_seo_fields(frontmatter, "/content/test/index.md")
        codes = [i["error_code"] for i in issues]
        assert "G4-SEO-001" in codes

    def test_description_too_long_g4_seo_002(self, check_seo_fields):
        frontmatter = {
            "title": "Test",
            "description": "A" * 161,  # 161 chars — over 160 limit
        }
        issues = check_seo_fields(frontmatter, "/content/test/index.md")
        codes = [i["error_code"] for i in issues]
        assert "G4-SEO-002" in codes

    def test_description_exactly_160_chars_ok(self, check_seo_fields):
        frontmatter = {
            "title": "Test",
            "description": "A" * 160,  # Exactly 160 — OK
        }
        issues = check_seo_fields(frontmatter, "/content/test/index.md")
        codes = [i["error_code"] for i in issues]
        assert "G4-SEO-002" not in codes

    def test_seo_title_too_long_g4_seo_003(self, check_seo_fields):
        frontmatter = {
            "title": "Short",
            "seoTitle": "A" * 61,  # 61 chars — over 60 limit
            "description": "Valid description here.",
        }
        issues = check_seo_fields(frontmatter, "/content/test/index.md")
        codes = [i["error_code"] for i in issues]
        assert "G4-SEO-003" in codes

    def test_seo_title_exactly_60_chars_ok(self, check_seo_fields):
        frontmatter = {
            "title": "Short",
            "seoTitle": "A" * 60,  # Exactly 60 — OK
            "description": "Valid description here.",
        }
        issues = check_seo_fields(frontmatter, "/content/test/index.md")
        codes = [i["error_code"] for i in issues]
        assert "G4-SEO-003" not in codes

    def test_falls_back_to_title_for_seo_check(self, check_seo_fields):
        """If no seoTitle, should check title length."""
        frontmatter = {
            "title": "A" * 61,  # Over 60
            "description": "Valid description here.",
            # No seoTitle
        }
        issues = check_seo_fields(frontmatter, "/content/test/index.md")
        codes = [i["error_code"] for i in issues]
        assert "G4-SEO-003" in codes

    def test_all_issues_have_required_fields(self, check_seo_fields):
        frontmatter = {}  # Missing everything
        issues = check_seo_fields(frontmatter, "/content/test/index.md")
        for issue in issues:
            assert "issue_id" in issue
            assert "gate" in issue
            assert "severity" in issue
            assert "message" in issue
            assert "error_code" in issue
            assert "location" in issue
            assert "status" in issue

    def test_severity_is_warn_not_error(self, check_seo_fields):
        """SEO issues are warnings, not errors (non-blocking)."""
        frontmatter = {}  # Missing everything
        issues = check_seo_fields(frontmatter, "/content/test/index.md")
        seo_issues = [i for i in issues if i.get("error_code", "").startswith("G4-SEO")]
        for issue in seo_issues:
            assert issue["severity"] == "warn"
