"""Unit tests for taskcard_loader.py.

Tests taskcard loading, parsing, and error handling.
"""

import tempfile
from pathlib import Path

import pytest

from launch.util.taskcard_loader import (
    TaskcardNotFoundError,
    TaskcardParseError,
    find_taskcard_file,
    get_allowed_paths,
    get_taskcard_status,
    load_taskcard,
    parse_frontmatter,
)


class TestParseFrontmatter:
    """Test YAML frontmatter parsing."""

    def test_parse_valid_frontmatter(self):
        """Test parsing valid frontmatter."""
        content = """---
id: TC-100
status: Done
allowed_paths:
  - pyproject.toml
  - src/launch/__init__.py
---

# Body content here
"""
        frontmatter, body = parse_frontmatter(content)

        assert frontmatter is not None
        assert frontmatter["id"] == "TC-100"
        assert frontmatter["status"] == "Done"
        assert len(frontmatter["allowed_paths"]) == 2
        assert "# Body content here" in body

    def test_parse_no_frontmatter(self):
        """Test parsing content without frontmatter."""
        content = "# Just a markdown file\n\nNo frontmatter here."
        frontmatter, body = parse_frontmatter(content)

        assert frontmatter is None
        assert body == content

    def test_parse_invalid_yaml(self):
        """Test parsing invalid YAML frontmatter."""
        content = """---
id: TC-100
invalid: [unclosed bracket
---

# Body
"""
        frontmatter, body = parse_frontmatter(content)

        # Invalid YAML returns None
        assert frontmatter is None


class TestFindTaskcardFile:
    """Test taskcard file discovery."""

    def test_find_existing_taskcard(self):
        """Test finding an existing taskcard file."""
        # Use real repo to find TC-100
        repo_root = Path(__file__).parent.parent.parent.parent
        taskcard_file = find_taskcard_file("TC-100", repo_root)

        assert taskcard_file is not None
        assert taskcard_file.exists()
        assert taskcard_file.name.startswith("TC-100_")
        assert taskcard_file.suffix == ".md"

    def test_find_nonexistent_taskcard(self):
        """Test that nonexistent taskcard returns None."""
        repo_root = Path(__file__).parent.parent.parent.parent
        taskcard_file = find_taskcard_file("TC-9999", repo_root)

        assert taskcard_file is None

    def test_find_in_empty_directory(self):
        """Test finding taskcard when taskcards directory doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            taskcard_file = find_taskcard_file("TC-100", repo_root)

            assert taskcard_file is None


class TestLoadTaskcard:
    """Test taskcard loading."""

    def test_load_existing_taskcard(self):
        """Test loading an existing taskcard."""
        repo_root = Path(__file__).parent.parent.parent.parent
        taskcard = load_taskcard("TC-100", repo_root)

        assert taskcard["id"] == "TC-100"
        assert "status" in taskcard
        assert "allowed_paths" in taskcard
        assert isinstance(taskcard["allowed_paths"], list)

    def test_load_multiple_taskcards(self):
        """Test loading multiple different taskcards."""
        repo_root = Path(__file__).parent.parent.parent.parent

        # Load TC-100
        tc100 = load_taskcard("TC-100", repo_root)
        assert tc100["id"] == "TC-100"

        # Load TC-200
        tc200 = load_taskcard("TC-200", repo_root)
        assert tc200["id"] == "TC-200"

        # Taskcards should be different
        assert tc100 != tc200

    def test_load_nonexistent_taskcard_raises_error(self):
        """Test that loading nonexistent taskcard raises TaskcardNotFoundError."""
        repo_root = Path(__file__).parent.parent.parent.parent

        with pytest.raises(TaskcardNotFoundError) as exc_info:
            load_taskcard("TC-9999", repo_root)

        assert exc_info.value.taskcard_id == "TC-9999"
        assert "TC-9999" in str(exc_info.value)

    def test_load_invalid_yaml_raises_error(self):
        """Test that invalid YAML raises TaskcardParseError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            taskcards_dir = repo_root / "plans" / "taskcards"
            taskcards_dir.mkdir(parents=True)

            # Create taskcard with invalid YAML
            invalid_file = taskcards_dir / "TC-999_test.md"
            invalid_file.write_text("# Not a valid taskcard\n\nNo frontmatter.")

            with pytest.raises(TaskcardParseError) as exc_info:
                load_taskcard("TC-999", repo_root)

            assert exc_info.value.taskcard_id == "TC-999"
            assert "No valid YAML frontmatter" in str(exc_info.value)

    def test_load_taskcard_missing_id_field(self):
        """Test that taskcard without id field raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            taskcards_dir = repo_root / "plans" / "taskcards"
            taskcards_dir.mkdir(parents=True)

            # Create taskcard without id field
            invalid_file = taskcards_dir / "TC-999_test.md"
            invalid_file.write_text(
                """---
status: Draft
---

# Body
"""
            )

            with pytest.raises(TaskcardParseError) as exc_info:
                load_taskcard("TC-999", repo_root)

            assert "Missing required field: id" in str(exc_info.value)


class TestGetAllowedPaths:
    """Test extracting allowed_paths from taskcard."""

    def test_get_allowed_paths_from_taskcard(self):
        """Test extracting allowed_paths list."""
        repo_root = Path(__file__).parent.parent.parent.parent
        taskcard = load_taskcard("TC-100", repo_root)

        paths = get_allowed_paths(taskcard)

        assert isinstance(paths, list)
        assert len(paths) > 0
        # TC-100 should allow pyproject.toml
        assert "pyproject.toml" in paths

    def test_get_allowed_paths_empty(self):
        """Test getting allowed_paths when field is missing."""
        taskcard = {"id": "TC-999", "status": "Draft"}

        paths = get_allowed_paths(taskcard)

        assert paths == []

    def test_get_allowed_paths_invalid_type(self):
        """Test getting allowed_paths when field is not a list."""
        taskcard = {"id": "TC-999", "allowed_paths": "not-a-list"}

        paths = get_allowed_paths(taskcard)

        assert paths == []


class TestGetTaskcardStatus:
    """Test extracting taskcard status."""

    def test_get_status_present(self):
        """Test getting status when present."""
        taskcard = {"id": "TC-100", "status": "Done"}

        status = get_taskcard_status(taskcard)

        assert status == "Done"

    def test_get_status_missing(self):
        """Test getting status when missing."""
        taskcard = {"id": "TC-100"}

        status = get_taskcard_status(taskcard)

        assert status is None

    def test_get_status_from_real_taskcard(self):
        """Test getting status from real taskcard."""
        repo_root = Path(__file__).parent.parent.parent.parent
        taskcard = load_taskcard("TC-100", repo_root)

        status = get_taskcard_status(taskcard)

        # TC-100 should have a status (Done or In-Progress)
        assert status is not None
        assert isinstance(status, str)
