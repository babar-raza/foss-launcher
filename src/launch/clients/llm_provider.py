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
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..util.logging import get_logger

logger = get_logger()


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
        """
        self.api_base_url = api_base_url.rstrip("/")
        self.model = model
        self.run_dir = Path(run_dir)
        self.api_key = api_key
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout

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
        """Chat completion with evidence capture.

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

        Raises:
            LLMError: On API error
        """
        start_time = time.time()

        # Generate call_id if not provided
        if call_id is None:
            call_id = f"llm_call_{int(time.time() * 1000)}"

        # Compute prompt hash
        prompt_hash = self._hash_prompt(messages, tools)

        # Build request payload
        request_payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature if temperature is not None else self.temperature,
        }

        if max_tokens is not None or self.max_tokens is not None:
            request_payload["max_tokens"] = max_tokens if max_tokens is not None else self.max_tokens

        if response_format:
            request_payload["response_format"] = response_format

        if tools:
            request_payload["tools"] = tools

        # Make API call
        try:
            response_data = self._call_api(request_payload)
        except Exception as e:
            logger.error("llm_call_failed", call_id=call_id, error=str(e))
            raise LLMError(f"LLM API call failed: {str(e)}")

        end_time = time.time()
        latency_ms = int((end_time - start_time) * 1000)

        # Extract response content
        try:
            content = response_data["choices"][0]["message"]["content"]
            usage = response_data.get("usage", {})
        except (KeyError, IndexError) as e:
            raise LLMError(f"Invalid LLM response structure: {str(e)}")

        # Save evidence
        evidence_path = self._save_evidence(
            call_id=call_id,
            request=request_payload,
            response=response_data,
            prompt_hash=prompt_hash,
            latency_ms=latency_ms,
        )

        # Build result
        result = {
            "content": content,
            "prompt_hash": prompt_hash,
            "model": self.model,
            "usage": usage,
            "latency_ms": latency_ms,
            "evidence_path": str(evidence_path),
        }

        # Include tool calls if present
        if "tool_calls" in response_data["choices"][0]["message"]:
            result["tool_calls"] = response_data["choices"][0]["message"]["tool_calls"]

        return result

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
        """Call OpenAI-compatible API.

        Args:
            request_payload: Request payload

        Returns:
            Response data dict

        Raises:
            Exception: On API error
        """
        url = f"{self.api_base_url}/chat/completions"

        headers = {
            "Content-Type": "application/json",
        }

        # Add API key if provided
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        elif "ANTHROPIC_API_KEY" in os.environ:
            headers["Authorization"] = f"Bearer {os.environ['ANTHROPIC_API_KEY']}"
        elif "OPENAI_API_KEY" in os.environ:
            headers["Authorization"] = f"Bearer {os.environ['OPENAI_API_KEY']}"

        # Make request
        from .http import http_post

        json_data = json.dumps(request_payload, ensure_ascii=False, sort_keys=True)

        response = http_post(
            url,
            data=json_data,
            headers=headers,
            timeout=self.timeout,
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
    ) -> Path:
        """Save request/response evidence to disk.

        Args:
            call_id: Call identifier
            request: Request payload
            response: Response data
            prompt_hash: Prompt hash
            latency_ms: Latency in milliseconds

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
        }

        # Write atomically
        tmp_file = evidence_file.with_suffix(".json.tmp")
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(evidence, f, ensure_ascii=False, indent=2, sort_keys=True)

        os.replace(tmp_file, evidence_file)

        logger.info(
            "llm_evidence_saved",
            call_id=call_id,
            evidence_path=str(evidence_file),
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
