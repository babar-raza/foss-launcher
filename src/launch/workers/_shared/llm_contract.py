"""LLM Contract Module: Reusable contracts for structured LLM interactions.

Provides four building blocks for hardening LLM micro-task interactions:

1. **OutputSchemaValidator** -- validates LLM output against a JSON Schema.
2. **FailureClassifier** -- classifies error strings into actionable categories.
3. **RetryStrategy** -- decides whether to retry based on failure class + attempt.
4. **RuleChecklist** -- formats per-task rules for injection into LLM prompts.

All classes are stateless and safe for concurrent use.

TC-2519: LLM Contract Hardening (Phase 5).
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Conditional jsonschema import -- if not available, validation is skipped
# with a warning (never blocks the pipeline).
# ---------------------------------------------------------------------------
try:
    import jsonschema as _jsonschema  # type: ignore[import-untyped]
except ImportError:  # pragma: no cover
    _jsonschema = None  # type: ignore[assignment]

# Regex to extract JSON from markdown-fenced code blocks
_FENCED_JSON_RE = re.compile(
    r"```(?:json)?\s*\n(.*?)\n\s*```",
    re.DOTALL,
)


# ── OutputSchemaValidator ──────────────────────────────────────────────────


class OutputSchemaValidator:
    """Validate LLM output against a JSON Schema.

    Handles both raw JSON strings and markdown-fenced JSON (```json ... ```).
    When ``jsonschema`` is not installed, validation always succeeds with a
    logged warning.

    Usage::

        validator = OutputSchemaValidator({"type": "object", "required": ["content"]})
        ok, data, err = validator.validate(llm_output_str)
        if not ok:
            print(f"Schema error: {err}")
    """

    def __init__(self, schema: Dict[str, Any]) -> None:
        self._schema = schema

    @property
    def schema(self) -> Dict[str, Any]:
        return self._schema

    def validate(self, output: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """Parse *output* as JSON and validate against the schema.

        Tries raw JSON first; falls back to extracting from a markdown fence.

        Returns:
            ``(True, parsed_dict, None)`` on success, or
            ``(False, None, error_message)`` on failure.
        """
        # Step 1: parse the JSON
        parsed = self._try_parse(output)
        if parsed is None:
            return False, None, "JSON parse error: could not extract valid JSON from output"

        # Step 2: validate against schema (skip if jsonschema unavailable)
        if _jsonschema is None:
            logger.debug("jsonschema not installed -- schema validation skipped")
            return True, parsed, None

        try:
            _jsonschema.validate(instance=parsed, schema=self._schema)
        except _jsonschema.ValidationError as exc:
            return False, None, f"Schema validation error: {exc.message}"
        except _jsonschema.SchemaError as exc:
            # Bad schema is a programming error but should not crash the pipeline
            logger.warning("Invalid JSON Schema provided: %s", exc.message)
            return True, parsed, None

        return True, parsed, None

    # ------------------------------------------------------------------
    @staticmethod
    def _try_parse(output: str) -> Optional[Dict[str, Any]]:
        """Attempt to parse *output* as JSON, with fence-extraction fallback."""
        text = output.strip()

        # Try raw JSON first
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                return data
        except (json.JSONDecodeError, ValueError):
            pass

        # Try extracting from markdown fence
        m = _FENCED_JSON_RE.search(text)
        if m:
            try:
                data = json.loads(m.group(1))
                if isinstance(data, dict):
                    return data
            except (json.JSONDecodeError, ValueError):
                pass

        return None


# ── FailureClassifier ──────────────────────────────────────────────────────


class FailureClassifier:
    """Classify an LLM call failure into an actionable category.

    Categories:
        ``"schema_error"``     -- output did not match expected schema/format.
        ``"content_error"``    -- content-level issue (hallucination, policy).
        ``"timeout_error"``    -- call timed out.
        ``"rate_limit_error"`` -- provider rate limit hit.
        ``"unknown_error"``    -- none of the above matched.
    """

    # Keywords/patterns mapped to failure classes (checked in order)
    _PATTERNS: List[Tuple[str, re.Pattern[str]]] = [
        ("timeout_error", re.compile(r"timeout|timed?\s*out|deadline\s*exceeded", re.IGNORECASE)),
        ("rate_limit_error", re.compile(r"rate.?limit|429|too\s*many\s*requests|quota", re.IGNORECASE)),
        ("schema_error", re.compile(
            r"schema|json|parse|decode|validation\s*error|missing\s*required|"
            r"invalid\s*type|unexpected\s*token",
            re.IGNORECASE,
        )),
        ("content_error", re.compile(
            r"hallucin|policy|content.?filter|unsafe|blocked|refus|inappropriate",
            re.IGNORECASE,
        )),
    ]

    def classify(self, error: str, output: str = "") -> str:
        """Return the failure class for the given *error* string.

        Also inspects *output* for schema-level issues (e.g. non-JSON when
        JSON was expected).

        Args:
            error:  The error/exception message.
            output: The raw LLM output (may be empty on timeout).

        Returns:
            One of ``"schema_error"``, ``"content_error"``,
            ``"timeout_error"``, ``"rate_limit_error"``, ``"unknown_error"``.
        """
        combined = f"{error} {output}"
        for cls, pattern in self._PATTERNS:
            if pattern.search(combined):
                return cls
        return "unknown_error"


# ── RetryStrategy ──────────────────────────────────────────────────────────


@dataclass(frozen=True)
class RetryStrategy:
    """Decide whether to retry an LLM call based on failure class and attempt.

    Attributes:
        max_retries:  Maximum number of retry attempts (0 = no retries).
        retry_on:     Set of failure classes that should be retried.
        escalate_on:  Set of failure classes that should be escalated (no retry).
    """

    max_retries: int = 2
    retry_on: FrozenSet[str] = frozenset({"schema_error", "timeout_error", "rate_limit_error"})
    escalate_on: FrozenSet[str] = frozenset({"content_error"})

    def should_retry(self, failure_class: str, attempt: int) -> bool:
        """Return ``True`` if the call should be retried.

        Args:
            failure_class: The classified failure type.
            attempt:       Current attempt number (0-based; 0 = first try).

        Returns:
            ``True`` if a retry is appropriate.
        """
        if failure_class in self.escalate_on:
            return False
        if attempt >= self.max_retries:
            return False
        return failure_class in self.retry_on


# ── RuleChecklist ──────────────────────────────────────────────────────────


_MAX_RULES = 10


@dataclass
class RuleChecklist:
    """A bounded list of rules for injection into LLM prompts.

    Attributes:
        rules:     List of rule strings (max ``MAX_RULES``).
        MAX_RULES: Hard upper limit per micro-task (class-level constant).
    """

    rules: List[str] = field(default_factory=list)
    MAX_RULES: int = field(default=_MAX_RULES, init=False, repr=False)

    def __post_init__(self) -> None:
        if len(self.rules) > self.MAX_RULES:
            logger.warning(
                "RuleChecklist truncated from %d to %d rules",
                len(self.rules), self.MAX_RULES,
            )
            self.rules = self.rules[: self.MAX_RULES]

    def format_for_prompt(self) -> str:
        """Format the rules as a numbered checklist for LLM prompt injection.

        Returns:
            A multiline string like::

                RULES CHECKLIST (you MUST follow all):
                1. Rule one
                2. Rule two
                ...

            Returns an empty string if there are no rules.
        """
        if not self.rules:
            return ""
        lines = ["RULES CHECKLIST (you MUST follow all):"]
        for i, rule in enumerate(self.rules, 1):
            lines.append(f"{i}. {rule}")
        return "\n".join(lines)
