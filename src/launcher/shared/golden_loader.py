"""
Golden reference index — loads and queries curated A/B exemplar files from golden/.

GoldenIndex is the single entry point. Load once at worker startup:
    index = GoldenIndex.load(Path("golden/"))

Performance note: _load_golden_for_role uses an LRU cache keyed on the absolute
golden_dir path. Call _clear_golden_cache() between test cases that use different
golden_dir fixtures.
"""
from __future__ import annotations
import functools
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# Stop-words stripped before Jaccard comparison (V2AC-02)
_STOP_WORDS: frozenset[str] = frozenset({
    "a", "an", "the", "and", "or", "of", "to", "in", "for", "on",
    "with", "at", "by", "from", "as", "is", "are", "was", "be",
})

# GL-02: Jaccard similarity threshold for section heading matching (Level 3 fallback).
# Value 0.5 (TC-3878 Wave 0): raising from 0.3 eliminates false-positive matches such as
# "Code Examples" ↔ "Usage Examples" (score=0.33) that inject wrong golden exemplars.
# A 2-token minimum guard skips Jaccard entirely for single-word headings where the
# score is unstable. No-match returns None instead of the best-below-threshold section.
_SECTION_JACCARD_THRESHOLD: float = 0.5
# Minimum meaningful token count for Level 3 Jaccard comparison (TC-3878 Wave 0).
# Single-token headings have Jaccard bounded to 0 or 1 — too binary to be useful.
_JACCARD_MIN_TOKENS: int = 2


@dataclass
class GoldenResolution:
    """Result of a golden section resolution attempt, including match metadata."""
    match_level: str  # "exact", "substring", "jaccard", "role_fallback", "miss"
    matched_heading: str
    query_heading: str
    page_role: str
    variant: str
    jaccard_score: float
    golden_page_path: str
    golden_word_count: int
    has_structural_spec: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "match_level": self.match_level,
            "matched_heading": self.matched_heading,
            "query_heading": self.query_heading,
            "page_role": self.page_role,
            "variant": self.variant,
            "jaccard_score": self.jaccard_score,
            "golden_page_path": self.golden_page_path,
            "golden_word_count": self.golden_word_count,
            "has_structural_spec": self.has_structural_spec,
        }


@dataclass
class GoldenSection:
    """One section (## heading) from a golden page."""
    heading: str
    raw_markdown: str
    word_count: int
    has_code: bool
    has_list: bool
    has_table: bool
    excerpt: str  # first 600 chars of raw_markdown
    # TC-3881 Wave 3 (G1): Structural fingerprint fields for binding prompt injection.
    code_block_count: int = 0
    list_block_count: int = 0
    table_count: int = 0
    heading_count: int = 0
    code_to_prose_ratio: float = 0.0
    block_sequence: list[str] | None = None  # TC-FIX-214: ordered block types


@dataclass
class GoldenBlockSpec:
    """Structural contract derived from a golden section."""
    required_block_types: list[str]
    min_words: int
    max_retries: int = 1


@dataclass
class GoldenPage:
    """One golden exemplar file, parsed into sections."""
    source_path: Path
    page_role: str
    variant: str
    subdomain: str
    grade: str
    sections: list[GoldenSection]
    total_word_count: int
    content: str = ""  # Full markdown (GOLDEN comment stripped); set by _parse_golden_file

    @property
    def grade_letter(self) -> str:
        """Normalize 'A-', 'B+', 'B-' → 'A', 'B', etc. Returns uppercase letter."""
        return self.grade[0].upper() if self.grade else "A"


def build_block_spec(gs: GoldenSection, richness_tier: str = "B") -> GoldenBlockSpec:
    """Derive a GoldenBlockSpec from a GoldenSection."""
    required = ["paragraph"]
    if gs.has_code:
        required.append("code")
    if gs.has_list:
        required.append("list")
    if gs.has_table:
        required.append("table")
    if richness_tier == "C":
        min_words = max(20, int(gs.word_count * 0.2))
    else:
        min_words = max(30, int(gs.word_count * 0.4))
    return GoldenBlockSpec(required_block_types=required, min_words=min_words)


