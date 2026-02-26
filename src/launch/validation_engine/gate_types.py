"""Pure data containers for the gate registry system."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class RunnerType(Enum):
    """Callable convention used by a gate implementation."""

    EXECUTE_GATE = "execute_gate"
    INLINE_FN = "inline_fn"
    INLINE_VALIDATE_14 = "inline_validate_14"
    RUN_GATE_PAGES_16 = "run_gate_pages_16"
    RUN_GATE_PAGES = "run_gate_pages"
    RUN_GATE_MD_FILES = "run_gate_md_files"
    RUN_GATE_MD_FILES_LLM = "run_gate_md_files_llm"


class SkipGroup(Enum):
    """Gates sharing a skip-group are all skipped when a dependency fails."""

    ARTIFACT_BLOCK = "artifact_block"
    NONE = "none"


@dataclass(frozen=True)
class GateDefinition:
    """Immutable descriptor loaded from ``gates_registry.yaml``."""

    gate_id: str
    display_name: str
    order: int
    module: str
    callable_name: str
    runner_type: RunnerType
    skip_group: SkipGroup = SkipGroup.NONE
    skip_on_error: bool = False
    graceful_artifact_skip: bool = False
    inputs: tuple = ()  # type: ignore[assignment]
    notes: str = ""
    mandatory_profiles: tuple = ()  # TC-2870: profiles where this gate MUST pass


@dataclass
class GateResult:
    """Outcome of running a single gate."""

    gate_id: str
    ok: bool
    issues: List[Dict[str, Any]] = field(default_factory=list)
    skipped: bool = False
    error_message: Optional[str] = None
