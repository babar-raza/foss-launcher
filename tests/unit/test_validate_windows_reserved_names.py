"""Tests for Windows reserved names validation gate (TC-571-1).

Validates that the gate correctly detects Windows reserved device filenames.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path


def test_is_reserved_name():
    """Test the is_reserved_name function logic."""
    # Import the function from the gate script
    import importlib.util

    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "tools" / "validate_windows_reserved_names.py"

    spec = importlib.util.spec_from_file_location("validator", script_path)
    assert spec is not None
    assert spec.loader is not None

    validator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validator)

    is_reserved_name = validator.is_reserved_name

    # Test exact matches (case-insensitive)
    assert is_reserved_name("NUL") is True
    assert is_reserved_name("nul") is True
    assert is_reserved_name("Nul") is True
    assert is_reserved_name("CON") is True
    assert is_reserved_name("con") is True
    assert is_reserved_name("PRN") is True
    assert is_reserved_name("AUX") is True

    # Test COM and LPT variants
    assert is_reserved_name("COM1") is True
    assert is_reserved_name("com9") is True
    assert is_reserved_name("LPT1") is True
    assert is_reserved_name("lpt9") is True

    # Test CLOCK$
    assert is_reserved_name("CLOCK$") is True
    assert is_reserved_name("clock$") is True

    # Test with extensions
    assert is_reserved_name("NUL.txt") is True
    assert is_reserved_name("con.log") is True
    assert is_reserved_name("COM1.dat") is True

    # Test non-reserved names
    assert is_reserved_name("normal.txt") is False
    assert is_reserved_name("README.md") is False
    assert is_reserved_name("config.yaml") is False
    assert is_reserved_name("NUCLEUS") is False  # Contains NUL but isn't reserved
    assert is_reserved_name("CONSOLE") is False  # Contains CON but isn't reserved


def test_self_test_mode():
    """Test that --self-test mode passes."""
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "tools" / "validate_windows_reserved_names.py"

    result = subprocess.run(
        [sys.executable, str(script_path), "--self-test"],
        cwd=str(repo_root),
        capture_output=True,
        text=True
    )

    assert result.returncode == 0, f"Self-test failed: {result.stdout}\n{result.stderr}"
    assert "PASSED" in result.stdout
    assert "21/21 tests passed" in result.stdout


def test_clean_repo_passes():
    """Test that current repository passes validation."""
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "tools" / "validate_windows_reserved_names.py"

    result = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=str(repo_root),
        capture_output=True,
        text=True
    )

    assert result.returncode == 0, f"Gate failed: {result.stdout}\n{result.stderr}"
    assert "PASSED" in result.stdout
    assert "No Windows reserved names found" in result.stdout


def test_reserved_name_detection():
    """Test that reserved names are detected (using is_reserved_name function).

    Note: On Windows, the filesystem prevents creating files with reserved names.
    Even though the operations may appear to succeed, the files are actually
    opened as device handles, not created as regular files. This test verifies
    that the detection logic works by testing it directly, rather than trying
    to work around Windows filesystem behavior.
    """
    # Import the is_reserved_name function
    import importlib.util

    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "tools" / "validate_windows_reserved_names.py"

    spec = importlib.util.spec_from_file_location("validator", script_path)
    assert spec is not None
    assert spec.loader is not None

    validator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validator)

    is_reserved_name = validator.is_reserved_name

    # Test that reserved names are detected
    reserved_test_cases = [
        "NUL", "CON", "PRN", "AUX",
        "COM1", "COM9", "LPT1", "LPT9",
        "CLOCK$",
        "nul.txt", "con.log", "COM1.dat",  # With extensions
    ]

    for name in reserved_test_cases:
        assert is_reserved_name(name) is True, f"{name} should be detected as reserved"

    # Test that non-reserved names are not detected
    non_reserved_test_cases = [
        "README.md", "normal.txt", "config.yaml",
        "NUCLEUS", "CONSOLE", "COMPLEXITY",  # Contain reserved substrings but aren't reserved
    ]

    for name in non_reserved_test_cases:
        assert is_reserved_name(name) is False, f"{name} should not be detected as reserved"


def test_case_insensitive_detection():
    """Test that detection is case-insensitive.

    Note: On Windows, the filesystem prevents creating files with reserved names.
    This test verifies the is_reserved_name logic is case-insensitive using
    the function directly rather than trying to create actual files.
    """
    import importlib.util

    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "tools" / "validate_windows_reserved_names.py"

    spec = importlib.util.spec_from_file_location("validator", script_path)
    assert spec is not None
    assert spec.loader is not None

    validator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validator)

    is_reserved_name = validator.is_reserved_name

    # Test case insensitivity directly via the function
    # This tests the logic without requiring filesystem operations
    case_variations = [
        "NUL", "nul", "Nul", "nUL",
        "CON", "con", "Con", "cOn",
        "PRN", "prn", "Prn",
        "AUX", "aux", "Aux",
        "COM1", "com1", "Com1",
        "LPT9", "lpt9", "Lpt9",
    ]

    for name in case_variations:
        assert is_reserved_name(name) is True, f"{name} should be detected as reserved"


def test_exclusions():
    """Test that excluded directories are skipped."""
    import importlib.util

    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "tools" / "validate_windows_reserved_names.py"

    spec = importlib.util.spec_from_file_location("validator", script_path)
    assert spec is not None
    assert spec.loader is not None

    validator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validator)

    scan_tree = validator.scan_tree

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        # Create violations in excluded directories
        (tmp_path / ".git").mkdir()
        (tmp_path / ".git" / "NUL").touch()

        (tmp_path / ".venv").mkdir()
        (tmp_path / ".venv" / "CON").touch()

        (tmp_path / "node_modules").mkdir()
        (tmp_path / "node_modules" / "AUX").touch()

        (tmp_path / "__pycache__").mkdir()
        (tmp_path / "__pycache__" / "PRN").touch()

        # Create a violation outside excluded dirs
        (tmp_path / "COM1").touch()

        violations = scan_tree(tmp_path)

        # Should only find COM1 (excluded dirs should be ignored)
        assert len(violations) == 1
        assert violations[0].name == "COM1"


def test_deterministic_output():
    """Test that output is deterministic (sorted)."""
    import importlib.util

    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "tools" / "validate_windows_reserved_names.py"

    spec = importlib.util.spec_from_file_location("validator", script_path)
    assert spec is not None
    assert spec.loader is not None

    validator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validator)

    scan_tree = validator.scan_tree

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        # Create violations in non-alphabetical order
        (tmp_path / "subdir3").mkdir()
        (tmp_path / "subdir3" / "NUL").touch()

        (tmp_path / "subdir1").mkdir()
        (tmp_path / "subdir1" / "AUX").touch()

        (tmp_path / "subdir2").mkdir()
        (tmp_path / "subdir2" / "CON").touch()

        violations = scan_tree(tmp_path)

        # Verify violations are sorted
        assert violations == sorted(violations)

        # Run multiple times to verify determinism
        violations2 = scan_tree(tmp_path)
        assert violations == violations2
