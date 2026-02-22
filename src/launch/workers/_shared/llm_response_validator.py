"""Layer 1 LLM Response Validator — catches defects at call time before downstream propagation.

Validates raw LLM responses immediately after each call and returns a structured result
that the caller can use to retry with an enhanced prompt. Target: <15ms per call.

Defects caught:
- Unbalanced code fences (odd number of ``` markers)
- Frontmatter contamination (more than 2 ``---`` delimiters)
- Truncation (response does not end with sentence-terminal punctuation or a closing fence)
- Minimum content length (<50 chars stripped)

Reference: content-generator/src/utils/llm_response_validator.py
Integration: src/launch/clients/llm_provider.py LLMProviderClient.chat_completion()

Spec: specs/21_worker_contracts.md
TC: TC-2392
"""

from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from typing import List

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────

# Terminal characters that indicate a response is complete
_TERMINAL_CHARS = frozenset(".!?`>")

# Minimum stripped length for a response to be considered non-empty
_MIN_LENGTH = 50


# ── Data model ─────────────────────────────────────────────────────────────────


@dataclass
class ValidationResult:
    """Structured result from :func:`validate_llm_response`.

    Attributes:
        is_valid: True when no errors were found; False otherwise.
        errors: Hard failures that indicate the response must be retried or
            treated as best-effort.  Non-empty => ``is_valid`` is False.
        warnings: Soft signals (e.g. possible truncation).  Non-empty does NOT
            make ``is_valid`` False — callers decide how to handle them.
        content_type: The ``content_type`` string passed to the validator.
        validation_duration_ms: Wall-clock time the validator took in ms.
    """

    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    content_type: str = "unknown"
    validation_duration_ms: int = 0


# ── Public API ─────────────────────────────────────────────────────────────────


