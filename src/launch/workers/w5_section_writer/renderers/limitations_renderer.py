"""Structured Limitations section renderer.

Feature flag: LAUNCH_STRUCTURED_LIMITATIONS=json|freeform (default: freeform)
In freeform mode (default): this module functions are available but NOT called by W5.
In json mode: LLM generates JSON, this module parses + renders deterministic markdown.
Falls back to freeform on any parse/validation failure.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional

_STRUCTURED_MODE = os.environ.get("LAUNCH_STRUCTURED_LIMITATIONS", "freeform")

LLM_JSON_PROMPT_ADDENDUM = (
    "\n\nCRITICAL: Output ONLY a JSON array using this EXACT schema:\n"
    '[{"title": "Short title (max 10 words)", "description": "One to two sentences.", "workaround": "Workaround or null"}]\n'
    "No prose, no explanation, no code fences. Start with [ and end with ]."
)


def is_structured_mode() -> bool:
    """True when LAUNCH_STRUCTURED_LIMITATIONS=json."""
    return _STRUCTURED_MODE == "json"


def parse_limitations_json(raw: str) -> Optional[List[Dict[str, Any]]]:
    """Extract and validate JSON limitations array from LLM output.

    Handles:
      - Bare JSON array: [{"title": ...}]
      - JSON inside ```json ... ``` or ``` ... ``` fences
      - Leading/trailing prose (finds first [ ... ] pair)
      - Null workaround values

    Returns None on any parse or validation failure (caller should fall back to freeform).
    """
    if not raw or not raw.strip():
        return None

    text = raw.strip()

    # Strip code fence if present
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if fence_match:
        text = fence_match.group(1).strip()

    # Find outermost JSON array bounds
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1 or end <= start:
        return None

    try:
        data = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None

    if not isinstance(data, list):
        return None

    validated = []
    for item in data:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title", "")).strip()
        description = str(item.get("description", "")).strip()
        # Minimum length validation
        if len(title) < 3 or len(description) < 10:
            continue
        workaround = item.get("workaround")
        if workaround is not None:
            workaround = str(workaround).strip() or None
        validated.append({
            "title": title,
            "description": description,
            "workaround": workaround,
        })

    return validated if validated else None


def render_limitations_to_markdown(
    items: List[Dict[str, Any]],
    product_name: str,
    claim_ids: Optional[List[str]] = None,
) -> str:
    """Render validated limitations list to deterministic markdown.

    Args:
        items: Validated list from parse_limitations_json()
        product_name: Used in introductory sentence
        claim_ids: Optional claim IDs to embed as HTML comment markers

    Returns:
        Deterministic markdown string (same input -> same output, always)
    """
    if not items:
        return f"No verified limitations documented in sources for {product_name}."

    lines = [f"Known limitations and constraints for {product_name}:\n"]

    for i, item in enumerate(items):
        lines.append(f"**{item['title']}**")
        lines.append(f"{item['description']}")
        if item.get("workaround"):
            lines.append(f"*Workaround*: {item['workaround']}")
        if claim_ids and i < len(claim_ids) and claim_ids[i]:
            lines.append(f"<!-- claim: {claim_ids[i]} -->")
        lines.append("")

    return "\n".join(lines).rstrip()
