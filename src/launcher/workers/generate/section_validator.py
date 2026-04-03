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
# TC-GEN-603: Backtick-wrapping exempt words
# Lowercase common English words that happen to match lowercase API method names.
# These are NOT wrapped in backticks even when they appear in the API surface,
# because wrapping them produces awkward prose ("you can `get` the value").
# NOTE: PascalCase class names must NOT be added here — they ARE legitimate API
# classes and must remain wrapped when they appear as API identifiers in prose.
# ---------------------------------------------------------------------------
_BACKTICK_EXEMPT_WORDS: frozenset[str] = frozenset({
    # Very short lowercase words that would produce awkward backtick prose
    # if they happen to match a same-named API method or constant.
    "get", "set", "add", "del", "run", "key", "map", "use",
    "new", "old", "raw", "all", "any", "max", "min",
})


# ---------------------------------------------------------------------------
# TC-5329: Wrong-ecosystem pattern detection for C++ code blocks.
# The qwen3-next LLM defaults to .NET/C++CLI Aspose patterns when writing C++ code.
# These patterns are syntactically valid enough to pass basic checks but are semantically
# wrong for a standard C++ library. Detect them post-LLM to drive retry or block drop.
# ---------------------------------------------------------------------------
_CPP_FENCE_LANGS: frozenset[str] = frozenset({"cpp", "c++", "c"})
_CPP_CONTAMINATION_MARKER = "# __CPP_CONTAMINATION__:"

_CPP_CONTAMINATION_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bSystem\s*::\s*MakeObject\s*<"),   "System::MakeObject"),
    (re.compile(r"\bSystem\s*::\s*DynamicCast\s*<"),  "System::DynamicCast"),
    (re.compile(r"\bSystem\s*::\s*SafeCast\s*<"),     "System::SafeCast"),
    (re.compile(r"\bSystem\s*::\s*Drawing\s*::"),     "System::Drawing"),
    (re.compile(r"\bSystem\s*::\s*Exception\b"),      "System::Exception"),
    (re.compile(r"\bgcnew\b"),                        "gcnew"),
    # ^ managed-pointer: letter/paren immediately before ^ (XOR has spaces: a ^ b)
    (re.compile(r"[A-Za-z_)]\^"),                     "managed-pointer(^)"),
    # IInterface instantiation: e.g. IPresentation p("file") or ISlide s =
    (re.compile(r"\bI[A-Z][A-Za-z]{3,}\s+\w+\s*[=(;]"), "IInterface-instantiation"),
    # .get_X() .NET property accessor: e.g. ->get_Message() ->get_Slides()
    (re.compile(r"->\s*get_[A-Z][A-Za-z]+\s*\(\)"),  "get_X()-accessor"),
]


def scan_cpp_contamination(code: str) -> list[str]:
    """Return list of wrong-ecosystem pattern labels found in a C++ code block.

    TC-5329: Detects .NET/C++CLI idioms that are invalid in standard C++ FOSS code.
    Returns an empty list if the code is clean.
    """
    labels: list[str] = []
    for pattern, label in _CPP_CONTAMINATION_PATTERNS:
        if pattern.search(code):
            labels.append(label)
    return labels


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


def _strip_skeleton_directives(content: str, display_name: str) -> str:
    """Strip skeleton-directive sentences from paragraph content (TC-GEN-602).

    The LLM sometimes echoes section guidance verbatim:
      "Aspose.Cells for Python via .NET -- Provide an overview of..."
    These are internal scaffolding notes, never real content.
    Strip the entire sentence (to end of line or period) when this pattern appears.
    """
    if not content or not display_name:
        return content
    # Match: display_name -- <rest of sentence/line>
    pattern = re.escape(display_name) + r'\s*--\s*[^\n.]+'
    content = re.sub(pattern, "", content).strip()
    return content


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


