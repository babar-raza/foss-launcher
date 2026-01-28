"""Secret redaction with placeholder generation.

Binding contract: specs/34_strict_compliance_guarantees.md (security requirements)

Provides:
1. Text redaction with placeholder generation
2. Structured data redaction (JSON, YAML)
3. Redaction mapping for audit purposes (one-way only)
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from .secret_detector import SecretMatch


@dataclass
class RedactionMapping:
    """Mapping of original secret to redacted placeholder.

    Note: Original secret is NOT stored (one-way only for security).
    """

    redacted: str
    secret_type: str
    secret_id: str  # Unique identifier for this secret
    start_pos: int  # Position in original text
    end_pos: int  # Position in original text


def generate_secret_id(secret_value: str, secret_type: str) -> str:
    """Generate deterministic unique ID for a secret.

    Uses SHA256 hash (first 8 chars) for determinism without storing original.

    Args:
        secret_value: The secret value
        secret_type: Type of secret

    Returns:
        Unique identifier (8 chars)
    """
    # Use deterministic hash
    hash_input = f"{secret_type}:{secret_value}"
    hash_digest = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()
    return hash_digest[:8]


def redact_text(text: str, secrets: List[SecretMatch]) -> Tuple[str, List[RedactionMapping]]:
    """Redact secrets from text with placeholder generation.

    Args:
        text: Original text
        secrets: List of detected secrets to redact

    Returns:
        Tuple of (redacted_text, redaction_mappings)
    """
    if not secrets:
        return text, []

    # Sort secrets by position (reverse order to maintain positions)
    sorted_secrets = sorted(secrets, key=lambda s: s.start_pos, reverse=True)

    mappings: List[RedactionMapping] = []
    redacted_text = text

    for secret in sorted_secrets:
        # Generate placeholder
        secret_id = generate_secret_id(secret.value, secret.secret_type)
        placeholder = f"[REDACTED:{secret.secret_type.upper()}:{secret_id}]"

        # Replace in text
        redacted_text = (
            redacted_text[: secret.start_pos] + placeholder + redacted_text[secret.end_pos :]
        )

        # Record mapping (without original value for security)
        mapping = RedactionMapping(
            redacted=placeholder,
            secret_type=secret.secret_type,
            secret_id=secret_id,
            start_pos=secret.start_pos,
            end_pos=secret.end_pos,
        )
        mappings.append(mapping)

    # Reverse mappings to get original order
    mappings.reverse()

    return redacted_text, mappings


def redact_dict(data: Dict[str, Any], secrets: List[SecretMatch]) -> Dict[str, Any]:
    """Redact secrets from dictionary recursively.

    Args:
        data: Dictionary to redact
        secrets: List of detected secrets

    Returns:
        Redacted dictionary
    """
    # Convert to JSON and back for consistent handling
    json_str = json.dumps(data, indent=2, sort_keys=True)
    redacted_str, _ = redact_text(json_str, secrets)

    try:
        return json.loads(redacted_str)
    except json.JSONDecodeError:
        # If redaction broke JSON structure, return original with warning
        return {"error": "Redaction failed to preserve JSON structure", "original_keys": list(data.keys())}


def redact_value(value: Any, secret_detector_func) -> Any:
    """Recursively redact secrets from a value.

    Args:
        value: Value to redact (can be dict, list, str, or primitive)
        secret_detector_func: Function to detect secrets (signature: str -> List[SecretMatch])

    Returns:
        Redacted value
    """
    if isinstance(value, dict):
        return {k: redact_value(v, secret_detector_func) for k, v in value.items()}
    elif isinstance(value, list):
        return [redact_value(item, secret_detector_func) for item in value]
    elif isinstance(value, str):
        secrets = secret_detector_func(value)
        if secrets:
            redacted, _ = redact_text(value, secrets)
            return redacted
        return value
    else:
        # Primitives (int, float, bool, None) pass through
        return value
