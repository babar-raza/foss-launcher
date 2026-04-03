"""Tests for TC-5329: scan_cpp_contamination() in section_validator.py.

Verifies that:
- Each confirmed .NET/C++CLI contamination pattern is detected
- Valid standard C++ code does NOT trigger false positives
- The XOR operator (a ^ b) is not confused with the managed-pointer ^ syntax
"""
from __future__ import annotations

import pytest

from launcher.workers.generate.section_validator import scan_cpp_contamination


class TestCppContaminationScannerTC5329:
    """Unit tests for scan_cpp_contamination()."""

    # -----------------------------------------------------------------------
    # True-positive tests: each pattern must be detected
    # -----------------------------------------------------------------------

    def test_system_makeobject_detected(self) -> None:
        code = 'auto pres = System::MakeObject<Presentation>("file.pptx");'
        labels = scan_cpp_contamination(code)
        assert "System::MakeObject" in labels

    def test_system_dynamiccast_detected(self) -> None:
        code = 'auto shape = System::DynamicCast<AutoShape>(item);'
        labels = scan_cpp_contamination(code)
        assert "System::DynamicCast" in labels

    def test_system_safecast_detected(self) -> None:
        code = 'auto shape = System::SafeCast<IShape>(item);'
        labels = scan_cpp_contamination(code)
        assert "System::SafeCast" in labels

    def test_system_drawing_detected(self) -> None:
        code = 'fillFormat->set_Color(System::Drawing::Color::get_Blue());'
        labels = scan_cpp_contamination(code)
        assert "System::Drawing" in labels

    def test_system_exception_detected(self) -> None:
        code = 'catch (System::Exception& ex) { /* handle */ }'
        labels = scan_cpp_contamination(code)
        assert "System::Exception" in labels

    def test_gcnew_detected(self) -> None:
        code = 'Presentation^ pres = gcnew Presentation("file.pptx");'
        labels = scan_cpp_contamination(code)
        assert "gcnew" in labels

    def test_managed_pointer_hat_detected(self) -> None:
        """Type^ var syntax is C++/CLI managed pointer — not valid in standard C++."""
        code = 'Presentation^ pres = gcnew Presentation();'
        labels = scan_cpp_contamination(code)
        assert "managed-pointer(^)" in labels

    def test_iinterface_instantiation_detected(self) -> None:
        """IPresentation p(...) is an interface instantiation — not valid C++."""
        code = 'IPresentation presentation("file.pptx");'
        labels = scan_cpp_contamination(code)
        assert "IInterface-instantiation" in labels

    def test_get_accessor_detected(self) -> None:
        """.get_X() .NET property accessor naming is wrong in C++ FOSS."""
        code = 'auto msg = ex->get_Message();'
        labels = scan_cpp_contamination(code)
        assert "get_X()-accessor" in labels

    # -----------------------------------------------------------------------
    # False-positive tests: valid C++ must NOT be flagged
    # -----------------------------------------------------------------------

    def test_valid_direct_construction_not_flagged(self) -> None:
        code = (
            '#include <Aspose/Slides/Foss/presentation.h>\n'
            'using namespace Aspose::Slides::Foss;\n'
            'int main() {\n'
            '    Presentation pres("input.pptx");\n'
            '    pres.save("output.pptx", SaveFormat::PPTX);\n'
            '}'
        )
        labels = scan_cpp_contamination(code)
        assert labels == [], f"Unexpected contamination labels: {labels}"

    def test_xor_operator_not_flagged(self) -> None:
        """XOR operator (a ^ b) has a space before ^ — must not trigger managed-pointer detection."""
        code = 'int result = a ^ b;'
        labels = scan_cpp_contamination(code)
        assert "managed-pointer(^)" not in labels, (
            "XOR operator 'a ^ b' should not trigger managed-pointer detection"
        )

    def test_std_exception_not_flagged(self) -> None:
        code = (
            'try {\n'
            '    Presentation pres("file.pptx");\n'
            '} catch (const std::runtime_error& e) {\n'
            '    std::cerr << e.what();\n'
            '}'
        )
        labels = scan_cpp_contamination(code)
        assert labels == [], f"Unexpected contamination labels: {labels}"

    def test_dynamic_cast_standard_not_flagged(self) -> None:
        """Standard C++ dynamic_cast is NOT the same as System::DynamicCast."""
        code = 'auto shape = dynamic_cast<AutoShape*>(item.get());'
        labels = scan_cpp_contamination(code)
        assert labels == [], f"Unexpected contamination labels: {labels}"

    def test_empty_code_returns_empty(self) -> None:
        labels = scan_cpp_contamination("")
        assert labels == []

    def test_multipattern_all_detected(self) -> None:
        """Multiple patterns in one code block should all be reported."""
        code = (
            'auto pres = System::MakeObject<Presentation>();\n'
            'auto shape = System::DynamicCast<AutoShape>(item);\n'
        )
        labels = scan_cpp_contamination(code)
        assert "System::MakeObject" in labels
        assert "System::DynamicCast" in labels
