"""TC-2910: Tests for W5 _format_api_symbols_block enrichment."""

import pytest
from src.launch.workers.w5_section_writer.multi_pass import _format_api_symbols_block


class TestFormatApiSymbolsBlock:
    """TC-2910: Verify enriched inventory is correctly formatted for LLM prompt."""

    def test_includes_properties(self):
        """Properties appear in the ALLOWED API SYMBOLS block."""
        inventory = {
            "package_name": "aspose-3d",
            "classes": [{
                "name": "Scene",
                "import_path": "aspose.threed.Scene",
                "methods": ["open", "save"],
                "properties": ["root_node", "library"],
            }],
            "functions": [],
            "modules": ["aspose.threed"],
        }
        block = _format_api_symbols_block(inventory)
        assert "properties=[root_node, library]" in block

    def test_includes_constructor(self):
        """Constructor parameters appear in the block."""
        inventory = {
            "package_name": "aspose-3d",
            "classes": [{
                "name": "Scene",
                "import_path": "aspose.threed.Scene",
                "methods": ["save"],
                "constructor": {
                    "parameters": [
                        {"name": "path", "annotation": "str"},
                        {"name": "options", "annotation": "dict"},
                    ]
                },
            }],
            "functions": [],
            "modules": [],
        }
        block = _format_api_symbols_block(inventory)
        assert "constructor(path: str, options: dict)" in block

    def test_includes_constants(self):
        """Class constants appear in the block."""
        inventory = {
            "package_name": "aspose-3d",
            "classes": [{
                "name": "FileFormat",
                "import_path": "aspose.threed.FileFormat",
                "methods": [],
                "class_constants": ["STL", "OBJ", "FBX"],
            }],
            "functions": [],
            "modules": [],
        }
        block = _format_api_symbols_block(inventory)
        assert "constants=[STL, OBJ, FBX]" in block

    def test_omits_empty_fields(self):
        """Empty properties/constructor/constants are not shown."""
        inventory = {
            "package_name": "pkg",
            "classes": [{
                "name": "Simple",
                "import_path": "pkg.Simple",
                "methods": ["run"],
                "properties": [],
                "constructor": None,
                "class_constants": [],
            }],
            "functions": [],
            "modules": [],
        }
        block = _format_api_symbols_block(inventory)
        assert "properties=" not in block
        assert "constructor" not in block
        assert "constants=" not in block
        assert "methods=[run]" in block

    def test_full_enriched_line(self):
        """A fully enriched class produces all sections."""
        inventory = {
            "package_name": "lib",
            "classes": [{
                "name": "Doc",
                "import_path": "lib.Doc",
                "methods": ["save", "load"],
                "properties": ["pages"],
                "constructor": {"parameters": [{"name": "path", "annotation": "str"}]},
                "class_constants": ["PDF", "DOCX"],
            }],
            "functions": [],
            "modules": [],
        }
        block = _format_api_symbols_block(inventory)
        assert "- lib.Doc:" in block
        assert "methods=[save, load]" in block
        assert "properties=[pages]" in block
        assert "constructor(path: str)" in block
        assert "constants=[PDF, DOCX]" in block

    def test_constructor_no_annotation(self):
        """Constructor param without annotation shows just name."""
        inventory = {
            "package_name": "pkg",
            "classes": [{
                "name": "Cls",
                "import_path": "pkg.Cls",
                "methods": [],
                "constructor": {"parameters": [{"name": "data", "annotation": ""}]},
            }],
            "functions": [],
            "modules": [],
        }
        block = _format_api_symbols_block(inventory)
        assert "constructor(data)" in block

    def test_empty_inventory(self):
        """Empty classes list returns empty string."""
        inventory = {"package_name": "pkg", "classes": [], "functions": [], "modules": []}
        block = _format_api_symbols_block(inventory)
        assert block == ""

    def test_caps_properties_at_10(self):
        """Properties capped at 10 items."""
        props = [f"prop_{i}" for i in range(15)]
        inventory = {
            "package_name": "pkg",
            "classes": [{
                "name": "Big",
                "import_path": "pkg.Big",
                "methods": ["m"],
                "properties": props,
            }],
            "functions": [],
            "modules": [],
        }
        block = _format_api_symbols_block(inventory)
        # Should have exactly 10 properties
        prop_match = block.split("properties=[")[1].split("]")[0]
        assert len(prop_match.split(", ")) == 10

    def test_caps_constants_at_10(self):
        """Constants capped at 10 items."""
        consts = [f"CONST_{i}" for i in range(15)]
        inventory = {
            "package_name": "pkg",
            "classes": [{
                "name": "Big",
                "import_path": "pkg.Big",
                "methods": [],
                "class_constants": consts,
            }],
            "functions": [],
            "modules": [],
        }
        block = _format_api_symbols_block(inventory)
        const_match = block.split("constants=[")[1].split("]")[0]
        assert len(const_match.split(", ")) == 10
