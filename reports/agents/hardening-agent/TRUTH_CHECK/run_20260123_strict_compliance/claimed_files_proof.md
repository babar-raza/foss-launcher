# File Existence Verification

Verifying all claimed files from compliance_matrix.md actually exist.

## Core Specs

### specs/34_strict_compliance_guarantees.md
-rw-r--r-- 1 prora 197609 16859 Jan 23 19:33 specs/34_strict_compliance_guarantees.md
# Strict Compliance Guarantees (Binding)

## Purpose

This specification defines **mandatory** compliance guarantees that MUST be enforced via automated gates, runtime validation, and tests. These guarantees eliminate entire classes of supply-chain, security, and reliability risks.

**Status**: BINDING for all production runs and agent implementations.

## Dependencies

- [specs/01_system_contract.md](../../../../../specs/01_system_contract.md) - System-wide contracts
- [specs/09_validation_gates.md](../../../../../specs/09_validation_gates.md) - Validation gate contracts
- [specs/19_toolchain_and_ci.md](../../../../../specs/19_toolchain_and_ci.md) - Toolchain and CI contracts
- [specs/29_project_repo_structure.md](../../../../../specs/29_project_repo_structure.md) - RUN_DIR isolation contracts
- [tools/validate_swarm_ready.py](../../../../../tools/validate_swarm_ready.py) - Preflight gate runner
- [src/launch/validators/cli.py](../../../../../src/launch/validators/cli.py) - Runtime validation (`launch_validate`)

---

## Production Paths (Binding Definition)

**Production paths** are code paths that MUST NOT contain placeholders, stubs, or "NOT_IMPLEMENTED" patterns that could produce false passes in validation.

Production paths include:
- `src/launch/**` (all runtime launcher code)
- Validation paths: `tools/validate_*.py`, `src/launch/validators/**`
- Gate scripts invoked by `tools/validate_swarm_ready.py`

**Exemptions**:
- Test fixtures under `tests/` MAY use placeholders for negative test cases

## Path Validation Implementation

### src/launch/util/path_validation.py
-rw-r--r-- 1 prora 197609 5617 Jan 23 19:59 src/launch/util/path_validation.py
"""Hermetic path validation utilities (Guarantee B).

Validates that all file operations are confined to allowed boundaries
and prevents path escape via .., absolute paths, or symlink traversal.

Binding contract: specs/34_strict_compliance_guarantees.md (Guarantee B)
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Union


class PathValidationError(Exception):
    """Raised when path validation fails (policy violation)."""

    def __init__(self, message: str, error_code: str = "POLICY_PATH_ESCAPE"):
        super().__init__(message)
        self.error_code = error_code


def validate_path_in_boundary(
    path: Union[str, Path],
    boundary: Union[str, Path],
    *,
    resolve_symlinks: bool = True,
) -> Path:
    """Validate that a path is within the allowed boundary.


### tests/unit/util/test_path_validation.py
-rw-r--r-- 1 prora 197609 11246 Jan 23 19:59 tests/unit/util/test_path_validation.py
"""Tests for hermetic path validation utilities (Guarantee B)."""

import pytest
from pathlib import Path
import tempfile
import os

from launch.util.path_validation import (
    PathValidationError,
    validate_path_in_boundary,
    validate_path_in_allowed,
    validate_no_path_traversal,
    is_path_in_boundary,
)


class TestValidatePathInBoundary:
    """Tests for validate_path_in_boundary function."""

    def test_valid_path_within_boundary(self, tmp_path):
        """Path within boundary should pass."""
        boundary = tmp_path
        file_path = boundary / "subdir" / "file.txt"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.touch()

        result = validate_path_in_boundary(file_path, boundary)
        assert result.is_relative_to(boundary)

    def test_path_equals_boundary(self, tmp_path):

## Determinism Implementation

### tests/conftest.py
-rw-r--r-- 1 prora 197609 1770 Jan 23 20:02 tests/conftest.py
"""Pytest configuration and fixtures for non-flaky tests (Guarantee I).

All tests use seeded randomness and deterministic operations
to ensure stability and reproducibility.
"""

import random
import pytest
from typing import Generator


@pytest.fixture(autouse=True)
def deterministic_random() -> Generator[random.Random, None, None]:
    """Enforce seeded randomness for all tests.

    This fixture automatically runs for every test and ensures
    any random operations use a deterministic seed.

    Usage:
        def test_something(deterministic_random):
            # random.random() will use seed=42
            value = random.random()
    """
    # Save original state
    original_state = random.getstate()

    # Set deterministic seed
    random.seed(42)

    yield random

## Validation Gates

tools/validate_budgets_config.py
tools/validate_ci_parity.py
tools/validate_dotvenv_policy.py
tools/validate_mcp_contract.py
tools/validate_network_allowlist.py
tools/validate_no_placeholders_production.py
tools/validate_phase_report_integrity.py
tools/validate_pilots_contract.py
tools/validate_pinned_refs.py
tools/validate_platform_layout.py
tools/validate_secrets_hygiene.py
tools/validate_supply_chain_pinning.py
tools/validate_swarm_ready.py
tools/validate_taskcard_version_locks.py
tools/validate_taskcards.py
tools/validate_untrusted_code_policy.py

## Network Allowlist

-rw-r--r-- 1 prora 197609 742 Jan 23 19:46 config/network_allowlist.yaml
# Network Egress Allowlist (Guarantee D)
#
# All HTTP requests MUST be to hosts in this allowlist.
# See: specs/34_strict_compliance_guarantees.md (Guarantee D)
#
# Format: List of allowed hosts/domains

allowed_hosts:
  # Local development
  - localhost
  - 127.0.0.1

  # GitHub API
  - api.github.com
  - github.com
  - raw.githubusercontent.com

  # Aspose services (placeholder - replace with actual endpoints)
  - "*.aspose.com"

  # LLM providers (localhost for development, update for production)
  # Example: Ollama local endpoint
  - 127.0.0.1:11434

  # Telemetry service (localhost for development)
  - 127.0.0.1:8765

  # Commit service (localhost for development)
  - 127.0.0.1:4320

  # Add production endpoints here as needed

