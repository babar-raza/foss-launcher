"""Check 8: SEO quality check."""
from __future__ import annotations

import re

import yaml

from launcher.models.evaluation import Finding

_MAX_TITLE_LENGTH = 70
_MAX_DESCRIPTION_LENGTH = 160
_HTML_ENTITY_RE = re.compile(r"&[a-zA-Z]+;|&#\d+;|&#x[0-9a-fA-F]+;")

# SEO-19: anchor text deny-list (generic, non-descriptive anchors)
_GENERIC_ANCHORS: frozenset[str] = frozenset({
    "click here", "here", "learn more", "read more",
    "this link", "more info", "more information", "link",
})


def _check_anchor_text(content: str) -> list[Finding]:
    """Flag generic anchor text in markdown links (SEO-19).

    Strips code blocks and inline code before scanning so anchors in
    code examples are not flagged.
    """
    findings: list[Finding] = []
    # Strip fenced and inline code to avoid false positives
    body = re.sub(r"```[^\n]*\n.*?```", "", content, flags=re.DOTALL)
    body = re.sub(r"`[^`]+`", "", body)
    for m in re.finditer(r"\[([^\]]+)\]\([^)]+\)", body):
        anchor = m.group(1).strip().lower()
        if anchor in _GENERIC_ANCHORS:
            findings.append(Finding(
                check="seo",
                message=(
                    f"Generic anchor text '{m.group(1).strip()}' is an SEO anti-pattern; "
                    "use descriptive link text instead."
                ),
                severity="medium",
                location="",
            ))
    return findings


