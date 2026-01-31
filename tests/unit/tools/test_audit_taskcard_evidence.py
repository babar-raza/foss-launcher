"""
Unit tests for audit_taskcard_evidence.py

Tests audit script functionality with various evidence scenarios.
"""

import pytest
from pathlib import Path
from tools.audit_taskcard_evidence import (
    extract_frontmatter,
    read_taskcard_metadata,
    find_taskcards,
    find_evidence_directories,
    verify_evidence,
    find_orphaned_evidence,
    generate_report,
    audit_taskcards,
)


class TestFrontmatterExtraction:
    """Test YAML frontmatter extraction."""

    def test_valid_frontmatter(self):
        """Extract valid YAML frontmatter."""
        content = """---
id: TC-100
status: Done
owner: TEST_AGENT
---

# Content here
"""
        result = extract_frontmatter(content)
        assert result is not None
        assert result["id"] == "TC-100"
        assert result["status"] == "Done"
        assert result["owner"] == "TEST_AGENT"

    def test_missing_frontmatter_marker(self):
        """Return None when frontmatter markers missing."""
        content = "# Content without frontmatter"
        result = extract_frontmatter(content)
        assert result is None

    def test_malformed_yaml(self):
        """Handle malformed YAML gracefully."""
        content = """---
id: TC-100
status: [invalid yaml: {
---

Content
"""
        # Should return None or handle gracefully
        result = extract_frontmatter(content)
        # Depending on YAML parser, may return None or raise
        # Our function catches exceptions
        assert result is None or isinstance(result, dict)

    def test_empty_frontmatter(self):
        """Handle empty frontmatter."""
        content = """---
---

Content
"""
        result = extract_frontmatter(content)
        # Should handle empty YAML
        assert result is None or result == {} or result is None


class TestTaskcardReading:
    """Test taskcard metadata reading."""

    def test_read_valid_taskcard(self, tmp_path):
        """Read valid taskcard with frontmatter."""
        tc_file = tmp_path / "TC-100_test.md"
        tc_file.write_text("""---
id: TC-100
title: "Test Taskcard"
status: Done
owner: TEST_AGENT
evidence_required:
  - reports/agents/<agent>/TC-100/report.md
---

# Content
""")

        metadata = read_taskcard_metadata(tc_file)
        assert metadata is not None
        assert metadata["id"] == "TC-100"
        assert metadata["_filename"] == "TC-100_test.md"
        assert metadata["_path"] == str(tc_file)

    def test_read_nonexistent_file(self, tmp_path):
        """Handle nonexistent file gracefully."""
        nonexistent = tmp_path / "missing.md"
        metadata = read_taskcard_metadata(nonexistent)
        assert metadata is None

    def test_read_invalid_frontmatter(self, tmp_path):
        """Handle invalid frontmatter gracefully."""
        tc_file = tmp_path / "TC-200_test.md"
        tc_file.write_text("# No frontmatter here")

        metadata = read_taskcard_metadata(tc_file)
        assert metadata is None


class TestTaskcardFinding:
    """Test taskcard discovery."""

    def test_find_taskcards(self, tmp_path):
        """Find all taskcard files in plans/taskcards/."""
        taskcards_dir = tmp_path / "plans" / "taskcards"
        taskcards_dir.mkdir(parents=True)

        # Create test taskcard files
        (taskcards_dir / "TC-100_test1.md").write_text("---\nid: TC-100\n---\n")
        (taskcards_dir / "TC-200_test2.md").write_text("---\nid: TC-200\n---\n")
        (taskcards_dir / "INDEX.md").write_text("# Index (not a taskcard)")

        found = find_taskcards(tmp_path)
        assert len(found) == 2
        assert any("TC-100" in p.name for p in found)
        assert any("TC-200" in p.name for p in found)
        assert not any("INDEX" in p.name for p in found)

    def test_find_taskcards_empty_directory(self, tmp_path):
        """Handle missing taskcards directory."""
        found = find_taskcards(tmp_path)
        assert found == []


class TestEvidenceDirectoryFinding:
    """Test evidence directory discovery."""

    def test_find_evidence_directories(self, tmp_path):
        """Find all evidence directories."""
        agents_dir = tmp_path / "reports" / "agents"
        agents_dir.mkdir(parents=True)

        # Create test evidence directories
        (agents_dir / "AGENT_A" / "TC-100").mkdir(parents=True)
        (agents_dir / "AGENT_A" / "TC-200").mkdir(parents=True)
        (agents_dir / "AGENT_B" / "TC-300").mkdir(parents=True)
        (agents_dir / "AGENT_B" / "other_dir").mkdir(parents=True)

        found = find_evidence_directories(tmp_path)

        # Should find 3 TC-* directories, not other_dir
        assert len(found) == 3
        assert "AGENT_A/TC-100" in found
        assert "AGENT_A/TC-200" in found
        assert "AGENT_B/TC-300" in found
        assert "AGENT_B/other_dir" not in found

    def test_find_evidence_directories_missing_agents(self, tmp_path):
        """Handle missing agents directory."""
        found = find_evidence_directories(tmp_path)
        assert found == {}


