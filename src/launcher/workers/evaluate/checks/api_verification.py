"""API identifier verification gate (TC-HYBRID-05).

Scans code blocks in generated content for API calls and cross-references
them against the extracted ApiSurface. Flags unknown identifiers.

TC-REG-301: Context-aware method checking — when a variable is assigned from
a known library class, method calls on that variable bypass the generic
_ALWAYS_ALLOWED_METHODS exemption and are checked against the class's actual
methods from class_briefs.
"""
from __future__ import annotations

import re
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from launcher.models.product import ApiSurface

from launcher.models.evaluation import Finding

logger = logging.getLogger(__name__)


# Pattern to extract code blocks from markdown
_CODE_BLOCK_RE = re.compile(r'```(?:python|py)\n(.*?)```', re.DOTALL)

# EVL-2: Pattern to match string literals (triple-quoted first, then single-line)
_STRING_RE = re.compile(
    r'""".*?"""|' + r"'''.*?'''|" + r'"(?:[^"\\]|\\.)*"|' + r"'(?:[^'\\]|\\.)*'",
    re.DOTALL,
)


def _strip_string_literals(code: str) -> str:
    """Replace string literal content with empty strings to prevent false matches.

    Handles triple-quoted strings, single-quoted strings, and escape sequences.
    Used before class instantiation scanning to ensure formula names and cell
    references embedded in string values are not matched by _CLASS_INSTANTIATION_RE.
    """
    return _STRING_RE.sub('""', code)


# EVL-2: Common spreadsheet formula names — never flag these as unknown classes
_SPREADSHEET_FORMULA_NAMES: frozenset[str] = frozenset({
    "SUM", "AVERAGE", "COUNT", "COUNTA", "MAX", "MIN", "IF", "VLOOKUP",
    "HLOOKUP", "INDEX", "MATCH", "SUMIF", "COUNTIF", "AVERAGEIF", "ROUND",
    "ABS", "CONCATENATE", "LEFT", "RIGHT", "MID", "LEN", "TRIM", "UPPER",
    "LOWER", "TODAY", "NOW", "DATE", "YEAR", "MONTH", "DAY", "TEXT",
    "IFERROR", "AND", "OR", "NOT", "TRUE", "FALSE",
})

# EVL-2: Cell reference pattern — A1, BC123, AAA1234567 (but NOT WorkflowManager)
_CELL_REF_RE = re.compile(r'^[A-Z]{1,3}\d{1,7}$')

# Patterns to extract API calls from Python code
# Class instantiation: ClassName(...)
_CLASS_INSTANTIATION_RE = re.compile(r'\b([A-Z][a-zA-Z0-9]+)\s*\(')
# TC-REG-301: Receiver + method call (captures both parts)
_RECEIVER_METHOD_RE = re.compile(r'\b([a-z_][a-zA-Z0-9_]*)\.([a-z_][a-zA-Z0-9_]*)\s*\(')
# TC-REG-301: Variable assignment from class instantiation: var = ClassName(...)
# REG-H-06: Also matches type-annotated (var: Type = Cls(...)) and module-qualified (var = mod.Cls(...))
_ASSIGNMENT_RE = re.compile(
    r'\b([a-z_][a-zA-Z0-9_]*)\s*(?::\s*\w+\s*)?=\s*(?:\w+\.)*([A-Z][a-zA-Z0-9]+)\s*\('
)
# TC-REG-301: Bare property access without parens: obj.prop_name (not followed by `(`)
_PROPERTY_ACCESS_RE = re.compile(r'\b([a-z_][a-zA-Z0-9_]*)\.([a-z_][a-zA-Z0-9_]*)\b(?!\s*\()')

# Classes to always allow (standard Python builtins and common idioms)
_ALWAYS_ALLOWED_CLASSES = frozenset({
    "str", "int", "float", "bool", "list", "dict", "set", "tuple",
    "bytes", "bytearray", "object", "type", "Exception", "ValueError",
    "TypeError", "RuntimeError", "FileNotFoundError", "IOError",
    "NotImplementedError", "AttributeError", "KeyError", "IndexError",
    "StopIteration", "GeneratorExit", "SystemExit",
    "Path", "PurePath", "PurePosixPath", "PureWindowsPath",
    "Enum", "IntEnum", "StrEnum", "Flag", "IntFlag",
    "ABC", "abstractmethod",
    "Optional", "Union", "List", "Dict", "Set", "Tuple", "Any",
    "ClassVar", "Final", "Literal",
    "print", "len", "range", "enumerate", "zip", "map", "filter",
    "sorted", "reversed", "sum", "min", "max", "abs", "round",
    "open", "input", "format", "repr", "hash", "id",
    "True", "False", "None",
    "super", "property", "classmethod", "staticmethod",
    "isinstance", "issubclass", "hasattr", "getattr", "setattr",
    # unittest (TC-5194)
    "TestCase", "TestSuite", "TestLoader", "TextTestRunner", "TestResult",
})

