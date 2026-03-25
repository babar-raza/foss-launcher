"""Unit tests for check_api_identifiers — TC-REG-301 context-aware method checking.

Tests verify that:
1. Method calls on tracked library class instances bypass _ALWAYS_ALLOWED_METHODS
2. Method calls on untracked variables still use the generic allowlist
3. Bare property access on tracked instances flags unknown attributes
4. Pre-existing behavior (unknown classes, property-as-method) is preserved
"""
from __future__ import annotations

from types import SimpleNamespace

from launcher.workers.evaluate.checks.api_verification import check_api_identifiers


def _make_surface(
    public_classes: list[str] | None = None,
    class_briefs: list | None = None,
    api_identifiers: list[str] | None = None,
    confidence: str = "high",
) -> SimpleNamespace:
    """Build a minimal ApiSurface-like object for testing."""
    return SimpleNamespace(
        public_classes=public_classes or [],
        class_briefs=class_briefs or [],
        api_identifiers=api_identifiers or [],
        confidence=confidence,
    )


def _make_brief(
    name: str,
    methods: list[str] | None = None,
    properties: list[str] | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        name=name,
        methods=methods or [],
        properties=properties or [],
        typed_methods=[],
        typed_properties=[],
    )


def _md(code: str) -> str:
    """Wrap Python code in a markdown code block."""
    return f"---\ntitle: Test\n---\n\n```python\n{code}\n```\n"


# ---------------------------------------------------------------------------
# TC-REG-301: Context-aware method checking
# ---------------------------------------------------------------------------

class TestContextAwareMethodChecking:
    """When a variable is assigned from a known library class, method calls
    on that variable bypass _ALWAYS_ALLOWED_METHODS and are checked against
    the class's actual methods."""

    def test_tracked_receiver_get_flagged(self):
        """cells.get() should be flagged when Cells has no 'get' method."""
        brief = _make_brief("Cells", methods=["clear", "merge"])
        surface = _make_surface(
            public_classes=["Cells", "Workbook"],
            class_briefs=[brief],
        )
        content = _md("cells = Cells()\ncells.get(0, 0)")
        findings = check_api_identifiers(content, "test-slug", api_surface=surface)
        method_findings = [f for f in findings if f.check == "api_identifier_unknown_method"]
        assert len(method_findings) >= 1
        assert any("get" in f.message for f in method_findings)

    def test_tracked_receiver_known_method_passes(self):
        """cells.merge() should NOT be flagged when merge is in Cells.methods."""
        brief = _make_brief("Cells", methods=["clear", "merge"])
        surface = _make_surface(
            public_classes=["Cells", "Workbook"],
            class_briefs=[brief],
        )
        content = _md("cells = Cells()\ncells.merge(0, 0, 5, 5)")
        findings = check_api_identifiers(content, "test-slug", api_surface=surface)
        method_findings = [f for f in findings if f.check == "api_identifier_unknown_method"]
        assert len(method_findings) == 0

    def test_untracked_receiver_get_allowed(self):
        """my_dict.get() should NOT be flagged — receiver is not tracked."""
        brief = _make_brief("Cells", methods=["clear", "merge"])
        surface = _make_surface(
            public_classes=["Cells"],
            class_briefs=[brief],
        )
        content = _md('my_dict = {"a": 1}\nresult = my_dict.get("a")')
        findings = check_api_identifiers(content, "test-slug", api_surface=surface)
        method_findings = [f for f in findings if f.check == "api_identifier_unknown_method"]
        assert len(method_findings) == 0

    def test_receiver_name_matches_class_lowercase(self):
        """When receiver name is lowercase version of a known class (e.g. 'cells'),
        it should be treated as a library instance even without explicit assignment."""
        brief = _make_brief("Cells", methods=["clear", "merge"])
        surface = _make_surface(
            public_classes=["Cells"],
            class_briefs=[brief],
        )
        content = _md("cells.get(0, 0)")
        findings = check_api_identifiers(content, "test-slug", api_surface=surface)
        method_findings = [f for f in findings if f.check == "api_identifier_unknown_method"]
        assert len(method_findings) >= 1
        assert any("get" in f.message for f in method_findings)

    def test_tracked_receiver_save_on_workbook(self):
        """wb.save() should pass when Workbook has 'save' method."""
        brief = _make_brief("Workbook", methods=["save", "load"])
        surface = _make_surface(
            public_classes=["Workbook"],
            class_briefs=[brief],
        )
        content = _md('wb = Workbook()\nwb.save("output.xlsx")')
        findings = check_api_identifiers(content, "test-slug", api_surface=surface)
        method_findings = [f for f in findings if f.check == "api_identifier_unknown_method"]
        assert len(method_findings) == 0

    def test_tracked_receiver_save_flagged_when_not_method(self):
        """wb.save() should be flagged when Workbook does NOT have 'save' method."""
        brief = _make_brief("Workbook", methods=["load"])
        surface = _make_surface(
            public_classes=["Workbook"],
            class_briefs=[brief],
        )
        content = _md('wb = Workbook()\nwb.save("output.xlsx")')
        findings = check_api_identifiers(content, "test-slug", api_surface=surface)
        method_findings = [f for f in findings if f.check == "api_identifier_unknown_method"]
        assert len(method_findings) >= 1
        assert any("save" in f.message for f in method_findings)