# SRP-03 (2026-03-24): Also strip "# source: snippet_N" metadata comments.
_CLM_COMMENT_RE = re.compile(r"^\s*#\s*(?:Claims:\s*CLM-|source:\s*snippet_)")
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

    # Try to parse as JSON array of dicts or list-of-lists (LLM sometimes outputs these)
    if stripped.startswith("["):
        try:
            json_str = stripped.replace("'", '"')
            rows = json.loads(json_str)
            if isinstance(rows, list) and rows:
                if isinstance(rows[0], dict):
                    table = _json_array_to_markdown_table(rows)
                    logger.info("Converted JSON array (%d rows) to markdown table", len(rows))
                    return table
                # SRP-03 (2026-03-24): list-of-lists → first row = headers, rest = data
                if isinstance(rows[0], list) and len(rows) >= 2:
                    headers = [str(h) for h in rows[0]]
                    header_line = "| " + " | ".join(headers) + " |"
                    separator = "| " + " | ".join("---" for _ in headers) + " |"
                    data_lines = []
                    for row in rows[1:]:
                        cells = [str(c).replace("|", "\\|") for c in row]
                        # Pad or truncate to match header count
                        while len(cells) < len(headers):
                            cells.append("")
                        cells = cells[:len(headers)]
                        data_lines.append("| " + " | ".join(cells) + " |")
                    logger.info("Converted list-of-lists (%d rows) to markdown table", len(rows) - 1)
                    return "\n".join([header_line, separator] + data_lines)
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
    """Validate and normalize a single raw block dict into BlockIR.

    TC-4228: When the LLM omits the ``type`` field, attempt to infer it
    from block content before rejecting the block:
    - If the raw dict has a ``language`` key → infer ``type="code"``
    - If content starts with triple-backtick → infer ``type="code"``
    - Otherwise → infer ``type="paragraph"``
    Only applied when ``type`` is absent or empty; an explicitly invalid
    type value still triggers the normal rejection path.
    """
    if not isinstance(raw, dict):
        return None

    block_type_str = raw.get("type", "")

    # TC-4228: Coerce missing type field before validation.
    # The LLM frequently omits "type" causing L1_VALIDATOR_FAIL.
    if not block_type_str:
        content_preview = str(raw.get("content", "")).strip()
        if "language" in raw:
            block_type_str = "code"
            logger.debug(
                "TC-4228: inferred type='code' from 'language' key (content preview: %.40r)",
                content_preview,
            )
        elif content_preview.startswith("```"):
            block_type_str = "code"
            logger.debug(
                "TC-4228: inferred type='code' from triple-backtick content (preview: %.40r)",
                content_preview,
            )
        else:
            block_type_str = "paragraph"
            logger.debug(
                "TC-4228: inferred type='paragraph' for typeless block (content preview: %.40r)",
                content_preview,
            )

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
        # TC-GEN-602: Strip skeleton-directive sentences (e.g. "Aspose.Cells -- Provide an overview").
        content = _strip_skeleton_directives(content, product.display_name)
        # Drop the block entirely if stripping emptied it.
        if not content.strip():
            logger.debug("Dropping empty paragraph block after skeleton-directive strip")
            return None

    # TC-3873 W1-S3: Strip dict-literal anchor artifacts from paragraph and list blocks.
    # Catches [{"type":...}](url) LLM artifacts that survive _parse_anchor_response.
    if block_type in (BlockType.paragraph, BlockType.list):
        content = _strip_dict_anchors(content)

    # For code blocks: validate imports and strip claim metadata
    language = raw.get("language")
    if block_type == BlockType.code:
        content = _strip_claim_comments(content)
        content = _strip_claim_citations(content)
        if (language or "").lower() in ("python", "py", "python3") and (
            getattr(product, "platform", "python") or "python"
        ).lower() == "python":
            # TC-5314: Only apply Python import normalization when the product IS Python.
            # A non-Python product with a mistakenly python-tagged block must not have
            # its C#/C++/Java code rewritten as Python imports.
            content = _normalize_imports(
                content, product.canonical_import, import_allowlist,
                runtime_import=getattr(product, "runtime_import", ""),
            )
        elif (language or "").lower() in ("csharp", "cs", "c#"):
            # TC-NET-002: C#-specific using-statement normalization.
            # Rewrites wrong Aspose sub-namespaces (e.g. Aspose.Slides.Foss)
            # to canonical_import before passing to the TS/generic normalizer.
            if product.canonical_import:
                content = _normalize_csharp_imports(
                    content, product.canonical_import, import_allowlist
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

        # TC-5329: Annotate C++ code blocks that contain wrong-ecosystem (.NET/C++CLI) patterns.
        # The annotation is a comment prepended to the code content; worker.py reads it to
        # decide whether to retry or drop the block. The marker is also in FORBIDDEN_PATTERNS
        # as a backstop so it can never reach published output.
        if (language or "").lower() in _CPP_FENCE_LANGS:
            _contamination_labels = scan_cpp_contamination(content)
            if _contamination_labels:
                _annotation = (
                    _CPP_CONTAMINATION_MARKER
                    + " " + ", ".join(_contamination_labels)
                )
                content = _annotation + "\n" + content

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

    # TC-GEN-603: Exclude common English words that share names with API identifiers.
    effective_ids = api_identifiers - _BACKTICK_EXEMPT_WORDS
    if not effective_ids:
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

    pattern = _compile_api_pattern(tuple(sorted(effective_ids)))

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
    """Remove cross-section paragraph and code block duplication (V2CP-03 Phase 4).

    Iterates sections in skeleton order.
    - Prose paragraph blocks: deduplicated by Jaccard similarity (>= threshold).
    - Code blocks: deduplicated by exact content hash (TC-GEN-605). Short code
      blocks (< 5 lines) are exempt from dedup to preserve legitimate one-liners.

    Input order is preserved. Returns modified sections (uses model_copy).
    """
    import hashlib
    import string
    from launcher.shared.jaccard import STOPWORDS, jaccard_similarity

    def _word_set(text: str) -> frozenset[str]:
        translator = str.maketrans("", "", string.punctuation)
        words = text.lower().translate(translator).split()
        return frozenset(w for w in words if w and w not in STOPWORDS and len(w) > 2)

    seen: list[tuple[frozenset[str], str]] = []
    seen_code_hashes: set[str] = set()
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
            is_code = (
                btype == BlockType.code
                or (hasattr(btype, "value") and btype.value == "code")
            )

            if is_code:
                # TC-GEN-605: Exact-match dedup for code blocks (skip short snippets).
                content = getattr(block, "content", "") or ""
                if len(content.strip().splitlines()) < 5:
                    new_blocks.append(block)
                    continue
                code_hash = hashlib.sha1(
                    content.strip().encode("utf-8", errors="replace")
                ).hexdigest()
                if code_hash in seen_code_hashes:
                    logger.debug("[dedup] Dropped duplicate code block in section '%s'", heading)
                else:
                    seen_code_hashes.add(code_hash)
                    new_blocks.append(block)
                continue

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
# HG-20: Also match PascalCase+digit names (Vector3, Matrix4, Quaternion4) that the
# LLM hallucinates from training data when they are not in the actual public API.
# Pattern: [A-Z][a-z]+\d+ — e.g. Vector3, Matrix4, Buffer2
# Does NOT match: V3 (no lowercase after uppercase), STL3 (no lowercase run)
_CLASS_USAGE_RE = re.compile(r'\b([A-Z][a-z]+(?:[A-Z][a-z0-9]*)+|[A-Z][a-z]+\d+)\b')

# SRP-01 (2026-03-24): Shared source in launcher.shared.python_names.
from launcher.shared.python_names import STDLIB_PYTHON_NAMES

_PYTHON_BUILTINS: frozenset[str] = STDLIB_PYTHON_NAMES


def _strip_hallucinated_code_blocks(
    blocks: list[BlockIR],
    public_classes: set[str],
) -> tuple[list[BlockIR], list[dict]]:
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

    GEN-4 (TC-5203): Returns a tuple of (kept_blocks, stripped_metadata) so
    the caller can attempt snippet-pool replacement for stripped blocks.

    Parameters
    ----------
    blocks:
        BlockIR list from parse_and_validate_blocks().
    public_classes:
        Set of known class names from api_surface.public_classes.
        If empty, the repair pass is skipped (no data → no false positives).

    Returns
    -------
    tuple[list[BlockIR], list[dict]]
        (kept_blocks, stripped_metadata) where kept_blocks is the filtered
        block list and stripped_metadata is a list of dicts with keys
        ``content``, ``claim_ids``, and ``language`` for each removed block.
        Prose/list/table blocks are always preserved.
    """
    if not public_classes:
        return blocks, []

    result: list[BlockIR] = []
    stripped_meta: list[dict] = []
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
            # GEN-4: Record metadata so caller can attempt snippet replacement.
            stripped_meta.append({
                "content": block.content or "",
                "claim_ids": list(block.claim_ids or []),
                "language": block.language or "",
            })
            # Drop this block — do NOT append to result
        else:
            result.append(block)

    if removed_count:
        logger.info("[HG-16] Removed %d hallucinated Python code block(s)", removed_count)

    return result, stripped_meta


# ---------------------------------------------------------------------------
# HG-21: Enum member access validation + method name correction
# ---------------------------------------------------------------------------

# Detects ClassName.ALL_CAPS_MEMBER patterns (e.g. FileFormat.STLASCII)
_ENUM_ACCESS_RE = re.compile(r'\b([A-Z][A-Za-z0-9]+)\.([A-Z][A-Z0-9_]{2,})\b')


def _strip_hallucinated_enum_member_access(
    blocks: list[BlockIR],
    class_enum_members: dict[str, set[str]],
) -> list[BlockIR]:
    """Remove Python code blocks that access invalid ALL-CAPS enum members on known classes.

    HG-21: Detects patterns like FileFormat.STLASCII or FileFormat.OBJ where FileFormat
    is a known API class but STLASCII / OBJ are not in its documented members. Such blocks
    are removed because they will cause factual_accuracy/api_consistency review failures.

    Parameters
    ----------
    blocks:
        BlockIR list from post-generate parsing.
    class_enum_members:
        dict mapping class name → set of valid ALL-CAPS member names.
        Built from class_briefs.typed_methods where name.upper() == name.
        If empty, the repair pass is skipped.
    """
    if not class_enum_members:
        return blocks

    result: list[BlockIR] = []
    for block in blocks:
        if block.type != BlockType.code or (block.language or "").lower() != "python":
            result.append(block)
            continue

        code = block.content or ""
        # Strip comment content before scanning (HG-17)
        code_for_scanning = "\n".join(line.split("#")[0] for line in code.split("\n"))
        if not code_for_scanning.strip():
            result.append(block)
            continue

        hallucinated: list[str] = []
        for m in _ENUM_ACCESS_RE.finditer(code_for_scanning):
            class_name = m.group(1)
            member_name = m.group(2)
            if class_name not in class_enum_members:
                continue  # Unknown class → no opinion
            if member_name in class_enum_members[class_name]:
                continue  # Valid member → keep
            hallucinated.append(f"{class_name}.{member_name}")

        if hallucinated:
            logger.debug(
                "[HG-21] Removing code block with invalid enum member(s): %s", hallucinated,
            )
        else:
            result.append(block)

    return result


def _correct_method_names_in_code(
    blocks: list[BlockIR],
    corrections: dict[str, str],
) -> list[BlockIR]:
    """Replace known-wrong method names in Python code blocks.

    HG-21: LLM hallucinates method names that are similar to real API methods
    (e.g., create_child_node instead of add_child_node). This function applies
    data-driven corrections derived from typed_methods suffix matching.

    Parameters
    ----------
    blocks:
        BlockIR list.
    corrections:
        dict mapping wrong_name → right_name.
        Computed in worker.py from api_identifiers vs typed_methods comparison.
        If empty, skipped.
    """
    if not corrections:
        return blocks

    result: list[BlockIR] = []
    for block in blocks:
        if block.type != BlockType.code or (block.language or "").lower() != "python":
            result.append(block)
            continue

        code = block.content or ""
        corrected = code
        applied: list[str] = []
        for wrong, right in corrections.items():
            pattern = re.compile(r'\b' + re.escape(wrong) + r'\b')
            if pattern.search(corrected):
                corrected = pattern.sub(right, corrected)
                applied.append(f"{wrong}→{right}")

        if applied:
            logger.debug("[HG-21] Corrected method names in code block: %s", applied)
            result.append(block.model_copy(update={"content": corrected}))
        else:
            result.append(block)

    return result


# ---------------------------------------------------------------------------
# HG-22: Post-generate method verification against class_briefs
# ---------------------------------------------------------------------------

# Regex patterns copied from evaluate/checks/api_verification.py to avoid
# cross-layer import coupling.  Keep in sync if the evaluate patterns change.
_HG22_ASSIGNMENT_RE = re.compile(
    r'\b([a-z_][a-zA-Z0-9_]*)\s*(?::\s*\w+\s*)?=\s*(?:\w+\.)*([A-Z][a-zA-Z0-9]+)\s*\('
)
_HG22_RECEIVER_METHOD_RE = re.compile(
    r'\b([a-z_][a-zA-Z0-9_]*)\.([a-z_][a-zA-Z0-9_]*)\s*\('
)


def _strip_hallucinated_method_calls(
    blocks: list[BlockIR],
    class_method_map: dict[str, frozenset[str]],
    public_classes: set[str],
) -> list[BlockIR]:
    """Remove or comment-out hallucinated method calls on tracked library instances.

    HG-22 (TC-GEN-301): Complements HG-16 (class-level) by checking method calls.
    For each Python code block, tracks ``var = KnownClass()`` assignments and verifies
    ``receiver.method()`` calls against ``class_method_map[tracked_class]``.

    Decision logic per block:
    - 2+ unknown tracked methods → strip entire block (same as HG-16 for classes)
    - 1 unknown tracked method → comment out the offending line
    - 0 unknown → pass through unchanged

    Non-Python blocks and untracked receivers pass through without inspection.

    Parameters
    ----------
    blocks:
        BlockIR list from parse_and_validate_blocks().
    class_method_map:
        ``{ClassName: frozenset(method_names | property_names)}`` from class_briefs.
    public_classes:
        Known class names from api_surface.public_classes.
    """
    if not class_method_map or not public_classes:
        return blocks

    # Build case-insensitive class name lookup for receiver matching
    class_name_lower: dict[str, str] = {c.lower(): c for c in public_classes}

    result: list[BlockIR] = []
    stripped_count = 0
    commented_count = 0

    for block in blocks:
        if block.type != BlockType.code:
            result.append(block)
            continue

        lang = (block.language or "").lower()
        if lang not in ("python", "py", "python3", ""):
            result.append(block)
            continue

        code = block.content or ""
        if not code.strip():
            result.append(block)
            continue

        # HG-17 pattern: strip comments before scanning
        code_for_scanning = "\n".join(
            line.split("#")[0] for line in code.split("\n")
        )

        # Track var → ClassName assignments
        var_class_map: dict[str, str] = {}
        for m in _HG22_ASSIGNMENT_RE.finditer(code_for_scanning):
            var_name, cls_name = m.group(1), m.group(2)
            if cls_name in public_classes:
                var_class_map[var_name] = cls_name

        # Find unknown method calls on tracked receivers
        unknown_lines: set[int] = set()
        unknown_methods: list[str] = []

        lines = code.split("\n")
        scan_lines = code_for_scanning.split("\n")
        for line_idx, scan_line in enumerate(scan_lines):
            for m in _HG22_RECEIVER_METHOD_RE.finditer(scan_line):
                receiver = m.group(1)
                method_name = m.group(2)
                if method_name.startswith("_"):
                    continue

                # Determine tracked class
                tracked_class = var_class_map.get(receiver)
                if tracked_class is None:
                    matched_cls = class_name_lower.get(receiver)
                    if matched_cls:
                        tracked_class = matched_cls

                if tracked_class is None:
                    continue  # Untracked — skip

                class_members = class_method_map.get(tracked_class, frozenset())
                if method_name not in class_members:
                    unknown_lines.add(line_idx)
                    unknown_methods.append(method_name)

        if len(unknown_methods) >= 2:
            # Strip entire block
            logger.info(
                "[HG-22] Removing code block with %d hallucinated method(s): %s",
                len(unknown_methods),
                ", ".join(sorted(set(unknown_methods))),
            )
            stripped_count += 1
            continue  # Drop block

        if len(unknown_methods) == 1:
            # Remove the offending line (TC-GEN-601: no visible markers in published code)
            new_lines: list[str] = []
            for idx, line in enumerate(lines):
                if idx in unknown_lines:
                    commented_count += 1  # reuse counter for logging
                else:
                    new_lines.append(line)
            new_code = "\n".join(new_lines)
            logger.debug(
                "[HG-22] Removed hallucinated method '%s' from code block",
                unknown_methods[0],
            )
            result.append(block.model_copy(update={"content": new_code}))
        else:
            result.append(block)

    if stripped_count or commented_count:
        logger.info(
            "[HG-22] Method verification: %d blocks stripped, %d lines removed",
            stripped_count, commented_count,
        )

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
            if base.lower() == "aspose" or module.lower().startswith("aspose."):
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


def _normalize_csharp_imports(
    code: str,
    canonical_import: str,
    import_allowlist: list[str],
) -> str:
    """TC-NET-002: Normalize C# ``using`` statements to the canonical import.

    Rewrites any ``using Aspose.*.Foss*;`` or other wrong Aspose sub-namespace
    that is neither ``canonical_import`` nor present in ``import_allowlist``.
    Non-Aspose ``using`` statements (e.g. ``using System.IO;``) are left intact.

    Example::

        _normalize_csharp_imports(
            "using Aspose.Slides.Foss;", "Aspose.Slides", []
        )
        # → "using Aspose.Slides;"
    """
    if not canonical_import:
        return code

    allowlist_set = set(import_allowlist or [])
    lines = code.split("\n")
    normalized: list[str] = []

    for line in lines:
        m = re.match(r"^(\s*)using\s+([\w.]+)\s*;", line)
        if m:
            indent = m.group(1)
            namespace = m.group(2)
            # Only touch Aspose namespaces; leave System.*, Microsoft.*, etc. alone.
            if namespace.lower().startswith("aspose"):
                if namespace != canonical_import and namespace not in allowlist_set:
                    normalized.append(f"{indent}using {canonical_import};")
                    continue
        normalized.append(line)

    return "\n".join(normalized)


# ---------------------------------------------------------------------------
# TC-FIX-214: Product name canonicalization
# ---------------------------------------------------------------------------

_ASPOSE_MISSPELLINGS = re.compile(
    r"\b(Aspire|Aspuse|Apose|Aspsoe|Asopse)\.",
    re.IGNORECASE,
)
_ASPOSE_SPACE_DOT = re.compile(r"\bAspose\.\s+", re.IGNORECASE)
_DOUBLED_QUALIFIER = re.compile(r"\b(for \w+)\s+\1\b", re.IGNORECASE)
# Match code blocks to exclude them from canonicalization
_CODE_FENCE = re.compile(r"```[\s\S]*?```", re.MULTILINE)


def _canonicalize_product_name(content: str, product_name: str) -> str:
    """Fix common LLM misspellings of Aspose product names in prose.

    Code blocks (```...```) are excluded from replacement.
    """
    if not content or not product_name or "." not in product_name:
        return content

    # Extract code blocks, replace in prose only
    code_blocks: list[tuple[int, int, str]] = []
    for m in _CODE_FENCE.finditer(content):
        code_blocks.append((m.start(), m.end(), m.group()))

    # Split content around code blocks
    parts: list[str] = []
    last_end = 0
    for start, end, block_text in code_blocks:
        prose = content[last_end:start]
        # Fix misspellings in prose
        prose = _ASPOSE_MISSPELLINGS.sub("Aspose.", prose)
        prose = _ASPOSE_SPACE_DOT.sub("Aspose.", prose)
        prose = _DOUBLED_QUALIFIER.sub(r"\1", prose)
        parts.append(prose)
        parts.append(block_text)  # Code block unchanged
        last_end = end

    # Handle trailing prose after last code block
    trailing = content[last_end:]
    trailing = _ASPOSE_MISSPELLINGS.sub("Aspose.", trailing)
    trailing = _ASPOSE_SPACE_DOT.sub("Aspose.", trailing)
    trailing = _DOUBLED_QUALIFIER.sub(r"\1", trailing)
    parts.append(trailing)

    return "".join(parts)


# ---------------------------------------------------------------------------
# TC-FIX-214: Opener boilerplate stripping
# ---------------------------------------------------------------------------

_WHEN_WORKING_WITH = re.compile(
    r"When working with\s[^.]*\.\s*",
    re.IGNORECASE,
)


def _strip_opener_boilerplate(content: str) -> str:
    """Remove 'When working with ...' opener sentences after H2 headings.

    Only strips when the phrase is at the start of the first paragraph
    following an H2 heading. Content without H2 headings is returned unchanged.
    """
    if not content:
        return ""
    if "## " not in content:
        return content

    lines = content.split("\n")
    result_lines: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        result_lines.append(line)
        # If this is an H2 heading, look at the next non-empty line
        if line.strip().startswith("## "):
            i += 1
            # Skip blank lines between heading and paragraph
            while i < len(lines) and not lines[i].strip():
                result_lines.append(lines[i])
                i += 1
            if i < len(lines):
                para_line = lines[i]
                if para_line.strip().lower().startswith("when working with"):
                    # Strip the opener sentence
                    cleaned = _WHEN_WORKING_WITH.sub("", para_line, count=1).strip()
                    if cleaned:
                        result_lines.append(cleaned)
                    # else: entire line was the opener, skip it
                else:
                    result_lines.append(para_line)
                i += 1
        else:
            i += 1

    return "\n".join(result_lines)
