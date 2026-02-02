"""RunConfig model for run configuration.

RunConfig defines all inputs and parameters for a launch run.

Spec references:
- specs/01_system_contract.md (System inputs and contract)
- specs/schemas/run_config.schema.json (Schema definition)

Note: This is a foundational model. Worker-specific taskcards may extend
with additional helper methods as needed.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .base import Artifact

logger = logging.getLogger(__name__)


class RunConfig(Artifact):
    """Run configuration artifact.

    Defines product identity, repo inputs, sections, LLM config, and budgets.
    Per specs/01_system_contract.md:28-40 and run_config.schema.json.
    """

    def __init__(
        self,
        schema_version: str,
        product_slug: str,
        product_name: str,
        family: str,
        github_repo_url: str,
        github_ref: str,
        required_sections: List[str],
        site_layout: Dict[str, Any],
        allowed_paths: List[str],
        llm: Dict[str, Any],
        mcp: Dict[str, Any],
        telemetry: Dict[str, Any],
        commit_service: Dict[str, Any],
        templates_version: str,
        ruleset_version: str,
        allow_inference: bool,
        max_fix_attempts: int,
        budgets: Dict[str, Any],
        # Optional fields
        locale: Optional[str] = None,
        locales: Optional[List[str]] = None,
        target_platform: Optional[str] = None,
        layout_mode: Optional[str] = None,
        site_repo_url: Optional[str] = None,
        site_ref: Optional[str] = None,
        workflows_repo_url: Optional[str] = None,
        workflows_ref: Optional[str] = None,
        platform_hints: Optional[Dict[str, Any]] = None,
        canonical_urls: Optional[Dict[str, str]] = None,
        allow_manual_edits: Optional[bool] = None,
        validation_profile: Optional[str] = None,
        ci_strictness: Optional[str] = None,
        product_type: Optional[str] = None,
        extra_evidence_urls: Optional[List[str]] = None,
        repo_hints: Optional[Dict[str, Any]] = None,
        launch_tier: Optional[str] = None,
        hugo: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(schema_version)
        # Required fields
        self.product_slug = product_slug
        self.product_name = product_name
        self.family = family
        self.github_repo_url = github_repo_url
        self.github_ref = github_ref
        self.required_sections = required_sections
        self.site_layout = site_layout
        self.allowed_paths = allowed_paths
        self.llm = llm
        self.mcp = mcp
        self.telemetry = telemetry
        self.commit_service = commit_service
        self.templates_version = templates_version
        self.ruleset_version = ruleset_version
        self.allow_inference = allow_inference
        self.max_fix_attempts = max_fix_attempts
        self.budgets = budgets

        # Optional fields
        self.locale = locale
        self.locales = locales
        self.target_platform = target_platform
        self.layout_mode = layout_mode
        self.site_repo_url = site_repo_url
        self.site_ref = site_ref
        self.workflows_repo_url = workflows_repo_url
        self.workflows_ref = workflows_ref
        self.platform_hints = platform_hints
        self.canonical_urls = canonical_urls
        self.allow_manual_edits = allow_manual_edits
        self.validation_profile = validation_profile
        self.ci_strictness = ci_strictness
        self.product_type = product_type
        self.extra_evidence_urls = extra_evidence_urls
        self.repo_hints = repo_hints
        self.launch_tier = launch_tier
        self.hugo = hugo

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary with stable field ordering."""
        result: Dict[str, Any] = {
            "schema_version": self.schema_version,
            "product_slug": self.product_slug,
            "product_name": self.product_name,
            "family": self.family,
            "github_repo_url": self.github_repo_url,
            "github_ref": self.github_ref,
            "required_sections": self.required_sections,
            "site_layout": self.site_layout,
            "allowed_paths": self.allowed_paths,
            "llm": self.llm,
            "mcp": self.mcp,
            "telemetry": self.telemetry,
            "commit_service": self.commit_service,
            "templates_version": self.templates_version,
            "ruleset_version": self.ruleset_version,
            "allow_inference": self.allow_inference,
            "max_fix_attempts": self.max_fix_attempts,
            "budgets": self.budgets,
        }

        # Add optional fields if present
        if self.locale is not None:
            result["locale"] = self.locale
        if self.locales is not None:
            result["locales"] = self.locales
        if self.target_platform is not None:
            result["target_platform"] = self.target_platform
        if self.layout_mode is not None:
            result["layout_mode"] = self.layout_mode
        if self.site_repo_url is not None:
            result["site_repo_url"] = self.site_repo_url
        if self.site_ref is not None:
            result["site_ref"] = self.site_ref
        if self.workflows_repo_url is not None:
            result["workflows_repo_url"] = self.workflows_repo_url
        if self.workflows_ref is not None:
            result["workflows_ref"] = self.workflows_ref
        if self.platform_hints is not None:
            result["platform_hints"] = self.platform_hints
        if self.canonical_urls is not None:
            result["canonical_urls"] = self.canonical_urls
        if self.allow_manual_edits is not None:
            result["allow_manual_edits"] = self.allow_manual_edits
        if self.validation_profile is not None:
            result["validation_profile"] = self.validation_profile
        if self.ci_strictness is not None:
            result["ci_strictness"] = self.ci_strictness
        if self.product_type is not None:
            result["product_type"] = self.product_type
        if self.extra_evidence_urls is not None:
            result["extra_evidence_urls"] = self.extra_evidence_urls
        if self.repo_hints is not None:
            result["repo_hints"] = self.repo_hints
        if self.launch_tier is not None:
            result["launch_tier"] = self.launch_tier
        if self.hugo is not None:
            result["hugo"] = self.hugo

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> RunConfig:
        """Deserialize from dictionary."""
        # Backward compatibility: default schema_version if missing
        if "schema_version" not in data:
            logger.warning("schema_version missing from run_config, defaulting to '1.0'")

        return cls(
            schema_version=data.get("schema_version", "1.0"),
            product_slug=data["product_slug"],
            product_name=data["product_name"],
            family=data["family"],
            github_repo_url=data["github_repo_url"],
            github_ref=data["github_ref"],
            required_sections=data["required_sections"],
            site_layout=data["site_layout"],
            allowed_paths=data["allowed_paths"],
            llm=data["llm"],
            mcp=data["mcp"],
            telemetry=data["telemetry"],
            commit_service=data["commit_service"],
            templates_version=data["templates_version"],
            ruleset_version=data["ruleset_version"],
            allow_inference=data["allow_inference"],
            max_fix_attempts=data["max_fix_attempts"],
            budgets=data["budgets"],
            locale=data.get("locale"),
            locales=data.get("locales"),
            target_platform=data.get("target_platform"),
            layout_mode=data.get("layout_mode"),
            site_repo_url=data.get("site_repo_url"),
            site_ref=data.get("site_ref"),
            workflows_repo_url=data.get("workflows_repo_url"),
            workflows_ref=data.get("workflows_ref"),
            platform_hints=data.get("platform_hints"),
            canonical_urls=data.get("canonical_urls"),
            allow_manual_edits=data.get("allow_manual_edits"),
            validation_profile=data.get("validation_profile"),
            ci_strictness=data.get("ci_strictness"),
            product_type=data.get("product_type"),
            extra_evidence_urls=data.get("extra_evidence_urls"),
            repo_hints=data.get("repo_hints"),
            launch_tier=data.get("launch_tier"),
            hugo=data.get("hugo"),
        )
