"""RunConfig model for run configuration.

RunConfig defines all inputs and parameters for a launch run.

Spec references:
- specs/01_system_contract.md (System inputs and contract)
- specs/schemas/run_config.schema.json (Schema definition)
- specs/02_repo_ingestion.md (Configurable ingestion settings, TC-1020/TC-1021)
- specs/05_example_curation.md (Configurable example directories, TC-1020/TC-1021)

Note: This is a foundational model. Worker-specific taskcards may extend
with additional helper methods as needed.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .base import Artifact

logger = logging.getLogger(__name__)

# Platform family mapping (V2 platform-aware layout)
PLATFORM_FAMILY_MAP = {
    "python": "python",
    "typescript": "node",
    "javascript": "node",
    "java": "java",
    "dotnet": "dotnet",
    "cpp": "cpp",
    "go": "go",
    "ruby": "ruby",
    "php": "php",
    "kotlin": "kotlin",
    "swift": "swift",
    "rust": "rust",
}


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
        site_repo_url: Optional[str] = None,
        site_ref: Optional[str] = None,
        workflows_repo_url: Optional[str] = None,
        workflows_ref: Optional[str] = None,
        canonical_urls: Optional[Dict[str, str]] = None,
        allow_manual_edits: Optional[bool] = None,
        validation_profile: Optional[str] = None,
        ci_strictness: Optional[str] = None,
        product_type: Optional[str] = None,
        extra_evidence_urls: Optional[List[str]] = None,
        repo_hints: Optional[Dict[str, Any]] = None,
        launch_tier: Optional[str] = None,
        hugo: Optional[Dict[str, Any]] = None,
        ingestion: Optional[Dict[str, Any]] = None,
        target_platform: Optional[str] = None,
        platform_family: Optional[str] = None,
        # Round 12: Multi-pass generation, incremental updates, prompt library
        multi_pass_generation: Optional[Dict[str, Any]] = None,
        incremental: Optional[Dict[str, Any]] = None,
        prompt_library_path: Optional[str] = None,
        review_enabled: Optional[bool] = None,
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
        self.site_repo_url = site_repo_url
        self.site_ref = site_ref
        self.workflows_repo_url = workflows_repo_url
        self.workflows_ref = workflows_ref
        self.canonical_urls = canonical_urls
        self.allow_manual_edits = allow_manual_edits
        self.validation_profile = validation_profile
        self.ci_strictness = ci_strictness
        self.product_type = product_type
        self.extra_evidence_urls = extra_evidence_urls
        self.repo_hints = repo_hints
        self.launch_tier = launch_tier
        self.hugo = hugo
        self.ingestion = ingestion
        self.target_platform = target_platform
        # Auto-derive platform_family from target_platform if not specified
        if platform_family is not None:
            self.platform_family = platform_family
        elif target_platform is not None:
            self.platform_family = PLATFORM_FAMILY_MAP.get(target_platform, target_platform)
        else:
            self.platform_family = None

        # Round 12 fields (all optional, backward-compatible defaults)
        self.multi_pass_generation = multi_pass_generation
        self.incremental = incremental
        self.prompt_library_path = prompt_library_path
        self.review_enabled = review_enabled

    # -- Ingestion config helpers (TC-1021) --------------------------------
    # Each helper returns the schema default if the ingestion section or
    # individual field is missing, ensuring backward compatibility.

    def get_scan_directories(self) -> List[str]:
        """Return configured scan directories, default [\".\"] (entire repo root).

        See specs/02_repo_ingestion.md 'Configurable scan directories (TC-1020)'.
        """
        if self.ingestion is None:
            return ["."]
        return self.ingestion.get("scan_directories") or ["."]

    def get_exclude_patterns(self) -> List[str]:
        """Return configured exclude patterns, default [].

        See specs/02_repo_ingestion.md.
        """
        if self.ingestion is None:
            return []
        return self.ingestion.get("exclude_patterns") or []

    def get_gitignore_mode(self) -> str:
        """Return configured .gitignore handling mode, default \"respect\".

        See specs/02_repo_ingestion.md '.gitignore support (TC-1020)'.
        Values: respect | ignore | strict
        """
        if self.ingestion is None:
            return "respect"
        return self.ingestion.get("gitignore_mode") or "respect"

    def get_example_directories(self) -> List[str]:
        """Return additional example directories beyond standard dirs, default [].

        See specs/05_example_curation.md 'Configurable example discovery directories (TC-1020)'.
        These are IN ADDITION to the standard dirs (examples/, samples/, demo/).
        """
        if self.ingestion is None:
            return []
        return self.ingestion.get("example_directories") or []

    def get_record_binary_files(self) -> bool:
        """Return whether to record binary files in repo_inventory, default True.

        See specs/02_repo_ingestion.md 'Binary assets discovery'.
        """
        if self.ingestion is None:
            return True
        val = self.ingestion.get("record_binary_files")
        return val if val is not None else True

    def get_detect_phantom_paths(self) -> bool:
        """Return whether to detect phantom path references, default True.

        See specs/02_repo_ingestion.md 'Phantom path detection'.
        """
        if self.ingestion is None:
            return True
        val = self.ingestion.get("detect_phantom_paths")
        return val if val is not None else True

    # -- Round 12: Multi-pass generation helpers (TC-1701) -------------------

    def is_multi_pass_enabled(self) -> bool:
        """Return whether multi-pass generation is enabled, default False.

        See specs/21_worker_contracts.md 'W5 Multi-Pass Generation Contract'.
        """
        if self.multi_pass_generation is None:
            return False
        return self.multi_pass_generation.get("enabled", False)

    def get_multi_pass_config(self) -> Dict[str, Any]:
        """Return multi-pass generation config with defaults.

        See specs/21_worker_contracts.md 'W5 Multi-Pass Generation Contract'.
        """
        defaults = {
            "enabled": False,
            "skip_refine_for_thin_pages": True,
            "min_claims_for_outline": 3,
            "outline_temperature": 0.0,
            "draft_temperature": 0.1,
            "refine_temperature": 0.0,
        }
        if self.multi_pass_generation is None:
            return defaults
        merged = dict(defaults)
        merged.update(self.multi_pass_generation)
        return merged

    # -- Round 12: Incremental update helpers (TC-1701) ----------------------

    def is_incremental_enabled(self) -> bool:
        """Return whether incremental updates are enabled, default False.

        See specs/03_product_facts_and_evidence.md 'Incremental Claim Management'.
        """
        if self.incremental is None:
            return False
        return self.incremental.get("enabled", False)

    def get_previous_run_path(self) -> Optional[str]:
        """Return the previous run path for incremental updates, or None.

        See specs/06_page_planning.md 'Incremental Page Preservation'.
        """
        if self.incremental is None:
            return None
        return self.incremental.get("previous_run_path")

    def get_incremental_config(self) -> Dict[str, Any]:
        """Return incremental update config with defaults."""
        defaults = {
            "enabled": False,
            "page_preservation_threshold": 0.75,
            "claim_enrichment_strategy": "full_re_enrich",
        }
        if self.incremental is None:
            return defaults
        merged = dict(defaults)
        merged.update(self.incremental)
        return merged

    # -- Round 12: Prompt library path (TC-1701) -----------------------------

    def get_prompt_library_path(self) -> str:
        """Return the prompt library path, default 'src/launch/prompts'.

        See specs/21_worker_contracts.md 'Prompt Library Contract'.
        """
        return self.prompt_library_path or "src/launch/prompts"

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
        if self.site_repo_url is not None:
            result["site_repo_url"] = self.site_repo_url
        if self.site_ref is not None:
            result["site_ref"] = self.site_ref
        if self.workflows_repo_url is not None:
            result["workflows_repo_url"] = self.workflows_repo_url
        if self.workflows_ref is not None:
            result["workflows_ref"] = self.workflows_ref
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
        if self.ingestion is not None:
            result["ingestion"] = self.ingestion
        if self.target_platform is not None:
            result["target_platform"] = self.target_platform
        if self.platform_family is not None:
            result["platform_family"] = self.platform_family
        # Round 12 fields
        if self.multi_pass_generation is not None:
            result["multi_pass_generation"] = self.multi_pass_generation
        if self.incremental is not None:
            result["incremental"] = self.incremental
        if self.prompt_library_path is not None:
            result["prompt_library_path"] = self.prompt_library_path
        if self.review_enabled is not None:
            result["review_enabled"] = self.review_enabled

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
            site_repo_url=data.get("site_repo_url"),
            site_ref=data.get("site_ref"),
            workflows_repo_url=data.get("workflows_repo_url"),
            workflows_ref=data.get("workflows_ref"),
            canonical_urls=data.get("canonical_urls"),
            allow_manual_edits=data.get("allow_manual_edits"),
            validation_profile=data.get("validation_profile"),
            ci_strictness=data.get("ci_strictness"),
            product_type=data.get("product_type"),
            extra_evidence_urls=data.get("extra_evidence_urls"),
            repo_hints=data.get("repo_hints"),
            launch_tier=data.get("launch_tier"),
            hugo=data.get("hugo"),
            ingestion=data.get("ingestion"),
            target_platform=data.get("target_platform"),
            platform_family=data.get("platform_family"),
            # Round 12
            multi_pass_generation=data.get("multi_pass_generation"),
            incremental=data.get("incremental"),
            prompt_library_path=data.get("prompt_library_path"),
            review_enabled=data.get("review_enabled"),
        )
