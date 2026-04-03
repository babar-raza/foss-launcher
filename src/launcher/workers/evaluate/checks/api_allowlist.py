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

# TC-NET-006: .NET stdlib types that appear legitimately in .NET documentation prose.
_DOTNET_STDLIB = frozenset({
    "Console", "String", "Int32", "Int64", "Boolean", "Double",
    "Object", "List", "Dictionary", "HashSet", "Queue", "Stack",
    "StringBuilder", "Stream", "FileStream", "MemoryStream",
    "StreamReader", "StreamWriter", "File", "Directory",
    "Thread", "Task", "CancellationToken",
    "IDisposable", "IEnumerable", "IList", "IDictionary",
    "Exception", "ArgumentException", "InvalidOperationException",
    "NotSupportedException", "IOException", "FileNotFoundException",
    "NullReferenceException", "OutOfMemoryException",
    "Nullable", "Span", "Memory", "ReadOnlySpan",
    "Action", "Func", "Predicate", "Comparison",
    "using", "var", "new", "void", "null", "true", "false",
    "byte", "char", "short", "long", "float", "double", "decimal",
    "uint", "ulong", "ushort", "sbyte", "nint", "nuint",
})

# TC-5315: Java stdlib types that appear legitimately in Java documentation prose.
# Covers java.lang, java.util, java.io essentials plus generics conventions.
_JAVA_STDLIB = frozenset({
    # java.lang
    "String", "Integer", "Long", "Double", "Float", "Boolean", "Byte", "Short",
    "Character", "Number", "Object", "Class", "System", "Math", "StringBuilder",
    "StringBuffer", "Enum", "Comparable", "Runnable", "Thread", "Void",
    "Exception", "RuntimeException", "Error", "Throwable",
    "IllegalArgumentException", "IllegalStateException", "NullPointerException",
    "IndexOutOfBoundsException", "UnsupportedOperationException",
    "StackOverflowError", "OutOfMemoryError", "ClassCastException",
    "ArithmeticException", "NumberFormatException", "CloneNotSupportedException",
    "InterruptedException",
    # java.util
    "List", "ArrayList", "LinkedList", "Map", "HashMap", "LinkedHashMap",
    "TreeMap", "Set", "HashSet", "LinkedHashSet", "TreeSet", "Collection",
    "Collections", "Arrays", "Iterator", "Optional", "Stream", "Collectors",
    "Objects", "UUID", "Date", "Calendar", "Properties", "Scanner", "Random",
    "Queue", "Deque", "ArrayDeque", "PriorityQueue", "Stack",
    # java.io
    "IOException", "File", "InputStream", "OutputStream", "Reader", "Writer",
    "BufferedReader", "BufferedWriter", "FileInputStream", "FileOutputStream",
    "InputStreamReader", "OutputStreamWriter", "Closeable", "AutoCloseable",
    "Serializable", "PrintWriter",
    # java.nio
    "Path", "Paths", "Files", "ByteBuffer",
    # Generic type parameters (single-letter conventions)
    "T", "E", "K", "V", "R", "N",
    # Java keywords / primitives appearing as identifiers
    "void", "int", "long", "double", "float", "boolean", "byte", "char", "short",
    "null", "true", "false", "new", "static", "final", "public", "private",
    "protected", "interface", "abstract", "extends", "implements", "throws",
    "import", "return", "class",
})

