"""Load and validate the gate registry YAML."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List

import yaml

from .gate_types import GateDefinition, RunnerType, SkipGroup

logger = logging.getLogger(__name__)

_REGISTRY_PATH = Path(__file__).parent / "gates_registry.yaml"


def load_registry(path: Path | None = None) -> List[GateDefinition]:
    """Load gate definitions from the YAML registry.

    Args:
        path: Path to registry YAML.  Defaults to the bundled
              ``gates_registry.yaml`` shipped with this package.

    Returns:
        List of :class:`GateDefinition` sorted by ``order``.

    Raises:
        FileNotFoundError: If the registry file is missing.
        ValueError: If structural invariants are violated.
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
