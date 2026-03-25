"""Check: Golden template conformance scoring (TC-2500).

Computes a continuous conformance score (0.0-1.0) measuring how closely a
generated page's structure matches its golden template across 5 dimensions:

1. Section Coverage   (0.25) - fraction of golden sections present
2. Section Order      (0.15) - Kendall tau on matched section ordering
3. Depth Proportion   (0.25) - cosine similarity of word-count distribution
4. Block-Type Cover   (0.20) - average Jaccard of block type sets per section
5. Code Density Align (0.15) - ratio similarity of code-to-prose per section

Unlike the binary golden_spec check (which asks "does this section have code?"),
this check measures *degree of conformance* — two pages that both pass
golden_spec can still differ significantly in conformance score.
"""
from __future__ import annotations

import math
import re
from pathlib import Path

from launcher.models.evaluation import Finding

# Module-level result cache: slug -> (score, breakdown)
# Populated by check_golden_conformance(), consumed by get_conformance_result().
_conformance_cache: dict[str, tuple[float | None, dict[str, float]]] = {}

# Dimension weights (must sum to 1.0)
_W_COVERAGE = 0.25
_W_ORDER = 0.15
_W_DEPTH = 0.25
_W_BLOCK_TYPE = 0.20
_W_CODE_DENSITY = 0.15

# Finding severity thresholds — TC-5145: tightened for Phase 2
# Previous: HIGH < 0.35, MEDIUM < 0.55, LOW < 0.75
_THRESHOLD_HIGH = 0.50
_THRESHOLD_MEDIUM = 0.65
_THRESHOLD_LOW = 0.80

_FENCE_RE = re.compile(r"```[^\n]*\n.*?```", re.DOTALL)


def check_golden_conformance(
    content: str,
    slug: str,
    *,
    page_role: str = "",
    golden_dir: "Path | None" = None,
    variant: str = "standard",
    skeleton_section_count: int = 0,
) -> list[Finding]:
    """Compute conformance score and emit findings based on thresholds.

    Returns list of Finding objects (0 or 1 finding). Also caches the
    conformance score and breakdown for retrieval by get_conformance_result().

    Graceful degradation: returns [] and caches (None, {}) when:
    - golden_dir is None or does not exist
    - No golden page exists for this page_role/variant
    - Golden page has 0 sections
    """
    if golden_dir is None:
        _conformance_cache[slug] = (None, {})
        return []

    try:
        gdir = Path(golden_dir) if not isinstance(golden_dir, Path) else golden_dir
        if not gdir.exists():
            _conformance_cache[slug] = (None, {})
            return []

        from launcher.shared.golden_loader import GoldenIndex
        index = GoldenIndex.load(gdir)
        golden_page = index.get(page_role, variant) or index.get(page_role, "standard")
        if golden_page is None or not golden_page.sections:
            _conformance_cache[slug] = (None, {})
            return []
    except Exception:
        _conformance_cache[slug] = (None, {})
        return []

    # Parse generated content into sections
    body = re.sub(r"^---\n.*?\n---\n?", "", content, flags=re.DOTALL)
    from launcher.workers.evaluate.checks.structure import split_markdown_sections
    gen_sections = split_markdown_sections(body)
    # Filter out empty-heading pre-content
    gen_sections = [(h, b) for h, b in gen_sections if h]

    if not gen_sections:
        _conformance_cache[slug] = (0.0, {
            "section_coverage": 0.0,
            "section_order": 0.0,
            "depth_proportionality": 0.0,
            "block_type_coverage": 0.0,
            "code_density_alignment": 0.0,
        })
        return [Finding(
            check="golden_conformance",
            message=f"Conformance score 0.00 — no sections found in generated page",
            severity="high",
            location=slug,
        )]

    # Build matched pairs: (golden_section_idx, gen_section_idx, GoldenSection, gen_heading, gen_body)
    matched_pairs = _match_sections(index, golden_page, page_role, gen_sections)

    # Compute 5 dimensions
    coverage = _dim_section_coverage(golden_page, matched_pairs, skeleton_section_count)
    order = _dim_section_order(matched_pairs)
    depth = _dim_depth_proportionality(golden_page, gen_sections, matched_pairs)
    block_type = _dim_block_type_coverage(matched_pairs)
    code_density = _dim_code_density_alignment(matched_pairs)

    # Composite score
    score = (
        _W_COVERAGE * coverage
        + _W_ORDER * order
        + _W_DEPTH * depth
        + _W_BLOCK_TYPE * block_type
        + _W_CODE_DENSITY * code_density
    )

    breakdown = {
        "section_coverage": round(coverage, 4),
        "section_order": round(order, 4),
        "depth_proportionality": round(depth, 4),
        "block_type_coverage": round(block_type, 4),
        "code_density_alignment": round(code_density, 4),
    }
    _conformance_cache[slug] = (round(score, 4), breakdown)

    # Emit findings based on score thresholds
    findings: list[Finding] = []
    if score < _THRESHOLD_HIGH:
        findings.append(Finding(
            check="golden_conformance",
            message=(
                f"Conformance score {score:.2f} — page structure diverges "
                f"significantly from golden template (coverage={coverage:.2f}, "
                f"order={order:.2f}, depth={depth:.2f}, blocks={block_type:.2f}, "
                f"code_density={code_density:.2f})"
            ),
            severity="high",
            location=slug,
        ))
    elif score < _THRESHOLD_MEDIUM:
        findings.append(Finding(
            check="golden_conformance",
            message=(
                f"Conformance score {score:.2f} — moderate structural divergence "
                f"from golden template (coverage={coverage:.2f}, depth={depth:.2f})"
            ),
            severity="medium",
            location=slug,
        ))
    elif score < _THRESHOLD_LOW:
        findings.append(Finding(
            check="golden_conformance",
            message=f"Conformance score {score:.2f} — minor structural divergence",
            severity="low",
            location=slug,
        ))
    # score >= _THRESHOLD_LOW → no finding

    return findings


