"""Check 7: Safety checks."""
from __future__ import annotations

import re

from launcher.models.evaluation import Finding

_MAX_PAGE_SIZE_BYTES = 500_000  # 500KB

_SENSITIVE_PATTERNS = [
    r"(?:password|passwd|secret|api[_-]?key|token)\s*[:=]\s*['\"][^'\"]+['\"]",
    r"[a-zA-Z0-9+/]{40,}={1,2}",  # base64-like strings with padding (potential keys)
    r"(?:sk|pk|rk|ak)-[a-zA-Z0-9_-]{20,}",  # prefixed API keys (sk-..., pk-...)
]

_COMMERCIAL_DOMAIN_RE = re.compile(
    # TC-3894: "forum." removed — Aspose forum is a legitimate community resource.
    # "docs." and "reference." blocked because FOSS docs use *.aspose.org, not .com.
    r"https?://(?:www\.|docs\.|reference\.|purchase\.|releases\.)?aspose\.com\b",
    re.IGNORECASE,
)

# TC-4038: competitor library domains — external library links are a brand risk.
_COMPETITOR_LINK_RE = re.compile(
    r"https?://(?:www\.)?(?:"
    r"openpyxl\.readthedocs\.io"
    r"|xlsxwriter\.readthedocs\.io"
    r"|pandas\.pydata\.org"
    r"|python-excel\.org"
    r"|xlrd\.readthedocs\.io"
    r"|xlwt\.readthedocs\.io"
    r")\b",
    re.IGNORECASE,
)

_XSS_PATTERNS = [
    r"<script",
    r"javascript:",
    r"on\w+\s*=",
    r"<iframe",
]


def check_safety(content: str, slug: str, *, page_role: str = "") -> list[Finding]:
    """Safety checks: XSS, sensitive data, page size, commercial links.

    All pattern scans operate on prose only — code blocks and inline code are stripped
    before scanning to avoid false positives from code examples and doc comments.
    Page size is measured on the raw content before any stripping.

    Args:
        content: Raw markdown content including frontmatter.
        slug: Page slug for finding location attribution.
        page_role: Hugo page role (reserved for future role-specific branching).
    """
    findings: list[Finding] = []

    # Page size (raw content — no stripping)
    size = len(content.encode("utf-8"))
    if size > _MAX_PAGE_SIZE_BYTES:
        findings.append(
            Finding(
                check="safety",
                message=f"Page size {size} bytes exceeds {_MAX_PAGE_SIZE_BYTES}",
                severity="high",
                location=slug,
            )
        )

    # XSS patterns (check prose only, not code blocks or inline code).
    # Strip fenced code blocks then inline backtick spans so patterns like on\w+\s*=
    # do not fire on legitimate code such as `flag.font = True` or `on_error = True`.
    prose = re.sub(r"```.*?```", "", content, flags=re.DOTALL)
    prose = re.sub(r"`[^`\n]+`", "", prose)
    for pattern in _XSS_PATTERNS:
        if re.search(pattern, prose, re.IGNORECASE):
            findings.append(
                Finding(
                    check="safety",
                    message=f"Potential XSS pattern: {pattern}",
                    severity="critical",
                    location=slug,
                )
            )

    # Sensitive data — strip code blocks AND inline code before scanning.
    # Long inline identifiers (e.g. `Aspose_BarCode_..._ctor_System_String_`) can
    # match the base64-like pattern; they are not sensitive data.
    body_no_code = re.sub(r"```.*?```", "", content, flags=re.DOTALL)[:50_000]
    body_no_code = re.sub(r"`[^`\n]+`", "", body_no_code)
    for pattern in _SENSITIVE_PATTERNS:
        matches = re.findall(pattern, body_no_code, re.IGNORECASE)
        if matches:
            findings.append(
                Finding(
                    check="safety",
                    message=f"Potential sensitive data leak ({len(matches)} matches)",
                    severity="critical",
                    location=slug,
                )
            )

    # -- Commercial domain links (FOSS content must not link to commercial sites) --
    # Strip code blocks: release URLs in code examples (e.g. pip install download
    # comments) are not prose violations. Only prose links are checked.
    content_no_code = re.sub(r"```.*?```", "", content, flags=re.DOTALL)
    commercial_links = _COMMERCIAL_DOMAIN_RE.findall(content_no_code)
    if commercial_links:
        unique = sorted(set(commercial_links))
        findings.append(
            Finding(
                check="safety",
                message=f"Commercial domain link(s) found ({len(commercial_links)} total): {', '.join(unique[:3])}",
                severity="high",
                location=slug,
            )
        )

    # TC-4038: competitor library links — brand risk regardless of FOSS/commercial.
    competitor_links = _COMPETITOR_LINK_RE.findall(content_no_code)
    if competitor_links:
        unique_comp = sorted(set(competitor_links))
        findings.append(
            Finding(
                check="safety",
                message=f"Competitor library link(s) found ({len(competitor_links)} total): {', '.join(unique_comp[:3])}",
                severity="high",
                location=slug,
            )
        )

    return findings
