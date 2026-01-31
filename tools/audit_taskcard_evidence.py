#!/usr/bin/env python3
"""
Audit Taskcard Evidence Completeness

Verifies that all Done taskcards have complete supporting evidence
in the reports directory structure.

Usage:
    python tools/audit_taskcard_evidence.py [--taskcard TC-XXX] [--json] [--detailed]

Exit codes:
    0 - All evidence complete
    1 - Missing or incomplete evidence found
    2 - Error during audit
"""

import sys
import re
import json
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

try:
    import yaml
except ImportError:
    print("ERROR: pyyaml required. Install with: pip install pyyaml")
    sys.exit(2)


def extract_frontmatter(content: str) -> Optional[Dict]:
    """Extract YAML frontmatter from markdown content."""
    if not content.startswith("---\n"):
        return None

    match = re.match(r"^---\n(.*?)\n---\n", content, re.DOTALL)
    if not match:
        return None

    try:
        data = yaml.safe_load(match.group(1))
        return data if isinstance(data, dict) else None
    except yaml.YAMLError as e:
        print(f"Warning: YAML parse error: {e}", file=sys.stderr)
        return None


def read_taskcard_metadata(filepath: Path) -> Optional[Dict]:
    """Read taskcard and extract metadata."""
    try:
        content = filepath.read_text(encoding="utf-8")
        frontmatter = extract_frontmatter(content)
        if frontmatter:
            frontmatter["_filename"] = filepath.name
            frontmatter["_path"] = str(filepath)
        return frontmatter
    except Exception as e:
        print(f"Warning: Failed to read {filepath.name}: {e}", file=sys.stderr)
        return None


def find_taskcards(base_path: Path) -> List[Path]:
    """Find all taskcard markdown files."""
    taskcards_dir = base_path / "plans" / "taskcards"
    if not taskcards_dir.exists():
        return []

    taskcards = []
    for md_file in taskcards_dir.glob("*.md"):
        if re.match(r"^TC-\d+.*\.md$", md_file.name):
            taskcards.append(md_file)

    return sorted(taskcards)


def find_evidence_directories(base_path: Path) -> Dict[str, Path]:
    """Find all evidence directories (reports/agents/*/TC-**)."""
    evidence_dirs = {}
    agents_dir = base_path / "reports" / "agents"

    if not agents_dir.exists():
        return evidence_dirs

    for agent_dir in agents_dir.iterdir():
        if not agent_dir.is_dir():
            continue

        for tc_dir in agent_dir.iterdir():
            if tc_dir.is_dir() and re.match(r"^TC-\d+", tc_dir.name):
                # Key: TC-XXX, Value: full path to evidence directory
                key = f"{agent_dir.name}/{tc_dir.name}"
                evidence_dirs[key] = tc_dir

    return evidence_dirs


def extract_tc_id(filename: str) -> Optional[str]:
    """Extract TC-XXX ID from taskcard filename."""
    match = re.match(r"^(TC-\d+)", filename)
    return match.group(1) if match else None


def verify_evidence(
    taskcard: Dict, base_path: Path
) -> Tuple[bool, List[str], str]:
    """
    Verify evidence completeness for a taskcard.

    Returns:
        (is_complete, missing_items, evidence_path)
    """
    tc_id = taskcard.get("id", "UNKNOWN")
    owner = taskcard.get("owner", "UNKNOWN")
    evidence_required = taskcard.get("evidence_required", [])

    # Build evidence directory path
    evidence_dir = base_path / "reports" / "agents" / owner / tc_id

    missing_items = []

    # Check if evidence directory exists
    if not evidence_dir.exists():
        missing_items.append(f"directory {tc_id}/ not found")
    else:
        # Check for report.md
        report_path = evidence_dir / "report.md"
        if not report_path.exists():
            missing_items.append("report.md")

        # Check for self_review.md
        self_review_path = evidence_dir / "self_review.md"
        if not self_review_path.exists():
            missing_items.append("self_review.md")

        # Check for additional required evidence
        for evidence_item in evidence_required:
            # Replace <agent> placeholder
            item_path = evidence_item.replace("<agent>", owner)

            # Handle relative paths
            if item_path.startswith("reports/agents/"):
                check_path = base_path / item_path
            else:
                check_path = evidence_dir / item_path

            # Skip if it's a pattern (ends with /**)
            if "/**" in item_path or item_path.endswith("/"):
                continue

            # Check file existence
            if not check_path.exists():
                # For simpler reporting, just check in evidence_dir
                simple_name = Path(item_path).name
                if not (evidence_dir / simple_name).exists():
                    missing_items.append(simple_name)

    is_complete = len(missing_items) == 0
    return is_complete, missing_items, str(evidence_dir)