# TC-5329: C++ standard library identifiers that appear legitimately in C++ documentation.
# Covers std namespace, streams, types, keywords — but intentionally EXCLUDES .NET/CLR types
# (System, InvalidOperationException, Drawing, etc.) which are genuine errors in C++ content.
_CPP_STDLIB = frozenset({
    # std namespace and sub-namespaces
    "std", "chrono", "filesystem", "regex", "literals",
    # string types
    "string", "wstring", "u8string", "u16string", "u32string",
    # containers
    "vector", "map", "unordered_map", "set", "unordered_set", "list",
    "deque", "array", "tuple", "pair", "optional", "variant", "any",
    # smart pointers
    "shared_ptr", "unique_ptr", "weak_ptr",
    # streams
    "istream", "ostream", "fstream", "ifstream", "ofstream",
    "stringstream", "istringstream", "ostringstream",
    "cin", "cout", "cerr", "clog", "endl",
    # time / chrono
    "time_point", "duration", "seconds", "milliseconds", "microseconds",
    "nanoseconds", "minutes", "hours", "system_clock", "steady_clock",
    # C++ primitives and keywords appearing as identifiers
    "int", "long", "short", "char", "bool", "float", "double", "void",
    "uint8_t", "uint16_t", "uint32_t", "uint64_t",
    "int8_t", "int16_t", "int32_t", "int64_t", "size_t", "ptrdiff_t",
    "nullptr", "true", "false", "null", "new", "delete",
    "const", "static", "auto", "inline", "virtual", "override", "final",
    "return", "class", "struct", "enum", "template", "typename",
    "public", "private", "protected", "namespace", "using",
    # exceptions from <stdexcept> and <exception> — commonly used in C++ error-handling prose
    "exception", "runtime_error", "logic_error", "domain_error", "length_error",
    "range_error", "overflow_error", "underflow_error", "invalid_argument", "out_of_range",
    # CMake package name used in find_package() install instructions
    "aspose_slides_foss", "aspose_cells_foss", "aspose_3d_foss",
    # TC-5336: CMake keywords that appear in cmake code blocks and install prose.
    # find_package(aspose_slides_foss REQUIRED) — REQUIRED is all-caps CMake keyword.
    "REQUIRED", "PRIVATE", "PUBLIC", "INTERFACE", "STATIC", "SHARED",
    "TARGET_LINK_LIBRARIES", "find_package", "target_include_directories",
    "target_link_libraries", "add_executable", "add_library",
    "cmake_minimum_required", "project", "CMakeLists", "CMake",
    # third-party libraries commonly seen in Aspose C++ docs
    "pugi", "xml_node", "xml_document", "xml_attribute",
    # format extension strings (lowercase) in prose references like "output.pptx"
    "pptx", "pdf", "html", "svg", "tiff", "odp", "ppt", "xlsx",
})

# Platform frontmatter detection.
_PLATFORM_FM_RE = re.compile(r"^platform:\s*[\"']?(\w+)", re.MULTILINE)

# Identifier extraction regex: backticked names, possibly dotted
_BACKTICK_RE = re.compile(r"`([A-Za-z_]\w*(?:(?:::|\.)[A-Za-z_]\w*)*)`")

# TC-5317: Marker pattern for identifiers replaced by _identifier_repair.py.
# Compiled at module level (not per-call) for performance.
_UNKNOWN_MARKER_RE = re.compile(r"_UNKNOWN_\w+_")


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
        # TC-5325: Split on both . and :: so C++ namespace parts (Aspose, Slides, Foss)
        # are added to member_names. Without this, fully-qualified C++ backtick identifiers
        # like `Aspose::Slides::Foss::Presentation` produce false-positive HIGH findings for
        # the namespace qualifier parts. Python/Java/dotnet entries use . only — unaffected.
        for part in re.split(r"(?:::|\.)", imp):
            if part:
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
    # TC-NET-006: Extend exemptions for .NET platform to avoid false positives.
    # TC-5315: Extend exemptions for Java platform to avoid Java stdlib false positives.
    # TC-5329-fix: Search full content — platform: field can be past char 500 in long frontmatter.
    _pm = _PLATFORM_FM_RE.search(content)
    if _pm:
        _platform_slug = _pm.group(1).lower()
        if _platform_slug == "dotnet":
            all_exempt = all_exempt | _DOTNET_STDLIB
        elif _platform_slug == "java":
            all_exempt = all_exempt | _JAVA_STDLIB
        elif _platform_slug == "cpp":
            # TC-5329: Exempt C++ stdlib identifiers (std, istream, chrono, etc.).
            # NOTE: .NET types (System, InvalidOperationException) are intentionally
            # NOT exempted — they are genuine errors in C++ content.
            all_exempt = all_exempt | _CPP_STDLIB
    # Build lowercase versions for case-insensitive variable-name matching
    # e.g. `workbook` should match class `Workbook` (common Python convention)
    class_names_lower = frozenset(c.lower() for c in class_names)

    # TC-5317: Detect _UNKNOWN_{ident}_ markers left by identifier repair.
    # These markers indicate the LLM hallucinated an identifier and the repair
    # logic preserved the line structure while flagging the bad token.
    # Check in both prose and code blocks (use full body, not just prose strip)
    if _UNKNOWN_MARKER_RE.search(body):
        findings.append(Finding(
            check="api_allowlist",
            message=(
                "Code contains _UNKNOWN_ marker from identifier repair — "
                "LLM used an identifier not in the API surface"
            ),
            severity="high",
            location=slug,
        ))

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
