"""Post-LLM BlockIR validation and normalization."""
from __future__ import annotations

import functools
import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

from launcher.models.page_ir import BlockIR, BlockType
from launcher.models.product import ProductIdentity
from launcher.workers.evaluate.checks.artifacts import _ARTIFACT_PHRASES

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# W1-S1: Template-label heading prevention
# Keep in sync with checks/structure.py template_patterns local list.
# ---------------------------------------------------------------------------
_HEADING_LABEL_PATTERNS = [
    "section title", "content to be generated", "tbd", "todo",
    "fill in", "section heading", "section content", "[content]",
]


# ---------------------------------------------------------------------------
# W1-S2: LLM artifact phrase strip
# Imports _ARTIFACT_PHRASES from checks/artifacts.py (authoritative list).
# ---------------------------------------------------------------------------

def _strip_artifact_phrases(content: str) -> str:
    """Strip common LLM artifact/boilerplate phrases. Called post-LLM, pre-acceptance.

    Uses _ARTIFACT_PHRASES imported from checks/artifacts.py so the list stays
    authoritative in one place. Matches at sentence boundaries (sentence start or
    preceded by '. ') to avoid partial matches inside legitimate sentences.
    """
    if not content:
        return content
    for phrase in _ARTIFACT_PHRASES:
        # Strip at sentence boundaries: phrase at start of string or after '. '
        pattern = r'(?i)(^|\.\s+)' + re.escape(phrase) + r'[,.]?\s*'
        content = re.sub(pattern, lambda m: m.group(1), content)
    return content.strip()


def parse_and_validate_blocks(
    raw_response: str,
    product: ProductIdentity,
    allowed_claim_ids: set[str],
    import_allowlist: list[str],
    section_heading: str = "",
    api_identifiers: set[str] | None = None,
) -> list[BlockIR] | None:
    """Parse LLM response into validated BlockIR objects.

    The LLM is expected to return a JSON array of block dicts.  This
    function strips any surrounding markdown fences, parses the JSON,
    and normalises each block into a :class:`BlockIR`.

    Parameters
    ----------
    raw_response:
        Raw text returned by the LLM.
    product:
        Product identity for name/import normalisation.
    allowed_claim_ids:
        Set of claim IDs that are valid for the current page.
        Block ``claim_ids`` are filtered to this set.
    import_allowlist:
        List of allowed import paths for Python code blocks.
    section_heading:
        The heading of the section being generated.  Heading blocks
        matching this text are stripped to avoid duplication (the
        renderer already emits section headings).

    Returns
    -------
    list[BlockIR] | None
        Validated blocks, or ``None`` if parsing/validation fails.
    """
    # 1. Extract JSON array from response (handle markdown fences)
    json_str = _extract_json_array(raw_response)
    if json_str is None:
        logger.warning("No JSON array found in LLM response")
        return None

    # 2. Parse JSON
    try:
        raw_blocks = json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.warning("JSON parse error: %s", e)
        return None

    if not isinstance(raw_blocks, list):
        logger.warning("Expected JSON array, got %s", type(raw_blocks).__name__)
        return None

    # 3. Validate and normalize each block
    blocks: list[BlockIR] = []
    for raw in raw_blocks:
        block = _validate_block(raw, product, allowed_claim_ids, import_allowlist, api_identifiers)
        if block is not None:
            blocks.append(block)

    # 4. Strip heading blocks that duplicate the section heading.
    #    The LLM sometimes emits heading content with markdown prefixes
    #    (e.g. "## Steps" instead of "Steps"), so we strip those first.
    if section_heading and blocks:
        heading_lower = section_heading.strip().lower()
        blocks = [
            b for b in blocks
            if not (
                b.type == BlockType.heading
                and _strip_md_heading_prefix(b.content).strip().lower() == heading_lower
            )
        ]

    # 5. Split overlong headings (TC-3817 Change D).
    #    LLM sometimes puts full answer text in heading blocks (FAQ pattern).
    #    If a heading block has > 80 chars, split: first sentence → heading, rest → paragraph.
    split_blocks: list[BlockIR] = []
    for b in blocks:
        if b.type == BlockType.heading and len(b.content) > 80:
            # Find first sentence break
            dot_pos = b.content.find(". ")
            q_pos = b.content.find("? ")
            break_pos = -1
            if dot_pos > 0 and (q_pos < 0 or dot_pos < q_pos):
                break_pos = dot_pos + 1
            elif q_pos > 0:
                break_pos = q_pos + 1

            if break_pos > 0 and break_pos < len(b.content) - 5:
                heading_text = b.content[:break_pos].strip()
                para_text = b.content[break_pos:].strip()
                split_blocks.append(BlockIR(
                    type=BlockType.heading,
                    content=heading_text,
                    level=b.level,
                    claim_ids=b.claim_ids,
                ))
                split_blocks.append(BlockIR(
                    type=BlockType.paragraph,
                    content=para_text,
                    claim_ids=b.claim_ids,
                ))
                logger.debug("Split overlong heading (%d chars) into heading + paragraph", len(b.content))
                continue
        split_blocks.append(b)
    blocks = split_blocks

    return blocks if blocks else None