def find_orphaned_evidence(
    base_path: Path, taskcard_ids: set
) -> List[Dict]:
    """Find evidence directories with no matching taskcard."""
    orphaned = []
    evidence_dirs = find_evidence_directories(base_path)

    for evidence_key, evidence_path in evidence_dirs.items():
        # Extract TC-XXX from key (agent/TC-XXX)
        tc_id = evidence_key.split("/")[1]

        if tc_id not in taskcard_ids:
            orphaned.append(
                {
                    "evidence_dir": evidence_key,
                    "taskcard_id": tc_id,
                    "full_path": str(evidence_path),
                }
            )

    return sorted(orphaned, key=lambda x: x["evidence_dir"])


def generate_report(
    done_taskcards: List[Dict],
    evidence_results: List[Dict],
    orphaned_evidence: List[Dict],
    detailed: bool = False,
) -> str:
    """Generate audit report in markdown format."""
    lines = [
        "# Taskcard Evidence Audit Report",
        "",
        "## Summary",
        "",
    ]

    total_done = len(done_taskcards)
    complete_count = sum(1 for r in evidence_results if r["is_complete"])
    incomplete_count = total_done - complete_count
    compliance_rate = (complete_count / total_done * 100) if total_done > 0 else 0

    lines.extend([
        f"- **Total Done taskcards**: {total_done}",
        f"- **Complete evidence**: {complete_count}",
        f"- **Incomplete evidence**: {incomplete_count}",
        f"- **Compliance rate**: {compliance_rate:.1f}%",
        f"- **Orphaned evidence dirs**: {len(orphaned_evidence)}",
        "",
    ])

    # Incomplete evidence section
    if incomplete_count > 0:
        lines.extend([
            "## Incomplete Evidence",
            "",
        ])

        for result in evidence_results:
            if not result["is_complete"]:
                tc_id = result["taskcard_id"]
                title = result["title"]
                missing = ", ".join(result["missing_items"])

                lines.append(f"### {tc_id}: {title}")
                lines.append(f"**Missing**: {missing}")

                if detailed:
                    lines.append(f"**Path**: `{result['evidence_path']}`")

                lines.append("")

    # Orphaned evidence section
    if orphaned_evidence:
        lines.extend([
            "## Orphaned Evidence",
            "",
            "The following evidence directories have no matching taskcard:",
            "",
        ])

        for orphan in orphaned_evidence:
            lines.append(f"- `{orphan['evidence_dir']}`")
            if detailed:
                lines.append(f"  (full path: `{orphan['full_path']}`)")

        lines.append("")

    # Summary table of all Done taskcards
    lines.extend([
        "## Detailed Results",
        "",
        "| Taskcard | Status | Owner | Missing |",
        "|---|---|---|---|",
    ])

    for result in sorted(evidence_results, key=lambda x: x["taskcard_id"]):
        tc_id = result["taskcard_id"]
        status = "[OK] Complete" if result["is_complete"] else "[FAIL] Incomplete"
        owner = result["owner"]
        missing = ", ".join(result["missing_items"]) if result["missing_items"] else "-"

        lines.append(f"| {tc_id} | {status} | {owner} | {missing} |")

    lines.append("")
    return "\n".join(lines)


