from __future__ import annotations

import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[1]

# Allow running this script without an editable install.
# CI installs the package via `pip install -e .`, but local forensic runs
# often call the script directly.
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from launch.io.run_config import load_and_validate_run_config  # noqa: E402
from launch.io.toolchain import load_toolchain_lock  # noqa: E402


def _compile_schemas() -> list[str]:
    errors: list[str] = []
    schemas_dir = REPO_ROOT / "specs" / "schemas"
    for schema_path in sorted(schemas_dir.glob("*.schema.json")):
        try:
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
            Draft202012Validator.check_schema(schema)
        except Exception as e:
            errors.append(f"{schema_path.name}: {e}")
    return errors


def main() -> int:
    errors: list[str] = []

    # Toolchain lock sentinel check
    try:
        load_toolchain_lock(REPO_ROOT)
    except Exception as e:
        errors.append(f"toolchain.lock.yaml: {e}")

    # Schema compilation
    errors.extend(_compile_schemas())

    # Validate pinned pilot configs
    pilots = [
        REPO_ROOT / "specs" / "pilots" / "pilot-aspose-3d-foss-python" / "run_config.pinned.yaml",
        REPO_ROOT / "specs" / "pilots" / "pilot-aspose-note-foss-python" / "run_config.pinned.yaml",
    ]
    for pilot in pilots:
        try:
            load_and_validate_run_config(REPO_ROOT, pilot)
        except Exception as e:
            errors.append(f"{pilot}: {e}")

    if errors:
        print("SPEC PACK VALIDATION FAILED")
        for e in errors:
            print("-", e)
        return 2

    print("SPEC PACK VALIDATION OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