# ---------------------------------------------------------------------------
# TC-REG-301: Bare property access detection
# ---------------------------------------------------------------------------

class TestPropertyAccessDetection:
    """Bare property access (no parens) on tracked library instances flags
    unknown attributes."""

    def test_unknown_property_flagged(self):
        """workbook.worksheets should be flagged when 'worksheets' is not known."""
        brief = _make_brief("Workbook", methods=["save"], properties=["name"])
        surface = _make_surface(
            public_classes=["Workbook"],
            class_briefs=[brief],
        )
        content = _md("wb = Workbook()\nsheets = wb.worksheets")
        findings = check_api_identifiers(content, "test-slug", api_surface=surface)
        prop_findings = [f for f in findings if f.check == "api_identifier_unknown_property"]
        assert len(prop_findings) >= 1
        assert any("worksheets" in f.message for f in prop_findings)

    def test_known_property_passes(self):
        """workbook.name should NOT be flagged when 'name' is a known property."""
        brief = _make_brief("Workbook", methods=["save"], properties=["name"])
        surface = _make_surface(
            public_classes=["Workbook"],
            class_briefs=[brief],
        )
        content = _md("wb = Workbook()\ntitle = wb.name")
        findings = check_api_identifiers(content, "test-slug", api_surface=surface)
        prop_findings = [f for f in findings if f.check == "api_identifier_unknown_property"]
        assert len(prop_findings) == 0

    def test_untracked_receiver_property_not_flagged(self):
        """Bare property access on untracked receiver should not be flagged."""
        brief = _make_brief("Workbook", methods=["save"], properties=["name"])
        surface = _make_surface(
            public_classes=["Workbook"],
            class_briefs=[brief],
        )
        content = _md("result = my_obj.something")
        findings = check_api_identifiers(content, "test-slug", api_surface=surface)
        prop_findings = [f for f in findings if f.check == "api_identifier_unknown_property"]
        assert len(prop_findings) == 0

    def test_property_access_only_at_high_confidence(self):
        """Property access detection should skip at medium confidence."""
        brief = _make_brief("Workbook", methods=["save"], properties=["name"])
        surface = _make_surface(
            public_classes=["Workbook"],
            class_briefs=[brief],
            confidence="medium",
        )
        content = _md("wb = Workbook()\nsheets = wb.worksheets")
        findings = check_api_identifiers(content, "test-slug", api_surface=surface)
        prop_findings = [f for f in findings if f.check == "api_identifier_unknown_property"]
        assert len(prop_findings) == 0


# ---------------------------------------------------------------------------
# Pre-existing behavior preservation
# ---------------------------------------------------------------------------

