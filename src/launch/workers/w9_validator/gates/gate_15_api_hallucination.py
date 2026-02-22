"""Gate 15: API Hallucination Detection.

Detects potentially fabricated API references in generated content by
cross-referencing against the known API surface from product_facts.json.

TC-1832: W7 Validator Gate Enhancement

Per specs/09_validation_gates.md.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple


# Common stdlib/builtin symbols to exclude from hallucination checks
STDLIB_ALLOWLIST = frozenset({
    "print", "str", "int", "float", "list", "dict", "set", "tuple", "bool",
    "None", "True", "False", "os", "sys", "json", "re", "Path", "pathlib",
    "open", "close", "read", "write", "Exception", "TypeError", "ValueError",
    "RuntimeError", "KeyError", "IndexError", "AttributeError", "ImportError",
    "FileNotFoundError", "IOError", "OSError", "StopIteration", "NotImplementedError",
    "PermissionError", "TimeoutError", "ConnectionError", "UnicodeError",
    "ArithmeticError", "LookupError", "SyntaxError", "NameError", "OverflowError",
    "ZeroDivisionError", "RecursionError", "SystemError", "MemoryError",
    "UnicodeDecodeError", "UnicodeEncodeError", "AssertionError",
    "SemanticError", "Warning", "DeprecationWarning", "FutureWarning",
    "range", "len", "enumerate", "zip", "map", "filter", "sorted",
    "min", "max", "sum", "abs", "round", "type", "isinstance", "issubclass",
    "hasattr", "getattr", "setattr", "delattr", "property", "staticmethod",
    "classmethod", "super", "object", "bytes", "bytearray", "memoryview",
    "frozenset", "complex", "iter", "next", "hash", "id", "repr", "format",
    "Any", "Dict", "List", "Set", "Tuple", "Optional", "Union",
    "Callable", "Iterator", "Generator", "Sequence", "Mapping",
    "String", "Integer", "Float", "Boolean", "Array", "Object",
    "Math", "Date", "RegExp", "Error", "Promise", "Map", "Set",
    "Console", "Document", "Window", "Element", "Event", "Node",
    "File", "Stream", "Buffer", "Process", "Module",
})


def execute_gate(run_dir: Path, profile: str) -> Tuple[bool, List[Dict[str, Any]]]:
    """Execute Gate 15: API Hallucination Detection.

    Scans all markdown files for API references (backtick-quoted class names,
    ClassName.method() patterns) and compares against the known API surface
    from product_facts.json. Reports unrecognized symbols as warnings.

    Args:
        run_dir: Run directory path
        profile: Validation profile (local, ci, prod)

    Returns:
        Tuple of (gate_passed, issues)
    """
    issues: List[Dict[str, Any]] = []

    # Load product_facts
    pf_path = run_dir / "artifacts" / "product_facts.json"
    if not pf_path.exists():
        return True, [
            {
                "issue_id": "gate15_no_product_facts",
                "gate": "gate_15_api_hallucination",
                "severity": "info",
                "message": "No product_facts.json found, skipping API hallucination check",
                "error_code": "GATE15_API_SURFACE_MISSING",
                "status": "OPEN",
            }
        ]

    try:
        with open(pf_path, "r", encoding="utf-8") as f:
            product_facts = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        return True, [
            {
                "issue_id": "gate15_product_facts_error",
                "gate": "gate_15_api_hallucination",
                "severity": "info",
                "message": f"Error reading product_facts.json: {e}",
                "error_code": "GATE15_API_SURFACE_MISSING",
                "status": "OPEN",
            }
        ]

    api_summary = product_facts.get("api_surface_summary", {})
    if not api_summary:
        return True, [
            {
                "issue_id": "gate15_no_api_surface",
                "gate": "gate_15_api_hallucination",
                "severity": "info",
                "message": "No api_surface_summary in product_facts, skipping",
                "error_code": "GATE15_API_SURFACE_MISSING",
                "status": "OPEN",
            }
        ]

    # Build allowlist of known symbols
    known_symbols: Set[str] = set()
    for cls in api_summary.get("classes", []):
        name = cls if isinstance(cls, str) else cls.get("name", "")
        if name:
            known_symbols.add(name)
    for mod in api_summary.get("modules", []):
        name = mod if isinstance(mod, str) else mod.get("name", "")
        if name:
            known_symbols.add(name)
    for func in api_summary.get("functions", []):
        name = func if isinstance(func, str) else func.get("name", "")
        if name:
            known_symbols.add(name)

    # Also load code_analysis.json for real API symbols from AST parsing (TC-1900)
    # TC-2370: also extract per-class method lists for method signature validation
    class_methods: Dict[str, Set[str]] = {}
    ca_path = run_dir / "artifacts" / "code_analysis.json"
    if ca_path.exists():
        try:
            with open(ca_path, "r", encoding="utf-8") as f:
                code_analysis = json.load(f)
            for cls in code_analysis.get("classes", []):
                cls_data = cls if isinstance(cls, dict) else {"name": cls}
                cls_name = cls_data.get("name", "")
                methods = cls_data.get("methods", [])
                if cls_name:
                    known_symbols.add(cls_name)
                    class_methods[cls_name] = {
                        m if isinstance(m, str) else m.get("name", "")
                        for m in methods
                    } - {""}
            for func in code_analysis.get("functions", []):
                name = func if isinstance(func, str) else func.get("name", "")
                if name:
                    known_symbols.add(name)
        except (json.JSONDecodeError, OSError):
            pass  # code_analysis is supplementary, not required

    if not known_symbols:
        return True, []

    # Scan markdown files in work/site
    site_dir = run_dir / "work" / "site"
    if not site_dir.exists():
        return True, []

    md_files = sorted(site_dir.rglob("*.md"))

    # Pattern: backtick-quoted identifiers that look like class/module references
    # Matches `ClassName`, `ClassName.method`, `ClassName.method.sub_method`
    api_ref_pattern = re.compile(
        r'`([A-Z][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)`'
    )

    # Cap per-file issues to avoid noise on reference/API doc pages
    MAX_ISSUES_PER_FILE = 10

    for md_file in md_files:
        try:
            content = md_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        # Skip code blocks for prose-level analysis
        content_no_code = _strip_code_blocks(content)

        file_issues: List[Dict[str, Any]] = []

        for match in api_ref_pattern.finditer(content_no_code):
            full_ref = match.group(1)
            # Extract the top-level class/module name
            symbol = full_ref.split(".")[0]

            if symbol in STDLIB_ALLOWLIST:
                continue  # Standard library / common type

            line_num = content_no_code[:match.start()].count("\n") + 1

            if symbol in known_symbols:
                # TC-2370: method signature check — known class, check the member
                if "." in full_ref and symbol in class_methods:
                    member = full_ref.split(".")[1].split("(")[0]
                    if member and member not in class_methods[symbol]:
                        file_issues.append({
                            "issue_id": (
                                f"gate15_unknown_method_{md_file.stem}"
                                f"_{line_num}_{symbol}_{member}"
                            ),
                            "gate": "gate_15_api_hallucination",
                            "severity": "warn",
                            "message": f"Unknown method `{full_ref}` on class `{symbol}`",
                            "error_code": "GATE15_UNKNOWN_METHOD",
                            "location": {"path": str(md_file), "line": line_num},
                            "status": "OPEN",
                        })
                        if len(file_issues) >= MAX_ISSUES_PER_FILE:
                            break
                continue  # Symbol itself is known — not a class-level hallucination

            file_issues.append(
                {
                    "issue_id": f"gate15_unrecognized_api_{md_file.stem}_{line_num}_{symbol}",
                    "gate": "gate_15_api_hallucination",
                    "severity": "warn",
                    "message": f"Potentially fabricated API reference: `{full_ref}`",
                    "error_code": "GATE15_UNRECOGNIZED_API",
                    "location": {"path": str(md_file), "line": line_num},
                    "status": "OPEN",
                }
            )

            if len(file_issues) >= MAX_ISSUES_PER_FILE:
                break

        issues.extend(file_issues)

    # Gate always passes (warnings only — hallucination detection is advisory)
    gate_passed = not any(
        issue.get("severity") in ["blocker", "error"] for issue in issues
    )

    return gate_passed, issues


def _strip_code_blocks(content: str) -> str:
    """Strip fenced code blocks from markdown content.

    Preserves line count by replacing code block content with empty lines
    so that line number calculations remain accurate.

    Args:
        content: Markdown content

    Returns:
        Content with code blocks replaced by blank lines
    """
    lines = content.split("\n")
    result: List[str] = []
    in_code_block = False

    for line in lines:
        if line.strip().startswith("```") or line.strip().startswith("~~~"):
            in_code_block = not in_code_block
            result.append("")  # Preserve line count
        elif in_code_block:
            result.append("")  # Preserve line count
        else:
            result.append(line)

    return "\n".join(result)