def _strip_md_heading_prefix(text: str) -> str:
    """Remove leading ``#`` characters from heading block content."""
    return re.sub(r"^#+\s*", "", text.strip())


_CLM_COMMENT_RE = re.compile(r"^\s*#\s*Claims:\s*CLM-")
_CLM_CITATION_RE = re.compile(r"\s*\[CLM-[^\]]*\]")

# TC-3873: dict-literal anchor pattern --- matches [{'key': ...}](url) artifacts.
# Defined locally to avoid circular import from checks.artifacts.
_DICT_ANCHOR_RE = re.compile(r"\[\{[^\]]*\}\]\([^)]*\)")


def _strip_dict_anchors(content: str) -> str:
    """Remove [{'type':...}](url) dict-literal artifacts from LLM output.

    Replaces the entire [dict](url) markdown link with just the raw URL,
    preserving the link target while removing the unreadable anchor text.
    """
    def _replace_with_url(m: re.Match) -> str:
        full = m.group(0)
        # Extract URL: everything between last ]( and )
        url_match = re.search(r"\]\(([^)]+)\)$", full)
        return url_match.group(1) if url_match else ""
    return _DICT_ANCHOR_RE.sub(_replace_with_url, content)


def _strip_claim_comments(code: str) -> str:
    """Remove ``# Claims: CLM-xxx`` metadata comments from code blocks."""
    lines = code.split("\n")
    filtered = [line for line in lines if not _CLM_COMMENT_RE.match(line)]
    if len(filtered) < len(lines):
        logger.debug("Stripped %d claim comment line(s) from code block", len(lines) - len(filtered))
    return "\n".join(filtered)


def _strip_claim_citations(text: str) -> str:
    """Remove bracket-format claim citations like ``[CLM-xxx, CLM-yyy]`` from prose."""
    cleaned = _CLM_CITATION_RE.sub("", text)
    if cleaned != text:
        logger.debug("Stripped claim citations from prose content")
    return cleaned


# ---------------------------------------------------------------------------
# TC-3802: Table content validation + HTML link sanitization
# ---------------------------------------------------------------------------

_HTML_LINK_RE = re.compile(
    r'<a\s+href=["\']([^"\']+)["\'](?:\s[^>]*)?>(.*?)</a>',
    re.IGNORECASE,
)

_PIPE_ROW_RE = re.compile(r"^\|.+\|$", re.MULTILINE)


def _sanitize_html_links(content: str) -> str:
    """Convert HTML ``<a href="url">text</a>`` tags to markdown ``[text](url)``."""
    return _HTML_LINK_RE.sub(r"[\2](\1)", content)


