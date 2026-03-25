"""Snippet-to-claim linking and tier relevance assignment.

TC-5135: Three-tier structural linking cascade:
  Tier 1 — API identity: match snippet's demonstrated class/methods against
           claims that reference the same API entities. Structural, not lexical.
  Tier 2 — TF-IDF cosine: IDF-weighted vocabulary overlap from shared/embeddings.
           Automatically downweights domain-frequent terms.
  Tier 3 — Word overlap: legacy _link_snippet_to_claims() for anything unlinked.
"""
from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from launcher.models.claims import Claim, Snippet
from launcher.models.product import ApiSurface
from launcher.shared.embeddings import compute_tfidf_similarity

if TYPE_CHECKING:
    from launcher.models.understanding import ApiFact

logger = logging.getLogger(__name__)


def _assign_tier_relevance(text: str, kind: str, api_surface: ApiSurface) -> str:
    """Determine tier relevance based on claim content.

    - API claims mentioning public classes -> "full"
    - Install/config claims -> "all" (relevant at every tier)
    - Feature claims -> "all"
    """
    if kind == "api":
        # Check if the claim mentions any known public class
        for cls_name in api_surface.public_classes:
            if cls_name.lower() in text.lower():
                return "full"
        return "core"

    if kind in ("install", "config", "license"):
        return "all"

    return "all"


# TC-5121: Expanded stopword list — generic English, code keywords, and very
# high-frequency domain words that match nearly every claim/snippet pair.
# NOTE: Product-specific terms (workbook, worksheet, cell, scene, node) are
# intentionally NOT included — they carry meaningful signal for API linking.
_LINKING_STOPWORDS: frozenset[str] = frozenset({
    # Generic English
    "the", "and", "for", "from", "with", "this", "that", "import",
    "not", "are", "can", "has", "have", "use", "will", "also",
    "its", "all", "any", "but", "into", "each", "when", "both",
    "only", "does", "such", "than", "them", "then", "should",
    "which", "there", "these", "their", "other", "using", "about",
    "more", "like", "some", "most", "very", "been", "were",
    # Python/code keywords
    "class", "def", "self", "none", "true", "false", "return",
    "import", "pass", "raise", "except", "try", "finally",
    "lambda", "yield", "async", "await", "print",
    # Very-high-frequency domain words (match nearly everything)
    "file", "data", "type", "name", "value", "method", "object",
    "new", "set", "get", "add", "create", "string", "list",
    "format", "path", "error", "default", "result", "index",
    "support", "supports", "provides", "allows", "enables",
    "function", "parameter", "returns", "specified", "given",
})


# ---------------------------------------------------------------------------
# TC-5135: Tier 1 — API identity matching
# ---------------------------------------------------------------------------

_CLASS_INSTANTIATE_RE = re.compile(r"\b([A-Z][A-Za-z0-9]+)\s*\(")
_METHOD_CALL_RE = re.compile(r"\b([A-Z][A-Za-z0-9]+)\.(\w+)\s*\(")
_MAX_LINKS_PER_SNIPPET: int = 10
_TFIDF_LINK_THRESHOLD: float = 0.25


def _strip_namespace(name: str, platform: str = "python") -> str:
    """Strip outer namespace qualifiers from a type or method name.

    TC-PLT-213: Different platforms use different separator conventions:
    - C++: ``Aspose::Slides::Presentation`` → ``Presentation``
    - Java: ``com.aspose.slides.Presentation`` → ``Presentation``
    - C#/.NET: ``Aspose.Slides.Presentation`` → ``Presentation``
    - Python: no stripping needed (flat imports)

    Only strips the outer namespace; ``ClassName.method`` is preserved.
    """
    if platform == "python":
        return name
    if platform == "cpp" and "::" in name:
        return name.rsplit("::", 1)[-1]
    if platform in ("java", "dotnet") and "." in name:
        # Preserve ClassName.method pattern (exactly 2 parts, first starts uppercase)
        parts = name.split(".")
        if len(parts) == 2 and parts[0][0:1].isupper():
            return name  # Already a Class.method key
        return parts[-1]
    return name


