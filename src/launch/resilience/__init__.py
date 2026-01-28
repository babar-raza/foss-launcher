"""
Resilience module for failure recovery and backoff.

Provides retry policies, checkpoint management, run resume, and idempotency
enforcement for robust distributed system execution.

Spec: specs/11_state_and_events.md, specs/28_coordination_and_handoffs.md
"""

from .retry_policy import (
    RetryConfig,
    RetryContext,
    FailureClassification,
    retry_with_backoff,
    classify_failure,
)
from .checkpoint import (
    Checkpoint,
    create_checkpoint,
    cleanup_old_checkpoints,
)
from .resume import (
    ResumeResult,
    resume_run,
)
from .idempotency import (
    is_idempotent_write,
    compute_content_hash,
)

__all__ = [
    "RetryConfig",
    "RetryContext",
    "FailureClassification",
    "retry_with_backoff",
    "classify_failure",
    "Checkpoint",
    "create_checkpoint",
    "cleanup_old_checkpoints",
    "ResumeResult",
    "resume_run",
    "is_idempotent_write",
    "compute_content_hash",
]
