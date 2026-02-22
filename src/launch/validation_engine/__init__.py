"""Declarative validation gate registry and runner.

Provides a data-driven alternative to the manually-coded gate orchestration
in ``w9_validator/worker.py``.  The public API:

- ``load_registry()``  – parse ``gates_registry.yaml``
- ``GateContext``       – lazy-loaded shared artifacts for a single run
- ``run_gates()``       – iterate the registry, call adapters, collect results

See also: ``specs/09_validation_gates.md`` and
``tools/extract_validation_gates.py --validate``.
"""

from __future__ import annotations

from .context import GateContext
from .gate_types import GateDefinition, GateResult, RunnerType, SkipGroup
from .registry_loader import load_registry
from .runner import run_gates

__all__ = [
    "GateContext",
    "GateDefinition",
    "GateResult",
    "RunnerType",
    "SkipGroup",
    "load_registry",
    "run_gates",
]
