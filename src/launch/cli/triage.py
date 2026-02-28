"""Operator triage for validation reports.

Reads a validation_report.json and produces:
1. A summary of the run (state, profile, gate counts, severity breakdown)
2. A ranked list of top issues
3. Deterministic recommended next-action commands

TC-2900: Operator triage CLI command.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

_logger = logging.getLogger(__name__)

from rich.console import Console
from rich.table import Table


# ── Severity ordering (highest first) ──────────────────────────────────────
_SEVERITY_RANK: Dict[str, int] = {
    "blocker": 0,
    "error": 1,
    "warn": 2,
    "info": 3,
}


# ── Data loading ───────────────────────────────────────────────────────────

def load_validation_report(run_dir: Path) -> Dict[str, Any]:
    """Load and return the parsed validation_report.json.

    TC-3580: Prefers the W9 41-gate report (validation_report.json).
    Falls back to the site-level report (validation_report.site.json) with a
    loud warning when only the latter is present.

    Raises:
        FileNotFoundError: If neither report file exists.
    """
    report_path = run_dir / "artifacts" / "validation_report.json"
    if report_path.exists():
        with open(report_path, encoding="utf-8") as f:
            return json.load(f)
    # TC-3580: fallback — `launch validate` writes to .site.json; W9 may not have run
    site_path = run_dir / "artifacts" / "validation_report.site.json"
    if site_path.exists():
        _logger.warning(
            "[Triage] W9 validation_report.json not found; falling back to "
            "validation_report.site.json (13-gate site report). "
            "Run W9 for full 41-gate coverage."
        )
        with open(site_path, encoding="utf-8") as f:
            return json.load(f)
    raise FileNotFoundError(
        f"validation_report.json not found at {report_path}"
    )


def load_snapshot(run_dir: Path) -> Optional[Dict[str, Any]]:
    """Load snapshot.json if it exists, else return None."""
    snapshot_path = run_dir / "snapshot.json"
    if not snapshot_path.exists():
        return None
    try:
        with open(snapshot_path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


# ── Summary ────────────────────────────────────────────────────────────────

def build_summary(
    run_id: str,
    report: Dict[str, Any],
    snapshot: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build a summary dict from the validation report and optional snapshot."""
    gates = report.get("gates", [])
    issues = report.get("issues", [])

    severity_counts: Dict[str, int] = {
        "blocker": 0,
        "error": 0,
        "warn": 0,
        "info": 0,
    }
    for issue in issues:
        sev = issue.get("severity", "info")
        if sev in severity_counts:
            severity_counts[sev] += 1

    return {
        "run_id": run_id,
        "run_state": snapshot.get("run_state") if snapshot else None,
        "profile": report.get("profile", "unknown"),
        "total_gates": len(gates),
        "failed_gates": sum(1 for g in gates if not g.get("ok", True)),
        "severity_counts": severity_counts,
    }


# ── Issue ranking ──────────────────────────────────────────────────────────

def rank_issues(
    report: Dict[str, Any],
    top_n: int = 10,
) -> List[Dict[str, Any]]:
    """Return the top issues ranked by severity.

    Always includes all blockers and errors.  If that count is less than
    *top_n*, pads with warnings (then infos) up to *top_n*.
    """
    issues = report.get("issues", [])

    # Separate by severity class
    critical: List[Dict[str, Any]] = []
    rest: List[Dict[str, Any]] = []
    for issue in issues:
        sev = issue.get("severity", "info")
        if sev in ("blocker", "error"):
            critical.append(issue)
        else:
            rest.append(issue)

    # Sort each bucket by severity rank, then gate, then path
    def _sort_key(iss: Dict[str, Any]) -> tuple:
        loc = iss.get("location") or {}
        return (
            _SEVERITY_RANK.get(iss.get("severity", "info"), 99),
            iss.get("gate", ""),
            loc.get("path", ""),
            loc.get("line", 0),
        )

    critical.sort(key=_sort_key)
    rest.sort(key=_sort_key)

    # Always show all critical; pad with rest up to top_n
    result = list(critical)
    needed = max(0, top_n - len(result))
    result.extend(rest[:needed])
    return result


# ── Recommendation engine ──────────────────────────────────────────────────


def _gate_failed(gate_id: str, gates: List[Dict[str, Any]]) -> bool:
    """Check whether a specific gate failed."""
    for g in gates:
        if g.get("name") == gate_id and not g.get("ok", True):
            return True
    return False


def _match_truth(issue: Dict[str, Any], gates: List[Dict[str, Any]]) -> bool:
    return (
        _gate_failed("gate_truth_layer_completeness", gates)
        or _gate_failed("gate_truth_facts_completeness", gates)
    )


def _match_code_fence(issue: Dict[str, Any], gates: List[Dict[str, Any]]) -> bool:
    return (
        issue.get("gate", "") == "gate_15b_code_fence_api"
        or _gate_failed("gate_15b_code_fence_api", gates)
    )


def _match_scaffold_or_fmt(issue: Dict[str, Any], gates: List[Dict[str, Any]]) -> bool:
    return (
        issue.get("gate", "") == "gate_scaffold_leak"
        or _gate_failed("gate_scaffold_leak", gates)
        or (issue.get("error_code") or "").startswith("FQ-")
        or (issue.get("error_code") or "").startswith("G17-")
        or (issue.get("error_code") or "").startswith("SCAFFOLD")
    )


def _match_kb_howto(issue: Dict[str, Any], gates: List[Dict[str, Any]]) -> bool:
    return (
        issue.get("gate", "").startswith("gate_kb_howto")
        or (issue.get("error_code") or "").startswith("GATE_KB_HOWTO_")
    )


