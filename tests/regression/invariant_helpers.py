"""Pure-function detectors for content invariant regression tests (TC-2920).

These helpers wrap existing pattern lists from the production gate/sanitizer
modules into a simple content-string API so tests can check invariants
without needing a full run_dir structure.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from launch.review.dimensions.deterministic import _PROMPT_LEAK_PATTERNS
from launch.workers._shared.content_sanitizer import _SCAFFOLDING_PATTERNS
from launch.workers.w9_validator.gates.gate_scaffold_leak import _LEAK_PATTERNS


# ---------------------------------------------------------------------------
# 1. Scaffold / prompt leak detection
# ---------------------------------------------------------------------------


def detect_scaffold_leaks(content: str) -> List[Dict[str, Any]]:
    """Scan markdown content for scaffold/prompt leak patterns.

    Combines patterns from three production sources:
    - gate_scaffold_leak._LEAK_PATTERNS  (21 regexes, TC-2890)
    - deterministic._PROMPT_LEAK_PATTERNS (19 regexes, TC-2890)
    - content_sanitizer._SCAFFOLDING_PATTERNS (21 regexes, TC-2890)

    Fence-aware: pipeline diagnostics/JSON inside code fences get severity
    ``"warn"``; everything else outside fences is ``"error"``.

    Returns list of ``{line, category, text, severity, source}`` dicts.
    """
    results: List[Dict[str, Any]] = []
    lines = content.splitlines()
    in_fence = False

    for line_num, line in enumerate(lines, 1):
        stripped = line.strip()

        if stripped.startswith("```"):
            in_fence = not in_fence
            continue

        # --- gate_scaffold_leak patterns (fence-aware severity) ---
        for pattern, category in _LEAK_PATTERNS:
            if pattern.search(line):
                if in_fence and category in ("PIPELINE_DIAGNOSTIC", "PIPELINE_JSON"):
                    severity = "warn"
                elif in_fence:
                    # LLM scaffold / meta inside fence is still suspicious
                    severity = "warn"
                else:
                    severity = "error"
                results.append({
                    "line": line_num,
                    "category": category,
                    "text": stripped[:80],
                    "severity": severity,
                    "source": "gate_scaffold_leak",
                })
                break  # one hit per line per source

        # --- prompt leak patterns (prose only) ---
        if not in_fence:
            for pattern in _PROMPT_LEAK_PATTERNS:
                if pattern.search(line):
                    results.append({
                        "line": line_num,
                        "category": "PROMPT_LEAK",
                        "text": stripped[:80],
                        "severity": "error",
                        "source": "review_deterministic",
                    })
                    break

            # --- scaffolding section headings (prose only) ---
            for pattern in _SCAFFOLDING_PATTERNS:
                if pattern.match(stripped):
                    results.append({
                        "line": line_num,
                        "category": "SCAFFOLDING_SECTION",
                        "text": stripped[:80],
                        "severity": "error",
                        "source": "content_sanitizer",
                    })
                    break

    return results


# ---------------------------------------------------------------------------
# 2. Consecutive same-language code fence detection
# ---------------------------------------------------------------------------

_FENCE_OPEN = re.compile(r"^(`{3,})\s*(\S*)")


def detect_consecutive_same_lang_fences(content: str) -> List[Dict[str, Any]]:
    """Detect adjacent code fences with the same language separated only by whitespace.

    Does NOT merge — detection only.  Prose (non-whitespace text) or headings
    between fences mean they are intentionally separate and are not flagged.

    Returns list of ``{line, lang, message}`` dicts.
    """
    lines = content.split("\n")
    # Parse into blocks: list of (type, lang, start_line)
    blocks: List[Dict[str, Any]] = []
    in_fence = False
    fence_marker: str = ""

    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        m = _FENCE_OPEN.match(stripped)

        if in_fence:
            # Inside a fence — look for matching close
            if stripped == fence_marker or (m and m.group(1) == fence_marker and not m.group(2)):
                in_fence = False
                i += 1
                continue
            # Still inside fence body — skip
            i += 1
            continue

        # Outside fence — check for opening
        if m:
            fence_marker = m.group(1)
            lang = m.group(2) or ""
            start = i + 1  # 1-indexed
            in_fence = True
            blocks.append({"type": "code", "lang": lang, "start": start})
            i += 1
        else:
            if blocks and blocks[-1]["type"] == "text":
                blocks[-1]["lines"].append(lines[i])
            else:
                blocks.append({"type": "text", "lang": "", "start": i + 1, "lines": [lines[i]]})
            i += 1

    # Check consecutive code blocks
    hits: List[Dict[str, Any]] = []
    for j in range(len(blocks) - 2):
        b1, b_mid, b2 = blocks[j], blocks[j + 1], blocks[j + 2]
        if b1["type"] != "code" or b2["type"] != "code":
            continue
        if b_mid["type"] != "text":
            continue
        # Same language?
        if b1["lang"] != b2["lang"]:
            continue
        # Intervening text is whitespace-only? (no prose, no headings)
        mid_text = "\n".join(b_mid.get("lines", [])).strip()
        if mid_text == "":
            lang_display = b2["lang"] or "(bare)"
            hits.append({
                "line": b2["start"],
                "lang": b2["lang"],
                "message": (
                    f"Consecutive '{lang_display}' fence at line {b2['start']}, "
                    f"previous at line {b1['start']}"
                ),
            })

    return hits


# ---------------------------------------------------------------------------
# 3. Limitations section size cap
# ---------------------------------------------------------------------------

_LIMITATIONS_RE = re.compile(
    r"^##\s+Limitations\s*\n(.*?)(?=^##\s|\Z)",
    re.MULTILINE | re.DOTALL,
)
_BULLET_RE = re.compile(r"^\s*[-*+]\s", re.MULTILINE)


def check_limitations_cap(
    content: str,
    max_words: int = 300,
    max_bullets: int = 15,
) -> Optional[Dict[str, Any]]:
    """Check whether a ``## Limitations`` section exceeds size heuristic caps.

    Returns ``None`` if within limits (or section absent).
    Returns ``{words, bullets, message}`` if either cap is exceeded.
    """
    match = _LIMITATIONS_RE.search(content)
    if not match:
        return None

    section = match.group(1)
    words = len(section.split())
    bullets = len(_BULLET_RE.findall(section))

    if words > max_words or bullets > max_bullets:
        return {
            "words": words,
            "bullets": bullets,
            "message": (
                f"Limitations section: {words} words, {bullets} bullets "
                f"(caps: {max_words}/{max_bullets})"
            ),
        }
    return None
