"""Tests for TC-3682: W10 G4 routing split and W8 See Also detection hardening."""

from __future__ import annotations

import re
import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestW10G4RoutingSplit:
    """Verify apply_fix routes G4 error codes to the correct handler."""

    def test_g4_heading_trailing_punct_routes_correctly(self):
        """G4_HEADING_TRAILING_PUNCT should go to fix_g4_heading_punct."""
        from launch.workers.w10_fixer.worker import apply_fix

        issue = {
            "error_code": "G4_HEADING_TRAILING_PUNCT",
            "gate": "gate_section_structure",
            "location": {"path": "test.md"},
        }
        with patch(
            "launch.workers.w10_fixer.worker.fix_g4_heading_punct",
            return_value={"fixed": True},
        ) as mock:
            result = apply_fix(issue, Path("/tmp/run"), None)
            mock.assert_called_once()
            assert result["fixed"] is True

    def test_g4_duplicate_h2_routes_to_dedup(self):
        """G4_DUPLICATE_H2 should go to fix_g4_duplicate_h2."""
        from launch.workers.w10_fixer.worker import apply_fix

        issue = {
            "error_code": "G4_DUPLICATE_H2",
            "gate": "gate_section_structure",
            "location": {"path": "test.md"},
        }
        with patch(
            "launch.workers.w10_fixer.worker.fix_g4_duplicate_h2",
            return_value={"fixed": True},
        ) as mock:
            result = apply_fix(issue, Path("/tmp/run"), None)
            mock.assert_called_once()
            assert result["fixed"] is True

    def test_g4_see_also_not_last_routes_to_position(self):
        """G4_SEE_ALSO_NOT_LAST should go to fix_g4_see_also_position."""
        from launch.workers.w10_fixer.worker import apply_fix

        issue = {
            "error_code": "G4_SEE_ALSO_NOT_LAST",
            "gate": "gate_section_structure",
            "location": {"path": "test.md"},
        }
        with patch(
            "launch.workers.w10_fixer.worker.fix_g4_see_also_position",
            return_value={"fixed": True},
        ) as mock:
            result = apply_fix(issue, Path("/tmp/run"), None)
            mock.assert_called_once()
            assert result["fixed"] is True

    def test_unknown_g4_falls_back_to_heading_punct(self):
        """Unknown G4_XXX codes should fall back to fix_g4_heading_punct."""
        from launch.workers.w10_fixer.worker import apply_fix

        issue = {
            "error_code": "G4_UNKNOWN_FUTURE",
            "gate": "gate_section_structure",
            "location": {"path": "test.md"},
        }
        with patch(
            "launch.workers.w10_fixer.worker.fix_g4_heading_punct",
            return_value={"fixed": True},
        ) as mock:
            result = apply_fix(issue, Path("/tmp/run"), None)
            mock.assert_called_once()


class TestW8SeeAlsoDetection:
    """Verify W8 inject_see_also_section uses case-insensitive detection."""

    def test_case_insensitive_see_also(self):
        """W8 should detect '## See also' (lowercase a)."""
        from launch.workers.w8_linker_and_patcher.worker import (
            inject_see_also_section,
        )

        content = "## See also\n\n- [Link](url)\n"
        result = inject_see_also_section(content, [], [])
        # Should NOT inject duplicate (already has See Also)
        assert result.count("## See") == 1

    def test_h3_see_also_detected(self):
        """W8 should detect '### See Also' (H3 level)."""
        from launch.workers.w8_linker_and_patcher.worker import (
            inject_see_also_section,
        )

        content = "### See Also\n\n- [Link](url)\n"
        result = inject_see_also_section(content, [], [])
        assert result.count("See Also") == 1