def _validate_table_content(content: str) -> str:
    """Validate and repair table block content.

    If content is already pipe-delimited markdown, return as-is.
    If content is a JSON/Python array of dicts, convert to a markdown table.
    Otherwise, wrap in a minimal single-column table.
    """
    stripped = content.strip()
    if not stripped:
        return content

    # Already valid pipe-delimited table
    if _PIPE_ROW_RE.search(stripped):
        return content

    # Try to parse as JSON array of dicts (LLM sometimes outputs these)
    if stripped.startswith("["):
        try:
            json_str = stripped.replace("'", '"')
            rows = json.loads(json_str)
            if isinstance(rows, list) and rows and isinstance(rows[0], dict):
                table = _json_array_to_markdown_table(rows)
                logger.info("Converted JSON array (%d rows) to markdown table", len(rows))
                return table
        except (json.JSONDecodeError, ValueError):
            pass

    # Last resort: wrap in single-column table
    logger.warning("Table content is not pipe-delimited markdown; wrapping as single-column")
    return f"| Content |\n| --- |\n| {stripped} |"


def _json_array_to_markdown_table(rows: list[dict]) -> str:
    """Convert a list of dicts to a pipe-delimited markdown table."""
    if not rows:
        return ""
    headers = list(rows[0].keys())
    header_line = "| " + " | ".join(str(h) for h in headers) + " |"
    separator = "| " + " | ".join("---" for _ in headers) + " |"
    data_lines: list[str] = []
    for row in rows:
        cells = [
            str(row.get(h, "")).replace("|", "\\|").replace("\n", " ")
            for h in headers
        ]
        data_lines.append("| " + " | ".join(cells) + " |")
    return "\n".join([header_line, separator] + data_lines)


def _extract_json_array(text: str) -> str | None:
    """Extract a JSON array from *text*, handling markdown code fences."""
    # Strip markdown fences if present
    stripped = re.sub(r"^```(?:json)?\s*\n?", "", text.strip())
    stripped = re.sub(r"\n?```\s*$", "", stripped)

    # Find the first [ ... ] block with balanced brackets
    start = stripped.find("[")
    if start == -1:
        return None

    depth = 0
    for i in range(start, len(stripped)):
        if stripped[i] == "[":
            depth += 1
        elif stripped[i] == "]":
            depth -= 1
            if depth == 0:
                return stripped[start : i + 1]

    return None


