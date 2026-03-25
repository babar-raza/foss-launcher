#!/usr/bin/env python3
"""Check that all Done taskcards have evidence files.

Usage: python scripts/check_tc_evidence.py
Returns exit code 1 if any Done TC is missing reports/TC-NNNN/evidence.md.
"""
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
TASKCARDS_DIR = REPO_ROOT / "plans" / "taskcards"
REPORTS_DIR = REPO_ROOT / "reports"

_STATUS_RE = re.compile(r"^status:\s*(.+)$", re.MULTILINE)
_ID_RE = re.compile(r"^id:\s*(TC-[\w-]+)$", re.MULTILINE)


def check_all() -> int:
    """Return number of Done TCs missing evidence."""
    missing = []
    for tc_file in sorted(TASKCARDS_DIR.glob("TC-*.md")):
        text = tc_file.read_text(encoding="utf-8")
        status_m = _STATUS_RE.search(text)
        id_m = _ID_RE.search(text)
        if not status_m or not id_m:
            continue
        status = status_m.group(1).strip().lower()
        tc_id = id_m.group(1).strip()
        if status == "done":
            evidence = REPORTS_DIR / tc_id / "evidence.md"
            if not evidence.exists():
                missing.append(tc_id)
                print(f"MISSING evidence: {tc_id} ({tc_file.name})")
    if not missing:
        print(f"OK — all Done taskcards have evidence files.")
    else:
        print(f"\n{len(missing)} Done taskcard(s) missing evidence.")
    return len(missing)


if __name__ == "__main__":
    gaps = check_all()
    sys.exit(1 if gaps else 0)
