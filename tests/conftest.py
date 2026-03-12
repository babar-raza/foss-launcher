from __future__ import annotations

import os
import random
import sys
from pathlib import Path
from typing import Generator

import pytest


def pytest_configure(config):
    """Enforce PYTHONHASHSEED=0 for determinism and add src to path."""
    seed = os.environ.get("PYTHONHASHSEED", "")
    if seed != "0":
        os.environ["PYTHONHASHSEED"] = "0"

    repo_root = Path(__file__).parent.parent
    src_dir = repo_root / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))


@pytest.fixture(autouse=True)
def deterministic_random() -> Generator[random.Random, None, None]:
    """Enforce seeded randomness for all tests."""
    original_state = random.getstate()
    random.seed(42)
    yield random
    random.setstate(original_state)


@pytest.fixture
def seeded_rng() -> random.Random:
    """Provide an explicitly seeded RNG for tests that need it."""
    return random.Random(42)


@pytest.fixture
def fixed_timestamp() -> int:
    """Provide a fixed timestamp (2024-01-01 00:00:00 UTC)."""
    return 1704067200


@pytest.fixture
def minimal_run_config():
    from launcher.models.run_config import RunConfig, LLMEndpoint, LLMConfig
    return RunConfig(
        family="cells",
        platform="python",
        repo_url="https://github.com/test/test-repo",
        llm=LLMConfig(
            primary=LLMEndpoint(base_url="http://localhost:11434/v1", model="test-model"),
        ),
    )


@pytest.fixture
def tmp_run_dir(tmp_path):
    run_dir = tmp_path / "runs" / "test-run"
    run_dir.mkdir(parents=True)
    return run_dir


@pytest.fixture
def repo_root() -> Path:
    """Return the repo root directory."""
    return Path(__file__).parent.parent
