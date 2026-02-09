"""TC-995: Template audit tests for structure, parity, and page_role derivation.

Verifies that:
  - All 3 families (3d, cells, note) have identical template trees per subdomain
  - No obsolete placeholder filenames remain in the template directory
  - Blog templates contain no __PLATFORM__ or __LOCALE__ path segments
  - _derive_page_role_from_template() returns correct roles for each template type
  - enumerate_templates() includes page_role in every template descriptor
  - Template file counts per subdomain are within expected ranges
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Set

import pytest

# ---------------------------------------------------------------------------
# Resolve the specs/templates directory relative to the project root.
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[3]
TEMPLATES_DIR = PROJECT_ROOT / "specs" / "templates"

FAMILIES = ["3d", "cells", "note"]
SUBDOMAINS = [
    "blog.aspose.org",
    "docs.aspose.org",
    "kb.aspose.org",
    "products.aspose.org",
    "reference.aspose.org",
]


# ---------------------------------------------------------------------------
# Helper: collect relative paths per family under a given subdomain,
# replacing the family name with a placeholder so we can compare sets.
# ---------------------------------------------------------------------------
def _template_tree_for_family(subdomain: str, family: str) -> Set[str]:
    """Return set of relative paths under subdomain/family with family replaced."""
    family_dir = TEMPLATES_DIR / subdomain / family
    if not family_dir.exists():
        return set()
    paths: Set[str] = set()
    for md_file in family_dir.rglob("*.md"):
        if md_file.name == "README.md":
            continue
        rel = md_file.relative_to(family_dir).as_posix()
        paths.add(rel)
    return paths


# ===================================================================
# Test 1: Family parity verification
# ===================================================================
class TestFamilyParity:
    """All 3 families must have identical template tree structures per subdomain."""

    @pytest.mark.parametrize("subdomain", SUBDOMAINS)
    def test_family_parity(self, subdomain: str) -> None:
        trees: Dict[str, Set[str]] = {}
        for fam in FAMILIES:
            trees[fam] = _template_tree_for_family(subdomain, fam)

        # Each family tree must be non-empty
        for fam in FAMILIES:
            assert trees[fam], (
                f"No templates found for {subdomain}/{fam} "
                f"(directory: {TEMPLATES_DIR / subdomain / fam})"
            )

        # All families must match
        baseline = trees[FAMILIES[0]]
        for fam in FAMILIES[1:]:
            assert trees[fam] == baseline, (
                f"Family parity mismatch for {subdomain}: "
                f"{FAMILIES[0]} vs {fam}.\n"
                f"  Only in {FAMILIES[0]}: {sorted(baseline - trees[fam])}\n"
                f"  Only in {fam}: {sorted(trees[fam] - baseline)}"
            )


# ===================================================================
# Test 2: No obsolete placeholder filenames remain
# ===================================================================
OBSOLETE_PLACEHOLDERS = [
    "__CONVERTER_SLUG__",
    "__FORMAT_SLUG__",
    "__SECTION_PATH__",
    "__TOPIC_SLUG__",
    "__REFERENCE_SLUG__",
]


class TestNoObsoletePlaceholders:
    def test_no_obsolete_placeholder_in_paths(self) -> None:
        violations = []
        for md_file in TEMPLATES_DIR.rglob("*.md"):
            path_str = md_file.relative_to(TEMPLATES_DIR).as_posix()
            for placeholder in OBSOLETE_PLACEHOLDERS:
                if placeholder in path_str:
                    violations.append(f"{path_str} contains {placeholder}")
        assert not violations, (
            f"Found {len(violations)} template(s) with obsolete placeholders:\n"
            + "\n".join(f"  - {v}" for v in violations)
        )


# ===================================================================
# Test 3: Blog templates have no __PLATFORM__ or __LOCALE__
# ===================================================================
class TestBlogTemplateConstraints:
    def test_no_platform_or_locale_in_blog(self) -> None:
        blog_dir = TEMPLATES_DIR / "blog.aspose.org"
        violations = []
        for md_file in blog_dir.rglob("*.md"):
            path_str = md_file.relative_to(blog_dir).as_posix()
            if "__PLATFORM__" in path_str:
                violations.append(f"{path_str} contains __PLATFORM__")
            if "__LOCALE__" in path_str:
                violations.append(f"{path_str} contains __LOCALE__")
        assert not violations, (
            "Blog templates must not use __PLATFORM__ or __LOCALE__:\n"
            + "\n".join(f"  - {v}" for v in violations)
        )


# ===================================================================
# Test 4: page_role derivation
# ===================================================================
class TestPageRoleDerivation:
    """Test _derive_page_role_from_template() with representative inputs."""

    @pytest.mark.parametrize(
        "filename, relative_path, section, expected_role",
        [
            # _index.md in getting-started/ -> workflow_page (subsection index)
            ("_index.md", "getting-started/_index.md", "docs", "workflow_page"),
            # _index.md in developer-guide/ -> comprehensive_guide
            ("_index.md", "developer-guide/_index.md", "docs", "comprehensive_guide"),
            # _index.md at root with section="docs" -> toc
            ("_index.md", "_index.md", "docs", "toc"),
            # feature.variant-minimal.md -> workflow_page
            (
                "feature.variant-minimal.md",
                "developer-guide/feature.variant-minimal.md",
                "docs",
                "workflow_page",
            ),
            # howto.variant-standard.md -> feature_showcase
            (
                "howto.variant-standard.md",
                "howto.variant-standard.md",
                "kb",
                "feature_showcase",
            ),
            # reference.variant-standard.md with section="reference" -> api_reference
            (
                "reference.variant-standard.md",
                "reference.variant-standard.md",
                "reference",
                "api_reference",
            ),
            # installation.md -> workflow_page
            ("installation.md", "getting-started/installation.md", "docs", "workflow_page"),
        ],
        ids=[
            "subsection_index_getting_started",
            "developer_guide_index",
            "root_index_docs",
            "feature_variant",
            "howto_variant",
            "reference_variant",
            "installation",
        ],
    )
    def test_derive_page_role(
        self,
        filename: str,
        relative_path: str,
        section: str,
        expected_role: str,
    ) -> None:
        from launch.workers.w4_ia_planner.worker import _derive_page_role_from_template

        result = _derive_page_role_from_template(filename, relative_path, section)
        assert result == expected_role, (
            f"_derive_page_role_from_template({filename!r}, {relative_path!r}, {section!r}) "
            f"returned {result!r}, expected {expected_role!r}"
        )


# ===================================================================
# Test 5: Template descriptor includes page_role
# ===================================================================
class TestEnumerateTemplatesPageRole:
    """enumerate_templates() must include a non-empty page_role in every descriptor."""

    def test_page_role_in_descriptors(self, tmp_path: Path) -> None:
        from launch.workers.w4_ia_planner.worker import enumerate_templates

        # Build a minimal mock template directory
        subdomain = "docs.aspose.org"
        family = "testfam"
        base = tmp_path / subdomain / family / "__LOCALE__"

        # Root _index
        base.mkdir(parents=True, exist_ok=True)
        (base / "_index.md").write_text("---\ntitle: Root\n---\n", encoding="utf-8")

        # getting-started/_index
        gs_dir = base / "getting-started"
        gs_dir.mkdir(parents=True, exist_ok=True)
        (gs_dir / "_index.md").write_text(
            "---\ntitle: Getting Started\n---\n", encoding="utf-8"
        )
        (gs_dir / "installation.md").write_text(
            "---\ntitle: Installation\n---\n", encoding="utf-8"
        )

        descriptors = enumerate_templates(
            template_dir=tmp_path,
            subdomain=subdomain,
            family=family,
            locale="en",
        )

        assert len(descriptors) >= 3, (
            f"Expected at least 3 template descriptors, got {len(descriptors)}: "
            f"{[d['filename'] for d in descriptors]}"
        )

        for desc in descriptors:
            assert "page_role" in desc, (
                f"Template descriptor missing page_role: {desc}"
            )
            assert isinstance(desc["page_role"], str), (
                f"page_role must be a string, got {type(desc['page_role']).__name__}: {desc}"
            )
            assert desc["page_role"], (
                f"page_role must be non-empty for {desc['filename']}"
            )


# ===================================================================
# Test 6: Template file count ranges
# ===================================================================
EXPECTED_COUNTS = {
    "blog.aspose.org": (15, 25),
    "docs.aspose.org": (20, 35),
    "kb.aspose.org": (15, 25),
    "products.aspose.org": (3, 10),
    "reference.aspose.org": (8, 15),
}


class TestTemplateFileCounts:
    @pytest.mark.parametrize(
        "subdomain, min_count, max_count",
        [
            (sd, lo, hi)
            for sd, (lo, hi) in EXPECTED_COUNTS.items()
        ],
        ids=list(EXPECTED_COUNTS.keys()),
    )
    def test_file_count_in_range(
        self, subdomain: str, min_count: int, max_count: int
    ) -> None:
        sub_dir = TEMPLATES_DIR / subdomain
        assert sub_dir.exists(), f"Subdomain directory not found: {sub_dir}"
        count = len(list(sub_dir.rglob("*.md")))
        assert min_count <= count <= max_count, (
            f"{subdomain} has {count} .md files, expected {min_count}-{max_count}"
        )
