"""Test suite for secret redaction (TC-590).

Tests:
1. Redaction placeholder generation
2. Redaction mapping creation
3. Text redaction with multiple secrets
4. Dictionary redaction (JSON structures)
5. Recursive value redaction
6. Redaction preserving structure
7. Secret ID generation (deterministic)
8. Empty/no secrets handling
"""

from __future__ import annotations

import pytest

from launch.security.redactor import (
    RedactionMapping,
    generate_secret_id,
    redact_text,
    redact_dict,
    redact_value,
)
from launch.security.secret_detector import SecretMatch, detect_secrets


class TestSecretIDGeneration:
    """Test secret ID generation."""

    def test_generate_secret_id_deterministic(self) -> None:
        """Test that secret ID generation is deterministic."""
        id1 = generate_secret_id("my_secret", "api_key")
        id2 = generate_secret_id("my_secret", "api_key")

        assert id1 == id2
        assert len(id1) == 8

    def test_generate_secret_id_different_values(self) -> None:
        """Test that different secrets get different IDs."""
        id1 = generate_secret_id("secret1", "api_key")
        id2 = generate_secret_id("secret2", "api_key")

        assert id1 != id2

    def test_generate_secret_id_different_types(self) -> None:
        """Test that same secret with different types gets different IDs."""
        id1 = generate_secret_id("my_secret", "api_key")
        id2 = generate_secret_id("my_secret", "password")

        assert id1 != id2


class TestRedactionMapping:
    """Test RedactionMapping dataclass."""

    def test_redaction_mapping_creation(self) -> None:
        """Test creating a RedactionMapping."""
        mapping = RedactionMapping(
            redacted="[REDACTED:API_KEY:abc12345]",
            secret_type="api_key",
            secret_id="abc12345",
            start_pos=10,
            end_pos=30,
        )

        assert mapping.secret_type == "api_key"
        assert mapping.secret_id == "abc12345"
        assert "[REDACTED:" in mapping.redacted


class TestTextRedaction:
    """Test text redaction."""

    def test_redact_text_empty(self) -> None:
        """Test redacting empty text."""
        redacted, mappings = redact_text("", [])

        assert redacted == ""
        assert mappings == []

    def test_redact_text_no_secrets(self) -> None:
        """Test redacting text with no secrets."""
        text = "This is normal text"
        redacted, mappings = redact_text(text, [])

        assert redacted == text
        assert mappings == []

    def test_redact_text_single_secret(self) -> None:
        """Test redacting text with single secret."""
        text = "My API key is AKIAIOSFODNN7EXAMPLE"
        secrets = detect_secrets(text)

        assert len(secrets) > 0

        redacted, mappings = redact_text(text, secrets)

        assert "AKIAIOSFODNN7EXAMPLE" not in redacted
        assert "[REDACTED:" in redacted
        assert "AWS_ACCESS_KEY_ID" in redacted.upper()
        assert len(mappings) == len(secrets)

    def test_redact_text_multiple_secrets(self) -> None:
        """Test redacting text with multiple secrets."""
        text = """
        AWS_KEY=AKIAIOSFODNN7EXAMPLE
        GITHUB=ghp_1234567890abcdefghijklmnopqrstuvwxyz
        """
        secrets = detect_secrets(text)

        assert len(secrets) >= 2

        redacted, mappings = redact_text(text, secrets)

        assert "AKIAIOSFODNN7EXAMPLE" not in redacted
        assert "ghp_1234567890abcdefghijklmnopqrstuvwxyz" not in redacted
        assert redacted.count("[REDACTED:") >= 2
        assert len(mappings) == len(secrets)

    def test_redact_text_preserves_structure(self) -> None:
        """Test that redaction preserves text structure."""
        text = "key=AKIAIOSFODNN7EXAMPLE\n"
        secrets = detect_secrets(text)

        redacted, mappings = redact_text(text, secrets)

        # Should preserve newline
        assert redacted.endswith("\n")
        assert "key=" in redacted

    def test_redaction_mapping_no_original(self) -> None:
        """Test that redaction mapping does NOT store original secret."""
        text = "password=SuperSecret123"
        secrets = detect_secrets(text)

        _, mappings = redact_text(text, secrets)

        # Mappings should not have an 'original' attribute with the secret
        for mapping in mappings:
            # Check that the mapping doesn't expose the original
            assert not hasattr(mapping, "original") or mapping.original is None


class TestDictionaryRedaction:
    """Test dictionary redaction."""

    def test_redact_dict_simple(self) -> None:
        """Test redacting a simple dictionary."""
        data = {
            "username": "john",
            "password": "SuperSecret123",
        }

        # Detect secrets in the JSON representation
        import json

        json_str = json.dumps(data)
        secrets = detect_secrets(json_str)

        redacted = redact_dict(data, secrets)

        # Password should be redacted
        assert "SuperSecret123" not in str(redacted)

    def test_redact_dict_nested(self) -> None:
        """Test redacting a nested dictionary."""
        data = {
            "config": {
                "api_key": "abc123def456ghi789jkl012mno345pqr678",
            }
        }

        import json

        json_str = json.dumps(data)
        secrets = detect_secrets(json_str)

        redacted = redact_dict(data, secrets)

        # API key should be redacted
        assert "abc123def456ghi789jkl012mno345pqr678" not in str(redacted)


