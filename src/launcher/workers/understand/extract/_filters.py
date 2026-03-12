"""Claim filtering helpers: junk detection and off-topic classification."""
from __future__ import annotations

import re
import unicodedata

from launcher.models.product import ProductIdentity
from launcher.shared.jaccard import STOPWORDS

# Third-party library indicators for off-topic detection
_THIRD_PARTY_INDICATORS: frozenset[str] = frozenset({
    "scikit-learn", "sklearn", "django", "flask", "tensorflow", "numpy",
    "scipy", "matplotlib", "pandas", "pytorch", "keras", "fastapi",
    "requests", "beautifulsoup", "scrapy", "celery", "sqlalchemy",
})


def _is_junk_claim(text: str) -> bool:
    """Return True if *text* is not a meaningful product claim.

    Filters: too short, code-like, changelog noise, bold-only labels,
    emoji-leading, horizontal rules, badge lines, install commands,
    high stop-word ratio.
    """
    if len(text) < 20:
        return True

    # Code-like lines (must start with the keyword to avoid false positives)
    if re.match(r"^(?:import |from \S+ import |def |class |return |>>> )", text):
        return True

    # Changelog noise
    if re.search(r"\(#\d+\)", text):
        return True
    if re.search(r"PR\s*#?\d+", text):
        return True
    if re.match(r"^v?\d+\.\d+\.\d+", text):
        return True
    if re.match(r"^Merge\s", text):
        return True

    # Bold-only label
    if re.match(r"^\*\*[^*]{1,30}\*\*$", text):
        return True

    # Emoji-leading lines (Symbol, Other category covers emoji without CJK/accented)
    if text and unicodedata.category(text[0]) == "So":
        return True

    # Horizontal rules / badge lines
    if re.match(r"^[-*]{3,}$", text):
        return True
    if re.match(r"^!\[", text):
        return True

    # Install commands (with or without backtick wrapping)
    if re.match(r"^`?(?:pip|npm|yarn|cargo|go)\s+(?:install|add|get)\b", text):
        return True

    # High stop-word ratio (>65%)
    words = re.findall(r"\b[a-z]+\b", text.lower())
    if words:
        stop_count = sum(1 for w in words if w in STOPWORDS)
        if stop_count / len(words) > 0.65:
            return True

    return False


def _is_off_topic(text: str, product: ProductIdentity) -> bool:
    """Return True if *text* describes a third-party product, not the target.

    A claim is off-topic when it mentions a known third-party library
    AND does not mention any product keyword derived from ProductIdentity.
    """
    lower = text.lower()

    # Build product keywords from identity fields (exclude generic platform names)
    _GENERIC_TOKENS = {"python", "java", "net", "foss", "for", "via", "the"}
    product_keywords: set[str] = set()
    for field in (product.family, product.display_name, getattr(product, "canonical_import", "")):
        if field:
            for token in re.split(r"[\s._-]+", field.lower()):
                if len(token) >= 3 and token not in _GENERIC_TOKENS:
                    product_keywords.add(token)

    # Check for third-party indicators
    has_third_party = any(tp in lower for tp in _THIRD_PARTY_INDICATORS)
    if not has_third_party:
        return False

    # If the claim also mentions product keywords, keep it (mixed mention)
    has_product = any(kw in lower for kw in product_keywords)
    return not has_product
