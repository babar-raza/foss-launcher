"""Tests for hashing utilities.

Validates:
- SHA256 hashing for bytes and files
- Deterministic output
- Correctness of hash values
"""

from __future__ import annotations

from pathlib import Path

from launch.io.hashing import sha256_bytes, sha256_file


def test_sha256_bytes_basic() -> None:
    """Test basic SHA256 hashing of bytes."""
    data = b"Hello, World!"
    hash_result = sha256_bytes(data)

    # Known SHA256 hash of "Hello, World!"
    expected = "dffd6021bb2bd5b0af676290809ec3a53191dd81c7f70a4b28688a362182986f"
    assert hash_result == expected


def test_sha256_bytes_empty() -> None:
    """Test SHA256 of empty bytes."""
    data = b""
    hash_result = sha256_bytes(data)

    # Known SHA256 hash of empty string
    expected = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    assert hash_result == expected


def test_sha256_bytes_deterministic() -> None:
    """Test that hashing the same data produces the same hash."""
    data = b"Test data for determinism"

    hash1 = sha256_bytes(data)
    hash2 = sha256_bytes(data)

    assert hash1 == hash2


def test_sha256_bytes_different_data() -> None:
    """Test that different data produces different hashes."""
    data1 = b"data1"
    data2 = b"data2"

    hash1 = sha256_bytes(data1)
    hash2 = sha256_bytes(data2)

    assert hash1 != hash2


def test_sha256_file_basic(tmp_path: Path) -> None:
    """Test basic SHA256 hashing of a file."""
    test_file = tmp_path / "test.txt"
    test_file.write_bytes(b"Hello, World!")

    hash_result = sha256_file(test_file)

    # Known SHA256 hash of "Hello, World!"
    expected = "dffd6021bb2bd5b0af676290809ec3a53191dd81c7f70a4b28688a362182986f"
    assert hash_result == expected


def test_sha256_file_empty(tmp_path: Path) -> None:
    """Test SHA256 of empty file."""
    test_file = tmp_path / "empty.txt"
    test_file.write_bytes(b"")

    hash_result = sha256_file(test_file)

    # Known SHA256 hash of empty file
    expected = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    assert hash_result == expected


def test_sha256_file_deterministic(tmp_path: Path) -> None:
    """Test that hashing the same file produces the same hash."""
    test_file = tmp_path / "test.txt"
    test_file.write_bytes(b"Test data for determinism")

    hash1 = sha256_file(test_file)
    hash2 = sha256_file(test_file)

    assert hash1 == hash2


def test_sha256_file_large_file(tmp_path: Path) -> None:
    """Test hashing of large file (tests chunked reading)."""
    test_file = tmp_path / "large.txt"
    # Create a 5MB file
    large_data = b"x" * (5 * 1024 * 1024)
    test_file.write_bytes(large_data)

    hash_result = sha256_file(test_file)

    # Verify against direct hash
    expected = sha256_bytes(large_data)
    assert hash_result == expected


def test_sha256_file_matches_bytes_hash(tmp_path: Path) -> None:
    """Test that file hash matches bytes hash for the same data."""
    data = b"Test data for comparison"

    test_file = tmp_path / "test.txt"
    test_file.write_bytes(data)

    file_hash = sha256_file(test_file)
    bytes_hash = sha256_bytes(data)

    assert file_hash == bytes_hash


def test_sha256_file_binary_data(tmp_path: Path) -> None:
    """Test hashing of binary file."""
    test_file = tmp_path / "binary.dat"
    binary_data = bytes(range(256))  # All byte values
    test_file.write_bytes(binary_data)

    hash_result = sha256_file(test_file)

    # Should produce a valid hash
    assert len(hash_result) == 64
    assert all(c in "0123456789abcdef" for c in hash_result)


def test_sha256_file_unicode_content(tmp_path: Path) -> None:
    """Test hashing of file with Unicode content."""
    test_file = tmp_path / "unicode.txt"
    unicode_data = "Привет мир 🌍".encode('utf-8')
    test_file.write_bytes(unicode_data)

    hash_result = sha256_file(test_file)

    # Should match direct hash of the UTF-8 bytes
    expected = sha256_bytes(unicode_data)
    assert hash_result == expected