class GoldenIndex:
    """In-memory index of all golden exemplar files."""

    def __init__(self) -> None:
        self._pages: dict[tuple[str, str], GoldenPage] = {}  # (page_role, variant) -> GoldenPage

    @classmethod
    def load(cls, golden_dir: Path) -> "GoldenIndex":
        """Parse all .md files in golden_dir and build the index."""
        index = cls()
        if not golden_dir.exists():
            return index
        for md_file in sorted(golden_dir.rglob("*.md")):
            try:
                page = _parse_golden_file(md_file, golden_dir)
                if page is not None:
                    key = (page.page_role, page.variant)
                    index._pages[key] = page
            except Exception:
                pass  # graceful degradation on corrupt files
        return index

    def get(self, page_role: str, variant: str) -> Optional[GoldenPage]:
        """Return the GoldenPage for the given role+variant, or None."""
        return self._pages.get((page_role, variant))

    def get_section(
        self,
        page_role: str,
        variant: str,
        section_heading: str,
    ) -> Optional[GoldenSection]:
        """Return matching GoldenSection using 3-level fallback.

        Match levels (in order):
          1. Exact match (normalized: lowercase, no punctuation, stop-words removed)
          2. Substring match (raw lowercased strings)
          3. Jaccard >= _SECTION_JACCARD_THRESHOLD on normalized stop-word-stripped tokens

        See _SECTION_JACCARD_THRESHOLD for rationale on the chosen threshold value.
        """
        page = self.get(page_role, variant)
        if page is None:
            return None
        needle = _normalize_heading(section_heading)
        raw_needle = section_heading.lower().strip()
        # Level 1: exact match (normalized)
        for s in page.sections:
            if _normalize_heading(s.heading) == needle:
                return s
        # Level 2: substring match (raw)
        for s in page.sections:
            hay = s.heading.lower().strip()
            if raw_needle in hay or hay in raw_needle:
                return s
        # Level 3: Jaccard >= _SECTION_JACCARD_THRESHOLD on normalized (stop-word stripped) tokens.
        # Skip entirely when either heading has fewer than _JACCARD_MIN_TOKENS meaningful tokens —
        # single-token headings produce unstable scores (0 or 1 only) and cause false positives.
        needle_words = set(needle.split())
        if len(needle_words) < _JACCARD_MIN_TOKENS:
            return None
        best_score, best_section = 0.0, None
        for s in page.sections:
            hay_words = set(_normalize_heading(s.heading).split())
            if len(hay_words) < _JACCARD_MIN_TOKENS:
                continue
            intersection = len(needle_words & hay_words)
            union = len(needle_words | hay_words)
            score = intersection / union if union > 0 else 0.0
            if score > best_score:
                best_score, best_section = score, s
        return best_section if best_score >= _SECTION_JACCARD_THRESHOLD else None

    def resolve_section(
        self,
        page_role: str,
        variant: str,
        section_heading: str,
    ) -> tuple[GoldenSection | None, GoldenResolution]:
        """Like get_section but also returns a GoldenResolution with match metadata."""
        page = self.get(page_role, variant)
        if page is None:
            return None, GoldenResolution(
                match_level="miss",
                matched_heading="",
                query_heading=section_heading,
                page_role=page_role,
                variant=variant,
                jaccard_score=0.0,
                golden_page_path="",
                golden_word_count=0,
                has_structural_spec=False,
            )

        page_path = str(page.source_path)
        needle = _normalize_heading(section_heading)
        raw_needle = section_heading.lower().strip()

        # Level 1: exact match (normalized)
        for s in page.sections:
            if _normalize_heading(s.heading) == needle:
                wc = sum(b.word_count for b in page.sections if b is s) or s.word_count
                return s, GoldenResolution(
                    match_level="exact",
                    matched_heading=s.heading,
                    query_heading=section_heading,
                    page_role=page_role,
                    variant=variant,
                    jaccard_score=0.0,
                    golden_page_path=page_path,
                    golden_word_count=s.word_count,
                    has_structural_spec=s.has_code and s.has_list,
                )

        # Level 2: substring match (raw)
        for s in page.sections:
            hay = s.heading.lower().strip()
            if raw_needle in hay or hay in raw_needle:
                return s, GoldenResolution(
                    match_level="substring",
                    matched_heading=s.heading,
                    query_heading=section_heading,
                    page_role=page_role,
                    variant=variant,
                    jaccard_score=0.0,
                    golden_page_path=page_path,
                    golden_word_count=s.word_count,
                    has_structural_spec=s.has_code and s.has_list,
                )

        # Level 3: Jaccard
        needle_words = set(needle.split())
        if len(needle_words) >= _JACCARD_MIN_TOKENS:
            best_score, best_section = 0.0, None
            for s in page.sections:
                hay_words = set(_normalize_heading(s.heading).split())
                if len(hay_words) < _JACCARD_MIN_TOKENS:
                    continue
                intersection = len(needle_words & hay_words)
                union = len(needle_words | hay_words)
                score = intersection / union if union > 0 else 0.0
                if score > best_score:
                    best_score, best_section = score, s
            if best_score >= _SECTION_JACCARD_THRESHOLD and best_section is not None:
                return best_section, GoldenResolution(
                    match_level="jaccard",
                    matched_heading=best_section.heading,
                    query_heading=section_heading,
                    page_role=page_role,
                    variant=variant,
                    jaccard_score=best_score,
                    golden_page_path=page_path,
                    golden_word_count=best_section.word_count,
                    has_structural_spec=best_section.has_code and best_section.has_list,
                )

        # Miss (page exists but no section matched)
        return None, GoldenResolution(
            match_level="miss",
            matched_heading="",
            query_heading=section_heading,
            page_role=page_role,
            variant=variant,
            jaccard_score=0.0,
            golden_page_path=page_path,
            golden_word_count=0,
            has_structural_spec=False,
        )

    def get_heal_excerpt(
        self,
        page_role: str,
        variant: str,
        section_heading: str,
        *,
        max_words: int = 300,
    ) -> Optional[str]:
        """Return a truncated golden excerpt for a section, or None if not found.

        Used by H2.4 heal diagnostician to provide a reference excerpt when
        suggesting regeneration strategy for a failing section.
        """
        section = self.get_section(page_role, variant, section_heading)
        if section is None:
            return None
        text = section.raw_markdown or ""
        if not text.strip():
            return None
        words = text.split()
        if len(words) > max_words:
            return " ".join(words[:max_words]) + " …"
        return text

    def get_spec(
        self,
        page_role: str,
        variant: str,
        section_heading: str,
    ) -> Optional[GoldenBlockSpec]:
        """Return GoldenBlockSpec for a section heading, or None if no golden exists."""
        section = self.get_section(page_role, variant, section_heading)
        if section is None:
            return None
        return build_block_spec(section)

    def select_for_tier(self, page_role: str, richness_tier: str) -> Optional[GoldenPage]:
        """Select the best GoldenPage for the given richness tier."""
        if richness_tier == "C":
            # Prefer minimal variant; fall back to standard
            page = self.get(page_role, "minimal") or self.get(page_role, "standard")
        else:
            # Tier A/B: prefer standard variant
            page = self.get(page_role, "standard") or self.get(page_role, "minimal")
        return page

    def all_pages(self) -> list[GoldenPage]:
        """Return all loaded golden pages in deterministic order (subdomain, role, variant)."""
        return sorted(
            self._pages.values(),
            key=lambda p: (p.subdomain, p.page_role, p.variant),
        )

    def __len__(self) -> int:
        return len(self._pages)


