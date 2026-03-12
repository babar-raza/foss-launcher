"""Check 2: Heading structure validation."""
from __future__ import annotations

import re

from launcher.models.evaluation import Finding


# TC-HO-08C: Tier-aware heading-density thresholds.
# Tuple: (min_word_count_for_check, min_h2_count_required).
# Tier C repos (limited docs) get a much more lenient threshold.
_TIER_HEADING: dict[str, tuple[int, int]] = {
    "A": (500, 2),   # 500+ words → need ≥2 H2s
    "B": (500, 1),   # 500+ words → need ≥1 H2
    "C": (1000, 1),  # 1000+ words → need ≥1 H2 (very lenient)
}


def check_structure(content: str, slug: str, *, richness_tier: str = "A") -> list[Finding]:
    """Validate heading hierarchy and structure.

    TC-HO-08C: ``richness_tier`` (one of "A", "B", "C") adjusts the heading-density
    threshold so Tier C pages (limited documentation) are not penalised for having
    fewer H2 sections.  Defaults to "A" for backward compatibility.
    """
    findings: list[Finding] = []

    # Extract body (after frontmatter)
    body = re.sub(r"^---\n.*?\n---\n?", "", content, flags=re.DOTALL)

    # Strip fenced code blocks so Python comments aren't mis-detected as headings
    body_no_code = re.sub(r"```[^\n]*\n.*?```", "", body, flags=re.DOTALL)

    # Find all headings
    headings = re.findall(r"^(#{1,6})\s+(.+)$", body_no_code, re.MULTILINE)

    if not headings:
        findings.append(
            Finding(
                check="structure",
                message="No headings found",
                severity="high",
                location=slug,
            )
        )
        return findings

    # Check for H1 (should only be in frontmatter title, not body)
    h1_count = sum(1 for h, _ in headings if len(h) == 1)
    if h1_count > 0:
        findings.append(
            Finding(
                check="structure",
                message=f"Found {h1_count} H1 headings in body (should be in frontmatter only)",
                severity="high",
                location=slug,
            )
        )

    # Check heading hierarchy (no skipping levels)
    prev_level = 1
    for hashes, text in headings:
        level = len(hashes)
        if level > prev_level + 1:
            findings.append(
                Finding(
                    check="structure",
                    message=f"Heading level skip: H{prev_level} -> H{level} at '{text}'",
                    severity="medium",
                    location=slug,
                    section_id=text,
                )
            )
        prev_level = level

    # Check for template-label headings (bare placeholders)
    template_patterns = [
        "[section title]",
        "[content]",
        "section heading",
        "tbd",
        "todo",
    ]
    for _, text in headings:
        lower = text.lower().strip()
        if any(p in lower for p in template_patterns):
            findings.append(
                Finding(
                    check="structure",
                    message=f"Template-label heading: '{text}'",
                    severity="high",
                    location=slug,
                    section_id=text,
                )
            )

    # Check 2: Deep heading H5+
    for hashes, text in headings:
        if len(hashes) >= 5:
            findings.append(Finding(
                check="structure",
                message=f"Deep heading H{len(hashes)} rarely needed in docs: '{text[:50]}'",
                severity="low",
                location=slug,
                section_id=text,
            ))

    # Check 3: Heading too long (>80 chars)
    # Strip HTML tags before measuring: reference page headings include
    # `<a id="...long-anchor..."></a>` tags that inflate the character count.
    for hashes, text in headings:
        clean_text = re.sub(r"<[^>]+>", "", text).strip()
        if len(clean_text) > 80:
            findings.append(Finding(
                check="structure",
                message=f"Heading too long ({len(clean_text)} chars): '{clean_text[:50]}...'",
                severity="medium",
                location=slug,
                section_id=text,
            ))

    # Check 4: Insufficient heading density — tier-aware (TC-HO-08C)
    word_count = len(body_no_code.split())
    h2_count = sum(1 for h, _ in headings if len(h) == 2)
    _wc_threshold, _h2_min = _TIER_HEADING.get(richness_tier, _TIER_HEADING["A"])
    if word_count > _wc_threshold and h2_count < _h2_min:
        findings.append(Finding(
            check="structure",
            message=f"Insufficient structure: {h2_count} H2 headings for {word_count}-word page",
            severity="low",
            location=slug,
        ))

    return findings


# ---------------------------------------------------------------------------
# Golden spec compliance — markdown-native (TC-3864)
# ---------------------------------------------------------------------------


def _split_markdown_sections(body: str) -> list[tuple[str, str]]:
    """Split markdown body into (heading, content) pairs.

    Returns list of (heading_text, section_body) for each ## heading found.
    The first item may have an empty heading if content precedes the first ##.
    """
    parts: list[tuple[str, str]] = []
    # Split on ## headings (level 2)
    chunks = re.split(r"\n(## [^\n]+)", "\n" + body)
    # chunks: [pre_content, "## Heading1", content1, "## Heading2", content2, ...]
    if chunks:
        pre = chunks[0].strip()
        if pre:
            parts.append(("", pre))
        for i in range(1, len(chunks), 2):
            heading = chunks[i].lstrip("#").strip()
            section_body = chunks[i + 1] if i + 1 < len(chunks) else ""
            parts.append((heading, section_body))
    return parts


