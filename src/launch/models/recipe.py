"""Recipe System: Config-driven output specification.

A Recipe is a YAML-parseable configuration that fully describes what pages
to generate, how to generate them, and what quality standards to enforce.
No Python needed for new content types or products.

Usage:
    from launch.models.recipe import Recipe, load_recipe

    # Load from YAML file
    recipe = load_recipe("recipes/aspose-3d-python.recipe.yaml")

    # Load from dict (e.g., embedded in run_config)
    recipe = Recipe.from_dict(config_dict)

    # Apply to registries
    recipe.apply_llm_strategies(strategy_registry)

    # Query page specs
    pages = recipe.get_pages_for_section("docs")
    quality = recipe.quality

Integration seams:
    - W4 IAPlanner: recipe.sections drives page planning instead of templates
    - W5 SectionWriter: recipe.pages[].generator selects generator function
    - ClaimRegistry: recipe.pages[].claims customizes claim selection
    - StrategyRegistry: recipe.llm_strategies overrides model/prompt/temperature
    - SiteConfig: recipe.site overrides domain/path templates
    - W7 ContentReviewer: recipe.quality sets min scores and max rounds
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ── Sub-models ────────────────────────────────────────────────────────────


@dataclass
class ClaimSpec:
    """Claim selection specification for a page."""

    # Which claim kinds to include (e.g., ["feature", "api", "workflow"])
    kinds: List[str] = field(default_factory=list)

    # Min/max claims for the page
    min: int = 0
    max: int = 0

    # Specific claim groups to pull from (overrides kind-based selection)
    groups: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {}
        if self.kinds:
            d["kinds"] = sorted(self.kinds)
        if self.min:
            d["min"] = self.min
        if self.max:
            d["max"] = self.max
        if self.groups:
            d["groups"] = sorted(self.groups)
        return d

    @classmethod
    def from_dict(cls, data: Any) -> ClaimSpec:
        if not isinstance(data, dict):
            return cls()
        return cls(
            kinds=data.get("kinds", []),
            min=data.get("min", 0),
            max=data.get("max", 0),
            groups=data.get("groups", []),
        )


@dataclass
class PageSpec:
    """Specification for a single page in the recipe."""

    # Page role (maps to generator): comprehensive_guide, faq, tutorial, etc.
    role: str

    # URL slug
    slug: str

    # Page title (optional — auto-generated if not specified)
    title: str = ""

    # Claim selection spec
    claims: Optional[ClaimSpec] = None

    # Content tone: "technical", "tutorial-friendly", "marketing"
    tone: str = ""

    # Target audience: "beginner", "intermediate", "advanced"
    audience: str = ""

    # Whether this page is mandatory (always generated) or optional
    mandatory: bool = True

    # LLM strategy override for this specific page (key into llm_strategies)
    strategy_override: str = ""

    # Custom heading structure (overrides generator defaults)
    headings: List[str] = field(default_factory=list)

    # Template path (for template-driven pages, optional)
    template_path: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "role": self.role,
            "slug": self.slug,
        }
        if self.title:
            d["title"] = self.title
        if self.claims:
            cd = self.claims.to_dict()
            if cd:
                d["claims"] = cd
        if self.tone:
            d["tone"] = self.tone
        if self.audience:
            d["audience"] = self.audience
        if not self.mandatory:
            d["mandatory"] = False
        if self.strategy_override:
            d["strategy_override"] = self.strategy_override
        if self.headings:
            d["headings"] = self.headings
        if self.template_path:
            d["template_path"] = self.template_path
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PageSpec:
        claims_data = data.get("claims")
        claims = ClaimSpec.from_dict(claims_data) if claims_data else None
        return cls(
            role=data.get("role", ""),
            slug=data.get("slug", ""),
            title=data.get("title", ""),
            claims=claims,
            tone=data.get("tone", ""),
            audience=data.get("audience", ""),
            mandatory=data.get("mandatory", True),
            strategy_override=data.get("strategy_override", ""),
            headings=data.get("headings", []),
            template_path=data.get("template_path", ""),
        )


@dataclass
class SectionSpec:
    """Specification for a site section in the recipe."""

    # Section name (docs, products, reference, kb, blog)
    name: str

    # Pages in this section (ordered)
    pages: List[PageSpec] = field(default_factory=list)

    # Max pages for this section (0 = no limit)
    max_pages: int = 0

    # Whether to allow auto-generated optional pages beyond the spec
    allow_optional: bool = True

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "pages": [p.to_dict() for p in self.pages],
        }
        if self.max_pages:
            d["max_pages"] = self.max_pages
        if not self.allow_optional:
            d["allow_optional"] = False
        return d

    @classmethod
    def from_dict(cls, name: str, data: Dict[str, Any]) -> SectionSpec:
        pages = [PageSpec.from_dict(p) for p in data.get("pages", [])]
        return cls(
            name=name,
            pages=pages,
            max_pages=data.get("max_pages", 0),
            allow_optional=data.get("allow_optional", True),
        )

    @property
    def mandatory_pages(self) -> List[PageSpec]:
        """Return only mandatory pages."""
        return [p for p in self.pages if p.mandatory]

    @property
    def optional_pages(self) -> List[PageSpec]:
        """Return only optional pages."""
        return [p for p in self.pages if not p.mandatory]

    def get_page(self, slug: str) -> Optional[PageSpec]:
        """Get a page by slug."""
        for p in self.pages:
            if p.slug == slug:
                return p
        return None


@dataclass
class SiteSpec:
    """Site configuration overrides in the recipe."""

    # Domain override
    domain: str = ""

    # Output path template override
    output_template: str = ""

    # URL template override
    url_template: str = ""

    # Blog output path template override
    blog_output_template: str = ""

    # Subdomain map overrides
    subdomain_map: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {}
        if self.domain:
            d["domain"] = self.domain
        if self.output_template:
            d["output_template"] = self.output_template
        if self.url_template:
            d["url_template"] = self.url_template
        if self.blog_output_template:
            d["blog_output_template"] = self.blog_output_template
        if self.subdomain_map:
            d["subdomain_map"] = dict(sorted(self.subdomain_map.items()))
        return d

    @classmethod
    def from_dict(cls, data: Any) -> SiteSpec:
        if not isinstance(data, dict):
            return cls()
        return cls(
            domain=data.get("domain", ""),
            output_template=data.get("output_template", ""),
            url_template=data.get("url_template", ""),
            blog_output_template=data.get("blog_output_template", ""),
            subdomain_map=data.get("subdomain_map", {}),
        )

    def apply_to_site_config(self, site_config) -> None:
        """Apply overrides to a SiteConfig instance in-place."""
        if self.domain:
            site_config.domain = self.domain
        if self.output_template:
            site_config.output_path_template = self.output_template
        if self.blog_output_template:
            site_config.blog_output_path_template = self.blog_output_template
        if self.subdomain_map:
            site_config.subdomain_map.update(self.subdomain_map)


@dataclass
class QualitySpec:
    """Quality gate configuration."""

    # Minimum dimension scores for PASS (1-5)
    min_content_quality: int = 4
    min_technical_accuracy: int = 4
    min_usability: int = 4

    # Maximum review rounds before giving up
    max_review_rounds: int = 3

    # Whether to enable W7 content review
    review_enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "min_content_quality": self.min_content_quality,
            "min_technical_accuracy": self.min_technical_accuracy,
            "min_usability": self.min_usability,
            "max_review_rounds": self.max_review_rounds,
            "review_enabled": self.review_enabled,
        }

    @classmethod
    def from_dict(cls, data: Any) -> QualitySpec:
        if not isinstance(data, dict):
            return cls()
        return cls(
            min_content_quality=data.get("min_content_quality", 4),
            min_technical_accuracy=data.get("min_technical_accuracy", 4),
            min_usability=data.get("min_usability", 4),
            max_review_rounds=data.get("max_review_rounds", 3),
            review_enabled=data.get("review_enabled", True),
        )


# ── Main Recipe Model ─────────────────────────────────────────────────────


@dataclass
class Recipe:
    """Complete output specification for a product.

    A Recipe defines:
    - What pages to generate (sections + pages)
    - How to generate them (LLM strategies, generator selection)
    - What quality standards to enforce (quality gates)
    - Where to put them (site config overrides)
    """

    # Recipe metadata
    name: str = ""
    version: str = "1.0"
    description: str = ""

    # Product identity
    product: str = ""
    platform: str = ""
    family: str = ""

    # Site config overrides
    site: SiteSpec = field(default_factory=SiteSpec)

    # Section definitions (ordered dict)
    sections: Dict[str, SectionSpec] = field(default_factory=dict)

    # LLM strategy overrides (keyed by "{worker}.{content_type}")
    llm_strategies: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Quality gate settings
    quality: QualitySpec = field(default_factory=QualitySpec)

    # ── Query Methods ─────────────────────────────────────────────────

    def get_section(self, section_name: str) -> Optional[SectionSpec]:
        """Get a section spec by name."""
        return self.sections.get(section_name)

    def get_pages_for_section(self, section_name: str) -> List[PageSpec]:
        """Get all page specs for a section."""
        section = self.sections.get(section_name)
        if section is None:
            return []
        return list(section.pages)

    def get_page(self, section_name: str, slug: str) -> Optional[PageSpec]:
        """Get a specific page by section and slug."""
        section = self.sections.get(section_name)
        if section is None:
            return None
        return section.get_page(slug)

    @property
    def all_pages(self) -> List[PageSpec]:
        """Get all pages across all sections (flat list)."""
        pages = []
        for section in self.sections.values():
            pages.extend(section.pages)
        return pages

    @property
    def all_page_roles(self) -> List[str]:
        """Get all unique page roles referenced in the recipe."""
        roles = set()
        for page in self.all_pages:
            if page.role:
                roles.add(page.role)
        return sorted(roles)

    @property
    def section_names(self) -> List[str]:
        """Get all section names (sorted)."""
        return sorted(self.sections.keys())

    @property
    def total_pages(self) -> int:
        """Total number of pages across all sections."""
        return sum(len(s.pages) for s in self.sections.values())

    # ── Registry Integration ──────────────────────────────────────────

    def apply_llm_strategies(self, registry) -> int:
        """Apply LLM strategy overrides to a StrategyRegistry.

        Args:
            registry: StrategyRegistry instance to update

        Returns:
            Number of strategies applied.
        """
        if not self.llm_strategies:
            return 0
        return registry.load_from_dict(self.llm_strategies)

    def apply_site_config(self, site_config) -> None:
        """Apply site configuration overrides to a SiteConfig.

        Args:
            site_config: SiteConfig instance to update in-place
        """
        self.site.apply_to_site_config(site_config)

    def get_claim_spec(self, section: str, slug: str) -> Optional[ClaimSpec]:
        """Get claim selection spec for a specific page.

        Returns None if no recipe claim spec is defined (use defaults).
        """
        page = self.get_page(section, slug)
        if page is None:
            return None
        return page.claims

    # ── Serialization ─────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        """Serialize recipe to a dictionary suitable for YAML/JSON output."""
        d: Dict[str, Any] = {}

        # Metadata
        if self.name:
            d["name"] = self.name
        d["version"] = self.version
        if self.description:
            d["description"] = self.description

        # Product identity
        if self.product:
            d["product"] = self.product
        if self.platform:
            d["platform"] = self.platform
        if self.family:
            d["family"] = self.family

        # Site overrides
        site_d = self.site.to_dict()
        if site_d:
            d["site"] = site_d

        # Sections
        if self.sections:
            d["sections"] = {
                name: section.to_dict()
                for name, section in sorted(self.sections.items())
            }

        # LLM strategies
        if self.llm_strategies:
            d["llm_strategies"] = dict(sorted(self.llm_strategies.items()))

        # Quality
        d["quality"] = self.quality.to_dict()

        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Recipe:
        """Deserialize recipe from a dictionary (parsed YAML/JSON)."""
        # Parse sections
        sections: Dict[str, SectionSpec] = {}
        for name, section_data in data.get("sections", {}).items():
            if isinstance(section_data, dict):
                sections[name] = SectionSpec.from_dict(name, section_data)

        return cls(
            name=data.get("name", ""),
            version=data.get("version", "1.0"),
            description=data.get("description", ""),
            product=data.get("product", ""),
            platform=data.get("platform", ""),
            family=data.get("family", ""),
            site=SiteSpec.from_dict(data.get("site")),
            sections=sections,
            llm_strategies=data.get("llm_strategies", {}),
            quality=QualitySpec.from_dict(data.get("quality")),
        )

    # ── Validation ────────────────────────────────────────────────────

    def validate(self) -> List[str]:
        """Validate recipe for common issues.

        Returns list of error messages (empty = valid).
        """
        errors: List[str] = []

        # Every page must have role and slug
        for section_name, section in self.sections.items():
            for i, page in enumerate(section.pages):
                if not page.role:
                    errors.append(
                        f"sections.{section_name}.pages[{i}]: missing 'role'"
                    )
                if not page.slug:
                    errors.append(
                        f"sections.{section_name}.pages[{i}]: missing 'slug'"
                    )

            # Check for duplicate slugs within a section
            slugs = [p.slug for p in section.pages if p.slug]
            seen = set()
            for slug in slugs:
                if slug in seen:
                    errors.append(
                        f"sections.{section_name}: duplicate slug '{slug}'"
                    )
                seen.add(slug)

        # Quality bounds
        for dim in ("min_content_quality", "min_technical_accuracy", "min_usability"):
            val = getattr(self.quality, dim)
            if val < 1 or val > 5:
                errors.append(f"quality.{dim}: must be 1-5, got {val}")

        if self.quality.max_review_rounds < 1:
            errors.append(
                f"quality.max_review_rounds: must be >= 1, got {self.quality.max_review_rounds}"
            )

        # LLM strategy keys must follow worker.content_type format
        for key in self.llm_strategies:
            if "." not in key:
                errors.append(
                    f"llm_strategies: key '{key}' must be 'worker.content_type' format"
                )

        return errors


# ── Loading Helpers ───────────────────────────────────────────────────────


def load_recipe(path: str | Path) -> Recipe:
    """Load a recipe from a YAML or JSON file.

    Supports .yaml, .yml, and .json extensions.

    Args:
        path: Path to recipe file.

    Returns:
        Parsed Recipe instance.

    Raises:
        FileNotFoundError: If recipe file doesn't exist.
        ValueError: If file format is unsupported or content is invalid.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Recipe file not found: {path}")

    content = path.read_text(encoding="utf-8")

    if path.suffix in (".yaml", ".yml"):
        try:
            import yaml
            data = yaml.safe_load(content)
        except ImportError:
            # Fallback: try JSON-compatible subset of YAML
            raise ValueError(
                "PyYAML not installed. Install with: pip install pyyaml"
            )
    elif path.suffix == ".json":
        data = json.loads(content)
    else:
        raise ValueError(f"Unsupported recipe file format: {path.suffix}")

    if not isinstance(data, dict):
        raise ValueError(f"Recipe file must contain a mapping, got {type(data).__name__}")

    recipe = Recipe.from_dict(data)

    # Validate
    errors = recipe.validate()
    if errors:
        error_list = "\n  ".join(errors)
        logger.warning(f"Recipe '{path}' has validation issues:\n  {error_list}")

    return recipe


def recipe_from_run_config(run_config: Dict[str, Any]) -> Optional[Recipe]:
    """Extract a Recipe from run_config if one is embedded.

    Looks for run_config["recipe"] dict. Returns None if not present.
    """
    recipe_data = run_config.get("recipe")
    if not isinstance(recipe_data, dict):
        return None
    return Recipe.from_dict(recipe_data)
