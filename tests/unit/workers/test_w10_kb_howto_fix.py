"""Unit tests for W10 KB howto structure fix (TC-3214, TC-3260).

Tests the improved fix_kb_howto_structure() with:
- H2/H3 heading level detection
- Canonical package name from shared_facts.json
- Append-at-end fallback
- Idempotency
- TC-3260: Prose false-positive, cascade injection, heading level arithmetic
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import pytest

from launch.workers.w10_fixer.worker import fix_kb_howto_structure


# ── Helpers ────────────────────────────────────────────────────────────────


def _make_issue(
    slug: str = "test-howto",
    heading: str = "Goal",
    error_code: str = "GATE_KB_HOWTO_STRUCTURE_HEADING_ORDER",
) -> Dict[str, Any]:
    return {
        "issue_id": f"gate_kb_howto_structure_heading_{slug}",
        "gate": "gate_kb_howto_structure",
        "severity": "error",
        "error_code": error_code,
        "message": f"Heading '{heading}' missing in required heading order",
        "location": {"path": f"drafts/kb/{slug}.md"},
    }


def _setup_run_dir(
    tmp_path: Path,
    slug: str = "test-howto",
    content: str = "",
    shared_facts: Dict[str, Any] | None = None,
) -> Path:
    """Create minimal run_dir with draft and optional shared_facts."""
    run_dir = tmp_path / "run"
    (run_dir / "drafts" / "kb").mkdir(parents=True)
    (run_dir / "artifacts").mkdir(parents=True)

    draft = run_dir / "drafts" / "kb" / f"{slug}.md"
    draft.write_text(content, encoding="utf-8")

    if shared_facts is not None:
        sf_path = run_dir / "artifacts" / "shared_facts.json"
        sf_path.write_text(json.dumps(shared_facts), encoding="utf-8")

    return run_dir


# ── Tests ──────────────────────────────────────────────────────────────────


class TestH3LevelDetection:
    """TC-3214: Fixer detects H3 headings and injects at H3 level."""

    def test_missing_goal_injected_at_h3_level(self, tmp_path: Path) -> None:
        """Document with H3 headings → Goal injected as ### Goal."""
        content = (
            "---\ntitle: Test\n---\n\n"
            "### Prerequisites\n\n- Python 3.8+\n\n"
            "### Steps\n\n1. Do something\n\n"
            "### Code Example\n\n```python\npass\n```\n\n"
            "### See Also\n\n- [Docs](https://docs.aspose.com/)\n"
        )
        run_dir = _setup_run_dir(tmp_path, content=content)
        issue = _make_issue(heading="Goal")

        result = fix_kb_howto_structure(issue, run_dir, None)

        assert result["fixed"] is True
        fixed_content = (run_dir / "drafts" / "kb" / "test-howto.md").read_text(
            encoding="utf-8"
        )
        assert "### Goal" in fixed_content
        # Ensure it's H3, not H2 (substring check: "## Goal" appears in "### Goal",
        # so check that no standalone "## Goal" line exists)
        import re
        assert not re.search(r"^## Goal\b", fixed_content, re.MULTILINE)

    def test_missing_goal_injected_at_h2_level_by_default(self, tmp_path: Path) -> None:
        """Document with H2 headings → Goal injected as ## Goal."""
        content = (
            "---\ntitle: Test\n---\n\n"
            "## Prerequisites\n\n- Python 3.8+\n\n"
            "## Steps\n\n1. Do something\n\n"
            "## See Also\n\n- [Docs](https://docs.aspose.com/)\n"
        )
        run_dir = _setup_run_dir(tmp_path, content=content)
        issue = _make_issue(heading="Goal")

        result = fix_kb_howto_structure(issue, run_dir, None)

        assert result["fixed"] is True
        fixed_content = (run_dir / "drafts" / "kb" / "test-howto.md").read_text(
            encoding="utf-8"
        )
        assert "## Goal" in fixed_content