def check_golden_spec_from_markdown(
    content: str,
    slug: str,
    page_role: str,
    golden_dir: object,  # Path | None
    variant: str = "standard",
) -> list[Finding]:
    """Check markdown content against GoldenBlockSpec requirements.

    TC-3881 Wave 3 (G5): Now performs section-level compliance checking.
    For each detected H2 section, looks up the golden spec for that heading
    and checks code-block and word-count requirements per section.
    Falls back to page-level aggregation if no section-level specs match.

    Returns [] if golden_dir is None/missing, the role is unknown, or any
    exception occurs (graceful degradation).
    """
    if golden_dir is None:
        return []
    try:
        from pathlib import Path as _Path
        gdir = _Path(golden_dir) if not isinstance(golden_dir, _Path) else golden_dir
        if not gdir.exists():
            return []
        from launcher.shared.golden_loader import GoldenIndex
        index = GoldenIndex.load(gdir)
        golden_page = index.get(page_role, variant) or index.get(page_role, "minimal")
        if golden_page is None:
            return []
    except Exception:
        return []

    findings: list[Finding] = []

    # Strip frontmatter for body analysis
    body = re.sub(r"^---\n.*?\n---\n?", "", content, flags=re.DOTALL)

    # TC-3881 (G5): Section-level compliance check
    detected_sections = _split_markdown_sections(body)
    section_level_matches = 0

    for heading, sec_body in detected_sections:
        if not heading:
            continue  # skip pre-heading content
        spec = index.get_spec(page_role, golden_page.variant, heading)
        if spec is None:
            continue
        section_level_matches += 1

        rbt = getattr(spec, "required_block_types", []) or []
        if "code" in rbt:
            has_code = bool(re.search(r"```", sec_body))
            if not has_code:
                findings.append(Finding(
                    check="structure",
                    message=(
                        f"Section '{heading}' requires a code block per golden spec"
                        " but none found."
                    ),
                    severity="high",
                    location=slug,
                    section_id=heading,
                ))

        mw = getattr(spec, "min_words", 0) or 0
        if mw > 0:
            prose = re.sub(r"```[^\n]*\n.*?```", "", sec_body, flags=re.DOTALL)
            wc = len(prose.split())
            if wc < mw:
                findings.append(Finding(
                    check="structure",
                    message=(
                        f"Section '{heading}' has {wc} prose words; "
                        f"golden spec requires \u2265{mw}."
                    ),
                    severity="medium",
                    location=slug,
                    section_id=heading,
                ))

    # Fallback: page-level aggregation when no section specs matched
    if section_level_matches == 0:
        needs_code = False
        total_min_words = 0
        for section in golden_page.sections:
            spec = index.get_spec(page_role, golden_page.variant, section.heading)
            if spec is None:
                continue
            rbt = getattr(spec, "required_block_types", []) or []
            if "code" in rbt:
                needs_code = True
            mw = getattr(spec, "min_words", 0) or 0
            total_min_words += mw

        has_code = bool(re.search(r"```", body))
        if needs_code and not has_code:
            findings.append(Finding(
                check="structure",
                message=(
                    f"Page role '{page_role}' requires a code block per golden spec"
                    " but none found in body."
                ),
                severity="high",
                location=slug,
            ))

        if total_min_words > 0:
            prose = re.sub(r"```[^\n]*\n.*?```", "", body, flags=re.DOTALL)
            word_count = len(prose.split())
            if word_count < total_min_words:
                findings.append(Finding(
                    check="structure",
                    message=(
                        f"Page body has {word_count} prose words; "
                        f"golden spec requires \u2265{total_min_words}."
                    ),
                    severity="medium",
                    location=slug,
                ))

    return findings


# ---------------------------------------------------------------------------
# Block spec compliance check (G004) — TC-3844
# ---------------------------------------------------------------------------

def check_block_spec_compliance(
    page_ir: object,
    page_role: str,
    golden_dir: object,  # Path | None
    variant: str = "standard",
) -> list:
    """Check page sections against GoldenBlockSpec requirements.

    Returns findings for missing code blocks (high) and
    under-length sections (medium). Returns [] if golden_dir is
    None/missing or any exception occurs.
    """
    if golden_dir is None:
        return []
    try:
        from pathlib import Path as _Path
        gdir = _Path(golden_dir) if not isinstance(golden_dir, _Path) else golden_dir
        if not gdir.exists():
            return []
        from launcher.shared.golden_loader import GoldenIndex
        index = GoldenIndex.load(gdir)
    except Exception:
        return []

    findings = []
    sections = getattr(page_ir, "sections", []) or []
    for section in sections:
        heading = getattr(section, "heading", "") or ""
        spec = index.get_spec(page_role, variant, heading)
        if spec is None:
            continue

        # Check code block requirement (required_block_types contains "code")
        required_block_types = getattr(spec, "required_block_types", []) or []
        if "code" in required_block_types:
            has_code = any(
                getattr(block, "type", "") in ("code", "fence")
                for block in (getattr(section, "blocks", []) or [])
            )
            if not has_code:
                findings.append({
                    "check": "structure",
                    "message": (
                        f"Section '{heading}' requires a code block per golden spec"
                        " but none found."
                    ),
                    "severity": "high",
                    "location": heading,
                })

        # Check word count requirement
        min_words = getattr(spec, "min_words", 0) or 0
        if min_words > 0:
            word_count = len((getattr(section, "body", "") or "").split())
            if word_count < min_words:
                findings.append({
                    "check": "structure",
                    "message": (
                        f"Section '{heading}' has {word_count} words "
                        f"(golden spec requires \u2265{min_words})."
                    ),
                    "severity": "medium",
                    "location": heading,
                })

    return findings