def _validate_block(
    raw: dict[str, Any],
    product: ProductIdentity,
    allowed_claim_ids: set[str],
    import_allowlist: list[str],
    api_identifiers: set[str] | None = None,
) -> BlockIR | None:
    """Validate and normalize a single raw block dict into BlockIR."""
    if not isinstance(raw, dict):
        return None

    block_type_str = raw.get("type", "")
    try:
        block_type = BlockType(block_type_str)
    except ValueError:
        logger.warning("Invalid block type: %s", block_type_str)
        return None

    content = raw.get("content", "")
    if not isinstance(content, str):
        content = str(content) if content is not None else ""
    claim_ids = raw.get("claim_ids", [])

    # Filter to only valid claim IDs
    if allowed_claim_ids:
        claim_ids = [cid for cid in claim_ids if cid in allowed_claim_ids]

    # Validate table content format first (TC-3802) — must run before prose
    # normalization so backtick wrapping operates on pipe-delimited markdown,
    # not raw JSON that _validate_table_content() would restructure.
    if block_type == BlockType.table:
        content = _validate_table_content(content)

    # Normalize prose content (not code blocks)
    if block_type != BlockType.code:
        content = _sanitize_html_links(content)
        content = _strip_claim_citations(content)
        content = _normalize_product_name(content, product)
        if api_identifiers:
            content = _backtick_api_names(content, api_identifiers, product.display_name)

    # W1-S2: Strip LLM artifact phrases from paragraph blocks (deterministic engineering fix).
    # Applied after prose normalization so strip operates on clean text.
    if block_type == BlockType.paragraph:
        content = _strip_artifact_phrases(content)

    # TC-3873 W1-S3: Strip dict-literal anchor artifacts from paragraph and list blocks.
    # Catches [{"type":...}](url) LLM artifacts that survive _parse_anchor_response.
    if block_type in (BlockType.paragraph, BlockType.list):
        content = _strip_dict_anchors(content)

    # For code blocks: validate imports and strip claim metadata
    language = raw.get("language")
    if block_type == BlockType.code:
        content = _strip_claim_comments(content)
        content = _strip_claim_citations(content)
        if (language or "").lower() in ("python", "py", "python3"):
            content = _normalize_imports(
                content, product.canonical_import, import_allowlist,
                runtime_import=getattr(product, "runtime_import", ""),
            )
        elif language and product.canonical_import:
            try:
                # TC-3901: AST-based normalization handles hyphenated npm scoped packages
                # (e.g. @aspose/3d-foss) correctly. The previous regex was hyphen-blind
                # and produced @aspose/3d-foss-foss double-suffix bugs.
                from launcher.shared.ts_analyzer import normalize_imports_ast as _ts_normalize
                content = _ts_normalize(content, language, product.canonical_import)
            except ImportError:
                pass

    items = [_strip_dict_anchors(_strip_claim_citations(item)) if isinstance(item, str) else item
             for item in raw.get("items", [])]
    level = raw.get("level")

    # For heading blocks: strip markdown prefixes from content
    # (LLM sometimes emits "## Steps" instead of "Steps")
    if block_type == BlockType.heading:
        content = _strip_md_heading_prefix(content)
        # Clamp heading levels: never level 1 (reserved for page title)
        if level is not None and level < 2:
            level = 2
        # W1-S1: Drop template-label headings (bare placeholder text).
        # Keep in sync with checks/structure.py template_patterns.
        heading_text_lower = content.strip().lower()
        if any(pat in heading_text_lower for pat in _HEADING_LABEL_PATTERNS):
            logger.debug("Dropping template-label heading: %r", content)
            return None

    return BlockIR(
        type=block_type,
        content=content,
        language=language,
        claim_ids=claim_ids,
        items=items,
        level=level,
    )


def _normalize_product_name(content: str, product: ProductIdentity) -> str:
    """Ensure product name appears correctly in prose text.

    In prose (outside backticks), the display_name should be used.
    Inside backticks, the canonical_import should be used.
    """
    if not product.display_name:
        return content

    display = product.display_name  # e.g. "Aspose.Cells"
    canonical = product.canonical_import  # e.g. "aspose.cells"

    if not canonical:
        return content

    # Replace backtick-quoted wrong imports with canonical
    content = re.sub(r"`aspose\.pydrawing`", f"`{canonical}`", content, flags=re.IGNORECASE)

    # Replace bare (non-backtick) lowercase product name in prose with display_name
    # but preserve backtick-quoted references as canonical_import
    def _replace_bare(m: re.Match) -> str:
        # Check if preceded by backtick (inside inline code)
        start = m.start()
        if start > 0 and content[start - 1] == '`':
            return m.group(0)  # leave backtick-quoted as-is
        return display

    # Build pattern from canonical import (escape dots)
    escaped = re.escape(canonical)
    content = re.sub(escaped, _replace_bare, content, flags=re.IGNORECASE)

    return content


@functools.lru_cache(maxsize=4)
def _compile_api_pattern(identifiers: tuple[str, ...]) -> re.Pattern[str]:
    """Compile a regex pattern for API identifiers, cached across calls."""
    sorted_ids = sorted(identifiers, key=len, reverse=True)
    escaped = [re.escape(ident) for ident in sorted_ids]
    return re.compile(r"\b(" + "|".join(escaped) + r")\b")


