"""Gate 15b: Code Fence API Validation (TC-2811).

Validates Python code fences in generated markdown against the api_inventory.json
artifact. Unlike Gate 15 (prose-level, warn-only), this gate parses code blocks
with ast.parse() and flags unknown imports, classes, and methods at error/blocker
severity.

This is the primary defense against hallucinated API calls in published code
examples.

TC-2870: Type inference upgrade — tracks import aliases, constructor assignments,
and validates instance method calls (e.g., ``s = Scene(); s.open()``).
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# Common stdlib/third-party modules to exclude from unknown-import checks
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

# Python built-in classes/functions that should never be flagged as unknown
# constructors, even if they look like ClassName() calls.
_BUILTIN_CLASSES = frozenset({
    # Built-in types
    "bool", "bytearray", "bytes", "complex", "dict", "float", "frozenset",
    "int", "list", "memoryview", "object", "property", "range", "set",
    "slice", "str", "tuple", "type", "super",
    # Built-in exceptions
    "BaseException", "Exception", "ArithmeticError", "AssertionError",
    "AttributeError", "BlockingIOError", "BrokenPipeError",
    "BufferError", "BytesWarning", "ChildProcessError",
    "ConnectionAbortedError", "ConnectionError", "ConnectionRefusedError",
    "ConnectionResetError", "DeprecationWarning", "EOFError",
    "EnvironmentError", "FileExistsError", "FileNotFoundError",
    "FloatingPointError", "FutureWarning", "GeneratorExit",
    "IOError", "ImportError", "ImportWarning", "IndentationError",
    "IndexError", "InterruptedError", "IsADirectoryError",
    "KeyError", "KeyboardInterrupt", "LookupError",
    "MemoryError", "ModuleNotFoundError", "NameError",
    "NotADirectoryError", "NotImplementedError", "OSError",
    "OverflowError", "PendingDeprecationWarning", "PermissionError",
    "ProcessLookupError", "RecursionError", "ReferenceError",
    "ResourceWarning", "RuntimeError", "RuntimeWarning",
    "StopAsyncIteration", "StopIteration", "SyntaxError",
    "SyntaxWarning", "SystemError", "SystemExit", "TabError",
    "TimeoutError", "TypeError", "UnboundLocalError",
    "UnicodeDecodeError", "UnicodeEncodeError", "UnicodeError",
    "UnicodeTranslateError", "UnicodeWarning", "UserWarning",
    "ValueError", "Warning", "ZeroDivisionError",
    # Common built-in functions that look like constructors
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
    "StringIO", "BytesIO",
    "Pattern",
})


def execute_gate(run_dir: Path, profile: str) -> Tuple[bool, List[Dict[str, Any]]]:
    """Execute Gate 15b: Code Fence API Validation.

    Parses Python code fences in generated markdown and validates imports
    and symbol references against the api_inventory.json artifact.

    Args:
        run_dir: Run directory path
        profile: Validation profile (local, ci, prod)

    Returns:
        Tuple of (gate_passed, issues)
    """
    issues: List[Dict[str, Any]] = []

    # Load api_inventory.json
    inv_path = run_dir / "artifacts" / "api_inventory.json"
    if not inv_path.exists():
        # TC-2870: Missing inventory is error/blocker in CI/prod, info in local
        if profile in ("ci", "prod"):
            sev = "blocker" if profile == "prod" else "error"
            return False, [
                {
                    "issue_id": "gate15b_no_api_inventory",
                    "gate": "gate_15b_code_fence_api",
                    "severity": sev,
                    "message": "No api_inventory.json found — cannot validate code fence APIs",
                    "error_code": "GATE15B_INVENTORY_MISSING",
                    "status": "OPEN",
                }
            ]
        return True, [
            {
                "issue_id": "gate15b_no_api_inventory",
                "gate": "gate_15b_code_fence_api",
                "severity": "info",
                "message": "No api_inventory.json found, skipping code fence API validation",
                "error_code": "GATE15B_INVENTORY_MISSING",
                "status": "OPEN",
            }
        ]

    try:
        with open(inv_path, "r", encoding="utf-8") as f:
            inventory = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        # TC-2870: Corrupted inventory is error/blocker in CI/prod, info in local
        if profile in ("ci", "prod"):
            sev = "blocker" if profile == "prod" else "error"
            return False, [
                {
                    "issue_id": "gate15b_inventory_error",
                    "gate": "gate_15b_code_fence_api",
                    "severity": sev,
                    "message": f"Error reading api_inventory.json: {e}",
                    "error_code": "GATE15B_INVENTORY_ERROR",
                    "status": "OPEN",
                }
            ]
        return True, [
            {
                "issue_id": "gate15b_inventory_error",
                "gate": "gate_15b_code_fence_api",
                "severity": "info",
                "message": f"Error reading api_inventory.json: {e}",
                "error_code": "GATE15B_INVENTORY_ERROR",
                "status": "OPEN",
            }
        ]

    # Build symbol lookups
    known_imports, known_classes, class_methods, known_functions = _build_symbol_lookups(inventory)

    if not known_classes and not known_imports:
        return True, []

    # Scan markdown files
    site_dir = run_dir / "work" / "site"
    if not site_dir.exists():
        return True, []

    md_files = sorted(site_dir.rglob("*.md"))
    MAX_ISSUES_PER_FILE = 15

    for md_file in md_files:
        try:
            content = md_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        fences = _extract_python_code_fences(content)
        file_issues: List[Dict[str, Any]] = []

        for code_str, line_offset in fences:
            fence_issues = _validate_code_fence(
                code_str, line_offset, md_file,
                known_imports, known_classes, class_methods,
                known_functions, profile,
            )
            file_issues.extend(fence_issues)
            if len(file_issues) >= MAX_ISSUES_PER_FILE:
                file_issues = file_issues[:MAX_ISSUES_PER_FILE]
                break

        issues.extend(file_issues)

    gate_passed = not any(
        issue.get("severity") in ["blocker", "error"] for issue in issues
    )
    return gate_passed, issues


def _build_symbol_lookups(
    inventory: Dict[str, Any],
) -> Tuple[Set[str], Set[str], Dict[str, Set[str]], Set[str]]:
    """Build lookup sets from API inventory.

    Returns:
        (known_imports, known_classes, class_methods, known_functions)

    TC-2870: Now returns 4-tuple; class_methods includes properties;
    known_functions extracted from inventory["functions"].
    """
    known_imports: Set[str] = set()
    known_classes: Set[str] = set()
    class_methods: Dict[str, Set[str]] = {}

    package_name = inventory.get("package_name", "")
    if package_name:
        # Add package name and common import variants
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
                # TC-2870: Fold properties into class_methods so property
                # access (scene.root_node) is validated the same way.
                for prop in cls.get("properties", []):
                    prop_name = prop if isinstance(prop, str) else prop.get("name", "")
                    if prop_name:
                        class_methods[name].add(prop_name)
                # Also add import_path components
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

    # TC-2870: Extract known functions from inventory
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


_PYTHON_FENCE_RE = re.compile(
    r'^```(?:python|py)\s*\n(.*?)^```',
    re.MULTILINE | re.DOTALL,
)


def _extract_python_code_fences(content: str) -> List[Tuple[str, int]]:
    """Extract Python code fences from markdown.

    Returns:
        List of (code_string, line_offset) tuples.
    """
    results = []
    for match in _PYTHON_FENCE_RE.finditer(content):
        code = match.group(1)
        line_offset = content[:match.start()].count("\n") + 1
        results.append((code, line_offset))
    return results


def _validate_code_fence(
    code_str: str,
    line_offset: int,
    md_file: Path,
    known_imports: Set[str],
    known_classes: Set[str],
    class_methods: Dict[str, Set[str]],
    known_functions: Set[str],
    profile: str,
) -> List[Dict[str, Any]]:
    """Validate a single Python code fence against the API inventory.

    TC-2870: Enhanced with type inference — tracks import aliases and
    constructor assignments so ``s = Scene(); s.open()`` is validated.

    Returns:
        List of issue dicts.
    """
    issues: List[Dict[str, Any]] = []

    # Try to parse the code
    try:
        tree = ast.parse(code_str)
    except SyntaxError:
        # Pseudocode or incomplete — skip, don't error
        return []

    # TC-2870: Build type bindings for this fence
    var_types, import_aliases = _build_type_bindings(
        tree, known_classes, class_methods, known_imports,
    )

    # Check imports
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                module_name = alias.name.split(".")[0]
                if module_name in STDLIB_IMPORT_ALLOWLIST:
                    continue
                if module_name in known_imports or alias.name in known_imports:
                    continue
                # Check if any known import starts with this module
                if any(ki.startswith(module_name + ".") or ki.startswith(module_name.replace("-", ".")) for ki in known_imports):
                    continue
                severity = _escalate_severity("error", profile)
                issues.append({
                    "issue_id": f"gate15b_unknown_import_{md_file.stem}_{line_offset}_{module_name}",
                    "gate": "gate_15b_code_fence_api",
                    "severity": severity,
                    "message": f"Unknown import `{alias.name}` not in API inventory",
                    "error_code": "GATE15B_UNKNOWN_IMPORT",
                    "location": {"path": str(md_file), "line": line_offset + (node.lineno or 1)},
                    "status": "OPEN",
                })

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                module_root = node.module.split(".")[0]
                if module_root in STDLIB_IMPORT_ALLOWLIST:
                    continue
                if module_root in known_imports or node.module in known_imports:
                    continue
                if any(ki.startswith(module_root + ".") or ki.startswith(module_root.replace("-", ".")) for ki in known_imports):
                    continue
                severity = _escalate_severity("error", profile)
                issues.append({
                    "issue_id": f"gate15b_unknown_from_import_{md_file.stem}_{line_offset}_{node.module}",
                    "gate": "gate_15b_code_fence_api",
                    "severity": severity,
                    "message": f"Unknown import `from {node.module}` not in API inventory",
                    "error_code": "GATE15B_UNKNOWN_IMPORT",
                    "location": {"path": str(md_file), "line": line_offset + (node.lineno or 1)},
                    "status": "OPEN",
                })

    # TC-2870: Check attribute access with type inference
    # Resolves: direct class refs (Scene.open), aliases (S.open where S=Scene),
    # and variable refs (s.open where s = Scene()).
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            name = node.value.id
            method_name = node.attr
            resolved_class: Optional[str] = None

            # Direct class reference: Scene.open()
            if name in known_classes:
                resolved_class = name
            # Alias reference: S.open() where S is aliased to Scene
            elif name in import_aliases and import_aliases[name] in known_classes:
                resolved_class = import_aliases[name]
            # Variable reference: scene.open() where scene = Scene()
            elif name in var_types:
                resolved_class = var_types[name]

            if resolved_class and resolved_class in class_methods:
                if method_name not in class_methods[resolved_class]:
                    # TC-2870: Escalate unknown method severity by profile
                    severity = _escalate_severity("error", profile)
                    issues.append({
                        "issue_id": f"gate15b_unknown_method_{md_file.stem}_{line_offset}_{resolved_class}_{method_name}",
                        "gate": "gate_15b_code_fence_api",
                        "severity": severity,
                        "message": f"Unknown method `{resolved_class}.{method_name}` not in API inventory",
                        "error_code": "GATE15B_UNKNOWN_METHOD",
                        "location": {"path": str(md_file), "line": line_offset + (node.lineno or 1)},
                        "status": "OPEN",
                    })

    return issues


# -----------------------------------------------------------------------
# TC-2870: Type inference helpers
# -----------------------------------------------------------------------


def _build_type_bindings(
    tree: ast.Module,
    known_classes: Set[str],
    class_methods: Dict[str, Set[str]],
    known_imports: Set[str],
) -> Tuple[Dict[str, str], Dict[str, str]]:
    """Build variable-to-class type bindings from AST (single pass).

    Handles four common LLM code patterns:
      1. ``import aspose.threed as a3d``  → alias ``a3d``
      2. ``from aspose.threed import Scene as S`` → alias ``S`` → ``Scene``
      3. ``scene = Scene()``  → ``scene`` bound to ``Scene``
      4. ``scene = aspose.threed.Scene()`` → ``scene`` bound to ``Scene``

    Conservative: if a variable is reassigned to something we can't resolve,
    we remove the binding (never flag based on stale info).

    Returns:
        (var_types, import_aliases)
        var_types: {variable_name: class_name}
        import_aliases: {alias: original_name_or_class}
    """
    var_types: Dict[str, str] = {}
    import_aliases: Dict[str, str] = {}

    for node in ast.walk(tree):
        # 1. Track import aliases
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

        # 2. Track constructor assignments: var = ClassName(...)
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
                    # Conservative: reassignment to unknown → remove binding
                    del var_types[var_name]

    return var_types, import_aliases


def _resolve_call_class(
    node: ast.expr,
    known_classes: Set[str],
    import_aliases: Dict[str, str],
) -> Optional[str]:
    """Resolve an ast expression to a known class name (from a Call).

    Returns the class name if the node is a Call to a known class constructor,
    or None otherwise.
    """
    if not isinstance(node, ast.Call):
        return None

    func = node.func

    # Direct: Scene()
    if isinstance(func, ast.Name):
        name = func.id
        resolved = import_aliases.get(name, name)
        if resolved in known_classes:
            return resolved

    # Qualified: module.Scene() or alias.Scene()
    elif isinstance(func, ast.Attribute):
        class_name = func.attr
        if class_name in known_classes:
            return class_name
        # Check alias: a3d.Scene() where a3d is alias for aspose.threed
        if isinstance(func.value, ast.Name):
            alias = func.value.id
            if alias in import_aliases:
                return class_name if class_name in known_classes else None

    return None


def _escalate_severity(base_severity: str, profile: str) -> str:
    """Escalate severity based on profile.

    prod: error -> blocker
    ci: error stays error
    local: error -> warn
    """
    if profile == "prod" and base_severity == "error":
        return "blocker"
    if profile == "local" and base_severity == "error":
        return "warn"
    return base_severity
