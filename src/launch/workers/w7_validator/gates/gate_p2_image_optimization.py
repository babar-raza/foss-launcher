"""Gate P2: Image Optimization.

Validates that images are optimized (compressed, < 200KB, WebP preferred).

Per TC-571 requirements: Image Optimization (compressed, < 200KB, WebP preferred).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Tuple


def execute_gate(run_dir: Path, profile: str) -> Tuple[bool, List[Dict[str, Any]]]:
    """Execute Gate P2: Image Optimization.

    Validates that images are optimized:
    - Images should be < 200KB
    - WebP format preferred for better compression
    - Detects images referenced in markdown files

    Args:
        run_dir: Run directory path
        profile: Validation profile (local, ci, prod)

    Returns:
        Tuple of (gate_passed, issues)
    """
    issues = []
    max_image_size_kb = 200
    max_image_size_bytes = max_image_size_kb * 1024

    # Find all markdown files
    site_dir = run_dir / "work" / "site"
    if not site_dir.exists():
        return True, []

    md_files = sorted(site_dir.rglob("*.md"))

    # Pattern to match images: ![alt](url)
    image_pattern = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")

    # Track referenced images
    referenced_images = set()

    for md_file in md_files:
        try:
            content = md_file.read_text(encoding="utf-8")

            # Find all image references
            for match in image_pattern.finditer(content):
                image_url = match.group(2).strip()

                # Skip external URLs
                if image_url.startswith(("http://", "https://", "//")):
                    continue

                # Resolve relative path
                if image_url.startswith("/"):
                    # Absolute path from site root
                    image_path = site_dir / image_url.lstrip("/")
                else:
                    # Relative path from markdown file
                    image_path = (md_file.parent / image_url).resolve()

                referenced_images.add(image_path)

        except Exception as e:
            issues.append(
                {
                    "issue_id": f"image_check_error_{md_file.name}",
                    "gate": "gate_p2_image_optimization",
                    "severity": "warn",
                    "message": f"Error checking images in {md_file.name}: {e}",
                    "error_code": "GATE_IMAGE_CHECK_ERROR",
                    "location": {"path": str(md_file)},
                    "status": "OPEN",
                }
            )

    # Check all referenced images
    for image_path in sorted(referenced_images):
        if not image_path.exists():
            issues.append(
                {
                    "issue_id": f"image_missing_{image_path.name}",
                    "gate": "gate_p2_image_optimization",
                    "severity": "error",
                    "message": f"Referenced image not found: {image_path.name}",
                    "error_code": "GATE_IMAGE_MISSING",
                    "location": {"path": str(image_path)},
                    "status": "OPEN",
                }
            )
            continue

        try:
            file_size = image_path.stat().st_size

            # Check size
            if file_size > max_image_size_bytes:
                size_kb = file_size / 1024
                issues.append(
                    {
                        "issue_id": f"image_size_{image_path.name}",
                        "gate": "gate_p2_image_optimization",
                        "severity": "warn",
                        "message": f"Image {image_path.name} exceeds recommended size: {size_kb:.2f}KB > {max_image_size_kb}KB",
                        "error_code": "GATE_IMAGE_SIZE_EXCEEDED",
                        "location": {"path": str(image_path)},
                        "status": "OPEN",
                    }
                )

            # Check format (prefer WebP)
            if image_path.suffix.lower() not in [".webp"]:
                if image_path.suffix.lower() in [".png", ".jpg", ".jpeg", ".gif"]:
                    issues.append(
                        {
                            "issue_id": f"image_format_{image_path.name}",
                            "gate": "gate_p2_image_optimization",
                            "severity": "info",
                            "message": f"Image {image_path.name} uses {image_path.suffix} format; consider WebP for better compression",
                            "error_code": "GATE_IMAGE_FORMAT_NOT_WEBP",
                            "location": {"path": str(image_path)},
                            "status": "OPEN",
                        }
                    )

        except Exception as e:
            issues.append(
                {
                    "issue_id": f"image_stat_error_{image_path.name}",
                    "gate": "gate_p2_image_optimization",
                    "severity": "warn",
                    "message": f"Error checking image {image_path.name}: {e}",
                    "error_code": "GATE_IMAGE_CHECK_ERROR",
                    "location": {"path": str(image_path)},
                    "status": "OPEN",
                }
            )

    # Gate passes if no error/blocker issues (warnings and info are OK)
    gate_passed = not any(
        issue["severity"] in ["blocker", "error"] for issue in issues
    )

    return gate_passed, issues