def _detect_api_entities(
    code: str,
    public_classes: list[str],
) -> tuple[str, list[str]]:
    """Extract the primary class and method calls a snippet demonstrates.

    Searches for known class names (case-sensitive whole-word) and extracts
    ``ClassName.method()`` call patterns. Deterministic string matching only.

    Returns:
        (primary_class, [method_keys]) where method_keys are lowercase
        ``"classname.method"`` strings.
    """
    if not code or not public_classes:
        return ("", [])

    # Build a lookup set for fast matching
    known = set(public_classes)

    # Find all class instantiations/references matching known classes
    found_classes: list[str] = []
    for match in _CLASS_INSTANTIATE_RE.finditer(code):
        name = match.group(1)
        if name in known:
            found_classes.append(name)

    # Also check for bare references (e.g. variable type hints, isinstance)
    for cls in public_classes:
        # Whole-word match, case-sensitive
        if re.search(rf"\b{re.escape(cls)}\b", code):
            if cls not in found_classes:
                found_classes.append(cls)

    primary = found_classes[0] if found_classes else ""

    # Extract Class.method() patterns — also detect var.method() when var was
    # assigned from a known class (e.g. "ws = Worksheet()\nws.get_cells()")
    _var_re = re.compile(r"(\w+)\s*=\s*(" + "|".join(re.escape(c) for c in known) + r")\s*\(") if known else None
    var_to_class: dict[str, str] = {}
    if _var_re:
        for m in _var_re.finditer(code):
            var_to_class[m.group(1)] = m.group(2)

    _any_method_re = re.compile(r"\b(\w+)\.(\w+)\s*\(")
    methods: list[str] = []
    for match in _any_method_re.finditer(code):
        receiver, method_name = match.group(1), match.group(2)
        # Direct Class.method() call
        if receiver in known:
            key = f"{receiver}.{method_name}"
            if key not in methods:
                methods.append(key)
        # Variable assigned from a known class
        elif receiver in var_to_class:
            cls_name = var_to_class[receiver]
            key = f"{cls_name}.{method_name}"
            if key not in methods:
                methods.append(key)

    return (primary, methods)


def _build_claim_api_index(
    claims: list[Claim],
    api_facts: list[ApiFact],
    public_classes: list[str],
) -> dict[str, list[str]]:
    """Map API entity names to claim IDs that reference them.

    Scans each claim's text for known class names and ``Class.method`` patterns
    (from api_facts). Returns a reverse index like::

        {"workbook": ["CLM-1", "CLM-5"], "workbook.save": ["CLM-3"]}
    """
    index: dict[str, list[str]] = {}

    # Build known method patterns from api_facts
    known_methods: set[str] = set()
    for fact in api_facts:
        cn = getattr(fact, "class_name", "") or ""
        mn = getattr(fact, "member_name", "") or ""
        if cn and mn:
            known_methods.add(f"{cn}.{mn}")

    cls_lower_map = {c.lower(): c for c in public_classes}

    for claim in claims:
        text_lower = claim.text.lower()

        # Check class name mentions
        for cls in public_classes:
            if cls.lower() in text_lower:
                key = cls.lower()
                lst = index.setdefault(key, [])
                if claim.claim_id not in lst:
                    lst.append(claim.claim_id)

        # Check Class.method mentions
        for method_key in known_methods:
            if method_key.lower() in text_lower:
                key = method_key.lower()
                lst = index.setdefault(key, [])
                if claim.claim_id not in lst:
                    lst.append(claim.claim_id)

    return index


# ---------------------------------------------------------------------------
# TC-5135: Orchestrator — link_snippets
# ---------------------------------------------------------------------------

