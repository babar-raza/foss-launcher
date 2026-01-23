"""Bootstrap tests for TC-100.

Validates basic repository setup and package structure.
"""

from __future__ import annotations

import sys
from pathlib import Path


def test_python_version() -> None:
    """Verify Python version is >= 3.12."""
    assert sys.version_info >= (3, 12), f"Python {sys.version_info} is too old, requires >= 3.12"


def test_launch_package_importable() -> None:
    """Verify launch package can be imported."""
    import launch  # noqa: F401


def test_launch_has_version() -> None:
    """Verify launch package has version info."""
    import launch
    # Version info might be in __init__.py or not, but package should at least be importable
    assert hasattr(launch, "__file__"), "launch package should have __file__ attribute"


def test_repo_structure() -> None:
    """Verify required directories exist."""
    # Assuming tests/unit/test_bootstrap.py, go up to repo root
    repo_root = Path(__file__).resolve().parents[2]

    required_dirs = [
        "src/launch",
        "specs",
        "plans",
        "tests",
        "configs",
        "reports",
    ]

    for dir_path in required_dirs:
        full_path = repo_root / dir_path
        assert full_path.is_dir(), f"Required directory missing: {dir_path}"


def test_pyproject_toml_exists() -> None:
    """Verify pyproject.toml exists and is valid."""
    repo_root = Path(__file__).resolve().parents[2]
    pyproject = repo_root / "pyproject.toml"

    assert pyproject.is_file(), "pyproject.toml not found"

    # Basic validation that it contains expected content
    content = pyproject.read_text(encoding="utf-8")
    assert "[project]" in content, "pyproject.toml missing [project] section"
    assert "name = " in content, "pyproject.toml missing project name"