# Methods to always allow (common Python protocols and builtins).
# TC-REG-301: These are ONLY exempt when the receiver is NOT a tracked library
# class instance. When the receiver IS tracked, we check against the class's
# actual methods from class_briefs instead.
_ALWAYS_ALLOWED_METHODS = frozenset({
    "__init__", "__str__", "__repr__", "__len__", "__iter__",
    "__enter__", "__exit__", "__getitem__", "__setitem__",
    "append", "extend", "insert", "remove", "pop", "clear",
    "update", "get", "keys", "values", "items",
    "strip", "split", "join", "replace", "lower", "upper",
    "encode", "decode", "read", "write", "close",
    "format", "startswith", "endswith", "find", "index",
    "save", "load", "open", "run", "execute",
    "to_string", "from_string", "to_dict", "from_dict",
    "model_validate", "model_dump",
    # unittest assertions (TC-5194: common in example code)
    "assertTrue", "assertFalse", "assertEqual", "assertNotEqual",
    "assertIsNone", "assertIsNotNone", "assertIn", "assertRaises",
    "setUp", "tearDown",
    # os.path (TC-5194: common in file-handling examples)
    "dirname", "abspath", "basename", "exists", "isfile", "isdir",
})

# Attributes to always allow on any object (Python built-in protocols)
_ALWAYS_ALLOWED_ATTRS = frozenset({
    "__class__", "__dict__", "__doc__", "__module__", "__name__",
})


def _build_class_method_map(
    api_surface: "ApiSurface",
) -> dict[str, frozenset[str]]:
    """Build per-class method+property lookup from class_briefs.

    Returns ``{ClassName: frozenset(method_names | property_names)}`` so that
    context-aware checking can verify method calls against the specific class.
    """
    result: dict[str, set[str]] = {}
    for brief in api_surface.class_briefs:
        methods: set[str] = set(brief.methods)
        for tm in brief.typed_methods:
            methods.add(tm.name)
        for p in brief.properties:
            methods.add(p)
        for tp in brief.typed_properties:
            methods.add(tp.name)
        result[brief.name] = methods
    return {k: frozenset(v) for k, v in result.items()}


def _track_assignments(block: str, known_classes: set[str]) -> dict[str, str]:
    """Track variable→class assignments in a code block.

    Scans for patterns like ``var = ClassName(...)`` where ClassName is in
    ``known_classes``. Returns ``{var_name: ClassName}``.

    Also tracks lowercase aliases: if ``cells = workbook.cells`` and Cells is
    a known class, does NOT track (property access, not instantiation).
    Only tracks direct instantiation ``var = KnownClass(...)``.
    """
    assignments: dict[str, str] = {}
    for m in _ASSIGNMENT_RE.finditer(block):
        var_name, cls_name = m.group(1), m.group(2)
        if cls_name in known_classes:
            assignments[var_name] = cls_name
    return assignments


