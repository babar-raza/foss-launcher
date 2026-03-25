"""Assign A-F grades to pages based on findings."""
from __future__ import annotations

from launcher.models.evaluation import Finding, Grade

# TC-3879 Wave 1 (E1): Safety-critical checks whose HIGH findings are deployment blockers.
# A single HIGH from these checks is a Grade D (same as before — these are correctness-critical).
# HIGHs from other checks are non-safety-critical and apply the new softer grading table.
SAFETY_CRITICAL_CHECKS: frozenset[str] = frozenset({
    "safety",           # XSS, malicious links, commercial domains
    "slug_safety",      # Unsafe slug format — breaks URL routing
    "claim_leakage",    # [CLM-xxx] in published content
    "spec_leakage",     # Internal spec identifiers in published content
    "seo",              # Canonical URL not HTTPS — deployment SEO blocker
    "frontmatter",      # Missing required frontmatter fields (title, page_role)
    "structure",        # H1 in body, template-label headings — structural corruption
})

# TC-4031 Wave 4F: Editorial-critical checks — HIGH from these means the page
# is substantively wrong (off-topic, missing claims, fabricated APIs) and earns
# Grade D regardless of other findings. Distinct from safety-critical (which blocks
# deployment for policy reasons); editorial-critical blocks for quality reasons.
EDITORIAL_CRITICAL_CHECKS: frozenset[str] = frozenset({
    "route_consistency",              # Slug topic words absent from prose — off-topic content
    "claim_coverage",                 # Assigned claims not addressed in page — hollow content
    "code",                           # TC-REG-302: Python syntax errors (HIGH) — unparseable code
    "api_identifier_unknown_class",   # TC-REG-301: hallucinated class names in code blocks (HIGH)
    "api_property_called_as_method",  # TC-REG-301: property called as method in code blocks (HIGH)
    "api_identifier_unknown_method",  # TC-EVAL-301: hallucinated methods on tracked receivers (HIGH)
})


# TC-5189: LLM-generated check names (prose review checks). These findings count toward
# the LLM-specific grading thresholds, not the deterministic grading table.
# Deterministic checks (not in this set) use the standard MEDIUM/HIGH severity escalation.
_LLM_CHECK_NAMES: frozenset[str] = frozenset({
    "prose_quality",
    "prose_review",
    "llm_prose",
    "opener_boilerplate",
    "content_tone",
    "explanation_depth",
    "api_consistency",   # TC-5199: LLM-subjective API consistency check
    "content_density",   # TC-5199: LLM-subjective content density check
})

# TC-5199: Checks eligible for HIGH severity promotion when message contains
# high-signal patterns (e.g., "no such method", "does not exist").
_PROMOTED_LLM_CHECKS: frozenset[str] = frozenset({
    "api_consistency",
})

# TC-5199: Message patterns that indicate a high-confidence LLM finding
# worthy of retaining HIGH severity despite being from an LLM check.
_PROMOTION_PATTERNS: tuple[str, ...] = (
    "no such method",
    "does not exist",
    "not in api",
    "property does not exist",
)


def _is_promoted_llm_finding(finding: Finding) -> bool:
    """TC-5199: Return True if this LLM finding has a high-signal message.

    A promoted LLM finding retains its HIGH severity instead of being capped
    to MEDIUM. Only checks in _PROMOTED_LLM_CHECKS are eligible, and only
    when the message contains specific patterns indicating a concrete API
    discrepancy (not a vague style complaint).
    """
    if finding.check not in _PROMOTED_LLM_CHECKS:
        return False
    msg = (finding.message or "").lower()
    if not msg:
        return False
    return any(p in msg for p in _PROMOTION_PATTERNS)


def _effective_severity(finding: Finding) -> str:
    """TC-5199: Return the effective severity after LLM check capping.

    LLM-generated checks (_LLM_CHECK_NAMES) have their HIGH findings capped
    to MEDIUM by default, unless _is_promoted_llm_finding returns True.
    All other checks pass through unchanged.
    """
    if finding.check not in _LLM_CHECK_NAMES:
        return finding.severity
    if finding.severity != "high":
        return finding.severity
    # HIGH from an LLM check — cap to MEDIUM unless promoted
    if _is_promoted_llm_finding(finding):
        return "high"
    return "medium"


def _is_editorial_critical(finding: Finding) -> bool:
    """Return True if this finding's check is editorial-critical (Grade D on any HIGH).

    TC-4031 Wave 4F: editorial-critical checks fire for substantive content quality
    failures — off-topic pages, hollow content. These are distinct from safety
    violations and warrant Grade D to prevent automated GO on bad content.
    """
    return finding.check in EDITORIAL_CRITICAL_CHECKS


def _is_safety_critical(finding: Finding) -> bool:
    """Return True if this finding's check is safety-critical (Grade D on any HIGH).

    TC-3881 Wave 3: For 'structure' check, only H1-in-body and template-label headings
    are safety-critical. Golden spec findings (missing code block per golden spec) are
    content quality issues and should be non-safety-critical.
    """
    if finding.check not in SAFETY_CRITICAL_CHECKS:
        return False
    if finding.check == "structure":
        # Only structural corruption findings are safety-critical for 'structure'
        msg = finding.message or ""
        return "H1 heading" in msg or "Template-label heading" in msg
    return True


def grade_page(findings: list[Finding]) -> Grade:
    """Assign a grade based on severity of findings.

    TC-3879 Wave 1 (E1) grading table — safety-critical/non-safety-critical split:
      F = any CRITICAL finding
      D = any safety-critical HIGH (safety, slug_safety, claim_leakage, spec_leakage,
                                    seo/https, frontmatter, structure)
      C = 2+ non-safety-critical HIGH, OR 3+ MEDIUM
      B = 1 non-safety-critical HIGH, OR 1-2 MEDIUM
      A = 0 HIGH, 0 MEDIUM (LOW-only or clean)

    Rationale: The previous "any HIGH = D" binary cliff meant 16 checks × multiple
    sub-rules created ~48 failure opportunities to drop from A to D in one shot.
    content_density HIGH (thin section) was grading the same as a safety violation.
    The split allows pages with minor density/completeness HIGHs to reach Grade B/C.
    """
    # TC-5199: Use _effective_severity to cap LLM check HIGHs to MEDIUM
    # unless the finding is promoted (high-signal pattern).
    effective = [(f, _effective_severity(f)) for f in findings]
    critical = sum(1 for _, sev in effective if sev == "critical")
    safety_high = sum(1 for f, sev in effective if sev == "high" and _is_safety_critical(f))
    editorial_high = sum(1 for f, sev in effective if sev == "high" and _is_editorial_critical(f))
    non_safety_high = sum(
        1 for f, sev in effective
        if sev == "high" and not _is_safety_critical(f) and not _is_editorial_critical(f)
    )
    medium = sum(1 for _, sev in effective if sev == "medium")

    if critical > 0:
        return Grade.F
    if safety_high > 0 or editorial_high > 0:  # TC-4031 Wave 4F: editorial-critical → D
        return Grade.D
    if non_safety_high >= 2 or medium >= 3:
        return Grade.C
    if non_safety_high >= 1 or medium >= 1:
        return Grade.B
    return Grade.A
