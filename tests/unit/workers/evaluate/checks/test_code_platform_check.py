"""Tests for check_code_platform — TC-EVAL-502, and check_ecosystem_contamination — TC-5329."""
from __future__ import annotations

from launcher.workers.evaluate.checks.code_platform import (
    check_code_platform,
    check_ecosystem_contamination,
)


class TestCodePlatformCheck:
    def test_python_page_with_python_code_no_finding(self) -> None:
        content = "---\nplatform: python\n---\n\n```python\nimport aspose.cells\n```\n"
        findings = check_code_platform(content, "test/slug")
        lang_findings = [f for f in findings if "language" in f.message.lower()]
        assert lang_findings == []

    def test_python_page_with_csharp_code_flagged(self) -> None:
        content = "---\nplatform: python\n---\n\n```csharp\nvar wb = new Workbook();\n```\n"
        findings = check_code_platform(content, "test/slug")
        assert any("csharp" in f.message.lower() for f in findings)

    def test_python_page_with_pip_install_ok(self) -> None:
        content = "---\nplatform: python\n---\n\nInstall with:\n```bash\npip install aspose-cells\n```\n"
        findings = check_code_platform(content, "test/slug")
        assert findings == []

    def test_python_page_with_nuget_install_flagged(self) -> None:
        content = "---\nplatform: python\n---\n\nInstall with:\n```bash\nnuget install Aspose.Cells\n```\n"
        findings = check_code_platform(content, "test/slug")
        assert any("nuget" in f.message.lower() for f in findings)

    def test_cpp_page_with_pip_install_flagged(self) -> None:
        content = "---\nplatform: cpp\n---\n\n```bash\npip install aspose\n```\n"
        findings = check_code_platform(content, "test/slug")
        assert any("pip" in f.message.lower() for f in findings)

    def test_no_platform_frontmatter_no_findings(self) -> None:
        content = "---\ntitle: test\n---\n\n```java\nSystem.out.println();\n```\n"
        findings = check_code_platform(content, "test/slug")
        assert findings == []

    def test_dotnet_page_with_java_code_flagged(self) -> None:
        content = "---\nplatform: dotnet\n---\n\n```java\nWorkbook wb = new Workbook();\n```\n"
        findings = check_code_platform(content, "test/slug")
        assert any("java" in f.message.lower() for f in findings)

    def test_java_page_with_java_code_ok(self) -> None:
        content = "---\nplatform: java\n---\n\n```java\nWorkbook wb = new Workbook();\n```\n"
        findings = check_code_platform(content, "test/slug")
        lang_findings = [f for f in findings if "language" in f.message.lower()]
        assert lang_findings == []


def _cpp_page(code_body: str, lang: str = "cpp") -> str:
    """Helper: wrap code_body in a cpp-platform page with the given fence language."""
    return f"---\nplatform: cpp\n---\n\n```{lang}\n{code_body}\n```\n"


class TestEcosystemContaminationTC5329:
    """Tests for check_ecosystem_contamination() — TC-5329."""

    # True-positive tests: confirmed .NET/C++CLI patterns on cpp pages

    def test_system_makeobject_high_finding(self) -> None:
        content = _cpp_page('auto pres = System::MakeObject<Presentation>("file.pptx");')
        findings = check_ecosystem_contamination(content, "test/slug")
        ec = [f for f in findings if f.check == "ecosystem_contamination"]
        assert ec, "Expected ecosystem_contamination finding for System::MakeObject"
        assert all(f.severity == "high" for f in ec)
        assert any("System::MakeObject" in f.message for f in ec)

    def test_system_dynamiccast_flagged(self) -> None:
        content = _cpp_page('auto s = System::DynamicCast<AutoShape>(item);')
        findings = check_ecosystem_contamination(content, "test/slug")
        assert any("System::DynamicCast" in f.message for f in findings)

    def test_system_drawing_flagged(self) -> None:
        content = _cpp_page('fillFormat->set_Color(System::Drawing::Color::get_Blue());')
        findings = check_ecosystem_contamination(content, "test/slug")
        assert any("System::Drawing" in f.message for f in findings)

    def test_system_exception_flagged(self) -> None:
        content = _cpp_page('catch (System::Exception& ex) { }')
        findings = check_ecosystem_contamination(content, "test/slug")
        assert any("System::Exception" in f.message for f in findings)

    def test_gcnew_flagged(self) -> None:
        content = _cpp_page('Presentation^ p = gcnew Presentation();')
        findings = check_ecosystem_contamination(content, "test/slug")
        assert any("gcnew" in f.message for f in findings)

    def test_managed_pointer_hat_flagged(self) -> None:
        content = _cpp_page('Presentation^ pres = nullptr;')
        findings = check_ecosystem_contamination(content, "test/slug")
        assert any("managed-pointer" in f.message.lower() for f in findings)

    def test_iinterface_instantiation_flagged(self) -> None:
        content = _cpp_page('IPresentation presentation("file.pptx");')
        findings = check_ecosystem_contamination(content, "test/slug")
        assert any("IInterface" in f.message for f in findings)

    def test_get_accessor_flagged(self) -> None:
        content = _cpp_page('auto msg = ex->get_Message();')
        findings = check_ecosystem_contamination(content, "test/slug")
        assert any("get_X" in f.message for f in findings)

    # False-positive tests: valid C++ must NOT be flagged

    def test_valid_cpp_construction_not_flagged(self) -> None:
        code = (
            'using namespace Aspose::Slides::Foss;\n'
            'int main() {\n'
            '    Presentation pres("input.pptx");\n'
            '    pres.save("output.pptx", SaveFormat::PPTX);\n'
            '}'
        )
        content = _cpp_page(code)
        findings = check_ecosystem_contamination(content, "test/slug")
        assert findings == [], f"Unexpected findings for valid C++: {findings}"

    def test_xor_operator_not_flagged(self) -> None:
        """a ^ b (XOR) must not trigger managed-pointer detection."""
        content = _cpp_page('int r = a ^ b;')
        findings = check_ecosystem_contamination(content, "test/slug")
        hat_findings = [f for f in findings if "managed-pointer" in f.message.lower()]
        assert hat_findings == []

    def test_non_cpp_page_returns_empty(self) -> None:
        """check_ecosystem_contamination must be silent on Python pages."""
        content = (
            "---\nplatform: python\n---\n\n"
            '```python\nimport aspose_slides_foss\n```\n'
        )
        findings = check_ecosystem_contamination(content, "test/slug")
        assert findings == []

    def test_python_fence_on_cpp_page_not_checked_by_ecosystem(self) -> None:
        """check_ecosystem_contamination only checks cpp/c++/c fences; python fence handled by code_platform."""
        content = (
            "---\nplatform: cpp\n---\n\n"
            '```python\nimport aspose_slides_foss\n```\n'
        )
        findings = check_ecosystem_contamination(content, "test/slug")
        # Should not fire — this is handled by check_code_platform, not ecosystem check
        assert findings == []