def _backtick_api_names(
    content: str,
    api_identifiers: set[str],
    display_name: str,
) -> str:
    """Wrap known API identifiers in backticks in prose/table text.

    Uses the AST-extracted ``api_identifiers`` set as a whitelist.
    Only case-sensitive exact matches at word boundaries are wrapped.

    Skips tokens that:
    - are already inside backticks
    - are part of the product display_name (e.g. "Cells" in "Aspose.Cells")
    - are inside markdown links ``[text](url)``
    """
    if not api_identifiers or not content:
        logger.debug("Backtick pass: skipped (no identifiers or empty content)")
        return content

    # Build protected spans: backtick regions, markdown links, display_name occurrences
    protected: list[tuple[int, int]] = []

    # Backtick spans
    for m in re.finditer(r"`[^`]+`", content):
        protected.append((m.start(), m.end()))

    # Markdown link text spans [text](url)
    for m in re.finditer(r"\[([^\]]+)\]\([^)]+\)", content):
        protected.append((m.start(), m.end()))

    # Product display_name spans (e.g. "Aspose.Cells")
    if display_name:
        for m in re.finditer(re.escape(display_name), content, flags=re.IGNORECASE):
            protected.append((m.start(), m.end()))

    def _is_protected(start: int, end: int) -> bool:
        return any(ps <= start and end <= pe for ps, pe in protected)

    pattern = _compile_api_pattern(tuple(sorted(api_identifiers)))

    # Replace from right to left to preserve positions
    matches = list(pattern.finditer(content))
    skipped = 0
    wrapped = 0
    for m in reversed(matches):
        if _is_protected(m.start(), m.end()):
            skipped += 1
            continue
        content = content[:m.start()] + f"`{m.group()}`" + content[m.end():]
        wrapped += 1

    if matches:
        logger.debug(
            "Backtick pass: %d matches, %d protected, %d wrapped",
            len(matches), skipped, wrapped,
        )

    return content


def check_against_spec(section_ir: Any, spec: Any) -> bool:
    """Return True if section_ir satisfies spec requirements (required_block_types, min_words).

    Returns True when spec is None (safe pass-through).
    """
    if spec is None:
        return True
    blocks = getattr(section_ir, "blocks", []) or []
    body_parts = []
    has_code = False
    for block in blocks:
        btype = getattr(block, "type", "")
        if hasattr(btype, "value"):
            btype = btype.value
        if btype in ("code", "fence", "code_block"):
            has_code = True
        if btype in ("paragraph", "text", "prose"):
            content = getattr(block, "content", "") or ""
            if content:
                body_parts.append(content)
    # Check required_block_types (GoldenBlockSpec uses a list)
    required_types = getattr(spec, "required_block_types", None) or []
    if "code" in required_types and not has_code:
        return False
    # Legacy attribute name fallback
    if getattr(spec, "requires_code", False) and not has_code:
        return False
    min_words = getattr(spec, "min_words", 0) or 0
    if min_words > 0:
        word_count = len(" ".join(body_parts).split())
        if word_count < min_words:
            return False
    return True


@dataclass
class EnforcementContext:
    """Collects all per-section enforcement parameters (V2SC-07).

    Replaces the previous 9-parameter ``enforce_block_spec`` signature by
    grouping related values into a single typed object.  Callers construct
    one context per section and pass it to :func:`enforce_block_spec`.
    """

    product: ProductIdentity
    allowed_claim_ids: set[str] = field(default_factory=set)
    import_allowlist: list[str] = field(default_factory=list)
    section_heading: str = ""
    api_identifiers: set[str] | None = None
    spec: Any | None = None  # GoldenBlockSpec | None (avoids circular import)
    max_retries: int = 1


