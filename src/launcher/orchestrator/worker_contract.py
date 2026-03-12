"""Abstract worker contract and runtime context for the v2 pipeline.

Every pipeline worker implements WorkerContract. The orchestrator calls
run() then self_review() and validates inputs/outputs against JSON schemas
at every boundary (Rule 9: schema validation everywhere).
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from pydantic import Field

from launcher.io.artifact_store import ArtifactStore
from launcher.models.base import LauncherBaseModel
from launcher.models.run_config import LLMConfig, RunConfig

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Self-review result (Rule 1: every worker reviews its own work)
# ---------------------------------------------------------------------------


class SelfReviewResult(LauncherBaseModel):
    """Outcome of a worker's semantic self-review.

    A worker that passes self-review emits ``passed=True`` and may still
    include informational findings.  A failure triggers root-cause
    re-generation (Rule 6) rather than patching.
    """

    passed: bool = True
    findings: list[dict[str, Any]] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Worker context — runtime bag passed to every worker
# ---------------------------------------------------------------------------


class WorkerContext:
    """Runtime context injected into every worker invocation.

    This object is *not* a Pydantic model — it carries mutable runtime
    handles (artifact store, logger, etc.) that should not be serialised
    into the LangGraph state dict.
    """

    def __init__(
        self,
        run_id: str,
        run_dir: Path,
        config: RunConfig,
        *,
        llm_config: LLMConfig | None = None,
        schemas_dir: Path | None = None,
        telemetry_client: Any | None = None,
        telemetry_trace_id: str = "",
        heal_metadata: dict[str, Any] | None = None,
        heal_target_pages: list[str] | None = None,
        eval_fast_path: bool = False,
    ) -> None:
        self._run_id = run_id
        self._run_dir = run_dir
        self._config = config
        self._llm_config = llm_config or config.llm
        self._schemas_dir = schemas_dir
        self._store = ArtifactStore(run_dir=run_dir, schemas_dir=schemas_dir)
        self._logger = logging.getLogger(f"launcher.worker.{run_id}")
        self._repo_dir: Path | None = None
        self._repo_content: dict[str, str] = {}
        self._telemetry_client = telemetry_client
        self._telemetry_trace_id = telemetry_trace_id
        self._heal_metadata: dict[str, Any] = heal_metadata or {}
        self._heal_target_pages: list[str] | None = heal_target_pages
        self._eval_fast_path: bool = eval_fast_path

    # -- read-only properties ------------------------------------------------

    @property
    def run_id(self) -> str:
        return self._run_id

    @property
    def run_dir(self) -> Path:
        return self._run_dir

    @property
    def config(self) -> RunConfig:
        return self._config

    @property
    def llm_config(self) -> LLMConfig | None:
        return self._llm_config

    @property
    def schemas_dir(self) -> Path | None:
        return self._schemas_dir

    @property
    def store(self) -> ArtifactStore:
        """Artifact store for loading/writing run artifacts."""
        return self._store

    @property
    def log(self) -> logging.Logger:
        return self._logger

    @property
    def repo_dir(self) -> Path | None:
        """Path to the cloned repository (set from IntakeBundle by Understand worker)."""
        return self._repo_dir

    @repo_dir.setter
    def repo_dir(self, value: Path | None) -> None:
        self._repo_dir = value

    @property
    def repo_content(self) -> dict[str, str]:
        """Bulk-read repository content: {rel_path: text_content}."""
        return self._repo_content

    @repo_content.setter
    def repo_content(self, value: dict[str, str]) -> None:
        self._repo_content = value

    @property
    def telemetry_client(self) -> Any | None:
        """Optional TelemetryClient for observability."""
        return self._telemetry_client

    @property
    def telemetry_trace_id(self) -> str:
        """Trace ID for distributed tracing across workers."""
        return self._telemetry_trace_id

    @property
    def heal_metadata(self) -> dict[str, Any]:
        """Heal directives injected by the heal CLI (empty dict in normal runs)."""
        return self._heal_metadata

    @property
    def heal_target_pages(self) -> list[str] | None:
        """Page IDs targeted for healing. None = all pages (normal mode)."""
        return self._heal_target_pages

    @property
    def eval_fast_path(self) -> bool:
        """When True, skip expensive LLM review in evaluate worker (heal fast-path)."""
        return self._eval_fast_path

    # -- convenience helpers -------------------------------------------------

    def emit_event(self, event_type: str, data: dict[str, Any], *, worker: str = "") -> None:
        """Shorthand for emitting a pipeline event."""
        self._store.emit_event(event_type, data, run_id=self._run_id, worker=worker)


# ---------------------------------------------------------------------------
# Abstract worker contract
# ---------------------------------------------------------------------------


class WorkerContract(ABC):
    """Abstract contract that every pipeline worker must implement.

    Workers are instantiated once and reused across re-runs within the
    same pipeline invocation.  They must be stateless between calls —
    all mutable state lives in ``WorkerContext``.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Worker name matching the ``worker:`` key in pipeline.yaml."""

    @abstractmethod
    async def run(
        self,
        input_data: LauncherBaseModel,
        context: WorkerContext,
    ) -> LauncherBaseModel:
        """Execute the worker's core logic.

        Parameters
        ----------
        input_data:
            Validated input model (deserialized from the previous worker's
            output or the initial RunConfig).
        context:
            Runtime context with run directory, config, artifact store, etc.

        Returns
        -------
        A validated Pydantic model representing this worker's output.
        """

    @abstractmethod
    async def self_review(self, output: LauncherBaseModel) -> SelfReviewResult:
        """Semantic self-review of worker output (Rule 1).

        This is *not* schema validation (that happens automatically at the
        orchestrator boundary). This checks domain-level correctness:

        - Are claims public-facing?
        - Do code examples compile/import correctly?
        - Is there enough unique material per page?

        A failed self-review causes the orchestrator to skip downstream
        workers and route to the evaluate worker, which will diagnose
        root cause and trigger re-generation (Rule 6).
        """
