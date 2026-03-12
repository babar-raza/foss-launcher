"""Snippet-to-claim linking and tier relevance assignment."""
from __future__ import annotations

import re

from launcher.models.claims import Claim
from launcher.models.product import ApiSurface


def _assign_tier_relevance(text: str, kind: str, api_surface: ApiSurface) -> str:
    """Determine tier relevance based on claim content.

    - API claims mentioning public classes -> "full"
    - Install/config claims -> "all" (relevant at every tier)
    - Feature claims -> "all"
    """
    if kind == "api":
        # Check if the claim mentions any known public class
        for cls_name in api_surface.public_classes:
            if cls_name.lower() in text.lower():
                return "full"
        return "core"

    if kind in ("install", "config", "license"):
        return "all"

    return "all"


def _link_snippet_to_claims(code: str, claims: list[Claim]) -> list[str]:
    """Link a code snippet to claims via keyword overlap.

    A snippet is linked to a claim if they share meaningful words
    (class names, method names, etc.).
    """
    linked: list[str] = []
    code_words = set(re.findall(r"\b[A-Za-z_]\w{2,}\b", code.lower()))

    for claim in claims:
        claim_words = set(re.findall(r"\b[A-Za-z_]\w{2,}\b", claim.text.lower()))
        # Require at least 2 shared meaningful words
        shared = code_words & claim_words
        # Filter out very common words
        shared -= {"the", "and", "for", "from", "with", "this", "that", "import",
                    "class", "def", "self", "none", "true", "false", "return"}
        if len(shared) >= 2:
            linked.append(claim.claim_id)

    return linked
