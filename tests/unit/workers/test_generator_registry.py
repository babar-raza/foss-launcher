"""Tests for the W5 Generator Plugin Registry.

Validates:
- GeneratorRegistry stores and retrieves generators correctly
- Default generators are loaded lazily on first access
- Blog aliases (announcement, blog_announcement) resolve correctly
- TOC generator is marked as requiring page_plan
- Custom generators can be registered at runtime
- Registry introspection (all_roles, has, len, contains)
"""

import pytest

from launch.workers.w5_section_writer.generators import (
    GeneratorRegistry,
    GENERATOR_REGISTRY,
    get_registry,
)


class TestGeneratorRegistry:
    """Tests for the GeneratorRegistry class."""

    def test_empty_registry(self):
        reg = GeneratorRegistry()
        assert len(reg) == 0
        assert reg.all_roles == []
        assert reg.get("faq") is None

    def test_register_and_get(self):
        reg = GeneratorRegistry()
        mock_gen = lambda page, pf, sc, **kw: "content"
        reg.register("faq", mock_gen, description="FAQ generator")
        assert reg.has("faq")
        assert reg.get("faq") is mock_gen

    def test_register_with_aliases(self):
        reg = GeneratorRegistry()
        mock_gen = lambda page, pf, sc, **kw: "blog content"
        reg.register("blog", mock_gen, aliases=["announcement", "blog_announcement"])
        assert reg.has("blog")
        assert reg.has("announcement")
        assert reg.has("blog_announcement")
        assert reg.get("announcement") is mock_gen

    def test_requires_page_plan(self):
        reg = GeneratorRegistry()
        mock_gen = lambda page, pf, pp: "toc"
        reg.register("toc", mock_gen, requires_page_plan=True)
        assert reg.requires_page_plan("toc")
        assert not reg.requires_page_plan("unknown_role")

    def test_all_roles_sorted(self):
        reg = GeneratorRegistry()
        reg.register("faq", lambda *a, **k: "")
        reg.register("blog", lambda *a, **k: "")
        reg.register("tutorial", lambda *a, **k: "")
        assert reg.all_roles == ["blog", "faq", "tutorial"]

    def test_len_and_contains(self):
        reg = GeneratorRegistry()
        assert len(reg) == 0
        assert "faq" not in reg
        reg.register("faq", lambda *a, **k: "")
        assert len(reg) == 1
        assert "faq" in reg

    def test_repr(self):
        reg = GeneratorRegistry()
        reg.register("faq", lambda *a, **k: "")
        assert "GeneratorRegistry" in repr(reg)
        assert "faq" in repr(reg)

    def test_get_unknown_returns_none(self):
        reg = GeneratorRegistry()
        assert reg.get("nonexistent") is None


class TestDefaultRegistry:
    """Tests for the default GENERATOR_REGISTRY and get_registry()."""

    def test_get_registry_returns_populated(self):
        """Default registry should have all 9 standard generators loaded."""
        reg = get_registry()
        assert len(reg) >= 9  # 9 roles + 2 blog aliases = 11

    def test_default_generators_registered(self):
        """All standard page_roles should be registered."""
        reg = get_registry()
        expected_roles = [
            "toc", "comprehensive_guide", "feature_showcase",
            "troubleshooting", "faq", "best_practices",
            "tutorial", "blog", "performance_guide",
        ]
        for role in expected_roles:
            assert reg.has(role), f"Missing generator for page_role: {role}"

    def test_blog_aliases_registered(self):
        """Blog aliases should resolve to the same generator."""
        reg = get_registry()
        assert reg.has("announcement")
        assert reg.has("blog_announcement")
        assert reg.get("blog") is reg.get("announcement")
        assert reg.get("blog") is reg.get("blog_announcement")

    def test_toc_requires_page_plan(self):
        """TOC generator should be marked as requiring page_plan."""
        reg = get_registry()
        assert reg.requires_page_plan("toc")

    def test_non_toc_dont_require_page_plan(self):
        """Non-TOC generators should NOT require page_plan."""
        reg = get_registry()
        for role in ["faq", "tutorial", "blog", "troubleshooting"]:
            assert not reg.requires_page_plan(role), f"{role} should not require page_plan"

    def test_generators_are_callable(self):
        """All registered generators should be callable."""
        reg = get_registry()
        for role in reg.all_roles:
            gen_fn = reg.get(role)
            assert callable(gen_fn), f"Generator for {role} is not callable"

    def test_custom_registration_on_default(self):
        """Custom generators can be registered on the default registry."""
        reg = get_registry()
        initial_count = len(reg)
        custom_gen = lambda page, pf, sc, **kw: "custom content"
        reg.register("_test_custom_role", custom_gen, description="Custom test generator")
        assert len(reg) == initial_count + 1
        assert reg.get("_test_custom_role") is custom_gen
        # Clean up
        del reg._generators["_test_custom_role"]
        del reg._metadata["_test_custom_role"]

    def test_idempotent_initialization(self):
        """Calling get_registry() multiple times should not re-register."""
        reg1 = get_registry()
        count1 = len(reg1)
        reg2 = get_registry()
        count2 = len(reg2)
        assert count1 == count2
        assert reg1 is reg2  # Same registry instance