class TestPreExistingBehavior:
    """Ensure pre-existing checks still work correctly."""

    def test_unknown_class_flagged(self):
        """Unknown class instantiation should still be flagged HIGH."""
        brief = _make_brief("Workbook", methods=["save"])
        surface = _make_surface(
            public_classes=["Workbook"],
            class_briefs=[brief],
        )
        content = _md("mgr = WorkflowManager()")
        findings = check_api_identifiers(content, "test-slug", api_surface=surface)
        class_findings = [f for f in findings if f.check == "api_identifier_unknown_class"]
        assert len(class_findings) >= 1
        assert class_findings[0].severity == "high"

    def test_none_surface_returns_empty(self):
        findings = check_api_identifiers(_md("x = Foo()"), "slug", api_surface=None)
        assert findings == []

    def test_low_confidence_skips(self):
        surface = _make_surface(public_classes=["Workbook"], confidence="low")
        findings = check_api_identifiers(_md("x = Foo()"), "slug", api_surface=surface)
        assert findings == []

    def test_known_class_not_flagged(self):
        brief = _make_brief("Workbook", methods=["save"])
        surface = _make_surface(
            public_classes=["Workbook"],
            class_briefs=[brief],
        )
        content = _md("wb = Workbook()")
        findings = check_api_identifiers(content, "test-slug", api_surface=surface)
        class_findings = [f for f in findings if f.check == "api_identifier_unknown_class"]
        assert len(class_findings) == 0


# ---------------------------------------------------------------------------
# REG-H-01: Property access false-positive filtering
# ---------------------------------------------------------------------------

class TestPropertyAccessFalsePositives:
    """REG-H-01: Property regex must NOT match inside imports, strings, or comments."""

    def test_import_line_not_flagged(self):
        """'from aspose.cells import Workbook' should produce zero property findings."""
        brief = _make_brief("Workbook", methods=["save"], properties=["name"])
        surface = _make_surface(
            public_classes=["Workbook"],
            class_briefs=[brief],
        )
        content = _md("from aspose.cells import Workbook\nwb = Workbook()")
        findings = check_api_identifiers(content, "test-slug", api_surface=surface)
        prop_findings = [f for f in findings if f.check == "api_identifier_unknown_property"]
        assert len(prop_findings) == 0

    def test_string_literal_not_flagged(self):
        """'name = \"workbook.worksheets\"' should produce zero property findings."""
        brief = _make_brief("Workbook", methods=["save"], properties=["name"])
        surface = _make_surface(
            public_classes=["Workbook"],
            class_briefs=[brief],
        )
        content = _md('path = "workbook.worksheets"')
        findings = check_api_identifiers(content, "test-slug", api_surface=surface)
        prop_findings = [f for f in findings if f.check == "api_identifier_unknown_property"]
        assert len(prop_findings) == 0

    def test_comment_line_not_flagged(self):
        """'# workbook.worksheets is a property' should produce zero property findings."""
        brief = _make_brief("Workbook", methods=["save"], properties=["name"])
        surface = _make_surface(
            public_classes=["Workbook"],
            class_briefs=[brief],
        )
        content = _md("# workbook.worksheets is a property\nwb = Workbook()")
        findings = check_api_identifiers(content, "test-slug", api_surface=surface)
        prop_findings = [f for f in findings if f.check == "api_identifier_unknown_property"]
        assert len(prop_findings) == 0

    def test_import_config_variable_not_filtered(self):
        """'import_config.name' on a tracked receiver should NOT be filtered
        (variable happens to start with 'import' but it's not an import statement)."""
        brief = _make_brief("Workbook", methods=["save"], properties=["name"])
        surface = _make_surface(
            public_classes=["Workbook"],
            class_briefs=[brief],
        )
        # 'workbook' is a tracked receiver (lowercase of Workbook),
        # and 'worksheets' is unknown — should still flag
        content = _md("import_data = 1\nworkbook.worksheets")
        findings = check_api_identifiers(content, "test-slug", api_surface=surface)
        prop_findings = [f for f in findings if f.check == "api_identifier_unknown_property"]
        assert len(prop_findings) >= 1


# ---------------------------------------------------------------------------
# REG-H-06: Expanded assignment tracking
# ---------------------------------------------------------------------------