# -- Path -> page_role + variant mapping -------------------------------------

_VARIANT_RE = re.compile(r"\.variant-([a-z]+)\.")

def _infer_role_variant(path: Path, golden_dir: Path) -> tuple[str, str]:
    """Infer page_role and variant from the file path."""
    rel = path.relative_to(golden_dir)
    parts = rel.parts
    name = path.stem  # e.g. "feature.variant-minimal" or "installation"

    # Extract variant from filename
    m = _VARIANT_RE.search(name)
    variant = m.group(1) if m else "standard"

    # Determine page_role from path structure and filename
    subdomain = parts[0] if parts else ""

    if "_index" in name:
        if len(parts) <= 3:
            return "section_index", variant
        return "section_index", variant

    if subdomain == "docs.aspose.org":
        if "getting-started" in parts:
            if "installation" in name:
                return "installation", variant
            if "license" in name:
                return "license", variant
        if "developer-guide" in parts:
            return "workflow_page", variant
    elif subdomain == "kb.aspose.org":
        return "howto_article", variant
    elif subdomain == "reference.aspose.org":
        return "api_reference", variant
    elif subdomain == "products.aspose.org":
        return "landing", variant
    elif subdomain == "blog.aspose.org":
        return "feature_blog", variant

    # Fallback: use parent directory name
    return parts[-2] if len(parts) >= 2 else "unknown", variant


