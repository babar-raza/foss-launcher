from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .base import LauncherBaseModel


class LLMEndpoint(LauncherBaseModel):
    """Connection details for a single LLM endpoint."""

    base_url: str
    model: str


class ReasoningEndpoint(LauncherBaseModel):
    """Reasoning model override — shares base_url with primary."""

    model: str


class ModelRouting(LauncherBaseModel):
    """Per-task model selection: standard (primary) or reasoning."""

    extract: Literal["standard", "reasoning"] = "standard"
    generate: Literal["standard", "reasoning"] = "standard"
    review: Literal["standard", "reasoning"] = "reasoning"


class EmbeddingEndpoint(LauncherBaseModel):
    """Connection details for an embedding endpoint (optional)."""

    base_url: str = ""
    model: str = "qwen3-embedding-8b"


class LLMConfig(LauncherBaseModel):
    """LLM configuration with optional fallback and reasoning routing."""

    primary: LLMEndpoint
    fallback: LLMEndpoint | None = None
    reasoning: ReasoningEndpoint | None = None
    routing: ModelRouting | None = None
    embedding: EmbeddingEndpoint | None = None
    temperature: float = 0.0
    max_tokens: int = 6000
    max_concurrency: int = 4
    api_key_env: str | None = None
    request_timeout_s: int = 120


class TelemetryConfig(LauncherBaseModel):
    """Optional telemetry API configuration."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    endpoint_url: str = "http://127.0.0.1:8765"
    auth_token_env: str = ""
    project: str = ""


class GeminiSEOConfig(LauncherBaseModel):
    """Gemini sub-config for SEO."""

    enabled: bool = True
    model: str = "gemini-2.5-flash"
    rpm: int = 15
    rpd: int = 1500


class SEOConfig(LauncherBaseModel):
    """SEO pipeline configuration."""

    enabled: bool = True
    keyword_research: bool = True
    offline_mode: bool = False
    cache_ttl_days: int = 7
    keyword_density_target: float = 0.015
    slug_rewrite: bool = True
    gemini: GeminiSEOConfig = Field(default_factory=GeminiSEOConfig)
    subdomain_map: dict[str, str] = Field(default_factory=lambda: {
        "docs": "docs.aspose.org",
        "reference": "reference.aspose.org",
        "kb": "kb.aspose.org",
        "blog": "blog.aspose.org",
        "products": "products.aspose.org",
    })


class OutputConfig(LauncherBaseModel):
    """Controls where and how pipeline output is written."""

    goal: Literal["draft", "pr"] = "draft"
    run_dir: str = "runs/"
    deploy_dir: str = ""
    """Local staging directory; when set, promote_run() copies qualifying pages here."""
    content_repo_map: dict[str, str] = Field(default_factory=dict)
    """Maps TLD → local content repo root path. Supports ${ENV_VAR} expansion.

    Each key is the last two dot-separated components of the page's subdomain
    (the TLD, e.g. ``"aspose.org"``, ``"aspose.net"``).  Each value is the
    absolute path to the local clone of that TLD's content git repository.
    Pages from any subdomain (docs.aspose.org, products.aspose.org, …) all
    route to the same ``"aspose.org"`` root clone.

    Example (pilot config)::

        content_repo_map:
          "aspose.org": "${ASPOSE_ORG_CONTENT_REPO}"
          "aspose.net": "${ASPOSE_NET_CONTENT_REPO}"
    """


class SkillsConfig(LauncherBaseModel):
    """Quality-standards document configuration (TC-3856).

    When enabled, skills.md is loaded at worker startup and injected into
    both the generation and evaluation prompts. Works identically whether
    the pipeline is invoked via CLI, library import, or CI/CD.
    Gracefully degrades to no-op when the file at ``path`` does not exist.

    Path resolution:
        - Absolute paths are used as-is (recommended for library callers).
        - Relative paths are resolved against CWD first (CLI convention), then
          against ``run_dir.parent`` (library convention fallback).
        - Example for library use::

              from launcher.models.run_config import RunConfig, SkillsConfig
              config = RunConfig(
                  ...,
                  skills=SkillsConfig(enabled=True, path="/abs/path/to/skills.md"),
              )
    """

    enabled: bool = True
    path: str = "skills.md"


class GoldenConfig(LauncherBaseModel):
    """Golden reference corpus configuration.

    When enabled, A-grade exemplar files from ``dir`` are loaded at worker
    startup and used in two ways:
      1. Prompt injection: section prompts receive a golden excerpt showing
         the expected depth, tone, and structure.
      2. Structural enforcement: generated sections are checked against the
         golden block spec (required block types, min word count) and retried
         when the spec is not met.

    The ``get`` method provides dict-compatible access so existing code that
    calls ``golden_cfg.get("enabled")`` continues to work whether the value
    is a plain dict or a ``GoldenConfig`` instance.
    """

    enabled: bool = False
    dir: str = "golden/"

    def get(self, key: str, default: object = None) -> object:
        """Dict-compatible attribute access for backward compatibility."""
        return getattr(self, key, default)


class RunConfig(LauncherBaseModel):
    """Top-level configuration for a single pipeline run.

    Extended fields (github_ref, product_slug, budgets, telemetry, etc.)
    are silently ignored — forward-compatible metadata from the intake
    config generator.
    """

    model_config = ConfigDict(extra="ignore", frozen=True)

    family: str
    platform: str
    repo_url: str
    launch_tier: Literal["auto", "full", "core", "minimal"] = "auto"
    validation_profile: str = "default"
    product_name: str = ""
    display_name: str = ""
    canonical_import: str = ""
    runtime_import: str = ""
    llm: LLMConfig | None = None
    seo: SEOConfig = Field(default_factory=SEOConfig)
    skills: SkillsConfig = Field(default_factory=SkillsConfig)
    golden: GoldenConfig = Field(default_factory=GoldenConfig)
    telemetry: TelemetryConfig | None = None
    output: OutputConfig = Field(default_factory=OutputConfig)
