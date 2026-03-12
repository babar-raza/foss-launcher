"""Tests for page_role validation in check_frontmatter() (P7A-01 G-01)."""

import pytest

from launcher.workers.evaluate.checks.frontmatter import check_frontmatter, _VALID_ROLES
from launcher.shared.page_skeletons import PAGE_ROLE_SKELETONS


def _make_frontmatter(page_role: str = "workflow_page", **extra) -> str:
    """Build minimal frontmatter string with the given page_role."""
    fields = {"title": "Test Page", "page_role": page_role}
    fields.update(extra)
    lines = ["---"] + [f"{k}: {v}" for k, v in fields.items()] + ["---", "", "Content here."]
    return "\n".join(lines)


class TestPageRoleValidation:
    """Tests for page_role validation in the frontmatter checker."""

    def test_valid_role_produces_no_role_finding(self):
        """A known page_role produces no role-related finding."""
        content = _make_frontmatter(page_role="workflow_page")
        findings = check_frontmatter(content, "test-slug")
        role_findings = [
            f for f in findings
            if "Unknown page_role" in f.message or "Missing page_role" in f.message
        ]
        assert not role_findings, f"Unexpected role findings: {role_findings}"

    def test_unknown_role_produces_high_finding(self):
        """An unknown page_role produces a high-severity finding."""
        content = _make_frontmatter(page_role="invented_role_xyz")
        findings = check_frontmatter(content, "test-slug")
        role_findings = [f for f in findings if "Unknown page_role" in f.message]
        assert role_findings, "Expected a finding for unknown page_role"
        assert role_findings[0].severity == "high"

    def test_missing_role_produces_high_finding(self):
        """Missing page_role field produces a high-severity finding."""
        content = "---\ntitle: Test Page\n---\n\nContent here."
        findings = check_frontmatter(content, "test-slug")
        role_findings = [f for f in findings if "Missing page_role" in f.message]
        assert role_findings, "Expected a finding for missing page_role"
        assert role_findings[0].severity == "high"

    def test_valid_roles_equals_page_role_skeletons_keys(self):
        """_VALID_ROLES must equal PAGE_ROLE_SKELETONS.keys() (no drift)."""
        assert _VALID_ROLES == set(PAGE_ROLE_SKELETONS.keys()), (
            "_VALID_ROLES must stay in sync with PAGE_ROLE_SKELETONS.keys()"
        )

    def test_each_known_role_passes_validation(self):
        """Every role in PAGE_ROLE_SKELETONS produces no role-related findings."""
        for role in sorted(PAGE_ROLE_SKELETONS.keys()):
            content = _make_frontmatter(page_role=role)
            findings = check_frontmatter(content, f"{role}-slug")
            role_findings = [
                f for f in findings
                if "Unknown page_role" in f.message or "Missing page_role" in f.message
            ]
            assert not role_findings, (
                f"Role '{role}' triggered unexpected finding: {role_findings}"
            )