def get_conformance_result(slug: str) -> tuple[float | None, dict[str, float]]:
    """Retrieve cached conformance result for a slug.

    Returns (conformance_score, breakdown_dict). Returns (None, {}) if
    the slug has not been evaluated or no golden template exists.
    """
    return _conformance_cache.get(slug, (None, {}))


def clear_conformance_cache() -> None:
    """Clear the module-level conformance cache. For use in tests only."""
    _conformance_cache.clear()


# ---------------------------------------------------------------------------
# Section matching
# ---------------------------------------------------------------------------

def _match_sections(
    index: "GoldenIndex",
    golden_page: "GoldenPage",
    page_role: str,
    gen_sections: list[tuple[str, str]],
) -> list[tuple[int, int, "GoldenSection", str, str]]:
    """Match golden sections to generated sections via greedy bipartite matching.

    Returns list of (golden_idx, gen_idx, GoldenSection, gen_heading, gen_body)
    for each matched pair.

    TC-GLD-015: Uses greedy bipartite matching instead of forward-only iteration.
    For each (golden_section, gen_section) pair, computes a match score via the
    3-level heading matching in GoldenIndex.resolve_section(). Candidates are
    sorted by score descending and greedily assigned so each index is used at
    most once.  This fixes under-counting when generated sections are reordered
    or when a generated heading matches a different golden section than the one
    currently being iterated.
    """
    # Build candidate match pairs with scores
    candidates: list[tuple[int, int, object, str, str, float]] = []
    for g_idx, golden_sec in enumerate(golden_page.sections):
        for gen_idx, (gen_heading, gen_body) in enumerate(gen_sections):
            section, resolution = index.resolve_section(
                page_role, golden_page.variant, gen_heading,
            )
            if section is not None and section.heading == golden_sec.heading:
                # Score: exact > substring > jaccard
                if resolution.match_level == "exact":
                    score = 1.0
                elif resolution.match_level == "substring":
                    score = 0.8
                else:
                    score = max(0.5, resolution.jaccard_score)
                candidates.append(
                    (g_idx, gen_idx, golden_sec, gen_heading, gen_body, score)
                )

    # Greedy assignment: highest score first, each index used at most once
    candidates.sort(key=lambda c: (-c[5], c[0], c[1]))
    used_golden: set[int] = set()
    used_gen: set[int] = set()
    matched: list[tuple[int, int, object, str, str]] = []
    for g_idx, gen_idx, golden_sec, gen_heading, gen_body, _score in candidates:
        if g_idx not in used_golden and gen_idx not in used_gen:
            matched.append((g_idx, gen_idx, golden_sec, gen_heading, gen_body))
            used_golden.add(g_idx)
            used_gen.add(gen_idx)

    return matched


# ---------------------------------------------------------------------------
# Dimension 1: Section Coverage
# ---------------------------------------------------------------------------

def _dim_section_coverage(
    golden_page: "GoldenPage",
    matched_pairs: list,
    skeleton_section_count: int = 0,
) -> float:
    """Fraction of golden sections matched in generated page.

    TC-DFR-003: When skeleton_section_count > 0, normalize denominator to
    min(golden_sections, skeleton_sections) so pages are not penalized for
    having fewer skeleton sections than the golden file defines.
    """
    total_golden = len(golden_page.sections)
    if total_golden == 0:
        return 1.0
    denominator = min(total_golden, skeleton_section_count) if skeleton_section_count > 0 else total_golden
    return min(1.0, len(matched_pairs) / denominator)


# ---------------------------------------------------------------------------
# Dimension 2: Section Order Fidelity
# ---------------------------------------------------------------------------

