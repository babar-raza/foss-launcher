"""Tests for TC-571: Performance and Security Validation Gates.

This module tests the six new gates added in TC-571:
- Gate P1: Page Size Limit (< 500KB per page)
- Gate P2: Image Optimization (compressed, < 200KB, WebP preferred)
- Gate P3: Build Time Limit (< 60s total build time)
- Gate S1: XSS Prevention (no unsafe HTML, script tags sanitized)
- Gate S2: Sensitive Data Leak (no API keys, passwords, secrets)
- Gate S3: External Link Safety (HTTPS only, no broken external links)

Minimum 12 tests (2 per gate): positive and negative cases.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from launch.workers.w7_validator.gates import (
    gate_p1_page_size_limit,
    gate_p2_image_optimization,
    gate_p3_build_time_limit,
    gate_s1_xss_prevention,
    gate_s2_sensitive_data_leak,
    gate_s3_external_link_safety,
)


# Gate P1: Page Size Limit Tests


def test_gate_p1_page_size_pass(tmp_path: Path):
    """Test Gate P1 passes when all pages are under 500KB."""
    # Setup
    site_dir = tmp_path / "work" / "site"
    site_dir.mkdir(parents=True)

    # Create a small page (< 500KB)
    small_page = site_dir / "small.md"
    small_page.write_text("# Small Page\n\nThis is a small page." * 100)

    # Execute gate
    gate_passed, issues = gate_p1_page_size_limit.execute_gate(tmp_path, "local")

    # Assert
    assert gate_passed is True
    assert len(issues) == 0


def test_gate_p1_page_size_fail(tmp_path: Path):
    """Test Gate P1 fails when a page exceeds 500KB."""
    # Setup
    site_dir = tmp_path / "work" / "site"
    site_dir.mkdir(parents=True)

    # Create a large page (> 500KB)
    large_page = site_dir / "large.md"
    large_content = "# Large Page\n\n" + ("A" * 600 * 1024)  # 600KB
    large_page.write_text(large_content)

    # Execute gate
    gate_passed, issues = gate_p1_page_size_limit.execute_gate(tmp_path, "local")

    # Assert
    assert gate_passed is False
    assert len(issues) == 1
    assert issues[0]["error_code"] == "GATE_PAGE_SIZE_LIMIT_EXCEEDED"
    assert issues[0]["severity"] == "error"


# Gate P2: Image Optimization Tests


def test_gate_p2_image_optimization_pass(tmp_path: Path):
    """Test Gate P2 passes with optimized WebP images."""
    # Setup
    site_dir = tmp_path / "work" / "site"
    site_dir.mkdir(parents=True)

    # Create markdown with WebP image reference
    md_file = site_dir / "page.md"
    md_file.write_text("# Page\n\n![Alt text](image.webp)")

    # Create small WebP image
    image_file = site_dir / "image.webp"
    image_file.write_bytes(b"WEBP_CONTENT" * 100)  # Small file

    # Execute gate
    gate_passed, issues = gate_p2_image_optimization.execute_gate(tmp_path, "local")

    # Assert
    assert gate_passed is True
    # Info messages about format are OK, but no errors
    error_issues = [i for i in issues if i["severity"] in ["error", "blocker"]]
    assert len(error_issues) == 0


def test_gate_p2_image_optimization_fail_size(tmp_path: Path):
    """Test Gate P2 warns when image exceeds 200KB."""
    # Setup
    site_dir = tmp_path / "work" / "site"
    site_dir.mkdir(parents=True)

    # Create markdown with image reference
    md_file = site_dir / "page.md"
    md_file.write_text("# Page\n\n![Alt text](large.png)")

    # Create large PNG image (> 200KB)
    image_file = site_dir / "large.png"
    image_file.write_bytes(b"PNG_CONTENT" * 300 * 1024)  # 300KB

    # Execute gate
    gate_passed, issues = gate_p2_image_optimization.execute_gate(tmp_path, "local")

    # Assert
    # Gate passes (warnings don't fail), but issues reported
    assert gate_passed is True
    assert len(issues) >= 1
    # Check for size warning
    size_issues = [i for i in issues if "GATE_IMAGE_SIZE_EXCEEDED" in i["error_code"]]
    assert len(size_issues) == 1
    assert size_issues[0]["severity"] == "warn"


# Gate P3: Build Time Limit Tests


def test_gate_p3_build_time_pass(tmp_path: Path):
    """Test Gate P3 passes when build time is under 60s."""
    # Setup - Create events with build time < 60s
    events_file = tmp_path / "events.ndjson"
    start_time = datetime.now(timezone.utc)
    end_time = start_time + timedelta(seconds=30)

    events = [
        {
            "event_id": "1",
            "type": "HUGO_BUILD_STARTED",
            "ts": start_time.isoformat(),
        },
        {
            "event_id": "2",
            "type": "HUGO_BUILD_COMPLETED",
            "ts": end_time.isoformat(),
        },
    ]

    with events_file.open("w") as f:
        for event in events:
            f.write(json.dumps(event) + "\n")

    # Execute gate
    gate_passed, issues = gate_p3_build_time_limit.execute_gate(tmp_path, "local")

    # Assert
    assert gate_passed is True
    assert len(issues) == 0


def test_gate_p3_build_time_fail(tmp_path: Path):
    """Test Gate P3 warns when build time exceeds 60s."""
    # Setup - Create events with build time > 60s
    events_file = tmp_path / "events.ndjson"
    start_time = datetime.now(timezone.utc)
    end_time = start_time + timedelta(seconds=90)

    events = [
        {
            "event_id": "1",
            "type": "HUGO_BUILD_STARTED",
            "ts": start_time.isoformat(),
        },
        {
            "event_id": "2",
            "type": "HUGO_BUILD_COMPLETED",
            "ts": end_time.isoformat(),
        },
    ]

    with events_file.open("w") as f:
        for event in events:
            f.write(json.dumps(event) + "\n")

    # Execute gate
    gate_passed, issues = gate_p3_build_time_limit.execute_gate(tmp_path, "local")

    # Assert
    # Gate passes (warnings don't fail), but issue reported
    assert gate_passed is True
    assert len(issues) == 1
    assert issues[0]["error_code"] == "GATE_BUILD_TIME_LIMIT_EXCEEDED"
    assert issues[0]["severity"] == "warn"


# Gate S1: XSS Prevention Tests


def test_gate_s1_xss_prevention_pass(tmp_path: Path):
    """Test Gate S1 passes with safe content."""
    # Setup
    site_dir = tmp_path / "work" / "site"
    site_dir.mkdir(parents=True)

    # Create safe markdown
    md_file = site_dir / "safe.md"
    md_file.write_text("# Safe Page\n\nThis is safe content with [links](https://example.com).")

    # Execute gate
    gate_passed, issues = gate_s1_xss_prevention.execute_gate(tmp_path, "local")

    # Assert
    assert gate_passed is True
    assert len(issues) == 0


def test_gate_s1_xss_prevention_fail_script(tmp_path: Path):
    """Test Gate S1 fails when script tags are found."""
    # Setup
    site_dir = tmp_path / "work" / "site"
    site_dir.mkdir(parents=True)

    # Create unsafe markdown with script tag
    md_file = site_dir / "unsafe.md"
    md_file.write_text("# Unsafe Page\n\n<script>alert('XSS')</script>")

    # Execute gate
    gate_passed, issues = gate_s1_xss_prevention.execute_gate(tmp_path, "local")

    # Assert
    assert gate_passed is False
    assert len(issues) >= 1
    assert any(i["error_code"] == "GATE_XSS_SCRIPT_TAG" for i in issues)
    assert any(i["severity"] == "blocker" for i in issues)


def test_gate_s1_xss_prevention_fail_event_handler(tmp_path: Path):
    """Test Gate S1 fails when event handlers are found."""
    # Setup
    site_dir = tmp_path / "work" / "site"
    site_dir.mkdir(parents=True)

    # Create unsafe markdown with event handler
    md_file = site_dir / "unsafe.md"
    md_file.write_text("# Unsafe Page\n\n<img onclick=\"alert('XSS')\">")

    # Execute gate
    gate_passed, issues = gate_s1_xss_prevention.execute_gate(tmp_path, "local")

    # Assert
    assert gate_passed is False
    assert len(issues) >= 1
    assert any(i["error_code"] == "GATE_XSS_EVENT_HANDLER" for i in issues)


# Gate S2: Sensitive Data Leak Tests


def test_gate_s2_sensitive_data_pass(tmp_path: Path):
    """Test Gate S2 passes with no sensitive data."""
    # Setup
    site_dir = tmp_path / "work" / "site"
    site_dir.mkdir(parents=True)

    # Create safe markdown
    md_file = site_dir / "safe.md"
    md_file.write_text("# Safe Page\n\nThis page has no secrets.")

    # Execute gate
    gate_passed, issues = gate_s2_sensitive_data_leak.execute_gate(tmp_path, "local")

    # Assert
    assert gate_passed is True
    assert len(issues) == 0


def test_gate_s2_sensitive_data_fail_aws_key(tmp_path: Path):
    """Test Gate S2 fails when AWS access key is found."""
    # Setup
    site_dir = tmp_path / "work" / "site"
    site_dir.mkdir(parents=True)

    # Create unsafe markdown with AWS key
    md_file = site_dir / "unsafe.md"
    md_file.write_text("# Unsafe Page\n\nAWS Key: AKIAIOSFODNN7EXAMPLE")

    # Execute gate
    gate_passed, issues = gate_s2_sensitive_data_leak.execute_gate(tmp_path, "local")

    # Assert
    assert gate_passed is False
    assert len(issues) >= 1
    assert any("AWS_ACCESS_KEY" in i["error_code"] for i in issues)
    assert any(i["severity"] == "blocker" for i in issues)


def test_gate_s2_sensitive_data_fail_api_key(tmp_path: Path):
    """Test Gate S2 fails when generic API key is found."""
    # Setup
    site_dir = tmp_path / "work" / "site"
    site_dir.mkdir(parents=True)

    # Create unsafe markdown with API key
    md_file = site_dir / "unsafe.md"
    md_file.write_text("# Unsafe Page\n\napi_key = 'a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6'")

    # Execute gate
    gate_passed, issues = gate_s2_sensitive_data_leak.execute_gate(tmp_path, "local")

    # Assert
    assert gate_passed is False
    assert len(issues) >= 1
    assert any("GENERIC_API_KEY" in i["error_code"] for i in issues)


# Gate S3: External Link Safety Tests


def test_gate_s3_external_link_safety_pass(tmp_path: Path):
    """Test Gate S3 passes with HTTPS links."""
    # Setup
    site_dir = tmp_path / "work" / "site"
    site_dir.mkdir(parents=True)

    # Create markdown with HTTPS link
    md_file = site_dir / "safe.md"
    md_file.write_text("# Safe Page\n\n[Link](https://example.com)")

    # Execute gate
    gate_passed, issues = gate_s3_external_link_safety.execute_gate(tmp_path, "local")

    # Assert
    assert gate_passed is True
    assert len(issues) == 0


def test_gate_s3_external_link_safety_fail_http(tmp_path: Path):
    """Test Gate S3 fails when HTTP (insecure) links are found."""
    # Setup
    site_dir = tmp_path / "work" / "site"
    site_dir.mkdir(parents=True)

    # Create markdown with HTTP link
    md_file = site_dir / "unsafe.md"
    md_file.write_text("# Unsafe Page\n\n[Link](http://example.com)")

    # Execute gate
    gate_passed, issues = gate_s3_external_link_safety.execute_gate(tmp_path, "local")

    # Assert
    assert gate_passed is False
    assert len(issues) >= 1
    assert any(i["error_code"] == "GATE_EXTERNAL_LINK_INSECURE_HTTP" for i in issues)
    assert any(i["severity"] == "error" for i in issues)


# Additional test for deterministic ordering


def test_gate_deterministic_ordering(tmp_path: Path):
    """Test that gate execution produces deterministic issue ordering."""
    # Setup
    site_dir = tmp_path / "work" / "site"
    site_dir.mkdir(parents=True)

    # Create multiple files with issues
    for i in range(3):
        md_file = site_dir / f"page_{i}.md"
        md_file.write_text(f"# Page {i}\n\n<script>alert('{i}')</script>")

    # Execute gate multiple times
    results = []
    for _ in range(3):
        _, issues = gate_s1_xss_prevention.execute_gate(tmp_path, "local")
        issue_ids = [issue["issue_id"] for issue in issues]
        results.append(issue_ids)

    # Assert all runs produce same ordering
    assert results[0] == results[1] == results[2]