class TestCodeExampleInjection:
    """TC-3214: Code Example injected before See Also."""

    def test_missing_code_example_injected_before_see_also(self, tmp_path: Path) -> None:
        content = (
            "---\ntitle: Test\n---\n\n"
            "## Goal\n\nLearn something.\n\n"
            "## Prerequisites\n\n- Python\n\n"
            "## Steps\n\n1. Step one\n\n"
            "## See Also\n\n- [Docs](https://docs.aspose.com/)\n"
        )
        run_dir = _setup_run_dir(tmp_path, content=content)
        issue = _make_issue(heading="Code Example")

        result = fix_kb_howto_structure(issue, run_dir, None)

        assert result["fixed"] is True
        fixed_content = (run_dir / "drafts" / "kb" / "test-howto.md").read_text(
            encoding="utf-8"
        )
        # Code Example should appear before See Also
        ce_pos = fixed_content.index("## Code Example")
        sa_pos = fixed_content.index("## See Also")
        assert ce_pos < sa_pos


class TestPipInstallPlaceholder:
    """TC-3214: No pip install <package> placeholder."""

    def test_with_shared_facts_uses_canonical_package(self, tmp_path: Path) -> None:
        """shared_facts.json has package_name → used in prerequisites."""
        content = (
            "---\ntitle: Test\n---\n\n"
            "## Goal\n\nLearn something.\n\n"
            "## Steps\n\n1. Step\n\n"
            "## See Also\n\n- [Docs](https://docs.aspose.com/)\n"
        )
        run_dir = _setup_run_dir(
            tmp_path,
            content=content,
            shared_facts={"package_name": "aspose-cells-python"},
        )
        issue = _make_issue(heading="Prerequisites")

        result = fix_kb_howto_structure(issue, run_dir, None)

        assert result["fixed"] is True
        fixed_content = (run_dir / "drafts" / "kb" / "test-howto.md").read_text(
            encoding="utf-8"
        )
        assert "pip install aspose-cells-python" in fixed_content
        assert "<package>" not in fixed_content

    def test_without_shared_facts_uses_neutral_text(self, tmp_path: Path) -> None:
        """No shared_facts.json → neutral prerequisite text without pip install."""
        content = (
            "---\ntitle: Test\n---\n\n"
            "## Goal\n\nLearn something.\n\n"
            "## Steps\n\n1. Step\n\n"
            "## See Also\n\n- [Docs](https://docs.aspose.com/)\n"
        )
        run_dir = _setup_run_dir(tmp_path, content=content)
        issue = _make_issue(heading="Prerequisites")

        result = fix_kb_howto_structure(issue, run_dir, None)

        assert result["fixed"] is True
        fixed_content = (run_dir / "drafts" / "kb" / "test-howto.md").read_text(
            encoding="utf-8"
        )
        assert "<package>" not in fixed_content
        assert "pip install" not in fixed_content
        assert "installation instructions" in fixed_content


class TestAppendFallback:
    """TC-3214: Append-at-end when no insertion point found."""

    def test_append_at_end_when_no_see_also(self, tmp_path: Path) -> None:
        """No See Also heading and no inject-before match → append at end."""
        content = (
            "---\ntitle: Test\n---\n\n"
            "Some introductory text.\n"
        )
        run_dir = _setup_run_dir(tmp_path, content=content)
        issue = _make_issue(heading="Goal")

        result = fix_kb_howto_structure(issue, run_dir, None)

        assert result["fixed"] is True
        fixed_content = (run_dir / "drafts" / "kb" / "test-howto.md").read_text(
            encoding="utf-8"
        )
        assert "## Goal" in fixed_content
        # Should be appended after existing content
        assert fixed_content.index("introductory text") < fixed_content.index("## Goal")


class TestIdempotency:
    """TC-3214: Running fix twice produces same output."""

    def test_fix_is_idempotent(self, tmp_path: Path) -> None:
        content = (
            "---\ntitle: Test\n---\n\n"
            "## Prerequisites\n\n- Python\n\n"
            "## Steps\n\n1. Step\n\n"
            "## See Also\n\n- [Docs](https://docs.aspose.com/)\n"
        )
        run_dir = _setup_run_dir(tmp_path, content=content)
        issue = _make_issue(heading="Goal")

        # First fix
        result1 = fix_kb_howto_structure(issue, run_dir, None)
        assert result1["fixed"] is True
        content_after_first = (run_dir / "drafts" / "kb" / "test-howto.md").read_text(
            encoding="utf-8"
        )

        # Second fix — should be no-op
        result2 = fix_kb_howto_structure(issue, run_dir, None)
        assert result2["fixed"] is False
        content_after_second = (run_dir / "drafts" / "kb" / "test-howto.md").read_text(
            encoding="utf-8"
        )

        assert content_after_first == content_after_second


