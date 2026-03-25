"""Block sequence extraction from markdown content.

TC-FIX-214: Provides ``get_block_sequence`` used by ``golden_conformance``
for block-type coverage scoring.
"""
from __future__ import annotations

import re


_CODE_FENCE_RE = re.compile(r"^```", re.MULTILINE)
_TABLE_RE = re.compile(r"^\|.+\|", re.MULTILINE)
_LIST_RE = re.compile(r"^[ \t]*[-*+]\s|^[ \t]*\d+\.\s", re.MULTILINE)
_HEADING_RE = re.compile(r"^#{1,6}\s", re.MULTILINE)
_CALLOUT_RE = re.compile(r"^>\s*\[!", re.MULTILINE)


def get_block_sequence(markdown: str) -> list[str]:
    """Return an ordered list of block type tokens found in *markdown*.

    Recognised types: ``paragraph``, ``code``, ``table``, ``list``,
    ``heading``, ``callout``.  Consecutive paragraphs are collapsed into
    a single ``paragraph`` token.
    """
    if not markdown or not markdown.strip():
        return []

    types: list[str] = []
    in_code = False

    for line in markdown.splitlines():
        stripped = line.strip()

        # Toggle code fences
        if _CODE_FENCE_RE.match(line):
            if not in_code:
                in_code = True
                if not types or types[-1] != "code":
                    types.append("code")
            else:
                in_code = False
            continue

        if in_code:
            continue

        if not stripped:
            continue

        if _HEADING_RE.match(line):
            if not types or types[-1] != "heading":
                types.append("heading")
        elif _TABLE_RE.match(line):
            if not types or types[-1] != "table":
                types.append("table")
        elif _CALLOUT_RE.match(line):
            if not types or types[-1] != "callout":
                types.append("callout")
        elif _LIST_RE.match(line):
            if not types or types[-1] != "list":
                types.append("list")
        else:
            if not types or types[-1] != "paragraph":
                types.append("paragraph")

    return types
