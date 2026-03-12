"""Check 3: Code example validation."""
from __future__ import annotations

import ast
import re
import sys

from launcher.models.evaluation import Finding

# Python standard-library module names — portable across all platforms.
# `sys.stdlib_module_names` ships with CPython 3.10+ on every OS.
# The union with the fallback frozenset ensures coverage on older runtimes.
_STDLIB_MODULES: frozenset[str] = frozenset(
    getattr(sys, "stdlib_module_names", frozenset())
) | frozenset({
    # Fallback: covers the most common stdlib modules found in library examples.
    "os", "sys", "io", "re", "json", "math", "datetime", "time",
    "logging", "collections", "pathlib", "typing", "abc", "functools",
    "itertools", "contextlib", "shutil", "tempfile", "glob", "fnmatch",
    "struct", "copy", "dataclasses", "enum", "hashlib", "base64",
    "urllib", "http", "socket", "threading", "subprocess", "string",
    "random", "decimal", "fractions", "statistics", "operator",
    "weakref", "types", "inspect", "traceback", "warnings", "gc",
    "builtins", "importlib", "pkgutil", "platform", "argparse",
    "csv", "configparser", "xml", "html", "email", "unittest",
})


def _extract_module_name(import_line: str) -> str:
    """Return the top-level package name from an import statement.

    Examples::

        "import os"                          -> "os"
        "import os.path"                     -> "os"
        "from pathlib import Path"           -> "pathlib"
        "from xml.etree import ElementTree"  -> "xml"
    """
    stripped = import_line.strip()
    if stripped.startswith("from "):
        # "from X.Y import Z" -> first token after "from" -> split on "." -> [0]
        parts = stripped[5:].split()
        return parts[0].split(".")[0] if parts else ""
    if stripped.startswith("import "):
        # "import X.Y, A.B" or "import X as alias" -> first module token
        rest = stripped[7:].split(",")[0].strip()
        rest = rest.split(" as ")[0].strip()  # strip alias
        return rest.split(".")[0]
    return ""


def check_code(
    content: str,
    slug: str,
    *,
    canonical_import: str = "",
    runtime_import: str = "",
    import_allowlist: list[str] | None = None,
) -> list[Finding]:
    """Validate code blocks: language tags, syntax, imports."""
    findings: list[Finding] = []
    body = re.sub(r"^---\n.*?\n---\n?", "", content, flags=re.DOTALL)

    # Find fenced code blocks
    blocks = re.findall(r"```(\w*)\n(.*?)```", body, re.DOTALL)

    if not blocks:
        return findings  # No code blocks is not an error by itself

    for i, (lang, code) in enumerate(blocks):
        loc = f"{slug}:code-block-{i + 1}"

        # Check language tag
        if not lang:
            findings.append(
                Finding(
                    check="code",
                    message="Code block missing language tag",
                    severity="medium",
                    location=loc,
                )
            )

        # AST-validate Python code (skip shell commands mis-tagged as python)
        if lang == "python":
            first_line = code.strip().split("\n")[0].strip() if code.strip() else ""
            is_shell = first_line.startswith(("pip ", "pip3 ", "python ", "python3 ", "$ "))
            if not is_shell:
                try:
                    ast.parse(code)
                except SyntaxError as e:
                    findings.append(
                        Finding(
                            check="code",
                            message=f"Python syntax error: {e.msg}",
                            severity="high",
                            location=loc,
                        )
                    )

        # Check canonical import usage — flag non-canonical, non-stdlib imports.
        # Standard library modules (os, io, pathlib, sys, etc.) are always allowed
        # alongside the library import; only competing third-party packages are flagged.
        if lang == "python":
            # Use runtime_import (e.g. "aspose.threed") if available, else canonical_import
            effective_import = runtime_import or canonical_import
            if effective_import:
                lines = code.strip().split("\n")
                for line in lines:
                    stripped = line.strip()
                    if stripped.startswith("import ") or stripped.startswith("from "):
                        if effective_import not in stripped:
                            # Stdlib modules are always allowed on all platforms
                            module_name = _extract_module_name(stripped)
                            if module_name in _STDLIB_MODULES:
                                continue
                            # User-configured allowlist check
                            if import_allowlist and any(
                                allowed in stripped for allowed in import_allowlist
                            ):
                                continue
                            findings.append(
                                Finding(
                                    check="code",
                                    message=f"Import not in allowlist: {stripped}",
                                    severity="medium",
                                    location=loc,
                                )
                            )

    return findings
