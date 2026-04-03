#!/usr/bin/env python3
"""Diagnostic: audit clone cache health across all pipeline runs.

Reads all events.ndjson files under runs/ and checks:
  - Whether all active cache dirs use the correct brand prefix (aspose_*)
  - Whether any po_* dirs remain in either active cache
  - Per-slug transition history (first correct fresh clone, hit counts)
  - Stale entries older than _STALE_CACHE_DAYS in both caches

Exit 0: no structural anomalies (po_* dirs or missing .clone_timestamp markers).
Exit 1: structural anomalies found. Stale entries (age > _STALE_CACHE_DAYS) are
        reported as warnings but do NOT cause exit 1 — they are expected operational state.

Usage:
  python scripts/audit_clone_cache.py
  python scripts/audit_clone_cache.py --json
  python scripts/audit_clone_cache.py --runs-dir /path/to/runs
  python scripts/audit_clone_cache.py --stale-only
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Load _STALE_CACHE_DAYS and _CLONE_TIMESTAMP_MARKER from acquisition.py
# without importing the full package (avoids requests, heavy deps).
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parent.parent
_ACQ_PATH = _REPO_ROOT / "src" / "launcher" / "workers" / "intake" / "acquisition.py"

_STALE_CACHE_DAYS: int = 7
_CLONE_TIMESTAMP_MARKER: str = ".clone_timestamp"

if _ACQ_PATH.exists():
    _spec = importlib.util.spec_from_file_location("_acq_local", _ACQ_PATH)
    if _spec and _spec.loader:
        _acq = importlib.util.module_from_spec(_spec)
        sys.modules["_acq_local"] = _acq
        try:
            _spec.loader.exec_module(_acq)  # type: ignore[union-attr]
            _STALE_CACHE_DAYS = getattr(_acq, "_STALE_CACHE_DAYS", 7)
            _CLONE_TIMESTAMP_MARKER = getattr(_acq, "_CLONE_TIMESTAMP_MARKER", ".clone_timestamp")
        except Exception:
            pass  # fall back to hardcoded defaults


# ---------------------------------------------------------------------------
# Core audit logic
# ---------------------------------------------------------------------------

def _read_clone_events(runs_dir: Path) -> list[dict]:
    """Return all clone_completed events from all runs."""
    events: list[dict] = []
    if not runs_dir.is_dir():
        return events
    for run_path in sorted(runs_dir.iterdir()):
        if not run_path.is_dir():
            continue
        ev_file = run_path / "events.ndjson"
        if not ev_file.exists():
            continue
        try:
            with ev_file.open(encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        ev = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if ev.get("event_type") == "clone_completed":
                        d = ev.get("data", {})
                        repo_dir = d.get("repo_dir", "")
                        slug = Path(repo_dir.replace("\\", "/")).name
                        events.append({
                            "run_id": run_path.name,
                            "ts": ev.get("timestamp", ""),
                            "fresh": d.get("fresh"),
                            "slug": slug,
                            "sha": d.get("repo_sha", "")[:12],
                        })
                        break  # one clone_completed per run
        except OSError as exc:
            print(f"[WARN] Could not read {ev_file}: {exc}", file=sys.stderr)
    return events


def _check_cache_dirs(cache_dir: Path, now: datetime) -> dict:
    """Inspect a cache root for po_* entries and stale dirs."""
    result: dict = {"po_entries": [], "stale_entries": [], "valid_entries": []}
    if not cache_dir.is_dir():
        return result
    for entry in sorted(cache_dir.iterdir()):
        if not entry.is_dir():
            continue
        slug = entry.name
        if slug.startswith("po_"):
            result["po_entries"].append(slug)
        ts_file = entry / _CLONE_TIMESTAMP_MARKER
        if ts_file.exists():
            try:
                ts = datetime.fromisoformat(ts_file.read_text().strip())
                age_days = (now - ts).total_seconds() / 86400
                if age_days > _STALE_CACHE_DAYS:
                    result["stale_entries"].append({"slug": slug, "age_days": round(age_days, 1)})
                else:
                    result["valid_entries"].append({"slug": slug, "age_days": round(age_days, 1)})
            except (ValueError, OSError):
                result["stale_entries"].append({"slug": slug, "age_days": None})
        else:
            # No timestamp marker — incomplete / corrupt entry
            result["stale_entries"].append({"slug": slug, "age_days": None, "note": "missing .clone_timestamp"})
    return result


def _build_slug_summary(events: list[dict]) -> dict:
    """Per-slug: first_aspose_fresh, #aspose_fresh, #po_hits, last_state."""
    first_aspose_fresh: dict[str, str] = {}
    aspose_fresh_count: dict[str, int] = defaultdict(int)
    po_hit_count: dict[str, int] = defaultdict(int)
    last_state: dict[str, dict] = {}

    for ev in events:
        slug = ev["slug"]
        if not slug:
            continue
        last_state[slug] = ev
        if slug.startswith("aspose_") and ev.get("fresh"):
            aspose_fresh_count[slug] += 1
            if slug not in first_aspose_fresh:
                first_aspose_fresh[slug] = ev["ts"][:16]
        elif slug.startswith("po_") and not ev.get("fresh"):
            po_hit_count[slug] += 1

    return {
        "slugs": sorted(last_state.keys()),
        "first_aspose_fresh": first_aspose_fresh,
        "aspose_fresh_count": dict(aspose_fresh_count),
        "po_hit_count": dict(po_hit_count),
        "last_state": last_state,
    }


