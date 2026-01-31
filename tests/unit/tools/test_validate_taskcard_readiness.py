#!/usr/bin/env python3
"""
Unit tests for validate_taskcard_readiness.py (Gate B+1)
Tests taskcard readiness validation logic including dependency chains and circular dependencies.
"""

import pytest
from pathlib import Path
import sys

# Add tools to path for import
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "tools"))

from validate_taskcard_readiness import (
    extract_frontmatter,
    find_pilot_configs,
    extract_taskcard_id,
    find_taskcard_file,
    validate_taskcard_status,
    validate_dependency_chain,
    validate_taskcard,
)


# Test Fixtures

def create_pilot_config(tmp_path: Path, pilot_name: str, taskcard_id: str = None) -> Path:
    """Create a mock pilot config YAML file."""
    pilots_dir = tmp_path / "specs" / "pilots" / pilot_name
    pilots_dir.mkdir(parents=True, exist_ok=True)

    config_path = pilots_dir / "run_config.pinned.yaml"
    config_content = 'schema_version: "1.2"\n'

    if taskcard_id:
        config_content += f'taskcard_id: {taskcard_id}\n'

    config_content += 'product_slug: "test-pilot"\n'

    config_path.write_text(config_content)
    return config_path


def create_taskcard(tmp_path: Path, tc_id: str, status: str, depends_on: list = None) -> Path:
    """Create a mock taskcard markdown file."""
    taskcards_dir = tmp_path / "plans" / "taskcards"
    taskcards_dir.mkdir(parents=True, exist_ok=True)

    tc_path = taskcards_dir / f"{tc_id}_test_task.md"

    if depends_on is None:
        depends_on = []

    frontmatter = f"""---
id: {tc_id}
title: "Test Task"
status: {status}
owner: "TEST_AGENT"
updated: "2026-01-31"
depends_on: {depends_on}
allowed_paths:
  - "test/**"
evidence_required:
  - "test output"
spec_ref: "0000000000000000000000000000000000000000"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# Test Taskcard
"""

    tc_path.write_text(frontmatter)
    return tc_path


# Tests for extract_frontmatter

def test_extract_frontmatter_valid():
    """Test extracting valid YAML frontmatter."""
    content = """---
id: TC-100
title: Test
---

Body content
"""
    frontmatter, body, error = extract_frontmatter(content)

    assert error == ""
    assert frontmatter is not None
    assert frontmatter['id'] == 'TC-100'
    assert frontmatter['title'] == 'Test'
    assert 'Body content' in body


def test_extract_frontmatter_no_frontmatter():
    """Test content without frontmatter."""
    content = "Just body content"
    frontmatter, body, error = extract_frontmatter(content)

    assert frontmatter is None
    assert "No YAML frontmatter found" in error


def test_extract_frontmatter_malformed():
    """Test malformed frontmatter (no closing ---)."""
    content = """---
id: TC-100
title: Test

No closing marker
"""
    frontmatter, body, error = extract_frontmatter(content)

    assert frontmatter is None
    assert "Malformed YAML frontmatter" in error


def test_extract_frontmatter_invalid_yaml():
    """Test invalid YAML syntax."""
    content = """---
id: TC-100
  invalid indentation:
title: Test
---

Body
"""
    frontmatter, body, error = extract_frontmatter(content)

    assert frontmatter is None
    assert "YAML parse error" in error


# Tests for find_pilot_configs

def test_find_pilot_configs_empty(tmp_path):
    """Test finding pilot configs when none exist."""
    configs = find_pilot_configs(tmp_path)
    assert configs == []


def test_find_pilot_configs_single(tmp_path):
    """Test finding a single pilot config."""
    create_pilot_config(tmp_path, "pilot-test", "TC-100")

    configs = find_pilot_configs(tmp_path)
    assert len(configs) == 1
    assert configs[0].name == "run_config.pinned.yaml"


def test_find_pilot_configs_multiple(tmp_path):
    """Test finding multiple pilot configs."""
    create_pilot_config(tmp_path, "pilot-a", "TC-100")
    create_pilot_config(tmp_path, "pilot-b", "TC-200")

    configs = find_pilot_configs(tmp_path)
    assert len(configs) == 2


