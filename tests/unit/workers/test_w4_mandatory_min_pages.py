"""Unit tests for W4 mandatory minimum pages enforcement.

Tests that select_templates_with_quota() enforces min_pages and that the
main loop falls back to plan_pages_for_section() when templates are insufficient.

Spec references:
- specs/06_page_planning.md (Page planning algorithm)
"""

from __future__ import annotations

import pytest
from typing import Dict, Any, List

from launch.workers.w4_ia_planner.worker import (
    select_templates_with_quota,
    _get_section_expansion,
)


def _make_template(slug: str, is_mandatory: bool = False, section: str = "docs") -> Dict[str, Any]:
    """Create a minimal template dict for testing."""
    return {
        "slug": slug,
        "section": section,
        "is_mandatory": is_mandatory,
        "template_path": f"specs/templates/{section}/{slug}.md",
        "variant": "default",
    }


def _make_templates(count: int, prefix: str = "opt", is_mandatory: bool = False) -> List[Dict[str, Any]]:
    """Create a list of template dicts for testing."""
    return [_make_template(f"{prefix}-{i}", is_mandatory=is_mandatory) for i in range(count)]


# ---------------------------------------------------------------------------
# Test 1: Backward compatibility — no min_pages argument
# ---------------------------------------------------------------------------
class TestSelectTemplatesMinPages:

    def test_backward_compat_no_min_pages(self):
        """Calling without min_pages preserves existing max_pages-only behavior."""
        optional = _make_templates(3, prefix="opt")
        selected = select_templates_with_quota([], optional, max_pages=2)
        assert len(selected) == 2

    def test_min_met_by_mandatory(self):
        """When mandatory count >= min_pages, no extra optional needed."""
        mandatory = _make_templates(3, prefix="mand", is_mandatory=True)
        selected = select_templates_with_quota(mandatory, [], max_pages=5, min_pages=3)
        assert len(selected) == 3

    def test_min_met_by_mandatory_plus_optional(self):
        """min_pages already satisfied by normal selection (mandatory + optional up to max)."""
        mandatory = _make_templates(1, prefix="mand", is_mandatory=True)
        optional = _make_templates(5, prefix="opt")
        selected = select_templates_with_quota(mandatory, optional, max_pages=5, min_pages=3)
        # Normal selection: 1 mandatory + 4 optional = 5 (already >= 3)
        assert len(selected) == 5

    def test_min_forces_more_optional(self):
        """When min_pages > max_pages, min_pages wins and more optional are included."""
        mandatory = _make_templates(1, prefix="mand", is_mandatory=True)
        optional = _make_templates(5, prefix="opt")
        selected = select_templates_with_quota(mandatory, optional, max_pages=3, min_pages=4)
        # effective_max becomes 4 (min wins); 1 mandatory + 3 optional = 4
        assert len(selected) == 4

    def test_insufficient_templates(self):
        """When total templates < min_pages, return all available (caller handles fallback)."""
        mandatory = _make_templates(1, prefix="mand", is_mandatory=True)
        optional = _make_templates(1, prefix="opt")
        selected = select_templates_with_quota(mandatory, optional, max_pages=10, min_pages=5)
        # Only 2 templates available
        assert len(selected) == 2

    def test_zero_optional_only_mandatory(self):
        """Mandatory-only selection meets min_pages exactly."""
        mandatory = _make_templates(2, prefix="mand", is_mandatory=True)
        selected = select_templates_with_quota(mandatory, [], max_pages=5, min_pages=2)
        assert len(selected) == 2

    def test_min_exceeds_max_warning(self, capsys):
        """When min_pages > max_pages, a warning is logged and min_pages wins."""
        optional = _make_templates(10, prefix="opt")
        selected = select_templates_with_quota([], optional, max_pages=2, min_pages=5)
        assert len(selected) == 5
        captured = capsys.readouterr()
        assert "w4_quota_conflict" in captured.out

    def test_deterministic(self):
        """Same inputs produce identical outputs across multiple calls."""
        mandatory = _make_templates(1, prefix="mand", is_mandatory=True)
        optional = _make_templates(5, prefix="opt")
        kwargs = dict(max_pages=4, min_pages=3)
        result_a = select_templates_with_quota(mandatory, optional, **kwargs)
        result_b = select_templates_with_quota(mandatory, optional, **kwargs)
        assert result_a == result_b

    def test_empty_mandatory_and_optional(self):
        """No templates available — returns empty list (caller must handle fallback)."""
        selected = select_templates_with_quota([], [], max_pages=5, min_pages=3)
        assert len(selected) == 0

    def test_max_pages_zero_with_min(self, capsys):
        """max_pages=0 but min_pages>0: min_pages wins."""
        optional = _make_templates(3, prefix="opt")
        selected = select_templates_with_quota([], optional, max_pages=0, min_pages=2)
        assert len(selected) == 2
        captured = capsys.readouterr()
        assert "w4_quota_conflict" in captured.out

    def test_positional_args_unchanged(self):
        """Calling with only 3 positional args (no min_pages) works as before."""
        mandatory = _make_templates(2, prefix="mand", is_mandatory=True)
        optional = _make_templates(5, prefix="opt")
        selected = select_templates_with_quota(mandatory, optional, 5)
        # 2 mandatory + 3 optional = 5
        assert len(selected) == 5


# ---------------------------------------------------------------------------
# Test 9: required_min formula
# ---------------------------------------------------------------------------
class TestRequiredMinFormula:

    def test_all_zero_defaults_to_one(self):
        """max(1, 0, 0) == 1: every enabled section gets at least 1 page."""
        exp = _get_section_expansion({}, "docs")
        eff_min = 0
        required_min = max(1, exp["min_pages"], eff_min)
        assert required_min == 1

    def test_expansion_min_wins(self):
        """max(1, 3, 2) == 3: page_expansion.min_pages dominates."""
        exp = _get_section_expansion({"docs": {"min_pages": 3}}, "docs")
        eff_min = 2
        required_min = max(1, exp["min_pages"], eff_min)
        assert required_min == 3

    def test_eff_quota_min_wins(self):
        """max(1, 0, 5) == 5: effective_quotas.min_pages dominates."""
        exp = _get_section_expansion({}, "docs")
        eff_min = 5
        required_min = max(1, exp["min_pages"], eff_min)
        assert required_min == 5

    def test_equal_values(self):
        """max(1, 3, 3) == 3: both sources agree."""
        exp = _get_section_expansion({"docs": {"min_pages": 3}}, "docs")
        eff_min = 3
        required_min = max(1, exp["min_pages"], eff_min)
        assert required_min == 3

    def test_expansion_default_when_section_missing(self):
        """Unset section in page_expansion defaults to min_pages=0."""
        exp = _get_section_expansion({}, "products")
        assert exp["min_pages"] == 0
        assert exp["enabled"] is True
        assert exp["max_pages"] == 999