def check_api_identifiers(
    content: str,
    slug: str,
    *,
    api_surface: "ApiSurface | None" = None,
) -> "list[Finding]":
    """Verify API identifiers in generated code blocks against extracted ApiSurface.

    Scans Python code blocks for class instantiations and method calls.
    Cross-references against ``api_surface.class_briefs`` and
    ``api_surface.api_identifiers``.

    TC-REG-301: Context-aware checking — when a method is called on a variable
    that was assigned from a known library class (e.g. ``wb = Workbook()``),
    the ``_ALWAYS_ALLOWED_METHODS`` exemption is bypassed and the method is
    checked against that class's actual methods from ``class_briefs``.

    Args:
        content: Generated markdown content.
        slug: Page slug for Finding location.
        api_surface: Extracted ApiSurface from Understand worker. If None or
            low-confidence, the gate is skipped (returns []).

    Returns:
        List of Findings. HIGH = unknown class name (high confidence only).
        MEDIUM = unknown method (high or medium confidence).
        Empty list when gate skips (no api_surface, low confidence, no code blocks,
        or no class_briefs/api_identifiers to cross-reference against).
    """
    # Gate: skip when no api_surface or low confidence
    if api_surface is None:
        return []
    if api_surface.confidence == "low":
        return []
    if not api_surface.class_briefs and not api_surface.api_identifiers:
        return []

    # Build lookup sets from ApiSurface
    known_classes: set[str] = set(api_surface.public_classes)
    known_methods: set[str] = set()
    # TC-4005: Track properties separately for property-call detection
    known_properties_only: set[str] = set()

    for brief in api_surface.class_briefs:
        known_methods.update(brief.methods)
        # Also add typed method names
        for tm in brief.typed_methods:
            known_methods.add(tm.name)
        # TC-4005: Properties tracked separately — these are NOT callable
        for tp in brief.typed_properties:
            known_properties_only.add(tp.name)
        for p in brief.properties:
            known_properties_only.add(p)
        # Add the class name itself
        known_classes.add(brief.name)

    # Properties that are ALSO method names are valid calls (e.g. overloaded)
    properties_not_methods = known_properties_only - known_methods

    # Also use api_identifiers as a broader allowlist
    all_known = set(api_surface.api_identifiers) | known_classes | known_methods | known_properties_only

    # TC-REG-301: Per-class method+property lookup for context-aware checking
    class_method_map = _build_class_method_map(api_surface)
    # Build case-insensitive class name lookup for receiver matching
    class_name_lower: dict[str, str] = {c.lower(): c for c in known_classes}

    # Extract Python code blocks
    code_blocks = _CODE_BLOCK_RE.findall(content)
    if not code_blocks:
        return []

    findings: list[Finding] = []

    for block in code_blocks:
        # TC-REG-301: Track variable→class assignments in this block
        var_class_map = _track_assignments(block, known_classes)

        # Check class instantiations — only flag when confidence is "high"
        if api_surface.confidence == "high":
            # EVL-3: Build enum member set from api_surface class briefs so that
            # enum values (e.g. Scatter, Histogram, Protection) are never flagged
            known_enum_members: set[str] = set()
            for _brief in getattr(api_surface, "class_briefs", []) or []:
                for _enum in getattr(_brief, "enums", []) or []:
                    for _member in getattr(_enum, "members", []) or []:
                        _name = getattr(_member, "name", None)
                        if _name:
                            known_enum_members.add(_name)

            # EVL-2: Strip string literals so formula names / cell refs inside
            # strings (e.g. "=SUM(A1:B3)") do not produce false positives
            stripped_block = _strip_string_literals(block)
            for m in _CLASS_INSTANTIATION_RE.finditer(stripped_block):
                cls_name = m.group(1)
                if cls_name in _ALWAYS_ALLOWED_CLASSES:
                    continue
                # EVL-2: Skip spreadsheet formula names
                if cls_name in _SPREADSHEET_FORMULA_NAMES:
                    continue
                # EVL-2: Skip cell references (A1, BC3, etc.)
                if _CELL_REF_RE.match(cls_name):
                    continue
                # EVL-3: Skip enum members present in the extracted API surface
                if cls_name in known_enum_members:
                    continue
                # EVL-4: Skip generic test-framework/user-defined test classes
                # (TestCase is already in _ALWAYS_ALLOWED_CLASSES; this catches
                # TestWorkbookCreation, TestDataValidation, etc.)
                if cls_name.startswith("Test") and len(cls_name) > 4 and cls_name[4].isupper():
                    continue
                if cls_name in known_classes:
                    continue
                if cls_name in all_known:
                    continue
                findings.append(Finding(
                    check="api_identifier_unknown_class",
                    message=(
                        f"Code uses class `{cls_name}` which is not in extracted API surface. "
                        f"Known classes: {sorted(known_classes)[:5]}"
                    ),
                    severity="high",
                    location=slug,
                ))

        # Check method calls — flag on high or medium confidence
        if api_surface.confidence in ("high", "medium"):
            for m in _RECEIVER_METHOD_RE.finditer(block):
                receiver = m.group(1)
                method_name = m.group(2)
                if method_name.startswith("_"):
                    continue

                # TC-4005: Detect property-as-method anti-pattern
                if method_name in properties_not_methods:
                    findings.append(Finding(
                        check="api_property_called_as_method",
                        message=(
                            f"Code calls `{method_name}()` with parentheses but "
                            f"`{method_name}` is a property, not a method. "
                            f"Use `obj.{method_name}` without parentheses."
                        ),
                        severity="high",
                        location=slug,
                    ))
                    continue

                # TC-REG-301: Context-aware method checking
                # Determine if receiver maps to a known library class
                tracked_class: str | None = var_class_map.get(receiver)
                if tracked_class is None:
                    # Check if receiver name itself is a known class (lowercase)
                    matched_cls = class_name_lower.get(receiver)
                    if matched_cls:
                        tracked_class = matched_cls

                if tracked_class is not None:
                    # Receiver IS a library class instance — bypass generic allowlist,
                    # check against the specific class's methods+properties
                    class_members = class_method_map.get(tracked_class, frozenset())
                    if method_name in class_members:
                        continue  # Valid method for this class
                    if method_name in known_methods:
                        continue  # Valid method on another known class
                    if method_name in all_known:
                        continue
                    # NOT in class methods — flag even if in _ALWAYS_ALLOWED_METHODS
                    # TC-EVAL-301: HIGH for tracked receivers (known class, unknown method
                    # = confirmed hallucination). Untracked receivers stay MEDIUM below.
                    findings.append(Finding(
                        check="api_identifier_unknown_method",
                        message=(
                            f"Code calls `{receiver}.{method_name}()` but "
                            f"`{method_name}` is not a known method of `{tracked_class}`. "
                            f"Known methods: {sorted(list(class_members)[:5])}"
                        ),
                        severity="high",
                        location=slug,
                    ))
                    continue

                # Receiver is NOT tracked — apply generic allowlist
                if method_name in _ALWAYS_ALLOWED_METHODS:
                    continue
                if method_name in known_methods:
                    continue
                if method_name in all_known:
                    continue
                findings.append(Finding(
                    check="api_identifier_unknown_method",
                    message=(
                        f"Code calls method `{method_name}()` which is not in extracted API surface."
                    ),
                    severity="medium",
                    location=slug,
                ))

        # TC-REG-301: Check bare property access (no parens) — high confidence only
        # REG-H-01: Build line index for false-positive filtering
        if api_surface.confidence == "high":
            block_lines = block.splitlines()
            for m in _PROPERTY_ACCESS_RE.finditer(block):
                # REG-H-01: Find the source line for this match
                line_start = block.rfind('\n', 0, m.start()) + 1
                line_end = block.find('\n', m.end())
                if line_end == -1:
                    line_end = len(block)
                source_line = block[line_start:line_end].strip()
                # Skip import lines
                if source_line.startswith(("import ", "from ")):
                    continue
                # Skip comment lines
                if source_line.startswith("#"):
                    continue
                # Skip if match is inside a string literal (between quotes)
                prefix = block[line_start:m.start()]
                if prefix.count('"') % 2 == 1 or prefix.count("'") % 2 == 1:
                    continue
                receiver = m.group(1)
                attr_name = m.group(2)
                if attr_name.startswith("_"):
                    continue
                if attr_name in _ALWAYS_ALLOWED_ATTRS:
                    continue
                # Only check when receiver is a tracked library class instance
                tracked_class = var_class_map.get(receiver)
                if tracked_class is None:
                    tracked_class_name = class_name_lower.get(receiver)
                    if tracked_class_name:
                        tracked_class = tracked_class_name
                if tracked_class is None:
                    continue  # Untracked receiver — skip property checking
                class_members = class_method_map.get(tracked_class, frozenset())
                if attr_name in class_members:
                    continue  # Known property/method
                if attr_name in all_known:
                    continue
                findings.append(Finding(
                    check="api_identifier_unknown_property",
                    message=(
                        f"Code accesses `{receiver}.{attr_name}` but "
                        f"`{attr_name}` is not a known member of `{tracked_class}`."
                    ),
                    severity="medium",
                    location=slug,
                ))

    # Deduplicate (same check+message may appear in multiple code blocks)
    seen: set[str] = set()
    unique: list[Finding] = []
    for f in findings:
        key = f"{f.check}:{f.message}"
        if key not in seen:
            seen.add(key)
            unique.append(f)

    if unique:
        logger.info(
            "api_verification: slug=%s findings=%d (high=%d, medium=%d)",
            slug, len(unique),
            sum(1 for f in unique if f.severity == "high"),
            sum(1 for f in unique if f.severity == "medium"),
        )

    return unique
