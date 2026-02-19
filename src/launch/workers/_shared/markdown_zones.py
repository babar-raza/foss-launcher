"""Zone-aware markdown parser for content_sanitizer.py.

Splits a markdown document into typed zones so that sanitizer functions can be
applied selectively: prose rules are never applied to code blocks or frontmatter,
preventing the "fix one thing, break another" cascade pattern.

Zone types
----------
FRONTMATTER  Lines between the opening ``---`` and closing ``---`` (if present at top).
CODE_FENCE   Lines between a triple-backtick or tilde fence (``` / ~~~).
HEADING      One or more consecutive lines starting with ``#``.
TABLE        One or more consecutive lines with >= 2 ``|`` characters.
LIST         One or more consecutive list-item lines (``-``, ``*``, ``+``, ``N.``).
PROSE        Everything else (paragraphs, blank lines).

Key properties
--------------
- **Round-trip identity**: ``render_zones(parse_zones(text)) == text`` for any input.
- **Pure function**: no I/O, no side effects.
- **Stdlib only**: uses only ``re`` from the standard library.
- **Additive**: existing sanitizers are unchanged; ``apply_to_prose_zones`` is an
  opt-in wrapper.

TC-2375 (RD-02): Zone-aware content parser.

Per specs/21_worker_contracts.md §"Shared Module: Zone-Aware Sanitizer Model".
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, List


# ---------------------------------------------------------------------------
# Zone type constants
# ---------------------------------------------------------------------------

FRONTMATTER: str = "FRONTMATTER"
CODE_FENCE: str = "CODE_FENCE"
HEADING: str = "HEADING"
TABLE: str = "TABLE"
LIST: str = "LIST"
PROSE: str = "PROSE"

# Zones that prose sanitizers must never touch.
_PROTECTED: frozenset = frozenset({FRONTMATTER, CODE_FENCE})


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class Zone:
    """A typed region of a markdown document.

    Attributes:
        zone_type:  One of the zone type constants above.
        content:    Raw text of this zone (all original characters preserved).
        start_line: 0-based line index of the first line in the original document.
    """

    zone_type: str
    content: str
    start_line: int = 0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_zones(text: str) -> List[Zone]:
    """Split markdown text into an ordered list of typed Zone objects.

    Round-trip guarantee: ``render_zones(parse_zones(text)) == text``.

    The algorithm is line-based and uses ``splitlines(keepends=True)`` so that
    all line endings (``\\n``, ``\\r\\n``) are preserved exactly.

    Args:
        text: Raw markdown string (any encoding; may or may not end with ``\\n``).

    Returns:
        List of Zone objects in document order.  Empty list for empty input.
    """
    if not text:
        return []

    lines = text.splitlines(keepends=True)
    zones: List[Zone] = []
    i: int = 0
    doc_line: int = 0

    # ── Frontmatter ──────────────────────────────────────────────────────────
    if lines and lines[0].rstrip("\r\n") == "---":
        j = 1
        while j < len(lines) and lines[j].rstrip("\r\n") != "---":
            j += 1
        if j < len(lines):
            fm = "".join(lines[: j + 1])
            zones.append(Zone(FRONTMATTER, fm, 0))
            i = j + 1
            doc_line = i

    # ── Rest of document ─────────────────────────────────────────────────────
    accum: List[str] = []
    accum_type: str = PROSE
    accum_start: int = doc_line

    def _flush() -> None:
        if accum:
            zones.append(Zone(accum_type, "".join(accum), accum_start))
            accum.clear()

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # ── Code fence ───────────────────────────────────────────────────────
        if stripped.startswith("```") or stripped.startswith("~~~"):
            _flush()
            fence_lines: List[str] = [line]
            fence_start = doc_line
            i += 1
            doc_line += 1
            while i < len(lines):
                fence_lines.append(lines[i])
                doc_line += 1
                is_closer = (
                    lines[i].strip().startswith("```")
                    or lines[i].strip().startswith("~~~")
                )
                i += 1
                if is_closer:
                    break
            zones.append(Zone(CODE_FENCE, "".join(fence_lines), fence_start))
            accum_type = PROSE
            accum_start = doc_line
            continue

        # ── Classify non-fence line ───────────────────────────────────────────
        if stripped.startswith("#"):
            line_type = HEADING
        elif "|" in stripped and stripped.count("|") >= 2:
            line_type = TABLE
        elif stripped.startswith(("- ", "* ", "+ ")) or _is_ordered_list_item(stripped):
            line_type = LIST
        else:
            line_type = PROSE  # blank lines and regular prose

        # Flush accumulator on type change (blank lines stay with current zone)
        if stripped and line_type != accum_type and accum:
            _flush()
            accum_type = line_type
            accum_start = doc_line
        elif not accum:
            accum_type = line_type if stripped else PROSE
            accum_start = doc_line

        accum.append(line)
        i += 1
        doc_line += 1

    _flush()
    return zones


def render_zones(zones: List[Zone]) -> str:
    """Reconstruct markdown text from a list of zones.

    This is the inverse of ``parse_zones``: concatenating zone contents in
    order always yields the original text (round-trip identity property).

    Args:
        zones: List of Zone objects (typically produced by ``parse_zones``).

    Returns:
        Reconstructed markdown string.
    """
    return "".join(z.content for z in zones)


def apply_to_prose_zones(fn: Callable[[str], str], content: str) -> str:
    """Apply a sanitizer function to non-protected zones only.

    Protects ``FRONTMATTER`` and ``CODE_FENCE`` zones from modification.
    All other zone types (``HEADING``, ``TABLE``, ``LIST``, ``PROSE``) are
    passed through ``fn``.

    This is the core enabler of zone-aware sanitization: existing sanitizer
    functions need not be changed — simply wrap them with this helper when
    calling from ``run_pipeline()``.

    Args:
        fn:      Sanitizer with signature ``(content: str) -> str``.
        content: Full markdown document string.

    Returns:
        Sanitized markdown document with code fences and frontmatter intact.

    Example::

        # Before wrapping: strip_emojis could corrupt emoji in code strings
        content = strip_emojis(content)

        # After wrapping: code blocks are untouched
        content = apply_to_prose_zones(strip_emojis, content)
    """
    zones = parse_zones(content)
    result: List[str] = []
    for zone in zones:
        if zone.zone_type in _PROTECTED:
            result.append(zone.content)
        else:
            result.append(fn(zone.content))
    return "".join(result)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_ORDERED_LIST_RE = re.compile(r"^\d+[.)]\s")


def _is_ordered_list_item(stripped: str) -> bool:
    """Return True if the stripped line starts an ordered list item."""
    return bool(_ORDERED_LIST_RE.match(stripped))
