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

    # Restore original state after test
    random.setstate(original_state)


@pytest.fixture
def seeded_rng() -> random.Random:
    """Provide an explicitly seeded RNG for tests that need it.

    Usage:
        def test_randomness(seeded_rng):
            value = seeded_rng.randint(1, 100)
    """
    return random.Random(42)


@pytest.fixture
def fixed_timestamp() -> int:
    """Provide a fixed timestamp for deterministic time-based tests.

    Returns:
        Fixed Unix timestamp (2024-01-01 00:00:00 UTC)
    """
    return 1704067200  # 2024-01-01 00:00:00 UTC


@pytest.fixture
def minimal_run_config():
    """Provide a minimal valid run_config for testing.

    This config has all required fields per specs/schemas/run_config.schema.json.
    Tests can override specific fields by passing them as kwargs.

    Returns:
        Dict with minimal valid run configuration
    """
    return {
        "schema_version": "1.0",
        "product_slug": "test-product",
        "product_name": "Test Product",
        "family": "test",
        "github_repo_url": "https://github.com/example/test-repo.git",
        "github_ref": "main",
        "required_sections": ["overview", "features"],
        "site_layout": {"content_dir": "content", "output_dir": "public"},
        "allowed_paths": ["content/", "data/"],
        "llm": {"provider": "test", "model": "test-model"},
        "mcp": {"enabled": False},
        "telemetry": {"enabled": False},
        "commit_service": {"mode": "test"},
        "templates_version": "1.0",
        "ruleset_version": "1.0",
        "allow_inference": False,
        "max_fix_attempts": 3,
        "budgets": {"max_tokens": 10000},
    }


# Enforce PYTHONHASHSEED=0 check
def pytest_configure(config):
    """Verify determinism configuration at test startup."""
    import os
    import sys
    import warnings
    from pathlib import Path

    # Add src to path for imports
    repo_root = Path(__file__).parent.parent
    src_dir = repo_root / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    # Check PYTHONHASHSEED
    hashseed = os.environ.get("PYTHONHASHSEED")
    if hashseed != "0":
        warnings.warn(
            f"WARNING: PYTHONHASHSEED is '{hashseed}', expected '0' for deterministic tests "
            "(Guarantee I: Non-Flaky Tests)",
            UserWarning,
        )
