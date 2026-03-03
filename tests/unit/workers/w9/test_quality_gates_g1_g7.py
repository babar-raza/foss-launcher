"""TC-3670: Tests for Quality Content Gates G1-G7.

Covers all 7 quality content gates:
  G1: gate_llm_artifact_phrases — LLM boilerplate detection
  G2: gate_intra_page_repetition — Jaccard intra-page duplicate paragraphs
  G3: gate_api_import_allowlist — canonical import enforcement
  G4: gate_section_structure — heading structure contracts
  G5: gate_product_name_integrity — extended brand name corruption
  G6: gate_permalink_uniqueness — permalink collision detection
  G7: gate_spec_leakage — spec/internal terms on user pages

Each gate has >=2 tests (one triggering, one passing).
All gates use always-error severity (no profile demotion for local).
"""

from __future__ import annotations

import json
import pytest
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_md(run_dir: Path, rel_path: str, content: str) -> Path:
    """Write a markdown file under run_dir/work/site/."""
    md_file = run_dir / "work" / "site" / rel_path
    md_file.parent.mkdir(parents=True, exist_ok=True)
    md_file.write_text(content, encoding="utf-8")
    return md_file


def _write_artifact(run_dir: Path, filename: str, data: dict) -> Path:
    """Write a JSON artifact under run_dir/artifacts/."""
    art_dir = run_dir / "artifacts"
    art_dir.mkdir(parents=True, exist_ok=True)
    path = art_dir / filename
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


# ===========================================================================
# G1: LLM Artifact Phrases
# ===========================================================================

from src.launch.workers.w9_validator.gates.gate_llm_artifact_phrases import (
    execute_gate as g1_execute,
)