class TestExpandedAssignmentTracking:
    """REG-H-06: _ASSIGNMENT_RE matches type annotations and module-qualified constructors."""

    def test_type_annotated_assignment_tracked(self):
        """'wb: Workbook = Workbook()' then 'wb.get()' should flag."""
        brief = _make_brief("Workbook", methods=["save", "load"])
        surface = _make_surface(
            public_classes=["Workbook"],
            class_briefs=[brief],
        )
        content = _md("wb: Workbook = Workbook()\nwb.get(0)")
        findings = check_api_identifiers(content, "test-slug", api_surface=surface)
        method_findings = [f for f in findings if f.check == "api_identifier_unknown_method"]
        assert len(method_findings) >= 1
        assert any("get" in f.message for f in method_findings)

    def test_module_qualified_constructor_tracked(self):
        """'wb = aspose.cells.Workbook()' then 'wb.get()' should flag."""
        brief = _make_brief("Workbook", methods=["save", "load"])
        surface = _make_surface(
            public_classes=["Workbook"],
            class_briefs=[brief],
        )
        content = _md("wb = aspose.cells.Workbook()\nwb.get(0)")
        findings = check_api_identifiers(content, "test-slug", api_surface=surface)
        method_findings = [f for f in findings if f.check == "api_identifier_unknown_method"]
        assert len(method_findings) >= 1
        assert any("get" in f.message for f in method_findings)

    def test_type_annotated_known_method_passes(self):
        """'wb: Workbook = Workbook()' then 'wb.save()' should NOT flag."""
        brief = _make_brief("Workbook", methods=["save", "load"])
        surface = _make_surface(
            public_classes=["Workbook"],
            class_briefs=[brief],
        )
        content = _md('wb: Workbook = Workbook()\nwb.save("out.xlsx")')
        findings = check_api_identifiers(content, "test-slug", api_surface=surface)
        method_findings = [f for f in findings if f.check == "api_identifier_unknown_method"]
        assert len(method_findings) == 0


# ---------------------------------------------------------------------------
# TC-EVAL-301: Severity escalation for tracked vs untracked receivers
# ---------------------------------------------------------------------------

class TestMethodSeverityEscalation:
    """TC-EVAL-301: Tracked-receiver unknown method → HIGH, untracked → MEDIUM."""

    def test_tracked_receiver_unknown_method_is_high(self):
        """When receiver is assigned from a known class, unknown method is HIGH."""
        brief = _make_brief("Workbook", methods=["save"])
        surface = _make_surface(
            public_classes=["Workbook"],
            class_briefs=[brief],
        )
        content = _md("wb = Workbook()\nwb.create_chart()")
        findings = check_api_identifiers(content, "test-slug", api_surface=surface)
        method_findings = [f for f in findings if f.check == "api_identifier_unknown_method"]
        assert len(method_findings) >= 1
        assert method_findings[0].severity == "high"

    def test_untracked_receiver_unknown_method_is_medium(self):
        """When receiver is NOT a tracked library instance, unknown method is MEDIUM."""
        brief = _make_brief("Workbook", methods=["save"])
        surface = _make_surface(
            public_classes=["Workbook"],
            class_briefs=[brief],
            confidence="medium",  # method checks run at medium confidence
        )
        # 'obj' is not assigned from any known class → untracked
        content = _md("obj.fabricated_method()")
        findings = check_api_identifiers(content, "test-slug", api_surface=surface)
        method_findings = [f for f in findings if f.check == "api_identifier_unknown_method"]
        assert len(method_findings) >= 1
        assert method_findings[0].severity == "medium"

    def test_lowercase_class_name_receiver_is_high(self):
        """'workbook.fake()' where 'workbook' matches known class Workbook → HIGH."""
        brief = _make_brief("Workbook", methods=["save"])
        surface = _make_surface(
            public_classes=["Workbook"],
            class_briefs=[brief],
        )
        content = _md("workbook.fake_method()")
        findings = check_api_identifiers(content, "test-slug", api_surface=surface)
        method_findings = [f for f in findings if f.check == "api_identifier_unknown_method"]
        assert len(method_findings) >= 1
        assert method_findings[0].severity == "high"


# ---------------------------------------------------------------------------
# TC-5194: unittest / os.path stdlib allowlist
# ---------------------------------------------------------------------------

