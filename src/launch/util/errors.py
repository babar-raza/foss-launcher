from __future__ import annotations


class LaunchError(RuntimeError):
    """Base error for launcher failures."""


class ConfigError(LaunchError):
    """Raised when a run_config is missing, invalid, or fails schema validation."""


class ToolchainError(LaunchError):
    """Raised when config/toolchain.lock.yaml is missing or invalid."""


class ValidationError(LaunchError):
    """Raised when a validation gate fails or cannot be executed."""
