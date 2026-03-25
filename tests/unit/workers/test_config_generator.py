"""Unit tests for config_generator brand extraction integration (SR-03).

Verifies that _derive_config_filename, _derive_display_name, and
_derive_canonical_import all delegate to the canonical _extract_brand_from_org
from acquisition.py — not an inline copy.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Ensure acquisition module is registered before importing config_generator
# which will 'from launcher.phase1.acquisition import _extract_brand_from_org'
# ---------------------------------------------------------------------------
if "launcher.phase1.acquisition" not in sys.modules:
    import importlib.util as _ilu

    _acq_path = (
        Path(__file__).resolve().parent.parent.parent.parent
        / "src"
        / "launcher"
        / "phase1"
        / "acquisition.py"
    )
    _spec = _ilu.spec_from_file_location("launcher.phase1.acquisition", _acq_path)
    _acq_mod = _ilu.module_from_spec(_spec)  # type: ignore[arg-type]
    sys.modules["launcher.phase1.acquisition"] = _acq_mod
    _spec.loader.exec_module(_acq_mod)  # type: ignore[union-attr]

from launcher.intake.config_generator import (  # noqa: E402
    _derive_canonical_import,
    _derive_config_filename,
    _derive_display_name,
)
from launcher.phase1.acquisition import _extract_brand_from_org  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _repo(owner_login: str, repo_name: str = "", language: str = "Python") -> dict:
    return {
        "owner": {"login": owner_login},
        "name": repo_name,
        "language": language,
    }


# ---------------------------------------------------------------------------
# _derive_config_filename
# ---------------------------------------------------------------------------


class TestDeriveConfigFilename:
    def test_cells_python_returns_correct_slug(self):
        repo = _repo("aspose-cells-foss", "Aspose.Cells-FOSS-for-Python")
        result = _derive_config_filename(repo, platform="python")
        assert result == "aspose-cells-foss-python"

    def test_slides_java_returns_correct_slug(self):
        repo = _repo("aspose-slides-foss", "Aspose.Slides-FOSS-for-Java")
        result = _derive_config_filename(repo, platform="java")
        assert result == "aspose-slides-foss-java"

    def test_3d_dotnet_returns_correct_slug(self):
        repo = _repo("aspose-3d-foss", "Aspose.3D-FOSS-for-.NET")
        result = _derive_config_filename(repo, platform="dotnet")
        assert result == "aspose-3d-foss-dotnet"

    def test_all_stop_word_org_yields_unknown_brand(self):
        """Org with only stop words → brand='unknown' appears in slug."""
        repo = _repo("foss-for-net", "some-repo")
        result = _derive_config_filename(repo, platform="python")
        # _extract_family("some-repo") → "some"; brand → "unknown"
        assert result.startswith("unknown-")

    def test_uses_canonical_extractor(self):
        """Confirm the function actually calls _extract_brand_from_org."""
        repo = _repo("aspose-email-foss", "Aspose.Email-FOSS-for-Python")
        with patch(
            "launcher.intake.config_generator._extract_brand_from_org",
            wraps=_extract_brand_from_org,
        ) as mock_fn:
            _derive_config_filename(repo, platform="python")
        mock_fn.assert_called_once_with("aspose-email-foss")


# ---------------------------------------------------------------------------
# _derive_display_name
# ---------------------------------------------------------------------------


class TestDeriveDisplayName:
    def test_cells_org_returns_aspose_cells(self):
        repo = _repo("aspose-cells-foss", "Aspose.Cells-FOSS-for-Python")
        assert _derive_display_name(repo) == "Aspose.Cells"

    def test_3d_family_uses_display_map(self):
        repo = _repo("aspose-3d-foss", "Aspose.3D-FOSS-for-Python")
        assert _derive_display_name(repo) == "Aspose.3D"

    def test_unknown_brand_omits_brand_prefix(self):
        """All-stop-word org → brand='unknown' → display name has no brand prefix."""
        repo = _repo("foss-for-net", "some-repo")
        result = _derive_display_name(repo)
        # Should not start with 'Unknown.' — brand is suppressed for "unknown"
        assert not result.startswith("Unknown.")

    def test_uses_canonical_extractor(self):
        repo = _repo("aspose-note-foss", "Aspose.Note-FOSS-for-Python")
        with patch(
            "launcher.intake.config_generator._extract_brand_from_org",
            wraps=_extract_brand_from_org,
        ) as mock_fn:
            _derive_display_name(repo)
        mock_fn.assert_called_once_with("aspose-note-foss")


# ---------------------------------------------------------------------------
# _derive_canonical_import
# ---------------------------------------------------------------------------


class TestDeriveCanonicalImport:
    def test_cells_python_returns_underscore_slug(self):
        repo = _repo("aspose-cells-foss", "Aspose.Cells-FOSS-for-Python")
        result = _derive_canonical_import(repo, platform="python", families_yaml_path=None)
        assert result == "aspose_cells_foss"

    def test_uses_canonical_extractor(self):
        repo = _repo("aspose-cells-foss", "Aspose.Cells-FOSS-for-Python")
        with patch(
            "launcher.intake.config_generator._extract_brand_from_org",
            wraps=_extract_brand_from_org,
        ) as mock_fn:
            _derive_canonical_import(repo, platform="python", families_yaml_path=None)
        mock_fn.assert_called_once_with("aspose-cells-foss")

    def test_all_stop_word_org_uses_unknown(self):
        # Pass nonexistent yaml to force the brand-based fallback code path.
        # families.yaml has a hardcoded template ("aspose_{family}_foss") that
        # bypasses brand entirely — skip it so we can test the fallback logic.
        repo = _repo("foss-for-net", "some-repo")
        result = _derive_canonical_import(
            repo, platform="python", families_yaml_path=Path("/nonexistent/families.yaml")
        )
        # Fallback: f"{brand}_{family}_foss" → "unknown_some_foss"
        assert result.startswith("unknown_")


# ---------------------------------------------------------------------------
# TC-5188 — _derive_product_name: slash truncation, fallback, punct stripping
# ---------------------------------------------------------------------------


class TestDeriveProductName:
    """TC-5188: product_name sanitizer — UEX-05 regression coverage."""

    def _fn(self, desc, name="aspose-slides", *, brand="", family="", platform=""):
        from launcher.intake.config_generator import _derive_product_name
        return _derive_product_name(
            {"description": desc, "name": name},
            brand=brand, family=family, platform=platform,
        )

    def test_slash_in_description_no_trailing_hash_or_lone_char(self):
        """TC-5188 Test 1: slash-containing desc → no trailing '#', '/', or lone char."""
        import re
        result = self._fn("The official open-source C#/VB.NET library for presentations")
        assert not re.search(r"[#/(\\,;:([\]]$", result), f"Trailing punct in {result!r}"
        assert not re.search(r"\s[A-Za-z]$", result), f"Trailing lone char in {result!r}"

    def test_uex05_exact_regression(self):
        """TC-5188 Test 1b: full UEX-05 real-world input → exact match."""
        result = self._fn(
            "The official open-source C#/VB.NET library for generating and reading Word documents"
        )
        assert result == "The official open-source", (
            f"Expected 'The official open-source', got {result!r}"
        )

    def test_clean_description_unchanged(self):
        """TC-5188 Test 2: clean description without slash/punct passes through."""
        result = self._fn("Aspose Slides FOSS for Python - A free presentation library")
        assert result == "Aspose Slides FOSS for Python", (
            f"Expected 'Aspose Slides FOSS for Python', got {result!r}"
        )

    def test_bare_language_token_triggers_canonical_fallback(self):
        """TC-5188 Test 3: bare language token 'C#' → canonical fallback."""
        result = self._fn("C#", brand="Aspose", family="slides", platform="dotnet")
        assert result == "Aspose Slides FOSS for Dotnet", f"Got {result!r}"

    def test_trailing_punctuation_stripped(self):
        """TC-5188 Test 4: trailing '(' stripped, result has no trailing punct."""
        import re
        result = self._fn("Open source document library (C#")
        assert not re.search(r"[#/(\\,;:([\]]$", result), f"Trailing punct in {result!r}"
        assert not re.search(r"\s[A-Za-z]$", result), f"Trailing lone char in {result!r}"

    def test_short_description_no_kwargs_returns_repo_name(self):
        """TC-5188 Test 5: short desc + no brand/family/platform → repo name fallback."""
        result = self._fn("C#", name="aspose-slides-dotnet")
        assert result == "aspose-slides-dotnet", f"Expected repo name fallback, got {result!r}"

    def test_fallback_emits_warning(self, caplog):
        """TC-5188 Test 6: fallback condition emits WARNING with grep-able key.

        Uses 'C#/VB.NET' — len > 5 so enters the split path, produces 'C' after
        stripping '#', which is len < 8 → triggers product_name_sanitizer_fallback warning.
        """
        import logging
        from launcher.intake.config_generator import _derive_product_name
        with caplog.at_level(logging.WARNING, logger="launcher.intake.config_generator"):
            result = _derive_product_name(
                {"description": "C#/VB.NET", "name": "aspose-slides"},
                brand="Aspose", family="slides", platform="dotnet",
            )
        assert result == "Aspose Slides FOSS for Dotnet"
        assert any(
            "product_name_sanitizer_fallback" in r.message for r in caplog.records
        ), f"Expected sanitizer_fallback warning. Got: {[r.message for r in caplog.records]}"
