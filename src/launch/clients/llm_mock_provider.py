"""Mock LLM provider for offline/deterministic testing.

Binding contract:
- specs/10_determinism_and_caching.md (Deterministic decoding)
- specs/11_state_and_events.md (Evidence capture)

Provides deterministic mock responses for E2E testing without external APIs.
"""

from __future__ import annotations

import hashlib
import json
import random
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


class MockLLMProvider:
    """Mock LLM provider for offline/deterministic testing.

    Features:
    - Seedable deterministic response generation
    - Prompt hash → stable response mapping
    - Evidence logging (same format as real provider)
    - Configurable response templates

    Usage:
        >>> provider = MockLLMProvider(seed=42, run_dir=Path("runs/test"))
        >>> response = provider.chat_completion(messages=[...])
    """

    def __init__(
        self,
        seed: int = 42,
        run_dir: Optional[Path] = None,
        evidence_dir: Optional[Path] = None,
    ):
        """Initialize mock LLM provider.

        Args:
            seed: Random seed for deterministic responses
            run_dir: Run directory for evidence storage
            evidence_dir: Optional custom evidence directory
        """
        self.seed = seed
        self.run_dir = Path(run_dir) if run_dir else Path.cwd() / "runs" / "mock"
        self.model = "mock-llm-v1"

        # Evidence directory
        if evidence_dir:
            self.evidence_dir = Path(evidence_dir)
        else:
            self.evidence_dir = self.run_dir / "evidence" / "llm_calls"

        self.evidence_dir.mkdir(parents=True, exist_ok=True)

        # Initialize RNG with seed
        self.rng = random.Random(seed)

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        call_id: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, Any]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Generate deterministic mock response.

        Args:
            messages: List of message dicts (role, content)
            call_id: Optional call ID for evidence filename
            temperature: Ignored (mock is always deterministic)
            max_tokens: Ignored
            response_format: Optional response format hint
            tools: Optional tool definitions (ignored)

        Returns:
            Response dict with:
                - content: Mock response content
                - prompt_hash: SHA256 hash of prompt
                - model: "mock-llm-v1"
                - usage: Mock token usage
                - latency_ms: Mock latency (0-10ms)
                - evidence_path: Path to evidence file
        """
        start_time = time.time()

        # Generate call_id if not provided
        if call_id is None:
            call_id = f"mock_llm_call_{int(time.time() * 1000)}"

        # Compute prompt hash for deterministic seeding
        prompt_hash = self._hash_prompt(messages)

        # Generate deterministic response based on prompt hash
        content = self._generate_response(messages, prompt_hash, response_format)

        # Mock usage stats
        usage = {
            "prompt_tokens": len(json.dumps(messages)) // 4,  # Rough estimate
            "completion_tokens": len(content) // 4,
            "total_tokens": (len(json.dumps(messages)) + len(content)) // 4,
        }

        # Mock latency (deterministic based on hash)
        latency_seed = int(prompt_hash[:8], 16) % 11
        latency_ms = latency_seed  # 0-10ms

        end_time = time.time()

        # Build response structure (OpenAI-compatible)
        response_data = {
            "id": call_id,
            "object": "chat.completion",
            "created": int(start_time),
            "model": self.model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": content,
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": usage,
        }

        # Save evidence
        evidence_path = self._save_evidence(
            call_id=call_id,
            request={
                "model": self.model,
                "messages": messages,
                "temperature": 0.0,
            },
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

        return result

    def _hash_prompt(self, messages: List[Dict[str, str]]) -> str:
        """Compute deterministic hash of prompt.

        Args:
            messages: Message list

        Returns:
            SHA256 hash (hex string)
        """
        # Stable JSON serialization
        json_str = json.dumps(
            {"messages": messages, "model": self.model},
            ensure_ascii=False,
            sort_keys=True,
        )

        # Hash
        return hashlib.sha256(json_str.encode("utf-8")).hexdigest()

    def _generate_response(
        self,
        messages: List[Dict[str, str]],
        prompt_hash: str,
        response_format: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate deterministic mock response based on prompt content.

        Args:
            messages: Message list
            prompt_hash: Prompt hash for seeding
            response_format: Optional format hint (e.g., {"type": "json_object"})

        Returns:
            Mock response content
        """
        # Extract last user message for pattern matching
        last_message = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                last_message = msg.get("content", "")
                break

        last_message_lower = last_message.lower()

        # Pattern-based response templates
        # W2 Facts extraction
        if "product facts" in last_message_lower or "extract facts" in last_message_lower:
            return json.dumps({
                "facts": [
                    {
                        "claim": "The product supports Hugo static site generation.",
                        "evidence": ["README.md"],
                        "confidence": 0.95,
                    },
                    {
                        "claim": "The product is written in Go.",
                        "evidence": ["go.mod", "examples/hello.go"],
                        "confidence": 0.9,
                    },
                ],
            }, indent=2)

        # W4 IA Planning
        elif "page plan" in last_message_lower or "information architecture" in last_message_lower:
            return json.dumps({
                "pages": [
                    {
                        "path": "content/docs/getting-started.md",
                        "title": "Getting Started",
                        "sections": ["Introduction", "Installation", "Quick Start"],
                    },
                ],
            }, indent=2)

        # W5 Section Writing
        elif "write content" in last_message_lower or "generate section" in last_message_lower:
            return "## Getting Started\n\nThis guide helps you get started with the product.\n\n### Installation\n\nInstall using the standard package manager.\n\n[CLAIM:supports_hugo] The product integrates with Hugo for static site generation."

        # W8 Fix suggestions
        elif "fix" in last_message_lower or "validation error" in last_message_lower:
            return json.dumps({
                "fix_type": "content_update",
                "target_file": "content/docs/getting-started.md",
                "patch": "--- old\n+++ new\n@@ -1 +1 @@\n-Old content\n+Fixed content\n",
            }, indent=2)

        # Default: Generic response seeded by hash
        else:
            # Use hash to seed response variation
            hash_seed = int(prompt_hash[:8], 16)
            self.rng.seed(self.seed + hash_seed)

            # Generate response
            if response_format and response_format.get("type") == "json_object":
                return json.dumps({
                    "result": "Mock response",
                    "seed": self.seed,
                    "hash": prompt_hash[:8],
                }, indent=2)
            else:
                return f"Mock LLM response (seed={self.seed}, hash={prompt_hash[:8]})"

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
            latency_ms: Mock latency in milliseconds

        Returns:
            Path to evidence file
        """
        evidence_file = self.evidence_dir / f"{call_id}.json"

        evidence = {
            "call_id": call_id,
            "prompt_hash": prompt_hash,
            "model": self.model,
            "temperature": 0.0,
            "latency_ms": latency_ms,
            "request": request,
            "response": response,
            "timestamp": time.time(),
            "mock_metadata": {
                "provider": "mock",
                "seed": self.seed,
                "deterministic": True,
            },
        }

        # Write atomically
        tmp_file = evidence_file.with_suffix(".json.tmp")
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(evidence, f, ensure_ascii=False, indent=2, sort_keys=True)

        import os
        os.replace(tmp_file, evidence_file)

        return evidence_file

    def get_prompt_version(self, messages: List[Dict[str, str]]) -> str:
        """Get prompt version (hash) for telemetry.

        Args:
            messages: Message list

        Returns:
            Prompt hash (hex string)
        """
        return self._hash_prompt(messages)