# ── TC-3260 regression tests ─────────────────────────────────────────────


class TestProseFalsePositive:
    """TC-3260: Prose containing heading word does NOT prevent heading injection."""

    def test_goal_in_prose_does_not_prevent_injection(self, tmp_path: Path) -> None:
        """Word 'goal' in body prose must NOT block ## Goal injection."""
        content = (
            "---\ntitle: Test\n---\n\n"
            "## Prerequisites\n\n- Python 3.8+\n\n"
            "The goal of this library is to convert files.\n\n"
            "## Steps\n\n1. Do something\n\n"
            "## Code Example\n\n```python\npass\n```\n\n"
            "## See Also\n\n- [Docs](https://docs.aspose.com/)\n"
        )
        run_dir = _setup_run_dir(tmp_path, content=content)
        issue = _make_issue(heading="Goal")

        result = fix_kb_howto_structure(issue, run_dir, None)

        assert result["fixed"] is True
        fixed_content = (run_dir / "drafts" / "kb" / "test-howto.md").read_text(
            encoding="utf-8"
        )
        assert "## Goal" in fixed_content
        # Goal heading should be before Prerequisites
        goal_pos = fixed_content.index("## Goal")
        prereq_pos = fixed_content.index("## Prerequisites")
        assert goal_pos < prereq_pos

    def test_steps_in_prose_does_not_prevent_injection(self, tmp_path: Path) -> None:
        """Word 'steps' in body prose must NOT block ## Steps injection."""
        content = (
            "---\ntitle: Test\n---\n\n"
            "## Goal\n\nLearn the steps to convert files.\n\n"
            "## Prerequisites\n\n- Python 3.8+\n\n"
            "## Code Example\n\n```python\npass\n```\n\n"
            "## See Also\n\n- [Docs](https://docs.aspose.com/)\n"
        )
        run_dir = _setup_run_dir(tmp_path, content=content)
        issue = _make_issue(heading="Steps")

        result = fix_kb_howto_structure(issue, run_dir, None)

        assert result["fixed"] is True
        fixed_content = (run_dir / "drafts" / "kb" / "test-howto.md").read_text(
            encoding="utf-8"
        )
        import re

        assert re.search(r"^## Steps\b", fixed_content, re.MULTILINE)


class TestCascadeInjection:
    """TC-3260: Goal cascades through heading chain when immediate next is missing."""

    def test_goal_before_steps_when_prereq_missing(self, tmp_path: Path) -> None:
        """Goal -> inject before Prerequisites (missing) -> cascade to Steps."""
        content = (
            "---\ntitle: Test\n---\n\n"
            "## Steps\n\n1. Do something\n\n"
            "## Code Example\n\n```python\npass\n```\n\n"
            "## See Also\n\n- [Docs](https://docs.aspose.com/)\n"
        )
        run_dir = _setup_run_dir(tmp_path, content=content)
        issue = _make_issue(heading="Goal")

        result = fix_kb_howto_structure(issue, run_dir, None)

        assert result["fixed"] is True
        fixed_content = (run_dir / "drafts" / "kb" / "test-howto.md").read_text(
            encoding="utf-8"
        )
        # Goal must appear BEFORE Steps (not after it)
        goal_pos = fixed_content.index("## Goal")
        steps_pos = fixed_content.index("## Steps")
        assert goal_pos < steps_pos

    def test_goal_before_code_example_when_both_missing(
        self, tmp_path: Path
    ) -> None:
        """Goal cascades past missing Prerequisites AND Steps to Code Example."""
        content = (
            "---\ntitle: Test\n---\n\n"
            "## Code Example\n\n```python\npass\n```\n\n"
            "## See Also\n\n- [Docs](https://docs.aspose.com/)\n"
        )
        run_dir = _setup_run_dir(tmp_path, content=content)
        issue = _make_issue(heading="Goal")

        result = fix_kb_howto_structure(issue, run_dir, None)

        assert result["fixed"] is True
        fixed_content = (run_dir / "drafts" / "kb" / "test-howto.md").read_text(
            encoding="utf-8"
        )
        goal_pos = fixed_content.index("## Goal")
        ce_pos = fixed_content.index("## Code Example")
        assert goal_pos < ce_pos