# Tests for extract_taskcard_id

def test_extract_taskcard_id_present(tmp_path):
    """Test extracting taskcard_id when present."""
    config_path = create_pilot_config(tmp_path, "pilot-test", "TC-100")

    tc_id = extract_taskcard_id(config_path)
    assert tc_id == "TC-100"


def test_extract_taskcard_id_missing(tmp_path):
    """Test extracting taskcard_id when not present (backward compatible)."""
    config_path = create_pilot_config(tmp_path, "pilot-test", None)

    tc_id = extract_taskcard_id(config_path)
    assert tc_id is None


def test_extract_taskcard_id_invalid_yaml(tmp_path):
    """Test extracting taskcard_id from invalid YAML."""
    pilots_dir = tmp_path / "specs" / "pilots" / "pilot-test"
    pilots_dir.mkdir(parents=True)

    config_path = pilots_dir / "run_config.pinned.yaml"
    config_path.write_text("invalid: yaml: syntax:")

    tc_id = extract_taskcard_id(config_path)
    assert tc_id is None


# Tests for find_taskcard_file

def test_find_taskcard_file_exists(tmp_path):
    """Test finding existing taskcard file."""
    create_taskcard(tmp_path, "TC-100", "Ready")

    tc_path = find_taskcard_file("TC-100", tmp_path)
    assert tc_path is not None
    assert tc_path.name == "TC-100_test_task.md"


def test_find_taskcard_file_missing(tmp_path):
    """Test finding non-existent taskcard file."""
    tc_path = find_taskcard_file("TC-999", tmp_path)
    assert tc_path is None


def test_find_taskcard_file_no_directory(tmp_path):
    """Test finding taskcard when directory doesn't exist."""
    tc_path = find_taskcard_file("TC-100", tmp_path)
    assert tc_path is None


# Tests for validate_taskcard_status

def test_validate_taskcard_status_ready():
    """Test validating status 'Ready'."""
    frontmatter = {'status': 'Ready'}
    is_valid, error = validate_taskcard_status(frontmatter)

    assert is_valid is True
    assert error == ""


def test_validate_taskcard_status_done():
    """Test validating status 'Done'."""
    frontmatter = {'status': 'Done'}
    is_valid, error = validate_taskcard_status(frontmatter)

    assert is_valid is True
    assert error == ""


def test_validate_taskcard_status_draft():
    """Test validating status 'Draft' (should fail)."""
    frontmatter = {'status': 'Draft'}
    is_valid, error = validate_taskcard_status(frontmatter)

    assert is_valid is False
    assert "Draft" in error
    assert "Ready" in error or "Done" in error


def test_validate_taskcard_status_blocked():
    """Test validating status 'Blocked' (should fail)."""
    frontmatter = {'status': 'Blocked'}
    is_valid, error = validate_taskcard_status(frontmatter)

    assert is_valid is False
    assert "Blocked" in error


def test_validate_taskcard_status_in_progress():
    """Test validating status 'In-Progress' (should fail)."""
    frontmatter = {'status': 'In-Progress'}
    is_valid, error = validate_taskcard_status(frontmatter)

    assert is_valid is False
    assert "In-Progress" in error


def test_validate_taskcard_status_missing():
    """Test validating missing status field."""
    frontmatter = {}
    is_valid, error = validate_taskcard_status(frontmatter)

    assert is_valid is False
    assert "Missing 'status'" in error


def test_validate_taskcard_status_wrong_type():
    """Test validating status with wrong type."""
    frontmatter = {'status': 123}
    is_valid, error = validate_taskcard_status(frontmatter)

    assert is_valid is False
    assert "must be a string" in error


# Tests for validate_dependency_chain

def test_validate_dependency_chain_no_deps(tmp_path):
    """Test validating taskcard with no dependencies."""
    create_taskcard(tmp_path, "TC-100", "Ready", depends_on=[])

    is_valid, errors = validate_dependency_chain("TC-100", tmp_path)

    assert is_valid is True
    assert errors == []