def check_seo(
    content: str, slug: str, *, product_name: str = ""
) -> list[Finding]:
    """SEO checks: title length, meta description, slug format."""
    findings: list[Finding] = []

    # Extract frontmatter
    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return findings

    try:
        fm = yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        return findings

    if not isinstance(fm, dict):
        return findings

    # Title length
    title = fm.get("title", "")
    if not title:
        findings.append(
            Finding(
                check="seo",
                message="Missing title",
                severity="high",
                location=slug,
            )
        )
    elif len(title) > _MAX_TITLE_LENGTH:
        findings.append(
            Finding(
                check="seo",
                message=f"Title too long: {len(title)} chars (max {_MAX_TITLE_LENGTH})",
                severity="low",
                location=slug,
            )
        )

    # Meta description
    description = fm.get("description", "")
    if not description:
        findings.append(
            Finding(
                check="seo",
                message="Missing meta description",
                severity="low",
                location=slug,
            )
        )
    elif len(description) > _MAX_DESCRIPTION_LENGTH:
        findings.append(
            Finding(
                check="seo",
                message=f"Description too long: {len(description)} chars (max {_MAX_DESCRIPTION_LENGTH})",
                severity="low",
                location=slug,
            )
        )

    # Slug format (lowercase, hyphens only)
    fm_slug = fm.get("slug", slug)
    if fm_slug and not re.match(r"^[a-z0-9_-]+$", fm_slug):
        findings.append(
            Finding(
                check="seo",
                message=f"Non-standard slug format: '{fm_slug}'",
                severity="low",
                location=slug,
            )
        )

    # Doubled path segments in URL
    url = fm.get("url", "")
    if url:
        segments = [s for s in url.split("/") if s]
        for i in range(len(segments) - 1):
            if segments[i] == segments[i + 1]:
                findings.append(
                    Finding(
                        check="seo",
                        message=f"Doubled path segment: '/{segments[i]}/{segments[i]}/'",
                        severity="high",
                        location=slug,
                    )
                )
                break  # one finding per URL is sufficient

    # Product name in title
    if product_name and title and product_name.lower() not in title.lower() and not (slug == "_index" or slug.endswith("/_index")):
        findings.append(
            Finding(
                check="seo",
                message="Product name not in title",
                severity="low",
                location=slug,
            )
        )

    # --- Enhanced SEO checks (TC-3811) ---

    is_index = (
        slug == "_index"
        or slug.endswith("/_index")
        or fm.get("slug", "") == "_index"
    )

    # seoTitle checks (skip for index pages)
    # TC-3878 Wave 0 (E3): Downgraded from "medium" to "low" — missing seoTitle is a
    # planner/config failure, not a content quality failure. Stacking this MEDIUM with
    # the readability MEDIUM produced Grade C on otherwise clean pages.
    if not is_index:
        seo_title = fm.get("seoTitle", "")
        if not seo_title:
            findings.append(
                Finding(
                    check="seo",
                    message="Missing seoTitle",
                    severity="low",
                    location=slug,
                )
            )
        else:
            if len(seo_title) > 60:
                findings.append(
                    Finding(
                        check="seo",
                        message=f"seoTitle too long: {len(seo_title)} chars (max 60)",
                        severity="low",
                        location=slug,
                    )
                )
            if seo_title == title:
                findings.append(
                    Finding(
                        check="seo",
                        message="seoTitle identical to title",
                        severity="low",
                        location=slug,
                    )
                )

    # Canonical URL check (skip for index pages)
    # TC-3878 Wave 0 (E3): "Missing canonical URL" downgraded from "medium" to "low" —
    # this is a planner/metadata failure not a content failure. "Not HTTPS" stays HIGH
    # as it is a deployment blocker for production SEO.
    if not is_index:
        canonical = fm.get("canonical", "")
        if not canonical:
            findings.append(
                Finding(
                    check="seo",
                    message="Missing canonical URL",
                    severity="low",
                    location=slug,
                )
            )
        elif not canonical.startswith("https://"):
            findings.append(
                Finding(
                    check="seo",
                    message=f"Canonical URL not HTTPS: '{canonical[:60]}'",
                    severity="high",
                    location=slug,
                )
            )

    # Robots directive
    robots = fm.get("robots", "")
    if not robots:
        findings.append(
            Finding(
                check="seo",
                message="Missing robots directive",
                severity="low",
                location=slug,
            )
        )

    # Keyword count (non-index pages should have >=3)
    keywords = fm.get("keywords", [])
    if isinstance(keywords, str):
        keywords = [k.strip() for k in keywords.split(",") if k.strip()]
    if not is_index and len(keywords) < 3:
        findings.append(
            Finding(
                check="seo",
                message=f"Too few keywords: {len(keywords)} (min 3)",
                severity="low",
                location=slug,
            )
        )

    # Template description detection (rejects "{title} for {product}" pattern)
    if description and product_name:
        _desc_lower = description.lower().strip()
        _pattern = f"{title.lower()} for {product_name.lower()}"
        if _desc_lower == _pattern or _desc_lower == _pattern.rstrip("."):
            findings.append(
                Finding(
                    check="seo",
                    message="Description is template-generated (title + product name)",
                    severity="medium",
                    location=slug,
                )
            )

    # Keyword body presence (scan first 2000 chars after frontmatter)
    if not is_index and keywords:
        body_start_idx = content.find("---", 4)  # skip opening ---
        if body_start_idx > 0:
            body_text = content[body_start_idx + 3:body_start_idx + 2003].lower()
            kw_found = any(
                kw.lower() in body_text
                for kw in keywords
                if isinstance(kw, str) and kw.strip()
            )
            if not kw_found:
                findings.append(
                    Finding(
                        check="seo",
                        message="No keywords found in page body (first 2000 chars)",
                        severity="low",
                        location=slug,
                    )
                )

    # HTML entity detection in title/description
    for field_name, field_val in [("title", title), ("description", description)]:
        if field_val and _HTML_ENTITY_RE.search(field_val):
            findings.append(
                Finding(
                    check="seo",
                    message=f"HTML entity in {field_name}: '{field_val[:60]}'",
                    severity="high",
                    location=slug,
                )
            )

    # SEO-19: anchor text optimization (skip index pages)
    if not is_index:
        findings.extend(_check_anchor_text(content))

    return findings