class TestWorkSiteCopy:
    """TC-3260: Both draft and work/site copy are updated."""

    def test_both_draft_and_site_copy_fixed(self, tmp_path: Path) -> None:
        """Injection applies to draft AND work/site file."""
        content = (
            "---\ntitle: Test\n---\n\n"
            "## Prerequisites\n\n- Python\n\n"
            "## Steps\n\n1. Step\n\n"
            "## See Also\n\n- [Docs](https://docs.aspose.com/)\n"
        )
        run_dir = _setup_run_dir(tmp_path, slug="my-howto", content=content)
        # Also create work/site copy
        site_dir = run_dir / "work" / "site" / "content" / "kb"
        site_dir.mkdir(parents=True)
        site_file = site_dir / "my-howto.md"
        site_file.write_text(content, encoding="utf-8")

        issue = _make_issue(slug="my-howto", heading="Goal")

        result = fix_kb_howto_structure(issue, run_dir, None)

        assert result["fixed"] is True
        assert len(result["files_changed"]) >= 2

        draft_content = (run_dir / "drafts" / "kb" / "my-howto.md").read_text(
            encoding="utf-8"
        )
        site_content = site_file.read_text(encoding="utf-8")
        assert "## Goal" in draft_content
        assert "## Goal" in site_content


class TestMixedHeadingLevel:
    """TC-3260: _detect_heading_level picks the truly dominant level."""

    def test_more_h2_than_h3_picks_h2(self, tmp_path: Path) -> None:
        """3 H2 + 2 H3 -> H2 dominant -> inject at ## level."""
        content = (
            "---\ntitle: Test\n---\n\n"
            "## Prerequisites\n\n- Python\n\n"
            "### Sub Detail A\n\nDetail.\n\n"
            "## Steps\n\n1. Step\n\n"
            "### Sub Detail B\n\nDetail.\n\n"
            "## See Also\n\n- [Docs](https://docs.aspose.com/)\n"
        )
        run_dir = _setup_run_dir(tmp_path, content=content)
        issue = _make_issue(heading="Goal")

        result = fix_kb_howto_structure(issue, run_dir, None)

        assert result["fixed"] is True
        fixed_content = (run_dir / "drafts" / "kb" / "test-howto.md").read_text(
            encoding="utf-8"
        )
        import re

        # Should be H2 (not H3) because H2 is dominant (3 > 2)
        assert re.search(r"^## Goal\b", fixed_content, re.MULTILINE)
        assert not re.search(r"^### Goal\b", fixed_content, re.MULTILINE)


# ── TC-3550: H1 Goal → H2/H3 normalization ────────────────────────────────


