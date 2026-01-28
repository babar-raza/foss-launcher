"""
Retry policy with exponential backoff and failure classification.

Implements configurable retry logic with:
- Exponential backoff (base_delay * multiplier^attempt)
- Deterministic jitter (seed-based for reproducibility)
- Failure classification (transient vs. permanent)
- Max retry limits and delay caps

Spec: specs/28_coordination_and_handoffs.md (retry policy)
"""

import functools
import logging
import random
import time
from dataclasses import dataclass
from typing import Any, Callable, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class RetryConfig:
    """Configuration for retry policy."""

    max_retries: int = 3
    base_delay_seconds: float = 1.0
    multiplier: float = 2.0
    max_delay_seconds: float = 60.0
    jitter_seed: Optional[int] = None  # For deterministic jitter


@dataclass
class RetryContext:
    """Context for a retry operation."""

    operation_name: str
    attempt: int
    last_error: Optional[Exception]
    next_delay_seconds: float


@dataclass
class FailureClassification:
    """Classification of a failure."""

    error: Exception
    is_transient: bool  # True if retryable
    reason: str
    suggested_action: str  # "retry", "fail", "manual_intervention"


def calculate_backoff(
    attempt: int,
    base_delay: float,
    multiplier: float,
    max_delay: float,
    jitter_seed: Optional[int] = None,
) -> float:
    """
    Calculate backoff delay with exponential backoff and optional jitter.

    Formula: delay = min(base_delay * (multiplier ** attempt), max_delay) + jitter
    Jitter is 0-50% of the delay, deterministic if seed provided.

    Args:
        attempt: Current attempt number (0-indexed)
        base_delay: Base delay in seconds
        multiplier: Exponential multiplier
        max_delay: Maximum delay cap in seconds
        jitter_seed: Optional seed for deterministic jitter

    Returns:
        Delay in seconds
    """
    # Exponential backoff
    delay = base_delay * (multiplier**attempt)
    delay = min(delay, max_delay)

    # Add jitter (0-50% of delay)
    if jitter_seed is not None:
        # Deterministic jitter based on seed + attempt
        rng = random.Random(jitter_seed + attempt)
        jitter = delay * 0.5 * rng.random()
    else:
        jitter = delay * 0.5 * random.random()

    return delay + jitter


def classify_failure(error: Exception) -> FailureClassification:
    """
    Classify a failure as transient (retryable) or permanent (fail-fast).

    Transient failures:
    - Network errors (ConnectionError, Timeout, URLError)
    - API rate limits (HTTP 429, RateLimitError)
    - Temporary file locks (PermissionError, EAGAIN)
    - Service unavailable (HTTP 503, 504)

    Permanent failures:
    - Invalid input (ValueError, TypeError)
    - Schema validation errors
    - Logic errors (AssertionError)
    - File not found (permanent)

    Args:
        error: Exception to classify

    Returns:
        FailureClassification with suggested action
    """
    error_type = type(error).__name__
    error_msg = str(error).lower()

    # Network errors (transient)
    if error_type in [
        "ConnectionError",
        "Timeout",
        "TimeoutError",
        "URLError",
        "HTTPError",
    ]:
        return FailureClassification(
            error=error,
            is_transient=True,
            reason="Network error - temporary connectivity issue",
            suggested_action="retry",
        )

    # Rate limiting (transient)
    if error_type == "RateLimitError" or "429" in error_msg or "rate limit" in error_msg:
        return FailureClassification(
            error=error,
            is_transient=True,
            reason="API rate limit - temporary throttling",
            suggested_action="retry",
        )

    # Service unavailable (transient)
    if "503" in error_msg or "504" in error_msg or "service unavailable" in error_msg:
        return FailureClassification(
            error=error,
            is_transient=True,
            reason="Service unavailable - temporary outage",
            suggested_action="retry",
        )

    # File system temporary errors (transient)
    if error_type == "PermissionError" or "eagain" in error_msg or "ewouldblock" in error_msg:
        return FailureClassification(
            error=error,
            is_transient=True,
            reason="Temporary file lock or permission issue",
            suggested_action="retry",
        )

    # Schema validation (permanent)
    if "validation" in error_msg or "schema" in error_msg or error_type == "ValidationError":
        return FailureClassification(
            error=error,
            is_transient=False,
            reason="Schema validation failure - invalid data structure",
            suggested_action="fail",
        )

    # Invalid input (permanent)
    if error_type in ["ValueError", "TypeError", "KeyError", "AttributeError"]:
        return FailureClassification(
            error=error,
            is_transient=False,
            reason="Invalid input or logic error",
            suggested_action="fail",
        )

    # Assertion errors (permanent)
    if error_type == "AssertionError":
        return FailureClassification(
            error=error,
            is_transient=False,
            reason="Assertion failed - logic error",
            suggested_action="fail",
        )

    # File not found (permanent)
    if error_type == "FileNotFoundError":
        return FailureClassification(
            error=error,
            is_transient=False,
            reason="File not found - missing required resource",
            suggested_action="fail",
        )

    # Default: treat as transient but require manual intervention
    return FailureClassification(
        error=error,
        is_transient=True,
        reason="Unknown error type - defaulting to retryable",
        suggested_action="manual_intervention",
    )


def retry_with_backoff(
    config: Optional[RetryConfig] = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator for retrying operations with exponential backoff.

    Usage:
        @retry_with_backoff(RetryConfig(max_retries=5))
        def fetch_data():
            return requests.get("https://api.example.com")

    Args:
        config: RetryConfig instance (uses defaults if None)

    Returns:
        Decorated function with retry logic
    """
    if config is None:
        config = RetryConfig()

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_error: Optional[Exception] = None

            for attempt in range(config.max_retries + 1):
                try:
                    result = func(*args, **kwargs)
                    if attempt > 0:
                        logger.info(
                            f"Operation {func.__name__} succeeded on attempt {attempt + 1}"
                        )
                    return result

                except Exception as e:
                    last_error = e
                    classification = classify_failure(e)

                    # If permanent failure, don't retry
                    if not classification.is_transient:
                        logger.error(
                            f"Permanent failure in {func.__name__}: {classification.reason}"
                        )
                        raise

                    # If max retries reached, give up
                    if attempt >= config.max_retries:
                        logger.error(
                            f"Max retries ({config.max_retries}) exceeded for {func.__name__}"
                        )
                        raise

                    # Calculate backoff and retry
                    delay = calculate_backoff(
                        attempt=attempt,
                        base_delay=config.base_delay_seconds,
                        multiplier=config.multiplier,
                        max_delay=config.max_delay_seconds,
                        jitter_seed=config.jitter_seed,
                    )

                    logger.warning(
                        f"Attempt {attempt + 1}/{config.max_retries + 1} failed for {func.__name__}: "
                        f"{classification.reason}. Retrying in {delay:.2f}s..."
                    )

                    time.sleep(delay)

            # Should never reach here, but for type safety
            if last_error:
                raise last_error
            raise RuntimeError(f"Retry logic failed for {func.__name__}")

        return wrapper

    return decorator
