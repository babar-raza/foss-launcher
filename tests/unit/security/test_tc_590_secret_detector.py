"""Test suite for secret detection (TC-590).

Tests:
1. AWS key detection (access key ID, secret access key)
2. GitHub token detection (personal, OAuth, app, refresh)
3. Generic API key detection
4. Private key detection (RSA, EC)
5. Password detection in various contexts
6. High entropy string detection (base64, hex)
7. False positive avoidance (URLs, UUIDs)
8. Entropy calculation
9. Context extraction
10. Line number tracking
"""

from __future__ import annotations

import pytest

from launch.security.secret_detector import (
    SecretMatch,
    detect_secrets,
    calculate_entropy,
    is_high_entropy,
    is_likely_false_positive,
    get_line_number,
    get_context,
)


class TestEntropyCalculation:
    """Test entropy calculation functions."""

    def test_entropy_empty_string(self) -> None:
        """Test entropy of empty string."""
        assert calculate_entropy("") == 0.0

    def test_entropy_single_char(self) -> None:
        """Test entropy of single repeated character."""
        entropy = calculate_entropy("aaaa")
        assert entropy == 0.0  # No variation

    def test_entropy_uniform_distribution(self) -> None:
        """Test entropy of uniform distribution."""
        # "abcd" has max entropy for 4 chars
        entropy = calculate_entropy("abcd")
        assert entropy == 2.0  # log2(4) = 2.0

    def test_entropy_base64_string(self) -> None:
        """Test entropy of typical base64 string."""
        base64_str = "SGVsbG8gV29ybGQhIFRoaXMgaXMgYSB0ZXN0"
        entropy = calculate_entropy(base64_str)
        assert entropy > 4.0  # Base64 should have high entropy

    def test_is_high_entropy_base64(self) -> None:
        """Test high entropy detection for base64."""
        # Too short
        assert not is_high_entropy("short", charset="base64")

        # High entropy, long enough
        assert is_high_entropy("SGVsbG8gV29ybGQhIFRoaXMgaXMgYSB0ZXN0", charset="base64")

        # Low entropy, long enough
        assert not is_high_entropy("aaaaaaaaaaaaaaaaaaaaaa", charset="base64")

    def test_is_high_entropy_hex(self) -> None:
        """Test high entropy detection for hex."""
        # Too short
        assert not is_high_entropy("abcd1234", charset="hex")

        # High entropy, long enough
        assert is_high_entropy("a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6", charset="hex")

        # Low entropy, long enough
        assert not is_high_entropy("00000000000000000000000000000000", charset="hex")


class TestFalsePositiveDetection:
    """Test false positive filtering."""

    def test_urls_are_false_positives(self) -> None:
        """Test that URLs are flagged as false positives."""
        assert is_likely_false_positive("https://example.com/api/key")
        assert is_likely_false_positive("http://example.com")

    def test_uuids_are_false_positives(self) -> None:
        """Test that UUIDs are flagged as false positives."""
        assert is_likely_false_positive("550e8400-e29b-41d4-a716-446655440000")

    def test_all_caps_constants_are_false_positives(self) -> None:
        """Test that ALL_CAPS constants are flagged as false positives."""
        assert is_likely_false_positive("API_KEY")
        assert is_likely_false_positive("PASSWORD")

    def test_keywords_alone_are_false_positives(self) -> None:
        """Test that keywords alone are flagged as false positives."""
        assert is_likely_false_positive("password")
        assert is_likely_false_positive("api_key")

    def test_short_values_not_false_positives(self) -> None:
        """Test that reasonable length values are not automatically filtered."""
        # We don't want to be overly aggressive with filtering
        # Real secrets can appear in test code
        assert not is_likely_false_positive("example_key_12345")
        assert not is_likely_false_positive("test_password")
        assert not is_likely_false_positive("dummy_token")

    def test_already_redacted_are_false_positives(self) -> None:
        """Test that already redacted values are flagged as false positives."""
        assert is_likely_false_positive("********")
        assert is_likely_false_positive("[REDACTED:API_KEY:abc123]")

    def test_real_secrets_are_not_false_positives(self) -> None:
        """Test that real secrets are not flagged as false positives."""
        assert not is_likely_false_positive("AKIAIOSFODNN7EXAMPLE")
        assert not is_likely_false_positive("ghp_1234567890abcdefghijklmnopqrstuvwx")


