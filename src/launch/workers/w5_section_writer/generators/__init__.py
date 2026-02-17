"""Generator Plugin Registry for W5 SectionWriter.

Replaces the if/elif dispatch chain in generate_section_content() with a
pluggable registry. New content types = register a generator function.
No changes to worker.py dispatch logic needed.

Usage:
    from launch.workers.w5_section_writer.generators import GENERATOR_REGISTRY

    # Get a generator for a page_role
    gen_fn = GENERATOR_REGISTRY.get("faq")
    if gen_fn:
        content = gen_fn(page, product_facts, snippet_catalog, llm_client=llm_client)

    # Register a custom generator
    GENERATOR_REGISTRY.register("api_reference", my_api_ref_generator)

    # Register from config
    GENERATOR_REGISTRY.register_from_config({"tutorial": "my_module.generate_tutorial"})

Architecture:
    Each generator follows the standard interface:
        def generate(page, product_facts, snippet_catalog, *, llm_client=None, **kwargs) -> str

    TOC generator has a special interface (needs page_plan):
        def generate_toc(page, product_facts, page_plan) -> str

    The registry normalizes these into a uniform callable.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Set

from ....util.logging import get_logger

logger = get_logger()

# Type alias for generator functions
# Standard: (page, product_facts, snippet_catalog, *, llm_client=None, **kwargs) -> str
GeneratorFn = Callable[..., str]


class GeneratorRegistry:
    """Registry mapping page_role names to generator functions.

    Supports:
    - Direct registration: registry.register("faq", generate_faq)
    - Multi-role aliasing: blog, announcement, blog_announcement all map to same generator
    - Fallback: returns None for unknown page_roles (caller handles fallback)
    - Introspection: all_roles, has(role), len()
    """

    def __init__(self):
        self._generators: Dict[str, GeneratorFn] = {}
        self._metadata: Dict[str, Dict[str, Any]] = {}

    def register(
        self,
        page_role: str,
        generator_fn: GeneratorFn,
        *,
        aliases: Optional[List[str]] = None,
        description: str = "",
        requires_page_plan: bool = False,
    ) -> None:
        """Register a generator function for a page_role.

        Args:
            page_role: Primary page_role name (e.g., "faq", "tutorial")
            generator_fn: Generator function matching the standard interface
            aliases: Additional page_role names that map to the same generator
            description: Human-readable description
            requires_page_plan: If True, this generator needs page_plan parameter
        """
        self._generators[page_role] = generator_fn
        self._metadata[page_role] = {
            "description": description,
            "requires_page_plan": requires_page_plan,
        }

        if aliases:
            for alias in aliases:
                self._generators[alias] = generator_fn
                self._metadata[alias] = self._metadata[page_role]

    def get(self, page_role: str) -> Optional[GeneratorFn]:
        """Get generator function for a page_role, or None if not registered."""
        return self._generators.get(page_role)

    def has(self, page_role: str) -> bool:
        """Check if a generator is registered for a page_role."""
        return page_role in self._generators

    def requires_page_plan(self, page_role: str) -> bool:
        """Check if a generator needs the page_plan parameter."""
        meta = self._metadata.get(page_role, {})
        return meta.get("requires_page_plan", False)

    @property
    def all_roles(self) -> List[str]:
        """Return all registered page_role names (sorted)."""
        return sorted(self._generators.keys())

    def __len__(self) -> int:
        return len(self._generators)

    def __contains__(self, page_role: str) -> bool:
        return page_role in self._generators

    def __repr__(self) -> str:
        roles = ", ".join(sorted(self._generators.keys()))
        return f"GeneratorRegistry({len(self._generators)} roles: {roles})"


# ── Singleton Registry ────────────────────────────────────────────────────────

GENERATOR_REGISTRY = GeneratorRegistry()


def _register_defaults():
    """Register all default generators from content_generators.py.

    Called lazily on first access to avoid circular imports.
    TC-1770: Generators now live in .content_generators (extracted from worker.py).
    """
    if len(GENERATOR_REGISTRY) > 0:
        return  # Already registered

    from .content_generators import (
        generate_toc_content,
        generate_comprehensive_guide_content,
        generate_feature_showcase_content,
        generate_troubleshooting_content,
        generate_faq_content,
        generate_best_practices_content,
        generate_tutorial_content,
        generate_blog_content,
        generate_performance_content,
        generate_getting_started_content,
    )

    GENERATOR_REGISTRY.register(
        "toc", generate_toc_content,
        description="Table of contents hub page",
        requires_page_plan=True,
    )
    GENERATOR_REGISTRY.register(
        "comprehensive_guide", generate_comprehensive_guide_content,
        description="Full product guide with workflows and examples",
    )
    GENERATOR_REGISTRY.register(
        "feature_showcase", generate_feature_showcase_content,
        description="Feature highlights page",
    )
    GENERATOR_REGISTRY.register(
        "troubleshooting", generate_troubleshooting_content,
        description="Troubleshooting Q&A page",
    )
    GENERATOR_REGISTRY.register(
        "faq", generate_faq_content,
        description="FAQ page",
    )
    GENERATOR_REGISTRY.register(
        "best_practices", generate_best_practices_content,
        description="Best practices guide",
    )
    GENERATOR_REGISTRY.register(
        "tutorial", generate_tutorial_content,
        description="Step-by-step tutorial",
    )
    GENERATOR_REGISTRY.register(
        "blog", generate_blog_content,
        aliases=["announcement", "blog_announcement"],
        description="Blog or announcement post",
    )
    GENERATOR_REGISTRY.register(
        "performance_guide", generate_performance_content,
        description="Performance optimization guide",
    )
    GENERATOR_REGISTRY.register(
        "getting_started", generate_getting_started_content,
        aliases=["getting-started", "quickstart"],
        description="Getting started guide with code examples",
    )

    logger.info(f"[W5 Generators] Registered {len(GENERATOR_REGISTRY)} generators: {GENERATOR_REGISTRY.all_roles}")


def get_registry() -> GeneratorRegistry:
    """Get the initialized generator registry (lazy initialization)."""
    _register_defaults()
    return GENERATOR_REGISTRY
