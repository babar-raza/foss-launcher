"""Tier-driven template resolution for page generation."""
from __future__ import annotations

from pathlib import Path

from launcher.content.template_loader import load_template, select_template
from launcher.models.product import RichnessTier


_TIER_LABEL_MAP: dict[RichnessTier, str] = {
    RichnessTier.A: "A",
    RichnessTier.B: "B",
    RichnessTier.C: "C",
}


def resolve_template(
    section: str,
    page_role: str,
    family: str,
    tier: RichnessTier,
) -> tuple[str, str]:
    """Resolve template path and variant for a page.

    Delegates to :func:`launcher.content.template_loader.select_template`
    with the tier mapped to its label string.

    Parameters
    ----------
    section:
        Logical site section (``products``, ``docs``, etc.).
    page_role:
        Page role slug (e.g. ``overview``, ``installation``).
    family:
        Product family slug (e.g. ``cells``, ``words``).
    tier:
        Richness tier enum value.

    Returns
    -------
    tuple[str, str]
        ``(template_path_str, variant)`` where *template_path_str* is the
        absolute path to the template file (empty string if not found) and
        *variant* is ``"minimal"`` for tier C, ``"standard"`` otherwise.
    """
    tier_label = _TIER_LABEL_MAP.get(tier, "B")
    variant = "minimal" if tier == RichnessTier.C else "standard"

    path = select_template(section, page_role, tier_label, family=family)

    if path is not None:
        return str(path), variant

    return "", variant


def get_template_content(
    section: str,
    page_role: str,
    family: str,
    tier: RichnessTier,
) -> str | None:
    """Load template content if available.

    Parameters
    ----------
    section:
        Logical site section.
    page_role:
        Page role slug.
    family:
        Product family slug.
    tier:
        Richness tier enum value.

    Returns
    -------
    str | None
        Template content, or ``None`` if no matching template exists.
    """
    tier_label = _TIER_LABEL_MAP.get(tier, "B")
    path = select_template(section, page_role, tier_label, family=family)

    if path is not None:
        return load_template(path)

    return None