def _match_g20(issue: Dict[str, Any], gates: List[Dict[str, Any]]) -> bool:
    return (
        issue.get("gate", "") == "gate_20_cross_page_consistency"
        or (issue.get("error_code") or "").startswith("G20-")
    )


def _match_link_patch(issue: Dict[str, Any], gates: List[Dict[str, Any]]) -> bool:
    return (
        "link" in issue.get("gate", "").lower()
        or "patch" in issue.get("gate", "").lower()
    )


# Rules checked in priority order; first match per worker wins.
_RECOMMENDATION_RULES: List[Dict[str, Any]] = [
    {
        "label": "Truth layer artifacts missing or incomplete",
        "worker": "W2",
        "match": _match_truth,
    },
    {
        "label": "Hallucinated API symbols in code fences",
        "worker": "W5",
        "match": _match_code_fence,
    },
    {
        "label": "Scaffold/prompt leak or formatting issues (W10 auto-fixable)",
        "worker": "W10",
        "match": _match_scaffold_or_fmt,
    },
    {
        "label": "KB how-to structure or evidence issues (W10 auto-fixable)",
        "worker": "W10",
        "match": _match_kb_howto,
    },
    {
        "label": "Cross-page consistency issues (version/package, W10 auto-fixable)",
        "worker": "W10",
        "match": _match_g20,
    },
    {
        "label": "Cross-page link or patch issues",
        "worker": "W8",
        "match": _match_link_patch,
    },
]


def recommend_action(
    run_dir: Path,
    report: Dict[str, Any],
) -> List[Dict[str, str]]:
    """Return a list of recommended resume commands with rationale.

    Each entry: {"command": "launch resume ...", "reason": "..."}
    Returns at most one recommendation per worker, ordered by priority.
    """
    gates = report.get("gates", [])
    issues = report.get("issues", [])
    run_dir_str = str(run_dir).replace("\\", "/")

    seen_workers: set = set()
    recommendations: List[Dict[str, str]] = []

    for rule in _RECOMMENDATION_RULES:
        if rule["worker"] in seen_workers:
            continue
        matched = False
        for issue in issues:
            if rule["match"](issue, gates):
                matched = True
                break
        # Also fire on gate-only checks (no issues needed for truth layer)
        if not matched:
            matched = rule["match"]({}, gates)
        if matched:
            seen_workers.add(rule["worker"])
            recommendations.append({
                "command": (
                    f"launch resume --run-dir {run_dir_str} "
                    f"--from-worker {rule['worker']}"
                ),
                "reason": rule["label"],
            })

    # Fallback: if no specific recommendation, suggest W9 re-validation
    if not recommendations:
        recommendations.append({
            "command": f"launch resume --run-dir {run_dir_str} --from-worker W9",
            "reason": "General re-validation (no specific fixable pattern detected)",
        })

    return recommendations


# ── Rich output ────────────────────────────────────────────────────────────

_SEVERITY_STYLE: Dict[str, str] = {
    "blocker": "bold red",
    "error": "red",
    "warn": "yellow",
    "info": "dim",
}


def print_triage(
    console: Console,
    summary: Dict[str, Any],
    top_issues: List[Dict[str, Any]],
    recommendations: List[Dict[str, str]],
) -> None:
    """Print the three triage sections using Rich formatting."""

    # ── Section A: Summary ─────────────────────────────────────────────
    console.print("\n[bold blue]== Triage Summary ==[/bold blue]\n")
    console.print(f"  Run ID:        {summary['run_id']}")
    if summary.get("run_state"):
        console.print(f"  Run state:     [bold]{summary['run_state']}[/bold]")
    console.print(f"  Profile:       {summary['profile']}")
    console.print(
        f"  Gates:         {summary['total_gates']} total, "
        f"[red]{summary['failed_gates']} failed[/red]"
    )

    sev = summary["severity_counts"]
    console.print(
        f"  Issues:        "
        f"[bold red]{sev['blocker']}[/bold red] blocker, "
        f"[red]{sev['error']}[/red] error, "
        f"[yellow]{sev['warn']}[/yellow] warn, "
        f"[dim]{sev['info']}[/dim] info"
    )

    # ── Section B: Top Issues ──────────────────────────────────────────
    if top_issues:
        console.print("\n[bold blue]== Top Issues ==[/bold blue]\n")
        table = Table(show_header=True, header_style="bold blue")
        table.add_column("Sev", width=8)
        table.add_column("Gate")
        table.add_column("Code", width=14)
        table.add_column("Path")
        table.add_column("Line", width=5, justify="right")
        table.add_column("Message", max_width=60)

        for issue in top_issues:
            sev_val = issue.get("severity", "info")
            style = _SEVERITY_STYLE.get(sev_val, "")
            loc = issue.get("location") or {}
            # Sanitize message for Windows console (cp1252 can't encode some Unicode)
            msg = issue.get("message", "")[:60]
            msg = msg.encode("ascii", errors="replace").decode("ascii")
            table.add_row(
                f"[{style}]{sev_val}[/{style}]",
                issue.get("gate", ""),
                issue.get("error_code", ""),
                loc.get("path", ""),
                str(loc.get("line", "")) if loc.get("line") else "",
                msg,
            )
        console.print(table)
    else:
        console.print("\n[green]No issues found.[/green]")

    # ── Section C: Recommended Next Step ───────────────────────────────
    console.print("\n[bold blue]== Recommended Next Step ==[/bold blue]\n")
    for i, rec in enumerate(recommendations, 1):
        console.print(f"  {i}. [bold]{rec['reason']}[/bold]")
        console.print(f"     [green]{rec['command']}[/green]\n")
