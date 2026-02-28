"""Tests for G17-FQ-9: Limitations dump-shape detection (TC-2893).

Validates that the FQ-9 prelint correctly detects dump-shaped Limitations
sections: too many bullets, overly long bullets, and dump shape indicators
(file paths, JSON blobs, code patterns, raw claim fields).
"""

from __future__ import annotations

import pytest

from launch.workers.w9_validator.gates.gate_17_prelints import (
    lint_fq9_limitations_dump_shape,
    run_deterministic_prelints,
    FQ9_MAX_BULLETS,
    FQ9_MAX_LINE_LEN,
)


class TestFQ9LimitationsDumpShape:
    """G17-FQ-9: Limitations dump-shape detection (TC-2893)."""

    def test_clean_limitations_no_issues(self, tmp_path):
        """Clean section with 3 curated bullets produces no FQ-9."""
        md = tmp_path / "clean.md"
        md.write_text(
            "# Page Title\n\n"
            "## Limitations\n\n"
            "- Maximum file size is limited to 500 MB.\n"
            "- Concurrent thread access is not supported.\n"
            "- Performance degrades with files over 10000 elements.\n\n"
            "## Next Section\n",
            encoding="utf-8",
        )
        issues = lint_fq9_limitations_dump_shape(md.read_text(encoding="utf-8"), md)
        assert len(issues) == 0

    def test_too_many_bullets(self, tmp_path):
        """Bullets exceeding FQ9_MAX_BULLETS triggers FQ-9 warn."""
        bullets = "\n".join(
            f"- Limitation number {i} is a real problem." for i in range(15)
        )
        md = tmp_path / "many.md"
        md.write_text(
            f"# Title\n\n## Limitations\n\n{bullets}\n\n## Next\n",
            encoding="utf-8",
        )
        issues = lint_fq9_limitations_dump_shape(md.read_text(encoding="utf-8"), md)
        count_issues = [i for i in issues if "bullets" in i["message"]]
        assert len(count_issues) == 1
        assert count_issues[0]["severity"] == "warn"
        assert count_issues[0]["error_code"] == "G17-FQ-9"

    def test_exactly_at_threshold_no_issue(self, tmp_path):
        """Exactly FQ9_MAX_BULLETS bullets should NOT trigger count issue."""
        bullets = "\n".join(
            f"- Limitation number {i} is documented here." for i in range(FQ9_MAX_BULLETS)
        )
        md = tmp_path / "exact.md"
        md.write_text(
            f"# Title\n\n## Limitations\n\n{bullets}\n\n## Next\n",
            encoding="utf-8",
        )
        issues = lint_fq9_limitations_dump_shape(md.read_text(encoding="utf-8"), md)
        count_issues = [i for i in issues if "bullets" in i["message"]]
        assert len(count_issues) == 0

    def test_overly_long_bullet(self, tmp_path):
        """Bullet exceeding FQ9_MAX_LINE_LEN triggers FQ-9 warn."""
        long_bullet = "- " + "A" * 300 + "."
        md = tmp_path / "long.md"
        md.write_text(
            f"# Title\n\n## Limitations\n\n{long_bullet}\n\n## Next\n",
            encoding="utf-8",
        )
        issues = lint_fq9_limitations_dump_shape(md.read_text(encoding="utf-8"), md)
        len_issues = [i for i in issues if "too long" in i["message"]]
        assert len(len_issues) == 1
        assert len_issues[0]["severity"] == "warn"

    def test_dump_shape_file_path(self, tmp_path):
        """Bullet with Unix file path triggers FQ-9 warn."""
        md = tmp_path / "path.md"
        md.write_text(
            "# Title\n\n## Limitations\n\n"
            "- Found in /usr/lib/python3/site-packages/aspose/module.py during analysis.\n\n"
            "## Next\n",
            encoding="utf-8",
        )
        issues = lint_fq9_limitations_dump_shape(md.read_text(encoding="utf-8"), md)
        dump_issues = [i for i in issues if "dump-shape" in i["message"]]
        assert len(dump_issues) >= 1

    def test_dump_shape_claim_text(self, tmp_path):
        """Bullet with claim_text: literal triggers FQ-9 warn."""
        md = tmp_path / "claim.md"
        md.write_text(
            "# Title\n\n## Limitations\n\n"
            "- claim_text: The library does not support feature X.\n\n"
            "## Next\n",
            encoding="utf-8",
        )
        issues = lint_fq9_limitations_dump_shape(md.read_text(encoding="utf-8"), md)
        dump_issues = [i for i in issues if "dump-shape" in i["message"]]
        assert len(dump_issues) >= 1

    def test_dump_shape_json_blob(self, tmp_path):
        """Bullet starting with JSON triggers FQ-9 warn."""
        md = tmp_path / "json.md"
        md.write_text(
            "# Title\n\n## Limitations\n\n"
            '- {"claim_id": "abc", "text": "some limitation"}\n\n'
            "## Next\n",
            encoding="utf-8",
        )
        issues = lint_fq9_limitations_dump_shape(md.read_text(encoding="utf-8"), md)
        dump_issues = [i for i in issues if "dump-shape" in i["message"]]
        assert len(dump_issues) >= 1

    def test_dump_shape_code_import(self, tmp_path):
        """Bullet with import statement triggers FQ-9 warn."""
        md = tmp_path / "code.md"
        md.write_text(
            "# Title\n\n## Limitations\n\n"
            "- import aspose.threed as a3d is required for all operations.\n\n"
            "## Next\n",
            encoding="utf-8",
        )
        issues = lint_fq9_limitations_dump_shape(md.read_text(encoding="utf-8"), md)
        dump_issues = [i for i in issues if "dump-shape" in i["message"]]
        assert len(dump_issues) >= 1

    def test_dump_shape_evidence_score(self, tmp_path):
        """Bullet with evidence_score keyword triggers FQ-9 warn."""
        md = tmp_path / "score.md"
        md.write_text(
            "# Title\n\n## Limitations\n\n"
            "- evidence_score 0.45 — low confidence limitation.\n\n"
            "## Next\n",
            encoding="utf-8",
        )
        issues = lint_fq9_limitations_dump_shape(md.read_text(encoding="utf-8"), md)
        dump_issues = [i for i in issues if "dump-shape" in i["message"]]
        assert len(dump_issues) >= 1

    def test_no_limitations_section(self, tmp_path):
        """No ## Limitations section produces no FQ-9."""
        md = tmp_path / "nolim.md"
        md.write_text(
            "# Title\n\n## Features\n\n- Nice feature.\n\n",
            encoding="utf-8",
        )
        issues = lint_fq9_limitations_dump_shape(md.read_text(encoding="utf-8"), md)
        assert len(issues) == 0

    def test_known_limitations_heading(self, tmp_path):
        """## Known Limitations heading is also detected."""
        bullets = "\n".join(
            f"- Problem {i} is serious." for i in range(15)
        )
        md = tmp_path / "known.md"
        md.write_text(
            f"# Title\n\n## Known Limitations\n\n{bullets}\n\n## Next\n",
            encoding="utf-8",
        )
        issues = lint_fq9_limitations_dump_shape(md.read_text(encoding="utf-8"), md)
        assert any("bullets" in i["message"] for i in issues)

    def test_fence_aware_no_false_positive(self, tmp_path):
        """Code inside a fence within Limitations should NOT trigger FQ-9."""
        md = tmp_path / "fence.md"
        md.write_text(
            "# Title\n\n## Limitations\n\n"
            "- Export is not supported.\n\n"
            "```python\nimport aspose\ndef workaround():\n    pass\n```\n\n"
            "## Next\n",
            encoding="utf-8",
        )
        issues = lint_fq9_limitations_dump_shape(md.read_text(encoding="utf-8"), md)
        assert len(issues) == 0

    def test_severity_is_warn(self, tmp_path):
        """All FQ-9 issues should be warn, not error."""
        bullets = "\n".join(
            f"- Limitation {i} is a real problem." for i in range(15)
        )
        md = tmp_path / "sev.md"
        md.write_text(
            f"# Title\n\n## Limitations\n\n{bullets}\n\n",
            encoding="utf-8",
        )
        issues = lint_fq9_limitations_dump_shape(md.read_text(encoding="utf-8"), md)
        for issue in issues:
            assert issue["severity"] == "warn"
            assert issue["error_code"] == "G17-FQ-9"

    def test_integration_via_run_deterministic_prelints(self, tmp_path):
        """FQ-9 is included in run_deterministic_prelints and does not set has_errors."""
        bullets = "\n".join(
            f"- Limitation {i} is real." for i in range(15)
        )
        md = tmp_path / "int.md"
        md.write_text(
            f"# Title\n\n## Limitations\n\n{bullets}\n\n",
            encoding="utf-8",
        )
        issues, has_errors = run_deterministic_prelints(md)
        fq9 = [i for i in issues if i["error_code"] == "G17-FQ-9"]
        assert len(fq9) >= 1
        # FQ-9 is warn, NOT in _ERROR_CODES, so has_errors should be False
        assert has_errors is False

    def test_section_ends_at_next_heading(self, tmp_path):
        """Bullets after next ## heading are NOT scanned."""
        md = tmp_path / "scope.md"
        md.write_text(
            "# Title\n\n## Limitations\n\n"
            "- One limitation.\n\n"
            "## Other Section\n\n"
            + "\n".join(f"- Item {i} in other section." for i in range(20))
            + "\n",
            encoding="utf-8",
        )
        issues = lint_fq9_limitations_dump_shape(md.read_text(encoding="utf-8"), md)
        # Only 1 bullet in Limitations — no count issue
        count_issues = [i for i in issues if "bullets" in i["message"]]
        assert len(count_issues) == 0
