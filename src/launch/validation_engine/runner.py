"""Gate execution runner.

Iterates the YAML registry in order, delegates to adapters, collects
results.  Replicates the exact skip/error semantics of the original
``execute_validator()`` gate loop.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)


def run_gates(
    run_dir: Path,
    run_config: Dict[str, Any],
    profile: str,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Execute every gate in registry order.

    Returns ``(gate_results, all_issues)`` in the same format produced
    by the legacy ``execute_validator()`` gate loop.
    """
    from ..workers.w9_validator.worker import ValidatorArtifactMissingError

    from .adapters import ADAPTER_DISPATCH
    from .context import GateContext
    from .gate_types import SkipGroup
    from .registry_loader import load_registry

    registry = load_registry()
    ctx = GateContext(run_dir, run_config, profile)

    gate_results: List[Dict[str, Any]] = []
    all_issues: List[Dict[str, Any]] = []

    for gate_def in registry:
        # ── skip-group cascade ────────────────────────────────────
        if (
            gate_def.skip_group == SkipGroup.ARTIFACT_BLOCK
            and ctx.artifact_block_skip
        ):
            gate_results.append({"name": gate_def.gate_id, "ok": True})
            continue

        adapter = ADAPTER_DISPATCH[gate_def.runner_type]

        try:
            ok, issues = adapter(gate_def, ctx)
            gate_results.append({"name": gate_def.gate_id, "ok": ok})
            all_issues.extend(issues)

        except ValidatorArtifactMissingError:
            if gate_def.graceful_artifact_skip:
                # Gate 14: skip gracefully when artifacts are absent
                gate_results.append(
                    {"name": gate_def.gate_id, "ok": True}
                )
            elif gate_def.skip_group == SkipGroup.ARTIFACT_BLOCK:
                # Cascade: remaining artifact_block gates get skipped
                ctx.artifact_block_skip = True
                gate_results.append(
                    {"name": gate_def.gate_id, "ok": True}
                )
            else:
                raise

        except Exception as exc:
            if gate_def.skip_on_error:
                logger.warning(
                    "[W7] %s error (skipping): %s",
                    gate_def.gate_id,
                    exc,
                )
                gate_results.append(
                    {"name": gate_def.gate_id, "ok": True}
                )
            else:
                raise

    return gate_results, all_issues
