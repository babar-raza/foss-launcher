"""
TC-520: Test pilot discovery and enumeration.

These tests ensure that pilot enumeration is deterministic, sorted, and stable.
"""

import sys
from pathlib import Path

import pytest

# Add scripts to path
repo_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(repo_root / "scripts"))

from run_pilot import enumerate_pilots, get_repo_root


def test_pilot_discovery_sorted():
    """Test that pilot enumeration returns sorted, stable list."""
    repo_root = get_repo_root()
    pilots = enumerate_pilots(repo_root)

    # Should return a list
    assert isinstance(pilots, list), "enumerate_pilots should return a list"

    # Should be sorted
    assert pilots == sorted(pilots), "Pilot IDs should be sorted alphabetically"

    # Should be stable (call multiple times, get same result)
    pilots2 = enumerate_pilots(repo_root)
    assert pilots == pilots2, "Pilot enumeration should be deterministic"


def test_pilot_discovery_not_empty():
    """Test that at least one pilot exists."""
    repo_root = get_repo_root()
    pilots = enumerate_pilots(repo_root)

    assert len(pilots) > 0, "At least one pilot should exist in specs/pilots/"


def test_pilot_discovery_valid_ids():
    """Test that all discovered pilots have valid IDs."""
    repo_root = get_repo_root()
    pilots = enumerate_pilots(repo_root)

    for pilot_id in pilots:
        # Should be non-empty string
        assert isinstance(pilot_id, str), f"Pilot ID should be string: {pilot_id}"
        assert len(pilot_id) > 0, "Pilot ID should not be empty"

        # Should not start with dot (hidden directories)
        assert not pilot_id.startswith("."), f"Pilot ID should not start with dot: {pilot_id}"

        # Directory should exist
        pilot_dir = repo_root / "specs" / "pilots" / pilot_id
        assert pilot_dir.exists(), f"Pilot directory should exist: {pilot_dir}"
        assert pilot_dir.is_dir(), f"Pilot path should be directory: {pilot_dir}"


def test_pilot_has_config():
    """Test that all pilots have run_config.pinned.yaml."""
    repo_root = get_repo_root()
    pilots = enumerate_pilots(repo_root)

    for pilot_id in pilots:
        config_path = repo_root / "specs" / "pilots" / pilot_id / "run_config.pinned.yaml"
        assert config_path.exists(), (
            f"Pilot {pilot_id} should have run_config.pinned.yaml at {config_path}"
        )