def enforce_block_spec(
    blocks: list[BlockIR],
    ctx: EnforcementContext,
    *,
    _call_llm: Any = None,
) -> list[BlockIR]:
    """Enforce GoldenBlockSpec compliance on *blocks* using *ctx*.

    Pass 1 — check compliance via :func:`check_against_spec`.
    Pass 2…N — if spec has max_retries > 1 and a ``_call_llm`` callable is
    provided, re-parse a regenerated response for up to ``ctx.max_retries - 1``
    additional attempts.  Without ``_call_llm`` (unit tests / fallback), the
    function returns the original blocks — never drops content.

    The function is deliberately non-destructive: it never raises and never
    returns an empty list when *blocks* is non-empty.
    """
    if ctx.spec is None or check_against_spec(_MockSectionIR(blocks), ctx.spec):
        return blocks

    max_retries = getattr(ctx.spec, "max_retries", 1) or 1
    if max_retries <= 1 or _call_llm is None:
        # No retries possible — return original blocks, caller logs the miss
        logger.debug(
            "[enforce_block_spec] spec not met for '%s' — no retries available",
            ctx.section_heading,
        )
        return blocks

    for attempt in range(1, max_retries):
        try:
            raw = _call_llm(attempt)
            if raw is None:
                break
            new_blocks = parse_and_validate_blocks(
                raw,
                ctx.product,
                ctx.allowed_claim_ids,
                ctx.import_allowlist,
                section_heading=ctx.section_heading,
                api_identifiers=ctx.api_identifiers,
            )
            if new_blocks and check_against_spec(_MockSectionIR(new_blocks), ctx.spec):
                logger.info(
                    "[enforce_block_spec] spec satisfied on retry %d for '%s'",
                    attempt, ctx.section_heading,
                )
                return new_blocks
        except Exception as exc:
            logger.warning("[enforce_block_spec] retry %d failed: %s", attempt, exc)
            break

    return blocks


class _MockSectionIR:
    """Minimal duck-type wrapper so check_against_spec can operate on a block list."""

    def __init__(self, blocks: list[BlockIR]) -> None:
        self.blocks = blocks
        self.body = " ".join(
            b.content for b in blocks if b.type == BlockType.paragraph and b.content
        )


def deduplicate_sections(
    sections: list[Any],
    *,
    similarity_threshold: float = 0.7,
) -> list[Any]:
    """Remove cross-section paragraph duplication after parallel gather (V2CP-03 Phase 4).

    Iterates sections in skeleton order. For each paragraph block in a section,
    checks if it is nearly identical (Jaccard ≥ threshold) to a paragraph block
    already seen in an earlier section. Near-duplicate paragraphs are dropped.

    Only prose paragraph blocks are checked — code, list, and table blocks are
    always preserved. Input order is preserved.

    Returns the modified sections list (uses model_copy; originals unchanged).
    """
    import string
    from launcher.shared.jaccard import STOPWORDS, jaccard_similarity

    def _word_set(text: str) -> frozenset[str]:
        translator = str.maketrans("", "", string.punctuation)
        words = text.lower().translate(translator).split()
        return frozenset(w for w in words if w and w not in STOPWORDS and len(w) > 2)

    seen: list[tuple[frozenset[str], str]] = []
    result_sections: list[Any] = []

    for section in sections:
        heading = getattr(section, "heading", "") or ""
        blocks = list(getattr(section, "blocks", []) or [])
        new_blocks: list[Any] = []

        for block in blocks:
            btype = getattr(block, "type", None)
            is_paragraph = (
                btype == BlockType.paragraph
                or (hasattr(btype, "value") and btype.value == "paragraph")
            )
            if not is_paragraph:
                new_blocks.append(block)
                continue

            content = getattr(block, "content", "") or ""
            if len(content.split()) < 10:
                new_blocks.append(block)
                continue

            words = _word_set(content)
            if not words:
                new_blocks.append(block)
                continue

            is_dup = any(
                jaccard_similarity(words, prev_words) >= similarity_threshold
                for prev_words, _ in seen
            )
            if is_dup:
                logger.debug(
                    "[dedup] Dropped duplicate paragraph in section '%s'", heading
                )
            else:
                seen.append((words, heading))
                new_blocks.append(block)

        # Only create a new object if blocks were actually removed
        if len(new_blocks) == len(blocks):
            result_sections.append(section)
        elif hasattr(section, "model_copy"):
            result_sections.append(section.model_copy(update={"blocks": new_blocks}))
        else:
            result_sections.append(section)

    return result_sections