class TestUnittestStdlibAllowlist:
    """TC-5194: unittest.TestCase subclass code must not produce false positives."""

    def test_unittest_stdlib_no_false_positive(self):
        """Code with unittest.TestCase + assertEqual must yield zero findings
        for unittest identifiers (TestCase class, assert methods, setUp)."""
        brief = _make_brief("Workbook", methods=["save"])
        surface = _make_surface(
            public_classes=["Workbook"],
            class_briefs=[brief],
        )
        code = (
            "import unittest\n"
            "\n"
            "class TestWorkbook(unittest.TestCase):\n"
            "    def setUp(self):\n"
            "        self.wb = Workbook()\n"
            "\n"
            "    def test_save(self):\n"
            "        self.wb.save('out.xlsx')\n"
            "        self.assertEqual(1, 1)\n"
            "        self.assertTrue(True)\n"
        )
        content = _md(code)
        findings = check_api_identifiers(content, "test-slug", api_surface=surface)
        # Filter to only unittest-related false positives
        unittest_names = {
            "TestCase", "TestSuite", "TestLoader", "TextTestRunner",
            "TestResult", "assertEqual", "assertTrue", "setUp",
        }
        unittest_findings = [
            f for f in findings
            if any(name in f.message for name in unittest_names)
        ]
        assert unittest_findings == [], (
            f"Unexpected unittest false positives: {unittest_findings}"
        )

    def test_os_path_methods_no_false_positive(self):
        """os.path methods (dirname, abspath, exists) must not be flagged."""
        brief = _make_brief("Workbook", methods=["save"])
        surface = _make_surface(
            public_classes=["Workbook"],
            class_briefs=[brief],
            confidence="medium",
        )
        code = (
            "import os\n"
            "base = os.path.dirname('/some/file.txt')\n"
            "full = os.path.abspath(base)\n"
            "if os.path.exists(full):\n"
            "    pass\n"
        )
        content = _md(code)
        findings = check_api_identifiers(content, "test-slug", api_surface=surface)
        os_path_names = {"dirname", "abspath", "exists"}
        os_findings = [
            f for f in findings
            if any(name in f.message for name in os_path_names)
        ]
        assert os_findings == [], (
            f"Unexpected os.path false positives: {os_findings}"
        )


# ---------------------------------------------------------------------------
# TC-5200 / EVL-234: False-positive reduction — string literals, enum members,
#                     Test class filter
# ---------------------------------------------------------------------------

def _make_brief_with_enums(
    name: str,
    methods: list[str] | None = None,
    enum_members: list[str] | None = None,
) -> SimpleNamespace:
    """Build a class brief that includes enum members (EVL-3 helper)."""
    members = [SimpleNamespace(name=m) for m in (enum_members or [])]
    enum_obj = SimpleNamespace(members=members)
    return SimpleNamespace(
        name=name,
        methods=methods or [],
        properties=[],
        typed_methods=[],
        typed_properties=[],
        enums=[enum_obj] if members else [],
    )


