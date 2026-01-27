"""Shared data models for FOSS Launcher.

This package implements foundational models used across the system.
Per TC-250, this is a **single-writer area** - only TC-250 may add new files.

Models provide:
- Stable serialization (to_dict/from_dict)
- Schema validation support
- Deterministic JSON output

Spec references:
- specs/11_state_and_events.md (State and Event models)
- specs/01_system_contract.md (Artifact contracts)
- specs/10_determinism_and_caching.md (Deterministic serialization)
"""

# Base classes
from .base import Artifact, BaseModel

# Event and state models
from .event import (
    EVENT_ARTIFACT_WRITTEN,
    EVENT_GATE_RUN_FINISHED,
    EVENT_GATE_RUN_STARTED,
    EVENT_INPUTS_CLONED,
    EVENT_ISSUE_OPENED,
    EVENT_ISSUE_RESOLVED,
    EVENT_LLM_CALL_FAILED,
    EVENT_LLM_CALL_FINISHED,
    EVENT_LLM_CALL_STARTED,
    EVENT_PR_OPENED,
    EVENT_RUN_COMPLETED,
    EVENT_RUN_CREATED,
    EVENT_RUN_FAILED,
    EVENT_RUN_STATE_CHANGED,
    EVENT_WORK_ITEM_FINISHED,
    EVENT_WORK_ITEM_QUEUED,
    EVENT_WORK_ITEM_STARTED,
    Event,
)
from .state import (
    RUN_STATE_CANCELLED,
    RUN_STATE_CLONED_INPUTS,
    RUN_STATE_CREATED,
    RUN_STATE_DONE,
    RUN_STATE_DRAFT_READY,
    RUN_STATE_DRAFTING,
    RUN_STATE_FACTS_READY,
    RUN_STATE_FAILED,
    RUN_STATE_FIXING,
    RUN_STATE_INGESTED,
    RUN_STATE_LINKING,
    RUN_STATE_PLAN_READY,
    RUN_STATE_PR_OPENED,
    RUN_STATE_READY_FOR_PR,
    RUN_STATE_VALIDATING,
    SECTION_STATE_BLOCKED,
    SECTION_STATE_DONE,
    SECTION_STATE_DRAFTED,
    SECTION_STATE_MERGED_IN_WORKTREE,
    SECTION_STATE_NOT_STARTED,
    SECTION_STATE_OUTLINED,
    WORK_ITEM_STATUS_FAILED,
    WORK_ITEM_STATUS_FINISHED,
    WORK_ITEM_STATUS_QUEUED,
    WORK_ITEM_STATUS_RUNNING,
    WORK_ITEM_STATUS_SKIPPED,
    ArtifactIndexEntry,
    Snapshot,
    WorkItem,
)

# Configuration models
from .run_config import RunConfig

# Artifact models
from .product_facts import EvidenceMap, ProductFacts

__all__ = [
    # Base
    "BaseModel",
    "Artifact",
    # Event
    "Event",
    "EVENT_RUN_CREATED",
    "EVENT_INPUTS_CLONED",
    "EVENT_ARTIFACT_WRITTEN",
    "EVENT_WORK_ITEM_QUEUED",
    "EVENT_WORK_ITEM_STARTED",
    "EVENT_WORK_ITEM_FINISHED",
    "EVENT_GATE_RUN_STARTED",
    "EVENT_GATE_RUN_FINISHED",
    "EVENT_ISSUE_OPENED",
    "EVENT_ISSUE_RESOLVED",
    "EVENT_RUN_STATE_CHANGED",
    "EVENT_PR_OPENED",
    "EVENT_RUN_COMPLETED",
    "EVENT_RUN_FAILED",
    "EVENT_LLM_CALL_STARTED",
    "EVENT_LLM_CALL_FINISHED",
    "EVENT_LLM_CALL_FAILED",
    # State
    "Snapshot",
    "WorkItem",
    "ArtifactIndexEntry",
    "RUN_STATE_CREATED",
    "RUN_STATE_CLONED_INPUTS",
    "RUN_STATE_INGESTED",
    "RUN_STATE_FACTS_READY",
    "RUN_STATE_PLAN_READY",
    "RUN_STATE_DRAFTING",
    "RUN_STATE_DRAFT_READY",
    "RUN_STATE_LINKING",
    "RUN_STATE_VALIDATING",
    "RUN_STATE_FIXING",
    "RUN_STATE_READY_FOR_PR",
    "RUN_STATE_PR_OPENED",
    "RUN_STATE_DONE",
    "RUN_STATE_FAILED",
    "RUN_STATE_CANCELLED",
    "SECTION_STATE_NOT_STARTED",
    "SECTION_STATE_OUTLINED",
    "SECTION_STATE_DRAFTED",
    "SECTION_STATE_MERGED_IN_WORKTREE",
    "SECTION_STATE_DONE",
    "SECTION_STATE_BLOCKED",
    "WORK_ITEM_STATUS_QUEUED",
    "WORK_ITEM_STATUS_RUNNING",
    "WORK_ITEM_STATUS_FINISHED",
    "WORK_ITEM_STATUS_FAILED",
    "WORK_ITEM_STATUS_SKIPPED",
    # Config
    "RunConfig",
    # Artifacts
    "ProductFacts",
    "EvidenceMap",
]
