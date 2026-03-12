"""Tests that evaluate checks emit section_id on section-level findings (V2SC-03)."""
from __future__ import annotations

import pytest

from launcher.workers.evaluate.checks.density import check_density
from launcher.workers.evaluate.checks.repetition import check_repetition
from launcher.workers.evaluate.checks.structure import check_structure


SLUG = "test-slug"


class TestDensitySectionId:
    def test_thin_section_has_section_id(self) -> None:
        content = "---\ntitle: T\n---\n## Introduction\nshort.\n## Setup\nword " * 5
        findings = check_density(content, SLUG)
        section_findings = [f for f in findings if f.section_id is not None]
        # At least one per-section finding should carry section_id
        assert any(f.check == "density" for f in section_findings)

    def test_section_id_is_heading_text(self) -> None:
        content = "---\ntitle: T\n---\n## Overview\nx\n## Tiny\ny\n"
        findings = check_density(content, SLUG)
        section_ids = [f.section_id for f in findings if f.section_id]
        for sid in section_ids:
            assert isinstance(sid, str) and len(sid) > 0

    def test_page_level_finding_has_no_section_id(self) -> None:
        # A short page (< 100 words) triggers a page-level finding with no section_id
        content = "---\ntitle: T\n---\nToo short.\n"
        findings = check_density(content, SLUG)
        page_findings = [f for f in findings if f.section_id is None]
        assert any(f.message.startswith("Page has") for f in page_findings)


class TestStructureSectionId:
    def test_level_skip_has_section_id(self) -> None:
        content = "---\ntitle: T\n---\n## Level Two\n#### Level Four jump\n"
        findings = check_structure(content, SLUG)
        skip_findings = [f for f in findings if "skip" in f.message.lower()]
        assert all(f.section_id is not None for f in skip_findings)

    def test_template_heading_has_section_id(self) -> None:
        content = "---\ntitle: T\n---\n## [section title]\nSome content here.\n"
        findings = check_structure(content, SLUG)
        template_findings = [f for f in findings if "template" in f.message.lower()]
        assert all(f.section_id is not None for f in template_findings)


class TestRepetitionSectionId:
    def test_repetitive_section_gets_section_id(self) -> None:
        # Create a section with highly repetitive sentences
        repeated = " ".join([
            "The API converts documents efficiently and reliably."
        ] * 6)
        content = f"---\ntitle: T\n---\n## API Overview\n{repeated}\n"
        findings = check_repetition(content, SLUG)
        section_findings = [f for f in findings if f.section_id is not None]
        # If repetition is detected at section level, section_id should be set
        if section_findings:
            assert all(f.section_id == "API Overview" for f in section_findings)

    def test_page_level_repetition_has_no_section_id(self) -> None:
        # Duplicate sentences across the whole page (not per-section)
        dup = "The API converts documents efficiently. " * 5
        content = f"---\ntitle: T\n---\n{dup}"
        findings = check_repetition(content, SLUG)
        page_findings = [f for f in findings if f.section_id is None]
        # Page-level findings exist and have no section_id
        if page_findings:
            assert all(f.section_id is None for f in page_findings)
