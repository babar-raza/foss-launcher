"""Resilience module for failure recovery and backoff.

Provides retry policies, checkpoint management, and circuit breaker
for robust pipeline execution.

Spec: specs/11_state_and_events.md, specs/28_coordination_and_handoffs.md
"""

from __future__ import annotations

from .circuit_breaker import (
    CallRecord,
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
    build_circuit_breaker_from_config,
)
from .checkpoint import (
    Checkpoint,
    WorkerCheckpoint,
    cleanup_old_checkpoints,
    create_checkpoint,
    load_worker_checkpoint,
    restore_worker_checkpoint,
    write_worker_checkpoint,
)
from .retry_policy import (
    FailureClassification,
    RetryConfig,
    RetryContext,
    classify_failure,
    retry_with_backoff,
)

__all__ = [
    "CallRecord",
    "Checkpoint",
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitState",
    "FailureClassification",
    "RetryConfig",
    "RetryContext",
    "WorkerCheckpoint",
    "build_circuit_breaker_from_config",
    "classify_failure",
    "cleanup_old_checkpoints",
    "create_checkpoint",
    "load_worker_checkpoint",
    "restore_worker_checkpoint",
    "retry_with_backoff",
    "write_worker_checkpoint",
]
