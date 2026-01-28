"""
Tests for TC-600: Retry policy with exponential backoff.

Covers:
- Retry with exponential backoff
- Retry exhaustion
- Backoff calculation
- Deterministic jitter
- Failure classification
- Decorator usage
"""

import pytest
from unittest.mock import patch, MagicMock
from src.launch.resilience.retry_policy import (
    RetryConfig,
    RetryContext,
    FailureClassification,
    retry_with_backoff,
    classify_failure,
    calculate_backoff,
)


def test_calculate_backoff_no_jitter():
    """Test exponential backoff calculation without jitter."""
    config = RetryConfig(base_delay_seconds=1.0, multiplier=2.0, max_delay_seconds=60.0)

    # Attempt 0: 1.0 * 2^0 = 1.0 (+ jitter)
    delay0 = calculate_backoff(0, config.base_delay_seconds, config.multiplier, config.max_delay_seconds, jitter_seed=None)
    assert 1.0 <= delay0 <= 1.5  # Base 1.0 + up to 50% jitter

    # Attempt 1: 1.0 * 2^1 = 2.0 (+ jitter)
    delay1 = calculate_backoff(1, config.base_delay_seconds, config.multiplier, config.max_delay_seconds, jitter_seed=None)
    assert 2.0 <= delay1 <= 3.0

    # Attempt 2: 1.0 * 2^2 = 4.0 (+ jitter)
    delay2 = calculate_backoff(2, config.base_delay_seconds, config.multiplier, config.max_delay_seconds, jitter_seed=None)
    assert 4.0 <= delay2 <= 6.0


def test_calculate_backoff_deterministic_jitter():
    """Test deterministic jitter with fixed seed."""
    config = RetryConfig(base_delay_seconds=1.0, multiplier=2.0, jitter_seed=42)

    # Same seed should produce same delays
    delay1 = calculate_backoff(0, config.base_delay_seconds, config.multiplier, config.max_delay_seconds, jitter_seed=42)
    delay2 = calculate_backoff(0, config.base_delay_seconds, config.multiplier, config.max_delay_seconds, jitter_seed=42)
    assert delay1 == delay2

    # Different attempts should produce different delays (due to seed + attempt)
    delay_a0 = calculate_backoff(0, config.base_delay_seconds, config.multiplier, config.max_delay_seconds, jitter_seed=42)
    delay_a1 = calculate_backoff(1, config.base_delay_seconds, config.multiplier, config.max_delay_seconds, jitter_seed=42)
    assert delay_a0 != delay_a1


def test_calculate_backoff_max_delay_cap():
    """Test that backoff respects max_delay cap."""
    config = RetryConfig(base_delay_seconds=1.0, multiplier=2.0, max_delay_seconds=10.0)

    # Attempt 10: 1.0 * 2^10 = 1024.0, but should be capped at 10.0
    delay = calculate_backoff(10, config.base_delay_seconds, config.multiplier, config.max_delay_seconds, jitter_seed=42)
    assert delay <= 10.0 * 1.5  # Max delay + jitter


def test_classify_failure_network_error_transient():
    """Test classification of network errors as transient."""
    error = ConnectionError("Connection refused")
    classification = classify_failure(error)

    assert classification.is_transient is True
    assert classification.suggested_action == "retry"
    assert "network" in classification.reason.lower()


def test_classify_failure_rate_limit_transient():
    """Test classification of rate limit errors as transient."""
    # Test HTTP 429 in message
    error = Exception("HTTP 429: Rate limit exceeded")
    classification = classify_failure(error)

    assert classification.is_transient is True
    assert classification.suggested_action == "retry"
    assert "rate limit" in classification.reason.lower()


def test_classify_failure_service_unavailable_transient():
    """Test classification of service unavailable as transient."""
    error = Exception("HTTP 503: Service Unavailable")
    classification = classify_failure(error)

    assert classification.is_transient is True
    assert classification.suggested_action == "retry"
    assert "service unavailable" in classification.reason.lower()


def test_classify_failure_permission_error_transient():
    """Test classification of permission errors as transient (file locks)."""
    error = PermissionError("Access denied")
    classification = classify_failure(error)

    assert classification.is_transient is True
    assert classification.suggested_action == "retry"


def test_classify_failure_validation_error_permanent():
    """Test classification of validation errors as permanent."""
    error = ValueError("Schema validation failed")
    classification = classify_failure(error)

    assert classification.is_transient is False
    assert classification.suggested_action == "fail"


def test_classify_failure_value_error_permanent():
    """Test classification of ValueError as permanent."""
    error = ValueError("Invalid input value")
    classification = classify_failure(error)

    assert classification.is_transient is False
    assert classification.suggested_action == "fail"


def test_classify_failure_assertion_error_permanent():
    """Test classification of AssertionError as permanent."""
    error = AssertionError("Assertion failed")
    classification = classify_failure(error)

    assert classification.is_transient is False
    assert classification.suggested_action == "fail"


