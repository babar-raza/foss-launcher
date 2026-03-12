"""Claim classification: filter non-user-facing claims.

Classifies claims as:
- user_facing: Keep for documentation
- internal_detail: Code internals, hex constants, spec fragments
- developer_instruction: Comments directed at developers

Operates on v2 Claim objects. Used in extract.py post-LLM phase
to filter visibility before plan assignment.

Design: sandwich model (heuristic pre-filter, optional LLM, heuristic post-validate).
"""
from __future__ import annotations

import re
from typing import Literal

from launcher.models.claims import Claim

ClaimClassification = Literal["user_facing", "internal_detail", "developer_instruction"]

# ---------------------------------------------------------------------------
# Heuristic patterns (ported from v1, tuned for v2 claim model)
# ---------------------------------------------------------------------------

_DEVELOPER_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\byour job is to\b", re.IGNORECASE),
    re.compile(r"\bwe don.t need\b", re.IGNORECASE),
    re.compile(r"\bcode in module\b", re.IGNORECASE),
    re.compile(r"\btodo\b", re.IGNORECASE),
    re.compile(r"\bfixme\b", re.IGNORECASE),
    re.compile(r"\bhack\b", re.IGNORECASE),
    re.compile(r"\bworkaround\b", re.IGNORECASE),
]

_INTERNAL_PATTERNS: list[re.Pattern[str]] = [
    # --- RFC-2119 normative keywords (uppercase only, word-boundary matched) ---
    # Uppercase-only matching follows the RFC-2119 convention; avoids false positives
    # like lowercase "must-have" or "May release" (mixed case).
    # Order: longer phrases first (MUST NOT before MUST) to prevent partial matches.
    # (?!-) negative lookahead prevents matching hyphenated forms: "MUST-HAVE",
    # "SHOULD-HAVE", etc. Lowercase hyphenated forms are already excluded by case.
    # ACCEPTED TRADE-OFF: \bOPTIONAL\b(?!-) still matches "OPTIONAL parameter" in
    # all-caps API reference prose. All-caps OPTIONAL in user-facing content is rare;
    # the benefit of catching normative RFC-2119 usage outweighs this risk.
    # If false positives appear, scope via Claim.source_path metadata.
    re.compile(
        r"\b(?:MUST\s+NOT|SHALL\s+NOT|SHOULD\s+NOT|MAY\s+NOT"
        r"|MUST|SHALL|SHOULD|MAY|REQUIRED|OPTIONAL|RECOMMENDED)\b(?!-)"
    ),
    # --- Specification language phrases (case-insensitive) ---
    re.compile(
        r"(?i)this\s+specification|as\s+specified\s+in|normative\s+reference"
        r"|this\s+field\s+specifies|informative\s+reference"
        r"|conformance\s+requirement|per\s+the\s+specification"
    ),
    # --- Hex constants: 4+ digits = binary format constants, not user-facing literals ---
    # 2-digit hex (e.g. 0xFF) is common in user-facing code examples → not flagged.
    # 4+ digits (e.g. 0x0042, 0xFFFF) are binary format constants → flagged.
    re.compile(r"\b0x[0-9A-Fa-f]{4,}\b"),
    # --- Binary format identifiers ---
    re.compile(
        r"\b(?:CompactID|FileNode|ExtendedGUID|PartitionID"
        r"|ObjectDeclaration|PropertySet|OutlineElementRTL"
        r"|FNDX|IsFileData|RgOutlineIndentDistance)\b"
    ),
    re.compile(r"\bObject\s+Data\s+BLOB\b"),
    re.compile(r"\bunsigned\s+\d+-bit\s+integer\b", re.IGNORECASE),
    # --- Binary storage terms (case-insensitive) ---
    re.compile(r"\b(?:transaction\s+log|free\s+chunk\s+list|hashed\s+chunk\s+list"
               r"|object\s+space)\b", re.IGNORECASE),
    # --- Encoding / protocol terms (case-insensitive) ---
    re.compile(r"\b(?:little-endian|big-endian|cp1252|RFC\s+4122|C706)\b", re.IGNORECASE),
    # --- Low-level structure patterns ---
    re.compile(r"\bjcid\w+", re.IGNORECASE),
    re.compile(r"\bguid[_\-]", re.IGNORECASE),
    re.compile(r"\w+\s*\(\d+\s*bytes?\)\s*:", re.IGNORECASE),
    re.compile(r"\bsection\s+\d+\.\d+", re.IGNORECASE),
    re.compile(r'["\']0x[0-9A-Fa-f]{2}["\']'),
    re.compile(r"\d+\s*bytes?\b", re.IGNORECASE),
    # --- Terms synced from spec_leakage.py _INTERNAL_TERMS (TC-3804 / TC-3828 / TC-3872) ---
    # Keep in sync with checks/spec_leakage.py _INTERNAL_TERMS.
    # NOTE: "binary format" and "file format specification" are retained here as classify_claims
    # operates on raw claim text (pre-publication), while spec_leakage.py removed
    # "file format specification" (TC-3893) to reduce false positives on published content.
    re.compile(r"\bbinary\s+formats?\b", re.IGNORECASE),
    re.compile(r"\bfile\s+format\s+specifications?\b", re.IGNORECASE),
    re.compile(r"\binternal\s+apis?\b", re.IGNORECASE),
    re.compile(r"\binternal\s+methods?\b", re.IGNORECASE),
    re.compile(r"\bprivate\s+fields?\b", re.IGNORECASE),
    re.compile(r"\bwire\s+protocols?\b", re.IGNORECASE),
    re.compile(r"\bserialization\s+formats?\b", re.IGNORECASE),
    re.compile(r"\bbyte\s+offsets?\b", re.IGNORECASE),
    re.compile(r"\bmemory\s+layouts?\b", re.IGNORECASE),
    re.compile(r"\bvtables?\b", re.IGNORECASE),
    re.compile(r"\bopcodes?\b", re.IGNORECASE),
    re.compile(r"\._(?:internal|private)\b"),
]

