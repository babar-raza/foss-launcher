from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

import pytest
from jsonschema import Draft202012Validator

from launch.io.run_config import load_and_validate_run_config
from launch.io.toolchain import load_toolchain_lock


REPO_ROOT = Path(__file__).resolve().parents[1]


def _iter_values(obj: Any) -> Iterable[Any]:
    if isinstance(obj, dict):
        for v in obj.values():
            yield from _iter_values(v)
    elif isinstance(obj, list):
        for i in obj:
            yield from _iter_values(i)
    else:
        yield obj


def test_toolchain_lock_has_no_pin_me_values() -> None:
    data = load_toolchain_lock(REPO_ROOT)
    assert isinstance(data, dict)
    assert data.get("schema_version")
    assert "PIN_ME" not in set(v for v in _iter_values(data) if isinstance(v, str))


def test_json_schemas_compile() -> None:
    schemas_dir = REPO_ROOT / "specs" / "schemas"
    for schema_path in schemas_dir.glob("*.schema.json"):
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)


@pytest.mark.parametrize(
    "pilot_path",
    [
        REPO_ROOT / "specs" / "pilots" / "pilot-aspose-3d-foss-python" / "run_config.pinned.yaml",
        REPO_ROOT / "specs" / "pilots" / "pilot-aspose-note-foss-python" / "run_config.pinned.yaml",
    ],
)
def test_pilot_configs_validate(pilot_path: Path) -> None:
    cfg = load_and_validate_run_config(REPO_ROOT, pilot_path)
    assert cfg["product_slug"]
    assert cfg["github_repo_url"]
