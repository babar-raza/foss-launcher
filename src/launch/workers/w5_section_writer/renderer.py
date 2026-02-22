"""JSON-to-markdown renderer for W5 structured output (D-1).

TC-2376: Converts structured JSON from draft LLM calls into valid markdown.
Eliminates need for ~35 sanitizer transforms by producing structured output
directly from the LLM that can be rendered deterministically.

Spec reference: specs/41_structured_output_envelope.md
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def json_to_markdown(json_output: Dict[str, Any], page: Dict[str, Any]) -> str:
    """Convert structured JSON draft to markdown.

    Args:
        json_output: Dict with a "sections" list, each section having:
            - heading: str
            - level: int (heading level, e.g. 2 for ##)
            - body: str (prose with <!-- claim: id --> markers)
            - code_blocks: list of {language, code, caption}
        page: Page specification dict (used for context, e.g. slug).

    Returns:
        Rendered markdown string, stripped of leading/trailing whitespace.
        Returns empty string if json_output is not a dict or has no sections.
    """
    if not isinstance(json_output, dict):
        return ""
    lines: List[str] = []
    for section in json_output.get("sections", []):
        heading = section.get("heading", "")
        level = section.get("level", 2)
        body = section.get("body", "")
        code_blocks = section.get("code_blocks", [])
        if heading:
            lines.append(f"{'#' * level} {heading}")
            lines.append("")
        if body:
            lines.append(body)
            # A+.5: Inject claim markers from JSON envelope for auditing
            claim_ids_used = section.get("claim_ids_used", [])
            if claim_ids_used:
                # Only inject markers not already present in body
                for cid in claim_ids_used:
                    marker = f"<!-- claim: {cid} -->"
                    if marker not in body:
                        lines.append(marker)
            lines.append("")
        for cb in code_blocks:
            lang = cb.get("language", "")
            code = cb.get("code", "")
            caption = cb.get("caption", "")
            if code:
                lines.append(f"```{lang}")
                lines.append(code)
                lines.append("```")
                if caption:
                    lines.append(f"*{caption}*")
                lines.append("")
    return "\n".join(lines).strip()


def parse_json_draft(raw_content: str) -> Optional[Dict[str, Any]]:
    """Parse JSON from LLM response, handling common fence wrapping.

    Strips ```json or bare ``` fences if present, then attempts json.loads().
    Returns None on any parse failure (does NOT raise).

    Args:
        raw_content: Raw string from LLM response.

    Returns:
        Parsed dict on success, None on failure.
    """
    if not raw_content:
        return None
    content = raw_content.strip()
    # Strip JSON code fence if present
    if "```json" in content:
        m = re.search(r"```json\s*\n(.*?)\n```", content, re.DOTALL)
        if m:
            content = m.group(1)
    elif content.startswith("```"):
        m = re.search(r"```\s*\n(.*?)\n```", content, re.DOTALL)
        if m:
            content = m.group(1)
    try:
        result = json.loads(content)
        return result if isinstance(result, dict) else None
    except (json.JSONDecodeError, ValueError):
        logger.warning("W5_ENVELOPE_PARSE_FAILURE: could not parse JSON from LLM response")
        return None