def link_snippets(
    snippets: list[Snippet],
    claims: list[Claim],
    api_surface: ApiSurface,
    api_facts: list[ApiFact],
) -> list[Snippet]:
    """TC-5135: Three-tier structural linking cascade.

    Tier 1: API identity — structural class/method matching
    Tier 2: TF-IDF cosine — vocabulary-weighted overlap
    Tier 3: Word overlap — legacy fallback

    Post-linking: UND-03 redistribution to diversify coverage.
    """
    if not snippets:
        return snippets

    if not claims:
        return snippets

    public_classes = getattr(api_surface, "public_classes", []) or []
    claim_api_index = _build_claim_api_index(claims, api_facts, public_classes)
    claim_id_set = {c.claim_id for c in claims}

    tier1_count = 0
    tier2_count = 0
    tier3_count = 0

    result: list[Snippet] = []

    for snippet in snippets:
        # Preserve already-linked snippets
        existing = getattr(snippet, "claim_ids", None) or []
        if existing:
            result.append(snippet)
            continue

        code = getattr(snippet, "code", "") or ""
        linked: list[str] = []

        # --- Tier 1: API identity ---
        primary_cls, method_keys = _detect_api_entities(code, public_classes)
        if primary_cls or method_keys:
            seen: set[str] = set()
            # Method-level matches first (most precise)
            for mk in method_keys:
                for cid in claim_api_index.get(mk, []):
                    if cid not in seen and cid in claim_id_set:
                        linked.append(cid)
                        seen.add(cid)
            # Class-level matches
            if primary_cls:
                for cid in claim_api_index.get(primary_cls.lower(), []):
                    if cid not in seen and cid in claim_id_set:
                        linked.append(cid)
                        seen.add(cid)
            if linked:
                tier1_count += 1

        # --- Tier 2: TF-IDF cosine (only if Tier 1 found nothing) ---
        if not linked:
            tfidf_scores: list[tuple[str, float]] = []
            for claim in claims:
                score = compute_tfidf_similarity(code, claim.text)
                if score >= _TFIDF_LINK_THRESHOLD:
                    tfidf_scores.append((claim.claim_id, score))
            # Sort by score descending for deterministic selection.
            # Round to 4 decimal places to eliminate floating-point noise at score boundaries.
            tfidf_scores.sort(key=lambda x: (-round(x[1], 4), x[0]))
            linked = [cid for cid, _ in tfidf_scores]
            if linked:
                tier2_count += 1

        # --- Tier 3: Word overlap fallback ---
        if not linked:
            linked = _link_snippet_to_claims(code, claims)
            if linked:
                tier3_count += 1

        # Cap at max links
        linked = linked[:_MAX_LINKS_PER_SNIPPET]

        result.append(snippet.model_copy(update={"claim_ids": linked}))

    # Post-linking: UND-03 redistribution
    result = _redistribute_snippets(result, claims)

    total = len(snippets)
    logger.info(
        "link_snippets [TC-5135]: total=%d tier1=%d tier2=%d tier3=%d",
        total, tier1_count, tier2_count, tier3_count,
    )

    return result


def _link_snippet_to_claims(code: str, claims: list[Claim]) -> list[str]:
    """Link a code snippet to claims via keyword overlap.

    A snippet is linked to a claim if they share meaningful words
    (class names, method names, etc.).
    """
    linked: list[str] = []
    code_words = set(re.findall(r"\b[A-Za-z_]\w{2,}\b", code.lower())) - _LINKING_STOPWORDS

    for claim in claims:
        claim_words = set(re.findall(r"\b[A-Za-z_]\w{2,}\b", claim.text.lower())) - _LINKING_STOPWORDS
        # Require at least 2 shared meaningful words
        shared = code_words & claim_words
        if len(shared) >= 2:
            linked.append(claim.claim_id)

    return linked


# ---------------------------------------------------------------------------
# UND-03 + SR-01: Post-linking redistribution to diversify snippet coverage
# ---------------------------------------------------------------------------

_MAX_SNIPPETS_PER_CLAIM: int = 3
_REDISTRIBUTION_MIN_SCORE: float = 0.10


