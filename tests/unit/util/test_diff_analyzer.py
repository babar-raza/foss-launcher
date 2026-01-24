"""Tests for diff analyzer (Guarantee G)."""

import pytest
from launch.util.diff_analyzer import (
    detect_formatting_only_changes,
    count_diff_lines,
    analyze_file_change,
    analyze_patch_bundle,
    ChangeBudgetExceededError,
    normalize_whitespace,
)


class TestNormalizeWhitespace:
    """Test whitespace normalization."""

    def test_normalize_trailing_whitespace(self):
        """Test that trailing whitespace is removed."""
        original = "line1  \nline2\t\nline3   "
        normalized = normalize_whitespace(original)
        assert normalized == "line1\nline2\nline3"

    def test_normalize_line_endings(self):
        """Test that line endings are normalized."""
        original = "line1\r\nline2\rline3\n"
        normalized = normalize_whitespace(original)
        assert "\r" not in normalized


class TestFormattingDetection:
    """Test formatting-only change detection."""

    def test_detect_whitespace_only_change(self):
        """Test that whitespace-only changes are detected."""
        original = "def foo():\n    return 42"
        modified = "def foo():\n        return 42"  # Different indentation

        assert detect_formatting_only_changes(original, modified) is True

    def test_detect_line_ending_change(self):
        """Test that line ending changes are detected as formatting."""
        original = "line1\nline2\nline3"
        modified = "line1\r\nline2\r\nline3"

        assert detect_formatting_only_changes(original, modified) is True

    def test_detect_semantic_change(self):
        """Test that semantic changes are not formatting-only."""
        original = "def foo():\n    return 42"
        modified = "def foo():\n    return 43"  # Changed value

        assert detect_formatting_only_changes(original, modified) is False

    def test_detect_mixed_changes(self):
        """Test that mixed formatting + logic changes are not formatting-only."""
        original = "def foo():\n    return 42"
        modified = "def foo():\n        return 43"  # Indentation + value

        assert detect_formatting_only_changes(original, modified) is False


class TestLineCounting:
    """Test line counting."""

    def test_count_additions(self):
        """Test counting added lines."""
        original = "line1\nline2"
        modified = "line1\nline2\nline3\nline4"

        added, deleted = count_diff_lines(original, modified)

        assert added == 2
        assert deleted == 0

    def test_count_deletions(self):
        """Test counting deleted lines."""
        original = "line1\nline2\nline3"
        modified = "line1"

        added, deleted = count_diff_lines(original, modified)

        assert added == 0
        assert deleted == 2

    def test_count_modifications(self):
        """Test counting modified lines (counted as add + delete)."""
        original = "line1\nline2\nline3"
        modified = "line1\nmodified\nline3"

        added, deleted = count_diff_lines(original, modified)

        assert added == 1
        assert deleted == 1


class TestFileChangeAnalysis:
    """Test single file change analysis."""

    def test_analyze_under_budget(self):
        """Test file change within budget."""
        budgets = {"max_lines_per_file": 100}
        original = "line1\nline2"
        modified = "line1\nline2\nline3"

        lines_changed, is_formatting, violations = analyze_file_change(
            "test.txt", original, modified, budgets
        )

        assert lines_changed == 1
        assert is_formatting is False
        assert len(violations) == 0

    def test_analyze_exceeds_budget(self):
        """Test file change exceeding budget."""
        budgets = {"max_lines_per_file": 2}
        original = "line1"
        modified = "line1\nline2\nline3\nline4"

        lines_changed, is_formatting, violations = analyze_file_change(
            "test.txt", original, modified, budgets
        )

        assert lines_changed == 3
        assert len(violations) == 1
        assert "test.txt" in violations[0]


class TestPatchBundleAnalysis:
    """Test patch bundle analysis."""

    def test_analyze_empty_patch(self):
        """Test analyzing empty patch bundle."""
        patch_bundle = {"files": []}
        budgets = {
            "max_lines_per_file": 500,
            "max_files_changed": 100,
        }

        result = analyze_patch_bundle(patch_bundle, budgets)

        assert result.ok is True
        assert result.total_files_changed == 0
        assert len(result.budget_violations) == 0

    def test_analyze_within_budget(self):
        """Test analyzing patch within budget."""
        patch_bundle = {
            "files": [
                {
                    "path": "file1.txt",
                    "original": "line1",
                    "modified": "line1\nline2",
                },
                {
                    "path": "file2.txt",
                    "original": "content",
                    "modified": "new content",
                },
            ]
        }
        budgets = {
            "max_lines_per_file": 500,
            "max_files_changed": 100,
        }

        result = analyze_patch_bundle(patch_bundle, budgets)

        assert result.ok is True
        assert result.total_files_changed == 2

    def test_analyze_exceeds_file_count(self):
        """Test analyzing patch that exceeds file count budget."""
        files = [
            {"path": f"file{i}.txt", "original": "old", "modified": "new"}
            for i in range(10)
        ]
        patch_bundle = {"files": files}
        budgets = {
            "max_lines_per_file": 500,
            "max_files_changed": 5,  # Only allow 5 files
        }

        with pytest.raises(ChangeBudgetExceededError) as exc_info:
            analyze_patch_bundle(patch_bundle, budgets)

        assert exc_info.value.error_code == "POLICY_CHANGE_BUDGET_EXCEEDED"
        assert "10" in str(exc_info.value)  # Should mention 10 files

    def test_analyze_exceeds_lines_per_file(self):
        """Test analyzing patch that exceeds lines-per-file budget."""
        # Create a file with many line changes
        original = "\n".join([f"line{i}" for i in range(10)])
        modified = "\n".join([f"modified{i}" for i in range(10)])

        patch_bundle = {
            "files": [
                {"path": "large.txt", "original": original, "modified": modified}
            ]
        }
        budgets = {
            "max_lines_per_file": 5,  # Only allow 5 lines changed
            "max_files_changed": 100,
        }

        with pytest.raises(ChangeBudgetExceededError) as exc_info:
            analyze_patch_bundle(patch_bundle, budgets)

        assert exc_info.value.error_code == "POLICY_CHANGE_BUDGET_EXCEEDED"
