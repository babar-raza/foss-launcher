"""Shared FQ pre-lint detection functions.

Provides pure detection algorithms used by both W7 (early detection)
and W9 Gate 17 (enforcement). Each function returns raw data (tuples),
leaving issue formatting to the caller.

TC-3500: Extracted from gate_17_prelints.py to enable reuse without
cross-worker import dependency.
"""

from __future__ import annotations

from typing import List, Optional, Tuple


def detect_adjacent_same_lang_fences(content: str) -> List[Tuple[int, int, str]]:
    """Detect adjacent code fences with the same language tag.

    Two code fences are "adjacent" when the only content between the
    closing ``` of the first and the opening ``` of the second consists
    of blank lines and/or HTML comments.  If both have the same language
    tag (or one is empty), this indicates a fragmented example that should
    have been merged into a single copy-pasteable block.

    Algorithm extracted from gate_17_prelints.lint_fq8_adjacent_fences (TC-2892).

    Args:
        content: Markdown content string.

    Returns:
        List of (close_lineno, open_lineno, language) tuples for each
        adjacent-fence pair detected. ``language`` is the effective tag
        (non-empty tag from either fence, or "none" if both empty).
    """
    lines = content.splitlines()

    # Build fence events: (line_number, "open"/"close", language)
    fence_events: List[Tuple[int, str, str]] = []
    in_fence = False
    for lineno, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("```"):
            if not in_fence:
                lang = stripped[3:].strip().lower()
                fence_events.append((lineno, "open", lang))
                in_fence = True
            else:
                fence_events.append((lineno, "close", ""))
                in_fence = False

    results: List[Tuple[int, int, str]] = []

    for idx in range(len(fence_events) - 1):
        ev_close = fence_events[idx]
        ev_open = fence_events[idx + 1]
        if ev_close[1] != "close" or ev_open[1] != "open":
            continue

        close_lineno = ev_close[0]
        open_lineno = ev_open[0]

        # Check gap content (lines between closing and opening fence)
        gap_lines = lines[close_lineno: open_lineno - 1]  # 0-indexed slice
        only_blank_or_comment = all(
            not gl.strip() or gl.strip().startswith("<!--")
            for gl in gap_lines
        )
        if not only_blank_or_comment:
            continue

        # Determine the language of the block that closed
        prev_open_lang = _find_preceding_open_lang(fence_events, idx)
        next_open_lang = ev_open[2]

        # Same language (or either empty) → fragmentation
        if prev_open_lang is not None and (
            prev_open_lang == next_open_lang
            or not prev_open_lang
            or not next_open_lang
        ):
            lang_label = next_open_lang or prev_open_lang or "none"
            results.append((close_lineno, open_lineno, lang_label))

    return results


def _find_preceding_open_lang(
    fence_events: List[Tuple[int, str, str]],
    close_idx: int,
) -> Optional[str]:
    """Walk backward from a close event to find the matching open's language."""
    depth = 0
    for i in range(close_idx, -1, -1):
        if fence_events[i][1] == "close":
            depth += 1
        elif fence_events[i][1] == "open":
            depth -= 1
            if depth == 0:
                return fence_events[i][2]
    return None