class TestEvidenceVerification:
    """Test evidence completeness verification."""

    def test_complete_evidence(self, tmp_path):
        """Taskcard with complete evidence passes."""
        # Create evidence directory with required files
        evidence_dir = tmp_path / "reports" / "agents" / "TEST_AGENT" / "TC-100"
        evidence_dir.mkdir(parents=True)
        (evidence_dir / "report.md").write_text("# Report")
        (evidence_dir / "self_review.md").write_text("# Self Review")

        taskcard = {
            "id": "TC-100",
            "owner": "TEST_AGENT",
            "evidence_required": [
                "reports/agents/<agent>/TC-100/report.md",
                "reports/agents/<agent>/TC-100/self_review.md",
            ],
        }

        is_complete, missing, path = verify_evidence(taskcard, tmp_path)
        assert is_complete is True
        assert missing == []
        assert "TC-100" in path

    def test_missing_report_file(self, tmp_path):
        """Taskcard with missing report.md fails."""
        evidence_dir = tmp_path / "reports" / "agents" / "TEST_AGENT" / "TC-200"
        evidence_dir.mkdir(parents=True)
        # Note: NOT creating report.md
        (evidence_dir / "self_review.md").write_text("# Self Review")

        taskcard = {
            "id": "TC-200",
            "owner": "TEST_AGENT",
            "evidence_required": [],
        }

        is_complete, missing, path = verify_evidence(taskcard, tmp_path)
        assert is_complete is False
        assert "report.md" in missing

    def test_missing_self_review_file(self, tmp_path):
        """Taskcard with missing self_review.md fails."""
        evidence_dir = tmp_path / "reports" / "agents" / "TEST_AGENT" / "TC-300"
        evidence_dir.mkdir(parents=True)
        (evidence_dir / "report.md").write_text("# Report")
        # Note: NOT creating self_review.md

        taskcard = {
            "id": "TC-300",
            "owner": "TEST_AGENT",
            "evidence_required": [],
        }

        is_complete, missing, path = verify_evidence(taskcard, tmp_path)
        assert is_complete is False
        assert "self_review.md" in missing

    def test_missing_evidence_directory(self, tmp_path):
        """Taskcard with no evidence directory fails."""
        taskcard = {
            "id": "TC-400",
            "owner": "TEST_AGENT",
            "evidence_required": [],
        }

        is_complete, missing, path = verify_evidence(taskcard, tmp_path)
        assert is_complete is False
        assert any("not found" in m for m in missing)


class TestOrphanedEvidenceDetection:
    """Test orphaned evidence directory detection."""

    def test_find_orphaned_evidence(self, tmp_path):
        """Find evidence directories with no matching taskcard."""
        # Create orphaned evidence directory
        orphan_dir = tmp_path / "reports" / "agents" / "TEST_AGENT" / "TC-999"
        orphan_dir.mkdir(parents=True)
        (orphan_dir / "report.md").write_text("# Orphaned")

        # Known taskcard IDs
        taskcard_ids = {"TC-100", "TC-200"}

        orphaned = find_orphaned_evidence(tmp_path, taskcard_ids)
        assert len(orphaned) == 1
        assert orphaned[0]["taskcard_id"] == "TC-999"
        assert "TC-999" in orphaned[0]["evidence_dir"]

    def test_no_orphaned_evidence(self, tmp_path):
        """No orphaned evidence when all directories have taskcards."""
        # Create evidence directory
        evidence_dir = tmp_path / "reports" / "agents" / "TEST_AGENT" / "TC-100"
        evidence_dir.mkdir(parents=True)

        # Known taskcard IDs
        taskcard_ids = {"TC-100", "TC-200"}

        orphaned = find_orphaned_evidence(tmp_path, taskcard_ids)
        assert len(orphaned) == 0


class TestReportGeneration:
    """Test audit report generation."""

    def test_generate_complete_report(self):
        """Generate report with mixed results."""
        done_taskcards = [
            {"id": "TC-100"},
            {"id": "TC-200"},
        ]

        evidence_results = [
            {
                "taskcard_id": "TC-100",
                "title": "First Task",
                "owner": "AGENT_A",
                "is_complete": True,
                "missing_items": [],
                "evidence_path": "/path/TC-100",
            },
            {
                "taskcard_id": "TC-200",
                "title": "Second Task",
                "owner": "AGENT_B",
                "is_complete": False,
                "missing_items": ["report.md"],
                "evidence_path": "/path/TC-200",
            },
        ]

        orphaned_evidence = [
            {
                "evidence_dir": "AGENT_C/TC-999",
                "taskcard_id": "TC-999",
                "full_path": "/path/TC-999",
            }
        ]

        report = generate_report(done_taskcards, evidence_results, orphaned_evidence)

        assert "Taskcard Evidence Audit Report" in report
        assert "TC-100" in report
        assert "TC-200" in report
        assert "Complete" in report
        assert "Incomplete" in report
        assert "report.md" in report
        assert "Orphaned Evidence" in report
        assert "TC-999" in report

    def test_generate_all_complete_report(self):
        """Generate report when all evidence is complete."""
        done_taskcards = [{"id": "TC-100"}]

        evidence_results = [
            {
                "taskcard_id": "TC-100",
                "title": "Task",
                "owner": "AGENT_A",
                "is_complete": True,
                "missing_items": [],
                "evidence_path": "/path/TC-100",
            }
        ]

        report = generate_report(done_taskcards, evidence_results, [])

        assert "100.0%" in report or "100%" in report
        assert "Incomplete Evidence" not in report
        assert "Orphaned Evidence" not in report