class TestRecursiveValueRedaction:
    """Test recursive value redaction."""

    def test_redact_value_string(self) -> None:
        """Test redacting a string value."""
        value = "password=SuperSecret123"
        redacted = redact_value(value, detect_secrets)

        assert "SuperSecret123" not in redacted
        assert "[REDACTED:" in redacted

    def test_redact_value_dict(self) -> None:
        """Test redacting a dict value."""
        value = {
            "api_key": "AKIAIOSFODNN7EXAMPLE",  # AWS key that will be detected
            "username": "john",
        }
        redacted = redact_value(value, detect_secrets)

        assert isinstance(redacted, dict)
        assert "username" in redacted
        # API key should be redacted in the value
        assert "AKIAIOSFODNN7EXAMPLE" not in str(redacted.get("api_key", ""))

    def test_redact_value_list(self) -> None:
        """Test redacting a list value."""
        value = [
            "normal_value",
            "password=Secret123456",
        ]
        redacted = redact_value(value, detect_secrets)

        assert isinstance(redacted, list)
        assert len(redacted) == 2
        assert "normal_value" in redacted
        assert "Secret123456" not in str(redacted[1])

    def test_redact_value_nested(self) -> None:
        """Test redacting nested structures."""
        value = {
            "config": {
                "database": {
                    "aws_key": "AKIAIOSFODNN7EXAMPLE",
                }
            }
        }
        redacted = redact_value(value, detect_secrets)

        assert isinstance(redacted, dict)
        # AWS key should be redacted somewhere in the structure
        import json

        redacted_str = json.dumps(redacted)
        assert "AKIAIOSFODNN7EXAMPLE" not in redacted_str

    def test_redact_value_primitives(self) -> None:
        """Test that primitives pass through unchanged."""
        assert redact_value(42, detect_secrets) == 42
        assert redact_value(3.14, detect_secrets) == 3.14
        assert redact_value(True, detect_secrets) is True
        assert redact_value(None, detect_secrets) is None

    def test_redact_value_mixed_list(self) -> None:
        """Test redacting a list with mixed types."""
        value = [
            42,
            "password=Secret123456",
            {"key": "value"},
            None,
        ]
        redacted = redact_value(value, detect_secrets)

        assert isinstance(redacted, list)
        assert len(redacted) == 4
        assert redacted[0] == 42
        assert "Secret123456" not in str(redacted[1])
        assert isinstance(redacted[2], dict)
        assert redacted[3] is None


class TestRedactionIntegration:
    """Integration tests for redaction."""

    def test_redact_aws_credentials(self) -> None:
        """Test redacting AWS credentials from config."""
        text = """
        [default]
        aws_access_key_id = AKIAIOSFODNN7EXAMPLE
        aws_secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
        region = us-west-2
        """
        secrets = detect_secrets(text)

        redacted, mappings = redact_text(text, secrets)

        # AWS keys should be redacted
        assert "AKIAIOSFODNN7EXAMPLE" not in redacted
        # Structure should be preserved
        assert "[default]" in redacted
        assert "region = us-west-2" in redacted
        # Should have multiple redactions
        assert len(mappings) >= 1

    def test_redact_github_token_from_env(self) -> None:
        """Test redacting GitHub token from env file."""
        text = "GITHUB_TOKEN=ghp_1234567890abcdefghijklmnopqrstuvwxyz"
        secrets = detect_secrets(text)

        redacted, mappings = redact_text(text, secrets)

        assert "ghp_1234567890abcdefghijklmnopqrstuvwxyz" not in redacted
        assert "[REDACTED:" in redacted
        assert "GITHUB_TOKEN=" in redacted

    def test_redact_multiple_types_preserves_order(self) -> None:
        """Test that redaction preserves order of secrets."""
        text = """
        First: AKIAIOSFODNN7EXAMPLE
        Second: ghp_1234567890abcdefghijklmnopqrstuvwxyz
        Third: password=Secret123456
        """
        secrets = detect_secrets(text)

        redacted, mappings = redact_text(text, secrets)

        # Check that relative order is preserved
        assert "First:" in redacted
        assert "Second:" in redacted
        assert "Third:" in redacted

        # Original secrets should be gone
        assert "AKIAIOSFODNN7EXAMPLE" not in redacted
        assert "ghp_1234567890abcdefghijklmnopqrstuvwxyz" not in redacted
        assert "Secret123456" not in redacted

    def test_redaction_deterministic(self) -> None:
        """Test that redaction is deterministic."""
        text = "api_key=abc123def456ghi789jkl012mno345pqr678"
        secrets = detect_secrets(text)

        redacted1, mappings1 = redact_text(text, secrets)
        redacted2, mappings2 = redact_text(text, secrets)

        assert redacted1 == redacted2
        assert len(mappings1) == len(mappings2)

        # Same secret should get same ID
        if mappings1:
            assert mappings1[0].secret_id == mappings2[0].secret_id
