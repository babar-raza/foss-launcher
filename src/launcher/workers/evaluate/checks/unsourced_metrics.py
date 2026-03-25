"""Check: unsourced_metrics — flag performance claims without evidence (TC-EVAL-502).

Catches fabricated benchmarks like "40% faster" or "reduces memory by 38%"
that appear in generated content without any evidence citation.  Severity: HIGH.
"""
from __future__ import annotations

import re

from launcher.models.evaluation import Finding

# Percentage claims: "40% faster", "reduces by 38%", "15% memory reduction"
_PCT_CLAIM_RE = re.compile(
    r"\b\d{1,3}%\s*(?:faster|slower|reduction|improvement|memory|speedup|"
    r"smaller|larger|quicker|increase|decrease|gain|savings?|less|more|"
    r"better|worse|efficient|overhead)\b",
    re.IGNORECASE,
)

# Time claims: "10ms faster", "2 seconds reduction"
_TIME_CLAIM_RE = re.compile(
    r"\b\d+(?:\.\d+)?\s*(?:ms|seconds?|milliseconds?|microseconds?|nanoseconds?|minutes?)"
    r"\s*(?:faster|slower|reduction|improvement|latency|overhead)\b",
    re.IGNORECASE,
)

# Evidence markers that indicate the claim is sourced
_EVIDENCE_MARKERS = re.compile(
    r"(?:benchmark|measured|tested|profiled|according to|source:|"
    r"in our tests|test results|based on|documentation states)",
    re.IGNORECASE,
)


def check_unsourced_metrics(content: str, slug: str) -> list[Finding]:
    """Flag percentage and time-based performance claims without evidence."""
    findings: list[Finding] = []
    claims: list[str] = []

    for m in _PCT_CLAIM_RE.finditer(content):
        claims.append(m.group(0))
    for m in _TIME_CLAIM_RE.finditer(content):
        claims.append(m.group(0))

    if not claims:
        return findings

    # Check if ANY evidence marker exists in the content
    has_evidence = bool(_EVIDENCE_MARKERS.search(content))

    if not has_evidence:
        findings.append(Finding(
            check="unsourced_metrics",
            message=f"Unsourced performance claim(s): {', '.join(claims[:5])} — no evidence citation found",
            severity="high",
            location=slug,
        ))

    return findings