class TestH1GoalRename:
    """Tests for TC-3550: fix_kb_howto_structure renames H1 Goal headings."""

    def test_h1_goal_renamed_to_h2(self, tmp_path: Path) -> None:
        """A bare '# My Product Goal' line is renamed to '## Goal'."""
        import re as _re

        content = (
            "---\ntitle: Test\n---\n\n"
            "# My Product Goal\n\n"
            "## Prerequisites\n\nSome prereqs.\n\n"
            "## Steps\n\nSteps here.\n"
        )
        run_dir = _setup_run_dir(tmp_path, "test-h1", content)
        issue = _make_issue("test-h1", "Goal")

        result = fix_kb_howto_structure(issue, run_dir, None)

        assert result["fixed"] is True
        fixed = (run_dir / "drafts" / "kb" / "test-h1.md").read_text(encoding="utf-8")
        # H1 Goal must be gone
        assert not _re.search(r"^#\s+.*\bGoal\b", fixed, _re.MULTILINE | _re.IGNORECASE)
        # H2 (or H3) Goal must be present
        assert _re.search(r"^#{2,3}\s+Goal\b", fixed, _re.MULTILINE | _re.IGNORECASE)

    def test_h1_goal_rename_idempotent(self, tmp_path: Path) -> None:
        """Running the fix twice on a file with H1 Goal creates exactly one Goal heading."""
        import re as _re

        content = (
            "---\ntitle: Test\n---\n\n"
            "# Aspose.Cells for Python Goal\n\n"
            "## Prerequisites\n\nPrereqs.\n\n"
            "## Steps\n\nSteps here.\n"
        )
        run_dir = _setup_run_dir(tmp_path, "idempotent-h1", content)
        issue = _make_issue("idempotent-h1", "Goal")

        fix_kb_howto_structure(issue, run_dir, None)
        fix_kb_howto_structure(issue, run_dir, None)

        fixed = (run_dir / "drafts" / "kb" / "idempotent-h1.md").read_text(encoding="utf-8")
        goal_headings = _re.findall(r"^#{1,3}\s+.*\bGoal\b", fixed, _re.MULTILINE | _re.IGNORECASE)
        assert len(goal_headings) == 1, (
            f"Expected exactly 1 Goal heading after two runs, found: {goal_headings}"
        )

    def test_h1_goal_only_fires_for_goal_issue(self, tmp_path: Path) -> None:
        """H1 Goal line is NOT renamed when the issue is for a different heading (e.g. Steps)."""
        import re as _re

        content = (
            "---\ntitle: Test\n---\n\n"
            "# My Product Goal\n\n"
            "## Prerequisites\n\nPrereqs.\n\n"
            "## Code Example\n\n```python\npass\n```\n"
        )
        run_dir = _setup_run_dir(tmp_path, "steps-issue", content)
        # Issue is about 'Steps', not 'Goal' → H1 Goal must NOT be renamed
        issue = _make_issue("steps-issue", "Steps")

        fix_kb_howto_structure(issue, run_dir, None)

        fixed = (run_dir / "drafts" / "kb" / "steps-issue.md").read_text(encoding="utf-8")
        # H1 Goal must still be there (untouched)
        assert _re.search(r"^#\s+My Product Goal", fixed, _re.MULTILINE)

    def test_h1_goal_long_product_name(self, tmp_path: Path) -> None:
        """H1 Goal with a long product name is correctly renamed."""
        import re as _re

        content = (
            "---\ntitle: Test\n---\n\n"
            "# Aspose.Cells for Python via .NET Goal\n\n"
            "## Prerequisites\n\nSome prereqs.\n\n"
            "## Steps\n\nSteps here.\n"
        )
        run_dir = _setup_run_dir(tmp_path, "long-name", content)
        issue = _make_issue("long-name", "Goal")

        result = fix_kb_howto_structure(issue, run_dir, None)

        assert result["fixed"] is True
        fixed = (run_dir / "drafts" / "kb" / "long-name.md").read_text(encoding="utf-8")
        assert not _re.search(r"^#\s+.*\bGoal\b", fixed, _re.MULTILINE | _re.IGNORECASE)
        assert _re.search(r"^#{2,3}\s+Goal\b", fixed, _re.MULTILINE | _re.IGNORECASE)

    def test_h1_goal_applied_to_work_site_copy(self, tmp_path: Path) -> None:
        """The H1→H2 rename is applied to both drafts/ and work/site/ copies."""
        import re as _re

        content = (
            "---\ntitle: Test\n---\n\n"
            "# My Product Goal\n\n"
            "## Prerequisites\n\nPrereqs.\n\n"
            "## Steps\n\nSteps.\n"
        )
        run_dir = _setup_run_dir(tmp_path, "site-copy-h1", content)

        # Also create a work/site copy
        site_kb = run_dir / "work" / "site" / "content" / "en" / "kb" / "site-copy-h1"
        site_kb.mkdir(parents=True)
        site_file = site_kb / "index.md"
        site_file.write_text(content, encoding="utf-8")

        issue = _make_issue("site-copy-h1", "Goal")
        fix_kb_howto_structure(issue, run_dir, None)

        # Draft must be fixed
        draft_fixed = (run_dir / "drafts" / "kb" / "site-copy-h1.md").read_text(encoding="utf-8")
        assert not _re.search(r"^#\s+.*\bGoal\b", draft_fixed, _re.MULTILINE | _re.IGNORECASE)

        # Site copy must be fixed
        site_fixed = site_file.read_text(encoding="utf-8")
        assert not _re.search(r"^#\s+.*\bGoal\b", site_fixed, _re.MULTILINE | _re.IGNORECASE)
