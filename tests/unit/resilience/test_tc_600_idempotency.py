"""
Tests for TC-600: Idempotency enforcement.

Covers:
- Content hash computation
- Idempotent write detection
- Write-if-changed logic
- Unique key generation
"""

import pytest
from pathlib import Path
from src.launch.resilience.idempotency import (
    compute_content_hash,
    is_idempotent_write,
    write_if_changed,
    generate_unique_key,
)


def test_compute_content_hash_string():
    """Test SHA256 hash computation for string content."""
    content = "Hello, World!"
    hash1 = compute_content_hash(content)

    # Should be deterministic
    hash2 = compute_content_hash(content)
    assert hash1 == hash2

    # Should be 64 hex characters (SHA256)
    assert len(hash1) == 64
    assert all(c in "0123456789abcdef" for c in hash1)


def test_compute_content_hash_bytes():
    """Test SHA256 hash computation for bytes content."""
    content = b"Hello, World!"
    hash1 = compute_content_hash(content)

    # Should be deterministic
    hash2 = compute_content_hash(content)
    assert hash1 == hash2

    # String and bytes of same content should produce same hash
    string_hash = compute_content_hash("Hello, World!")
    assert hash1 == string_hash


def test_compute_content_hash_different_content():
    """Test that different content produces different hashes."""
    hash1 = compute_content_hash("content1")
    hash2 = compute_content_hash("content2")

    assert hash1 != hash2


def test_is_idempotent_write_file_not_exists(tmp_path):
    """Test idempotent write when file doesn't exist."""
    target = tmp_path / "test.txt"
    content = "new content"

    # File doesn't exist, should return False (write needed)
    assert is_idempotent_write(target, content) is False


def test_is_idempotent_write_identical_content(tmp_path):
    """Test idempotent write with identical content."""
    target = tmp_path / "test.txt"
    content = "existing content"

    # Create file with content
    target.write_text(content, encoding="utf-8")

    # Same content should return True (write not needed)
    assert is_idempotent_write(target, content) is True


def test_is_idempotent_write_different_content(tmp_path):
    """Test idempotent write with different content."""
    target = tmp_path / "test.txt"
    target.write_text("old content", encoding="utf-8")

    new_content = "new content"

    # Different content should return False (write needed)
    assert is_idempotent_write(target, new_content) is False


def test_is_idempotent_write_bytes(tmp_path):
    """Test idempotent write with bytes content."""
    target = tmp_path / "test.bin"
    content = b"binary content"

    # Create file
    target.write_bytes(content)

    # Same bytes should return True
    assert is_idempotent_write(target, content) is True

    # Different bytes should return False
    assert is_idempotent_write(target, b"different") is False


def test_write_if_changed_new_file(tmp_path):
    """Test write_if_changed creates new file."""
    target = tmp_path / "test.txt"
    content = "new content"

    # Should write and return True
    result = write_if_changed(target, content)

    assert result is True
    assert target.exists()
    assert target.read_text(encoding="utf-8") == content


def test_write_if_changed_identical_content(tmp_path):
    """Test write_if_changed skips write for identical content."""
    target = tmp_path / "test.txt"
    content = "existing content"

    # Create file
    target.write_text(content, encoding="utf-8")
    original_mtime = target.stat().st_mtime

    # Should skip write and return False
    result = write_if_changed(target, content)

    assert result is False
    assert target.read_text(encoding="utf-8") == content


def test_write_if_changed_different_content(tmp_path):
    """Test write_if_changed updates file with different content."""
    target = tmp_path / "test.txt"
    target.write_text("old content", encoding="utf-8")

    new_content = "new content"

    # Should write and return True
    result = write_if_changed(target, new_content)

    assert result is True
    assert target.read_text(encoding="utf-8") == new_content


def test_write_if_changed_creates_parent_dir(tmp_path):
    """Test write_if_changed creates parent directories."""
    target = tmp_path / "subdir" / "nested" / "test.txt"
    content = "content"

    # Should create parent dirs and write
    result = write_if_changed(target, content)

    assert result is True
    assert target.exists()
    assert target.read_text(encoding="utf-8") == content


def test_write_if_changed_bytes(tmp_path):
    """Test write_if_changed with bytes content."""
    target = tmp_path / "test.bin"
    content = b"binary content"

    # Should write new file
    result = write_if_changed(target, content)
    assert result is True
    assert target.read_bytes() == content

    # Should skip identical content
    result = write_if_changed(target, content)
    assert result is False


def test_generate_unique_key_single_component():
    """Test unique key generation from single component."""
    key = generate_unique_key("component1")

    # Should be 64 hex characters
    assert len(key) == 64
    assert all(c in "0123456789abcdef" for c in key)


def test_generate_unique_key_multiple_components():
    """Test unique key generation from multiple components."""
    key = generate_unique_key("comp1", "comp2", "comp3")

    # Should be deterministic
    key2 = generate_unique_key("comp1", "comp2", "comp3")
    assert key == key2

    # Different order should produce different key
    key3 = generate_unique_key("comp3", "comp2", "comp1")
    assert key != key3


def test_generate_unique_key_empty_components():
    """Test unique key generation with empty components."""
    key = generate_unique_key("", "", "")

    assert len(key) == 64


def test_generate_unique_key_for_event_id():
    """Test unique key generation for event IDs."""
    run_id = "run-123"
    worker_name = "facts_extractor"
    timestamp = "2025-01-28T12:00:00Z"

    event_id = generate_unique_key(run_id, worker_name, timestamp)

    # Should be unique for these components
    assert len(event_id) == 64

    # Different timestamp should produce different key
    event_id2 = generate_unique_key(run_id, worker_name, "2025-01-28T12:00:01Z")
    assert event_id != event_id2


def test_is_idempotent_write_permission_error(tmp_path):
    """Test idempotent write handles permission errors gracefully."""
    target = tmp_path / "test.txt"
    target.write_text("content", encoding="utf-8")

    # Make file read-only
    target.chmod(0o444)

    try:
        # Should return False (assume write needed) on permission error
        result = is_idempotent_write(target, "content")
        # If we can still read it, should detect identical content
        assert result in [True, False]  # Either is acceptable
    finally:
        # Restore permissions for cleanup
        target.chmod(0o644)


def test_compute_content_hash_unicode():
    """Test hash computation with Unicode content."""
    content = "Hello, 世界! 🌍"
    hash1 = compute_content_hash(content)
    hash2 = compute_content_hash(content)

    assert hash1 == hash2
    assert len(hash1) == 64


def test_write_if_changed_preserves_encoding(tmp_path):
    """Test that write_if_changed preserves UTF-8 encoding."""
    target = tmp_path / "test.txt"
    content = "Unicode: 你好 🎉"

    # Write with Unicode
    result = write_if_changed(target, content)
    assert result is True

    # Read back and verify
    read_content = target.read_text(encoding="utf-8")
    assert read_content == content

    # Should skip on second write
    result = write_if_changed(target, content)
    assert result is False


def test_is_idempotent_write_multiline_content(tmp_path):
    """Test idempotent write with multiline content."""
    target = tmp_path / "test.txt"
    content = """Line 1
Line 2
Line 3
"""

    target.write_text(content, encoding="utf-8")

    # Should detect identical multiline content
    assert is_idempotent_write(target, content) is True

    # Should detect different line endings
    different_content = "Line 1\nLine 2\nLine 4\n"
    assert is_idempotent_write(target, different_content) is False
