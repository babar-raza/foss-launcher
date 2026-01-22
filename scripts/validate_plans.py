from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
PLANS_DIR = REPO_ROOT / "plans"
TASKCARDS_DIR = PLANS_DIR / "taskcards"

TASKCARD_FILE_RE = re.compile(r"^(TC-\d{3})_.+\.md$")
TASKCARD_H1_RE = re.compile(r"^#\s*Taskcard\s+(TC-\d{3})\s+—", re.MULTILINE)

# These headings are treated as required in Phase 1.
REQUIRED_HEADINGS = [
    "## Objective",
    "## Required spec references",
    "## Scope",
    "## Inputs",
    "## Outputs",
    "## Allowed paths",
    "## Implementation steps",
    "## Deliverables",
    "## Acceptance checks",
    "## Self-review",
]



@dataclass(frozen=True)
class Finding:
    level: str  # "ERROR" | "WARN"
    where: str
    message: str


def _iter_taskcard_paths() -> Iterable[Path]:
    for p in sorted(TASKCARDS_DIR.glob("TC-*.md")):
        if p.is_file():
            yield p


def _extract_required_refs(md_text: str) -> list[str]:
    """
    Extract bullet lines from the '## Required spec references' section.
    Accepts lines like:
      - specs/01_system_contract.md
      - specs/schemas/*.schema.json
      - docs/reference/local-telemetry.md (reference)
    """
    start = md_text.find("## Required spec references")
    if start < 0:
        return []
    rest = md_text[start:]
    # find next top-level section after the header line itself
    m = re.search(r"\n##\s+", rest[len("## Required spec references"):])
    section = rest if not m else rest[: len("## Required spec references") + m.start()]
    refs: list[str] = []
    for line in section.splitlines():
        line = line.strip()
        if line.startswith("- "):
            refs.append(line[2:].strip())
    return refs


def _normalize_ref(raw: str) -> str:
    # Strip trailing inline notes like "(reference)" while preserving globs.
    if " (" in raw:
        raw = raw.split(" (", 1)[0].strip()
    return raw.strip().strip("`")


def _resolve_ref_glob(path_expr: str) -> list[Path]:
    # Treat as repo-relative unless it's already absolute (should not be).
    if "://" in path_expr:
        return []
    if path_expr.startswith("/"):
        p = Path(path_expr)
        return [p] if p.exists() else []
    # Glob patterns
    if any(ch in path_expr for ch in ["*", "?", "[", "]"]):
        return list(REPO_ROOT.glob(path_expr))
    p = REPO_ROOT / path_expr
    return [p] if p.exists() else []


def validate_taskcards() -> list[Finding]:
    findings: list[Finding] = []

    if not TASKCARDS_DIR.exists():
        return [Finding("ERROR", str(TASKCARDS_DIR), "plans/taskcards directory missing")]

    # Validate INDEX.md coverage
    index_path = TASKCARDS_DIR / "INDEX.md"
    if index_path.exists():
        idx_text = index_path.read_text(encoding="utf-8")
        idx_ids = set(re.findall(r"\b(TC-\d{3})\b", idx_text))
    else:
        idx_ids = set()
        findings.append(Finding("ERROR", str(index_path), "Missing plans/taskcards/INDEX.md"))

    actual_ids: set[str] = set()

    for path in _iter_taskcard_paths():
        md = path.read_text(encoding="utf-8", errors="replace")

        mfile = TASKCARD_FILE_RE.match(path.name)
        if not mfile:
            findings.append(Finding("ERROR", str(path), "Filename must match TC-XXX_<slug>.md"))
            continue
        file_id = mfile.group(1)
        actual_ids.add(file_id)

        mh1 = TASKCARD_H1_RE.search(md)
        if not mh1:
            findings.append(Finding("ERROR", str(path), "Missing H1 header '# Taskcard TC-XXX — ...'"))
        else:
            h1_id = mh1.group(1)
            if h1_id != file_id:
                findings.append(Finding("ERROR", str(path), f"Task ID mismatch: filename has {file_id} but H1 has {h1_id}"))

        for heading in REQUIRED_HEADINGS:
            if heading not in md:
                findings.append(Finding("ERROR", str(path), f"Missing required section: {heading}"))

        refs = [_normalize_ref(r) for r in _extract_required_refs(md)]
        if not refs:
            findings.append(Finding("ERROR", str(path), "No entries under '## Required spec references'"))
        for ref in refs:
            matches = _resolve_ref_glob(ref)
            if not matches:
                findings.append(Finding("ERROR", str(path), f"Broken spec reference: '{ref}' not found"))

    # Cross-check INDEX vs actual
    missing_in_index = sorted(actual_ids - idx_ids)
    extra_in_index = sorted(idx_ids - actual_ids)
    for tid in missing_in_index:
        findings.append(Finding("WARN", str(index_path), f"{tid} is present as a file but missing from INDEX.md"))
    for tid in extra_in_index:
        findings.append(Finding("WARN", str(index_path), f"{tid} is listed in INDEX.md but no file exists"))

    return findings


def main() -> int:
    findings = validate_taskcards()
    errors = [f for f in findings if f.level == "ERROR"]
    warns = [f for f in findings if f.level == "WARN"]

    if errors:
        print("PLANS VALIDATION FAILED")
        for f in errors:
            print(f"- {f.where}: {f.message}")
        if warns:
            print("\nWARNINGS")
            for f in warns:
                print(f"- {f.where}: {f.message}")
        return 2

    print("PLANS VALIDATION OK")
    if warns:
        print("\nWARNINGS")
        for f in warns:
            print(f"- {f.where}: {f.message}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