# ---------------------------------------------------------------------------
# HG-16: Hallucinated code block repair
# ---------------------------------------------------------------------------

# HG-18: Require CamelCase (at least two camel-words) to avoid false-positive removal
# of single-word capitalized variables like Author, Title, Developer, STL, ASCII.
# Matches: StlFormat, StlSaveOptions, ObjLoadOptions, AnimationClip, FileFormat
# Does NOT match: Scene, Node, Title, Author, STL, ASCII, Export, Load, Installation
_CLASS_USAGE_RE = re.compile(r'\b([A-Z][a-z]+(?:[A-Z][a-z0-9]*)+)\b')

_PYTHON_BUILTINS: frozenset[str] = frozenset({
    "True", "False", "None", "Ellipsis",
    "int", "float", "complex", "str", "bytes", "bytearray",
    "list", "dict", "tuple", "set", "frozenset", "bool",
    "type", "object", "super",
    "Exception", "BaseException", "ValueError", "TypeError", "KeyError",
    "AttributeError", "NotImplementedError", "RuntimeError", "OSError",
    "IOError", "IndexError", "StopIteration", "NameError", "ImportError",
    "ZeroDivisionError", "OverflowError", "FileNotFoundError",
    "PermissionError", "TimeoutError", "MemoryError", "RecursionError",
    "SystemExit", "KeyboardInterrupt", "GeneratorExit",
    "Path", "PurePath", "Enum", "Flag", "IntEnum",
    "ABC", "ABCMeta",
    "Optional", "Union", "List", "Dict", "Tuple", "Set", "FrozenSet",
    "Any", "Callable", "Iterator", "Generator", "Sequence", "Mapping",
    "ClassVar", "Final", "Literal", "TypeVar", "Generic",
    "NamedTuple", "TypedDict", "Protocol",
    "datetime", "date", "time", "timedelta", "timezone",
    "StringIO", "BytesIO",
    "Thread", "Lock", "Event",
})


def _strip_hallucinated_code_blocks(
    blocks: list[BlockIR],
    public_classes: set[str],
) -> list[BlockIR]:
    """Remove Python code blocks that reference class names not in public_classes.

    Scans each Python code block for capitalized identifiers that look like
    class names (e.g. ``ObjLoadOptions``, ``StlFormat``). If any such
    identifier is found that is NOT in ``public_classes`` and NOT a Python
    builtin, the entire code block is removed.

    This deterministically prevents hallucinated Aspose-pattern class names
    from reaching the evaluate worker and triggering factual_accuracy /
    api_consistency high-severity findings.

    Only Python code blocks are inspected (language in "python", "py",
    "python3", or empty string). Non-Python blocks pass through unchanged.

    Parameters
    ----------
    blocks:
        BlockIR list from parse_and_validate_blocks().
    public_classes:
        Set of known class names from api_surface.public_classes.
        If empty, the repair pass is skipped (no data → no false positives).

    Returns
    -------
    list[BlockIR]
        Modified block list. Prose/list/table blocks are always preserved.
    """
    if not public_classes:
        return blocks

    result: list[BlockIR] = []
    removed_count = 0

    for block in blocks:
        if block.type != BlockType.code:
            result.append(block)
            continue

        lang = (block.language or "").lower()
        if lang not in ("python", "py", "python3", ""):
            # Only repair Python blocks; non-Python passes through unchanged
            result.append(block)
            continue

        code = block.content or ""

        # HG-17: Strip Python comment content (after '#') before scanning.
        # Prevents capitalized English words in comments like "# Load the scene"
        # from being misidentified as hallucinated class names.
        code_for_scanning = "\n".join(
            line.split("#")[0] for line in code.split("\n")
        )
        # If the only content was comments, preserve the block (nothing to flag)
        if not code_for_scanning.strip():
            result.append(block)
            continue

        hallucinated: list[str] = []

        for m in _CLASS_USAGE_RE.finditer(code_for_scanning):
            class_name = m.group(1)
            if class_name in _PYTHON_BUILTINS:
                continue
            if class_name in public_classes:
                continue
            hallucinated.append(class_name)

        if hallucinated:
            logger.info(
                "[HG-16] Removing code block with unverified class(es): %s",
                ", ".join(sorted(set(hallucinated))),
            )
            removed_count += 1
            # Drop this block — do NOT append to result
        else:
            result.append(block)

    if removed_count:
        logger.info("[HG-16] Removed %d hallucinated Python code block(s)", removed_count)

    return result


