"""Check 10: Product name misspelling detection."""
from __future__ import annotations

import logging
import re

from launcher.models.evaluation import Finding
from launcher.shared.jaccard import strip_code_blocks

logger = logging.getLogger(__name__)


def _extract_frontmatter_title(content: str) -> str:
    """Extract the title field from YAML frontmatter."""
    m = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not m:
        return ""
    fm = m.group(1)
    tm = re.search(r"^title:\s*[\"']?(.+?)[\"']?\s*$", fm, re.MULTILINE)
    return tm.group(1) if tm else ""


def _build_patterns(product_name: str) -> list[tuple[re.Pattern[str], str]]:
    """Build misspelling detection patterns for the given product name."""
    patterns: list[tuple[re.Pattern[str], str]] = []

    # Parse product: e.g. "Aspose.Cells" -> prefix="Aspose", suffix="Cells"
    parts = product_name.split(".", 1)
    prefix = parts[0]
    suffix = parts[1] if len(parts) > 1 else ""

    # Common prefix typos (case-insensitive in prose)
    if prefix.lower() == "aspose":
        typos = ["Aspire", "Aspuse", "Apose", "Aspsoe", "Asopse"]
        for typo in typos:
            if suffix:
                patterns.append((
                    re.compile(rf"\b{typo}[.\s]{suffix}\b", re.IGNORECASE),
                    f"Misspelled product prefix: '{typo}' (should be '{prefix}')",
                ))
            else:
                patterns.append((
                    re.compile(rf"\b{typo}\b", re.IGNORECASE),
                    f"Misspelled product prefix: '{typo}' (should be '{prefix}')",
                ))

    # Missing dot: "Aspose Cells" instead of "Aspose.Cells"
    if suffix:
        patterns.append((
            re.compile(rf"\b{re.escape(prefix)}\s+{re.escape(suffix)}\b"),
            f"Missing dot in product name: '{prefix} {suffix}' (should be '{product_name}')",
        ))

    # Doubled qualifier: "for Python for Python"
    patterns.append((
        re.compile(r"\bfor\s+(\w+)\s+for\s+\1\b", re.IGNORECASE),
        "Doubled qualifier (e.g. 'for Python for Python')",
    ))

    # Space after dot: "Aspose. Cells" instead of "Aspose.Cells" (TC-QG-01)
    if suffix:
        patterns.append((
            re.compile(rf"\b{re.escape(prefix)}\.\s+{re.escape(suffix)}\b"),
            f"Space after dot in product name: '{prefix}. {suffix}' (should be '{product_name}')",
        ))

    # Wrong case in prose: all-lowercase like "aspose.cells"
    if suffix and (prefix[0].isupper() or suffix[0].isupper()):
        patterns.append((
            re.compile(rf"\b{re.escape(prefix.lower())}\.{re.escape(suffix.lower())}\b"),
            f"Wrong case in product name: should be '{product_name}'",
        ))

    return patterns


def check_product_names(
    content: str, slug: str, *, product_name: str = ""
) -> list[Finding]:
    """Detect product name misspellings in content."""
    logger.debug("[product_names] Evaluating %s", slug)
    findings: list[Finding] = []

    if not product_name:
        logger.warning("[product_names] No product_name provided, skipping for %s", slug)
        return findings

    patterns = _build_patterns(product_name)
    title = _extract_frontmatter_title(content)

    # Strip code blocks from body before scanning prose
    body = re.sub(r"^---\n.*?\n---\n?", "", content, flags=re.DOTALL)
    body_no_code = strip_code_blocks(body)

    for pat, message in patterns:
        # Check frontmatter title
        if title and pat.search(title):
            findings.append(
                Finding(
                    check="product_names",
                    message=f"Title: {message}",
                    severity="high",
                    location=slug,
                )
            )

        # Check body prose (code blocks already stripped)
        # TC-QG-01: body misspellings escalated to HIGH severity
        matches = pat.findall(body_no_code)
        if matches:
            findings.append(
                Finding(
                    check="product_names",
                    message=f"Body: {message}",
                    severity="high",
                    location=slug,
                )
            )

    logger.debug("[product_names] Found %d findings for %s", len(findings), slug)
    return findings
