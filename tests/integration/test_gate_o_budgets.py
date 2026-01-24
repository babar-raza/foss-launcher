"""Integration tests for Gate O (budget validation)."""

import json
import subprocess
import sys
from pathlib import Path
import pytest


def get_repo_root() -> Path:
    """Get repository root."""
    return Path(__file__).parent.parent.parent


def test_gate_o_exists():
    """Test that Gate O script exists."""
    gate_o_path = get_repo_root() / "tools" / "validate_budgets_config.py"
    assert gate_o_path.exists()


def test_gate_o_runs():
    """Test that Gate O can be executed."""
    gate_o_path = get_repo_root() / "tools" / "validate_budgets_config.py"

    result = subprocess.run(
        [sys.executable, str(gate_o_path)],
        capture_output=True,
        text=True,
        timeout=30,
    )

    # Should exit with 0 or 1 (not crash)
    assert result.returncode in (0, 1)


def test_schema_has_budgets_field():
    """Test that run_config schema defines budgets field."""
    schema_path = get_repo_root() / "specs" / "schemas" / "run_config.schema.json"

    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)

    # Check that budgets is in required fields
    assert "budgets" in schema["required"], "budgets not in schema required fields"

    # Check that budgets property is defined
    assert "budgets" in schema["properties"], "budgets property not defined in schema"

    # Check budgets fields
    budgets_schema = schema["properties"]["budgets"]
    assert budgets_schema["type"] == "object"

    required_budget_fields = [
        "max_runtime_s",
        "max_llm_calls",
        "max_llm_tokens",
        "max_file_writes",
        "max_patch_attempts",
        "max_lines_per_file",
        "max_files_changed",
    ]

    for field in required_budget_fields:
        assert field in budgets_schema["required"], f"{field} not in budgets required fields"
        assert field in budgets_schema["properties"], f"{field} property not defined"


def test_template_configs_have_budgets():
    """Test that template configs include budgets section."""
    templates = [
        get_repo_root() / "configs" / "products" / "_template.run_config.yaml",
        get_repo_root() / "configs" / "pilots" / "_template.pinned.run_config.yaml",
    ]

    for template_path in templates:
        if not template_path.exists():
            pytest.skip(f"Template not found: {template_path}")

        content = template_path.read_text(encoding="utf-8")

        assert "budgets:" in content, f"{template_path.name} missing budgets section"
        assert "max_runtime_s:" in content
        assert "max_llm_calls:" in content
        assert "max_llm_tokens:" in content
