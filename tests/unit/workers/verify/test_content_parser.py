"""Unit tests for content_parser.py — TC-5167."""
from __future__ import annotations

from launcher.workers.verify.content_parser import (
    extract_api_calls,
    extract_code_blocks,
    extract_imports,
    normalize_import,
)


# ---------------------------------------------------------------------------
# extract_code_blocks
# ---------------------------------------------------------------------------


def test_extract_code_blocks_single() -> None:
    md = "Some text.\n```python\nimport os\nprint('hello')\n```\nMore text."
    blocks = extract_code_blocks(md)
    assert len(blocks) == 1
    assert blocks[0]["language"] == "python"
    assert "import os" in blocks[0]["code"]


def test_extract_code_blocks_multiple() -> None:
    md = "```python\nimport os\n```\nMiddle.\n```csharp\nusing System;\n```"
    blocks = extract_code_blocks(md)
    assert len(blocks) == 2
    assert blocks[0]["language"] == "python"
    assert blocks[1]["language"] == "csharp"


def test_extract_code_blocks_no_language() -> None:
    md = "```\nsome code\n```"
    blocks = extract_code_blocks(md)
    assert len(blocks) == 1
    assert blocks[0]["language"] == ""


def test_extract_code_blocks_empty_md() -> None:
    blocks = extract_code_blocks("")
    assert blocks == []


def test_extract_code_blocks_line_start() -> None:
    md = "Intro.\n```java\npublic class Foo {}\n```"
    blocks = extract_code_blocks(md)
    # line_start should be the line number of the opening fence (1-indexed)
    assert blocks[0]["line_start"] == 2


# ---------------------------------------------------------------------------
# extract_imports — Python
# ---------------------------------------------------------------------------


def test_extract_imports_python_import() -> None:
    code = "import os\nimport sys\nfrom pathlib import Path\n"
    imports = extract_imports(code, "python")
    assert "import os" in imports
    assert "import sys" in imports
    assert "from pathlib import Path" in imports


def test_extract_imports_python_multiline() -> None:
    code = "import os\n\ndef foo():\n    pass\n"
    imports = extract_imports(code, "python")
    assert "import os" in imports


def test_extract_imports_csharp_using() -> None:
    code = "using System;\nusing Aspose.ThreeD;\n"
    imports = extract_imports(code, "csharp")
    assert "using System;" in imports
    assert "using Aspose.ThreeD;" in imports


def test_extract_imports_java_import() -> None:
    code = "import com.aspose.threed.Scene;\nimport java.util.List;\n"
    imports = extract_imports(code, "java")
    assert "import com.aspose.threed.Scene;" in imports
    assert "import java.util.List;" in imports


def test_extract_imports_unknown_language() -> None:
    code = "import something\n"
    imports = extract_imports(code, "ruby")
    assert imports == []


def test_extract_imports_empty_code() -> None:
    imports = extract_imports("", "python")
    assert imports == []


# ---------------------------------------------------------------------------
# extract_api_calls
# ---------------------------------------------------------------------------


def test_extract_api_calls_python() -> None:
    # Pattern requires UpperCase.lowerCase (e.g. ClassName.memberName)
    code = "node = Scene.root_node\nresult = Mesh.export_fbx()\n"
    calls = extract_api_calls(code, "python")
    assert "Scene.root_node" in calls or "Mesh.export_fbx" in calls


def test_extract_api_calls_csharp() -> None:
    code = "var scene = new Scene();\nvar node = scene.RootNode;\n"
    calls = extract_api_calls(code, "csharp")
    assert isinstance(calls, list)


def test_extract_api_calls_empty() -> None:
    calls = extract_api_calls("", "python")
    assert calls == []


# ---------------------------------------------------------------------------
# normalize_import
# ---------------------------------------------------------------------------


def test_normalize_import_python_bare() -> None:
    result = normalize_import("import aspose.threed", "python")
    assert result == "aspose.threed"


def test_normalize_import_python_from() -> None:
    result = normalize_import("from aspose.threed import Scene", "python")
    assert result == "aspose.threed"


def test_normalize_import_csharp_using() -> None:
    # C#: strips "using " prefix and ";" suffix, preserves case
    result = normalize_import("using Aspose.ThreeD;", "csharp")
    assert result == "Aspose.ThreeD"


def test_normalize_import_java_import() -> None:
    # Java: strips "import " prefix and ";" suffix, preserves case
    result = normalize_import("import com.aspose.threed.Scene;", "java")
    assert result == "com.aspose.threed.Scene"


def test_normalize_import_empty() -> None:
    result = normalize_import("", "python")
    assert result == ""


def test_normalize_import_unknown_language() -> None:
    # Unknown language: returns "" (cannot normalize safely)
    result = normalize_import("require 'aspose'", "ruby")
    assert result == ""


def test_normalize_import_csharp_cs_alias() -> None:
    # "cs" language tag is also recognised
    result = normalize_import("using System.IO;", "cs")
    assert result == "System.IO"


def test_normalize_import_java_whitespace() -> None:
    # Leading whitespace is stripped before normalisation
    result = normalize_import("  import java.util.List;  ", "java")
    assert result == "java.util.List"


def test_normalize_import_csharp_dotnet_alias() -> None:
    # "dotnet" language tag is also recognised
    result = normalize_import("using Aspose.Cells;", "dotnet")
    assert result == "Aspose.Cells"
