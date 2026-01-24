"""Tests for determinism enforcement (Guarantee I)."""

import os
import random
import pytest


def test_pythonhashseed_is_set():
    """Verify PYTHONHASHSEED=0 is enforced during test runs."""
    hashseed = os.environ.get("PYTHONHASHSEED")
    assert hashseed == "0", (
        f"PYTHONHASHSEED must be '0' for deterministic tests (Guarantee I), "
        f"got '{hashseed}'"
    )


def test_random_is_seeded(deterministic_random):
    """Verify random operations use deterministic seed."""
    # With seed=42, first random() call should always return same value
    value1 = random.random()

    # Reset seed and verify we get same value
    random.seed(42)
    value2 = random.random()

    assert value1 == value2, "Random values should be deterministic with same seed"


def test_seeded_rng_fixture(seeded_rng):
    """Verify seeded_rng fixture provides deterministic values."""
    # With seed=42, these values should always be the same
    value1 = seeded_rng.randint(1, 1000)
    value2 = seeded_rng.randint(1, 1000)
    value3 = seeded_rng.randint(1, 1000)

    # Create a new RNG with same seed - should get same sequence
    rng2 = random.Random(42)
    value1_repeat = rng2.randint(1, 1000)
    value2_repeat = rng2.randint(1, 1000)
    value3_repeat = rng2.randint(1, 1000)

    # Verify determinism
    assert value1 == value1_repeat
    assert value2 == value2_repeat
    assert value3 == value3_repeat


def test_fixed_timestamp_fixture(fixed_timestamp):
    """Verify fixed_timestamp fixture provides deterministic timestamp."""
    # Should always be 2024-01-01 00:00:00 UTC
    assert fixed_timestamp == 1704067200

    # Verify it's actually that date
    from datetime import datetime, UTC
    dt = datetime.fromtimestamp(fixed_timestamp, tz=UTC)
    assert dt.year == 2024
    assert dt.month == 1
    assert dt.day == 1


def test_hash_stability():
    """Verify dict/set ordering is deterministic with PYTHONHASHSEED=0."""
    # Create dict multiple times - order should be stable
    data1 = {f"key_{i}": i for i in range(100)}
    data2 = {f"key_{i}": i for i in range(100)}

    # Keys order should be deterministic
    assert list(data1.keys()) == list(data2.keys())

    # Set iteration order should be stable
    set1 = {f"item_{i}" for i in range(50)}
    set2 = {f"item_{i}" for i in range(50)}

    assert list(set1) == list(set2)
