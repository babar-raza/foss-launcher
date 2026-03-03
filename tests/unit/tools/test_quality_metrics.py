"""Unit tests for tools/quality_metrics.py.

Tests cover:
  - Empty run directories (no site content)
  - G1 artifact phrase detection
  - G4 structural violation detection
  - JSON output schema conformance
  - Deterministic ordering (same input -> same output)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Ensure project root is on sys.path so the tool module resolves its imports.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from tools.quality_metrics import compute_metrics, write_json, write_markdown, main  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_site_file(run_dir: Path, rel_path: str, content: str) -> Path:
    """Create a markdown file inside run_dir/work/site/ at rel_path."""
    file_path = run_dir / "work" / "site" / rel_path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")
    return file_path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestMetricsOnEmptyRunDir:
    """test_metrics_on_empty_run_dir: no site dir or no .md files."""

    def test_missing_site_dir(self, tmp_path: Path) -> None:
        """Metrics on a run_dir with no work/site/ produces zero counts."""
        run_dir = tmp_path / "run_empty"
        run_dir.mkdir()

        metrics = compute_metrics(run_dir)

        assert metrics["total_files"] == 0
        for key, gate_data in metrics["metrics"].items():
            assert gate_data["count"] == 0, f"{key} should have 0 issues"
            assert gate_data["files_affected"] == 0
            assert gate_data["file_list"] == []
        assert metrics["summary"]["total_issues"] == 0
        assert metrics["summary"]["total_files_with_issues"] == 0
        assert metrics["summary"]["files_clean"] == 0

    def test_empty_site_dir(self, tmp_path: Path) -> None:
        """Metrics on a run_dir with an empty work/site/ produces zero counts."""
        run_dir = tmp_path / "run_empty_site"
        (run_dir / "work" / "site").mkdir(parents=True)

        metrics = compute_metrics(run_dir)

        assert metrics["total_files"] == 0
        assert metrics["summary"]["total_issues"] == 0

    def test_site_with_no_issues(self, tmp_path: Path) -> None:
        """A clean markdown file produces zero issues and files_clean=1."""
        run_dir = tmp_path / "run_clean"
        _create_site_file(run_dir, "clean.md", "## Hello\n\nThis is clean content.\n")

        metrics = compute_metrics(run_dir)

        assert metrics["total_files"] == 1
        assert metrics["summary"]["total_issues"] == 0
        assert metrics["summary"]["files_clean"] == 1


class TestMetricsDetectsG1Artifacts:
    """test_metrics_detects_g1_artifacts: G1 LLM artifact phrases."""

    def test_preamble_when_working(self, tmp_path: Path) -> None:
        """'When working with...' triggers a G1 artifact hit."""
        run_dir = tmp_path / "run_g1"
        _create_site_file(
            run_dir,
            "feature.md",
            "## Feature\n\nWhen working with Aspose.Cells, you need to install it.\n",
        )

        metrics = compute_metrics(run_dir)

        g1 = metrics["metrics"]["G1_artifact_phrases"]
        assert g1["count"] >= 1
        assert g1["files_affected"] >= 1
        assert len(g1["file_list"]) >= 1

    def test_preamble_in_this_article(self, tmp_path: Path) -> None:
        """'In this article, we will...' triggers a G1 artifact hit."""
        run_dir = tmp_path / "run_g1b"
        _create_site_file(
            run_dir,
            "guide.md",
            "## Guide\n\nIn this article, we will explore the features.\n",
        )

        metrics = compute_metrics(run_dir)
        g1 = metrics["metrics"]["G1_artifact_phrases"]
        assert g1["count"] >= 1

    def test_multiple_artifacts_same_file(self, tmp_path: Path) -> None:
        """Multiple LLM phrases in one file are all counted."""
        run_dir = tmp_path / "run_g1c"
        content = (
            "## Overview\n\n"
            "When working with Aspose.Cells, setup is easy.\n\n"
            "It's worth noting that performance is critical.\n\n"
            "In conclusion, use the library wisely.\n"
        )
        _create_site_file(run_dir, "multi.md", content)

        metrics = compute_metrics(run_dir)
        g1 = metrics["metrics"]["G1_artifact_phrases"]
        assert g1["count"] >= 3, f"Expected >= 3 artifact hits, got {g1['count']}"

    def test_artifact_inside_code_fence_not_counted(self, tmp_path: Path) -> None:
        """Artifact phrases inside code fences are skipped."""
        run_dir = tmp_path / "run_g1_fence"
        content = (
            "## Example\n\n"
            "```python\n"
            "# When working with files\n"
            "print('hello')\n"
            "```\n"
        )
        _create_site_file(run_dir, "fenced.md", content)

        metrics = compute_metrics(run_dir)
        g1 = metrics["metrics"]["G1_artifact_phrases"]
        assert g1["count"] == 0, "Code fence content should not trigger G1"


class TestMetricsDetectsG4Structure:
    """test_metrics_detects_g4_structure: G4 structural violations."""

    def test_duplicate_h2(self, tmp_path: Path) -> None:
        """Duplicate H2 headings trigger G4 issues."""
        run_dir = tmp_path / "run_g4a"
        content = (
            "## Overview\n\n"
            "First section.\n\n"
            "## Overview\n\n"
            "Duplicate section.\n"
        )
        _create_site_file(run_dir, "dup_h2.md", content)

        metrics = compute_metrics(run_dir)
        g4 = metrics["metrics"]["G4_structure_violations"]
        assert g4["count"] >= 1
        assert g4["files_affected"] >= 1

    def test_trailing_punctuation_on_heading(self, tmp_path: Path) -> None:
        """Trailing period on a heading triggers G4."""
        run_dir = tmp_path / "run_g4b"
        content = "## Quick Start.\n\nContent here.\n"
        _create_site_file(run_dir, "punct.md", content)

        metrics = compute_metrics(run_dir)
        g4 = metrics["metrics"]["G4_structure_violations"]
        assert g4["count"] >= 1

    def test_see_also_not_last(self, tmp_path: Path) -> None:
        """'See Also' followed by another H2 triggers G4."""
        run_dir = tmp_path / "run_g4c"
        content = (
            "## Introduction\n\n"
            "Hello.\n\n"
            "## See Also\n\n"
            "- Link 1\n\n"
            "## Appendix\n\n"
            "Extra section.\n"
        )
        _create_site_file(run_dir, "seealso.md", content)

        metrics = compute_metrics(run_dir)
        g4 = metrics["metrics"]["G4_structure_violations"]
        assert g4["count"] >= 1

    def test_clean_structure_no_g4(self, tmp_path: Path) -> None:
        """Well-formed headings produce zero G4 issues."""
        run_dir = tmp_path / "run_g4_clean"
        content = (
            "## Introduction\n\n"
            "Hello.\n\n"
            "## Usage\n\n"
            "Use it.\n\n"
            "## See Also\n\n"
            "- Link\n"
        )
        _create_site_file(run_dir, "clean.md", content)

        metrics = compute_metrics(run_dir)
        g4 = metrics["metrics"]["G4_structure_violations"]
        assert g4["count"] == 0


class TestMetricsJsonOutputSchema:
    """test_metrics_json_output_schema: output matches expected schema."""

    def test_schema_keys_present(self, tmp_path: Path) -> None:
        """JSON output contains all required top-level and nested keys."""
        run_dir = tmp_path / "run_schema"
        _create_site_file(run_dir, "page.md", "## Title\n\nContent.\n")

        metrics = compute_metrics(run_dir)

        # Top-level keys
        assert "run_dir" in metrics
        assert "timestamp" in metrics
        assert "total_files" in metrics
        assert "metrics" in metrics
        assert "summary" in metrics

        # Summary keys
        summary = metrics["summary"]
        assert "total_issues" in summary
        assert "total_files_with_issues" in summary
        assert "files_clean" in summary

        # All 7 gate keys present
        expected_gate_keys = {
            "G1_artifact_phrases",
            "G2_intra_page_repetition",
            "G3_api_import_violations",
            "G4_structure_violations",
            "G5_product_name_errors",
            "G6_permalink_collisions",
            "G7_spec_leakage",
        }
        assert set(metrics["metrics"].keys()) == expected_gate_keys

        # Each gate has required sub-keys
        for key in expected_gate_keys:
            gate_data = metrics["metrics"][key]
            assert "count" in gate_data
            assert "files_affected" in gate_data
            assert "file_list" in gate_data
            assert isinstance(gate_data["count"], int)
            assert isinstance(gate_data["files_affected"], int)
            assert isinstance(gate_data["file_list"], list)

    def test_json_roundtrip(self, tmp_path: Path) -> None:
        """write_json produces valid JSON that can be parsed back identically."""
        run_dir = tmp_path / "run_json"
        _create_site_file(run_dir, "a.md", "## A\n\nClean.\n")

        metrics = compute_metrics(run_dir)
        out_dir = tmp_path / "out_json"
        json_path = write_json(metrics, out_dir)

        assert json_path.exists()
        loaded = json.loads(json_path.read_text(encoding="utf-8"))

        assert loaded["total_files"] == metrics["total_files"]
        assert loaded["summary"] == metrics["summary"]
        assert set(loaded["metrics"].keys()) == set(metrics["metrics"].keys())

    def test_markdown_output_written(self, tmp_path: Path) -> None:
        """write_markdown produces a .md file with expected headers."""
        run_dir = tmp_path / "run_md"
        _create_site_file(run_dir, "b.md", "## B\n\nContent.\n")

        metrics = compute_metrics(run_dir)
        out_dir = tmp_path / "out_md"
        md_path = write_markdown(metrics, out_dir)

        assert md_path.exists()
        text = md_path.read_text(encoding="utf-8")
        assert "# Quality Metrics Report" in text
        assert "## Summary" in text
        assert "## Per-Gate Breakdown" in text
        assert "G1: LLM artifact phrases" in text
        assert "G7: Spec leakage" in text


class TestDeterministicOrdering:
    """test_deterministic_ordering: same input -> same output."""

    def test_same_input_produces_same_output(self, tmp_path: Path) -> None:
        """Two compute_metrics calls on the same input produce identical JSON."""
        run_dir = tmp_path / "run_det"
        _create_site_file(
            run_dir,
            "z_last.md",
            "## Heading.\n\nWhen working with files.\n",
        )
        _create_site_file(
            run_dir,
            "a_first.md",
            "## Heading.\n\nWhen working with data.\n",
        )
        _create_site_file(
            run_dir,
            "m_mid.md",
            "## Title\n\nClean content here.\n",
        )

        metrics_a = compute_metrics(run_dir)
        metrics_b = compute_metrics(run_dir)

        # Remove timestamps for comparison (they will differ by microseconds)
        metrics_a.pop("timestamp")
        metrics_b.pop("timestamp")

        assert metrics_a == metrics_b

    def test_file_list_is_sorted(self, tmp_path: Path) -> None:
        """file_list entries within each gate are lexicographically sorted."""
        run_dir = tmp_path / "run_sorted"
        # Create files in reverse-alpha order
        for name in ["z_page.md", "m_page.md", "a_page.md"]:
            _create_site_file(
                run_dir,
                name,
                "## Heading.\n\nWhen working with something.\n",
            )

        metrics = compute_metrics(run_dir)

        g1 = metrics["metrics"]["G1_artifact_phrases"]
        # All 3 files should trigger G1 (trailing punct on heading fires G4 too)
        assert g1["files_affected"] == 3
        assert g1["file_list"] == sorted(g1["file_list"])

    def test_gate_keys_order_stable(self, tmp_path: Path) -> None:
        """Gate keys in the metrics dict follow the G1-G7 order."""
        run_dir = tmp_path / "run_key_order"
        _create_site_file(run_dir, "page.md", "## Clean\n\nNo issues.\n")

        metrics = compute_metrics(run_dir)
        keys = list(metrics["metrics"].keys())

        expected_order = [
            "G1_artifact_phrases",
            "G2_intra_page_repetition",
            "G3_api_import_violations",
            "G4_structure_violations",
            "G5_product_name_errors",
            "G6_permalink_collisions",
            "G7_spec_leakage",
        ]
        assert keys == expected_order


class TestCLIEntryPoint:
    """CLI argument parsing and exit codes."""

    def test_cli_success(self, tmp_path: Path) -> None:
        """main() returns 0 on a valid run_dir."""
        run_dir = tmp_path / "run_cli"
        _create_site_file(run_dir, "page.md", "## Hello\n\nWorld.\n")
        out_dir = tmp_path / "out_cli"

        exit_code = main(["--run-dir", str(run_dir), "--out-dir", str(out_dir)])

        assert exit_code == 0
        assert (out_dir / "quality_metrics.json").exists()
        assert (out_dir / "quality_metrics.md").exists()

    def test_cli_missing_run_dir(self, tmp_path: Path) -> None:
        """main() returns 1 when run_dir does not exist."""
        out_dir = tmp_path / "out_missing"
        exit_code = main([
            "--run-dir", str(tmp_path / "nonexistent"),
            "--out-dir", str(out_dir),
        ])
        assert exit_code == 1