def _redistribute_snippets(
    snippets: list,
    claims: list[Claim],
    *,
    max_per_claim: int = _MAX_SNIPPETS_PER_CLAIM,
    min_score: float = _REDISTRIBUTION_MIN_SCORE,
) -> list:
    """Cap per-claim snippet count and redistribute overflow to starved claims.

    UND-03 (UND-G03): After linking, some claims accumulate many snippets
    while most claims have zero.  This pass caps any claim at *max_per_claim*
    snippets and re-links overflow to under-served claims using overlap
    coefficient scoring (intersection / min(|A|, |B|)).

    SR-01: Uses overlap coefficient instead of Jaccard to handle asymmetric
    vocabularies (code identifiers vs. natural language claim text).
    """
    if not snippets or not claims:
        return snippets

    # Build claim→snippet-indices map
    claim_to_snippets: dict[str, list[int]] = {}
    for idx, snippet in enumerate(snippets):
        for cid in getattr(snippet, "claim_ids", None) or []:
            claim_to_snippets.setdefault(cid, []).append(idx)

    # Identify overloaded claims and track which (snippet_idx, claim_id) pairs
    # are overflow — the snippet must be unlinked from that claim.
    overflow_pairs: list[tuple[int, str]] = []  # (snippet_idx, overloaded_claim_id)
    for cid, indices in list(claim_to_snippets.items()):
        if len(indices) > max_per_claim:
            for idx in indices[max_per_claim:]:
                overflow_pairs.append((idx, cid))
            claim_to_snippets[cid] = indices[:max_per_claim]

    if not overflow_pairs:
        return snippets

    # Build claim text lookup and all_claim_ids
    all_claim_ids = {c.claim_id for c in claims}
    claim_text_by_id: dict[str, str] = {c.claim_id: c.text for c in claims}

    reassigned = 0

    for idx, removed_cid in overflow_pairs:
        snippet = snippets[idx]
        code = getattr(snippet, "code", "") or ""
        code_words = set(re.findall(r"\b[A-Za-z_]\w{2,}\b", code.lower())) - _LINKING_STOPWORDS

        # Remove the overloaded claim from this snippet's claim_ids
        old_ids = list(getattr(snippet, "claim_ids", None) or [])
        kept_ids = [c for c in old_ids if c != removed_cid]

        # Try to find a replacement claim
        best_score = 0.0
        best_cid: str | None = None

        if code_words:
            # Identify starved claims (zero snippets) — refresh each iteration
            linked_cids = {cid for cid, idxs in claim_to_snippets.items() if idxs}
            starved_ids = all_claim_ids - linked_cids

            # Prioritize starved claims, then under-capacity claims
            candidates = list(starved_ids) + [
                cid for cid in all_claim_ids
                if cid not in starved_ids
                and cid != removed_cid
                and cid not in old_ids
                and len(claim_to_snippets.get(cid, [])) < max_per_claim
            ]

            for cid in candidates:
                ct = claim_text_by_id.get(cid, "")
                claim_words = set(re.findall(r"\b[A-Za-z_]\w{2,}\b", ct.lower())) - _LINKING_STOPWORDS
                if not claim_words:
                    continue
                intersection = len(code_words & claim_words)
                if intersection == 0:
                    continue
                # SR-01: Use overlap coefficient (intersection / min(|A|,|B|))
                # instead of Jaccard.  Handles asymmetric vocabularies better.
                min_set = min(len(code_words), len(claim_words))
                overlap = intersection / min_set if min_set > 0 else 0.0
                if overlap > best_score:
                    best_score = overlap
                    best_cid = cid

        if best_score >= min_score and best_cid:
            kept_ids.append(best_cid)
            claim_to_snippets.setdefault(best_cid, []).append(idx)
            reassigned += 1

        # If no valid target and snippet would be orphaned, keep original link
        if not kept_ids:
            kept_ids = [removed_cid]
            claim_to_snippets.setdefault(removed_cid, []).append(idx)

        snippets[idx] = snippet.model_copy(update={"claim_ids": kept_ids})

    if overflow_pairs:
        effectiveness = (reassigned / len(overflow_pairs) * 100) if overflow_pairs else 0.0
        logger.info(
            "redistribute_snippets [UND-03]: reassigned=%d overflow=%d effectiveness=%.1f%%",
            reassigned, len(overflow_pairs), effectiveness,
        )

    return snippets


