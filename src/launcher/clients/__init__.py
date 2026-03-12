"""Client wrappers for external services.

Provides:
- TelemetryClient: Local telemetry API with outbox buffering
- CommitServiceClient: GitHub commit service with idempotency
- LLMProviderClient: OpenAI-compatible LLM with deterministic settings

Spec references:
- specs/16_local_telemetry_api.md (Telemetry)
- specs/17_github_commit_service.md (Commit service)
- specs/25_frameworks_and_dependencies.md (LLM provider)
"""

from .commit_service import CommitServiceClient, CommitServiceError
from .llm_provider import LangChainLLMAdapter, LLMError, LLMProviderClient
from .telemetry import TelemetryClient, TelemetryError

__all__ = [
    "TelemetryClient",
    "TelemetryError",
    "CommitServiceClient",
    "CommitServiceError",
    "LLMProviderClient",
    "LLMError",
    "LangChainLLMAdapter",
]