def test_validate_dependency_chain_satisfied(tmp_path):
    """Test validating satisfied dependency chain."""
    create_taskcard(tmp_path, "TC-100", "Done", depends_on=[])
    create_taskcard(tmp_path, "TC-200", "Ready", depends_on=["TC-100"])

    is_valid, errors = validate_dependency_chain("TC-200", tmp_path)

    assert is_valid is True
    assert errors == []


def test_validate_dependency_chain_missing(tmp_path):
    """Test validating chain with missing dependency."""
    create_taskcard(tmp_path, "TC-200", "Ready", depends_on=["TC-999"])

    is_valid, errors = validate_dependency_chain("TC-200", tmp_path)

    assert is_valid is False
    assert any("TC-999" in err and "not found" in err for err in errors)


def test_validate_dependency_chain_circular(tmp_path):
    """Test detecting circular dependencies."""
    create_taskcard(tmp_path, "TC-100", "Ready", depends_on=["TC-200"])
    create_taskcard(tmp_path, "TC-200", "Ready", depends_on=["TC-100"])

    is_valid, errors = validate_dependency_chain("TC-100", tmp_path)

    assert is_valid is False
    assert any("Circular dependency" in err for err in errors)


def test_validate_dependency_chain_self_reference(tmp_path):
    """Test detecting self-referencing dependency."""
    create_taskcard(tmp_path, "TC-100", "Ready", depends_on=["TC-100"])

    is_valid, errors = validate_dependency_chain("TC-100", tmp_path)

    assert is_valid is False
    assert any("Circular dependency" in err for err in errors)


def test_validate_dependency_chain_deep(tmp_path):
    """Test validating deep dependency chain."""
    create_taskcard(tmp_path, "TC-100", "Done", depends_on=[])
    create_taskcard(tmp_path, "TC-200", "Done", depends_on=["TC-100"])
    create_taskcard(tmp_path, "TC-300", "Ready", depends_on=["TC-200"])

    is_valid, errors = validate_dependency_chain("TC-300", tmp_path)

    assert is_valid is True
    assert errors == []


def test_validate_dependency_chain_draft_dependency(tmp_path):
    """Test validating chain with Draft dependency (should fail)."""
    create_taskcard(tmp_path, "TC-100", "Draft", depends_on=[])
    create_taskcard(tmp_path, "TC-200", "Ready", depends_on=["TC-100"])

    is_valid, errors = validate_dependency_chain("TC-200", tmp_path)

    assert is_valid is False
    assert any("TC-100" in err and "Draft" in err for err in errors)


# Tests for validate_taskcard

def test_validate_taskcard_exists_pass(tmp_path):
    """Test validating existing taskcard with Ready status."""
    create_taskcard(tmp_path, "TC-100", "Ready", depends_on=[])

    is_valid, errors = validate_taskcard("TC-100", tmp_path, "pilot-test")

    assert is_valid is True
    assert errors == []


def test_validate_taskcard_done_status_pass(tmp_path):
    """Test validating taskcard with Done status."""
    create_taskcard(tmp_path, "TC-100", "Done", depends_on=[])

    is_valid, errors = validate_taskcard("TC-100", tmp_path, "pilot-test")

    assert is_valid is True
    assert errors == []


def test_validate_taskcard_missing_fail(tmp_path):
    """Test validating missing taskcard."""
    is_valid, errors = validate_taskcard("TC-999", tmp_path, "pilot-test")

    assert is_valid is False
    assert any("TC-999" in err and "not found" in err for err in errors)
    assert any("pilot-test" in err for err in errors)


def test_validate_taskcard_draft_status_blocked(tmp_path):
    """Test validating taskcard with Draft status (should fail)."""
    create_taskcard(tmp_path, "TC-100", "Draft", depends_on=[])

    is_valid, errors = validate_taskcard("TC-100", tmp_path, "pilot-test")

    assert is_valid is False
    assert any("Draft" in err for err in errors)


def test_validate_taskcard_blocked_status_fail(tmp_path):
    """Test validating taskcard with Blocked status (should fail)."""
    create_taskcard(tmp_path, "TC-100", "Blocked", depends_on=[])

    is_valid, errors = validate_taskcard("TC-100", tmp_path, "pilot-test")

    assert is_valid is False
    assert any("Blocked" in err for err in errors)


