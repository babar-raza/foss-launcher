"""LLM provider client with deterministic settings and evidence capture.

Binding contract:
- specs/25_frameworks_and_dependencies.md (LangChain integration)
- specs/10_determinism_and_caching.md (Deterministic decoding, prompt hashing)
- specs/11_state_and_events.md (LLM call telemetry)

All LLM calls MUST be deterministic (temperature=0.0 by default).
Request/response pairs MUST be captured for evidence and audit.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from .http import http_post
from .llm_telemetry import LLMTelemetryContext
from ..state.event_log import generate_trace_id
from ..util.logging import get_logger

logger = get_logger()

# Import TelemetryClient type for type hints (avoid circular import at runtime)
if False:  # TYPE_CHECKING
    from .telemetry import TelemetryClient


class LLMError(Exception):
    """Raised when LLM operation fails."""
    pass


class LLMProviderClient:
    """Client for OpenAI-compatible LLM provider with deterministic settings.

    Features:
    - Deterministic decoding (temperature=0.0 by default)
    - Prompt hashing for cache keys and telemetry
    - Request/response capture for evidence
    - Token usage tracking
    - Latency measurement
    - Structured output support
    - Optional fallback endpoint for transient failures

    Spec: specs/25_frameworks_and_dependencies.md
    """

    def __init__(
        self,
        api_base_url: str,
        model: str,
        run_dir: Path,
        api_key: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
        timeout: int = 120,
        evidence_dir: Optional[Path] = None,
        telemetry_client: Optional[Any] = None,
        telemetry_run_id: Optional[str] = None,
        telemetry_trace_id: Optional[str] = None,
        telemetry_parent_span_id: Optional[str] = None,
        fallback_api_base_url: Optional[str] = None,
        fallback_model: Optional[str] = None,
        fallback_api_key: Optional[str] = None,
        fallback_timeout: Optional[int] = None,
    ):
        """Initialize LLM provider client.

        Args:
            api_base_url: Base URL for OpenAI-compatible API
            model: Model name (e.g., claude-sonnet-4-5, gpt-4)
            run_dir: RUN_DIR for evidence storage
            api_key: Optional API key (read from env if not provided)
            temperature: Temperature (default: 0.0 for determinism)
            max_tokens: Optional max tokens
            timeout: Request timeout in seconds
            evidence_dir: Optional custom evidence directory (defaults to RUN_DIR/evidence/llm_calls)
            telemetry_client: Optional TelemetryClient for observability
            telemetry_run_id: Optional parent run ID for telemetry hierarchy
            telemetry_trace_id: Optional trace ID for distributed tracing
            telemetry_parent_span_id: Optional parent span ID for distributed tracing
            fallback_api_base_url: Optional fallback endpoint URL (used on transient primary failure)
            fallback_model: Optional fallback model name (defaults to primary model)
            fallback_api_key: Optional fallback API key
            fallback_timeout: Optional fallback timeout (defaults to primary timeout)
        """
        self.api_base_url = api_base_url.rstrip("/")
        self.model = model
        self.run_dir = Path(run_dir)
        self.api_key = api_key
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout

        # Fallback endpoint parameters
        self.fallback_api_base_url = fallback_api_base_url.rstrip("/") if fallback_api_base_url else None
        self.fallback_model = fallback_model
        self.fallback_api_key = fallback_api_key
        self.fallback_timeout = fallback_timeout or timeout

        # Telemetry parameters
        self.telemetry_client = telemetry_client
        self.telemetry_run_id = telemetry_run_id
        self.telemetry_trace_id = telemetry_trace_id
        self.telemetry_parent_span_id = telemetry_parent_span_id

        # Evidence directory
        if evidence_dir:
            self.evidence_dir = Path(evidence_dir)
        else:
            self.evidence_dir = self.run_dir / "evidence" / "llm_calls"

        self.evidence_dir.mkdir(parents=True, exist_ok=True)

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        call_id: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, Any]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Chat completion with evidence capture and telemetry tracking.

        Args:
            messages: List of message dicts (role, content)
            call_id: Optional call ID for evidence filename
            temperature: Optional temperature override
            max_tokens: Optional max_tokens override
            response_format: Optional response format (e.g., {"type": "json_object"})
            tools: Optional tool definitions for function calling

        Returns:
            Response dict with:
                - content: Response content (string)
                - prompt_hash: SHA256 hash of prompt
                - model: Model name
                - usage: Token usage dict
                - latency_ms: Latency in milliseconds
                - evidence_path: Path to evidence file
                - endpoint_used: "primary" or "fallback"

        Raises:
            LLMError: On API error
        """
        # Generate call_id if not provided
        if call_id is None:
            call_id = f"llm_call_{int(time.time() * 1000)}"

        # Compute prompt hash
        prompt_hash = self._hash_prompt(messages, tools)

        # Determine event log path (if telemetry enabled)
        events_file = None
        if self.telemetry_run_id:
            events_file = self.run_dir / "events.ndjson"

        # Determine evidence path for telemetry context
        evidence_path_str = f"evidence/llm_calls/{call_id}.json"

        # Effective temperature and max_tokens
        effective_temperature = temperature if temperature is not None else self.temperature
        effective_max_tokens = max_tokens if max_tokens is not None else self.max_tokens

        # Wrap LLM call with telemetry context
        with LLMTelemetryContext(
            telemetry_client=self.telemetry_client,
            event_log_path=events_file,
            call_id=call_id,
            run_id=self.telemetry_run_id or "unknown",
            trace_id=self.telemetry_trace_id or generate_trace_id(),
            parent_span_id=self.telemetry_parent_span_id or "root",
            model=self.model,
            temperature=effective_temperature,
            max_tokens=effective_max_tokens or 4096,
            prompt_hash=prompt_hash,
            evidence_path=evidence_path_str,
        ) as telemetry:
            start_time = time.time()

            # Build request payload
            request_payload = {
                "model": self.model,
                "messages": messages,
                "temperature": effective_temperature,
            }

            if effective_max_tokens is not None:
                request_payload["max_tokens"] = effective_max_tokens

            if response_format:
                request_payload["response_format"] = response_format

            if tools:
                request_payload["tools"] = tools

            # Make API call with fallback
            endpoint_used = "primary"
            fallback_reason = None
            try:
                response_data = self._call_api(request_payload)
            except Exception as primary_error:
                response_data, endpoint_used, fallback_reason = (
                    self._try_fallback(request_payload, primary_error)
                )
                if response_data is None:
                    logger.error("llm_call_failed", call_id=call_id, error=str(primary_error))
                    raise LLMError(f"LLM API call failed: {str(primary_error)}")

            end_time = time.time()
            latency_ms = int((end_time - start_time) * 1000)

            # Determine actual model used
            actual_model = self.fallback_model or self.model if endpoint_used == "fallback" else self.model

            # Extract response content
            try:
                content = response_data["choices"][0]["message"]["content"]
                usage = response_data.get("usage", {})
            except (KeyError, IndexError) as e:
                raise LLMError(f"Invalid LLM response structure: {str(e)}")

            # Record telemetry usage
            # Convert usage keys to match telemetry schema
            telemetry_usage = {
                "input_tokens": usage.get("prompt_tokens", usage.get("input_tokens", 0)),
                "output_tokens": usage.get("completion_tokens", usage.get("output_tokens", 0)),
                "total_tokens": usage.get("total_tokens", 0),
                "prompt_tokens": usage.get("prompt_tokens", usage.get("input_tokens", 0)),
                "completion_tokens": usage.get("completion_tokens", usage.get("output_tokens", 0)),
                "finish_reason": response_data["choices"][0].get("finish_reason", "stop"),
                "output_hash": hashlib.sha256(content.encode("utf-8")).hexdigest(),
            }
            telemetry.record_usage(telemetry_usage)

            # Save evidence
            evidence_path = self._save_evidence(
                call_id=call_id,
                request=request_payload,
                response=response_data,
                prompt_hash=prompt_hash,
                latency_ms=latency_ms,
                endpoint_used=endpoint_used,
                fallback_reason=fallback_reason,
            )

            # Build result
            finish_reason = response_data["choices"][0].get("finish_reason", "stop")
            result = {
                "content": content,
                "prompt_hash": prompt_hash,
                "model": actual_model,
                "usage": usage,
                "latency_ms": latency_ms,
                "evidence_path": str(evidence_path),
                "endpoint_used": endpoint_used,
                "finish_reason": finish_reason,
            }

            # Include tool calls if present
            if "tool_calls" in response_data["choices"][0]["message"]:
                result["tool_calls"] = response_data["choices"][0]["message"]["tool_calls"]

            return result

    def _try_fallback(
        self,
        request_payload: Dict[str, Any],
        primary_error: Exception,
    ) -> tuple:
        """Attempt fallback endpoint on transient primary failure.

        Args:
            request_payload: Original request payload
            primary_error: Exception from primary endpoint

        Returns:
            Tuple of (response_data, endpoint_used, fallback_reason).
            response_data is None if fallback is not available or also fails.
        """
        if not self.fallback_api_base_url:
            return None, "primary", None

        # Check for HTTP 4xx client errors (permanent - don't fallback)
        # Error format from _call_endpoint: "LLM API error (NNN): ..."
        error_msg = str(primary_error)
        status_match = re.search(r"LLM API error \((\d{3})\)", error_msg)
        if status_match:
            status_code = int(status_match.group(1))
            if 400 <= status_code < 500 and status_code != 429:
                # 4xx errors (except 429 rate limit) are permanent - no fallback
                logger.warning(
                    "llm_primary_client_error_no_fallback",
                    error=error_msg,
                    status_code=status_code,
                )
                return None, "primary", None

        # Classify the failure to decide if fallback is appropriate
        from ..resilience.retry_policy import classify_failure
        classification = classify_failure(primary_error)

        if not classification.is_transient:
            logger.warning(
                "llm_primary_permanent_failure_no_fallback",
                error=str(primary_error),
                reason=classification.reason,
            )
            return None, "primary", None

        logger.warning(
            "llm_primary_endpoint_failed_falling_back",
            primary_url=self.api_base_url,
            fallback_url=self.fallback_api_base_url,
            error=str(primary_error),
            reason=classification.reason,
        )

        # Swap model in payload for fallback if a different model is configured
        fallback_payload = dict(request_payload)
        if self.fallback_model:
            fallback_payload["model"] = self.fallback_model

        try:
            response_data = self._call_endpoint(
                base_url=self.fallback_api_base_url,
                api_key=self.fallback_api_key,
                timeout=self.fallback_timeout,
                request_payload=fallback_payload,
            )
            logger.info(
                "llm_fallback_succeeded",
                fallback_url=self.fallback_api_base_url,
                fallback_model=self.fallback_model or self.model,
            )
            return response_data, "fallback", str(primary_error)
        except Exception as fallback_error:
            logger.error(
                "llm_fallback_also_failed",
                fallback_url=self.fallback_api_base_url,
                fallback_error=str(fallback_error),
                primary_error=str(primary_error),
            )
            return None, "primary", None

    def _hash_prompt(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """Compute deterministic hash of prompt and tools.

        Args:
            messages: Message list
            tools: Optional tool definitions

        Returns:
            SHA256 hash (hex string)
        """
        # Build stable representation
        components = {
            "messages": messages,
            "model": self.model,
            "temperature": self.temperature,
        }

        if tools:
            components["tools"] = tools

        # Stable JSON serialization
        json_str = json.dumps(components, ensure_ascii=False, sort_keys=True)

        # Hash
        return hashlib.sha256(json_str.encode("utf-8")).hexdigest()

    def _call_api(self, request_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Call primary OpenAI-compatible API endpoint.

        Args:
            request_payload: Request payload

        Returns:
            Response data dict

        Raises:
            Exception: On API error
        """
        return self._call_endpoint(
            base_url=self.api_base_url,
            api_key=self.api_key,
            timeout=self.timeout,
            request_payload=request_payload,
        )

    def _call_endpoint(
        self,
        base_url: str,
        api_key: Optional[str],
        timeout: int,
        request_payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Call a specific OpenAI-compatible API endpoint.

        Args:
            base_url: API base URL
            api_key: API key (or None)
            timeout: Request timeout in seconds
            request_payload: Request payload

        Returns:
            Response data dict

        Raises:
            Exception: On API error
        """
        url = f"{base_url.rstrip('/')}/chat/completions"

        headers = {
            "Content-Type": "application/json",
        }

        # Add API key: explicit > litellm_key > ANTHROPIC_API_KEY > OPENAI_API_KEY
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        elif "litellm_key" in os.environ:
            headers["Authorization"] = f"Bearer {os.environ['litellm_key']}"
        elif "ANTHROPIC_API_KEY" in os.environ:
            headers["Authorization"] = f"Bearer {os.environ['ANTHROPIC_API_KEY']}"
        elif "OPENAI_API_KEY" in os.environ:
            headers["Authorization"] = f"Bearer {os.environ['OPENAI_API_KEY']}"

        # Make request
        json_data = json.dumps(request_payload, ensure_ascii=False, sort_keys=True)

        response = http_post(
            url,
            data=json_data,
            headers=headers,
            timeout=timeout,
        )

        if response.status_code != 200:
            raise Exception(
                f"LLM API error ({response.status_code}): {response.text}"
            )

        return response.json()

    def _save_evidence(
        self,
        call_id: str,
        request: Dict[str, Any],
        response: Dict[str, Any],
        prompt_hash: str,
        latency_ms: int,
        endpoint_used: str = "primary",
        fallback_reason: Optional[str] = None,
    ) -> Path:
        """Save request/response evidence to disk.

        Args:
            call_id: Call identifier
            request: Request payload
            response: Response data
            prompt_hash: Prompt hash
            latency_ms: Latency in milliseconds
            endpoint_used: "primary" or "fallback"
            fallback_reason: Reason for fallback (if fallback was used)

        Returns:
            Path to evidence file
        """
        evidence_file = self.evidence_dir / f"{call_id}.json"

        evidence = {
            "call_id": call_id,
            "prompt_hash": prompt_hash,
            "model": self.model,
            "temperature": self.temperature,
            "latency_ms": latency_ms,
            "request": request,
            "response": response,
            "timestamp": time.time(),
            "endpoint_used": endpoint_used,
        }

        if fallback_reason:
            evidence["fallback_reason"] = fallback_reason

        # Write atomically
        tmp_file = evidence_file.with_suffix(".json.tmp")
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(evidence, f, ensure_ascii=False, indent=2, sort_keys=True)

        os.replace(tmp_file, evidence_file)

        logger.info(
            "llm_evidence_saved",
            call_id=call_id,
            evidence_path=str(evidence_file),
            endpoint_used=endpoint_used,
        )

        return evidence_file

    def get_prompt_version(self, messages: List[Dict[str, str]]) -> str:
        """Get prompt version (hash) for telemetry.

        Args:
            messages: Message list

        Returns:
            Prompt hash (hex string)
        """
        return self._hash_prompt(messages, None)


def _resolve_api_key(api_key_env: Optional[str] = None) -> Optional[str]:
    """Resolve API key from config env var name or well-known env vars.

    Priority: api_key_env > litellm_key > ANTHROPIC_API_KEY > OPENAI_API_KEY

    Args:
        api_key_env: Optional env var name from config (e.g., "litellm_key")

    Returns:
        API key string or None
    """
    if api_key_env:
        key = os.environ.get(api_key_env)
        if key:
            return key

    # Well-known fallback chain
    for env_var in ("litellm_key", "ANTHROPIC_API_KEY", "OPENAI_API_KEY"):
        key = os.environ.get(env_var)
        if key:
            return key

    return None


def create_llm_client_from_config(
    run_config: Dict[str, Any],
    run_dir: Path,
    telemetry_client: Optional[Any] = None,
    telemetry_run_id: Optional[str] = None,
    telemetry_trace_id: Optional[str] = None,
    telemetry_parent_span_id: Optional[str] = None,
) -> Optional[LLMProviderClient]:
    """Create LLMProviderClient from run_config with fallback support.

    Centralizes LLM client construction for all workers (W2, W5, W5.5, W8).
    Reads from run_config["llm"] and optional run_config["llm"]["fallback"].

    Args:
        run_config: Full run config dict (must have "llm" key)
        run_dir: RUN_DIR for evidence storage
        telemetry_client: Optional TelemetryClient
        telemetry_run_id: Optional run ID
        telemetry_trace_id: Optional trace ID
        telemetry_parent_span_id: Optional parent span ID

    Returns:
        Configured LLMProviderClient, or None if LLM config is missing/empty.
    """
    llm_cfg = run_config.get("llm")
    if not llm_cfg or not llm_cfg.get("api_base_url"):
        return None

    # Primary API key
    api_key = _resolve_api_key(llm_cfg.get("api_key_env"))

    if api_key is None:
        logger.warning(
            "llm_client_no_api_key",
            api_base_url=llm_cfg["api_base_url"],
            model=llm_cfg["model"],
            api_key_env_config=llm_cfg.get("api_key_env", "not_set"),
            message="No API key resolved. LLM calls will fail unless endpoint accepts unauthenticated requests. "
                    "Set one of: litellm_key, ANTHROPIC_API_KEY, or OPENAI_API_KEY environment variables.",
        )

    # Fallback config
    fallback_cfg = llm_cfg.get("fallback", {})
    fallback_api_key = None
    if fallback_cfg.get("api_base_url"):
        fallback_api_key = _resolve_api_key(fallback_cfg.get("api_key_env"))

    decoding = llm_cfg.get("decoding", {})

    return LLMProviderClient(
        api_base_url=llm_cfg["api_base_url"],
        model=llm_cfg["model"],
        run_dir=run_dir,
        api_key=api_key,
        temperature=decoding.get("temperature", 0.0),
        max_tokens=decoding.get("max_tokens"),
        timeout=llm_cfg.get("request_timeout_s", 120),
        telemetry_client=telemetry_client,
        telemetry_run_id=telemetry_run_id,
        telemetry_trace_id=telemetry_trace_id,
        telemetry_parent_span_id=telemetry_parent_span_id,
        fallback_api_base_url=fallback_cfg.get("api_base_url"),
        fallback_model=fallback_cfg.get("model"),
        fallback_api_key=fallback_api_key,
        fallback_timeout=fallback_cfg.get("request_timeout_s"),
    )


class LangChainLLMAdapter:
    """Adapter for LangChain integration.

    This adapter wraps LLMProviderClient for use with LangChain pipelines.
    It provides a LangChain-compatible interface while maintaining determinism
    and evidence capture.

    Usage:
        >>> client = LLMProviderClient(...)
        >>> adapter = LangChainLLMAdapter(client)
        >>> # Use adapter in LangChain chains
    """

    def __init__(self, client: LLMProviderClient):
        """Initialize adapter with LLMProviderClient.

        Args:
            client: Configured LLMProviderClient instance
        """
        self.client = client

    def __call__(self, messages: List[Dict[str, str]], **kwargs: Any) -> str:
        """Invoke LLM with messages (LangChain interface).

        Args:
            messages: Message list
            **kwargs: Additional arguments (temperature, max_tokens, etc.)

        Returns:
            Response content string
        """
        result = self.client.chat_completion(messages, **kwargs)
        return result["content"]

    def bind_tools(self, tools: List[Dict[str, Any]]) -> LangChainLLMAdapter:
        """Bind tools for function calling (LangChain interface).

        Args:
            tools: Tool definitions

        Returns:
            Self (for chaining)
        """
        # Store tools for next invocation
        self._bound_tools = tools
        return self

    def invoke(self, messages: List[Dict[str, str]], **kwargs: Any) -> Dict[str, Any]:
        """Invoke LLM with full response (LangChain interface).

        Args:
            messages: Message list
            **kwargs: Additional arguments

        Returns:
            Full response dict
        """
        if hasattr(self, "_bound_tools"):
            kwargs["tools"] = self._bound_tools

        return self.client.chat_completion(messages, **kwargs)
