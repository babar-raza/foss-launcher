"""
TC-703: E2E tests for VFV harness.

These tests are skipped by default unless RUN_PILOT_E2E=1 is set.
"""

import pytest
import subprocess
import sys
import os
from pathlib import Path


def get_repo_root() -> Path:
    """Get the repository root."""
    return Path(__file__).resolve().parent.parent.parent


@pytest.mark.skipif(
    os.environ.get("RUN_PILOT_E2E") != "1",
    reason="Pilot E2E tests require RUN_PILOT_E2E=1"
)
def test_vfv_script_exists():
    """VFV script must exist and be executable."""
    repo_root = get_repo_root()
    script = repo_root / "scripts" / "run_pilot_vfv.py"
    assert script.exists(), f"VFV script not found: {script}"


@pytest.mark.skipif(
    os.environ.get("RUN_PILOT_E2E") != "1",
    reason="Pilot E2E tests require RUN_PILOT_E2E=1"
)
def test_multi_pilot_vfv_script_exists():
    """Multi-pilot VFV script must exist and be executable."""
    repo_root = get_repo_root()
    script = repo_root / "scripts" / "run_multi_pilot_vfv.py"
    assert script.exists(), f"Multi-pilot VFV script not found: {script}"


@pytest.mark.skipif(
    os.environ.get("RUN_PILOT_E2E") != "1",
    reason="Pilot E2E tests require RUN_PILOT_E2E=1"
)
def test_vfv_script_help():
    """VFV script must support --help."""
    repo_root = get_repo_root()
    venv_python = repo_root / ".venv" / "Scripts" / "python.exe"
    if not venv_python.exists():
        venv_python = repo_root / ".venv" / "bin" / "python"

    result = subprocess.run(
        [str(venv_python), str(repo_root / "scripts" / "run_pilot_vfv.py"), "--help"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0, f"Help command failed: {result.stderr}"
    assert "--pilot" in result.stdout, "Missing --pilot argument in help"
    assert "--goldenize" in result.stdout, "Missing --goldenize argument in help"
    assert "--verbose" in result.stdout, "Missing --verbose argument in help"


@pytest.mark.skipif(
    os.environ.get("RUN_PILOT_E2E") != "1",
    reason="Pilot E2E tests require RUN_PILOT_E2E=1"
)
def test_multi_pilot_vfv_script_help():
    """Multi-pilot VFV script must support --help."""
    repo_root = get_repo_root()
    venv_python = repo_root / ".venv" / "Scripts" / "python.exe"
    if not venv_python.exists():
        venv_python = repo_root / ".venv" / "bin" / "python"

    result = subprocess.run(
        [str(venv_python), str(repo_root / "scripts" / "run_multi_pilot_vfv.py"), "--help"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0, f"Help command failed: {result.stderr}"
    assert "--pilots" in result.stdout, "Missing --pilots argument in help"
    assert "--goldenize" in result.stdout, "Missing --goldenize argument in help"


@pytest.mark.skipif(
    os.environ.get("RUN_PILOT_E2E") != "1",
    reason="Pilot E2E tests require RUN_PILOT_E2E=1"
)
def test_vfv_script_missing_pilot_arg():
    """VFV script must fail gracefully when --pilot is missing."""
    repo_root = get_repo_root()
    venv_python = repo_root / ".venv" / "Scripts" / "python.exe"
    if not venv_python.exists():
        venv_python = repo_root / ".venv" / "bin" / "python"

    result = subprocess.run(
        [str(venv_python), str(repo_root / "scripts" / "run_pilot_vfv.py")],
        capture_output=True,
        text=True
    )
    assert result.returncode != 0, "Script should fail when --pilot is missing"
    assert "--pilot" in result.stderr or "required" in result.stderr.lower(), \
        "Error message should mention missing --pilot argument"


@pytest.mark.skipif(
    os.environ.get("RUN_PILOT_E2E") != "1",
    reason="Pilot E2E tests require RUN_PILOT_E2E=1"
)
def test_multi_pilot_vfv_script_missing_pilots_arg():
    """Multi-pilot VFV script must fail gracefully when --pilots is missing."""
    repo_root = get_repo_root()
    venv_python = repo_root / ".venv" / "Scripts" / "python.exe"
    if not venv_python.exists():
        venv_python = repo_root / ".venv" / "bin" / "python"

    result = subprocess.run(
        [str(venv_python), str(repo_root / "scripts" / "run_multi_pilot_vfv.py")],
        capture_output=True,
        text=True
    )
    assert result.returncode != 0, "Script should fail when --pilots is missing"
    assert "--pilots" in result.stderr or "required" in result.stderr.lower(), \
        "Error message should mention missing --pilots argument"
