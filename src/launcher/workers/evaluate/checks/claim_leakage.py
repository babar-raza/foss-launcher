"""Check: Claim ID leakage detection.

Detects internal claim metadata (bracket citations and comment-format claim
IDs) that should never appear in publication-facing content.
"""
from __future__ import annotations

import re

from launcher.models.evaluation import Finding

_BRACKET_CITATION_RE = re.compile(r"\[CLM-[^\]]*\]")
_COMMENT_CLAIM_RE = re.compile(r"^\s*#\s*Claims:\s*CLM-", re.MULTILINE)


def check_claim_leakage(content: str, slug: str) -> list[Finding]:
    """Detect leaked claim IDs in user-facing markdown content.

    Code blocks are intentionally NOT stripped: pipeline metadata annotations
    like ``# Claims: CLM-xxx`` must never appear in output, even inside code
    blocks — their presence indicates internal metadata leaked into generated code.
    """
    findings: list[Finding] = []
    body = re.sub(r"^---\n.*?\n---\n?", "", content, flags=re.DOTALL)

    for match in _BRACKET_CITATION_RE.finditer(body):
        findings.append(
            Finding(
                check="claim_leakage",
                message=f"Claim citation leaked into content: '{match.group()}'",
                severity="critical",
                location=slug,
            )
        )

    for match in _COMMENT_CLAIM_RE.finditer(body):
        findings.append(
            Finding(
                check="claim_leakage",
                message=f"Claim comment leaked into content: '{match.group().strip()}'",
                severity="critical",
                location=slug,
            )
        )

    return findings
