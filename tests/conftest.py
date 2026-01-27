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
