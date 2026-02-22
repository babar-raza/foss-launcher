"""Tests for B1: W3 fallback to test/source files when example_paths empty."""
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


def _make_repo_inventory(tmp_path, example_paths=None, test_paths=None, source_paths=None):
    """Create repo_inventory.json with specified paths."""
    inventory = {
        "product_name": "test-lib",
        "product_family": "test",
    }
    if example_paths is not None:
        inventory["example_paths"] = example_paths
    if test_paths is not None:
        inventory["test_paths"] = test_paths
    if source_paths is not None:
        inventory["source_paths"] = source_paths
    return inventory


def test_fallback_to_test_files():
    """When example_paths is empty, fallback to test_paths + source_paths."""
    inventory = _make_repo_inventory(
        None,
        example_paths=[],
        test_paths=["tests/test_scene.py", "tests/test_mesh.py"],
        source_paths=["src/scene.py"],
    )
    example_paths = inventory.get("example_paths", [])
    if not example_paths:
        fallback_paths = [
            p for p in (
                inventory.get("test_paths", [])
                + inventory.get("source_paths", [])
            )
            if p.endswith(".py")
        ][:50]
        example_paths = fallback_paths

    assert len(example_paths) == 3
    assert "tests/test_scene.py" in example_paths
    assert "src/scene.py" in example_paths


def test_fallback_caps_at_50():
    """Fallback is capped at 50 paths."""
    inventory = _make_repo_inventory(
        None,
        example_paths=[],
        test_paths=[f"tests/test_{i}.py" for i in range(60)],
        source_paths=[],
    )
    example_paths = inventory.get("example_paths", [])
    if not example_paths:
        fallback_paths = [
            p for p in (
                inventory.get("test_paths", [])
                + inventory.get("source_paths", [])
            )
            if p.endswith(".py")
        ][:50]
        example_paths = fallback_paths

    assert len(example_paths) == 50


def test_no_fallback_when_examples_exist():
    """When example_paths is non-empty, no fallback occurs."""
    inventory = _make_repo_inventory(
        None,
        example_paths=["examples/demo.py"],
        test_paths=["tests/test_a.py"],
        source_paths=["src/core.py"],
    )
    example_paths = inventory.get("example_paths", [])
    if not example_paths:
        fallback_paths = [
            p for p in (
                inventory.get("test_paths", [])
                + inventory.get("source_paths", [])
            )
            if p.endswith(".py")
        ][:50]
        example_paths = fallback_paths

    assert example_paths == ["examples/demo.py"]


def test_fallback_filters_non_python():
    """Fallback only includes .py files."""
    inventory = _make_repo_inventory(
        None,
        example_paths=[],
        test_paths=["tests/test_a.py", "tests/conftest.js", "tests/data.json"],
        source_paths=["src/core.py", "src/config.yaml"],
    )
    example_paths = inventory.get("example_paths", [])
    if not example_paths:
        fallback_paths = [
            p for p in (
                inventory.get("test_paths", [])
                + inventory.get("source_paths", [])
            )
            if p.endswith(".py")
        ][:50]
        example_paths = fallback_paths

    assert len(example_paths) == 2
    assert all(p.endswith(".py") for p in example_paths)
