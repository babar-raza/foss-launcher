from __future__ import annotations

import logging
import re

import yaml

from launcher.models.page_ir import BlockType, PageIR
from launcher.util.errors import FrontmatterError

logger = logging.getLogger(__name__)

_CLM_CITATION_RE = re.compile(r"\s*\[CLM-[^\]]*\]")
# Matches a trailing empty comment marker (# or //) left after citation removal.
_DANGLING_COMMENT_RE = re.compile(r"\s+(?:#|//)\s*$")

# Minimum number of non-empty lines a code block must have to be eligible for
# deduplication.  Short snippets (e.g. single-line pip install commands or
# import-only stubs) are intentionally preserved verbatim in each section.
_DEDUP_MIN_LINES: int = 3

# Matches fenced code blocks including the language tag and content.
_CODE_BLOCK_RE = re.compile(r"(```[^\n]*\n)(.*?)(```)", re.DOTALL)

# Keys that MUST be present and non-None in every rendered page's frontmatter.
# Hugo silently fails or produces broken output when these are absent.
#
# Intentional exclusions:
#   "canonical"  — filled deterministically by the generate worker's canonical-fallback
#                  loop after the SEO phase; validated by the evaluate seo gate.
#   "seoTitle"   — filled by optimize_seo_metadata(); an empty-string sentinel is
#                  acceptable at render time because the evaluate seo gate detects it.
#                  Adding it here would cause render_page() to reject pages before the
#                  SEO phase has a chance to populate it.
_REQUIRED_FM_KEYS: frozenset[str] = frozenset({
    "title", "slug", "type", "url", "weight", "family", "platform", "page_role",
})


def render_page(page_ir: PageIR) -> str:
    """Render a PageIR to Hugo-compatible Markdown.

    Produces YAML frontmatter between ``---`` markers followed by
    each section rendered as Markdown with its heading and blocks.

    Raises:
        FrontmatterError: if frontmatter contains None values, is missing
            required keys, or the serialised YAML fails round-trip parse.
            Callers should catch this per-page and emit an issue_opened event
            rather than aborting the entire run.
    """
    parts: list[str] = []

    # --- Frontmatter validation ---
    fm = dict(page_ir.frontmatter) if page_ir.frontmatter else {}
    page_id: str = getattr(page_ir, "page_id", "") or ""

    # 1. Reject None values — yaml.dump produces 'null' which breaks Hugo
    #    template rendering for string fields.
    null_keys = sorted(k for k, v in fm.items() if v is None)
    if null_keys:
        raise FrontmatterError(
            f"Frontmatter has None values (Hugo renders these as 'null')",
            page_id=page_id,
            invalid_keys=null_keys,
        )

    # 2. Validate all required keys are present.
    missing = sorted(_REQUIRED_FM_KEYS - fm.keys())
    if missing:
        raise FrontmatterError(
            f"Frontmatter missing required keys",
            page_id=page_id,
            missing_keys=missing,
        )

    # 3. Serialize to YAML.
    try:
        fm_text = yaml.dump(
            fm,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=True,
        ).rstrip("\n")
    except Exception as exc:
        raise FrontmatterError(
            f"YAML serialization failed: {exc}",
            page_id=page_id,
            invalid_keys=list(fm.keys()),
        ) from exc

    # 4. Round-trip verification — parse back and confirm key count is intact.
    #    This catches custom objects or special strings that serialise but
    #    collapse on load (e.g. multi-document YAML artifacts).
    try:
        roundtripped = yaml.safe_load(fm_text)
    except yaml.YAMLError as exc:
        raise FrontmatterError(
            f"YAML round-trip parse failed: {exc}",
            page_id=page_id,
            detail=fm_text[:300],
        ) from exc

    if not isinstance(roundtripped, dict) or len(roundtripped) != len(fm):
        rt_count = len(roundtripped) if isinstance(roundtripped, dict) else "?"
        raise FrontmatterError(
            f"YAML round-trip key count mismatch: {len(fm)} serialised → {rt_count} parsed",
            page_id=page_id,
            detail=fm_text[:300],
        )

    parts.append(f"---\n{fm_text}\n---")

    # --- Sections ---
    for section in page_ir.sections:
        # Clamp heading level: minimum 2 (H1 is reserved for frontmatter title)
        level = max(section.level, 2)
        prefix = "#" * level
        parts.append(f"{prefix} {section.heading}")

        for block in section.blocks:
            parts.append(_render_block(block))

    return _dedup_code_blocks("\n\n".join(parts) + "\n")


def _normalize_code(code: str) -> str:
    """Return a whitespace-normalized key for a code block body."""
    return "\n".join(line.strip() for line in code.strip().split("\n"))


def _dedup_code_blocks(markdown: str) -> str:
    """Remove subsequent occurrences of the same code block within a page.

    Only code blocks with at least ``_DEDUP_MIN_LINES`` non-empty lines are
    eligible for deduplication. Short blocks (pip install commands, import-only
    stubs) are preserved in every section they appear.

    This is a post-render pass that corrects for the case where multiple
    concurrent section generators receive the same example snippet from the
    understanding phase and the LLM copies it verbatim into each section's output.
    """
    seen: set[str] = set()

    def _replace(m: re.Match) -> str:
        header, body, closing = m.group(1), m.group(2), m.group(3)
        non_empty_lines = [l for l in body.split("\n") if l.strip()]
        if len(non_empty_lines) < _DEDUP_MIN_LINES:
            # Too short to deduplicate — keep verbatim
            return m.group(0)
        key = _normalize_code(body)
        if key in seen:
            # Duplicate — remove the block entirely (return empty string)
            return ""
        seen.add(key)
        return m.group(0)

    result = _CODE_BLOCK_RE.sub(_replace, markdown)
    # Collapse any runs of blank lines introduced by removed blocks
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result


def _render_block(block) -> str:  # noqa: ANN001 (BlockIR)
    """Render a single BlockIR to Markdown text."""
    bt = block.type

    if bt == BlockType.paragraph:
        return _CLM_CITATION_RE.sub("", block.content)

    if bt == BlockType.code:
        lang = block.language or ""
        cleaned = "\n".join(
            _DANGLING_COMMENT_RE.sub("", _CLM_CITATION_RE.sub("", line)).rstrip()
            for line in block.content.split("\n")
        )
        return f"```{lang}\n{cleaned}\n```"

    if bt == BlockType.list:
        lines = [f"- {_CLM_CITATION_RE.sub('', item)}" for item in block.items]
        return "\n".join(lines)

    if bt == BlockType.heading:
        level = max(block.level or 3, 2)  # Never emit H1 in body
        prefix = "#" * level
        return f"{prefix} {_CLM_CITATION_RE.sub('', block.content)}"

    if bt == BlockType.table:
        content = _CLM_CITATION_RE.sub("", block.content)
        if content and "|" not in content:
            logger.warning("Table block has no pipe characters; wrapping in safety table")
            return f"| Content |\n| --- |\n| {content} |"
        return content

    if bt == BlockType.callout:
        content = _CLM_CITATION_RE.sub("", block.content)
        return f"{{{{< callout >}}}}\n{content}\n{{{{< /callout >}}}}"

    # Unknown block type - render content as-is
    return _CLM_CITATION_RE.sub("", block.content)