def run_audit(runs_dir: Path, intake_cache: Path, stale_only: bool = False) -> dict:
    """Full audit — returns structured result dict."""
    now = datetime.now(tz=timezone.utc)
    events = _read_clone_events(runs_dir)
    summary = _build_slug_summary(events)
    runs_cache = runs_dir / ".clone_cache"
    runs_cache_check = _check_cache_dirs(runs_cache, now)
    intake_cache_check = _check_cache_dirs(intake_cache, now)

    # Anomalies = structural corruption only (wrong prefix or missing timestamp marker).
    # Stale entries (age > _STALE_CACHE_DAYS) are operational WARNINGs, not anomalies.
    anomalies: list[str] = []
    if runs_cache_check["po_entries"]:
        anomalies.append(f"po_* dirs in runs/.clone_cache: {runs_cache_check['po_entries']}")
    if intake_cache_check["po_entries"]:
        anomalies.append(f"po_* dirs in intake/.clone_cache: {intake_cache_check['po_entries']}")
    # Missing .clone_timestamp = incomplete/corrupt clone — treat as structural anomaly
    missing_ts_runs = [e["slug"] for e in runs_cache_check["stale_entries"] if e.get("age_days") is None]
    missing_ts_intake = [e["slug"] for e in intake_cache_check["stale_entries"] if e.get("age_days") is None]
    if missing_ts_runs:
        anomalies.append(f"missing .clone_timestamp in runs/.clone_cache: {missing_ts_runs}")
    if missing_ts_intake:
        anomalies.append(f"missing .clone_timestamp in intake/.clone_cache: {missing_ts_intake}")

    return {
        "runs_dir": str(runs_dir),
        "intake_cache_dir": str(intake_cache),
        "total_events": len(events),
        "slug_summary": summary,
        "runs_cache": runs_cache_check,
        "intake_cache": intake_cache_check,
        "anomalies": anomalies,
        "clean": len(anomalies) == 0,
    }


def _print_table(result: dict, stale_only: bool) -> None:
    summary = result["slug_summary"]
    if not stale_only:
        print(f"\nTotal clone events scanned: {result['total_events']}")
        print()
        hdr = f"{'Slug':<28} {'First aspose fresh':<22} {'#aspose':>7} {'#po_hits':>9}  Last state"
        print(hdr)
        print("-" * 90)
        for slug in summary["slugs"]:
            ls = summary["last_state"][slug]
            first_cf = summary["first_aspose_fresh"].get(slug, "never")
            n_fresh = summary["aspose_fresh_count"].get(slug, 0)
            n_po = summary["po_hit_count"].get(slug, 0)
            print(
                f"{slug:<28} {first_cf:<22} {n_fresh:>7} {n_po:>9}  "
                f"fresh={ls['fresh']} @ {ls['ts'][:16]}"
            )

    # Cache dir status
    for label, check in [
        ("runs/.clone_cache", result["runs_cache"]),
        ("intake/.clone_cache", result["intake_cache"]),
    ]:
        print(f"\n{label}:")
        if check["po_entries"]:
            print(f"  [WARN] po_* entries: {check['po_entries']}")
        if check["stale_entries"]:
            for e in check["stale_entries"]:
                note = e.get("note", "")
                age = f"{e['age_days']}d" if e.get("age_days") is not None else "no-timestamp"
                print(f"  [WARN] stale: {e['slug']} ({age}){' - ' + note if note else ''}")
        if not check["po_entries"] and not check["stale_entries"]:
            valid = len(check["valid_entries"])
            print(f"  [OK] {valid} valid entries, none stale")

    print()
    if result["anomalies"]:
        print(f"ANOMALIES ({len(result['anomalies'])}):")
        for a in result["anomalies"]:
            print(f"  * {a}")
    else:
        print("[OK] No anomalies -- cache health OK")


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit clone cache health.")
    parser.add_argument(
        "--runs-dir",
        default=str(_REPO_ROOT / "runs"),
        help="Path to runs directory (default: runs/)",
    )
    parser.add_argument(
        "--intake-dir",
        default=str(_REPO_ROOT / "intake" / ".clone_cache"),
        help="Path to intake/.clone_cache directory",
    )
    parser.add_argument(
        "--json",
        dest="json_output",
        action="store_true",
        help="Output machine-readable JSON",
    )
    parser.add_argument(
        "--stale-only",
        action="store_true",
        help="Only show stale/anomalous cache entries",
    )
    args = parser.parse_args()

    result = run_audit(
        runs_dir=Path(args.runs_dir),
        intake_cache=Path(args.intake_dir),
        stale_only=args.stale_only,
    )

    if args.json_output:
        print(json.dumps(result, indent=2, default=str))
    else:
        _print_table(result, stale_only=args.stale_only)

    return 0 if result["clean"] else 1


if __name__ == "__main__":
    sys.exit(main())
