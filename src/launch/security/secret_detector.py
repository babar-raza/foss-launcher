"""Secret detection with pattern matching and entropy calculation.

Binding contract: specs/34_strict_compliance_guarantees.md (security requirements)

Detects:
1. AWS keys (access key ID, secret access key)
2. GitHub tokens (personal access tokens, OAuth tokens)
3. Generic API keys
4. Private keys (RSA, EC)
5. Passwords in code
6. High entropy strings (base64, hex)
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import List


@dataclass
class SecretMatch:
    """A detected secret."""

    secret_type: str  # "api_key", "password", "private_key", etc.
    value: str
    start_pos: int
    end_pos: int
    line_number: int
    context: str  # Surrounding text (redacted)
    confidence: float  # 0.0-1.0

    def __post_init__(self) -> None:
        """Validate confidence is in range."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be 0.0-1.0, got {self.confidence}")


# Secret detection patterns (ordered by specificity)
PATTERNS = [
    # AWS Access Key ID (very specific pattern)
    (
        r"\b(AKIA[0-9A-Z]{16})\b",
        "aws_access_key_id",
        1.0,
    ),
    # GitHub Personal Access Token (classic)
    (
        r"\b(ghp_[a-zA-Z0-9]{36})\b",
        "github_token",
        1.0,
    ),
    # GitHub OAuth Token
    (
        r"\b(gho_[a-zA-Z0-9]{36})\b",
        "github_oauth_token",
        1.0,
    ),
    # GitHub App Token
    (
        r"\b(ghs_[a-zA-Z0-9]{36})\b",
        "github_app_token",
        1.0,
    ),
    # GitHub Refresh Token
    (
        r"\b(ghr_[a-zA-Z0-9]{36})\b",
        "github_refresh_token",
        1.0,
    ),
    # Private keys (RSA, EC, etc.)
    (
        r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
        "private_key",
        1.0,
    ),
    # Generic API key patterns (case insensitive)
    (
        r"(?i)(api[_-]?key|apikey)[\"\s:=]+['\"]?([a-zA-Z0-9_\-]{20,})['\"]?",
        "api_key",
        0.8,
    ),
    # Password in code (case insensitive)
    (
        r"(?i)(password|passwd|pwd)[\"\s:=]+['\"]?([^\s\"']{8,})['\"]?",
        "password",
        0.7,
    ),
    # AWS Secret Access Key (entropy-based, need validation)
    (
        r"\b([A-Za-z0-9/+=]{40})\b",
        "aws_secret_key",
        0.6,  # Lower confidence, needs entropy check
    ),
]


def calculate_entropy(data: str) -> float:
    """Calculate Shannon entropy of a string.

    Args:
        data: String to calculate entropy for

    Returns:
        Shannon entropy (bits per character)
    """
    if not data:
        return 0.0

    # Count character frequencies
    freq: dict[str, int] = {}
    for char in data:
        freq[char] = freq.get(char, 0) + 1

    # Calculate entropy
    entropy = 0.0
    length = len(data)
    for count in freq.values():
        probability = count / length
        entropy -= probability * math.log2(probability)

    return entropy


def is_high_entropy(value: str, charset: str = "base64") -> bool:
    """Check if a string has high entropy (likely a secret).

    Args:
        value: String to check
        charset: Expected character set ("base64" or "hex")

    Returns:
        True if high entropy, False otherwise
    """
    if charset == "base64":
        # Base64: expect entropy > 4.0 bits/char, length >= 20
        return len(value) >= 20 and calculate_entropy(value) > 4.0
    elif charset == "hex":
        # Hex: expect entropy > 3.5 bits/char, length >= 32
        return len(value) >= 32 and calculate_entropy(value) > 3.5
    return False


def is_likely_false_positive(value: str) -> bool:
    """Check if a detected value is likely a false positive.

    Args:
        value: Detected value

    Returns:
        True if likely false positive, False otherwise
    """
    # Common false positives
    false_positive_patterns = [
        (r"^https?://", re.IGNORECASE),  # URLs
        (r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE),  # UUIDs
        (r"^[A-Z_]{3,}$", 0),  # ALL_CAPS constants (case sensitive!)
        (r"^(password|passwd|pwd|api[_-]?key|apikey)$", re.IGNORECASE),  # Just the keyword itself
        (r"^\*+$", 0),  # Just asterisks (already redacted)
        (r"^\[REDACTED", 0),  # Already redacted
    ]

    for pattern, flags in false_positive_patterns:
        if re.match(pattern, value, flags):
            return True

    return False


def get_line_number(text: str, pos: int) -> int:
    """Get line number for a position in text.

    Args:
        text: Full text
        pos: Character position

    Returns:
        Line number (1-indexed)
    """
    return text[:pos].count("\n") + 1


def get_context(text: str, start: int, end: int, context_chars: int = 20) -> str:
    """Get surrounding context for a match (with secret redacted).

    Args:
        text: Full text
        start: Start position of match
        end: End position of match
        context_chars: Number of characters to include before/after

    Returns:
        Context string with secret redacted
    """
    # Get before and after context
    before = text[max(0, start - context_chars) : start]
    after = text[end : min(len(text), end + context_chars)]
    secret_placeholder = "***"

    # Clean up newlines
    before = before.replace("\n", "\\n")
    after = after.replace("\n", "\\n")

    return f"{before}{secret_placeholder}{after}"


def detect_secrets(text: str) -> List[SecretMatch]:
    """Detect secrets in text using pattern matching and entropy analysis.

    Args:
        text: Text to scan for secrets

    Returns:
        List of detected secrets
    """
    matches: List[SecretMatch] = []
    seen_positions: set[tuple[int, int]] = set()

    for pattern, secret_type, base_confidence in PATTERNS:
        for match in re.finditer(pattern, text):
            # Extract the actual secret value (might be in a group)
            if match.lastindex and match.lastindex > 0:
                # If there are groups, use the last group (the value)
                value = match.group(match.lastindex)
                # Find the actual position of this group
                start_pos = match.start(match.lastindex)
                end_pos = match.end(match.lastindex)
            else:
                value = match.group(0)
                start_pos = match.start()
                end_pos = match.end()

            # Skip if we've already matched this position
            if (start_pos, end_pos) in seen_positions:
                continue

            # Skip false positives
            if is_likely_false_positive(value):
                continue

            # Adjust confidence based on entropy for certain types
            confidence = base_confidence
            if secret_type in ("aws_secret_key", "api_key"):
                if not is_high_entropy(value):
                    continue  # Skip low entropy matches for these types
                # Boost confidence for high entropy
                confidence = min(1.0, confidence + 0.2)

            # Create match
            secret_match = SecretMatch(
                secret_type=secret_type,
                value=value,
                start_pos=start_pos,
                end_pos=end_pos,
                line_number=get_line_number(text, start_pos),
                context=get_context(text, start_pos, end_pos),
                confidence=confidence,
            )

            matches.append(secret_match)
            seen_positions.add((start_pos, end_pos))

    # Sort by position for deterministic ordering
    matches.sort(key=lambda m: (m.start_pos, m.end_pos))

    return matches
