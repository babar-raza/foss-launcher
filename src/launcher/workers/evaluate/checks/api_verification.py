"""API identifier verification gate (TC-HYBRID-05).

Scans code blocks in generated content for API calls and cross-references
them against the extracted ApiSurface. Flags unknown identifiers.
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

# Patterns to extract API calls from Python code
# Class instantiation: ClassName(...)
_CLASS_INSTANTIATION_RE = re.compile(r'\b([A-Z][a-zA-Z0-9]+)\s*\(')
# Method call: obj.method_name(...) or cls.method_name(...)
_METHOD_CALL_RE = re.compile(r'\b[a-z_][a-zA-Z0-9_]*\.([a-z_][a-zA-Z0-9_]*)\s*\(')
# TC-4005: Property access with call parens: obj.prop_name(...)
# Same pattern as METHOD_CALL_RE but used to detect property-as-method calls
_PROPERTY_CALL_RE = _METHOD_CALL_RE  # same regex, different check logic

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
})

# Methods to always allow (common Python protocols and builtins)
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
})


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

    # Extract Python code blocks
    code_blocks = _CODE_BLOCK_RE.findall(content)
    if not code_blocks:
        return []

    findings: list[Finding] = []

    for block in code_blocks:
        # Check class instantiations — only flag when confidence is "high"
        if api_surface.confidence == "high":
            for m in _CLASS_INSTANTIATION_RE.finditer(block):
                cls_name = m.group(1)
                if cls_name in _ALWAYS_ALLOWED_CLASSES:
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
            for m in _METHOD_CALL_RE.finditer(block):
                method_name = m.group(1)
                if method_name in _ALWAYS_ALLOWED_METHODS:
                    continue
                if method_name.startswith("_"):
                    continue
                # TC-4005: Detect property-as-method anti-pattern
                # obj.prop() when prop is a known property but NOT a method
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