def _parse_golden_file(path: Path, golden_dir: Path) -> Optional[GoldenPage]:
    """Parse a single golden .md file into a GoldenPage."""
    raw = path.read_text(encoding="utf-8", errors="replace")
    if not raw.strip():
        return None

    page_role, variant = _infer_role_variant(path, golden_dir)
    subdomain = path.relative_to(golden_dir).parts[0] if path.relative_to(golden_dir).parts else ""

    # Strip GOLDEN REFERENCE comment if present (files start with <!-- ... -->).
    # Without this strip, content.startswith("---") is False and frontmatter is never parsed.
    content = raw
    if raw.startswith("<!--"):
        end_comment = raw.find("-->")
        if end_comment != -1:
            content = raw[end_comment + 3:].lstrip("\n")

    # GL-02: Parse grade from frontmatter; default to "A" for golden files.
    # Accept bare letters (A, B, C) and modifiers (A-, B+, B-) by checking first char.
    grade = "A"
    body = content
    if content.startswith("---"):
        end = content.find("\n---", 3)
        if end != -1:
            fm_text = content[3:end]
            for line in fm_text.splitlines():
                if line.startswith("grade:"):
                    raw_grade = line.split(":", 1)[1].strip().strip('"').strip("'")
                    if raw_grade and raw_grade[0].upper() in ("A", "B", "C", "D", "F"):
                        grade = raw_grade
                    break
            body = content[end + 4:]

    sections = _parse_sections(body)
    total_words = sum(s.word_count for s in sections)

    return GoldenPage(
        source_path=path,
        page_role=page_role,
        variant=variant,
        subdomain=subdomain,
        grade=grade,
        sections=sections,
        total_word_count=total_words,
        content=content,
    )


_FENCE_RE = re.compile(r"```[^\n]*\n.*?```", re.DOTALL)
_HEADING_RE = re.compile(r"^#{1,6}\s+(.+)$", re.MULTILINE)


def _normalize_heading(heading: str) -> str:
    """Lowercase, strip punctuation, remove stop-words for Jaccard comparison."""
    tokens = re.sub(r"[^a-z0-9\s]", "", heading.lower()).split()
    return " ".join(t for t in tokens if t not in _STOP_WORDS)

# GL-01: LRU cache for GoldenIndex to avoid re-parsing 22 files on every call.
# Cache key is the absolute path string (avoids aliasing between relative/absolute paths).
# maxsize=4 handles up to 4 distinct golden dirs (typical: 1 in production).
@functools.lru_cache(maxsize=4)
def _get_cached_index(golden_dir_str: str) -> GoldenIndex:
    """Load and cache a GoldenIndex by golden_dir absolute path string.

    Cached at process level. Use _clear_golden_cache() in tests to reset
    between test cases that use different golden_dir fixtures.
    """
    return GoldenIndex.load(Path(golden_dir_str))


def _clear_golden_cache() -> None:
    """Clear the GoldenIndex LRU cache. For use in tests only."""
    _get_cached_index.cache_clear()