_CAMEL_CASE_RE = re.compile(r"[A-Z][a-z]+(?:[A-Z][a-z]+){2,}")
_CODE_IDENT_RE = re.compile(r"\b[a-z]+(?:_[a-z]+)+\b|\b[a-z]+[A-Z]\w+\b")

_STOPWORDS = frozenset({
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "can", "shall", "to", "of", "in", "for",
    "on", "with", "at", "by", "from", "as", "into", "through", "and",
    "or", "but", "not", "no", "so", "if", "this", "that", "it", "its",
})


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def classify_claim(claim_text: str) -> ClaimClassification:
    """Classify a single claim text using deterministic heuristic patterns.

    Returns one of: "user_facing", "internal_detail", "developer_instruction".
    """
    for pattern in _DEVELOPER_PATTERNS:
        if pattern.search(claim_text):
            return "developer_instruction"

    for pattern in _INTERNAL_PATTERNS:
        if pattern.search(claim_text):
            return "internal_detail"

    # Stopword ratio check — flag non-informative claims as internal
    words = claim_text.lower().split()
    if words and sum(1 for w in words if w in _STOPWORDS) / len(words) > 0.6:
        return "internal_detail"

    # CamelCase identifiers with 3+ capitals and length > 10
    for match in _CAMEL_CASE_RE.findall(claim_text):
        if len(match) > 10:
            return "internal_detail"

    # Code identifier density
    raw_words = claim_text.split()
    if raw_words:
        code_words = _CODE_IDENT_RE.findall(claim_text)
        threshold = 0.20 if len(claim_text) > 100 else 0.15
        if len(code_words) / len(raw_words) > threshold:
            return "internal_detail"

    return "user_facing"


# ---------------------------------------------------------------------------
# Claim visibility classification (relocated from TC-3908-H5)
# Canonical location; compat shim at shared/extract_claims.py re-exports this.
# ---------------------------------------------------------------------------

_INTERNAL_VISIBILITY_TERMS: tuple[str, ...] = (
    r"internal\s+api\b",
    r"internal\s+method\b",
    r"private\s+field\b",
    r"wire\s+protocol\b",
    r"serialization\s+format\b",
    r"byte\s+offset\b",
    r"memory\s+layout\b",
    r"\bvtable\b",
    r"\bopcode",  # covers "opcode" and "opcodes"
)

_INTERNAL_VISIBILITY_PATTERN: re.Pattern[str] = re.compile(
    "|".join(_INTERNAL_VISIBILITY_TERMS),
    re.IGNORECASE,
)

_PRIVATE_MODULE_RE: re.Pattern[str] = re.compile(r"\._[a-zA-Z_]+")
_PRIVATE_IMPL_RE: re.Pattern[str] = re.compile(r"\bprivate\s+implementation\b", re.IGNORECASE)


def classify_claim_visibility(text: str, claim_kind: str) -> str:  # noqa: ARG001
    """Classify a claim as ``'public'`` or ``'internal'``.

    Returns ``'internal'`` when the text contains implementation-internal
    terminology, private module references, or private-implementation phrases.
    Returns ``'public'`` otherwise.

    The *claim_kind* parameter is accepted for API compatibility but unused.
    """
    if _INTERNAL_VISIBILITY_PATTERN.search(text):
        return "internal"
    if _PRIVATE_MODULE_RE.search(text):
        return "internal"
    if _PRIVATE_IMPL_RE.search(text):
        return "internal"
    return "public"


def filter_claims(claims: list[Claim]) -> list[Claim]:
    """Filter a list of Claim objects, keeping only user_facing ones.

    Claims classified as internal_detail or developer_instruction are
    re-tagged with visibility="internal" so downstream phases skip them.

    Returns a new list — does not mutate input.
    """
    result: list[Claim] = []
    for claim in claims:
        classification = classify_claim(claim.text)
        if classification == "user_facing":
            result.append(claim)
        else:
            # Re-tag as internal so the claim is preserved in artifacts
            # but excluded from page assignment
            result.append(claim.model_copy(update={"visibility": "internal"}))
    return result
