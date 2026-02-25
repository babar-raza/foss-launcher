"""Load and validate the gate registry YAML."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import List

import yaml

from .gate_types import GateDefinition, RunnerType, SkipGroup

logger = logging.getLogger(__name__)

_REGISTRY_PATH = Path(__file__).parent / "gates_registry.yaml"


def load_registry(
    path: Path | None = None,
    validate_callables: bool = False,
) -> List[GateDefinition]:
    """Load gate definitions from the YAML registry.

    Args:
        path: Path to registry YAML.  Defaults to the bundled
              ``gates_registry.yaml`` shipped with this package.
        validate_callables: When ``True``, eagerly import every gate's
            module and verify the named callable exists and is callable.
            Also activated when the environment variable
            ``LAUNCH_VALIDATE_GATE_CALLABLES=1`` is set.  Defaults to
            ``False`` to preserve backward compatibility.

    Returns:
        List of :class:`GateDefinition` sorted by ``order``.

    Raises:
        FileNotFoundError: If the registry file is missing.
        ValueError: If structural invariants are violated, or if
            ``validate_callables`` is active and any gate's callable
            cannot be resolved.
    """
    registry_path = path or _REGISTRY_PATH

    with registry_path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    if not isinstance(data, dict) or "gates" not in data:
        raise ValueError(
            f"Registry YAML must have a top-level 'gates' key: {registry_path}"
        )

    gates: List[GateDefinition] = []
    for entry in data["gates"]:
        gate = GateDefinition(
            gate_id=entry["gate_id"],
            display_name=entry["display_name"],
            order=entry["order"],
            module=entry["module"],
            callable_name=entry["callable_name"],
            runner_type=RunnerType(entry["runner_type"]),
            skip_group=SkipGroup(entry.get("skip_group", "none")),
            skip_on_error=entry.get("skip_on_error", False),
            graceful_artifact_skip=entry.get("graceful_artifact_skip", False),
            inputs=tuple(entry.get("inputs", [])),
            notes=entry.get("notes", ""),
        )
        gates.append(gate)

    gates.sort(key=lambda g: g.order)
    _validate_registry(gates)

    _should_validate = validate_callables or (
        os.environ.get("LAUNCH_VALIDATE_GATE_CALLABLES") == "1"
    )
    if _should_validate:
        _validate_callables(gates)

    return gates


def _validate_registry(gates: List[GateDefinition]) -> None:
    """Check structural invariants."""

    gate_ids = [g.gate_id for g in gates]
    if len(gate_ids) != len(set(gate_ids)):
        dupes = sorted({gid for gid in gate_ids if gate_ids.count(gid) > 1})
        raise ValueError(f"Duplicate gate_ids in registry: {dupes}")

    orders = [g.order for g in gates]
    if len(orders) != len(set(orders)):
        raise ValueError("Duplicate order values in registry")

    for gate in gates:
        if not gate.module:
            raise ValueError(f"Gate {gate.gate_id}: empty module path")
        if not gate.callable_name:
            raise ValueError(f"Gate {gate.gate_id}: empty callable_name")


def _validate_callables(gates: List[GateDefinition]) -> None:
    """Eagerly resolve every gate's callable and collect any errors.

    Args:
        gates: List of gate definitions to validate.

    Raises:
        ValueError: Listing all resolution errors if any were found.
    """
    from .adapters import resolve_callable

    errors: List[str] = []
    for gate in gates:
        try:
            fn = resolve_callable(gate)
            if not callable(fn):
                errors.append(
                    f"{gate.gate_id}: attribute '{gate.callable_name}' in "
                    f"'{gate.module}' is not callable "
                    f"(got {type(fn).__name__})"
                )
        except ImportError as exc:
            errors.append(
                f"{gate.gate_id}: cannot import module '{gate.module}': {exc}"
            )
        except AttributeError as exc:
            errors.append(
                f"{gate.gate_id}: attribute '{gate.callable_name}' not found "
                f"in '{gate.module}': {exc}"
            )
        except Exception as exc:  # noqa: BLE001
            errors.append(
                f"{gate.gate_id}: unexpected error resolving callable: {exc}"
            )

    if errors:
        bullet_list = "\n  - ".join(errors)
        raise ValueError(
            f"Gate callable validation failed ({len(errors)} error(s)):\n"
            f"  - {bullet_list}"
        )