class TestFalsePositiveFixes:
    """TC-5200 / EVL-234: String-aware scan, enum member recognition, Test class filter."""

    # ---- EVL-2: string literal stripping ----

    def test_formula_name_in_string_not_flagged(self):
        """SUM inside a string literal must not be flagged as an unknown class."""
        brief = _make_brief("Workbook", methods=["save"])
        surface = _make_surface(
            public_classes=["Workbook"],
            class_briefs=[brief],
        )
        # SUM appears inside a string — should NOT trigger api_identifier_unknown_class
        code = 'ws["A1"].value = "=SUM(A1:B3)"\nwb = Workbook()\nwb.save("out.xlsx")'
        content = _md(code)
        findings = check_api_identifiers(content, "test-slug", api_surface=surface)
        class_findings = [f for f in findings if f.check == "api_identifier_unknown_class"]
        formula_findings = [f for f in class_findings if "SUM" in f.message]
        assert formula_findings == [], (
            f"Formula name SUM was incorrectly flagged: {formula_findings}"
        )

    def test_cell_reference_in_string_not_flagged(self):
        """Cell reference A1 inside a string literal must not be flagged."""
        brief = _make_brief("Workbook", methods=["save"])
        surface = _make_surface(
            public_classes=["Workbook"],
            class_briefs=[brief],
        )
        # A1 appears inside a string subscript — after stripping should produce no match
        code = 'wb = Workbook()\nws["A1"] = 5\nwb.save("out.xlsx")'
        content = _md(code)
        findings = check_api_identifiers(content, "test-slug", api_surface=surface)
        class_findings = [f for f in findings if f.check == "api_identifier_unknown_class"]
        cell_findings = [f for f in class_findings if "A1" in f.message]
        assert cell_findings == [], (
            f"Cell reference A1 was incorrectly flagged: {cell_findings}"
        )

    def test_average_formula_in_string_not_flagged(self):
        """AVERAGE inside a formula string must not produce a class finding."""
        brief = _make_brief("Workbook", methods=["save"])
        surface = _make_surface(
            public_classes=["Workbook"],
            class_briefs=[brief],
        )
        code = 'cell.formula = "=AVERAGE(B1:B10)"\nwb = Workbook()\nwb.save("out.xlsx")'
        content = _md(code)
        findings = check_api_identifiers(content, "test-slug", api_surface=surface)
        class_findings = [f for f in findings if f.check == "api_identifier_unknown_class"]
        avg_findings = [f for f in class_findings if "AVERAGE" in f.message]
        assert avg_findings == [], (
            f"Formula name AVERAGE was incorrectly flagged: {avg_findings}"
        )

    # ---- EVL-3: enum member recognition ----

    def test_enum_member_not_flagged(self):
        """Enum member (Scatter) present in api_surface must not be flagged."""
        chart_brief = _make_brief_with_enums(
            "ChartType",
            methods=[],
            enum_members=["Scatter", "Histogram", "Bar", "Line"],
        )
        wb_brief = _make_brief("Workbook", methods=["save"])
        surface = _make_surface(
            public_classes=["Workbook", "ChartType"],
            class_briefs=[wb_brief, chart_brief],
        )
        # Scatter is used as if constructing an object — but it's an enum member
        code = "chart_type = Scatter()\nwb = Workbook()\nwb.save('out.xlsx')"
        content = _md(code)
        findings = check_api_identifiers(content, "test-slug", api_surface=surface)
        class_findings = [f for f in findings if f.check == "api_identifier_unknown_class"]
        scatter_findings = [f for f in class_findings if "Scatter" in f.message]
        assert scatter_findings == [], (
            f"Enum member Scatter was incorrectly flagged: {scatter_findings}"
        )

    # ---- EVL-4: Test class filter ----

    def test_generic_test_class_not_flagged(self):
        """TestWorkbookCreation() must not produce an api_identifier_unknown_class finding."""
        brief = _make_brief("Workbook", methods=["save"])
        surface = _make_surface(
            public_classes=["Workbook"],
            class_briefs=[brief],
        )
        code = (
            "class TestWorkbookCreation(unittest.TestCase):\n"
            "    def test_create(self):\n"
            "        wb = TestWorkbookCreation()\n"
            "        wb2 = Workbook()\n"
            "        wb2.save('out.xlsx')\n"
        )
        content = _md(code)
        findings = check_api_identifiers(content, "test-slug", api_surface=surface)
        class_findings = [f for f in findings if f.check == "api_identifier_unknown_class"]
        test_findings = [f for f in class_findings if "TestWorkbookCreation" in f.message]
        assert test_findings == [], (
            f"TestWorkbookCreation was incorrectly flagged: {test_findings}"
        )

    # ---- Regression: genuine unknown class still flagged ----

    def test_genuine_unknown_class_still_flagged(self):
        """FakeMadeUpClass() (no Test prefix, not in surface) must still be flagged HIGH."""
        brief = _make_brief("Workbook", methods=["save"])
        surface = _make_surface(
            public_classes=["Workbook"],
            class_briefs=[brief],
        )
        code = "mgr = FakeMadeUpClass()\nwb = Workbook()\nwb.save('out.xlsx')"
        content = _md(code)
        findings = check_api_identifiers(content, "test-slug", api_surface=surface)
        class_findings = [f for f in findings if f.check == "api_identifier_unknown_class"]
        fake_findings = [f for f in class_findings if "FakeMadeUpClass" in f.message]
        assert len(fake_findings) >= 1, "Expected FakeMadeUpClass to be flagged HIGH"
        assert fake_findings[0].severity == "high"
