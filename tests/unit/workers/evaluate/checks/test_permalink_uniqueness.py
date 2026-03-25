"""Unit tests for check_permalink_uniqueness (TC-QG-01)."""
from __future__ import annotations

from launcher.workers.evaluate.checks.permalink_uniqueness import check_permalink_uniqueness


def test_unique_urls_pass():
    """Different URLs -> no findings."""
    pages = [
        {"slug": "overview", "url": "/docs/overview/", "section": "docs", "page_role": "landing", "page_id": "1"},
        {"slug": "install", "url": "/docs/install/", "section": "docs", "page_role": "workflow_page", "page_id": "2"},
    ]
    findings = check_permalink_uniqueness(pages)
    assert len(findings) == 0


def test_duplicate_url_critical():
    """Same URL on 2 pages -> CRITICAL."""
    pages = [
        {"slug": "overview", "url": "/docs/overview/", "section": "docs", "page_role": "landing", "page_id": "1"},
        {"slug": "overview-2", "url": "/docs/overview/", "section": "docs", "page_role": "landing", "page_id": "2"},
    ]
    findings = check_permalink_uniqueness(pages)
    url_findings = [f for f in findings if f.check == "permalink_uniqueness" and f.severity == "critical"]
    assert len(url_findings) == 1
    assert "URL collision" in url_findings[0].message


def test_slug_collision_different_sections():
    """Same slug, different sections -> HIGH."""
    pages = [
        {"slug": "overview", "url": "/docs/overview/", "section": "docs", "page_role": "landing", "page_id": "1"},
        {"slug": "overview", "url": "/kb/overview/", "section": "kb", "page_role": "landing", "page_id": "2"},
    ]
    findings = check_permalink_uniqueness(pages)
    slug_findings = [f for f in findings if f.severity == "high"]
    assert len(slug_findings) == 1
    assert "Slug collision" in slug_findings[0].message


def test_slug_collision_same_section_no_high():
    """Same slug, same section -> no HIGH slug finding (only URL if collides)."""
    pages = [
        {"slug": "overview", "url": "/docs/overview/", "section": "docs", "page_role": "landing", "page_id": "1"},
        {"slug": "overview", "url": "/docs/overview-2/", "section": "docs", "page_role": "landing", "page_id": "2"},
    ]
    findings = check_permalink_uniqueness(pages)
    slug_findings = [f for f in findings if f.severity == "high"]
    # Same section -> sections set has only 1 entry -> no HIGH finding
    assert len(slug_findings) == 0


def test_empty_pages_list():
    """Empty pages list -> no findings."""
    findings = check_permalink_uniqueness([])
    assert len(findings) == 0