def _dim_section_order(matched_pairs: list) -> float:
    """Kendall tau correlation of matched section ordering, scaled to [0, 1].

    Compares golden section indices against generated section indices.
    tau = (concordant - discordant) / (n*(n-1)/2), scaled: (tau + 1) / 2.
    Returns 1.0 if fewer than 2 matched pairs.
    """
    n = len(matched_pairs)
    if n < 2:
        return 1.0

    # Extract (golden_idx, gen_idx) pairs, sorted by golden_idx for determinism
    pairs = sorted([(g_idx, gen_idx) for g_idx, gen_idx, *_ in matched_pairs])

    concordant = 0
    discordant = 0
    for i in range(n):
        for j in range(i + 1, n):
            # Golden order is guaranteed ascending (sorted above)
            # Check if generated order agrees
            if pairs[i][1] < pairs[j][1]:
                concordant += 1
            elif pairs[i][1] > pairs[j][1]:
                discordant += 1
            # ties don't count

    denom = n * (n - 1) / 2
    if denom == 0:
        return 1.0
    tau = (concordant - discordant) / denom
    return (tau + 1.0) / 2.0


# ---------------------------------------------------------------------------
# Dimension 3: Depth Proportionality
# ---------------------------------------------------------------------------

def _dim_depth_proportionality(
    golden_page: "GoldenPage",
    gen_sections: list[tuple[str, str]],
    matched_pairs: list,
) -> float:
    """Cosine similarity of normalized word-count vectors for matched sections."""
    if not matched_pairs:
        return 0.0

    golden_total = golden_page.total_word_count or 1
    gen_total = sum(_prose_word_count(body) for _, body in gen_sections) or 1

    golden_vec: list[float] = []
    gen_vec: list[float] = []

    for g_idx, gen_idx, golden_sec, gen_heading, gen_body in matched_pairs:
        golden_vec.append(golden_sec.word_count / golden_total)
        gen_vec.append(_prose_word_count(gen_body) / gen_total)

    return _cosine_similarity(golden_vec, gen_vec)


def _prose_word_count(text: str) -> int:
    """Count prose words (excluding code blocks and headings)."""
    no_code = _FENCE_RE.sub("", text)
    no_code = re.sub(r"`[^`]+`", "", no_code)
    no_code = re.sub(r"^#{1,6}\s+.+$", "", no_code, flags=re.MULTILINE)
    no_code = re.sub(r"^\|.+$", "", no_code, flags=re.MULTILINE)
    return len(no_code.split())


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two vectors. Returns 0.0 for zero vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0.0 or mag_b == 0.0:
        return 0.0
    return max(0.0, min(1.0, dot / (mag_a * mag_b)))


# ---------------------------------------------------------------------------
# Dimension 4: Block-Type Coverage
# ---------------------------------------------------------------------------

def _dim_block_type_coverage(matched_pairs: list) -> float:
    """Average Jaccard similarity of block type sets for matched section pairs."""
    if not matched_pairs:
        return 0.0

    from launcher.workers.evaluate.checks.golden_sequence import get_block_sequence

    scores: list[float] = []
    for g_idx, gen_idx, golden_sec, gen_heading, gen_body in matched_pairs:
        golden_types = set(golden_sec.block_sequence) if golden_sec.block_sequence else set()
        gen_types = set(get_block_sequence(gen_body))

        if not golden_types and not gen_types:
            scores.append(1.0)
        elif not golden_types or not gen_types:
            scores.append(0.0)
        else:
            intersection = len(golden_types & gen_types)
            union = len(golden_types | gen_types)
            scores.append(intersection / union if union > 0 else 0.0)

    return sum(scores) / len(scores) if scores else 0.0


# ---------------------------------------------------------------------------
# Dimension 5: Code Density Alignment
# ---------------------------------------------------------------------------

def _dim_code_density_alignment(matched_pairs: list) -> float:
    """Ratio similarity of code-to-prose ratio for matched sections with code.

    For each matched pair where the golden section has code:
      similarity = 1.0 - |golden_ratio - gen_ratio|

    Returns 1.0 if no golden sections have code (nothing to compare).
    """
    scores: list[float] = []

    for g_idx, gen_idx, golden_sec, gen_heading, gen_body in matched_pairs:
        golden_ratio = getattr(golden_sec, "code_to_prose_ratio", 0.0)
        if golden_ratio <= 0.0 and not getattr(golden_sec, "has_code", False):
            continue  # Skip sections without code in golden

        # Compute generated section's code-to-prose ratio
        gen_ratio = _compute_code_ratio(gen_body)
        diff = abs(golden_ratio - gen_ratio)
        scores.append(max(0.0, 1.0 - diff))

    if not scores:
        return 1.0  # No code sections to compare

    return sum(scores) / len(scores)


def _compute_code_ratio(text: str) -> float:
    """Compute code-to-prose character ratio for a section."""
    code_chars = sum(len(m) for m in re.findall(r"```[^\n]*\n[\s\S]*?```", text))
    prose_text = _FENCE_RE.sub("", text)
    prose_text = re.sub(r"^#{1,6}\s+.+$", "", prose_text, flags=re.MULTILINE)
    prose_chars = len(prose_text.strip())
    total = prose_chars + code_chars
    return code_chars / total if total > 0 else 0.0