def validate_llm_response(
    content: str,
    content_type: str = "markdown",
) -> ValidationResult:
    """Layer 1: fast structural validation at LLM call time.

    Runs in < 15 ms on typical 2 000-char responses.  All checks are pure
    string operations — no regex compilation at call time (patterns are
    pre-compiled at import time in the reference impl; here we keep it
    even simpler with ``str.count``/``str.split`` to stay under 15 ms).

    Checks (in order):
    1. Code-fence balance — ``content.count("```")`` must be even.
    2. Frontmatter contamination — more than 2 bare ``---`` lines means
       the LLM reproduced a YAML block inside generated markdown.
    3. Truncation detection — response does not end with ``.!?`>``
       (warning, not error).
    4. Minimum content — stripped content must be >= 50 chars (error).

    Args:
        content: Raw string returned by the LLM.
        content_type: Descriptive label stored on the result; does not
            change which checks run.  Examples: ``"markdown"``,
            ``"section"``, ``"outline"``.

    Returns:
        :class:`ValidationResult` with ``is_valid``, ``errors``,
        ``warnings``, ``content_type``, and ``validation_duration_ms``.
    """
    t0 = time.monotonic()
    errors: List[str] = []
    warnings: List[str] = []

    # ── Check 1: code fence balance ───────────────────────────────────────────
    fence_count = content.count("```")
    if fence_count % 2 != 0:
        errors.append(
            f"Unbalanced code fences: {fence_count} ``` markers found (must be even). "
            "LLM likely wrapped entire response in a code block or left one unclosed."
        )

    # ── Check 2: frontmatter contamination ───────────────────────────────────
    # Count lines that consist solely of "---" (bare YAML delimiters).
    # A valid single frontmatter block uses exactly 2 such lines.
    # More than 2 means the LLM duplicated or contaminated the frontmatter.
    dashes_lines = [ln for ln in content.split("\n") if ln.strip() == "---"]
    if len(dashes_lines) > 2:
        errors.append(
            f"Frontmatter contamination: {len(dashes_lines)} bare '---' lines found "
            "(maximum 2 for a single frontmatter block). "
            "Do not include YAML frontmatter in generated content."
        )

    # ── Check 3: truncation (warning only) ───────────────────────────────────
    # Skip truncation check for JSON responses (they end with } or ] which are valid)
    stripped = content.rstrip()
    _ends_like_json = stripped.endswith("}") or stripped.endswith("]") or stripped.endswith('"')
    if stripped and stripped[-1] not in _TERMINAL_CHARS and not _ends_like_json:
        warnings.append(
            f"Response may be truncated: last character is {stripped[-1]!r} "
            f"(expected one of {sorted(_TERMINAL_CHARS)}). "
            "Ensure the response ends with a complete sentence or closing fence."
        )

    # ── Check 4: minimum content length ───────────────────────────────────────
    # Skip minimum length for valid JSON responses: {"defects": [], "fixed_content": null}
    # is 44 chars and perfectly valid. Only flag truly empty/trivial responses.
    # Also skip for valid one-word keyword responses: NONE, YES, NO, TRUE, FALSE, PASS, FAIL, N/A.
    # These are expected for semantic yes/no checks (e.g. "NONE" = no hallucinations found).
    import re as _re
    _KEYWORD_PATTERN = _re.compile(
        r'^(NONE|YES|NO|TRUE|FALSE|PASS|FAIL|N/A|SKIP|OK|CLEAN)$',
        _re.IGNORECASE,
    )
    stripped_len = len(content.strip())
    if stripped_len < _MIN_LENGTH:
        # Allow short responses that are valid JSON (gate checks, structured outputs)
        _is_valid_json = False
        try:
            import json as _json
            _json.loads(content.strip())
            _is_valid_json = True
        except (ValueError, TypeError):
            pass
        # Allow short keyword responses (semantic yes/no checks)
        _is_keyword = bool(_KEYWORD_PATTERN.match(content.strip()))
        if not _is_valid_json and not _is_keyword:
            errors.append(
                f"Response too short: {stripped_len} chars (minimum {_MIN_LENGTH}). "
                "The LLM returned an empty or near-empty response."
            )

    duration_ms = int((time.monotonic() - t0) * 1000)
    is_valid = len(errors) == 0

    if is_valid:
        logger.debug(
            "l1_validation_passed content_type=%s duration_ms=%d warnings=%d",
            content_type,
            duration_ms,
            len(warnings),
        )
    else:
        logger.warning(
            "l1_validation_failed content_type=%s duration_ms=%d errors=%s",
            content_type,
            duration_ms,
            errors,
        )

    return ValidationResult(
        is_valid=is_valid,
        errors=errors,
        warnings=warnings,
        content_type=content_type,
        validation_duration_ms=duration_ms,
    )


def enhance_prompt_for_retry(
    base_prompt: str,
    validation_result: ValidationResult,
) -> str:
    """Inject error context into a prompt before a retry attempt.

    When :func:`validate_llm_response` returns ``is_valid=False`` the caller
    should pass the original prompt and the ``ValidationResult`` to this
    function, then use the returned string as the new prompt.

    If ``validation_result.errors`` is empty, ``base_prompt`` is returned
    unchanged (allows the same call-site logic regardless of validity).

    Args:
        base_prompt: The prompt that produced the invalid response.
        validation_result: Result from :func:`validate_llm_response`.

    Returns:
        Enhanced prompt with a trailing block listing the errors and
        instructions to avoid them, or ``base_prompt`` unchanged when
        there are no errors.
    """
    if not validation_result.errors:
        return base_prompt

    error_block = "\n".join(f"- {e}" for e in validation_result.errors)
    return (
        f"{base_prompt}\n\n"
        "IMPORTANT: Your previous attempt had the following issues — fix them:\n"
        f"{error_block}\n"
        "Ensure code fences are balanced (every opening ``` has a matching closing ```).\n"
        "Do not wrap the entire response in a code fence.\n"
        "Do not include YAML frontmatter (--- blocks) in the generated content.\n"
        "Complete all sentences before the response ends."
    )