def test_classify_failure_file_not_found_permanent():
    """Test classification of FileNotFoundError as permanent."""
    error = FileNotFoundError("File not found")
    classification = classify_failure(error)

    assert classification.is_transient is False
    assert classification.suggested_action == "fail"


def test_classify_failure_unknown_error_manual_intervention():
    """Test classification of unknown errors defaults to manual intervention."""
    error = Exception("Unknown error type")
    classification = classify_failure(error)

    assert classification.is_transient is True  # Default to retryable
    assert classification.suggested_action == "manual_intervention"


@patch('time.sleep')
def test_retry_with_backoff_success_on_retry(mock_sleep):
    """Test successful retry after initial failure."""
    call_count = 0

    @retry_with_backoff(RetryConfig(max_retries=3, base_delay_seconds=1.0, jitter_seed=42))
    def flaky_operation():
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise ConnectionError("Network error")
        return "success"

    result = flaky_operation()

    assert result == "success"
    assert call_count == 2
    assert mock_sleep.call_count == 1  # One sleep between attempts


@patch('time.sleep')
def test_retry_with_backoff_exhaustion(mock_sleep):
    """Test retry exhaustion after max retries."""
    call_count = 0

    @retry_with_backoff(RetryConfig(max_retries=2, base_delay_seconds=1.0, jitter_seed=42))
    def always_fails():
        nonlocal call_count
        call_count += 1
        raise ConnectionError("Network error")

    with pytest.raises(ConnectionError):
        always_fails()

    assert call_count == 3  # Initial + 2 retries
    assert mock_sleep.call_count == 2  # Two sleeps


@patch('time.sleep')
def test_retry_with_backoff_permanent_failure_no_retry(mock_sleep):
    """Test that permanent failures don't trigger retries."""
    call_count = 0

    @retry_with_backoff(RetryConfig(max_retries=3, base_delay_seconds=1.0))
    def permanent_failure():
        nonlocal call_count
        call_count += 1
        raise ValueError("Invalid input")

    with pytest.raises(ValueError):
        permanent_failure()

    assert call_count == 1  # No retries for permanent failures
    assert mock_sleep.call_count == 0


@patch('time.sleep')
def test_retry_with_backoff_delay_progression(mock_sleep):
    """Test that delays increase with exponential backoff."""
    call_count = 0

    @retry_with_backoff(RetryConfig(max_retries=3, base_delay_seconds=1.0, multiplier=2.0, jitter_seed=42))
    def always_fails():
        nonlocal call_count
        call_count += 1
        raise ConnectionError("Network error")

    with pytest.raises(ConnectionError):
        always_fails()

    # Check that delays increase
    assert mock_sleep.call_count == 3
    delays = [call[0][0] for call in mock_sleep.call_args_list]

    # Each delay should be approximately double the previous (with jitter)
    # Attempt 0: ~1.0, Attempt 1: ~2.0, Attempt 2: ~4.0
    assert delays[0] >= 1.0 and delays[0] <= 1.5
    assert delays[1] >= 2.0 and delays[1] <= 3.0
    assert delays[2] >= 4.0 and delays[2] <= 6.0


def test_retry_with_backoff_default_config():
    """Test retry with default RetryConfig."""
    call_count = 0

    @retry_with_backoff()
    def flaky_with_defaults():
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise ConnectionError("Network error")
        return "success"

    with patch('time.sleep'):
        result = flaky_with_defaults()

    assert result == "success"
    assert call_count == 2


def test_retry_context_structure():
    """Test RetryContext dataclass structure."""
    context = RetryContext(
        operation_name="test_op",
        attempt=2,
        last_error=ValueError("test"),
        next_delay_seconds=4.0
    )

    assert context.operation_name == "test_op"
    assert context.attempt == 2
    assert isinstance(context.last_error, ValueError)
    assert context.next_delay_seconds == 4.0


def test_failure_classification_structure():
    """Test FailureClassification dataclass structure."""
    error = ValueError("test error")
    classification = FailureClassification(
        error=error,
        is_transient=False,
        reason="Invalid input",
        suggested_action="fail"
    )

    assert classification.error == error
    assert classification.is_transient is False
    assert classification.reason == "Invalid input"
    assert classification.suggested_action == "fail"


def test_retry_config_structure():
    """Test RetryConfig dataclass with custom values."""
    config = RetryConfig(
        max_retries=5,
        base_delay_seconds=2.0,
        multiplier=3.0,
        max_delay_seconds=120.0,
        jitter_seed=123
    )

    assert config.max_retries == 5
    assert config.base_delay_seconds == 2.0
    assert config.multiplier == 3.0
    assert config.max_delay_seconds == 120.0
    assert config.jitter_seed == 123
