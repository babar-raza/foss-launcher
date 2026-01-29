"""
Idempotency enforcement for safe operation retries.

Ensures operations can be safely retried by:
- Content-based deduplication (hash comparison)
- Unique key generation (event_id, artifact hashes)
- Skip duplicate writes based on content identity

Spec: specs/21_worker_contracts.md (idempotency requirements)
"""

import hashlib
import logging
from pathlib import Path
from typing import Union

logger = logging.getLogger(__name__)


def compute_content_hash(content: Union[str, bytes]) -> str:
    """
    Compute SHA256 hash of content for idempotency checks.

    Args:
        content: String or bytes to hash

    Returns:
        Hex digest of SHA256 hash
    """
    if isinstance(content, str):
        content = content.encode("utf-8")

    return hashlib.sha256(content).hexdigest()


def is_idempotent_write(target_path: Path, content: Union[str, bytes]) -> bool:
    """
    Check if write would be idempotent (content identical to existing file).

    If the file doesn't exist, returns False (write needed).
    If the file exists and content is identical, returns True (skip write).
    If the file exists and content differs, returns False (write needed).

    Args:
        target_path: Path to check
        content: New content to write

    Returns:
        True if write can be skipped (content identical), False if write needed
    """
    if not target_path.exists():
        logger.debug(f"File {target_path} does not exist - write needed")
        return False

    try:
        # Read existing content
        if isinstance(content, str):
            existing_content = target_path.read_text(encoding="utf-8")
            new_content = content
        else:
            existing_content = target_path.read_bytes()
            new_content = content

        # Compare content directly (most efficient)
        if existing_content == new_content:
            logger.debug(f"File {target_path} has identical content - write skipped")
            return True

        logger.debug(f"File {target_path} has different content - write needed")
        return False

    except Exception as e:
        logger.warning(f"Error checking idempotency for {target_path}: {e}")
        # If we can't read the file, assume write is needed
        return False


def write_if_changed(target_path: Path, content: Union[str, bytes]) -> bool:
    """
    Write content to file only if it differs from existing content.

    Implements idempotent write with automatic change detection.

    Args:
        target_path: Path to write to
        content: Content to write

    Returns:
        True if file was written, False if skipped (identical content)
    """
    if is_idempotent_write(target_path, content):
        logger.info(f"Skipped idempotent write to {target_path}")
        return False

    # Ensure parent directory exists
    target_path.parent.mkdir(parents=True, exist_ok=True)

    # Write content
    if isinstance(content, str):
        target_path.write_text(content, encoding="utf-8")
    else:
        target_path.write_bytes(content)

    logger.info(f"Wrote content to {target_path}")
    return True


def generate_unique_key(*components: str) -> str:
    """
    Generate a unique key from multiple components using SHA256.

    Useful for creating event IDs, artifact keys, etc.

    Args:
        *components: String components to combine

    Returns:
        Hex digest of combined components
    """
    combined = "|".join(components)
    return compute_content_hash(combined)