def _load_golden_for_role(
    page_role: str,
    golden_dir: Path,
    section_heading: str = "",
    *,
    max_words: int = 500,
    variant: str = "standard",
) -> "str | None":
    """Load a golden excerpt for *page_role*, truncated to *max_words*.

    TC-3881 Wave 3 (G2): Accepts ``variant`` parameter for tier-aware selection.
    Tier C pages should pass ``variant="minimal"``; Tier A/B pass ``"standard"``.

    Returns ``None`` when golden_dir is missing, role not indexed, or
    section_heading given but no matching section found.

    Uses _get_cached_index (LRU cache) to avoid re-parsing all golden files
    on every call. Cache is keyed by absolute golden_dir path.
    """
    try:
        index = _get_cached_index(str(golden_dir.resolve()))
        if section_heading:
            # Try requested variant first, fall back to "standard"
            section = index.get_section(page_role, variant, section_heading)
            if section is None and variant != "standard":
                section = index.get_section(page_role, "standard", section_heading)
            if section is None:
                return None
            text = getattr(section, "raw_markdown", "") or ""
        else:
            page = index.get(page_role, variant) or index.get(page_role, "standard")
            if page is None:
                return None
            # Use concatenation of all section raw_markdown as full page text
            sections = getattr(page, "sections", []) or []
            text = "\n\n".join(
                getattr(s, "raw_markdown", "") or ""
                for s in sections
                if getattr(s, "raw_markdown", "")
            )
        if not text.strip():
            return None
        words = text.split()
        if len(words) > max_words:
            text = " ".join(words[:max_words]) + " …"
        return text
    except Exception:
        return None


def _load_golden_section_for_role(
    page_role: str,
    golden_dir: Path,
    section_heading: str,
    *,
    variant: str = "standard",
) -> "GoldenSection | None":
    """Load a GoldenSection object for structural fingerprint injection.

    TC-3881 Wave 3 (G1): Returns full GoldenSection so callers can access
    structural fingerprint fields (code_block_count, list_block_count, etc.).
    Used by `_build_golden_reference_block` to inject binding structural guidance.
    """
    try:
        index = _get_cached_index(str(golden_dir.resolve()))
        section = index.get_section(page_role, variant, section_heading)
        if section is None and variant != "standard":
            section = index.get_section(page_role, "standard", section_heading)
        return section
    except Exception:
        return None


def _summarize_section_structure(gs: "GoldenSection") -> str:
    """Return a compact structural constraint string for a golden section.

    TC-3881 Wave 3 (G1): Makes golden reference binding rather than aspirational.
    Replaces the vague "Match its depth, tone, and structure" instruction with
    an explicit list of block types the LLM must replicate.
    """
    block_types = ["paragraph"]
    if gs.code_block_count > 0:
        block_types.append(f"code ({gs.code_block_count})")
    if gs.list_block_count > 0:
        block_types.append(f"list ({gs.list_block_count})")
    if gs.table_count > 0:
        block_types.append(f"table ({gs.table_count})")
    sequence = " → ".join(block_types)
    lines = [
        f"Block sequence (minimum): {sequence}",
        f"Target depth: ~{gs.word_count} prose words | Code blocks: ≥{gs.code_block_count} | Lists: ≥{gs.list_block_count} | Tables: ≥{gs.table_count}",
        "Rule: include ALL listed block types at minimum — expand further to fully cover the topic.",
    ]
    return "\n".join(lines)


def get_nearest_golden(
    page_role: str,
    section_heading: str,
    golden_dir: "Path | None",
    *,
    variant: str = "standard",
) -> str:
    """Return the best available golden excerpt via 3-level fallback.

    TC-3878 (W2-S6): Ensures every section always has SOME golden reference
    even when no exact (page_role, section_heading) match exists.

    Level 1: Exact match — page_role + section_heading
    Level 2: Role match — same page_role, use first available section
    Level 3: Generic — any golden file with an overview/introduction section

    Returns empty string when golden_dir is None or no golden files exist.
    All exceptions are suppressed (non-blocking).
    """
    if golden_dir is None:
        return ""
    try:
        gdir = Path(golden_dir) if not isinstance(golden_dir, Path) else golden_dir
        if not gdir.exists():
            return ""

        # Level 1: Exact match
        excerpt = _load_golden_for_role(page_role, gdir, section_heading, variant=variant)
        if excerpt:
            return excerpt

        # Level 2: Same role, any section (pass empty heading to get first available)
        if page_role:
            excerpt = _load_golden_for_role(page_role, gdir, "", variant=variant)
            if excerpt:
                return excerpt

        # Level 3: Any golden file — try overview/introduction sections
        for fallback_heading in ("overview", "introduction", ""):
            excerpt = _load_golden_for_role("", gdir, fallback_heading, variant=variant)
            if excerpt:
                return excerpt
    except Exception:
        pass
    return ""


