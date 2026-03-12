"""Input sanitization for untrusted external content (TC-3825).

Applied at the pipeline input boundary (repo file reads, LLM claim text) before
any content enters the LLM prompt pipeline or is stored in pipeline artifacts.

Design principles:
- Code blocks (``` and ~~~) are EXEMPT from prose sanitization rules: security
  documentation and code examples legitimately contain XSS-like patterns.
- Sanitization is idempotent: sanitize_input(sanitize_input(t).text) == sanitize_input(t).
- No HTML escaping at render time — ir_renderer outputs Markdown, not HTML.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pre-compiled patterns
# ---------------------------------------------------------------------------

# XSS removal — matches common injection vectors in prose text.
# Applied to prose segments only (code blocks are exempt).
_XSS_PATTERNS: tuple[re.Pattern, ...] = (
    re.compile(r"<script[^>]*>.*?</script>", re.DOTALL | re.IGNORECASE),
    re.compile(r"<iframe[^>]*>.*?</iframe>", re.DOTALL | re.IGNORECASE),
    re.compile(r"javascript:[^\s\"'<>]*", re.IGNORECASE),
    re.compile(r'on[a-zA-Z]+\s*=\s*"[^"]*"', re.IGNORECASE),
    re.compile(r"on[a-zA-Z]+\s*=\s*'[^']*'", re.IGNORECASE),
)

# Secret redaction — matches key-like tokens with 20+ alphanumeric chars.
# Negative lookbehind prevents matching mid-word (e.g. inside a URL slug).
# Covers common API key prefixes: sk-, pk-, rk-, ak-
_SECRET_RE: re.Pattern = re.compile(
    r"(?<![A-Za-z0-9])((sk|pk|rk|ak)-[A-Za-z0-9]{20,})"
)

# Verify that the [REDACTED] sentinel does NOT match _SECRET_RE so that
# idempotency is preserved (running sanitizer twice produces the same output).
assert not _SECRET_RE.search("[REDACTED]"), (
    "_SECRET_RE must not match the [REDACTED] sentinel — idempotency would break"
)

# Truncation marker appended when content exceeds max_chars.
# Defined at module level so the budget calculation (max_chars - len(_TRUNCATION_MARKER))
# is based on a stable, pre-known length and is not recomputed on every call.
_TRUNCATION_MARKER: str = "\n\n[TRUNCATED: content exceeded limit]"


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SanitizationResult:
    """Immutable result of a single sanitize_input() call.

    Attributes:
        text:             The sanitized text.
        redaction_count:  Number of distinct redaction/removal operations applied.
        truncated:        True if the text was cut at max_chars.
        redacted_kinds:   Which rule categories fired (e.g. ['xss', 'secret']).
    """

    text: str
    redaction_count: int
    truncated: bool
    redacted_kinds: list[str] = field(default_factory=list)


def sanitize_input(text: str, *, max_chars: int = 50_000) -> SanitizationResult:
    """Sanitize untrusted external text for safe pipeline ingestion.

    Rules applied in order:
    1. Code block passthrough — content inside ``` / ~~~ fences is exempt.
    2. XSS removal — <script>, <iframe>, javascript:, event handlers.
    3. Secret redaction — sk-/pk-/rk-/ak- tokens with 20+ chars.
    4. Oversized truncation — hard cap at max_chars, cut at last whitespace.

    The function is idempotent:
        sanitize_input(sanitize_input(t).text) == sanitize_input(t)

    Args:
        text:      Raw text from an external source.
        max_chars: Maximum character count after redaction before truncating.

    Returns:
        SanitizationResult with the sanitized text and audit metadata.
    """
    if not text:
        return SanitizationResult(text=text, redaction_count=0, truncated=False)

    redaction_count = 0
    redacted_kinds: list[str] = []
    truncated = False

    # --- Step 1 + 2: Split into prose/code segments, apply XSS removal to prose ---
    prose_segments, code_ranges = _split_prose_code(text)

    # Apply XSS rules to each prose segment.
    xss_hits = 0
    sanitized_segments: list[str] = []
    for segment_text, is_code in prose_segments:
        if is_code:
            sanitized_segments.append(segment_text)
        else:
            cleaned = segment_text
            for pattern in _XSS_PATTERNS:
                new_cleaned, n = pattern.subn("", cleaned)
                xss_hits += n
                cleaned = new_cleaned
            sanitized_segments.append(cleaned)

    text = "".join(sanitized_segments)
    if xss_hits:
        redaction_count += xss_hits
        redacted_kinds.append("xss")

    # --- Step 3: Secret redaction ---
    def _redact_secret(m: re.Match) -> str:
        # Log kind (prefix) and byte position only — the secret value is never logged.
        logger.warning(
            "[Sanitizer] secret redacted: kind=%s pos=%d",
            m.group(2),  # "sk", "pk", "rk", or "ak"
            m.start(),   # byte offset in the text being sanitized
        )
        return "[REDACTED]"

    new_text, secret_count = _SECRET_RE.subn(_redact_secret, text)
    if secret_count:
        text = new_text
        redaction_count += secret_count
        redacted_kinds.append("secret")

    # --- Step 4: Oversized truncation ---
    if len(text) > max_chars:
        # Budget for actual content = max_chars minus the marker length, so that
        # len(result) <= max_chars on every pass (idempotency invariant).
        budget = max_chars - len(_TRUNCATION_MARKER)
        if budget <= 0:
            text = _TRUNCATION_MARKER
        else:
            cutpoint = text.rfind(" ", 0, budget)
            if cutpoint <= budget // 2:
                # No good word boundary — hard cut at budget
                cutpoint = budget
            text = text[:cutpoint] + _TRUNCATION_MARKER
        truncated = True
        if "oversized" not in redacted_kinds:
            redacted_kinds.append("oversized")

    return SanitizationResult(
        text=text,
        redaction_count=redaction_count,
        truncated=truncated,
        redacted_kinds=redacted_kinds,
    )


# ---------------------------------------------------------------------------
# Internal: prose/code segment splitting
# ---------------------------------------------------------------------------


def _split_prose_code(text: str) -> tuple[list[tuple[str, bool]], list[tuple[int, int]]]:
    """Split text into alternating prose and code-fence segments.

    Returns:
        segments: list of (text_fragment, is_code_block) tuples.
        code_ranges: list of (start_char, end_char) for code block regions
            (informational only — not used by the caller).

    Code fence detection uses a line-by-line state machine that tracks both
    backtick (```) and tilde (~~~) fence styles with their exact indent+marker.
    Indented code blocks (4 leading spaces) are also treated as code.
    """
    lines = text.split("\n")
    segments: list[tuple[str, bool]] = []
    code_ranges: list[tuple[int, int]] = []

    in_fence = False
    fence_marker: str = ""          # the opening fence chars (```, ~~~, etc.)
    prose_buf: list[str] = []
    code_buf: list[str] = []
    char_pos = 0
    fence_start = 0

    for line in lines:
        stripped = line.lstrip()

        if not in_fence:
            # Detect fence open: line starts with ``` or ~~~
            if stripped.startswith("```") or stripped.startswith("~~~"):
                # Flush prose buffer
                if prose_buf:
                    prose_text = "\n".join(prose_buf) + "\n"
                    segments.append((prose_text, False))
                    char_pos += len(prose_text)
                    prose_buf = []

                fence_marker = stripped[:3]
                in_fence = True
                fence_start = char_pos
                code_buf = [line]
            # Detect indented code block (4 spaces or tab prefix)
            elif line.startswith("    ") or line.startswith("\t"):
                # Flush prose, treat single indented line as code passthrough
                if prose_buf:
                    segments.append(("\n".join(prose_buf) + "\n", False))
                    prose_buf = []
                segments.append((line + "\n", True))
            else:
                prose_buf.append(line)
        else:
            code_buf.append(line)
            # Detect fence close: line stripped is exactly the same fence marker
            # (or starts with it without additional content after the quotes)
            if stripped.startswith(fence_marker) and stripped.strip("` ~") == "":
                code_text = "\n".join(code_buf) + "\n"
                segments.append((code_text, True))
                code_ranges.append((fence_start, char_pos + len(code_text)))
                char_pos += len(code_text)
                code_buf = []
                in_fence = False
                fence_marker = ""

    # Flush remaining buffers
    if in_fence and code_buf:
        # Unclosed fence — treat as code (conservative)
        code_text = "\n".join(code_buf)
        segments.append((code_text, True))
    elif prose_buf:
        segments.append(("\n".join(prose_buf), False))

    return segments, code_ranges
