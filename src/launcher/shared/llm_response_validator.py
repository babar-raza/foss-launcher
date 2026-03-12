"""LLM response validation — JSON parseability, array structure, element type keys."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ValidationResult:
    """Result of LLM response validation."""
    is_valid: bool = True
    issues: list[str] = field(default_factory=list)

    @property
    def errors(self) -> list[str]:
        """Alias for issues — backward compatibility with llm_provider.py."""
        return self.issues


def validate_llm_response(response: str, **kwargs: Any) -> ValidationResult:
    """Validate an LLM response according to the expected content_type.

    content_type (passed via kwargs, default "json_array"):
      "markdown"   — no structural validation; always valid (caller owns parsing)
      "json_object"— Layer 1 (parseable JSON) + Layer 2 (top-level dict)
      "json_array" — Three-layer check:
                       1. JSON parseable
                       2. Top-level value is a list
                       3. Every element has a "type" key
    """
    content_type: str = kwargs.get("content_type", "json_array")

    # Markdown: no structural validation required — caller owns parsing
    if content_type == "markdown":
        return ValidationResult(is_valid=True)

    # Layer 1: JSON parseability (required for json_object and json_array)
    try:
        parsed = json.loads(response)
    except (json.JSONDecodeError, ValueError) as exc:
        return ValidationResult(is_valid=False, issues=[f"Not valid JSON: {exc}"])

    if content_type == "json_object":
        # Layer 2: must be a dict
        if not isinstance(parsed, dict):
            return ValidationResult(
                is_valid=False,
                issues=[f"Expected JSON object, got {type(parsed).__name__}"],
            )
        return ValidationResult(is_valid=True)

    # json_array (default) — original three-layer check
    # Layer 2: must be a list
    if not isinstance(parsed, list):
        return ValidationResult(
            is_valid=False,
            issues=[f"Expected JSON array, got {type(parsed).__name__}"],
        )

    # Layer 3: each element must have 'type' key
    issues: list[str] = []
    for i, element in enumerate(parsed):
        if not isinstance(element, dict) or "type" not in element:
            issues.append(f"Element {i} missing 'type' key")

    return ValidationResult(is_valid=len(issues) == 0, issues=issues)


def enhance_prompt_for_retry(
    prompt: str, issues: "list[str] | ValidationResult", **kwargs: Any
) -> str:
    """Prepend a CRITICAL validation failure notice to the retry prompt.

    Placed BEFORE the main prompt so the model reads the correction before any
    content — more effective than appending to a long prompt.

    *issues* may be a list of strings or a ``ValidationResult`` instance
    (backward-compatible with callers that pass the whole result object).
    """
    if isinstance(issues, ValidationResult):
        issues = issues.issues
    if not issues:
        return prompt
    issue_text = "\n".join(f"- {issue}" for issue in issues)
    notice = (
        "CRITICAL — YOUR PREVIOUS RESPONSE FAILED VALIDATION:\n"
        f"{issue_text}\n"
        "You MUST return a valid JSON array where EVERY element has a \"type\" key.\n"
        "Valid type values: paragraph, code, list, heading, table, callout.\n"
        "Example: [{\"type\": \"paragraph\", \"content\": \"...\", \"claim_ids\": []}]\n"
        "\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\n\n"
    )
    return notice + prompt
