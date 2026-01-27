from __future__ import annotations

import json
import site
import sys
from pathlib import Path

# Ensure user site-packages is available (handles disabled ENABLE_USER_SITE on Windows)
if not site.ENABLE_USER_SITE:
    user_site = site.getusersitepackages()
    if user_site and user_site not in sys.path:
        sys.path.insert(0, user_site)

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

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore


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


def _validate_rulesets() -> list[str]:
    """Validate all rulesets against ruleset.schema.json."""
    errors: list[str] = []

    if yaml is None:
        errors.append("rulesets: PyYAML not installed, skipping ruleset validation")
        return errors

    schemas_dir = REPO_ROOT / "specs" / "schemas"
    rulesets_dir = REPO_ROOT / "specs" / "rulesets"

    schema_path = schemas_dir / "ruleset.schema.json"
    if not schema_path.exists():
        errors.append("rulesets: ruleset.schema.json not found")
        return errors

    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        validator = Draft202012Validator(schema)
    except Exception as e:
        errors.append(f"rulesets: Failed to load schema: {e}")
        return errors

    if not rulesets_dir.exists():
        errors.append("rulesets: specs/rulesets/ directory not found")
        return errors

    ruleset_files = sorted(rulesets_dir.glob("*.yaml"))
    if not ruleset_files:
        errors.append("rulesets: No .yaml files found in specs/rulesets/")
        return errors

    for ruleset_path in ruleset_files:
        try:
            ruleset_data = yaml.safe_load(ruleset_path.read_text(encoding="utf-8"))
            validation_errors = list(validator.iter_errors(ruleset_data))
            if validation_errors:
                for err in validation_errors:
                    path = ".".join(str(p) for p in err.path) if err.path else "root"
                    errors.append(f"{ruleset_path.name}: {path}: {err.message}")
        except yaml.YAMLError as e:
            errors.append(f"{ruleset_path.name}: YAML parse error: {e}")
        except Exception as e:
            errors.append(f"{ruleset_path.name}: {e}")

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

    # Validate rulesets against schema
    errors.extend(_validate_rulesets())

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
