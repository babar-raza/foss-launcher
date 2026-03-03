"""Tests for TC-3624: W10 KB Howto Section Reorder Fixer.

Verifies that fix_kb_howto_structure() correctly reorders out-of-order
sections when all required headings are present but in wrong order.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from launch.workers.w10_fixer.worker import _reorder_kb_howto_sections, fix_kb_howto_structure


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_issue(slug: str, msg: str) -> Dict[str, Any]:
    return {
        "issue_id": f"gate_kb_howto_structure_order_{slug}",
        "error_code": "GATE_KB_HOWTO_STRUCTURE_HEADING_ORDER",
        "message": msg,
        "location": {"path": f"drafts/kb/{slug}.md"},
    }


_CANONICAL_ORDER = """\
---
title: Test
layout: kb
permalink: /kb/test/
---

Preamble text here.

## Goal

Learn how to do this.

## Prerequisites

- Python 3.8+

## Steps

1. First step.

## Code Example

```python
pass
```

## See Also

- [docs](https://docs.aspose.com/)
"""

_OUT_OF_ORDER = """\
---
title: Test
layout: kb
permalink: /kb/test/
---

Preamble text here.

## Goal

Learn how to do this.

## Prerequisites

- Python 3.8+

## Code Example

```python
pass
```

## Steps

1. First step.

## See Also

- [docs](https://docs.aspose.com/)
"""


# ---------------------------------------------------------------------------
# Tests for _reorder_kb_howto_sections helper
# ---------------------------------------------------------------------------

class TestReorderKbHowtoSections:
    """Unit tests for the _reorder_kb_howto_sections helper."""

    def test_reorder_code_example_before_steps(self, tmp_path):
        """File with Code Example before Steps → reordered correctly."""
        f = tmp_path / "test.md"
        f.write_text(_OUT_OF_ORDER, encoding="utf-8")

        changed = _reorder_kb_howto_sections(f)
        assert changed is True

        result = f.read_text(encoding="utf-8")
        # Steps must appear before Code Example
        steps_pos = result.find("## Steps")
        code_pos = result.find("## Code Example")
        assert steps_pos < code_pos, "Steps must come before Code Example"

    def test_reorder_already_correct_is_noop(self, tmp_path):
        """Correctly ordered file → fixed=False (idempotent)."""
        f = tmp_path / "test.md"
        f.write_text(_CANONICAL_ORDER, encoding="utf-8")

        changed = _reorder_kb_howto_sections(f)
        assert changed is False
        # File content must be unchanged
        assert f.read_text(encoding="utf-8") == _CANONICAL_ORDER

    def test_reorder_preserves_preamble(self, tmp_path):
        """Preamble text before first heading is preserved."""
        f = tmp_path / "test.md"
        f.write_text(_OUT_OF_ORDER, encoding="utf-8")

        _reorder_kb_howto_sections(f)
        result = f.read_text(encoding="utf-8")
        assert "Preamble text here." in result

    def test_reorder_preserves_other_sections(self, tmp_path):
        """Non-required sections (e.g. Troubleshooting) appended after required."""
        content = (
            "---\ntitle: Test\n---\n\n"
            "## Code Example\n\ncode\n\n"
            "## Steps\n\nstep\n\n"
            "## Goal\n\ngoal\n\n"
            "## Troubleshooting\n\nextra\n\n"
            "## See Also\n\n- link\n\n"
            "## Prerequisites\n\n- prereq\n\n"
        )
        f = tmp_path / "test.md"
        f.write_text(content, encoding="utf-8")

        _reorder_kb_howto_sections(f)
        result = f.read_text(encoding="utf-8")

        goal_pos = result.find("## Goal")
        prereq_pos = result.find("## Prerequisites")
        steps_pos = result.find("## Steps")
        code_pos = result.find("## Code Example")
        see_pos = result.find("## See Also")
        trouble_pos = result.find("## Troubleshooting")

        assert goal_pos < prereq_pos < steps_pos < code_pos < see_pos
        # Troubleshooting (non-required) must appear after required sections
        assert trouble_pos > see_pos

    def test_nonexistent_file_returns_false(self, tmp_path):
        """Nonexistent file → returns False without error."""
        f = tmp_path / "nonexistent.md"
        changed = _reorder_kb_howto_sections(f)
        assert changed is False


# ---------------------------------------------------------------------------
# Tests for fix_kb_howto_structure routing
# ---------------------------------------------------------------------------

class TestFixKbHowtoStructureReorderRouting:
    """Verify fix_kb_howto_structure routes ordering violations to reorder helper."""

    def test_ordering_violation_triggers_reorder(self, tmp_path):
        """Issue with 'appears before' in message → reorder is called."""
        slug = "how-to-test"
        draft = tmp_path / "drafts" / "kb" / f"{slug}.md"
        draft.parent.mkdir(parents=True)
        draft.write_text(_OUT_OF_ORDER, encoding="utf-8")

        # Create minimal work/site structure
        (tmp_path / "work" / "site").mkdir(parents=True)
        # Create a fake validation_report.json so load_json_artifact doesn't fail
        artifacts = tmp_path / "artifacts"
        artifacts.mkdir()
        (artifacts / "validation_report.json").write_text(
            json.dumps({"gates": [], "issues": []}), encoding="utf-8"
        )
        (artifacts / "shared_facts.json").write_text(
            json.dumps({"package_name": "test-pkg"}), encoding="utf-8"
        )

        issue = _make_issue(
            slug,
            f"Heading 'steps' appears before 'code example' in draft '{slug}' — "
            "expected order: ['goal', 'prerequisites', 'steps', 'code example', 'see also']."
        )

        result = fix_kb_howto_structure(issue, tmp_path, MagicMock())

        assert result["fixed"] is True
        assert any(slug in f for f in result.get("files_changed", []))

        # Verify the draft is now in correct order
        content = draft.read_text(encoding="utf-8")
        steps_pos = content.find("## Steps")
        code_pos = content.find("## Code Example")
        assert steps_pos < code_pos

    def test_missing_heading_uses_injection_not_reorder(self, tmp_path):
        """Issue with 'missing' in message → injection path (not reorder)."""
        slug = "how-to-test2"
        draft = tmp_path / "drafts" / "kb" / f"{slug}.md"
        draft.parent.mkdir(parents=True)
        # File missing the Goal heading
        content = "## Steps\n\nstep\n\n## See Also\n\n- link\n"
        draft.write_text(content, encoding="utf-8")

        (tmp_path / "work" / "site").mkdir(parents=True)
        artifacts = tmp_path / "artifacts"
        artifacts.mkdir()
        (artifacts / "validation_report.json").write_text(
            json.dumps({"gates": [], "issues": []}), encoding="utf-8"
        )
        (artifacts / "shared_facts.json").write_text(
            json.dumps({"package_name": "test-pkg"}), encoding="utf-8"
        )

        issue = {
            "issue_id": f"gate_kb_howto_structure_missing_{slug}",
            "error_code": "GATE_KB_HOWTO_STRUCTURE_HEADING_ORDER",
            "message": f"Heading 'goal' missing in draft '{slug}'.",
            "location": {"path": f"drafts/kb/{slug}.md"},
        }

        result = fix_kb_howto_structure(issue, tmp_path, None)
        # Should inject Goal, not fail
        assert result["fixed"] is True
        assert "goal" in draft.read_text(encoding="utf-8").lower()
