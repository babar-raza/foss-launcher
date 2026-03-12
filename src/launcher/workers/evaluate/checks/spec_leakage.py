"""Check 5: Spec leakage detection."""
from __future__ import annotations

import re

from launcher.models.evaluation import Finding
from launcher.shared.jaccard import strip_code_blocks

# NOTE: These terms are also checked upstream in:
#   - extract_claims.py: _INTERNAL_CONTENT_TERMS (L1 classifier)
#   - classify_claims.py: _INTERNAL_PATTERNS (L1 filter)
# Keep all three lists in sync when adding/removing terms.
_INTERNAL_TERMS = [
    # NOTE: "file format specification" removed (TC-3893) — false positive for Aspose
    # libraries that legitimately reference public format specs (OneNote, Excel, etc.).
    # The _SPEC_PATTERNS list catches actual internal spec document references.
    "internal api",
    "internal method",
    "private field",
    "wire protocol",
    "serialization format",
    "byte offset",
    "memory layout",
    "vtable",
    "opcode",
]

_SPEC_PATTERNS = [
    r"specs?/\d+",  # spec file references
    r"TC-\d{3,4}",  # taskcard references
    r"AG-\d{3}",  # governance rule references in content
]


def check_spec_leakage(content: str, slug: str, *, page_role: str = "") -> list[Finding]:
    """Detect internal terms and spec references in user-facing content.

    Code blocks are stripped before term matching to avoid false positives from XML doc
    comments or third-party code examples that mention implementation-oriented vocabulary.

    Args:
        content: Raw markdown content including frontmatter.
        slug: Page slug for finding location attribution.
        page_role: Hugo page role (reserved for future role-specific branching).
    """
    findings: list[Finding] = []
    body = re.sub(r"^---\n.*?\n---\n?", "", content, flags=re.DOTALL)
    body = strip_code_blocks(body)
    lower_body = body.lower()

    for term in _INTERNAL_TERMS:
        if re.search(r'\b' + re.escape(term) + r's?\b', lower_body):
            findings.append(
                Finding(
                    check="spec_leakage",
                    message=f"Internal term found: '{term}'",
                    severity="high",
                    location=slug,
                )
            )

    for pattern in _SPEC_PATTERNS:
        matches = re.findall(pattern, body)
        for match in matches:
            findings.append(
                Finding(
                    check="spec_leakage",
                    message=f"Spec reference found: '{match}'",
                    severity="high",
                    location=slug,
                )
            )

    return findings