def resolve_golden_for_section(
    page_role: str,
    golden_dir: Path | None,
    section_heading: str,
) -> GoldenResolution:
    """Resolve a golden section for *page_role* and *section_heading*.

    Always returns a GoldenResolution (never None).
    - If golden_dir is None or doesn't exist: returns miss.
    - Tries resolve_section with variant "standard".
    - If section found: returns its resolution.
    - If no section but the role exists in the index: returns role_fallback.
    """
    miss = GoldenResolution(
        match_level="miss",
        matched_heading="",
        query_heading=section_heading,
        page_role=page_role,
        variant="standard",
        jaccard_score=0.0,
        golden_page_path="",
        golden_word_count=0,
        has_structural_spec=False,
    )
    if golden_dir is None:
        return miss
    gdir = Path(golden_dir) if not isinstance(golden_dir, Path) else golden_dir
    if not gdir.exists():
        return miss
    try:
        index = _get_cached_index(str(gdir.resolve()))
        section, resolution = index.resolve_section(page_role, "standard", section_heading)
        if section is not None:
            return resolution
        # No section matched — check if role exists for role_fallback
        page = index.get(page_role, "standard")
        if page is not None:
            return GoldenResolution(
                match_level="role_fallback",
                matched_heading="",
                query_heading=section_heading,
                page_role=page_role,
                variant="standard",
                jaccard_score=0.0,
                golden_page_path=str(page.source_path),
                golden_word_count=page.total_word_count,
                has_structural_spec=False,
            )
        return resolution  # miss from resolve_section
    except Exception:
        return miss


def _extract_block_sequence(markdown: str) -> list[str]:
    """Extract ordered block type tokens from a markdown section."""
    from launcher.workers.evaluate.checks.golden_sequence import get_block_sequence
    return get_block_sequence(markdown)


def _parse_sections(body: str) -> list[GoldenSection]:
    """Split markdown body on ## headings and build GoldenSection list."""
    # Split on ## headings (level 2+)
    parts = re.split(r"\n(?=#{2,6}\s)", body.strip())
    sections = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        heading_match = re.match(r"^(#{2,6})\s+(.+)", part)
        if not heading_match:
            continue
        heading = heading_match.group(2).strip()
        raw = part
        excerpt = raw[:600]
        # Prose words (exclude code lines)
        no_code = _FENCE_RE.sub("", raw)
        no_code = re.sub(r"`[^`]+`", "", no_code)
        no_code = re.sub(r"^#{1,6}\s+.+$", "", no_code, flags=re.MULTILINE)
        no_code = re.sub(r"^\|.+$", "", no_code, flags=re.MULTILINE)
        words = [w for w in no_code.split() if w]
        word_count = len(words)
        has_code = bool(re.search(r"```", raw))
        has_list = bool(re.search(r"^\s*[-*]\s", raw, re.MULTILINE))
        has_table = bool(re.search(r"^\|", raw, re.MULTILINE))
        if word_count < 5:
            continue  # skip near-empty sections
        # TC-3881 Wave 3 (G1): Compute structural fingerprint counts.
        code_block_count = len(re.findall(r"```[^\n]*\n", raw))
        list_block_count = len(re.findall(r"^\s*[-*]\s", raw, re.MULTILINE))
        table_count = len(re.findall(r"^\|[-|]+\|", raw, re.MULTILINE))  # separator rows = 1 per table
        heading_count = len(re.findall(r"^#{2,6}\s", raw, re.MULTILINE))
        prose_chars = len(no_code.strip())
        code_chars = sum(len(m) for m in re.findall(r"```[^\n]*\n[\s\S]*?```", raw, re.DOTALL))
        code_to_prose_ratio = code_chars / max(prose_chars + code_chars, 1)
        sections.append(GoldenSection(
            heading=heading,
            raw_markdown=raw,
            word_count=word_count,
            has_code=has_code,
            has_list=has_list,
            has_table=has_table,
            excerpt=excerpt,
            code_block_count=code_block_count,
            list_block_count=list_block_count,
            table_count=table_count,
            heading_count=heading_count,
            code_to_prose_ratio=code_to_prose_ratio,
            block_sequence=_extract_block_sequence(raw),
        ))
    return sections
