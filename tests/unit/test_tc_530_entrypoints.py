"""
TC-530: CLI entrypoints smoke tests

These tests verify that CLI entrypoints are importable and console scripts
can be invoked (if installed). Tests are designed to pass even if console
scripts are not installed in the current environment.
"""

import importlib
import subprocess
import sys
from pathlib import Path

import pytest


def test_cli_module_importable():
    """Test that launch.cli module can be imported."""
    try:
        import launch.cli
        assert hasattr(launch.cli, "main"), "launch.cli.main function not found"
    except ImportError as e:
        pytest.fail(f"Failed to import launch.cli: {e}")


def test_validators_cli_module_importable():
    """Test that launch.validators.cli module can be imported."""
    try:
        import launch.validators.cli
        assert hasattr(launch.validators.cli, "main"), "launch.validators.cli.main function not found"
    except ImportError as e:
        pytest.fail(f"Failed to import launch.validators.cli: {e}")


def test_mcp_server_module_importable():
    """Test that launch.mcp.server module can be imported."""
    try:
        import launch.mcp.server
        assert hasattr(launch.mcp.server, "main"), "launch.mcp.server.main function not found"
    except ImportError as e:
        pytest.fail(f"Failed to import launch.mcp.server: {e}")


def _console_script_exists(script_name: str) -> bool:
    """Check if a console script is installed and in PATH."""
    try:
        result = subprocess.run(
            [script_name, "--help"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode in (0, 1, 2)  # Any exit code means it ran
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False


def test_launch_run_console_script_help():
    """Test that launch_run --help works (requires pip install -e .)."""
    # This test will fail if console script not installed - that's intentional
    # CI must install package before running tests
    result = subprocess.run(
        ["launch_run", "--help"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    # Help command may exit 0 (success) or 1 (Typer default for help in some versions)
    assert result.returncode in (0, 1), f"launch_run --help failed with exit code {result.returncode}"
    # Verify output contains expected help text
    output = result.stdout + result.stderr
    assert any(keyword in output.lower() for keyword in ["usage", "help", "options", "config"]), \
        f"launch_run --help output doesn't contain help text: {output[:200]}"


def test_launch_validate_console_script_help():
    """Test that launch_validate --help works (requires pip install -e .)."""
    result = subprocess.run(
        ["launch_validate", "--help"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode in (0, 1), f"launch_validate --help failed with exit code {result.returncode}"
    output = result.stdout + result.stderr
    assert any(keyword in output.lower() for keyword in ["usage", "help", "options", "validate"]), \
        f"launch_validate --help output doesn't contain help text: {output[:200]}"


def test_launch_mcp_console_script_help():
    """Test that launch_mcp --help works (requires pip install -e .)."""
    result = subprocess.run(
        ["launch_mcp", "--help"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode in (0, 1), f"launch_mcp --help failed with exit code {result.returncode}"
    output = result.stdout + result.stderr
    assert any(keyword in output.lower() for keyword in ["usage", "help", "options", "mcp", "server"]), \
        f"launch_mcp --help output doesn't contain help text: {output[:200]}"


def test_cli_modules_have_main_callable():
    """Verify all CLI modules have callable main functions."""
    modules_to_check = [
        "launch.cli",
        "launch.validators.cli",
        "launch.mcp.server",
    ]

    for module_name in modules_to_check:
        try:
            module = importlib.import_module(module_name)
            main_func = getattr(module, "main", None)
            assert main_func is not None, f"{module_name}.main not found"
            assert callable(main_func), f"{module_name}.main is not callable"
        except ImportError as e:
            pytest.fail(f"Failed to import {module_name}: {e}")


def test_pyproject_toml_has_console_scripts():
    """Verify pyproject.toml declares the expected console scripts."""
    # This test doesn't parse pyproject.toml to avoid adding toml parsing dependency
    # Instead, it just verifies the file exists and can be read
    repo_root = Path(__file__).parent.parent.parent
    pyproject_path = repo_root / "pyproject.toml"

    assert pyproject_path.exists(), "pyproject.toml not found"

    content = pyproject_path.read_text(encoding="utf-8")

    # Check that console scripts section exists
    assert "[project.scripts]" in content, "pyproject.toml missing [project.scripts] section"

    # Check for expected script declarations
    expected_scripts = [
        "launch_run",
        "launch_validate",
        "launch_mcp",
    ]

    for script_name in expected_scripts:
        assert script_name in content, f"Console script '{script_name}' not declared in pyproject.toml"


def test_cli_modules_are_in_allowed_paths():
    """Verify CLI modules exist at paths declared in TC-530 allowed_paths."""
    repo_root = Path(__file__).parent.parent.parent

    expected_files = [
        repo_root / "src" / "launch" / "cli.py",
        repo_root / "src" / "launch" / "validators" / "cli.py",
        repo_root / "src" / "launch" / "mcp" / "server.py",
    ]

    for file_path in expected_files:
        assert file_path.exists(), f"Expected CLI file not found: {file_path}"
        assert file_path.is_file(), f"Path exists but is not a file: {file_path}"