class TestG1CleanContent:
    """G1: Clean content passes the gate."""

    def test_normal_prose_passes(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_md(run_dir, "page.md", (
            "---\ntitle: Test\n---\n"
            "## Overview\n\n"
            "Aspose.Cells FOSS for Python provides spreadsheet manipulation.\n\n"
            "## See Also\n\n"
            "- [Docs](https://docs.aspose.org/cells/python/)\n"
        ))
        passed, issues = g1_execute(run_dir, "local")
        assert passed is True
        assert len(issues) == 0

    def test_no_site_dir_passes(self, tmp_path):
        run_dir = tmp_path / "run"
        run_dir.mkdir()
        passed, issues = g1_execute(run_dir, "ci")
        assert passed is True


class TestG1ArtifactDetection:
    """G1: LLM artifacts are detected."""

    def test_when_working_with_detected(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_md(run_dir, "page.md", (
            "## Overview\n\n"
            "When working with Aspose.Cells, you can create spreadsheets.\n"
        ))
        passed, issues = g1_execute(run_dir, "ci")
        assert passed is False
        assert any(i["error_code"] == "G1_PREAMBLE_WHEN_WORKING" for i in issues)

    def test_in_this_article_detected(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_md(run_dir, "page.md", (
            "In this article, we will explore how to use the library.\n"
        ))
        passed, issues = g1_execute(run_dir, "ci")
        assert passed is False
        assert any(i["error_code"] == "G1_PREAMBLE_IN_THIS" for i in issues)

    def test_this_guide_covers_detected(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_md(run_dir, "page.md", (
            "This guide covers the basics of cell formatting.\n"
        ))
        passed, issues = g1_execute(run_dir, "ci")
        assert passed is False
        assert any(i["error_code"] == "G1_PREAMBLE_THIS_ARTICLE" for i in issues)

    def test_worth_noting_detected(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_md(run_dir, "page.md", (
            "It's worth noting that this library is open source.\n"
        ))
        passed, issues = g1_execute(run_dir, "ci")
        assert passed is False
        assert any(i["error_code"] == "G1_FILLER_WORTH_NOTING" for i in issues)

    def test_should_be_noted_detected(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_md(run_dir, "page.md", (
            "It should be noted that the API is experimental.\n"
        ))
        passed, issues = g1_execute(run_dir, "ci")
        assert passed is False

    def test_in_conclusion_detected(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_md(run_dir, "page.md", "In conclusion, the library is useful.\n")
        passed, issues = g1_execute(run_dir, "ci")
        assert passed is False
        assert any(i["error_code"] == "G1_FILLER_IN_CONCLUSION" for i in issues)

    def test_important_to_note_detected(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_md(run_dir, "page.md", (
            "It's important to note that version 2.0 is required.\n"
        ))
        passed, issues = g1_execute(run_dir, "ci")
        assert passed is False
        assert any(i["error_code"] == "G1_FILLER_IMPORTANT_TO_NOTE" for i in issues)

    def test_skips_code_fences(self, tmp_path):
        """Artifacts inside code fences are not flagged."""
        run_dir = tmp_path / "run"
        _write_md(run_dir, "page.md", (
            "## Example\n\n"
            "```python\n"
            "# When working with large files\n"
            "print('hello')\n"
            "```\n"
        ))
        passed, issues = g1_execute(run_dir, "ci")
        assert passed is True
        assert len(issues) == 0

    def test_always_error_severity(self, tmp_path):
        """G1 uses always-error severity (no local profile demotion)."""
        run_dir = tmp_path / "run"
        _write_md(run_dir, "page.md", (
            "When working with this library, you can do many things.\n"
        ))
        passed, issues = g1_execute(run_dir, "local")
        assert passed is False
        assert issues[0]["severity"] == "error"

    def test_max_issues_capped(self, tmp_path):
        """G1 caps issues at 20 per file."""
        run_dir = tmp_path / "run"
        lines = [f"When working with item {i}, you should check it." for i in range(30)]
        _write_md(run_dir, "page.md", "\n".join(lines))
        passed, issues = g1_execute(run_dir, "ci")
        assert passed is False
        assert len(issues) == 20

    def test_issue_has_required_fields(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_md(run_dir, "page.md", "When working with this library.\n")
        passed, issues = g1_execute(run_dir, "ci")
        assert len(issues) >= 1
        issue = issues[0]
        for key in ("issue_id", "gate", "severity", "message", "error_code", "location", "status"):
            assert key in issue, f"Missing key: {key}"
        assert issue["gate"] == "gate_llm_artifact_phrases"


# ===========================================================================
# G2: Intra-Page Repetition
# ===========================================================================

from src.launch.workers.w9_validator.gates.gate_intra_page_repetition import (
    execute_gate as g2_execute,
    _jaccard_similarity,
    _tokenize,
)


class TestG2JaccardHelper:

    def test_identical_sets(self):
        a = {"hello", "world", "test"}
        assert _jaccard_similarity(a, a) == 1.0

    def test_disjoint_sets(self):
        a = {"hello", "world"}
        b = {"foo", "bar"}
        assert _jaccard_similarity(a, b) == 0.0

    def test_empty_set(self):
        assert _jaccard_similarity(set(), {"a"}) == 0.0

    def test_partial_overlap(self):
        a = {"hello", "world", "test"}
        b = {"hello", "world", "other"}
        sim = _jaccard_similarity(a, b)
        assert 0.4 < sim < 0.6  # 2/4 = 0.5


class TestG2CleanContent:

    def test_diverse_paragraphs_pass(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_md(run_dir, "page.md", (
            "---\ntitle: Test\n---\n"
            "## Overview\n\n"
            "Aspose.Cells FOSS provides spreadsheet manipulation capabilities "
            "for Python developers who need to work with Excel files.\n\n"
            "## Installation\n\n"
            "Install the package using pip. The library requires Python 3.8 or "
            "newer and has minimal external dependencies for easy setup.\n\n"
        ))
        passed, issues = g2_execute(run_dir, "ci")
        assert passed is True

    def test_no_site_dir_passes(self, tmp_path):
        run_dir = tmp_path / "run"
        run_dir.mkdir()
        passed, issues = g2_execute(run_dir, "ci")
        assert passed is True


class TestG2RepetitionDetection:

    def test_identical_paragraphs_detected(self, tmp_path):
        run_dir = tmp_path / "run"
        para = (
            "Aspose.Cells FOSS for Python provides a comprehensive spreadsheet "
            "manipulation library that enables developers to create read and modify "
            "Excel files programmatically with full support for all major formats."
        )
        _write_md(run_dir, "page.md", (
            "## Section One\n\n"
            f"{para}\n\n"
            "## Section Two\n\n"
            f"{para}\n\n"
        ))
        passed, issues = g2_execute(run_dir, "ci")
        assert passed is False
        assert any(i["error_code"] == "G2_INTRA_PAGE_REPEAT" for i in issues)

    def test_near_duplicate_detected(self, tmp_path):
        run_dir = tmp_path / "run"
        para1 = (
            "The library provides comprehensive spreadsheet manipulation capabilities "
            "for Python developers who need to create read and modify Excel files "
            "programmatically with support for all major spreadsheet formats."
        )
        para2 = (
            "This library provides comprehensive spreadsheet manipulation capabilities "
            "for Python programmers who need to create read and modify Excel documents "
            "programmatically with support for all major spreadsheet formats."
        )
        _write_md(run_dir, "page.md", f"## A\n\n{para1}\n\n## B\n\n{para2}\n\n")
        passed, issues = g2_execute(run_dir, "ci")
        assert passed is False

    def test_short_paragraphs_skipped(self, tmp_path):
        """Paragraphs under 15 words are not checked."""
        run_dir = tmp_path / "run"
        _write_md(run_dir, "page.md", (
            "## A\n\nShort para one.\n\n## B\n\nShort para one.\n\n"
        ))
        passed, issues = g2_execute(run_dir, "ci")
        assert passed is True  # Too short to flag

    def test_code_fences_excluded(self, tmp_path):
        """Repeated content in code fences is not flagged."""
        run_dir = tmp_path / "run"
        code = "from aspose.cells import Workbook\nwb = Workbook()\nwb.save('out.xlsx')"
        _write_md(run_dir, "page.md", (
            f"## A\n\n```python\n{code}\n```\n\n"
            f"## B\n\n```python\n{code}\n```\n\n"
        ))
        passed, issues = g2_execute(run_dir, "ci")
        assert passed is True

    def test_always_error_severity(self, tmp_path):
        run_dir = tmp_path / "run"
        para = (
            "Aspose.Cells FOSS for Python provides a comprehensive spreadsheet "
            "manipulation library that enables developers to create and modify files."
        )
        _write_md(run_dir, "page.md", f"## A\n\n{para}\n\n## B\n\n{para}\n\n")
        passed, issues = g2_execute(run_dir, "local")
        assert passed is False
        assert issues[0]["severity"] == "error"


# ===========================================================================
# G3: API Import Allowlist
# ===========================================================================

from src.launch.workers.w9_validator.gates.gate_api_import_allowlist import (
    execute_gate as g3_execute,
)


class TestG3CleanImports:

    def test_canonical_import_passes(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_artifact(run_dir, "product_facts.json", {
            "product_family": "cells",
            "product_name": "Aspose.Cells FOSS for Python",
        })
        _write_md(run_dir, "page.md", (
            "## Example\n\n"
            "```python\n"
            "from aspose.cells import Workbook\n"
            "wb = Workbook()\n"
            "```\n"
        ))
        passed, issues = g3_execute(run_dir, "ci")
        assert passed is True

    def test_stdlib_import_passes(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_md(run_dir, "page.md", (
            "```python\n"
            "import os\n"
            "import json\n"
            "from pathlib import Path\n"
            "```\n"
        ))
        passed, issues = g3_execute(run_dir, "ci")
        assert passed is True

    def test_no_site_dir_passes(self, tmp_path):
        run_dir = tmp_path / "run"
        run_dir.mkdir()
        passed, issues = g3_execute(run_dir, "ci")
        assert passed is True


class TestG3HallucinatedImports:

    def test_asposecells_detected(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_artifact(run_dir, "product_facts.json", {
            "product_family": "cells",
        })
        _write_md(run_dir, "page.md", (
            "```python\n"
            "import asposecells as cells\n"
            "```\n"
        ))
        passed, issues = g3_execute(run_dir, "ci")
        assert passed is False
        assert any(i["error_code"] == "G3_IMPORT_NOT_ALLOWLISTED" for i in issues)

    def test_aspire_cells_detected(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_artifact(run_dir, "product_facts.json", {
            "product_family": "cells",
        })
        _write_md(run_dir, "page.md", (
            "```python\n"
            "from aspire.cells import Workbook\n"
            "```\n"
        ))
        passed, issues = g3_execute(run_dir, "ci")
        assert passed is False

    def test_only_flags_inside_fences(self, tmp_path):
        """Imports in prose (not in code fences) are not flagged."""
        run_dir = tmp_path / "run"
        _write_md(run_dir, "page.md", (
            "You can import asposecells to get started.\n"
        ))
        passed, issues = g3_execute(run_dir, "ci")
        assert passed is True

    def test_always_error_severity(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_artifact(run_dir, "product_facts.json", {
            "product_family": "cells",
        })
        _write_md(run_dir, "page.md", "```python\nimport asposecells\n```\n")
        passed, issues = g3_execute(run_dir, "local")
        assert passed is False
        assert issues[0]["severity"] == "error"


# ===========================================================================
# G4: Section Structure
# ===========================================================================

from src.launch.workers.w9_validator.gates.gate_section_structure import (
    execute_gate as g4_execute,
)


class TestG4CleanStructure:

    def test_well_structured_page_passes(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_md(run_dir, "page.md", (
            "---\ntitle: Test\n---\n"
            "## Overview\n\nContent here.\n\n"
            "## Installation\n\nMore content.\n\n"
            "## See Also\n\n- [Link](https://example.com)\n"
        ))
        passed, issues = g4_execute(run_dir, "ci")
        assert passed is True

    def test_no_site_dir_passes(self, tmp_path):
        run_dir = tmp_path / "run"
        run_dir.mkdir()
        passed, issues = g4_execute(run_dir, "ci")
        assert passed is True


class TestG4StructureViolations:

    def test_trailing_period_on_heading_detected(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_md(run_dir, "page.md", (
            "---\ntitle: Test\n---\n"
            "## Quick Start.\n\nContent here.\n\n"
            "## See Also.\n\n- [Link](https://example.com)\n"
        ))
        passed, issues = g4_execute(run_dir, "ci")
        assert passed is False
        assert any(i["error_code"] == "G4_HEADING_TRAILING_PUNCT" for i in issues)

    def test_duplicate_h2_detected(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_md(run_dir, "page.md", (
            "## Overview\n\nFirst section.\n\n"
            "## Details\n\nMiddle section.\n\n"
            "## Overview\n\nDuplicate section.\n\n"
        ))
        passed, issues = g4_execute(run_dir, "ci")
        assert passed is False
        assert any(i["error_code"] == "G4_DUPLICATE_H2" for i in issues)

    def test_see_also_not_last_detected(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_md(run_dir, "page.md", (
            "## Overview\n\nContent.\n\n"
            "## See Also\n\n- [Link](https://example.com)\n\n"
            "## Extra Section\n\nThis should not be after See Also.\n"
        ))
        passed, issues = g4_execute(run_dir, "ci")
        assert passed is False
        assert any(i["error_code"] == "G4_SEE_ALSO_NOT_LAST" for i in issues)

    def test_headings_in_code_fences_skipped(self, tmp_path):
        """Headings inside code fences don't count."""
        run_dir = tmp_path / "run"
        _write_md(run_dir, "page.md", (
            "## Overview\n\n"
            "```markdown\n"
            "## Overview\n"
            "```\n\n"
            "## See Also\n\n- [Link](https://example.com)\n"
        ))
        passed, issues = g4_execute(run_dir, "ci")
        assert passed is True

    def test_always_error_severity(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_md(run_dir, "page.md", "## Quick Start.\n\nContent.\n")
        passed, issues = g4_execute(run_dir, "local")
        assert passed is False
        assert issues[0]["severity"] == "error"


# ===========================================================================
# G5: Product Name Integrity (extended)
# ===========================================================================

from src.launch.workers.w9_validator.gates.gate_product_name_integrity import (
    execute_gate as g5_execute,
)


class TestG5OriginalBehavior:

    def test_correct_name_passes(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_md(run_dir, "page.md", "Aspose.Cells FOSS for Python is great.\n")
        passed, issues = g5_execute(run_dir, "ci")
        assert passed is True

    def test_space_corruption_detected(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_md(run_dir, "page.md", "Aspose. Cells is a library.\n")
        passed, issues = g5_execute(run_dir, "ci")
        assert passed is False
        assert any(i["error_code"] == "G5_SPACE_CORRUPTED" for i in issues)


class TestG5ExtendedPatterns:

    def test_aspire_cells_detected(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_md(run_dir, "page.md", "Aspire.Cells is a library.\n")
        passed, issues = g5_execute(run_dir, "ci")
        assert passed is False
        assert any(i["error_code"] == "G5_BRAND_MISSPELLED" for i in issues)

    def test_aspuse_note_detected(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_md(run_dir, "page.md", "Use Aspuse.Note for OneNote files.\n")
        passed, issues = g5_execute(run_dir, "ci")
        assert passed is False
        assert any(i["error_code"] == "G5_BRAND_MISSPELLED" for i in issues)

    def test_doubled_platform_detected(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_md(run_dir, "page.md", "Aspose.Cells FOSS for Python for Python.\n")
        passed, issues = g5_execute(run_dir, "ci")
        assert passed is False
        assert any(i["error_code"] == "G5_DOUBLED_PLATFORM" for i in issues)

    def test_code_fences_skipped(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_md(run_dir, "page.md", (
            "## Example\n\n"
            "```python\n"
            "# Aspire.Cells example\n"
            "```\n"
        ))
        passed, issues = g5_execute(run_dir, "ci")
        assert passed is True

    def test_misspell_severity_always_error(self, tmp_path):
        """G5 extended patterns use always-error severity."""
        run_dir = tmp_path / "run"
        _write_md(run_dir, "page.md", "Aspire.Cells library.\n")
        passed, issues = g5_execute(run_dir, "local")
        assert passed is False
        g5_issues = [i for i in issues if i["error_code"] == "G5_BRAND_MISSPELLED"]
        assert len(g5_issues) >= 1
        assert g5_issues[0]["severity"] == "error"


# ===========================================================================
# G6: Permalink Uniqueness
# ===========================================================================

from src.launch.workers.w9_validator.gates.gate_permalink_uniqueness import (
    execute_gate as g6_execute,
)


class TestG6UniquePermalinks:

    def test_unique_permalinks_pass(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_md(run_dir, "page1.md", (
            "---\ntitle: Page 1\npermalink: /cells/python/overview/\n---\n"
            "Content 1.\n"
        ))
        _write_md(run_dir, "page2.md", (
            "---\ntitle: Page 2\npermalink: /cells/python/install/\n---\n"
            "Content 2.\n"
        ))
        passed, issues = g6_execute(run_dir, "ci")
        assert passed is True

    def test_no_site_dir_passes(self, tmp_path):
        run_dir = tmp_path / "run"
        run_dir.mkdir()
        passed, issues = g6_execute(run_dir, "ci")
        assert passed is True


class TestG6CollisionDetection:

    def test_duplicate_permalink_detected(self, tmp_path):
        """Same-section same permalink is a collision."""
        run_dir = tmp_path / "run"
        _write_md(run_dir, "content/docs.aspose.org/index.md", (
            "---\ntitle: Docs Index\npermalink: /cells/python/\n---\nDocs.\n"
        ))
        _write_md(run_dir, "content/docs.aspose.org/other.md", (
            "---\ntitle: Docs Other\npermalink: /cells/python/\n---\nOther.\n"
        ))
        passed, issues = g6_execute(run_dir, "ci")
        assert passed is False
        assert any(i["error_code"] == "G6_PERMALINK_COLLISION" for i in issues)

    def test_doubled_segment_detected(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_md(run_dir, "page.md", (
            "---\ntitle: Test\npermalink: /note/python/python/overview/\n---\n"
            "Content.\n"
        ))
        passed, issues = g6_execute(run_dir, "ci")
        assert passed is False
        assert any(i["error_code"] == "G6_DOUBLED_SEGMENT" for i in issues)

    def test_case_insensitive_collision(self, tmp_path):
        """Permalink comparison is case-insensitive."""
        run_dir = tmp_path / "run"
        _write_md(run_dir, "page1.md", (
            "---\ntitle: P1\npermalink: /Cells/Python/\n---\nA.\n"
        ))
        _write_md(run_dir, "page2.md", (
            "---\ntitle: P2\npermalink: /cells/python/\n---\nB.\n"
        ))
        passed, issues = g6_execute(run_dir, "ci")
        assert passed is False

    def test_no_permalink_file_ignored(self, tmp_path):
        """Files without permalink in frontmatter are ignored."""
        run_dir = tmp_path / "run"
        _write_md(run_dir, "page1.md", (
            "---\ntitle: No Permalink\n---\nContent.\n"
        ))
        _write_md(run_dir, "page2.md", (
            "---\ntitle: Has Permalink\npermalink: /cells/python/\n---\nContent.\n"
        ))
        passed, issues = g6_execute(run_dir, "ci")
        assert passed is True

    def test_always_error_severity(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_md(run_dir, "page.md", (
            "---\ntitle: T\npermalink: /note/python/python/x/\n---\n"
        ))
        passed, issues = g6_execute(run_dir, "local")
        assert passed is False
        assert issues[0]["severity"] == "error"


# ===========================================================================
# G7: Spec Leakage
# ===========================================================================

from src.launch.workers.w9_validator.gates.gate_spec_leakage import (
    execute_gate as g7_execute,
)


class TestG7CleanContent:

    def test_user_facing_clean_passes(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_artifact(run_dir, "page_plan.json", {"pages": [
            {"output_path": "content/page.md", "page_role": "tutorial"},
        ]})
        _write_md(run_dir, "content/page.md", (
            "---\ntitle: Getting Started\nmachine_readable:\n  page_role: tutorial\n---\n"
            "## Installation\n\n"
            "Install the package using pip.\n\n"
            "## See Also\n\n- [Docs](https://docs.aspose.org)\n"
        ))
        passed, issues = g7_execute(run_dir, "ci")
        assert passed is True

    def test_reference_page_allowed(self, tmp_path):
        """Reference pages can mention spec internals."""
        run_dir = tmp_path / "run"
        _write_md(run_dir, "page.md", (
            "---\ntitle: API Reference\nmachine_readable:\n  page_role: reference_object_page\n---\n"
            "## Overview\n\n"
            "The JCID field identifies object types in the OneNote format.\n"
            "CompactID resolution follows the specification precisely.\n"
        ))
        passed, issues = g7_execute(run_dir, "ci")
        assert passed is True

    def test_no_site_dir_passes(self, tmp_path):
        run_dir = tmp_path / "run"
        run_dir.mkdir()
        passed, issues = g7_execute(run_dir, "ci")
        assert passed is True


class TestG7SpecLeakageDetection:

    def test_jcid_on_tutorial_detected(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_md(run_dir, "page.md", (
            "---\ntitle: Tutorial\nmachine_readable:\n  page_role: tutorial\n---\n"
            "## Overview\n\n"
            "The JCID field identifies object types.\n"
        ))
        passed, issues = g7_execute(run_dir, "ci")
        assert passed is False
        assert any(i["error_code"] == "G7_SPEC_LEAKAGE" for i in issues)

    def test_compactid_on_howto_detected(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_md(run_dir, "page.md", (
            "---\ntitle: How-To\nmachine_readable:\n  page_role: howto_article\n---\n"
            "## Steps\n\n"
            "Handle CompactID resolution errors.\n"
        ))
        passed, issues = g7_execute(run_dir, "ci")
        assert passed is False

    def test_hex_constant_detected(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_md(run_dir, "page.md", (
            "---\ntitle: FAQ\nmachine_readable:\n  page_role: faq\n---\n"
            "## Overview\n\n"
            "The object type has value 0x00120034.\n"
        ))
        passed, issues = g7_execute(run_dir, "ci")
        assert passed is False

    def test_transaction_log_detected(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_md(run_dir, "page.md", (
            "---\ntitle: Feature\nmachine_readable:\n  page_role: feature_showcase\n---\n"
            "## Overview\n\n"
            "The transaction log tracks changes.\n"
        ))
        passed, issues = g7_execute(run_dir, "ci")
        assert passed is False

    def test_hashed_chunk_list_detected(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_md(run_dir, "page.md", (
            "---\ntitle: Blog\nmachine_readable:\n  page_role: blog\n---\n"
            "## Overview\n\n"
            "Files contain a hashed chunk list.\n"
        ))
        passed, issues = g7_execute(run_dir, "ci")
        assert passed is False

    def test_spec_section_ref_detected(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_md(run_dir, "page.md", (
            "---\ntitle: Guide\nmachine_readable:\n  page_role: tutorial\n---\n"
            "## Overview\n\n"
            "As described in section 2.2.1.3 of the specification.\n"
        ))
        passed, issues = g7_execute(run_dir, "ci")
        assert passed is False

    def test_patent_email_detected(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_md(run_dir, "page.md", (
            "---\ntitle: Guide\nmachine_readable:\n  page_role: tutorial\n---\n"
            "## Overview\n\n"
            "Contact iplg@microsoft.com for licensing.\n"
        ))
        passed, issues = g7_execute(run_dir, "ci")
        assert passed is False

    def test_code_fences_skipped(self, tmp_path):
        """Spec terms inside code fences are allowed."""
        run_dir = tmp_path / "run"
        _write_md(run_dir, "page.md", (
            "---\ntitle: Tutorial\nmachine_readable:\n  page_role: tutorial\n---\n"
            "## Example\n\n"
            "```python\n"
            "# Read JCID from the file\n"
            "jcid = reader.read_u32()\n"
            "```\n"
        ))
        passed, issues = g7_execute(run_dir, "ci")
        assert passed is True

    def test_always_error_severity(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_md(run_dir, "page.md", (
            "---\ntitle: T\nmachine_readable:\n  page_role: tutorial\n---\n"
            "## Overview\n\nThe JCID field.\n"
        ))
        passed, issues = g7_execute(run_dir, "local")
        assert passed is False
        assert issues[0]["severity"] == "error"

    def test_no_page_role_defaults_to_checking(self, tmp_path):
        """Files without page_role are checked (not skipped)."""
        run_dir = tmp_path / "run"
        _write_md(run_dir, "page.md", (
            "---\ntitle: Unknown\n---\n"
            "## Overview\n\n"
            "The JCID identifies objects.\n"
        ))
        passed, issues = g7_execute(run_dir, "ci")
        assert passed is False


# ===========================================================================
# Determinism: issue ordering stability
# ===========================================================================

class TestDeterministicOrdering:

    def test_g1_issues_sorted_by_file_then_line(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_md(run_dir, "b_page.md", "When working with B.\n")
        _write_md(run_dir, "a_page.md", "When working with A.\n")
        passed, issues = g1_execute(run_dir, "ci")
        assert len(issues) == 2
        # Issues should be sorted by file path (a before b)
        paths = [i["location"]["path"] for i in issues]
        assert "a_page" in paths[0]
        assert "b_page" in paths[1]

    def test_g6_collisions_sorted_by_permalink(self, tmp_path):
        run_dir = tmp_path / "run"
        _write_md(run_dir, "z.md", "---\npermalink: /a/\n---\nZ.\n")
        _write_md(run_dir, "a.md", "---\npermalink: /a/\n---\nA.\n")
        passed, issues = g6_execute(run_dir, "ci")
        collision_issues = [i for i in issues if i["error_code"] == "G6_PERMALINK_COLLISION"]
        assert len(collision_issues) == 1  # One file reports as duplicate
