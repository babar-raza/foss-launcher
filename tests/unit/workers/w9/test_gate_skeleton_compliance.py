"""Tests for TC-3687: Skeleton compliance gate."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from launch.workers.w9_validator.gates.gate_skeleton_compliance import (
    execute_gate,
    _classify_error_code,
)


def _setup_run(
    tmp_path: Path,
    pages: list,
    md_files: dict,
) -> Path:
    """Create a run directory with page_plan.json and markdown files.

    Args:
        tmp_path: pytest tmp_path fixture.
        pages: List of page dicts for page_plan.json.
        md_files: Dict of {relative_path: content} for markdown files.

    Returns:
        run_dir path.
    """
    run_dir = tmp_path / "run"

    # Write page_plan.json
    artifacts = run_dir / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    plan = {"pages": pages}
    (artifacts / "page_plan.json").write_text(
        json.dumps(plan), encoding="utf-8"
    )

    # Write markdown files
    for rel_path, content in md_files.items():
        md_file = run_dir / "work" / "site" / "content" / rel_path
        md_file.parent.mkdir(parents=True, exist_ok=True)
        md_file.write_text(content, encoding="utf-8")

    return run_dir


# ── Missing required section ────────────────────────────────────────────────


class TestMissingRequiredSection:
    """Detect pages missing required skeleton sections."""

    def test_missing_overview_in_landing(self, tmp_path):
        """Landing page without Overview triggers SKELETON_SECTION_MISSING."""
        pages = [{"slug": "mypage", "page_role": "landing"}]
        # Landing requires: Overview, Key Features, Quick Start, See Also
        content = (
            "---\ntitle: My Page\n---\n\n"
            "## Key Features\n\nSome features.\n\n"
            "## Quick Start\n\nSome code.\n\n"
            "## See Also\n\n- [Link](url)\n"
        )
        run_dir = _setup_run(
            tmp_path, pages, {"docs/mypage.md": content}
        )
        passed, issues = execute_gate(run_dir, "ci")
        assert passed is True  # All warnings, gate still passes
        missing = [i for i in issues if i["error_code"] == "SKELETON_SECTION_MISSING"]
        assert len(missing) == 1
        assert "Overview" in missing[0]["message"]

    def test_all_required_present_no_issues(self, tmp_path):
        """Landing page with all required sections → no issues."""
        pages = [{"slug": "mypage", "page_role": "landing"}]
        content = (
            "---\ntitle: My Page\n---\n\n"
            "## Overview\n\nIntro text.\n\n"
            "## Key Features\n\nSome features.\n\n"
            "## Quick Start\n\nSome code.\n\n"
            "## See Also\n\n- [Link](url)\n"
        )
        run_dir = _setup_run(
            tmp_path, pages, {"docs/mypage.md": content}
        )
        passed, issues = execute_gate(run_dir, "ci")
        assert passed is True
        assert len(issues) == 0

    def test_multiple_missing_sections(self, tmp_path):
        """Comprehensive guide missing multiple required sections."""
        pages = [{"slug": "guide", "page_role": "comprehensive_guide"}]
        # comprehensive_guide requires: Introduction, Core Concepts,
        # Implementation, See Also
        content = (
            "---\ntitle: Guide\n---\n\n"
            "## Introduction\n\nSome intro.\n\n"
            "## See Also\n\n- [Link](url)\n"
        )
        run_dir = _setup_run(
            tmp_path, pages, {"docs/guide.md": content}
        )
        passed, issues = execute_gate(run_dir, "ci")
        missing = [i for i in issues if i["error_code"] == "SKELETON_SECTION_MISSING"]
        # Missing: Core Concepts, Implementation
        assert len(missing) == 2
        messages = " ".join(i["message"] for i in missing)
        assert "Core Concepts" in messages
        assert "Implementation" in messages


# ── See Also position ───────────────────────────────────────────────────────


class TestSeeAlsoPosition:
    """Detect See Also not in last position (overlap with G4, warning only)."""

    def test_see_also_not_last_warns(self, tmp_path):
        """See Also before another H2 → SKELETON_SEE_ALSO_POSITION warning."""
        pages = [{"slug": "mypage", "page_role": "landing"}]
        content = (
            "---\ntitle: My Page\n---\n\n"
            "## Overview\n\nIntro.\n\n"
            "## See Also\n\n- [Link](url)\n\n"
            "## Key Features\n\nFeatures.\n\n"
            "## Quick Start\n\nCode.\n"
        )
        run_dir = _setup_run(
            tmp_path, pages, {"docs/mypage.md": content}
        )
        passed, issues = execute_gate(run_dir, "ci")
        assert passed is True  # Warning severity, gate passes
        position = [i for i in issues if i["error_code"] == "SKELETON_SEE_ALSO_POSITION"]
        assert len(position) == 1


# ── Duplicate H2 ────────────────────────────────────────────────────────────


class TestDuplicateH2:
    """Detect duplicate H2 headings (overlap with G4, warning only)."""

    def test_duplicate_h2_warns(self, tmp_path):
        """Duplicate H2 → SKELETON_DUPLICATE_H2 warning."""
        pages = [{"slug": "mypage", "page_role": "landing"}]
        content = (
            "---\ntitle: My Page\n---\n\n"
            "## Overview\n\nFirst overview.\n\n"
            "## Overview\n\nSecond overview.\n\n"
            "## Key Features\n\nFeatures.\n\n"
            "## Quick Start\n\nCode.\n\n"
            "## See Also\n\n- [Link](url)\n"
        )
        run_dir = _setup_run(
            tmp_path, pages, {"docs/mypage.md": content}
        )
        passed, issues = execute_gate(run_dir, "ci")
        assert passed is True
        dups = [i for i in issues if i["error_code"] == "SKELETON_DUPLICATE_H2"]
        assert len(dups) >= 1


# ── Graceful skip scenarios ─────────────────────────────────────────────────


class TestGracefulSkip:
    """Gate passes gracefully when inputs are unavailable."""

    def test_no_page_plan(self, tmp_path):
        """No page_plan.json → gate passes with no issues."""
        run_dir = tmp_path / "run"
        (run_dir / "work" / "site" / "content").mkdir(parents=True)
        passed, issues = execute_gate(run_dir, "ci")
        assert passed is True
        assert len(issues) == 0

    def test_unknown_role_skipped(self, tmp_path):
        """Page with role not in PAGE_ROLE_SKELETONS → skipped."""
        pages = [{"slug": "custom", "page_role": "unknown_custom_role"}]
        content = "---\ntitle: Custom\n---\n\n## Content\n\nText.\n"
        run_dir = _setup_run(
            tmp_path, pages, {"docs/custom.md": content}
        )
        passed, issues = execute_gate(run_dir, "ci")
        assert passed is True
        assert len(issues) == 0

    def test_no_site_dir(self, tmp_path):
        """No work/site directory → gate passes."""
        run_dir = tmp_path / "run"
        artifacts = run_dir / "artifacts"
        artifacts.mkdir(parents=True)
        plan = {"pages": [{"slug": "x", "page_role": "landing"}]}
        (artifacts / "page_plan.json").write_text(
            json.dumps(plan), encoding="utf-8"
        )
        passed, issues = execute_gate(run_dir, "ci")
        assert passed is True
        assert len(issues) == 0

    def test_page_role_empty_skipped(self, tmp_path):
        """Page with empty page_role → skipped."""
        pages = [{"slug": "nope", "page_role": ""}]
        content = "---\ntitle: Nope\n---\n\n## Content\n\nText.\n"
        run_dir = _setup_run(
            tmp_path, pages, {"docs/nope.md": content}
        )
        passed, issues = execute_gate(run_dir, "ci")
        assert passed is True
        assert len(issues) == 0


# ── _index.md slug resolution ──────────────────────────────────────────────


class TestIndexSlugResolution:
    """Verify _index.md files use parent directory name as slug."""

    def test_index_md_uses_parent_dir_name(self, tmp_path):
        """_index.md in python/ directory matches slug 'python'."""
        pages = [{"slug": "python", "page_role": "toc"}]
        # toc requires: Overview, Pages in This Section
        content = (
            "---\ntitle: Python\n---\n\n"
            "## Overview\n\nPython docs.\n\n"
            "## Pages in This Section\n\n- Page 1\n"
        )
        run_dir = _setup_run(
            tmp_path,
            pages,
            {"docs/python/_index.md": content},
        )
        passed, issues = execute_gate(run_dir, "ci")
        assert passed is True
        assert len(issues) == 0


# ── Error code classification ──────────────────────────────────────────────


class TestClassifyErrorCode:
    """Verify _classify_error_code produces correct codes."""

    def test_missing_section(self):
        assert _classify_error_code("Missing required section: ## Overview") == "SKELETON_SECTION_MISSING"

    def test_see_also_position(self):
        assert _classify_error_code('"See Also" must be the last H2 section') == "SKELETON_SEE_ALSO_POSITION"

    def test_duplicate_h2(self):
        assert _classify_error_code('Duplicate H2 heading: "overview" appears 2 times') == "SKELETON_DUPLICATE_H2"

    def test_unknown_message(self):
        assert _classify_error_code("Something unexpected") == "SKELETON_COMPLIANCE"