class TestContextExtraction:
    """Test context extraction."""

    def test_get_line_number(self) -> None:
        """Test line number extraction."""
        text = "line 1\nline 2\nline 3"
        assert get_line_number(text, 0) == 1
        assert get_line_number(text, 7) == 2  # Start of "line 2"
        assert get_line_number(text, 14) == 3  # Start of "line 3"

    def test_get_context(self) -> None:
        """Test context extraction."""
        text = "The password is 'secret123' in the config file"
        start = text.index("secret123")
        end = start + len("secret123")

        context = get_context(text, start, end, context_chars=15)
        assert "password" in context
        assert "***" in context
        assert "secret123" not in context  # Should be redacted

    def test_get_context_with_newlines(self) -> None:
        """Test context extraction with newlines."""
        text = "line 1\npassword=secret\nline 3"
        start = text.index("secret")
        end = start + len("secret")

        context = get_context(text, start, end, context_chars=5)
        assert "\\n" in context  # Newlines escaped


class TestAWSKeyDetection:
    """Test AWS key detection."""

    def test_detect_aws_access_key_id(self) -> None:
        """Test AWS access key ID detection."""
        text = "AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE"
        secrets = detect_secrets(text)

        assert len(secrets) == 1
        assert secrets[0].secret_type == "aws_access_key_id"
        assert secrets[0].value == "AKIAIOSFODNN7EXAMPLE"
        assert secrets[0].confidence == 1.0

    def test_detect_multiple_aws_keys(self) -> None:
        """Test detection of multiple AWS keys."""
        text = """
        AKIA1234567890ABCDEF
        AKIA9876543210ZYXWVU
        """
        secrets = detect_secrets(text)

        assert len(secrets) == 2
        assert all(s.secret_type == "aws_access_key_id" for s in secrets)

    def test_aws_key_not_detected_incomplete(self) -> None:
        """Test that incomplete AWS keys are not detected."""
        text = "AKIA123"  # Too short
        secrets = detect_secrets(text)

        assert len(secrets) == 0


class TestGitHubTokenDetection:
    """Test GitHub token detection."""

    def test_detect_github_personal_token(self) -> None:
        """Test GitHub personal access token detection."""
        text = "GITHUB_TOKEN=ghp_1234567890abcdefghijklmnopqrstuvwxyz"
        secrets = detect_secrets(text)

        assert len(secrets) == 1
        assert secrets[0].secret_type == "github_token"
        assert secrets[0].value.startswith("ghp_")
        assert secrets[0].confidence == 1.0

    def test_detect_github_oauth_token(self) -> None:
        """Test GitHub OAuth token detection."""
        text = "token=gho_1234567890abcdefghijklmnopqrstuvwxyz"
        secrets = detect_secrets(text)

        assert len(secrets) == 1
        assert secrets[0].secret_type == "github_oauth_token"
        assert secrets[0].value.startswith("gho_")

    def test_detect_github_app_token(self) -> None:
        """Test GitHub app token detection."""
        text = "ghs_1234567890abcdefghijklmnopqrstuvwxyz"
        secrets = detect_secrets(text)

        assert len(secrets) == 1
        assert secrets[0].secret_type == "github_app_token"

    def test_detect_github_refresh_token(self) -> None:
        """Test GitHub refresh token detection."""
        text = "ghr_1234567890abcdefghijklmnopqrstuvwxyz"
        secrets = detect_secrets(text)

        assert len(secrets) == 1
        assert secrets[0].secret_type == "github_refresh_token"


class TestPrivateKeyDetection:
    """Test private key detection."""

    def test_detect_rsa_private_key(self) -> None:
        """Test RSA private key detection."""
        text = "-----BEGIN RSA PRIVATE KEY-----"
        secrets = detect_secrets(text)

        assert len(secrets) == 1
        assert secrets[0].secret_type == "private_key"
        assert secrets[0].confidence == 1.0

    def test_detect_ec_private_key(self) -> None:
        """Test EC private key detection."""
        text = "-----BEGIN EC PRIVATE KEY-----"
        secrets = detect_secrets(text)

        assert len(secrets) == 1
        assert secrets[0].secret_type == "private_key"

    def test_detect_openssh_private_key(self) -> None:
        """Test OpenSSH private key detection."""
        text = "-----BEGIN OPENSSH PRIVATE KEY-----"
        secrets = detect_secrets(text)

        assert len(secrets) == 1
        assert secrets[0].secret_type == "private_key"

    def test_detect_generic_private_key(self) -> None:
        """Test generic private key detection."""
        text = "-----BEGIN PRIVATE KEY-----"
        secrets = detect_secrets(text)

        assert len(secrets) == 1
        assert secrets[0].secret_type == "private_key"


