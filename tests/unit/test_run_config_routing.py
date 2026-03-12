"""Tests for RunConfig routing model parsing."""
from __future__ import annotations

import pytest

from launcher.models.run_config import (
    LLMConfig,
    LLMEndpoint,
    ModelRouting,
    ReasoningEndpoint,
    RunConfig,
)


class TestLLMConfigRouting:
    def test_no_routing_fields_backward_compat(self) -> None:
        cfg = LLMConfig(primary=LLMEndpoint(base_url="http://x/v1", model="m"))
        assert cfg.reasoning is None
        assert cfg.routing is None

    def test_reasoning_only(self) -> None:
        cfg = LLMConfig(
            primary=LLMEndpoint(base_url="http://x/v1", model="m"),
            reasoning=ReasoningEndpoint(model="r-model"),
        )
        assert cfg.reasoning.model == "r-model"
        assert cfg.routing is None

    def test_reasoning_and_routing(self) -> None:
        cfg = LLMConfig(
            primary=LLMEndpoint(base_url="http://x/v1", model="m"),
            reasoning=ReasoningEndpoint(model="r-model"),
            routing=ModelRouting(extract="standard", generate="standard", review="reasoning"),
        )
        assert cfg.reasoning.model == "r-model"
        assert cfg.routing.extract == "standard"
        assert cfg.routing.generate == "standard"
        assert cfg.routing.review == "reasoning"

    def test_default_routing_values(self) -> None:
        routing = ModelRouting()
        assert routing.extract == "standard"
        assert routing.generate == "standard"
        assert routing.review == "reasoning"

    def test_full_run_config_with_routing(self) -> None:
        rc = RunConfig(
            family="cells",
            platform="python",
            repo_url="https://github.com/example/repo",
            llm=LLMConfig(
                primary=LLMEndpoint(base_url="http://x/v1", model="qwen3-next"),
                reasoning=ReasoningEndpoint(model="recommended"),
                routing=ModelRouting(),
            ),
        )
        assert rc.llm.primary.model == "qwen3-next"
        assert rc.llm.reasoning.model == "recommended"
        assert rc.llm.routing.review == "reasoning"
