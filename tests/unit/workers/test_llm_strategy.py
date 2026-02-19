"""Tests for LLM Strategy Layer (Phase 1C).

Validates pluggable model/prompt/temperature configuration per worker.
"""
import pytest
from launch.llm.strategy import (
    LLMStrategy,
    StrategyRegistry,
    STRATEGY_REGISTRY,
)


class TestLLMStrategy:
    def test_default_values(self):
        s = LLMStrategy()
        assert s.temperature == 0.0
        assert s.max_tokens == 4096
        assert s.response_format == "json_object"
        assert s.prompt_template is None
        assert s.model is None
        assert s.min_words == 0

    def test_to_call_kwargs(self):
        s = LLMStrategy(temperature=0.3, max_tokens=2000, response_format="json_object")
        kwargs = s.to_call_kwargs()
        assert kwargs["temperature"] == 0.3
        assert kwargs["max_tokens"] == 2000
        assert kwargs["response_format"] == {"type": "json_object"}

    def test_to_call_kwargs_no_response_format(self):
        s = LLMStrategy(response_format=None)
        kwargs = s.to_call_kwargs()
        assert "response_format" not in kwargs


class TestStrategyRegistry:
    def test_default_strategies_loaded(self):
        """Registry should have default strategies for W2, W5, W7."""
        assert "w2.extract_claims" in STRATEGY_REGISTRY
        assert "w5.faq" in STRATEGY_REGISTRY
        assert "w7.content_enhancer" in STRATEGY_REGISTRY

    def test_get_existing_strategy(self):
        s = STRATEGY_REGISTRY.get("w5", "faq")
        assert s.prompt_template == "faq.txt"
        assert s.min_words == 150

    def test_get_missing_returns_default(self):
        s = STRATEGY_REGISTRY.get("w99", "nonexistent")
        assert s.temperature == 0.0  # Default deterministic

    def test_w2_strategies_are_deterministic(self):
        """All W2 strategies should use temperature=0.0."""
        for key in STRATEGY_REGISTRY.all_keys:
            if key.startswith("w2."):
                s = STRATEGY_REGISTRY._strategies[key]
                assert s.temperature == 0.0, f"{key} should be deterministic"

    def test_w5_smart_truncate_is_creative(self):
        """smart_truncate is the only strategy with temperature > 0."""
        s = STRATEGY_REGISTRY.get("w5", "smart_truncate")
        assert s.temperature == 0.3

    def test_register_override(self):
        registry = StrategyRegistry()
        original = registry.get("w5", "faq")
        assert original.temperature == 0.0

        registry.register("w5.faq", LLMStrategy(temperature=0.7, model="gemma3:27b"))
        updated = registry.get("w5", "faq")
        assert updated.temperature == 0.7
        assert updated.model == "gemma3:27b"

    def test_load_from_dict(self):
        registry = StrategyRegistry()
        count = registry.load_from_dict({
            "w5.tutorial": {"temperature": 0.7, "model": "gemma3:27b"},
            "w5.faq": {"temperature": 0.3},
        })
        assert count == 2

        tutorial = registry.get("w5", "tutorial")
        assert tutorial.temperature == 0.7
        assert tutorial.model == "gemma3:27b"

        faq = registry.get("w5", "faq")
        assert faq.temperature == 0.3

    def test_load_from_dict_preserves_defaults(self):
        """Loading partial config should preserve unspecified fields."""
        registry = StrategyRegistry()
        original_prompt = registry.get("w5", "faq").prompt_template

        registry.load_from_dict({"w5.faq": {"temperature": 0.5}})

        updated = registry.get("w5", "faq")
        assert updated.temperature == 0.5
        assert updated.prompt_template == original_prompt  # Preserved

    def test_load_from_dict_skips_invalid(self):
        registry = StrategyRegistry()
        count = registry.load_from_dict({
            "w5.faq": "not_a_dict",  # Invalid
            "w5.tutorial": {"temperature": 0.7},  # Valid
        })
        assert count == 1

    def test_all_keys(self):
        keys = STRATEGY_REGISTRY.all_keys
        assert len(keys) > 0
        assert all("." in k for k in keys)

    def test_len(self):
        assert len(STRATEGY_REGISTRY) > 10  # At least W2 + W5 + W7 defaults

    def test_w5_generators_have_prompt_templates(self):
        """All W5 content generators should have prompt templates."""
        generators_with_prompts = [
            "comprehensive_guide", "feature_showcase", "troubleshooting",
            "faq", "best_practices", "tutorial",
        ]
        for gen in generators_with_prompts:
            s = STRATEGY_REGISTRY.get("w5", gen)
            assert s.prompt_template is not None, f"w5.{gen} should have prompt_template"

    def test_new_strategy_via_register(self):
        """Register a completely new strategy (for future content types)."""
        registry = StrategyRegistry()
        registry.register("w5.api_reference", LLMStrategy(
            temperature=0.0,
            max_tokens=8192,
            prompt_template="api_reference.txt",
            min_words=500,
            description="Generate API reference documentation",
        ))
        s = registry.get("w5", "api_reference")
        assert s.max_tokens == 8192
        assert s.prompt_template == "api_reference.txt"
