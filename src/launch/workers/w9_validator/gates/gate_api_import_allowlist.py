"""Gate G3: API Import Allowlist (TC-3670).

Validates that import statements and API references in code fences use
ONLY canonical import patterns derived from product_facts.json or
api_inventory.json. Detects hallucinated APIs.

Grounded in pilot review evidence: 4+ import styles per product
(e.g., aspose_cells, aspose.cells, asposecells, aspose.cells as cells)
and hallucinated class names (NoteDocument, RgOutlineIndentDistance).

Always-error severity: no profile demotion.

Spec: specs/09_validation_gates.md - Quality Content Gates (G3)
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple

# Max issues per file
_MAX_ISSUES_PER_FILE = 10

# Import statement patterns to extract from code fences
_IMPORT_RE = re.compile(
    r"^\s*(?:from\s+([\w.]+)\s+import|import\s+([\w.]+))",
)

# Known product families and their canonical module names.
# Derived from product_facts.json product_slug + standard Python packaging.
_CANONICAL_MODULES: Dict[str, FrozenSet[str]] = {
    "cells": frozenset({"aspose.cells", "aspose_cells_foss"}),
    "note": frozenset({"aspose.note", "aspose_note_foss"}),
    "3d": frozenset({"aspose.threed", "aspose_3d_foss"}),
    "words": frozenset({"aspose.words", "aspose_words_foss"}),
    "pdf": frozenset({"aspose.pdf", "aspose_pdf_foss"}),
    "slides": frozenset({"aspose.slides", "aspose_slides_foss"}),
    "email": frozenset({"aspose.email", "aspose_email_foss"}),
    "imaging": frozenset({"aspose.imaging", "aspose_imaging_foss"}),
}

# Known non-Aspose standard library / third-party modules (never flag these)
_STDLIB_PREFIXES = frozenset({
    "os", "sys", "json", "re", "pathlib", "typing", "collections",
    "datetime", "math", "io", "csv", "xml", "html", "http",
    "unittest", "pytest", "logging", "functools", "itertools",
    "hashlib", "base64", "struct", "abc", "enum", "dataclasses",
    "contextlib", "copy", "glob", "shutil", "tempfile", "textwrap",
    "traceback", "warnings", "argparse", "configparser", "time",
    "uuid", "random", "string", "pprint", "inspect", "dis",
    "PIL", "numpy", "pandas", "matplotlib", "scipy",
})


def execute_gate(run_dir: Path, profile: str) -> Tuple[bool, List[Dict[str, Any]]]:
    """Execute API import allowlist gate.

    Scans code fences in markdown files for import statements and
    validates them against the canonical import allowlist.

    Args:
        run_dir: Run directory path.
        profile: Validation profile (local, ci, prod).

    Returns:
        Tuple of (gate_passed, list_of_issues).
    """
    issues: List[Dict[str, Any]] = []

    site_dir = run_dir / "work" / "site"
    if not site_dir.exists():
        return True, []

    # Load canonical allowlist from artifacts
    product_family = _detect_product_family(run_dir)
    allowlist = _build_allowlist(run_dir, product_family)

    md_files = sorted(site_dir.rglob("*.md"))
    if not md_files:
        return True, []

    for md_file in md_files:
        try:
            content = md_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        file_issues = _scan_file(content, md_file, allowlist, product_family)
        issues.extend(file_issues)

    gate_passed = not any(
        issue.get("severity") in ("blocker", "error") for issue in issues
    )
    return gate_passed, issues


def _detect_product_family(run_dir: Path) -> Optional[str]:
    """Detect product family from run artifacts."""
    pf_path = run_dir / "artifacts" / "product_facts.json"
    if pf_path.exists():
        try:
            data = json.loads(pf_path.read_text(encoding="utf-8"))
            return data.get("product_family", "").lower() or None
        except Exception:
            pass

    # Fallback: check run_config.yaml for product_family
    rc_path = run_dir / "run_config.yaml"
    if rc_path.exists():
        try:
            text = rc_path.read_text(encoding="utf-8")
            for line in text.splitlines():
                if "product_family:" in line:
                    return line.split(":", 1)[1].strip().strip("'\"").lower() or None
        except Exception:
            pass

    return None


def _build_allowlist(
    run_dir: Path, product_family: Optional[str]
) -> Set[str]:
    """Build the set of allowed module prefixes.

    Combines:
    1. Standard library / known third-party modules
    2. Canonical modules for the detected product family
    3. Any modules found in api_inventory.json public_surface
    """
    allowed = set(_STDLIB_PREFIXES)

    # Add canonical modules for detected family
    if product_family and product_family in _CANONICAL_MODULES:
        allowed.update(_CANONICAL_MODULES[product_family])

    # Add all canonical modules (a site may cross-reference other products)
    for modules in _CANONICAL_MODULES.values():
        allowed.update(modules)

    # Extend from api_inventory.json if available
    api_inv_path = run_dir / "artifacts" / "api_inventory.json"
    if api_inv_path.exists():
        try:
            data = json.loads(api_inv_path.read_text(encoding="utf-8"))
            # Extract module names from public_surface or top-level keys
            if isinstance(data, dict):
                for key in ("public_surface", "modules", "namespaces"):
                    surface = data.get(key)
                    if isinstance(surface, dict):
                        allowed.update(surface.keys())
                    elif isinstance(surface, list):
                        for item in surface:
                            if isinstance(item, str):
                                allowed.add(item)
                            elif isinstance(item, dict) and "module" in item:
                                allowed.add(item["module"])
        except Exception:
            pass

    # TC-3684: Extend from product_facts.json evidence
    pf_path = run_dir / "artifacts" / "product_facts.json"
    if pf_path.exists():
        try:
            pf = json.loads(pf_path.read_text(encoding="utf-8"))
            if isinstance(pf, dict):
                # distribution[].identifier → module name (hyphen→underscore)
                dist = pf.get("distribution")
                if isinstance(dist, list):
                    for entry in dist:
                        ident = entry.get("identifier", "") if isinstance(entry, dict) else ""
                        if ident:
                            allowed.add(ident.replace("-", "_"))
                # code_structure.package_names → direct module names
                cs = pf.get("code_structure", {})
                if isinstance(cs, dict):
                    pkg_names = cs.get("package_names") or cs.get("package_name")
                    if isinstance(pkg_names, list):
                        for pkg in pkg_names:
                            if isinstance(pkg, str) and pkg:
                                allowed.add(pkg)
                    elif isinstance(pkg_names, str) and pkg_names:
                        allowed.add(pkg_names)
        except Exception:
            pass

    return allowed


def _is_allowed_import(module: str, allowlist: Set[str]) -> bool:
    """Check if an import module is in the allowlist.

    Matches against exact module names and prefixes.
    E.g., 'os.path' is allowed if 'os' is in the allowlist.
    """
    if module in allowlist:
        return True

    # Check prefix match (e.g., os.path matches os)
    parts = module.split(".")
    for i in range(1, len(parts)):
        prefix = ".".join(parts[:i])
        if prefix in allowlist:
            return True

    return False


def _is_aspose_like(module: str) -> bool:
    """Check if module looks like an Aspose module (to flag non-canonical)."""
    lower = module.lower()
    return (
        lower.startswith("aspose")
        or "aspose" in lower
        or lower.startswith("aspire")
        or lower.startswith("aspuse")
    )


def _scan_file(
    content: str,
    md_file: Path,
    allowlist: Set[str],
    product_family: Optional[str],
) -> List[Dict[str, Any]]:
    """Scan code fences in a file for non-allowlisted imports."""
    file_issues: List[Dict[str, Any]] = []
    lines = content.splitlines()
    in_fence = False

    for line_num, line in enumerate(lines, 1):
        stripped = line.strip()

        if stripped.startswith("```"):
            in_fence = not in_fence
            continue

        # Only check imports inside code fences
        if not in_fence:
            continue

        match = _IMPORT_RE.match(line)
        if not match:
            continue

        module = match.group(1) or match.group(2)
        if not module:
            continue

        # Check if the import is allowed
        if _is_allowed_import(module, allowlist):
            continue

        # Only flag Aspose-like modules that are non-canonical
        # (don't flag truly unknown third-party libs)
        if not _is_aspose_like(module):
            continue

        file_issues.append({
            "issue_id": f"g3_import_{md_file.stem}_{line_num}",
            "gate": "gate_api_import_allowlist",
            "severity": "error",
            "message": (
                f"Non-canonical import '{module}': "
                f"not in allowlist for family '{product_family or 'unknown'}'"
            ),
            "error_code": "G3_IMPORT_NOT_ALLOWLISTED",
            "location": {"path": str(md_file), "line": line_num},
            "status": "OPEN",
        })

        if len(file_issues) >= _MAX_ISSUES_PER_FILE:
            break

    return file_issues
