"""Gate: KB How-To Evidence Validation.

Spec v1.1 J6: Validates that conversion how-to drafts only reference
format names evidenced in ``product_facts.supported_formats``.

This is a **warn-only** gate: it always returns ``True`` for the gate pass
flag, but emits ``warn``-severity issues when hallucinated format names
are detected. This matches the advisory nature of format evidence checks.

``graceful_artifact_skip: true`` — skips when artifacts or drafts absent.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

# Common English words that can false-positive as format acronyms
_FALSE_POSITIVES = frozenset({
    "THE", "AND", "FOR", "NOT", "USE", "SEE", "ALL", "CAN", "HAS",
    "HOW", "RUN", "SET", "GET", "NEW", "OLD", "TRY", "ADD", "PUT",
    "API", "SDK", "CLI", "IDE", "URL", "PDF",
    # Common words from product names and 3D/document domain
    "3D", "2D", "NET", "VIA", "PY", "OPEN", "SAVE", "LOAD", "FILE",
    "SCENE", "MESH", "NODE", "DATA", "CODE", "PASS", "CALL",
    "THREED", "ASPOSE", "MODEL", "MODELS", "PRINT",
    # Additional false positives from real pilot drafts
    "AUTHOR", "COM", "TITLE", "EXPORT", "IMPORT", "FORMAT",
    "NAME", "TYPE", "INFO", "SCALE", "UNIT",
})


def _extract_format_like_tokens(content: str) -> Set[str]:
    """Extract tokens that look like file format references.

    Matches patterns like: .PDF, .XLSX, FBX format, OBJ file, etc.
    Returns uppercase-normalized set.
    """
    tokens: Set[str] = set()

    # Dot-prefixed extensions: ".pdf", ".obj"
    for m in re.finditer(r"\.([A-Za-z0-9]{2,6})\b", content):
        tokens.add(m.group(1).upper())

    # Format names in "X format", "X file", "X document"
    for m in re.finditer(
        r"\b([A-Z]{2,6})\s+(?:format|file|document|model)", content
    ):
        tokens.add(m.group(1).upper())

    # "convert X to Y" pattern
    for m in re.finditer(
        r"convert\s+(\w+)\s+to\s+(\w+)", content, re.IGNORECASE
    ):
        for g in (m.group(1), m.group(2)):
            upper = g.upper()
            if 2 <= len(upper) <= 6 and upper.isalpha():
                tokens.add(upper)

    return tokens


def execute_gate(
    run_dir: Path, profile: str
) -> Tuple[bool, List[Dict[str, Any]]]:
    """Execute Gate: KB How-To Evidence Validation.

    Args:
        run_dir: Run directory path.
        profile: Validation profile (local, ci, prod).

    Returns:
        Tuple of (gate_passed, issues). Always passes (warn-only).
    """
    issues: List[Dict[str, Any]] = []

    page_plan_path = run_dir / "artifacts" / "page_plan.json"
    product_facts_path = run_dir / "artifacts" / "product_facts.json"
    drafts_kb = run_dir / "drafts" / "kb"

    # Graceful skip when any required artifact is missing
    if not page_plan_path.exists() or not product_facts_path.exists():
        return True, []
    if not drafts_kb.exists():
        return True, []

    try:
        with page_plan_path.open(encoding="utf-8") as f:
            page_plan = json.load(f)
        with product_facts_path.open(encoding="utf-8") as f:
            product_facts = json.load(f)
    except Exception as e:
        issues.append({
            "issue_id": "gate_kb_howto_evidence_load_error",
            "gate": "gate_kb_howto_evidence",
            "severity": "error",
            "message": f"Failed to load artifacts: {e}",
            "error_code": "GATE_KB_HOWTO_EVIDENCE_LOAD_ERROR",
            "status": "OPEN",
        })
        return False, issues

    # Build set of evidenced format names (uppercase for normalization)
    evidenced_formats: Set[str] = set()
    for fmt_entry in product_facts.get("supported_formats", []):
        name = fmt_entry.get("format", "")
        if name:
            evidenced_formats.add(name.upper())

    # Nothing to validate if no formats are evidenced
    if not evidenced_formats:
        return True, []

    # Find conversion how-to pages and validate their draft content
    for page in page_plan.get("pages", []):
        cs = page.get("content_strategy", {})
        if not cs.get("is_conversion_howto", False):
            continue

        slug = page.get("slug", "")
        section = page.get("section", "kb")
        draft_path = run_dir / "drafts" / section / f"{slug}.md"
        if not draft_path.exists():
            continue

        try:
            content = draft_path.read_text(encoding="utf-8")
        except Exception:
            continue

        # Extract format-like tokens from draft
        mentioned_formats = _extract_format_like_tokens(content)

        # Remove false positives and evidenced formats
        hallucinated = mentioned_formats - evidenced_formats - _FALSE_POSITIVES

        if hallucinated:
            issues.append({
                "issue_id": f"gate_kb_howto_evidence_hallucinated_{slug}",
                "gate": "gate_kb_howto_evidence",
                "severity": "warn",
                "message": (
                    f"Conversion how-to '{slug}' mentions formats not in "
                    f"product_facts.supported_formats: {sorted(hallucinated)}. "
                    f"Evidenced formats: {sorted(evidenced_formats)}."
                ),
                "error_code": "GATE_KB_HOWTO_EVIDENCE_HALLUCINATED_FORMAT",
                "status": "OPEN",
            })

    # Warn-only gate: never hard-fails (unless artifact load error above)
    return True, issues
