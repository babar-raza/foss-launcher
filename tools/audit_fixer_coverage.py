#!/usr/bin/env python3
"""Audit W9 validator error codes vs W10 fixer coverage.

Deterministically scans gate files for emitted error_codes and the W10
fixer dispatch chain for handled tokens, then cross-references them to
produce a coverage report.

Usage:
    python tools/audit_fixer_coverage.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Dict, List, NamedTuple, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[1]
_GATES_DIR = _REPO_ROOT / "src" / "launch" / "workers" / "w9_validator" / "gates"
_FIXER_PATH = _REPO_ROOT / "src" / "launch" / "workers" / "w10_fixer" / "worker.py"
_REPORT_PATH = _REPO_ROOT / "docs" / "notes" / "fixer_coverage_report.md"

# ── Scanner A: W9 error codes ───────────────────────────────────────────────

# Static codes: "error_code": "CODE" or error_code = "CODE"
_STATIC_DICT_RE = re.compile(r'"error_code"\s*:\s*"([^"]+)"')
_STATIC_ASSIGN_RE = re.compile(r'error_code\s*=\s*"([^"]+)"')

# Dynamic f-string codes: f"PREFIX_{var}" — capture the prefix
_DYNAMIC_FSTR_RE = re.compile(r'f"([A-Z][A-Z0-9_]*_)\{')

# Severity hints near error_code lines
_SEVERITY_RE = re.compile(r'"severity"\s*:\s*"([^"]+)"')


class ErrorCode(NamedTuple):
    code: str          # literal code or dynamic prefix (ends with _)
    gate_id: str       # derived from filename
    severity: str      # "blocker", "error", "warn", "info", or ""
    is_dynamic: bool   # True if this is a prefix pattern


def _derive_gate_id(path: Path) -> str:
    """Derive gate_id from filename: gate_foo.py -> foo."""
    name = path.stem
    if name.startswith("gate_"):
        name = name[5:]
    return name


def _scan_w9_error_codes() -> List[ErrorCode]:
    """Scan all W9 gate files for error_code patterns."""
    results: List[ErrorCode] = []
    seen: set[Tuple[str, str]] = set()

    for gate_file in sorted(_GATES_DIR.glob("*.py")):
        if gate_file.name.startswith("__"):
            continue
        gate_id = _derive_gate_id(gate_file)
        content = gate_file.read_text(encoding="utf-8")
        lines = content.split("\n")

        # Extract static codes
        for pattern in (_STATIC_DICT_RE, _STATIC_ASSIGN_RE):
            for m in pattern.finditer(content):
                code = m.group(1)
                key = (code, gate_id)
                if key in seen:
                    continue
                seen.add(key)
                # Find severity hint near this match
                severity = _find_nearby_severity(lines, content, m.start())
                results.append(ErrorCode(code, gate_id, severity, False))

        # Extract dynamic prefixes
        for m in _DYNAMIC_FSTR_RE.finditer(content):
            prefix = m.group(1)
            key = (prefix, gate_id)
            if key in seen:
                continue
            seen.add(key)
            severity = _find_nearby_severity(lines, content, m.start())
            results.append(ErrorCode(prefix, gate_id, severity, True))

    results.sort(key=lambda e: (e.gate_id, e.code))
    return results


def _find_nearby_severity(
    lines: List[str], content: str, match_pos: int
) -> str:
    """Find severity hint within ±5 lines of a match position."""
    line_num = content[:match_pos].count("\n")
    start = max(0, line_num - 5)
    end = min(len(lines), line_num + 6)
    window = "\n".join(lines[start:end])
    m = _SEVERITY_RE.search(window)
    return m.group(1) if m else ""


# ── Scanner B: W10 fixer coverage ───────────────────────────────────────────


class FixToken(NamedTuple):
    token: str         # the literal matched against error_code
    match_type: str    # "exact", "contains", "startswith", "in_set"
    fix_func: str      # the fix function called


# Patterns for the dispatch chain in apply_fix():
# "TOKEN" in error_code  or  "TOKEN" in code
_CONTAINS_RE = re.compile(r'"([^"]+)"\s+in\s+error_code')
# error_code == "TOKEN"
_EXACT_RE = re.compile(r'error_code\s*==\s*"([^"]+)"')
# error_code.startswith("TOKEN")
_STARTSWITH_RE = re.compile(r'error_code\.startswith\("([^"]+)"\)')
# error_code in ("TOKEN1", "TOKEN2", ...)
_IN_SET_RE = re.compile(r'error_code\s+in\s+\(([^)]+)\)')
# Fix function call: return fix_xxx(...)
_FIX_CALL_RE = re.compile(r'return\s+(fix_\w+)\(')


def _scan_w10_coverage() -> Tuple[List[FixToken], List[Tuple[str, str]]]:
    """Scan W10 fixer for dispatch tokens and fix functions.

    Returns:
        (fix_tokens, fix_functions): fix_tokens is the list of FixToken,
        fix_functions is list of (func_name, first_docstring_line).
    """
    content = _FIXER_PATH.read_text(encoding="utf-8")

    # ── Extract dispatch tokens from apply_fix() ──
    # Find the apply_fix function body
    apply_fix_match = re.search(
        r'^def apply_fix\b.*?(?=\n(?:def |class |\Z))',
        content,
        re.MULTILINE | re.DOTALL,
    )
    if not apply_fix_match:
        print("ERROR: Could not find apply_fix() in W10 worker", file=sys.stderr)
        sys.exit(1)

    dispatch_body = apply_fix_match.group(0)
    tokens: List[FixToken] = []

    # Walk the dispatch chain line-by-line to pair condition → fix function
    dispatch_lines = dispatch_body.split("\n")
    for i, line in enumerate(dispatch_lines):
        # Determine fix function from next 1-3 lines
        fix_func = ""
        for j in range(i, min(i + 4, len(dispatch_lines))):
            fm = _FIX_CALL_RE.search(dispatch_lines[j])
            if fm:
                fix_func = fm.group(1)
                break

        # Check each pattern type
        for m in _CONTAINS_RE.finditer(line):
            tokens.append(FixToken(m.group(1), "contains", fix_func))
        for m in _EXACT_RE.finditer(line):
            tokens.append(FixToken(m.group(1), "exact", fix_func))
        for m in _STARTSWITH_RE.finditer(line):
            tokens.append(FixToken(m.group(1), "startswith", fix_func))
        for m in _IN_SET_RE.finditer(line):
            members_str = m.group(1)
            for member in re.findall(r'"([^"]+)"', members_str):
                tokens.append(FixToken(member, "in_set", fix_func))

    # ── Extract fix function names and docstrings ──
    fix_funcs: List[Tuple[str, str]] = []
    for m in re.finditer(
        r'^def (fix_\w+)\([^)]*\).*?:\s*(?:"""(.*?)""")?',
        content,
        re.MULTILINE | re.DOTALL,
    ):
        name = m.group(1)
        doc = ""
        if m.group(2):
            doc = m.group(2).strip().split("\n")[0]
        fix_funcs.append((name, doc))

    return tokens, fix_funcs


# ── Matcher ──────────────────────────────────────────────────────────────────


def _check_coverage(code: str, is_dynamic: bool, tokens: List[FixToken]) -> Tuple[str, str]:
    """Check if an error code is covered by any W10 fix token.

    Returns:
        (coverage, note): coverage is "yes", "partial", or "no";
        note describes the matching token/function.
    """
    for tok in tokens:
        if tok.match_type == "exact" and code == tok.token:
            return "yes", f"exact → {tok.fix_func}()"
        if tok.match_type == "in_set" and code == tok.token:
            return "yes", f"in_set → {tok.fix_func}()"
        if tok.match_type == "contains" and tok.token in code:
            return "yes", f'contains "{tok.token}" → {tok.fix_func}()'
        if tok.match_type == "startswith" and code.startswith(tok.token):
            return "yes", f'startswith "{tok.token}" → {tok.fix_func}()'

    # For dynamic prefixes, check if the prefix itself is covered
    if is_dynamic:
        for tok in tokens:
            if tok.match_type == "startswith" and tok.token.startswith(code.rstrip("_")):
                return "partial", f'prefix startswith "{tok.token}" → {tok.fix_func}()'
            if tok.match_type == "contains" and tok.token in code:
                return "partial", f'prefix contains "{tok.token}" → {tok.fix_func}()'

    return "no", ""


# ── Blocker risk heuristics ──────────────────────────────────────────────────

_HIGH_RISK_PREFIXES = (
    "SCAFFOLD_",
    "GATE_XSS_",
    "GATE_SENSITIVE_DATA_",
    "TRUTH_",
    "LICENSE_",
    "PRODUCT_NAME_",
    "GATE15B_",
    "GATE15_",
)


def _is_high_risk(code: str) -> bool:
    return any(code.startswith(p) or code.endswith("_") and p.startswith(code)
               for p in _HIGH_RISK_PREFIXES)


# ── Reporter ─────────────────────────────────────────────────────────────────


def _generate_report(
    error_codes: List[ErrorCode],
    tokens: List[FixToken],
    fix_funcs: List[Tuple[str, str]],
) -> str:
    """Generate the markdown coverage report."""
    lines: List[str] = []
    lines.append("# Fixer Coverage Report")
    lines.append("")
    lines.append("> Auto-generated by `tools/audit_fixer_coverage.py`. Do not edit manually.")
    lines.append("")

    # ── Summary stats ──
    covered = 0
    partial = 0
    uncovered = 0
    rows: List[Tuple[str, str, str, str, str]] = []
    blocker_risks: List[Tuple[str, str, str]] = []

    for ec in error_codes:
        cov, note = _check_coverage(ec.code, ec.is_dynamic, tokens)
        dyn_tag = " (prefix)" if ec.is_dynamic else ""
        rows.append((ec.code + dyn_tag, ec.gate_id, ec.severity or "-", cov, note or "-"))
        if cov == "yes":
            covered += 1
        elif cov == "partial":
            partial += 1
        else:
            uncovered += 1
            if _is_high_risk(ec.code):
                blocker_risks.append((ec.code + dyn_tag, ec.gate_id, ec.severity or "-"))

    total = len(error_codes)
    cov_pct = (covered / total * 100) if total else 0
    lines.append("## Summary")
    lines.append("")
    lines.append(f"| Metric | Count |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Total error codes | {total} |")
    lines.append(f"| Covered (yes) | {covered} |")
    lines.append(f"| Partial | {partial} |")
    lines.append(f"| Uncovered (no) | {uncovered} |")
    lines.append(f"| **Coverage %** | **{cov_pct:.1f}%** |")
    lines.append("")

    # ── Fix functions ──
    lines.append("## Fix Functions (W10)")
    lines.append("")
    lines.append("| Function | Description |")
    lines.append("|----------|-------------|")
    for name, doc in sorted(fix_funcs):
        lines.append(f"| `{name}()` | {doc or '-'} |")
    lines.append("")

    # ── Dispatch tokens ──
    lines.append("## Dispatch Tokens (apply_fix)")
    lines.append("")
    lines.append("| Token | Match Type | Fix Function |")
    lines.append("|-------|------------|--------------|")
    for tok in tokens:
        lines.append(f'| `{tok.token}` | {tok.match_type} | `{tok.fix_func}()` |')
    lines.append("")

    # ── Top blocker risks ──
    lines.append("## Top Blocker Risks (unfixed + high-risk prefix)")
    lines.append("")
    if blocker_risks:
        lines.append("| # | Error Code | Gate | Severity |")
        lines.append("|---|------------|------|----------|")
        for idx, (code, gate, sev) in enumerate(blocker_risks[:10], 1):
            lines.append(f"| {idx} | `{code}` | {gate} | {sev} |")
    else:
        lines.append("No high-risk unfixed error codes found.")
    lines.append("")

    # ── Full coverage table ──
    lines.append("## Full Coverage Table")
    lines.append("")
    lines.append("| Error Code | Gate | Severity | W10 Coverage | Notes |")
    lines.append("|------------|------|----------|:------------:|-------|")
    for code, gate, sev, cov, note in rows:
        icon = {"yes": "YES", "partial": "PARTIAL", "no": "no"}.get(cov, cov)
        lines.append(f"| `{code}` | {gate} | {sev} | {icon} | {note} |")
    lines.append("")

    return "\n".join(lines)


# ── Main ─────────────────────────────────────────────────────────────────────


def main() -> None:
    if not _GATES_DIR.is_dir():
        print(f"ERROR: Gates directory not found: {_GATES_DIR}", file=sys.stderr)
        sys.exit(1)
    if not _FIXER_PATH.is_file():
        print(f"ERROR: Fixer file not found: {_FIXER_PATH}", file=sys.stderr)
        sys.exit(1)

    print("Scanning W9 gates...")
    error_codes = _scan_w9_error_codes()
    print(f"  Found {len(error_codes)} error codes across {len(set(e.gate_id for e in error_codes))} gates")

    print("Scanning W10 fixer...")
    tokens, fix_funcs = _scan_w10_coverage()
    print(f"  Found {len(tokens)} dispatch tokens, {len(fix_funcs)} fix functions")

    print("Generating report...")
    report = _generate_report(error_codes, tokens, fix_funcs)

    _REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    _REPORT_PATH.write_text(report, encoding="utf-8")
    print(f"Report written to: {_REPORT_PATH}")


if __name__ == "__main__":
    main()
