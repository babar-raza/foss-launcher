"""Tests for check_code_platform — TC-EVAL-502."""
from __future__ import annotations

from launcher.workers.evaluate.checks.code_platform import check_code_platform


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