class TestAPIKeyDetection:
    """Test generic API key detection."""

    def test_detect_api_key_underscore(self) -> None:
        """Test API key with underscore."""
        text = "api_key = abc123def456ghi789jkl012mno345"
        secrets = detect_secrets(text)

        # Should detect the API key value
        api_keys = [s for s in secrets if s.secret_type == "api_key"]
        assert len(api_keys) >= 1
        assert any("abc123def456ghi789jkl012mno345" in s.value for s in api_keys)

    def test_detect_apikey_no_separator(self) -> None:
        """Test apikey without separator."""
        text = "apikey: xyz789abc456def123ghi890jkl567"
        secrets = detect_secrets(text)

        api_keys = [s for s in secrets if s.secret_type == "api_key"]
        assert len(api_keys) >= 1

    def test_api_key_case_insensitive(self) -> None:
        """Test API key detection is case insensitive."""
        text = "API_KEY = abc123def456ghi789jkl012mno345"
        secrets = detect_secrets(text)

        api_keys = [s for s in secrets if s.secret_type == "api_key"]
        assert len(api_keys) >= 1

    def test_api_key_with_quotes(self) -> None:
        """Test API key with quotes."""
        text = 'api_key="abc123def456ghi789jkl012mno345"'
        secrets = detect_secrets(text)

        api_keys = [s for s in secrets if s.secret_type == "api_key"]
        assert len(api_keys) >= 1


class TestPasswordDetection:
    """Test password detection."""

    def test_detect_password(self) -> None:
        """Test password detection."""
        text = "password = MyP@ssw0rd123"
        secrets = detect_secrets(text)

        passwords = [s for s in secrets if s.secret_type == "password"]
        assert len(passwords) >= 1

    def test_detect_passwd(self) -> None:
        """Test passwd detection."""
        text = "passwd: secret123456"
        secrets = detect_secrets(text)

        passwords = [s for s in secrets if s.secret_type == "password"]
        assert len(passwords) >= 1

    def test_detect_pwd(self) -> None:
        """Test pwd detection."""
        text = "pwd=SuperSecret99"
        secrets = detect_secrets(text)

        passwords = [s for s in secrets if s.secret_type == "password"]
        assert len(passwords) >= 1

    def test_password_too_short_not_detected(self) -> None:
        """Test that very short passwords are not detected."""
        text = "password=pass"  # Too short (< 8 chars)
        secrets = detect_secrets(text)

        # Should not detect passwords < 8 chars
        passwords = [s for s in secrets if s.secret_type == "password"]
        assert len(passwords) == 0


class TestSecretMatchDataclass:
    """Test SecretMatch dataclass."""

    def test_secret_match_creation(self) -> None:
        """Test creating a SecretMatch."""
        match = SecretMatch(
            secret_type="api_key",
            value="test_key",
            start_pos=0,
            end_pos=8,
            line_number=1,
            context="***",
            confidence=0.8,
        )

        assert match.secret_type == "api_key"
        assert match.value == "test_key"
        assert match.confidence == 0.8

    def test_secret_match_invalid_confidence(self) -> None:
        """Test that invalid confidence raises error."""
        with pytest.raises(ValueError, match="confidence must be 0.0-1.0"):
            SecretMatch(
                secret_type="api_key",
                value="test_key",
                start_pos=0,
                end_pos=8,
                line_number=1,
                context="***",
                confidence=1.5,  # Invalid
            )


class TestDetectSecretsIntegration:
    """Integration tests for detect_secrets."""

    def test_empty_text(self) -> None:
        """Test empty text."""
        secrets = detect_secrets("")
        assert secrets == []

    def test_no_secrets(self) -> None:
        """Test text with no secrets."""
        text = "This is just normal text with no secrets."
        secrets = detect_secrets(text)
        assert secrets == []

    def test_multiple_secret_types(self) -> None:
        """Test detection of multiple secret types."""
        text = """
        AWS_KEY=AKIAIOSFODNN7EXAMPLE
        GITHUB_TOKEN=ghp_1234567890abcdefghijklmnopqrstuvwxyz
        password=SuperSecret123
        """
        secrets = detect_secrets(text)

        assert len(secrets) >= 3
        secret_types = {s.secret_type for s in secrets}
        assert "aws_access_key_id" in secret_types
        assert "github_token" in secret_types
        assert "password" in secret_types

    def test_deterministic_ordering(self) -> None:
        """Test that detection is deterministic (same order)."""
        text = """
        key1=AKIAIOSFODNN7EXAMPLE
        key2=ghp_1234567890abcdefghijklmnopqrstuvwx
        """

        secrets1 = detect_secrets(text)
        secrets2 = detect_secrets(text)

        assert len(secrets1) == len(secrets2)
        for s1, s2 in zip(secrets1, secrets2):
            assert s1.start_pos == s2.start_pos
            assert s1.secret_type == s2.secret_type

    def test_overlapping_matches_deduplicated(self) -> None:
        """Test that overlapping matches are deduplicated."""
        text = "api_key=abc123def456ghi789jkl012mno345pqr678"
        secrets = detect_secrets(text)

        # Should not have duplicate matches at same position
        positions = [(s.start_pos, s.end_pos) for s in secrets]
        assert len(positions) == len(set(positions))
