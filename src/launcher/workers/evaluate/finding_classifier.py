"""
Finding classifier for the Heal system — TC-3838.

Classifies evaluation check names into four buckets:
  ENGINEERING_ONLY  — deterministic fixes only (never send to LLM)
  MIXED             — may need LLM or data fix depending on sub-type
  LLM_FIXABLE       — LLM re-generation can fix these
  DATA_FIXABLE      — fixing source data (claims, snippets) fixes these

Used by heal.py to decide which findings to pass to the LLM diagnostician.

TC-3882 Wave 4 (E10): Tag-based routing constants. Checks may prepend these
tags to MIXED finding messages for unambiguous classification:
  [ENG] — engineering-only, regardless of keywords
  [LLM] — LLM-fixable, regardless of keywords
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from launcher.models.evaluation import Finding

# TC-3882 Wave 4 (E10): Tag prefixes for unambiguous mixed-check routing.
_ENG_TAG: str = "[ENG]"
_LLM_TAG: str = "[LLM]"

# Typed alias for the three actionable fix classes returned by classify_finding().
# "mixed" and "unknown" are resolved internally — callers always receive one of these.
FixClass = Literal["engineering_only", "llm_fixable", "data_fixable"]


# Checks that can ONLY be fixed by engineering (config, schema, code changes)
# Never passed to the LLM for healing
ENGINEERING_ONLY_CHECKS: frozenset[str] = frozenset({
    "safety",
    "slug_safety",
})

# Checks that may be fixable by LLM OR by engineering depending on the specific finding
MIXED_CHECKS: frozenset[str] = frozenset({
    "frontmatter",    # missing entirely = engineering; wrong value = LLM
    "seo",            # missing FM fields = engineering; title too long = LLM
    "spec_leakage",   # internal terms in code = engineering; in prose = LLM
})

# Checks that LLM re-generation can fix
LLM_FIXABLE_CHECKS: frozenset[str] = frozenset({
    "density",
    "repetition",
    "product_names",
    "artifacts",
    "structure",
    "semantic_structure",
    "code",        # code syntax / missing example — LLM can regenerate
    "readability", # LLM can rewrite prose for complexity or simplicity (SEO-20)
})

# Checks that require fixing source data (claims or snippets) rather than regenerating prose
DATA_FIXABLE_CHECKS: frozenset[str] = frozenset({
    "reference_completeness",
    "claim_leakage",  # claim content is the problem
})


def classify_check(check_name: str) -> str:
    """Return the classification bucket for a given check name.

    Returns one of: "engineering_only", "mixed", "llm_fixable", "data_fixable", "unknown"
    """
    if check_name in ENGINEERING_ONLY_CHECKS:
        return "engineering_only"
    if check_name in MIXED_CHECKS:
        return "mixed"
    if check_name in LLM_FIXABLE_CHECKS:
        return "llm_fixable"
    if check_name in DATA_FIXABLE_CHECKS:
        return "data_fixable"
    return "unknown"


def classify_mixed_check(check_name: str, finding_message: str) -> str:
    """Sub-classify a MIXED check based on the finding message.

    TC-3882 Wave 4 (E10): Checks tag prefix first ([ENG]/[LLM]) for unambiguous
    routing, then falls back to keyword matching for backward compatibility.

    Returns: "engineering_only" or "llm_fixable"
    """
    if check_name not in MIXED_CHECKS:
        return classify_check(check_name)

    # Tag-based routing: unambiguous prefix overrides keyword heuristics.
    if finding_message.startswith(_ENG_TAG):
        return "engineering_only"
    if finding_message.startswith(_LLM_TAG):
        return "llm_fixable"

    msg_lower = finding_message.lower()
    if check_name == "frontmatter":
        if "missing" in msg_lower or "absent" in msg_lower or "required" in msg_lower:
            return "engineering_only"
        return "llm_fixable"
    if check_name == "seo":
        if "missing" in msg_lower or "absent" in msg_lower:
            return "engineering_only"
        return "llm_fixable"
    if check_name == "spec_leakage":
        if "code" in msg_lower or "import" in msg_lower:
            return "engineering_only"
        return "llm_fixable"
    return "llm_fixable"


def is_healable(check_name: str, finding_message: str = "") -> bool:
    """Return True if this finding can potentially be healed by the LLM loop."""
    bucket = classify_check(check_name)
    if bucket == "engineering_only":
        return False
    if bucket == "mixed":
        sub = classify_mixed_check(check_name, finding_message)
        return sub == "llm_fixable"
    return bucket in ("llm_fixable", "data_fixable", "unknown")


def classify_finding(finding: "Finding") -> FixClass:
    """Return the FixClass for a Finding object.

    Resolves "mixed" via sub-classifier and maps "unknown" to the safe
    default "engineering_only" so callers always receive a concrete class.

    Args:
        finding: A Finding instance from launcher.models.evaluation.

    Returns:
        "engineering_only" — do not send to LLM, needs code/config fix
        "llm_fixable"      — LLM re-generation can address this
        "data_fixable"     — fixing source data (claims/snippets) is required
    """
    check = finding.check.lower() if finding.check else ""
    message = finding.message or ""

    bucket = classify_check(check)

    if bucket == "mixed":
        sub = classify_mixed_check(check, message)
        # classify_mixed_check only returns "engineering_only" or "llm_fixable"
        return sub  # type: ignore[return-value]

    if bucket == "engineering_only":
        return "engineering_only"
    if bucket == "llm_fixable":
        return "llm_fixable"
    if bucket == "data_fixable":
        return "data_fixable"

    # "unknown" — fail-safe: treat as engineering_only to prevent wasting
    # LLM tokens on a check we don't understand.
    return "engineering_only"
