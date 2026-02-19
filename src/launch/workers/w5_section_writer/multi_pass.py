"""
Multi-pass content generation orchestrator for W5 SectionWriter.

Spec reference: specs/21_worker_contracts.md 'W5 Multi-Pass Generation Contract'

The MultiPassOrchestrator implements a 3-pass generation strategy:
1. OUTLINE: Generate content structure with claim mapping
2. DRAFT: Generate full content from outline
3. REFINE: Polish draft with cross-page awareness

Each pass includes validation and fallback to deterministic generation.
Hallucination detection runs after draft generation.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from .rich_context import RichContext

logger = logging.getLogger(__name__)


@dataclass
class MultiPassResult:
    """Result of multi-pass content generation."""

    content: str
    outline: Optional[Dict] = None
    risks: List[Dict] = field(default_factory=list)
    success: bool = True
    pass_used: int = 0  # Which pass produced the final content (1=outline only, 2=draft, 3=refined)


class MultiPassOrchestrator:
    """
    3-pass content generation orchestrator.

    Passes:
    1. OUTLINE: Structure with claim mapping
    2. DRAFT: Full content generation
    3. REFINE: Polish with cross-page awareness

    Includes validation, fallback, and hallucination detection.
    """

    def __init__(self, llm_client, prompt_loader, run_config=None):
        """
        Initialize orchestrator.

        Args:
            llm_client: LLM client for generation.
            prompt_loader: Prompt loader for system/page prompts.
            run_config: Optional run configuration.
        """
        self.llm_client = llm_client
        self.prompt_loader = prompt_loader
        self.run_config = run_config
        self.cross_page_summaries: Dict[str, str] = {}

    def generate(self, page: Dict, rich_ctx: "RichContext") -> MultiPassResult:
        """
        3-pass generation: outline -> draft -> refine.

        Args:
            page: Page specification.
            rich_ctx: Rich context for generation.

        Returns:
            MultiPassResult with final content and metadata.
        """
        # Get config
        mp_config = self.run_config.get_multi_pass_config() if self.run_config else {}

        # Pass 1: OUTLINE
        logger.info(f"Pass 1: Generating outline for {page.get('slug', 'unknown')}")
        outline = self._generate_outline(rich_ctx, page)
        if not self._validate_outline(outline, page):
            logger.warning(f"Outline validation failed, using deterministic outline")
            outline = self._deterministic_outline(page, rich_ctx)

        # Pass 2: DRAFT
        logger.info(f"Pass 2: Generating draft for {page.get('slug', 'unknown')}")
        draft = self._generate_draft(rich_ctx, outline, page)
        if not self._validate_draft(draft, page):
            logger.error(f"Draft validation failed, using deterministic fallback")
            return MultiPassResult(
                content=self._deterministic_fallback(page, rich_ctx),
                pass_used=0,
                success=False
            )

        # Check hallucination risk
        logger.info(f"Detecting hallucination risks in draft")
        risks = detect_hallucination_risk(draft, rich_ctx)
        if any(r.get("level") == "HIGH" for r in risks):
            logger.error(f"High hallucination risk detected, using deterministic fallback")
            return MultiPassResult(
                content=self._deterministic_fallback(page, rich_ctx),
                risks=risks,
                pass_used=0,
                success=False
            )

        # Pass 3: REFINE (skip for thin pages if configured)
        skip_refine = mp_config.get("skip_refine_for_thin_pages", True)
        word_count = len(draft.split())
        if skip_refine and word_count < 200:
            logger.info(f"Skipping refinement for thin page ({word_count} words)")
            self._update_cross_page_summaries(draft, page)
            return MultiPassResult(content=draft, outline=outline, risks=risks, pass_used=2)

        logger.info(f"Pass 3: Refining draft for {page.get('slug', 'unknown')}")
        refined = self._refine_draft(rich_ctx, outline, draft, page)
        if not self._validate_refinement(draft, refined):
            logger.warning(f"Refinement validation failed, keeping draft")
            refined = draft  # Keep draft if refinement failed

        self._update_cross_page_summaries(refined, page)
        return MultiPassResult(content=refined, outline=outline, risks=risks, pass_used=3)

    def _generate_outline(self, rich_ctx: "RichContext", page: Dict) -> Optional[Dict]:
        """
        Generate content outline with claim mapping.

        Args:
            rich_ctx: Rich context for generation.
            page: Page specification.

        Returns:
            Outline dict or None if generation failed.
        """
        try:
            # Load system prompt
            prompt_vars = rich_ctx.to_prompt_vars()
            prompt_vars["slug"] = page.get("slug", "")
            prompt_vars["title"] = page.get("title", "")

            system_prompt = self.prompt_loader.load("system/content_architect", **prompt_vars)

            # Generate outline via chat_completion
            # I-4: Include claim_text in outline request so draft pass has concrete material
            response_data = self.llm_client.chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt.text},
                    {
                        "role": "user",
                        "content": (
                            "Generate the content outline as JSON. "
                            "Each section must include 'claim_ids' (list of IDs) AND "
                            "'claim_texts' (list of corresponding claim text strings) "
                            "so the draft writer has concrete material to expand — "
                            "do not include IDs without their text."
                        ),
                    },
                ],
                call_id=f"mp_outline_{page.get('slug', 'unknown')}",
                temperature=0.3,
                max_tokens=2000,
                response_format={"type": "json_object"},
            )

            # Parse JSON from response
            # Try to extract JSON from markdown code blocks if present
            content = response_data["content"].strip()
            if "```json" in content:
                json_match = re.search(r"```json\s*\n(.*?)\n```", content, re.DOTALL)
                if json_match:
                    content = json_match.group(1)
            elif "```" in content:
                json_match = re.search(r"```\s*\n(.*?)\n```", content, re.DOTALL)
                if json_match:
                    content = json_match.group(1)

            outline = json.loads(content)
            return outline

        except Exception as e:
            logger.error(f"Outline generation failed: {e}")
            return None

    def _generate_draft(self, rich_ctx: "RichContext", outline: Dict, page: Dict) -> str:
        """
        Generate full content from outline.

        Args:
            rich_ctx: Rich context for generation.
            outline: Content outline.
            page: Page specification.

        Returns:
            Draft content string.
        """
        try:
            # Load system prompt with anti-hallucination fragment
            prompt_vars = rich_ctx.to_prompt_vars()
            prompt_vars["slug"] = page.get("slug", "")
            prompt_vars["title"] = page.get("title", "")
            prompt_vars["outline"] = json.dumps(outline, indent=2)

            system_prompt = self.prompt_loader.load_with_fragments(
                "system/technical_writer",
                ["fragments/anti_hallucination"],
                **prompt_vars
            )

            # Load page-role specific prompt
            page_role = rich_ctx.page_role or "default"
            try:
                page_prompt = self.prompt_loader.load(f"pages/{page_role}", **prompt_vars)
            except Exception as e:
                logger.warning(f"Failed to load page prompt for {page_role}, using default: {e}")
                page_prompt = self.prompt_loader.load("pages/default", **prompt_vars)

            # Combine system + page prompts
            combined_prompt = f"{system_prompt.text}\n\n{page_prompt.text}"

            # Generate draft via chat_completion
            response_data = self.llm_client.chat_completion(
                messages=[
                    {"role": "system", "content": combined_prompt},
                    {"role": "user", "content": f"Write the full page for: {page.get('title', '')}"},
                ],
                call_id=f"mp_draft_{page.get('slug', 'unknown')}",
                temperature=0.1,
                max_tokens=4000,
            )

            return response_data["content"].strip()

        except Exception as e:
            logger.error(f"Draft generation failed: {e}")
            return ""

    def _refine_draft(self, rich_ctx: "RichContext", outline: Dict, draft: str, page: Dict) -> str:
        """
        Refine draft with cross-page awareness.

        Args:
            rich_ctx: Rich context for generation.
            outline: Content outline.
            draft: Draft content.
            page: Page specification.

        Returns:
            Refined content string.
        """
        try:
            # Load system prompt
            prompt_vars = rich_ctx.to_prompt_vars()
            prompt_vars["slug"] = page.get("slug", "")
            prompt_vars["title"] = page.get("title", "")
            prompt_vars["outline"] = json.dumps(outline, indent=2)
            prompt_vars["draft"] = draft
            prompt_vars["cross_page_summaries"] = self._format_cross_page_summaries(
                self.cross_page_summaries
            )

            system_prompt = self.prompt_loader.load("system/content_editor", **prompt_vars)

            # Generate refinement via chat_completion
            response_data = self.llm_client.chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt.text},
                    {"role": "user", "content": "Refine the draft for clarity, flow, and cross-page consistency."},
                ],
                call_id=f"mp_refine_{page.get('slug', 'unknown')}",
                temperature=0.3,
                max_tokens=4000,
            )

            return response_data["content"].strip()

        except Exception as e:
            logger.error(f"Refinement failed: {e}")
            return draft

    def _validate_outline(self, outline: Optional[Dict], page: Dict) -> bool:
        """
        Validate outline structure.

        Args:
            outline: Outline dict to validate.
            page: Page specification.

        Returns:
            True if outline is valid.
        """
        if not outline:
            return False

        if not isinstance(outline, dict):
            logger.warning(f"Outline is not a dict: {type(outline)}")
            return False

        if "sections" not in outline:
            logger.warning(f"Outline missing 'sections' key")
            return False

        sections = outline["sections"]
        if not isinstance(sections, list):
            logger.warning(f"Outline 'sections' is not a list: {type(sections)}")
            return False

        for i, section in enumerate(sections):
            if not isinstance(section, dict):
                logger.warning(f"Section {i} is not a dict: {type(section)}")
                return False

            if "heading" not in section:
                logger.warning(f"Section {i} missing 'heading' key")
                return False

            if "claim_ids" not in section:
                logger.warning(f"Section {i} missing 'claim_ids' key")
                return False

        return True

    def _validate_draft(self, draft: str, page: Dict) -> bool:
        """
        Validate draft content.

        Args:
            draft: Draft content string.
            page: Page specification.

        Returns:
            True if draft is valid.
        """
        if not draft:
            logger.warning(f"Draft is empty")
            return False

        # Check minimum word count (configurable)
        min_words = 50  # Could be made configurable
        word_count = len(draft.split())
        if word_count < min_words:
            logger.warning(f"Draft too short: {word_count} words (minimum {min_words})")
            return False

        # Check for at least 1 claim marker (HTML comment or bracket format)
        claim_markers = re.findall(
            r"<!--\s*claim:\s*[a-zA-Z0-9_\-]+\s*-->|\[claim:\s*[a-zA-Z0-9_\-]+\]",
            draft,
        )
        if not claim_markers:
            logger.warning(f"Draft contains no claim markers")
            return False

        return True

    def _validate_refinement(self, draft: str, refined: str) -> bool:
        """
        Validate that refinement preserved key elements.

        Args:
            draft: Original draft content.
            refined: Refined content.

        Returns:
            True if refinement is valid.
        """
        if not refined:
            logger.warning(f"Refined content is empty")
            return False

        # Check claim markers preserved (count in refined >= count in draft * 0.9)
        _marker_re = r"<!--\s*claim:\s*[a-zA-Z0-9_\-]+\s*-->|\[claim:\s*[a-zA-Z0-9_\-]+\]"
        draft_markers = re.findall(_marker_re, draft)
        refined_markers = re.findall(_marker_re, refined)

        min_markers = int(len(draft_markers) * 0.9)
        if len(refined_markers) < min_markers:
            logger.warning(
                f"Refinement lost too many claim markers: "
                f"{len(refined_markers)} < {min_markers} (90% of {len(draft_markers)})"
            )
            return False

        # Check word count not decreased >10%
        draft_words = len(draft.split())
        refined_words = len(refined.split())

        min_words = int(draft_words * 0.9)
        if refined_words < min_words:
            logger.warning(
                f"Refinement reduced word count too much: "
                f"{refined_words} < {min_words} (90% of {draft_words})"
            )
            return False

        return True

    def _deterministic_outline(self, page: Dict, rich_ctx: "RichContext") -> Dict:
        """
        Create basic outline from required_headings and page_claims.

        Args:
            page: Page specification.
            rich_ctx: Rich context.

        Returns:
            Deterministic outline dict.
        """
        sections = []

        # Use required headings if available
        required_headings = rich_ctx.required_headings
        if required_headings:
            for heading in required_headings:
                sections.append({"heading": heading, "claim_ids": []})
        else:
            # Default sections based on page role
            page_role = rich_ctx.page_role
            if page_role == "tutorial":
                sections = [
                    {"heading": "Introduction", "claim_ids": []},
                    {"heading": "Prerequisites", "claim_ids": []},
                    {"heading": "Step-by-Step Guide", "claim_ids": []},
                    {"heading": "Conclusion", "claim_ids": []},
                ]
            elif page_role == "faq":
                sections = [
                    {"heading": "Frequently Asked Questions", "claim_ids": []},
                ]
            else:
                sections = [
                    {"heading": "Overview", "claim_ids": []},
                    {"heading": "Details", "claim_ids": []},
                ]

        # Distribute claims across sections
        # I-4: Include claim_text alongside claim_id so draft LLM has concrete material
        page_claims = rich_ctx.page_claims
        if page_claims and sections:
            claims_per_section = len(page_claims) // len(sections)
            remainder = len(page_claims) % len(sections)

            claim_idx = 0
            for i, section in enumerate(sections):
                num_claims = claims_per_section + (1 if i < remainder else 0)
                slice_claims = [
                    page_claims[claim_idx + j]
                    for j in range(num_claims)
                    if claim_idx + j < len(page_claims)
                ]
                section["claim_ids"] = [c.get("claim_id", "") for c in slice_claims]
                section["claim_texts"] = [c.get("claim_text", "") for c in slice_claims]
                claim_idx += num_claims

        return {"sections": sections}

    def _deterministic_fallback(self, page: Dict, rich_ctx: "RichContext") -> str:
        """
        Generate minimal content with headings and claim markers only (no LLM).

        Args:
            page: Page specification.
            rich_ctx: Rich context.

        Returns:
            Minimal content string.
        """
        lines = []

        # Title
        title = page.get("title", "")
        if title:
            lines.append(f"# {title}")
            lines.append("")

        # Introduction
        lines.append("## Introduction")
        lines.append("")
        short_description = rich_ctx.short_description
        if short_description:
            lines.append(short_description)
            lines.append("")

        # Required headings with claim markers
        required_headings = rich_ctx.required_headings
        page_claims = rich_ctx.page_claims

        if required_headings:
            claims_per_section = len(page_claims) // len(required_headings) if page_claims else 0

            for i, heading in enumerate(required_headings):
                lines.append(f"## {heading}")
                lines.append("")

                # Add claim markers for this section
                start_idx = i * claims_per_section
                end_idx = start_idx + claims_per_section
                for claim in page_claims[start_idx:end_idx]:
                    claim_id = claim.get("claim_id", "")
                    claim_text = claim.get("claim_text", "")
                    lines.append(f"<!-- claim: {claim_id} --> {claim_text}")
                    lines.append("")

        else:
            # Just list all claims
            lines.append("## Details")
            lines.append("")
            for claim in page_claims:
                claim_id = claim.get("claim_id", "")
                claim_text = claim.get("claim_text", "")
                lines.append(f"<!-- claim: {claim_id} --> {claim_text}")
                lines.append("")

        return "\n".join(lines)

    def _update_cross_page_summaries(self, content: str, page: Dict) -> None:
        """
        Extract summary from content and store in cross_page_summaries.

        Args:
            content: Generated content.
            page: Page specification.
        """
        slug = page.get("slug", "")
        if not slug:
            return

        # Extract first 200 characters as summary
        # Strip markdown headings and claim markers for cleaner summary
        clean_content = re.sub(r"^#+\s+.*$", "", content, flags=re.MULTILINE)
        clean_content = re.sub(
            r"<!--\s*claim:\s*[a-zA-Z0-9_\-]+\s*-->|\[claim:\s*[a-zA-Z0-9_\-]+\]",
            "",
            clean_content,
        )
        clean_content = clean_content.strip()

        summary = clean_content[:200]
        if len(clean_content) > 200:
            summary += "..."

        self.cross_page_summaries[slug] = summary

    def _format_cross_page_summaries(self, summaries: Dict[str, str]) -> str:
        """
        Format cross-page summaries for prompt.

        Args:
            summaries: Dict mapping slug to summary.

        Returns:
            Formatted string.
        """
        if not summaries:
            return "None"

        lines = []
        for slug, summary in summaries.items():
            lines.append(f"[{slug}] {summary}")

        return "\n".join(lines)


def detect_hallucination_risk(content: str, rich_ctx: "RichContext") -> List[Dict]:
    """
    8-layer hallucination detection.

    Layers:
    2. API names not in whitelist
    3. Code blocks not matching any snippet (basic Jaccard)
    4. Claim marker density check (< 1 per 150 words)
    7. Performance claims without claim markers

    Args:
        content: Generated content to check.
        rich_ctx: Rich context with reference data.

    Returns:
        List of risk dicts with layer, level, message, location.
    """
    risks = []

    # Layer 2: API names not in whitelist
    risks.extend(_check_api_names(content, rich_ctx))

    # Layer 3: Code blocks not matching any snippet
    risks.extend(_check_code_blocks(content, rich_ctx))

    # Layer 4: Claim marker density
    risks.extend(_check_claim_density(content))

    # Layer 7: Performance claims without claim markers
    risks.extend(_check_performance_claims(content))

    return risks


def _check_api_names(content: str, rich_ctx: "RichContext") -> List[Dict]:
    """Check for API names not in whitelist."""
    risks = []

    # Extract API-like names from content (CamelCase, snake_case with parens)
    api_pattern = r"\b([A-Z][a-zA-Z0-9_]*(?:\.[A-Z][a-zA-Z0-9_]*)*)\s*\("
    found_apis = set(re.findall(api_pattern, content))

    # Build whitelist from code understanding and snippets
    whitelist = set()

    # Add classes and functions from code understanding
    code_understanding = rich_ctx.code_understanding
    for cls in code_understanding.get("classes", []):
        whitelist.add(cls.get("name", ""))
    for func in code_understanding.get("functions", []):
        whitelist.add(func.get("name", ""))

    # Add APIs from snippets
    for snippet in rich_ctx.relevant_snippets:
        snippet_code = snippet.get("code", "")
        snippet_apis = re.findall(api_pattern, snippet_code)
        whitelist.update(snippet_apis)

    # Check for unknown APIs
    unknown_apis = found_apis - whitelist
    if unknown_apis:
        risks.append({
            "layer": 2,
            "level": "MEDIUM",
            "message": f"API names not in whitelist: {', '.join(sorted(unknown_apis)[:5])}",
            "location": "content"
        })

    return risks


def _check_code_blocks(content: str, rich_ctx: "RichContext") -> List[Dict]:
    """Check for code blocks not matching any snippet (basic Jaccard)."""
    risks = []

    # Extract code blocks
    code_blocks = re.findall(r"```(?:\w+)?\s*\n(.*?)\n```", content, re.DOTALL)
    if not code_blocks:
        return risks

    # Build snippet word sets
    snippet_word_sets = []
    for snippet in rich_ctx.relevant_snippets:
        snippet_code = snippet.get("code", "")
        words = set(re.findall(r"\w+", snippet_code.lower()))
        snippet_word_sets.append(words)

    # Check each code block
    for i, code_block in enumerate(code_blocks):
        code_words = set(re.findall(r"\w+", code_block.lower()))
        if not code_words:
            continue

        # Calculate max Jaccard similarity with any snippet
        max_similarity = 0.0
        for snippet_words in snippet_word_sets:
            intersection = len(code_words & snippet_words)
            union = len(code_words | snippet_words)
            similarity = intersection / union if union > 0 else 0.0
            max_similarity = max(max_similarity, similarity)

        # Flag if similarity too low
        if max_similarity < 0.3:
            risks.append({
                "layer": 3,
                "level": "HIGH",
                "message": f"Code block {i+1} has low similarity to snippets ({max_similarity:.2f})",
                "location": f"code_block_{i+1}"
            })

    return risks


def _check_claim_density(content: str) -> List[Dict]:
    """Check claim marker density (< 1 per 150 words)."""
    risks = []

    word_count = len(content.split())
    claim_markers = re.findall(
        r"<!--\s*claim:\s*[a-zA-Z0-9_\-]+\s*-->|\[claim:\s*[a-zA-Z0-9_\-]+\]",
        content,
    )

    if word_count == 0:
        return risks

    density = len(claim_markers) / (word_count / 150)

    if density < 1.0:
        risks.append({
            "layer": 4,
            "level": "MEDIUM",
            "message": f"Low claim marker density: {density:.2f} per 150 words (expected >= 1.0)",
            "location": "content"
        })

    return risks


def _check_performance_claims(content: str) -> List[Dict]:
    """Check for performance claims without claim markers."""
    risks = []

    # Performance keywords
    perf_keywords = [
        r"\bfast(?:er)?\b",
        r"\bslow(?:er)?\b",
        r"\bperformance\b",
        r"\boptimiz(?:e|ed|ation)\b",
        r"\befficient(?:cy)?\b",
        r"\bhigh(?:-|\s)?throughput\b",
        r"\blow(?:-|\s)?latency\b",
        r"\bscalable?\b",
        r"\bspeed(?:up)?\b",
    ]

    # Find sentences with performance claims
    sentences = re.split(r"[.!?]\s+", content)
    for i, sentence in enumerate(sentences):
        # Check if sentence contains performance keyword
        has_perf_keyword = any(re.search(pattern, sentence, re.IGNORECASE) for pattern in perf_keywords)

        if has_perf_keyword:
            # Check if sentence has claim marker
            has_claim_marker = re.search(
                r"<!--\s*claim:\s*[a-zA-Z0-9_\-]+\s*-->|\[claim:\s*[a-zA-Z0-9_\-]+\]",
                sentence,
            )

            if not has_claim_marker:
                risks.append({
                    "layer": 7,
                    "level": "MEDIUM",
                    "message": f"Performance claim without marker in sentence {i+1}",
                    "location": f"sentence_{i+1}"
                })

    return risks
