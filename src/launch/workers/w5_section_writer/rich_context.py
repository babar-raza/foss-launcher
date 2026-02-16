"""
RichContext dataclass and builder for W5 SectionWriter.

Spec reference: specs/21_worker_contracts.md 'W5 RichContext Contract'

The RichContext aggregates all contextual information needed for content generation:
- Product profile (name, tagline, description, audience, license)
- Page metadata (role, focus, SEO keywords, depth guidance, scenario coverage)
- Claims (page-specific claims, workflows)
- Code context (snippets, code understanding, API surface)
- Cross-page context (sibling pages, summaries from other pages)
- Constraints (forbidden topics, required headings, claim quotas)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class RichContext:
    """
    Rich contextual information for content generation.

    Organized into 6 categories:
    1. Product profile (5 fields)
    2. Page metadata (5 fields)
    3. Claims (2 fields)
    4. Code context (3 fields)
    5. Cross-page (2 fields)
    6. Constraints (3 fields)
    """

    # Product profile (5)
    product_name: str = ""
    tagline: str = ""
    short_description: str = ""
    audience: str = ""
    license_info: str = ""

    # Page metadata (5)
    page_role: str = ""
    primary_focus: str = ""
    seo_keywords: List[str] = field(default_factory=list)
    depth_guidance: str = ""
    scenario_coverage: str = ""

    # Claims (2)
    page_claims: List[Dict] = field(default_factory=list)
    workflows: List[Dict] = field(default_factory=list)

    # Code context (3)
    relevant_snippets: List[Dict] = field(default_factory=list)
    code_understanding: Dict = field(default_factory=dict)
    api_surface: Dict = field(default_factory=dict)

    # Cross-page (2)
    sibling_pages: List[Dict] = field(default_factory=list)
    cross_page_summaries: Dict[str, str] = field(default_factory=dict)

    # Constraints (3)
    forbidden_topics: List[str] = field(default_factory=list)
    required_headings: List[str] = field(default_factory=list)
    claim_quota: Dict[str, int] = field(default_factory=dict)

    def to_prompt_vars(self) -> Dict[str, str]:
        """
        Format all fields as a Dict[str, str] for template substitution.

        List and dict fields are formatted as readable text:
        - Lists: newline-separated items
        - Dicts: JSON-like or custom formatting

        Returns:
            Dictionary mapping variable names to string values.
        """
        return {
            # Product profile
            "product_name": self.product_name,
            "tagline": self.tagline,
            "short_description": self.short_description,
            "audience": self.audience,
            "license_info": self.license_info,

            # Page metadata
            "page_role": self.page_role,
            "primary_focus": self.primary_focus,
            "seo_keywords": ", ".join(self.seo_keywords),
            "depth_guidance": self.depth_guidance,
            "scenario_coverage": self.scenario_coverage,

            # Claims
            "page_claims": self._format_claims(self.page_claims),
            "workflows": self._format_workflows(self.workflows),

            # Code context
            "relevant_snippets": self._format_snippets(self.relevant_snippets),
            "code_understanding": self._format_code_understanding(self.code_understanding),
            "api_surface": self._format_api_surface(self.api_surface),

            # Cross-page
            "sibling_pages": self._format_sibling_pages(self.sibling_pages),
            "cross_page_summaries": self._format_cross_page_summaries(self.cross_page_summaries),

            # Constraints
            "forbidden_topics": self._format_list(self.forbidden_topics),
            "required_headings": self._format_list(self.required_headings),
            "claim_quota": self._format_claim_quota(self.claim_quota),
        }

    def _format_claims(self, claims: List[Dict]) -> str:
        """Format claims as readable text."""
        if not claims:
            return "None"

        lines = []
        for claim in claims:
            claim_id = claim.get("claim_id", "unknown")
            claim_text = claim.get("claim_text", "")
            claim_kind = claim.get("claim_kind", "")
            lines.append(f"[{claim_id}] ({claim_kind}) {claim_text}")

        return "\n".join(lines)

    def _format_workflows(self, workflows: List[Dict]) -> str:
        """Format workflows as readable text."""
        if not workflows:
            return "None"

        lines = []
        for wf in workflows:
            workflow_id = wf.get("workflow_id", "unknown")
            title = wf.get("title", "")
            steps = wf.get("steps", [])
            lines.append(f"[{workflow_id}] {title} ({len(steps)} steps)")

        return "\n".join(lines)

    def _format_snippets(self, snippets: List[Dict]) -> str:
        """Format snippets as readable text."""
        if not snippets:
            return "None"

        lines = []
        for snippet in snippets:
            snippet_id = snippet.get("snippet_id", "unknown")
            description = snippet.get("description", "")
            lines.append(f"[{snippet_id}] {description}")

        return "\n".join(lines)

    def _format_code_understanding(self, code_understanding: Dict) -> str:
        """Format code understanding as readable text."""
        if not code_understanding:
            return "None"

        lines = []
        classes = code_understanding.get("classes", [])
        functions = code_understanding.get("functions", [])

        if classes:
            lines.append(f"Classes: {len(classes)}")
        if functions:
            lines.append(f"Functions: {len(functions)}")

        return ", ".join(lines) if lines else "None"

    def _format_api_surface(self, api_surface: Dict) -> str:
        """Format API surface as readable text."""
        if not api_surface:
            return "None"

        lines = []
        for key, value in api_surface.items():
            if isinstance(value, list):
                lines.append(f"{key}: {len(value)}")
            else:
                lines.append(f"{key}: {value}")

        return ", ".join(lines) if lines else "None"

    def _format_sibling_pages(self, sibling_pages: List[Dict]) -> str:
        """Format sibling pages as readable text."""
        if not sibling_pages:
            return "None"

        lines = []
        for page in sibling_pages:
            slug = page.get("slug", "unknown")
            title = page.get("title", "")
            lines.append(f"- {slug}: {title}")

        return "\n".join(lines)

    def _format_cross_page_summaries(self, summaries: Dict[str, str]) -> str:
        """Format cross-page summaries as readable text."""
        if not summaries:
            return "None"

        lines = []
        for slug, summary in summaries.items():
            lines.append(f"[{slug}] {summary}")

        return "\n".join(lines)

    def _format_list(self, items: List[str]) -> str:
        """Format a list of strings as newline-separated items."""
        if not items:
            return "None"
        return "\n".join(f"- {item}" for item in items)

    def _format_claim_quota(self, quota: Dict[str, int]) -> str:
        """Format claim quota as readable text."""
        if not quota:
            return "None"

        lines = []
        for claim_kind, count in quota.items():
            lines.append(f"{claim_kind}: {count}")

        return ", ".join(lines)


def build_rich_context(
    page: Dict,
    product_facts: Dict,
    snippet_catalog: Dict,
    evidence_map: Dict = None,
    page_plan: Dict = None,
    cross_page_summaries: Dict[str, str] = None,
    code_understanding: Dict = None,
) -> RichContext:
    """
    Build a RichContext from page, product_facts, and optional context sources.

    Args:
        page: Page specification from page plan.
        product_facts: Product facts JSON (may be empty or missing fields).
        snippet_catalog: Snippet catalog JSON.
        evidence_map: Optional evidence mapping (claim_id -> evidence).
        page_plan: Optional full page plan (for sibling pages).
        cross_page_summaries: Optional summaries from previously generated pages.
        code_understanding: Optional code understanding data.

    Returns:
        RichContext instance with all fields populated.
    """
    ctx = RichContext()

    # Product profile (5)
    ctx.product_name = product_facts.get("product_name", "")

    positioning = product_facts.get("positioning", {})
    ctx.tagline = positioning.get("tagline", "")
    ctx.short_description = positioning.get("value_proposition", "")
    ctx.audience = positioning.get("audience", "")

    metadata = product_facts.get("metadata", {})
    ctx.license_info = metadata.get("license", "")

    # Page metadata (5)
    ctx.page_role = page.get("page_role", "")
    ctx.primary_focus = page.get("primary_focus", "")
    ctx.seo_keywords = page.get("seo_keywords", [])
    ctx.depth_guidance = _get_depth_guidance(ctx.page_role)
    ctx.scenario_coverage = page.get("scenario_coverage", "")

    # Claims (2)
    ctx.page_claims = _extract_page_claims(page, product_facts, evidence_map)
    ctx.workflows = _extract_workflows(page, product_facts)

    # Code context (3)
    ctx.relevant_snippets = _extract_relevant_snippets(page, snippet_catalog)
    ctx.code_understanding = code_understanding or {}
    ctx.api_surface = _extract_api_surface(code_understanding)

    # Cross-page (2)
    ctx.sibling_pages = _extract_sibling_pages(page, page_plan)
    ctx.cross_page_summaries = cross_page_summaries or {}

    # Constraints (3)
    ctx.forbidden_topics = page.get("forbidden_topics", [])
    ctx.required_headings = page.get("required_headings", [])
    ctx.claim_quota = page.get("claim_quota", {})

    return ctx


def _get_depth_guidance(page_role: str) -> str:
    """
    Map page_role to depth guidance string.

    Args:
        page_role: Page role (comprehensive_guide, tutorial, faq, etc.)

    Returns:
        Depth guidance string for content generation.
    """
    guidance_map = {
        "comprehensive_guide": "Rich depth: 800+ words, cover all aspects",
        "tutorial": "Step-by-step: 600+ words, hands-on walkthrough",
        "faq": "Concise answers: 50+ words each, 8+ Q&A pairs",
        "troubleshooting": "Problem-solution: 50+ words per entry",
        "toc": "Minimal: brief intro + child page listing",
    }

    return guidance_map.get(page_role, "Standard: 300-500 words")


def _extract_page_claims(
    page: Dict,
    product_facts: Dict,
    evidence_map: Dict = None,
) -> List[Dict]:
    """
    Extract claims relevant to this page.

    Args:
        page: Page specification with claim_ids.
        product_facts: Product facts with claims list.
        evidence_map: Optional evidence mapping.

    Returns:
        List of claim dicts relevant to this page.
    """
    page_claim_ids = set(page.get("claim_ids", []))
    if not page_claim_ids:
        return []

    all_claims = product_facts.get("claims", [])
    page_claims = [c for c in all_claims if c.get("claim_id") in page_claim_ids]

    # Enrich with evidence if available
    if evidence_map:
        for claim in page_claims:
            claim_id = claim.get("claim_id")
            if claim_id in evidence_map:
                claim["evidence"] = evidence_map[claim_id]

    return page_claims


def _extract_workflows(page: Dict, product_facts: Dict) -> List[Dict]:
    """
    Extract workflows relevant to this page.

    Args:
        page: Page specification with workflow_ids.
        product_facts: Product facts with workflows list.

    Returns:
        List of workflow dicts relevant to this page.
    """
    page_workflow_ids = set(page.get("workflow_ids", []))
    if not page_workflow_ids:
        return []

    all_workflows = product_facts.get("workflows", [])
    return [wf for wf in all_workflows if wf.get("workflow_id") in page_workflow_ids]


def _extract_relevant_snippets(page: Dict, snippet_catalog: Dict) -> List[Dict]:
    """
    Extract snippets relevant to this page.

    Args:
        page: Page specification with snippet_ids.
        snippet_catalog: Snippet catalog with snippets list.

    Returns:
        List of snippet dicts relevant to this page.
    """
    page_snippet_ids = set(page.get("snippet_ids", []))
    if not page_snippet_ids:
        return []

    all_snippets = snippet_catalog.get("snippets", [])
    return [s for s in all_snippets if s.get("snippet_id") in page_snippet_ids]


def _extract_api_surface(code_understanding: Dict = None) -> Dict:
    """
    Extract API surface summary from code understanding.

    Args:
        code_understanding: Code understanding data.

    Returns:
        Dict with API surface summary (classes, functions, etc.)
    """
    if not code_understanding:
        return {}

    return {
        "classes": len(code_understanding.get("classes", [])),
        "functions": len(code_understanding.get("functions", [])),
        "modules": len(code_understanding.get("modules", [])),
    }


def _extract_sibling_pages(page: Dict, page_plan: Dict = None) -> List[Dict]:
    """
    Extract sibling pages (same parent section).

    Args:
        page: Current page specification.
        page_plan: Full page plan with all pages.

    Returns:
        List of sibling page dicts.
    """
    if not page_plan:
        return []

    current_section = page.get("section_path", "")
    current_slug = page.get("slug", "")

    all_pages = page_plan.get("pages", [])
    siblings = [
        {"slug": p.get("slug"), "title": p.get("title")}
        for p in all_pages
        if p.get("section_path") == current_section and p.get("slug") != current_slug
    ]

    return siblings
