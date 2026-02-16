"""LLM Strategy Layer: Pluggable model/prompt/temperature per worker and content type.

Phase 1C: Instead of hardcoding temperature=0.0 everywhere, workers look up
their strategy from the registry and use those parameters for chat_completion().

Usage:
    from launch.llm.strategy import STRATEGY_REGISTRY

    # Worker looks up its strategy
    strategy = STRATEGY_REGISTRY.get("w5", "faq")
    response = llm_client.chat_completion(
        messages=messages,
        temperature=strategy.temperature,
        max_tokens=strategy.max_tokens,
        call_id=f"w5_faq_{page_id}",
    )

    # Load custom strategies from YAML
    STRATEGY_REGISTRY.load_from_dict(run_config.get("llm_strategies", {}))
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class LLMStrategy:
    """Configuration for a single LLM call pattern.

    Defines model, temperature, max_tokens, and prompt template for a specific
    worker + content type combination.
    """

    # Temperature for generation (0.0 = deterministic, higher = more creative)
    temperature: float = 0.0

    # Max tokens for response
    max_tokens: int = 4096

    # Response format ("json_object" for structured output, None for text)
    response_format: Optional[str] = "json_object"

    # Path to prompt template file (relative to worker prompts/ dir)
    prompt_template: Optional[str] = None

    # Model override (None = use default from run_config)
    model: Optional[str] = None

    # Min words for quality validation (0 = no minimum)
    min_words: int = 0

    # Description for logging/telemetry
    description: str = ""

    def to_call_kwargs(self) -> Dict[str, Any]:
        """Return kwargs suitable for LLMProviderClient.chat_completion().

        Only includes non-None values to allow defaults to propagate.
        """
        kwargs: Dict[str, Any] = {
            "temperature": self.temperature,
        }
        if self.max_tokens:
            kwargs["max_tokens"] = self.max_tokens
        if self.response_format:
            kwargs["response_format"] = {"type": self.response_format}
        return kwargs


# ── Default Strategies ─────────────────────────────────────────────────────

# W2 strategies: all deterministic (temperature=0.0), JSON output
_W2_DEFAULTS: Dict[str, LLMStrategy] = {
    "extract_claims": LLMStrategy(
        temperature=0.0, max_tokens=4096, response_format="json_object",
        description="Extract claims from code analysis",
    ),
    "workflow_steps": LLMStrategy(
        temperature=0.0, max_tokens=2000, response_format="json_object",
        description="Generate workflow step details",
    ),
    "faq_synthesis": LLMStrategy(
        temperature=0.0, max_tokens=4096, response_format="json_object",
        description="Synthesize FAQ entries",
    ),
    "troubleshooting_synthesis": LLMStrategy(
        temperature=0.0, max_tokens=4096, response_format="json_object",
        description="Synthesize troubleshooting entries",
    ),
    "best_practices_synthesis": LLMStrategy(
        temperature=0.0, max_tokens=4096, response_format="json_object",
        description="Synthesize best practice claims",
    ),
    "performance_synthesis": LLMStrategy(
        temperature=0.0, max_tokens=4096, response_format="json_object",
        description="Synthesize performance characteristics",
    ),
    "enrich_claims": LLMStrategy(
        temperature=0.0, max_tokens=4096, response_format="json_object",
        description="Enrich claim metadata and text",
    ),
    "code_understanding": LLMStrategy(
        temperature=0.0, max_tokens=4096, response_format="json_object",
        description="Analyze code semantics",
    ),
    "feature_profiles": LLMStrategy(
        temperature=0.0, max_tokens=2048, response_format="json_object",
        description="Build feature profile descriptions",
    ),
}

# W5 strategies: mostly deterministic, some creative for content generation
_W5_DEFAULTS: Dict[str, LLMStrategy] = {
    "comprehensive_guide": LLMStrategy(
        temperature=0.0, max_tokens=4096, response_format=None,
        prompt_template="comprehensive_guide.txt",
        min_words=100,
        description="Generate comprehensive guide content",
    ),
    "feature_showcase": LLMStrategy(
        temperature=0.0, max_tokens=4096, response_format=None,
        prompt_template="feature_showcase.txt",
        min_words=250,
        description="Generate feature showcase content",
    ),
    "troubleshooting": LLMStrategy(
        temperature=0.0, max_tokens=4096, response_format=None,
        prompt_template="troubleshooting.txt",
        min_words=100,
        description="Generate troubleshooting guide",
    ),
    "faq": LLMStrategy(
        temperature=0.0, max_tokens=4096, response_format=None,
        prompt_template="faq.txt",
        min_words=150,
        description="Generate FAQ page",
    ),
    "best_practices": LLMStrategy(
        temperature=0.0, max_tokens=4096, response_format=None,
        prompt_template="best_practices.txt",
        min_words=200,
        description="Generate best practices guide",
    ),
    "tutorial": LLMStrategy(
        temperature=0.0, max_tokens=4096, response_format=None,
        prompt_template="tutorial.txt",
        min_words=300,
        description="Generate step-by-step tutorial",
    ),
    "smart_truncate": LLMStrategy(
        temperature=0.3, max_tokens=100, response_format=None,
        description="Creative text summarization",
    ),
    "fallback": LLMStrategy(
        temperature=0.0, max_tokens=4096, response_format=None,
        min_words=50,
        description="Fallback content generation",
    ),
}

# W5.5 strategies: deterministic for review accuracy
_W55_DEFAULTS: Dict[str, LLMStrategy] = {
    "content_enhancer": LLMStrategy(
        temperature=0.0, max_tokens=4096, response_format=None,
        description="Enhance content quality",
    ),
    "technical_fixer": LLMStrategy(
        temperature=0.0, max_tokens=4096, response_format=None,
        description="Fix technical accuracy issues",
    ),
    "usability_improver": LLMStrategy(
        temperature=0.0, max_tokens=4096, response_format=None,
        description="Improve content usability",
    ),
}


class StrategyRegistry:
    """Central registry for LLM strategies.

    Keyed by "{worker}.{content_type}" (e.g., "w5.faq", "w2.extract_claims").
    """

    def __init__(self):
        self._strategies: Dict[str, LLMStrategy] = {}
        # Load defaults
        for key, strategy in _W2_DEFAULTS.items():
            self._strategies[f"w2.{key}"] = strategy
        for key, strategy in _W5_DEFAULTS.items():
            self._strategies[f"w5.{key}"] = strategy
        for key, strategy in _W55_DEFAULTS.items():
            self._strategies[f"w5_5.{key}"] = strategy

    def get(self, worker: str, content_type: str) -> LLMStrategy:
        """Look up strategy for a worker + content type.

        Args:
            worker: Worker identifier (e.g., "w2", "w5", "w5_5")
            content_type: Content type (e.g., "faq", "extract_claims")

        Returns:
            LLMStrategy for this combination, or a default deterministic strategy.
        """
        key = f"{worker}.{content_type}"
        if key in self._strategies:
            return self._strategies[key]

        # Fall back to default deterministic strategy
        logger.debug(f"No strategy for '{key}', using default deterministic")
        return LLMStrategy(description=f"default for {key}")

    def register(self, key: str, strategy: LLMStrategy) -> None:
        """Register or override a strategy.

        Args:
            key: Strategy key (e.g., "w5.faq")
            strategy: LLMStrategy instance
        """
        self._strategies[key] = strategy

    def load_from_dict(self, config: Dict[str, Any]) -> int:
        """Load strategies from a configuration dictionary.

        Expected format:
            {
                "w5.faq": {"temperature": 0.3, "max_tokens": 4096, "model": "gemma3:27b"},
                "w2.extract_claims": {"temperature": 0.0}
            }

        Args:
            config: Dict mapping strategy keys to parameter dicts.

        Returns:
            Number of strategies loaded/updated.
        """
        count = 0
        for key, params in config.items():
            if not isinstance(params, dict):
                logger.warning(f"Skipping invalid strategy config for '{key}': not a dict")
                continue

            # Start from existing strategy or default
            base = self._strategies.get(key, LLMStrategy())
            strategy = LLMStrategy(
                temperature=params.get("temperature", base.temperature),
                max_tokens=params.get("max_tokens", base.max_tokens),
                response_format=params.get("response_format", base.response_format),
                prompt_template=params.get("prompt_template", base.prompt_template),
                model=params.get("model", base.model),
                min_words=params.get("min_words", base.min_words),
                description=params.get("description", base.description),
            )
            self._strategies[key] = strategy
            count += 1

        logger.info(f"Loaded {count} LLM strategies from config")
        return count

    @property
    def all_keys(self) -> list:
        """Return all registered strategy keys."""
        return sorted(self._strategies.keys())

    def __contains__(self, key: str) -> bool:
        return key in self._strategies

    def __len__(self) -> int:
        return len(self._strategies)


# ── Singleton ──────────────────────────────────────────────────────────────

STRATEGY_REGISTRY = StrategyRegistry()
