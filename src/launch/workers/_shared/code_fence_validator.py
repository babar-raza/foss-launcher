"""Shared code fence validation logic (TC-2870).

Reusable validation of Python code fences against an API inventory.
Used by:
  - Gate 15b (w9_validator) — post-generation validation with severity-aware reporting
  - W5 (multi_pass.py) — post-draft sanitization with repair-or-pseudocode fallback

This module provides severity-agnostic validation; callers decide policy.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple


# Common stdlib/third-party modules to exclude from unknown-import checks.
# Canonical copy — Gate 15b and W5 both import from here.
STDLIB_IMPORT_ALLOWLIST = frozenset({
    # Python stdlib
    "os", "sys", "json", "re", "pathlib", "io", "math", "time", "datetime",
    "collections", "itertools", "functools", "operator", "typing", "abc",
    "enum", "dataclasses", "copy", "pprint", "textwrap", "string",
    "struct", "array", "queue", "threading", "multiprocessing",
    "subprocess", "shutil", "tempfile", "glob", "fnmatch",
    "hashlib", "hmac", "secrets", "base64", "binascii",
    "csv", "configparser", "argparse", "logging", "warnings",
    "unittest", "doctest", "pdb", "traceback", "inspect",
    "contextlib", "weakref", "gc", "dis", "ast",
    "html", "xml", "urllib", "http", "email", "mimetypes",
    "socket", "ssl", "select", "signal", "ctypes",
    "sqlite3", "dbm", "shelve", "pickle", "marshal",
    "gzip", "bz2", "lzma", "zipfile", "tarfile",
    "random", "statistics", "decimal", "fractions",
    "locale", "gettext", "unicodedata",
    "platform", "sysconfig", "site",
    # Common third-party
    "numpy", "np", "pandas", "pd", "matplotlib", "plt",
    "scipy", "sklearn", "torch", "tensorflow", "tf",
    "requests", "flask", "django", "fastapi",
    "PIL", "pillow", "cv2", "opencv",
    "pytest", "mock", "unittest",
    "yaml", "toml", "dotenv",
    "tqdm", "rich", "click",
    "setuptools", "pip", "pkg_resources",
})

# Python built-in classes/functions that should never be flagged as unknown.
BUILTIN_CLASSES = frozenset({
    # Built-in types
    "bool", "bytearray", "bytes", "complex", "dict", "float", "frozenset",
    "int", "list", "memoryview", "object", "property", "range", "set",
    "slice", "str", "tuple", "type", "super",
    # Built-in exceptions (subset — most common)
    "BaseException", "Exception", "ArithmeticError", "AssertionError",
    "AttributeError", "EOFError", "FileExistsError", "FileNotFoundError",
    "ImportError", "IndexError", "KeyError", "MemoryError", "NameError",
    "NotImplementedError", "OSError", "OverflowError", "PermissionError",
    "RuntimeError", "StopIteration", "SyntaxError", "SystemError",
    "SystemExit", "TypeError", "ValueError", "Warning", "ZeroDivisionError",
    # Common builtins that look like constructors
    "enumerate", "filter", "iter", "map", "max", "min", "next",
    "open", "print", "reversed", "sorted", "sum", "zip",
    "classmethod", "staticmethod", "abs", "all", "any",
    "bin", "callable", "chr", "compile", "delattr", "dir",
    "divmod", "eval", "exec", "format", "getattr", "globals",
    "hasattr", "hash", "hex", "id", "input", "isinstance",
    "issubclass", "len", "locals", "oct", "ord", "pow",
    "repr", "round", "setattr", "vars",
    # Common stdlib classes used as constructors
    "Path", "PurePath", "PosixPath", "WindowsPath",
    "Counter", "OrderedDict", "defaultdict", "deque", "namedtuple",
    "Decimal", "Fraction",
    "Thread", "Lock", "Event", "Timer", "Semaphore",
    "Queue", "PriorityQueue", "LifoQueue",
    "StringIO", "BytesIO", "Pattern",
})

# Regex for extracting Python code fences from markdown.
PYTHON_FENCE_RE = re.compile(
    r'^```(?:python|py)\s*\n(.*?)^```',
    re.MULTILINE | re.DOTALL,
)


@dataclass
class CodeFenceIssue:
    """Structured issue from code fence validation (severity-agnostic)."""

    error_type: str   # "unknown_import", "unknown_method", "unknown_class"
    symbol: str       # The offending symbol name
    class_name: str = ""  # Resolved class (for method issues)
    line: int = 0     # Line within the fence (1-based)
    message: str = ""


# -----------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------


def extract_python_code_fences(content: str) -> List[Tuple[str, int]]:
    """Extract Python code fences from markdown.

    Returns:
        List of (code_string, line_offset) tuples.
    """
    results = []
    for match in PYTHON_FENCE_RE.finditer(content):
        code = match.group(1)
        line_offset = content[:match.start()].count("\n") + 1
        results.append((code, line_offset))
    return results


def build_symbol_lookups(
    inventory: Dict[str, Any],
) -> Tuple[Set[str], Set[str], Dict[str, Set[str]], Set[str]]:
    """Build lookup sets from API inventory.

    Returns:
        (known_imports, known_classes, class_methods, known_functions)

    ``class_methods`` includes both methods and properties.
    """
    known_imports: Set[str] = set()
    known_classes: Set[str] = set()
    class_methods: Dict[str, Set[str]] = {}

    package_name = inventory.get("package_name", "")
    if package_name:
        known_imports.add(package_name)
        known_imports.add(package_name.replace("-", "."))
        known_imports.add(package_name.replace("-", "_"))

    for cls in inventory.get("classes", []):
        if isinstance(cls, dict):
            name = cls.get("name", "")
            if name:
                known_classes.add(name)
                methods = cls.get("methods", [])
                class_methods[name] = {
                    m if isinstance(m, str) else m.get("name", "")
                    for m in methods
                } - {""}
                for prop in cls.get("properties", []):
                    prop_name = prop if isinstance(prop, str) else prop.get("name", "")
                    if prop_name:
                        class_methods[name].add(prop_name)
                imp_path = cls.get("import_path", "")
                if imp_path:
                    parts = imp_path.split(".")
                    for i in range(len(parts)):
                        known_imports.add(".".join(parts[: i + 1]))
        elif isinstance(cls, str):
            known_classes.add(cls)

    for mod in inventory.get("modules", []):
        if isinstance(mod, str):
            known_imports.add(mod)

    known_functions: Set[str] = set()
    for fn in inventory.get("functions", []):
        if isinstance(fn, str):
            if fn:
                known_functions.add(fn)
        elif isinstance(fn, dict):
            fn_name = fn.get("name", "")
            if fn_name:
                known_functions.add(fn_name)

    return known_imports, known_classes, class_methods, known_functions


def build_type_bindings(
    tree: ast.Module,
    known_classes: Set[str],
    class_methods: Dict[str, Set[str]],
    known_imports: Set[str],
) -> Tuple[Dict[str, str], Dict[str, str]]:
    """Build variable-to-class type bindings from AST (single pass).

    Returns:
        (var_types, import_aliases)
    """
    var_types: Dict[str, str] = {}
    import_aliases: Dict[str, str] = {}

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.asname:
                    import_aliases[alias.asname] = alias.name

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                for alias in node.names:
                    actual_name = alias.name
                    alias_name = alias.asname or alias.name
                    if actual_name in known_classes:
                        import_aliases[alias_name] = actual_name
                    else:
                        import_aliases[alias_name] = f"{node.module}.{actual_name}"

        elif isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name):
                var_name = target.id
                call_class = _resolve_call_class(
                    node.value, known_classes, import_aliases,
                )
                if call_class:
                    var_types[var_name] = call_class
                elif var_name in var_types:
                    del var_types[var_name]

    return var_types, import_aliases


def validate_code_fence(
    code_str: str,
    inventory: Dict[str, Any],
    *,
    check_methods: bool = True,
    check_constructors: bool = True,
) -> List[CodeFenceIssue]:
    """Validate a Python code string against an API inventory.

    Returns structured issues (no severity — caller decides policy).
    Pseudocode (SyntaxError on parse) returns empty list.
    """
    try:
        tree = ast.parse(code_str)
    except SyntaxError:
        return []

    known_imports, known_classes, class_methods, known_functions = build_symbol_lookups(
        inventory,
    )
    if not known_classes and not known_imports:
        return []

    var_types, import_aliases = build_type_bindings(
        tree, known_classes, class_methods, known_imports,
    )

    issues: List[CodeFenceIssue] = []

    # Check imports
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                module_name = alias.name.split(".")[0]
                if module_name in STDLIB_IMPORT_ALLOWLIST:
                    continue
                if module_name in known_imports or alias.name in known_imports:
                    continue
                if any(
                    ki.startswith(module_name + ".")
                    or ki.startswith(module_name.replace("-", "."))
                    for ki in known_imports
                ):
                    continue
                issues.append(CodeFenceIssue(
                    error_type="unknown_import",
                    symbol=alias.name,
                    line=getattr(node, "lineno", 0),
                    message=f"Unknown import `{alias.name}` not in API inventory",
                ))

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                module_root = node.module.split(".")[0]
                if module_root in STDLIB_IMPORT_ALLOWLIST:
                    continue
                if module_root in known_imports or node.module in known_imports:
                    continue
                if any(
                    ki.startswith(module_root + ".")
                    or ki.startswith(module_root.replace("-", "."))
                    for ki in known_imports
                ):
                    continue
                issues.append(CodeFenceIssue(
                    error_type="unknown_import",
                    symbol=node.module,
                    line=getattr(node, "lineno", 0),
                    message=f"Unknown import `from {node.module}` not in API inventory",
                ))

    # Check attribute access with type inference
    if check_methods:
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
                name = node.value.id
                method_name = node.attr
                resolved_class: Optional[str] = None

                if name in known_classes:
                    resolved_class = name
                elif name in import_aliases and import_aliases[name] in known_classes:
                    resolved_class = import_aliases[name]
                elif name in var_types:
                    resolved_class = var_types[name]

                if resolved_class and resolved_class in class_methods:
                    if method_name not in class_methods[resolved_class]:
                        issues.append(CodeFenceIssue(
                            error_type="unknown_method",
                            symbol=method_name,
                            class_name=resolved_class,
                            line=getattr(node, "lineno", 0),
                            message=f"Unknown method `{resolved_class}.{method_name}` not in API inventory",
                        ))

    return issues


# -----------------------------------------------------------------------
# Internal helpers
# -----------------------------------------------------------------------


def _resolve_call_class(
    node: ast.expr,
    known_classes: Set[str],
    import_aliases: Dict[str, str],
) -> Optional[str]:
    """Resolve an ast expression to a known class name (from a Call)."""
    if not isinstance(node, ast.Call):
        return None

    func = node.func

    if isinstance(func, ast.Name):
        name = func.id
        resolved = import_aliases.get(name, name)
        if resolved in known_classes:
            return resolved

    elif isinstance(func, ast.Attribute):
        class_name = func.attr
        if class_name in known_classes:
            return class_name
        if isinstance(func.value, ast.Name):
            alias = func.value.id
            if alias in import_aliases:
                return class_name if class_name in known_classes else None

    return None


# -----------------------------------------------------------------------
# Multi-language code fence audit API (TC-3110)
# -----------------------------------------------------------------------

# Regex for extracting any language-tagged code fence from markdown.
GENERIC_FENCE_RE = re.compile(
    r'^```(\w+)\s*\n(.*?)^```',
    re.MULTILINE | re.DOTALL,
)

# Language-specific builtin/stdlib skip sets for non-Python languages.
_LANG_BUILTINS: Dict[str, FrozenSet[str]] = {
    'typescript': frozenset({
        'console',
        'Promise',
        'Array',
        'Map',
        'Set',
        'Error',
        'TypeError',
        'undefined',
        'null',
        'true',
        'false',
        'void',
        'string',
        'number',
        'boolean',
        'any',
        'never',
        'object',
        'Symbol',
        'BigInt',
        'Math',
        'JSON',
        'Date',
        'RegExp',
        'Function',
        'Event',
        'window',
        'document',
        'process',
        'module',
        'exports',
        'require',
        'Buffer',
        'setTimeout',
        'clearTimeout',
        'setInterval',
    }),
    'javascript': frozenset({
        'console',
        'Promise',
        'Array',
        'Map',
        'Set',
        'Error',
        'TypeError',
        'undefined',
        'null',
        'Math',
        'JSON',
        'Date',
        'RegExp',
        'window',
        'document',
        'process',
        'module',
        'exports',
        'require',
        'Buffer',
        'setTimeout',
        'clearTimeout',
        'setInterval',
    }),
    'go': frozenset({
        'fmt',
        'os',
        'io',
        'log',
        'strings',
        'errors',
        'context',
        'sync',
        'time',
        'http',
        'net',
        'path',
        'bytes',
        'bufio',
        'strconv',
        'unicode',
        'math',
        'rand',
        'sort',
        'reflect',
        'json',
        'xml',
        'csv',
        'regexp',
        'testing',
        'flag',
        'make',
        'new',
        'len',
        'cap',
        'append',
        'copy',
        'delete',
        'panic',
        'recover',
        'close',
        'print',
        'println',
    }),
}


@dataclass
class CompactAllowlist:
    """Minimal structured allowlist for programmatic code fence auditing.

    Designed for zero-copy comparison -- all fields are frozensets/dicts
    built once and reused across multiple fence audits per page.
    """
    package_stems: FrozenSet[str]            # package import roots
    class_names: FrozenSet[str]              # known class names
    method_index: Dict[str, FrozenSet[str]]  # class -> methods
    known_functions: FrozenSet[str]          # module-level function names


def build_compact_allowlist(inventory: Dict[str, Any]) -> CompactAllowlist:
    """Build a compact structured allowlist from api_inventory dict.

    Reuses build_symbol_lookups() for consistency with Gate 15b validation.
    """
    known_imports, known_classes, class_methods, known_functions = build_symbol_lookups(inventory)
    # Include all known import paths as stems for prefix matching
    all_stems = frozenset(known_imports)
    # method_index: class_name -> frozenset of methods+properties
    method_index = {k: frozenset(v) for k, v in class_methods.items()}
    return CompactAllowlist(
        package_stems=all_stems,
        class_names=frozenset(known_classes),
        method_index=method_index,
        known_functions=frozenset(known_functions),
    )


# TypeScript/JavaScript identifier extraction patterns
_TS_IMPORT_FROM_RE = re.compile(r"import\s+(?:\*\s+as\s+\w+|\{([^}]*)\}|(\w+))\s+from\s+[\x27\"]([^\x27\"]+)[\x27\"]")
_TS_REQUIRE_RE = re.compile(r"require\s*\(\s*[\x27\"]([^\x27\"]+)[\x27\"]\s*\)")
_TS_NEW_RE = re.compile(r"\bnew\s+([A-Z]\w*)")
_TS_CLASS_RE = re.compile(r"\b(?:class|interface)\s+([A-Z]\w*)")

# Go identifier extraction patterns
_GO_IMPORT_RE = re.compile(r"\"([a-zA-Z][a-zA-Z0-9_/.]+)\"")
_GO_QUALIFIED_RE = re.compile(r"\b([a-zA-Z][a-zA-Z0-9_]*)\s*\.")


def extract_identifiers_heuristic(code: str, language: str) -> Set[str]:
    """Extract identifiers from a code fence using language-specific heuristics.

    Python uses AST (most accurate). TypeScript/JS/Go use regex heuristics.
    Unknown languages return empty set (validation is skipped -- safe default).
    """
    lang = language.lower()

    if lang in ("python", "py"):
        return _extract_python_identifiers(code)
    elif lang in ("typescript", "ts", "javascript", "js"):
        return _extract_ts_identifiers(code)
    elif lang in ("go", "golang"):
        return _extract_go_identifiers(code)
    else:
        return set()  # Unknown language -- skip validation


def _extract_python_identifiers(code: str) -> Set[str]:
    """Extract Python identifiers via AST with regex fallback."""
    identifiers: Set[str] = set()
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    identifiers.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    identifiers.add(node.module.split(".")[0])
                    for alias in node.names:
                        identifiers.add(alias.name)
            elif isinstance(node, ast.Attribute):
                if isinstance(node.value, ast.Name):
                    identifiers.add(node.value.id)
            elif isinstance(node, ast.Name):
                if node.id[0].isupper():  # Class-like names only
                    identifiers.add(node.id)
    except SyntaxError:
        # Fallback: regex extraction for pseudocode or invalid Python
        for m in re.finditer(r"\b([A-Z][A-Za-z0-9_]*)\b", code):
            identifiers.add(m.group(1))
        for m in re.finditer(r"(?:import|from)\s+([\w.]+)", code):
            identifiers.add(m.group(1).split(".")[0])
    return identifiers


def _extract_ts_identifiers(code: str) -> Set[str]:
    """Extract TypeScript/JavaScript identifiers via regex heuristics."""
    identifiers: Set[str] = set()
    for m in _TS_IMPORT_FROM_RE.finditer(code):
        if m.group(1):  # Named imports { X, Y }
            for name in re.split(r"[,\s]+", m.group(1)):
                name = name.strip().split(" as ")[0].strip()
                if name:
                    identifiers.add(name.split(".")[0])
        if m.group(2):  # Default import
            identifiers.add(m.group(2))
        if m.group(3):  # Module path
            identifiers.add(m.group(3).split("/")[0].lstrip("@"))
    for m in _TS_REQUIRE_RE.finditer(code):
        identifiers.add(m.group(1).split("/")[0].lstrip("@"))
    for m in _TS_NEW_RE.finditer(code):
        identifiers.add(m.group(1))
    for m in _TS_CLASS_RE.finditer(code):
        identifiers.add(m.group(1))
    return identifiers


def _extract_go_identifiers(code: str) -> Set[str]:
    """Extract Go identifiers via regex heuristics."""
    identifiers: Set[str] = set()
    for m in _GO_IMPORT_RE.finditer(code):
        parts = m.group(1).split("/")
        identifiers.add(parts[-1])
    for m in _GO_QUALIFIED_RE.finditer(code):
        identifiers.add(m.group(1))
    return identifiers


@dataclass
class FenceAuditResult:
    """Result of auditing a single code fence against an allowlist."""
    language: str
    fence_offset: int            # Character offset in source markdown
    identifiers: Set[str]        # All identifiers extracted from fence
    unknown_ids: Set[str]        # Identifiers not in allowlist
    is_valid: bool               # True when unknown_ids is empty


def audit_fence(
    code: str,
    language: str,
    allowlist: CompactAllowlist,
    *,
    fence_offset: int = 0,
) -> FenceAuditResult:
    """Validate a single code fence against a compact allowlist.

    For Python, delegates to validate_code_fence() for full AST-based
    validation (imports + method calls + constructors).
    For other languages, uses heuristic identifier extraction.
    Unknown languages always pass (is_valid=True, unknown_ids empty).
    """
    lang = language.lower()

    if lang in ("python", "py"):
        # Use full AST validation for Python -- most accurate
        issues = validate_code_fence(
            code,
            _allowlist_to_inventory_stub(allowlist),
            check_methods=True,
            check_constructors=True,
        )
        unknown_ids = {issue.symbol for issue in issues}
        all_ids = extract_identifiers_heuristic(code, language)
        return FenceAuditResult(
            language=lang,
            fence_offset=fence_offset,
            identifiers=all_ids,
            unknown_ids=unknown_ids,
            is_valid=len(unknown_ids) == 0,
        )

    # For non-Python: heuristic extraction
    identifiers = extract_identifiers_heuristic(code, language)
    lang_builtins = _LANG_BUILTINS.get(lang, frozenset())

    unknown_ids: Set[str] = set()
    for ident in identifiers:
        if not ident:
            continue
        if ident in STDLIB_IMPORT_ALLOWLIST:
            continue
        if ident in BUILTIN_CLASSES:
            continue
        if ident in lang_builtins:
            continue
        if ident in allowlist.class_names:
            continue
        if ident in allowlist.known_functions:
            continue
        if ident in allowlist.package_stems:
            continue
        if any(stem.startswith(ident) or ident.startswith(stem) for stem in allowlist.package_stems):
            continue
        unknown_ids.add(ident)

    return FenceAuditResult(
        language=lang,
        fence_offset=fence_offset,
        identifiers=identifiers,
        unknown_ids=unknown_ids,
        is_valid=len(unknown_ids) == 0,
    )


def _allowlist_to_inventory_stub(allowlist: CompactAllowlist) -> Dict[str, Any]:
    """Build minimal inventory-like dict from CompactAllowlist for validate_code_fence().

    This allows the full AST-based Python validator to run using the
    CompactAllowlist data without needing the original inventory dict.
    """
    classes = []
    for class_name, methods in allowlist.method_index.items():
        classes.append({"name": class_name, "methods": sorted(methods)})
    for cls in allowlist.class_names:
        if cls not in allowlist.method_index:
            classes.append({"name": cls, "methods": []})
    return {
        "package_name": next(
            (s for s in sorted(allowlist.package_stems) if "." not in s), ""
        ),
        "classes": classes,
        "modules": sorted(allowlist.package_stems),
        "functions": sorted(allowlist.known_functions),
        "public_surface": {"confidence": "unknown", "classes": []},
    }
