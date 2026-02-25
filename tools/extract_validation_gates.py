#!/usr/bin/env python3
"""Extract and validate the validation gate registry against worker.py.

Usage:
    python tools/extract_validation_gates.py --validate          # check gate-set sync
    python tools/extract_validation_gates.py --check-callables   # verify all callables resolve
    python tools/extract_validation_gates.py --generate          # regenerate skeleton YAML
"""

from __future__ import annotations

import argparse
import importlib
import re
import sys
from pathlib import Path

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[1]
_WORKER_PATH = _REPO_ROOT / "src" / "launch" / "workers" / "w9_validator" / "worker.py"
_REGISTRY_PATH = _REPO_ROOT / "src" / "launch" / "validation_engine" / "gates_registry.yaml"


def extract_gate_order_from_worker(worker_path: Path) -> list[str]:
    """Extract unique gate_ids from ``gate_results.append()`` calls.

    Scans the legacy function ``_execute_validator_legacy`` (or the
    original ``execute_validator`` if legacy not yet extracted).
    De-duplicates gate IDs to handle conditional branches that append
    the same gate in multiple code paths (e.g., except blocks).
    """
    content = worker_path.read_text(encoding="utf-8")
    # Handle both single-line and multi-line append calls:
    #   gate_results.append({"name": "gate_X", ...})
    #   gate_results.append(\n    {"name": "gate_X", ...})
    pattern = re.compile(
        r'gate_results\.append\(\s*\{["\']name["\']\s*:\s*["\']([^"\']+)["\']',
        re.DOTALL,
    )

    gate_ids: list[str] = []
    seen: set[str] = set()
    for match in pattern.finditer(content):
        gate_id = match.group(1)
        if gate_id not in seen:
            gate_ids.append(gate_id)
            seen.add(gate_id)
    return gate_ids


def load_registry_order(registry_path: Path) -> list[str]:
    """Load gate_ids from registry YAML in order."""
    with registry_path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    gates = sorted(data["gates"], key=lambda g: g["order"])
    return [g["gate_id"] for g in gates]


def discover_gate_modules(repo_root: Path) -> list[str]:
    """Find all gate module files under w9_validator/gates/."""
    gates_dir = repo_root / "src" / "launch" / "workers" / "w9_validator" / "gates"
    modules: list[str] = []
    for py_file in sorted(gates_dir.glob("gate_*.py")):
        modules.append(py_file.stem)
    return modules


def validate(worker_path: Path, registry_path: Path) -> bool:
    """Compare gate sets and coverage: worker.py vs registry YAML.

    Validates:
    1. Both have the same set of gate_ids (no missing, no extra)
    2. All gate modules on disk are represented in the registry

    Note: Strict positional comparison is not enforced because the
    legacy code's ``except`` blocks can cause textual order to differ
    from actual runtime order (e.g. gate_20 appears in an except block
    before gate_17's normal code path).  The golden comparison test
    (``test_validation_engine_golden.py``) validates actual runtime
    identity.
    """
    worker_gates = extract_gate_order_from_worker(worker_path)
    registry_gates = load_registry_order(registry_path)

    ok = True

    # Set comparison — must have identical gate_id sets
    worker_set = set(worker_gates)
    registry_set = set(registry_gates)

    missing_from_registry = worker_set - registry_set
    extra_in_registry = registry_set - worker_set

    if missing_from_registry:
        print(f"ERROR: gates in worker.py but missing from registry: {sorted(missing_from_registry)}")
        ok = False

    if extra_in_registry:
        print(f"ERROR: gates in registry but missing from worker.py: {sorted(extra_in_registry)}")
        ok = False

    if len(worker_gates) != len(registry_gates):
        print(f"ERROR: count mismatch: worker={len(worker_gates)}, registry={len(registry_gates)}")
        ok = False

    if ok:
        print(f"OK: {len(worker_gates)} gates match between worker.py and registry")

    # Check for gate modules not in registry
    repo_root = worker_path.parents[4]
    modules = discover_gate_modules(repo_root)
    registry_modules = set()
    with registry_path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    for g in data["gates"]:
        mod_parts = g["module"].split(".")
        if "gates" in mod_parts:
            idx = mod_parts.index("gates")
            if idx + 1 < len(mod_parts):
                registry_modules.add(mod_parts[idx + 1])

    for mod in modules:
        if mod == "__init__":
            continue
        if mod not in registry_modules:
            print(f"WARNING: gate module '{mod}' exists but is not in registry")

    return ok


def generate(worker_path: Path) -> None:
    """Print a skeleton registry YAML from worker.py gate order."""
    gate_ids = extract_gate_order_from_worker(worker_path)
    print("gates:")
    for i, gate_id in enumerate(gate_ids, 1):
        print(f"  - gate_id: {gate_id}")
        print(f"    display_name: '{gate_id}'")
        print(f"    order: {i}")
        print(f"    module: TODO")
        print(f"    callable_name: TODO")
        print(f"    runner_type: execute_gate")
        print()


def check_callables(registry_path: Path) -> bool:
    """Eagerly import every gate module and verify the named callable exists.

    Hard-fails (returns False) if any gate module cannot be imported or if the
    named callable attribute is missing or not callable.

    This mirrors ``registry_loader._validate_callables()`` but runs from the
    command line without requiring the package to be fully installed.

    Returns:
        True  — all 28 callables resolved successfully
        False — one or more callables failed (errors printed to stdout)
    """
    # Add src/ to sys.path so imports resolve without installation
    src_dir = _REPO_ROOT / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    with registry_path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    errors: list[str] = []
    ok_count = 0

    for entry in sorted(data["gates"], key=lambda g: g["order"]):
        gate_id = entry["gate_id"]
        module_path = entry["module"]
        callable_name = entry["callable_name"]
        try:
            mod = importlib.import_module(module_path)
        except ImportError as exc:
            errors.append(f"  {gate_id}: cannot import '{module_path}': {exc}")
            continue

        fn = getattr(mod, callable_name, None)
        if fn is None:
            errors.append(
                f"  {gate_id}: attribute '{callable_name}' not found in '{module_path}'"
            )
        elif not callable(fn):
            errors.append(
                f"  {gate_id}: '{callable_name}' in '{module_path}' is not callable "
                f"(got {type(fn).__name__})"
            )
        else:
            ok_count += 1

    if errors:
        print(f"FAILED: {len(errors)} callable(s) could not be resolved:")
        for err in errors:
            print(err)
        return False

    print(f"OK: {ok_count} callables resolved successfully")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--validate", action="store_true", help="Validate registry against worker.py")
    group.add_argument("--check-callables", action="store_true", help="Verify all gate callables resolve")
    group.add_argument("--generate", action="store_true", help="Generate skeleton registry from worker.py")
    args = parser.parse_args()

    if args.generate:
        generate(_WORKER_PATH)
    elif args.validate:
        ok = validate(_WORKER_PATH, _REGISTRY_PATH)
        sys.exit(0 if ok else 1)
    elif args.check_callables:
        ok = check_callables(_REGISTRY_PATH)
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