def test_validate_taskcard_with_dependencies(tmp_path):
    """Test validating taskcard with satisfied dependencies."""
    create_taskcard(tmp_path, "TC-100", "Done", depends_on=[])
    create_taskcard(tmp_path, "TC-200", "Ready", depends_on=["TC-100"])

    is_valid, errors = validate_taskcard("TC-200", tmp_path, "pilot-test")

    assert is_valid is True
    assert errors == []


def test_validate_taskcard_dependency_missing_fail(tmp_path):
    """Test validating taskcard with missing dependency."""
    create_taskcard(tmp_path, "TC-200", "Ready", depends_on=["TC-999"])

    is_valid, errors = validate_taskcard("TC-200", tmp_path, "pilot-test")

    assert is_valid is False
    assert any("TC-999" in err and "not found" in err for err in errors)


def test_validate_taskcard_circular_dependency_fail(tmp_path):
    """Test validating taskcard with circular dependency."""
    create_taskcard(tmp_path, "TC-100", "Ready", depends_on=["TC-200"])
    create_taskcard(tmp_path, "TC-200", "Ready", depends_on=["TC-100"])

    is_valid, errors = validate_taskcard("TC-100", tmp_path, "pilot-test")

    assert is_valid is False
    assert any("Circular dependency" in err for err in errors)


def test_validate_taskcard_invalid_frontmatter(tmp_path):
    """Test validating taskcard with invalid frontmatter."""
    taskcards_dir = tmp_path / "plans" / "taskcards"
    taskcards_dir.mkdir(parents=True)

    tc_path = taskcards_dir / "TC-100_test.md"
    tc_path.write_text("No frontmatter here")

    is_valid, errors = validate_taskcard("TC-100", tmp_path, "pilot-test")

    assert is_valid is False
    assert any("frontmatter" in err.lower() for err in errors)


# Integration Tests

def test_integration_no_pilots(tmp_path):
    """Integration test: no pilot configs found."""
    configs = find_pilot_configs(tmp_path)
    assert configs == []


def test_integration_pilot_without_taskcard_id(tmp_path):
    """Integration test: pilot without taskcard_id (backward compatible)."""
    create_pilot_config(tmp_path, "pilot-test", None)

    configs = find_pilot_configs(tmp_path)
    assert len(configs) == 1

    tc_id = extract_taskcard_id(configs[0])
    assert tc_id is None


def test_integration_valid_pilot_and_taskcard(tmp_path):
    """Integration test: valid pilot referencing valid taskcard."""
    create_pilot_config(tmp_path, "pilot-test", "TC-100")
    create_taskcard(tmp_path, "TC-100", "Ready", depends_on=[])

    configs = find_pilot_configs(tmp_path)
    assert len(configs) == 1

    tc_id = extract_taskcard_id(configs[0])
    assert tc_id == "TC-100"

    is_valid, errors = validate_taskcard(tc_id, tmp_path, "pilot-test")
    assert is_valid is True
    assert errors == []


def test_integration_multiple_pilots_mixed(tmp_path):
    """Integration test: multiple pilots with mixed validation results."""
    # Pilot 1: No taskcard_id (skip)
    create_pilot_config(tmp_path, "pilot-a", None)

    # Pilot 2: Valid taskcard
    create_pilot_config(tmp_path, "pilot-b", "TC-100")
    create_taskcard(tmp_path, "TC-100", "Ready", depends_on=[])

    # Pilot 3: Missing taskcard
    create_pilot_config(tmp_path, "pilot-c", "TC-999")

    configs = find_pilot_configs(tmp_path)
    assert len(configs) == 3

    # Validate pilot-b (should pass)
    tc_id_b = extract_taskcard_id(configs[1])
    is_valid_b, errors_b = validate_taskcard(tc_id_b, tmp_path, "pilot-b")
    assert is_valid_b is True

    # Validate pilot-c (should fail)
    tc_id_c = extract_taskcard_id(configs[2])
    is_valid_c, errors_c = validate_taskcard(tc_id_c, tmp_path, "pilot-c")
    assert is_valid_c is False
