"""Tests for scripts/quality_metrics.py."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Ensure the scripts directory is importable
REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from quality_metrics import (  # noqa: E402
    DirectoryMetrics,
    FileMetrics,
    compare_baselines,
    load_allowlist,
    scan_directory,
    scan_file,
)

FIXTURES = REPO_ROOT / "tests" / "fixtures" / "quality"
DEFECT_FILE = str(FIXTURES / "sample_with_defects.md")
CLEAN_FILE = str(FIXTURES / "sample_clean.md")

# Allowlist containing only Workbook-related identifiers (simulates api_surface.md)
_ALLOWLIST = {
    "Workbook", "Worksheet", "Cell", "Cells",
    "add_worksheet", "get_worksheet", "save",
    "save_csv", "load_csv", "set_cell_value",
}


class TestScanFileWithDefects:
    """Verify all 7 defect types are detected in the sample_with_defects fixture."""

    @pytest.fixture(autouse=True)
    def _scan(self) -> None:
        self.fm = scan_file(
            DEFECT_FILE,
            allowlist=_ALLOWLIST,
            product_name="Aspose.Cells",
        )
        self.by_gate = self.fm.counts_by_gate()

    def test_g1_artifact_phrases(self) -> None:
        """G1: should detect 'let's dive', 'plays a crucial role', etc."""
        assert self.by_gate.get("G1", 0) >= 1, f"Expected G1 defects, got {self.by_gate}"

    def test_g2_near_duplicates(self) -> None:
        """G2: should detect the near-duplicate loading sentences."""
        assert self.by_gate.get("G2", 0) >= 1, f"Expected G2 defects, got {self.by_gate}"

    def test_g3_unknown_identifiers(self) -> None:
        """G3: should flag FakeClass and BogusMethod as unknown."""
        assert self.by_gate.get("G3", 0) >= 1, f"Expected G3 defects, got {self.by_gate}"
        g3_msgs = [d.message for d in self.fm.defects if d.gate == "G3"]
        combined = " ".join(g3_msgs)
        assert "FakeClass" in combined or "BogusMethod" in combined

    def test_g4_structural_issues(self) -> None:
        """G4: should detect duplicate H2 and content after See Also."""
        assert self.by_gate.get("G4", 0) >= 1, f"Expected G4 defects, got {self.by_gate}"

    def test_g5_product_name_misspelling(self) -> None:
        """G5: should detect 'Aspose Cells' (missing dot) and 'aspose.cells' (wrong case)."""
        assert self.by_gate.get("G5", 0) >= 1, f"Expected G5 defects, got {self.by_gate}"

    def test_g7_forbidden_patterns(self) -> None:
        """G7: should detect [Content to be generated], CLM- leak, confidence%, etc."""
        assert self.by_gate.get("G7", 0) >= 1, f"Expected G7 defects, got {self.by_gate}"

    def test_total_positive(self) -> None:
        """Total defect count must be > 0."""
        assert self.fm.total > 0


class TestScanFileClean:
    """Verify the clean fixture produces zero defects."""

    def test_zero_defects(self) -> None:
        fm = scan_file(
            CLEAN_FILE,
            allowlist=_ALLOWLIST,
            product_name="Aspose.Cells",
        )
        assert fm.total == 0, (
            f"Expected 0 defects, got {fm.total}: "
            + "; ".join(f"{d.gate}: {d.message}" for d in fm.defects)
        )


class TestCompareBaselines:
    """Verify delta computation between two report dicts."""

    def test_delta_computation(self) -> None:
        before = {
            "total_defects": 10,
            "by_gate": {"G1": 3, "G2": 2, "G4": 5},
        }
        after = {
            "total_defects": 7,
            "by_gate": {"G1": 1, "G2": 2, "G4": 3, "G7": 1},
        }
        delta = compare_baselines(before, after)
        assert delta["total_defects_before"] == 10
        assert delta["total_defects_after"] == 7
        assert delta["total_defects_delta"] == -3
        assert delta["by_gate"]["G1"]["delta"] == -2
        assert delta["by_gate"]["G2"]["delta"] == 0
        assert delta["by_gate"]["G4"]["delta"] == -2
        assert delta["by_gate"]["G7"]["before"] == 0
        assert delta["by_gate"]["G7"]["after"] == 1
        assert delta["by_gate"]["G7"]["delta"] == 1


class TestAggregeCounts:
    """Verify DirectoryMetrics aggregation math."""

    def test_aggregation(self) -> None:
        dm = scan_directory(
            str(FIXTURES),
            allowlist=_ALLOWLIST,
            product_name="Aspose.Cells",
        )
        assert dm.total_files == 2
        # The defect file should have defects, the clean file should not
        assert dm.files_with_defects >= 1
        # Total defects should equal sum of individual file totals
        assert dm.total_defects == sum(f.total for f in dm.files)
        # by_gate aggregation must be consistent
        agg = dm.counts_by_gate()
        recomputed: dict[str, int] = {}
        for f in dm.files:
            for gate, count in f.counts_by_gate().items():
                recomputed[gate] = recomputed.get(gate, 0) + count
        assert agg == recomputed

    def test_g6_duplicate_slugs(self) -> None:
        """G6 is only flagged when slugs collide — our fixtures have distinct slugs."""
        dm = scan_directory(str(FIXTURES), allowlist=_ALLOWLIST)
        agg = dm.counts_by_gate()
        # Our two fixtures have different slugs, so G6 should be 0
        assert agg.get("G6", 0) == 0


class TestLoadAllowlist:
    """Verify allowlist parsing from api_surface.md format."""

    def test_parse_api_surface(self, tmp_path: Path) -> None:
        surface = tmp_path / "api_surface.md"
        surface.write_text(
            "## Workbook\n"
            "**Methods**:\n"
            "- `save(file_path, save_format) -> None`\n"
            "- `add_worksheet(name) -> Worksheet`\n"
            "**Properties**:\n"
            "- `worksheets: list  [readonly]`\n"
            "\n"
            "## Cell\n"
            "**Methods**:\n"
            "- `set_value(val) -> None`\n",
            encoding="utf-8",
        )
        ids = load_allowlist(str(surface))
        assert "Workbook" in ids
        assert "Cell" in ids
        assert "save" in ids
        assert "add_worksheet" in ids
        assert "set_value" in ids
        assert "worksheets" in ids

    def test_missing_file_returns_empty(self) -> None:
        ids = load_allowlist("/nonexistent/path.md")
        assert ids == set()

    def test_none_returns_empty(self) -> None:
        ids = load_allowlist(None)
        assert ids == set()


class TestFileMetricsDataclass:
    """Verify FileMetrics dataclass properties."""

    def test_to_dict_roundtrip(self) -> None:
        fm = scan_file(DEFECT_FILE, allowlist=_ALLOWLIST, product_name="Aspose.Cells")
        d = fm.to_dict()
        assert d["path"] == DEFECT_FILE
        assert d["total"] == fm.total
        assert isinstance(d["by_gate"], dict)
        assert isinstance(d["defects"], list)
        # JSON-serialisable
        json.dumps(d)