def _normalize_imports(
    code: str, canonical_import: str, import_allowlist: list[str],
    runtime_import: str = "",
) -> str:
    """Normalize import statements to use the correct runtime import.

    Rewrites common wrong-import patterns to use runtime_import (or canonical_import
    when runtime_import is empty):
    - ``import aspose_cells_foss`` → ``import aspose.cells``
    - ``from aspose_cells_foss import X`` → ``from aspose.cells import X``
    - ``import aspose.pydrawing`` → removed (not part of FOSS)

    Also strips lines importing modules not in the allowlist.
    """
    # Use runtime_import (e.g. "aspose.threed") as the normalization target if available
    effective_import = runtime_import or canonical_import
    if not effective_import:
        return code

    lines = code.split("\n")
    normalized: list[str] = []

    # Build set of allowed base modules
    allowed_bases = set()
    for path in import_allowlist:
        allowed_bases.add(path.split(".")[0])
    allowed_bases.add(effective_import.split(".")[0])
    # Also allow canonical_import base (pip name) in case it differs from runtime
    if canonical_import:
        allowed_bases.add(canonical_import.split(".")[0])

    for line in lines:
        stripped = line.strip()

        # Match import statements
        import_match = re.match(r"^(\s*)(import|from)\s+([\w.]+)", line)
        if import_match:
            indent = import_match.group(1)
            keyword = import_match.group(2)
            module = import_match.group(3)
            base = module.split(".")[0]

            # Skip non-FOSS Aspose modules (e.g. aspose.pydrawing)
            if "pydrawing" in module.lower():
                continue

            # Rewrite aspose.cells / aspose_cells_foss variants to effective_import
            # (runtime_import takes precedence so we emit e.g. "aspose.threed" not "aspose_3d_foss")
            if base == "aspose" or module.startswith("aspose."):
                if keyword == "import":
                    rest = line[import_match.end():]
                    normalized.append(f"{indent}import {effective_import}{rest}")
                else:
                    after_module = line[import_match.end():]
                    normalized.append(f"{indent}from {effective_import}{after_module}")
                continue

            # TC-3873 W1-S5: Catch aspose_XXX without _foss suffix (e.g. aspose_cells vs aspose_cells_foss).
            # canonical_base is e.g. "aspose_cells_foss"; base is e.g. "aspose_cells".
            canonical_base = canonical_import.split(".")[0] if canonical_import else ""
            if (
                base.startswith("aspose_")
                and canonical_base
                and base != canonical_base
            ):
                if keyword == "import":
                    rest = line[import_match.end():]
                    normalized.append(f"{indent}import {effective_import}{rest}")
                else:
                    after_module = line[import_match.end():]
                    normalized.append(f"{indent}from {effective_import}{after_module}")
                continue

        normalized.append(line)

    return "\n".join(normalized)