def audit_taskcards(
    base_path: Path,
    filter_taskcard: Optional[str] = None,
) -> Tuple[int, List[Dict], List[Dict], List[Dict]]:
    """
    Audit taskcard evidence.

    Returns:
        (exit_code, done_taskcards, evidence_results, orphaned_evidence)
    """
    # Find all taskcards
    taskcards_paths = find_taskcards(base_path)
    if not taskcards_paths:
        print("ERROR: No taskcards found", file=sys.stderr)
        return 2, [], [], []

    # Read metadata
    all_taskcards = []
    done_taskcards = []
    all_tc_ids = set()

    for tc_path in taskcards_paths:
        metadata = read_taskcard_metadata(tc_path)
        if metadata:
            all_taskcards.append(metadata)
            tc_id = metadata.get("id")
            if tc_id:
                all_tc_ids.add(tc_id)

            # Filter to Done status
            if metadata.get("status") == "Done":
                # Apply filter if specified
                if filter_taskcard is None or tc_id == filter_taskcard:
                    done_taskcards.append(metadata)

    if not all_taskcards:
        print("ERROR: No valid taskcard metadata found", file=sys.stderr)
        return 2, [], [], []

    # Verify evidence for Done taskcards
    evidence_results = []
    has_issues = False

    for taskcard in done_taskcards:
        is_complete, missing_items, evidence_path = verify_evidence(taskcard, base_path)

        evidence_results.append({
            "taskcard_id": taskcard.get("id"),
            "title": taskcard.get("title", ""),
            "owner": taskcard.get("owner", ""),
            "is_complete": is_complete,
            "missing_items": missing_items,
            "evidence_path": evidence_path,
        })

        if not is_complete:
            has_issues = True

    # Find orphaned evidence
    orphaned_evidence = find_orphaned_evidence(base_path, all_tc_ids)
    if orphaned_evidence:
        has_issues = True

    # Determine exit code
    exit_code = 1 if has_issues else 0

    return exit_code, done_taskcards, evidence_results, orphaned_evidence


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Audit taskcard evidence completeness",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exit codes:
  0 - All evidence complete
  1 - Missing or incomplete evidence found
  2 - Error during audit

Examples:
  python tools/audit_taskcard_evidence.py
  python tools/audit_taskcard_evidence.py --taskcard TC-500
  python tools/audit_taskcard_evidence.py --json --detailed
        """,
    )

    parser.add_argument(
        "--taskcard",
        type=str,
        default=None,
        help="Audit specific taskcard only (e.g., TC-500)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )
    parser.add_argument(
        "--detailed",
        action="store_true",
        help="Show detailed paths for all checks",
    )
    parser.add_argument(
        "--ignore-orphaned",
        action="store_true",
        help="Don't report orphaned evidence directories",
    )

    args = parser.parse_args()

    # Determine repo root
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent

    # Run audit
    exit_code, done_taskcards, evidence_results, orphaned_evidence = audit_taskcards(
        repo_root,
        filter_taskcard=args.taskcard,
    )

    # Generate output
    if args.json:
        # JSON output
        output = {
            "audit_summary": {
                "total_done": len(done_taskcards),
                "complete": sum(1 for r in evidence_results if r["is_complete"]),
                "incomplete": sum(1 for r in evidence_results if not r["is_complete"]),
                "orphaned": len(orphaned_evidence),
            },
            "evidence_results": evidence_results,
            "orphaned_evidence": orphaned_evidence if not args.ignore_orphaned else [],
            "exit_code": exit_code,
        }
        print(json.dumps(output, indent=2))
    else:
        # Markdown report
        if args.ignore_orphaned:
            orphaned_evidence = []

        report = generate_report(
            done_taskcards,
            evidence_results,
            orphaned_evidence,
            detailed=args.detailed,
        )
        print(report)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