# ---------------------------------------------------------------------------
# TC-5174: Bundle finalization gate — filter orphaned snippets
# ---------------------------------------------------------------------------


def promote_corroborated_claims(claims: list[Claim]) -> tuple[list[Claim], int]:
    """TC-UND-210: Promote llm claims to llm_corroborated when a docstring backs the same class.

    An LLM claim is corroborated when its text contains a PascalCase class name that also
    appears as the subject of a docstring claim (i.e., the docstring evidence source_file
    starts with ``"docstring:<ClassName>"``).

    Returns:
        (updated_claims, promoted_count) — updated_claims has the same length as the input.
    """
    from launcher.workers.understand.extract._validation import CONFIDENCE_BY_SOURCE

    # Build the set of class names backed by at least one docstring claim.
    docstring_classes: set[str] = set()
    for c in claims:
        if getattr(c, "claim_source", "") == "docstring":
            for ev in getattr(c, "evidence", []) or []:
                sf = getattr(ev, "source_file", "") or ""
                if sf.startswith("docstring:"):
                    class_ref = sf[len("docstring:"):].split(".")[0]
                    if class_ref:
                        docstring_classes.add(class_ref)

    if not docstring_classes:
        logger.info(
            "[Linking] promote_corroborated_claims: docstring_classes is empty "
            "(no class-level docstrings found); skipping corroboration promotion. "
            "Total claims: %d", len(claims),
        )
        return claims, 0

    # TC-5198: Promote both "llm" and "llm_sparse_grounding" claims
    _PROMOTABLE_SOURCES = ("llm", "llm_sparse_grounding")

    _pascal = re.compile(r"\b[A-Z][a-zA-Z0-9]*[a-z][a-zA-Z0-9]*\b")
    promoted = 0
    result: list[Claim] = []
    for c in claims:
        if getattr(c, "claim_source", "") in _PROMOTABLE_SOURCES:
            tokens = set(_pascal.findall(getattr(c, "text", "") or ""))
            if tokens & docstring_classes:
                logger.debug(
                    "[Linking] promoted claim %s: matched docstring classes %s",
                    getattr(c, "claim_id", "?"),
                    tokens & docstring_classes,
                )
                result.append(c.model_copy(update={
                    "claim_source": "llm_corroborated",
                    "confidence": CONFIDENCE_BY_SOURCE["llm_corroborated"],
                }))
                promoted += 1
                continue
        result.append(c)

    logger.info(
        "[Linking] corroboration promotion complete: %d promoted of %d eligible "
        "(source in llm/llm_sparse_grounding), %d total claims",
        promoted,
        sum(1 for c in claims if getattr(c, "claim_source", "") in _PROMOTABLE_SOURCES),
        len(claims),
    )

    return result, promoted


def filter_orphaned_snippets(snippets: list[Snippet]) -> tuple[list[Snippet], int]:
    """Remove snippets with no claim links from the bundle (finalization gate).

    Called after link_snippets() to guarantee the UnderstandingBundle contains
    only snippets with at least one claim_id. Orphaned snippets are logged at
    WARNING level for auditability. Returns (filtered_list, dropped_count).

    Downstream workers (Planner, Generate) implicitly exclude orphaned snippets
    anyway, but this gate makes the invariant explicit and prevents dead data
    from accumulating in phase_store/ artifacts.
    """
    linked: list[Snippet] = []
    dropped = 0
    for s in snippets:
        if getattr(s, "claim_ids", None):
            linked.append(s)
        else:
            dropped += 1
            logger.warning(
                "filter_orphaned_snippets [TC-5174]: dropping orphaned snippet "
                "source_file=%r code_prefix=%r",
                getattr(s, "source_file", "unknown"),
                (getattr(s, "code", "") or "")[:80],
            )
    if dropped:
        logger.info(
            "filter_orphaned_snippets [TC-5174]: kept=%d dropped=%d",
            len(linked), dropped,
        )
    return linked, dropped
