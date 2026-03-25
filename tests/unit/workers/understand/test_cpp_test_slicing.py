"""TC-CPP-404: Tests for C++ test slicing in _snippets.py."""
from __future__ import annotations

import textwrap
from types import SimpleNamespace

import pytest

from launcher.workers.understand.extract._snippets import (
    _extract_cpp_test_slices,
    _extract_cpp_include_block,
    _sanitize_cpp_test_body,
)


def _make_api_surface(classes: list[str] | None = None):
    return SimpleNamespace(
        public_classes=classes or ["Presentation", "Slide"],
        public_methods=[],
        import_allowlist=[],
    )


class TestCppTestSlicing:
    """Verify C++ test extraction from Google Test and Catch2 files."""

    def test_google_test_extracted(self):
        """TEST() macro body is extracted."""
        code = textwrap.dedent("""
            #include <gtest/gtest.h>
            #include "Presentation.h"

            TEST(PresentationTest, LoadPPTX) {
                auto pres = Presentation::Load("test.pptx");
                ASSERT_NE(pres, nullptr);
                int count = pres->GetSlideCount();
            }
        """).strip()
        result = _extract_cpp_test_slices(code, _make_api_surface())
        assert len(result) >= 1
        assert "Presentation" in result[0]

    def test_test_f_extracted(self):
        """TEST_F() fixture macro body is extracted."""
        code = textwrap.dedent("""
            #include "Presentation.h"

            class PresentationFixture : public ::testing::Test {};

            TEST_F(PresentationFixture, SaveSlide) {
                Presentation pres;
                pres.Save("out.pptx");
            }
        """).strip()
        result = _extract_cpp_test_slices(code, _make_api_surface())
        assert len(result) >= 1
        assert "Presentation" in result[0]

    def test_assertions_stripped(self):
        """ASSERT_* and EXPECT_* lines are removed from slices."""
        code = textwrap.dedent("""
            #include "Presentation.h"

            TEST(Foo, Bar) {
                auto p = Presentation::Load("test.pptx");
                ASSERT_NE(p, nullptr);
                EXPECT_EQ(p->GetSlideCount(), 3);
                auto slide = p->GetSlide(0);
            }
        """).strip()
        result = _extract_cpp_test_slices(code, _make_api_surface())
        assert len(result) >= 1
        assert "ASSERT_" not in result[0]
        assert "EXPECT_" not in result[0]
        assert "Presentation" in result[0]

    def test_include_block_prepended(self):
        """#include lines (non-test) are prepended to slices."""
        code = textwrap.dedent("""
            #include <gtest/gtest.h>
            #include "Presentation.h"
            #include "Slide.h"

            TEST(SlideTest, Create) {
                Presentation pres;
                auto slide = pres.AddSlide();
            }
        """).strip()
        result = _extract_cpp_test_slices(code, _make_api_surface())
        assert len(result) >= 1
        assert '#include "Presentation.h"' in result[0]
        assert "gtest" not in result[0]

    def test_catch2_test_case_extracted(self):
        """Catch2 TEST_CASE() is extracted."""
        code = textwrap.dedent("""
            #include "Presentation.h"

            TEST_CASE("Load presentation", "[presentation]") {
                auto pres = Presentation::Load("file.pptx");
                REQUIRE(pres != nullptr);
            }
        """).strip()
        result = _extract_cpp_test_slices(code, _make_api_surface())
        assert len(result) >= 1
        assert "Presentation" in result[0]

    def test_empty_code_returns_empty(self):
        """Empty input returns empty list."""
        assert _extract_cpp_test_slices("", _make_api_surface()) == []

    def test_no_test_macros_returns_empty(self):
        """Code without test macros returns empty list."""
        code = textwrap.dedent("""
            #include "Presentation.h"
            int main() { return 0; }
        """).strip()
        result = _extract_cpp_test_slices(code, _make_api_surface())
        assert result == []


class TestCppIncludeBlock:
    """Verify _extract_cpp_include_block."""

    def test_filters_test_framework_includes(self):
        code = '#include <gtest/gtest.h>\n#include "Presentation.h"\n'
        result = _extract_cpp_include_block(code)
        assert "gtest" not in result
        assert "Presentation.h" in result


class TestSanitizeCppTestBody:
    """Verify _sanitize_cpp_test_body."""

    def test_strips_assert_lines(self):
        lines = [
            "    auto p = Load();",
            "    ASSERT_NE(p, nullptr);",
            "    EXPECT_EQ(p->Count(), 3);",
            "    auto s = p->Get(0);",
        ]
        result = _sanitize_cpp_test_body(lines)
        assert "ASSERT_" not in result
        assert "EXPECT_" not in result
        assert "Load()" in result
        assert "Get(0)" in result