class TestFullAudit:
    """Test complete audit workflow."""

    def test_audit_with_complete_evidence(self, tmp_path):
        """Full audit with all evidence complete."""
        # Create taskcard
        taskcards_dir = tmp_path / "plans" / "taskcards"
        taskcards_dir.mkdir(parents=True)
        (taskcards_dir / "TC-100_test.md").write_text("""---
id: TC-100
title: Test Task
status: Done
owner: TEST_AGENT
evidence_required: []
---
Content
""")

        # Create evidence
        evidence_dir = tmp_path / "reports" / "agents" / "TEST_AGENT" / "TC-100"
        evidence_dir.mkdir(parents=True)
        (evidence_dir / "report.md").write_text("# Report")
        (evidence_dir / "self_review.md").write_text("# Review")

        # Run audit
        exit_code, done, results, orphaned = audit_taskcards(tmp_path)

        assert exit_code == 0
        assert len(done) == 1
        assert len(results) == 1
        assert results[0]["is_complete"] is True
        assert len(orphaned) == 0

    def test_audit_with_missing_evidence(self, tmp_path):
        """Full audit detects missing evidence."""
        # Create taskcard
        taskcards_dir = tmp_path / "plans" / "taskcards"
        taskcards_dir.mkdir(parents=True)
        (taskcards_dir / "TC-200_test.md").write_text("""---
id: TC-200
title: Test Task
status: Done
owner: TEST_AGENT
evidence_required: []
---
Content
""")

        # Create incomplete evidence (missing report.md)
        evidence_dir = tmp_path / "reports" / "agents" / "TEST_AGENT" / "TC-200"
        evidence_dir.mkdir(parents=True)
        (evidence_dir / "self_review.md").write_text("# Review")

        # Run audit
        exit_code, done, results, orphaned = audit_taskcards(tmp_path)

        assert exit_code == 1  # Should fail
        assert len(done) == 1
        assert len(results) == 1
        assert results[0]["is_complete"] is False
        assert "report.md" in results[0]["missing_items"]

    def test_audit_with_orphaned_evidence(self, tmp_path):
        """Full audit detects orphaned evidence."""
        # Create taskcard
        taskcards_dir = tmp_path / "plans" / "taskcards"
        taskcards_dir.mkdir(parents=True)
        (taskcards_dir / "TC-100_test.md").write_text("""---
id: TC-100
title: Test Task
status: Draft
owner: TEST_AGENT
evidence_required: []
---
Content
""")

        # Create orphaned evidence (no matching taskcard)
        orphan_dir = tmp_path / "reports" / "agents" / "TEST_AGENT" / "TC-999"
        orphan_dir.mkdir(parents=True)
        (orphan_dir / "report.md").write_text("# Orphaned")

        # Run audit
        exit_code, done, results, orphaned = audit_taskcards(tmp_path)

        # TC-100 is Draft, not Done, so no Done taskcards
        assert len(done) == 0
        assert len(orphaned) == 1
        assert orphaned[0]["taskcard_id"] == "TC-999"
        assert exit_code == 1  # Should fail due to orphaned evidence

    def test_audit_specific_taskcard(self, tmp_path):
        """Audit specific taskcard with --taskcard filter."""
        # Create two taskcards
        taskcards_dir = tmp_path / "plans" / "taskcards"
        taskcards_dir.mkdir(parents=True)
        (taskcards_dir / "TC-100_test.md").write_text("""---
id: TC-100
status: Done
owner: AGENT_A
evidence_required: []
---
""")
        (taskcards_dir / "TC-200_test.md").write_text("""---
id: TC-200
status: Done
owner: AGENT_B
evidence_required: []
---
""")

        # Run audit for TC-100 only
        exit_code, done, results, orphaned = audit_taskcards(
            tmp_path, filter_taskcard="TC-100"
        )

        assert len(done) == 1
        assert done[0]["id"] == "TC-100"
        assert len(results) == 1
        assert results[0]["taskcard_id"] == "TC-100"

    def test_audit_no_taskcards(self, tmp_path):
        """Handle missing taskcards directory."""
        exit_code, done, results, orphaned = audit_taskcards(tmp_path)

        assert exit_code == 2  # Error code
        assert len(done) == 0
        assert len(results) == 0
