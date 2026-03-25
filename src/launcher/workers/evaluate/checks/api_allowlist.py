"""Check: api_allowlist -- verify backticked identifiers against API surface (TC-QG-01)."""
from __future__ import annotations

import re

from launcher.models.evaluation import Finding
from launcher.shared.jaccard import strip_code_blocks

_PYTHON_BUILTINS = frozenset({
    "str", "int", "float", "bool", "list", "dict", "tuple", "set", "None",
    "True", "False", "print", "open", "len", "range", "type", "isinstance",
    "Exception", "ValueError", "TypeError", "KeyError", "IndexError",
    "RuntimeError", "FileNotFoundError", "ImportError", "AttributeError",
    "StopIteration", "NotImplementedError",
})

_PYTHON_STDLIB = frozenset({
    "os", "sys", "json", "csv", "pathlib", "io", "re", "datetime",
    "collections", "itertools", "functools", "typing", "abc", "enum",
    "dataclasses", "contextlib", "logging", "unittest", "math",
    "Path", "BytesIO", "StringIO",
})

_COMMON_TERMS = frozenset({
    "self", "cls", "args", "kwargs", "value", "key", "name", "path",
    "data", "result", "output", "input", "index", "count", "size",
    "format", "string", "number", "text", "file", "url", "content",
    "object", "class", "method", "property", "function", "module",
    "import", "from", "return", "yield", "async", "await",
    "pip", "python", "python3", "pip3",
})

# REG-H-02: Common framework/ecosystem class names that appear in documentation
# prose but are not library-specific — should not trigger findings.
_FRAMEWORK_CLASSES = frozenset({
    "DataFrame", "Series", "Iterator", "Generator", "Callable",
    "Optional", "Union", "Type", "Any", "Sequence", "Mapping",
    "Protocol", "TypeVar", "Generic", "Awaitable", "Coroutine",
    "AsyncIterator", "AsyncGenerator", "NamedTuple", "TypedDict",
    "Iterable", "Collection", "MutableMapping", "MutableSequence",
})

# Identifier extraction regex: backticked names, possibly dotted
_BACKTICK_RE = re.compile(r"`([A-Za-z_]\w*(?:(?:::|\.)[A-Za-z_]\w*)*)`")


def _build_allowlist(api_surface: object) -> tuple[frozenset[str], frozenset[str]]:
    """Build sets of allowed class names and member names from ApiSurface.

    Returns (class_names, member_names).
    """
    class_names: set[str] = set()
    member_names: set[str] = set()

    if api_surface is None:
        return frozenset(), frozenset()

    # public_classes
    for cls_name in getattr(api_surface, "public_classes", []) or []:
        class_names.add(cls_name)

    # import_allowlist
    for imp in getattr(api_surface, "import_allowlist", []) or []:
        # Could be dotted path like "aspose.cells"; add each part
        for part in imp.split("."):
            member_names.add(part)

    # api_identifiers
    for ident in getattr(api_surface, "api_identifiers", []) or []:
        member_names.add(ident)

    # api_identifiers_native
    for ident in getattr(api_surface, "api_identifiers_native", []) or []:
        member_names.add(ident)

    # class_briefs: methods and properties
    for brief in getattr(api_surface, "class_briefs", []) or []:
        class_names.add(getattr(brief, "name", ""))
        for m in getattr(brief, "methods", []) or []:
            member_names.add(m)
        for p in getattr(brief, "properties", []) or []:
            member_names.add(p)
        for tm in getattr(brief, "typed_methods", []) or []:
            member_names.add(getattr(tm, "name", ""))
        for tp in getattr(brief, "typed_properties", []) or []:
            member_names.add(getattr(tp, "name", ""))

    # enums
    for enum_rec in getattr(api_surface, "enums", []) or []:
        class_names.add(getattr(enum_rec, "name", ""))
        for member in getattr(enum_rec, "members", []) or []:
            member_names.add(getattr(member, "name", ""))

    class_names.discard("")
    member_names.discard("")
    return frozenset(class_names), frozenset(member_names)


def check_api_allowlist(
    content: str,
    api_surface: object,  # ApiSurface or None
    slug: str,
) -> list[Finding]:
    """Verify backticked identifiers in prose against API surface allowlist.

    Extracts all backticked terms from prose (outside code blocks).
    Checks each against ApiSurface.public_classes + class_briefs methods/properties.

    Returns HIGH for unknown class names, MEDIUM for unknown method/property names.
    Exempts Python builtins, stdlib, and common programming terms.

    TC-QG-01.
    """
    if api_surface is None:
        return []

    findings: list[Finding] = []
    # Strip frontmatter
    body = re.sub(r"^---\n.*?\n---\n?", "", content, flags=re.DOTALL)
    # Strip code blocks — we only check prose
    prose = strip_code_blocks(body)

    class_names, member_names = _build_allowlist(api_surface)
    all_exempt = _PYTHON_BUILTINS | _PYTHON_STDLIB | _COMMON_TERMS | _FRAMEWORK_CLASSES
    # Build lowercase versions for case-insensitive variable-name matching
    # e.g. `workbook` should match class `Workbook` (common Python convention)
    class_names_lower = frozenset(c.lower() for c in class_names)

    identifiers = _BACKTICK_RE.findall(prose)
    unknown_classes: set[str] = set()
    unknown_members: set[str] = set()

    for ident in identifiers:
        parts = re.split(r"(?:::|\.)", ident)
        for part in parts:
            if part in all_exempt:
                continue
            if part in class_names:
                continue
            if part in member_names:
                continue
            # Case-insensitive class name match (variable convention)
            if part.lower() in class_names_lower:
                continue
            # Heuristic: starts with uppercase → likely a class name
            if part and part[0].isupper():
                unknown_classes.add(part)
            else:
                unknown_members.add(part)

    for cls in sorted(unknown_classes):
        findings.append(
            Finding(
                check="api_allowlist",
                message=f"Unknown class identifier in prose: `{cls}` not in API surface",
                severity="high",  # REG-H-02: downgraded from critical to high
                location=slug,
            )
        )

    for mem in sorted(unknown_members):
        findings.append(
            Finding(
                check="api_allowlist",
                message=f"Unknown member identifier in prose: `{mem}` not in API surface",
                severity="medium",
                location=slug,
            )
        )

    return findings
