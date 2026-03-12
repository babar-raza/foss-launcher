"""Tests for hashing utilities.

Validates:
- SHA256 hashing for bytes and files
- Deterministic output
- Correctness of hash values
"""

from __future__ import annotations

from pathlib import Path

from launcher.io.hashing import sha256_bytes, sha256_file


def test_sha256_bytes_basic() -> None:
    data = b"Hello, World!"
    hash_result = sha256_bytes(data)
    assert isinstance(hash_result, str)
    assert len(hash_result) == 64  # SHA256 hex digest is 64 chars


def test_sha256_bytes_deterministic() -> None:
    data = b"test data for hashing"
    h1 = sha256_bytes(data)
    h2 = sha256_bytes(data)
    assert h1 == h2


def test_sha256_bytes_different_inputs() -> None:
    h1 = sha256_bytes(b"input_a")
    h2 = sha256_bytes(b"input_b")
    assert h1 != h2


def test_sha256_bytes_empty() -> None:
    h = sha256_bytes(b"")
    assert isinstance(h, str)
    assert len(h) == 64


def test_sha256_bytes_known_value() -> None:
    # SHA256("abc") is well-known
    h = sha256_bytes(b"abc")
    assert h == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


def test_sha256_file(tmp_path: Path) -> None:
    f = tmp_path / "test.txt"
    f.write_bytes(b"file content for hashing")
    h = sha256_file(f)
    assert isinstance(h, str)
    assert len(h) == 64


def test_sha256_file_matches_bytes(tmp_path: Path) -> None:
    data = b"consistent hashing test"
    f = tmp_path / "test.txt"
    f.write_bytes(data)
    assert sha256_file(f) == sha256_bytes(data)


def test_sha256_file_large(tmp_path: Path) -> None:
    """Verify chunked reading works for files > 1MB."""
    f = tmp_path / "large.bin"
    data = b"x" * (2 * 1024 * 1024)  # 2MB
    f.write_bytes(data)
    h = sha256_file(f)
    assert h == sha256_bytes(data)
