#!/usr/bin/env python3
"""
Allowed Paths Overlap Auditor

Analyzes all taskcard allowed_paths to identify overlaps and verify
single-writer enforcement for shared libraries.
"""

import sys
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict
import yaml


# Shared library directories (single-writer enforcement required)
SHARED_LIBS = {
    "src/launch/io/**": "TC-200",
    "src/launch/util/**": "TC-200",
    "src/launch/models/**": "TC-250",
    "src/launch/clients/**": "TC-500",
}


def extract_frontmatter(content: str) -> Dict | None:
    """Extract YAML frontmatter from markdown content."""
    if not content.startswith("---\n"):
        return None

    match = re.match(r"^---\n(.*?)\n---\n", content, re.DOTALL)
    if not match:
        return None

    try:
        return yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        return None


def find_taskcards(repo_root: Path) -> List[Path]:
    """Find all taskcard markdown files."""
    taskcards_dir = repo_root / "plans" / "taskcards"
    if not taskcards_dir.exists():
        return []

    taskcards = []
    for md_file in taskcards_dir.glob("*.md"):
        if re.match(r"^TC-\d+.*\.md$", md_file.name):
            taskcards.append(md_file)

    return sorted(taskcards)


def normalize_path_pattern(pattern: str) -> str:
    """Normalize a path pattern for comparison."""
    return pattern.strip().replace("\\", "/")


def patterns_overlap(pattern1: str, pattern2: str) -> bool:
    """
    Check if two path patterns might overlap.
    Simplified check: exact match or one is prefix of other.
    """
    p1 = normalize_path_pattern(pattern1).rstrip("*")
    p2 = normalize_path_pattern(pattern2).rstrip("*")

    return p1.startswith(p2) or p2.startswith(p1)


def check_shared_lib_violations(
    tc_id: str, allowed_paths: List[str]
) -> List[Tuple[str, str]]:
    """
    Check if a taskcard's allowed_paths violate single-writer rules.
    Returns list of (path_pattern, owner_tc) violations.
    """
    violations = []

    for path in allowed_paths:
        normalized = normalize_path_pattern(path)
        for shared_lib, owner in SHARED_LIBS.items():
            if tc_id != owner and patterns_overlap(normalized, shared_lib):
                violations.append((path, owner))

    return violations


def is_critical_path(path: str) -> bool:
    """
    Check if a path is critical (src/** or repo-root file).
    These paths must NOT have overlaps (zero tolerance).
    """
    normalized = normalize_path_pattern(path)

    # Repo-root files (exact matches)
    root_files = ["README.md", "Makefile", "pyproject.toml", ".gitignore"]
    if normalized in root_files:
        return True

    # src/** paths (any file under src/)
    if normalized.startswith("src/") or normalized == "src/**":
        return True

    return False


def check_critical_overlaps(overlaps: Dict[str, List[str]]) -> Dict[str, List[str]]:
    """
    Filter overlaps to find critical path overlaps that MUST be fixed.
    Returns dict of {path: [tc_ids]} for critical overlaps only.
    """
    critical_overlaps = {}

    for path, tc_list in overlaps.items():
        if is_critical_path(path):
            critical_overlaps[path] = tc_list

    return critical_overlaps


def analyze_overlap(taskcards_data: List[Dict]) -> Dict:
    """
    Analyze path overlaps between all taskcards.
    Returns dict with overlap statistics and violations.
    """
    # Build path-to-taskcards mapping
    path_usage = defaultdict(list)

    for tc_data in taskcards_data:
        tc_id = tc_data.get("id", "UNKNOWN")
        allowed_paths = tc_data.get("allowed_paths", [])

        for path in allowed_paths:
            normalized = normalize_path_pattern(path)
            path_usage[normalized].append(tc_id)

    # Find overlaps
    overlaps = {}
    for path, tc_list in path_usage.items():
        if len(tc_list) > 1:
            overlaps[path] = tc_list

    # Find critical overlaps (zero tolerance)
    critical_overlaps = check_critical_overlaps(overlaps)

    # Check shared lib violations
    violations = {}
    for tc_data in taskcards_data:
        tc_id = tc_data.get("id", "UNKNOWN")
        allowed_paths = tc_data.get("allowed_paths", [])
        tc_violations = check_shared_lib_violations(tc_id, allowed_paths)
        if tc_violations:
            violations[tc_id] = tc_violations

    return {
        "path_usage": dict(path_usage),
        "overlaps": overlaps,
        "critical_overlaps": critical_overlaps,
        "shared_lib_violations": violations,
        "total_paths": len(path_usage),
        "overlapping_paths": len(overlaps),
        "critical_overlapping_paths": len(critical_overlaps),
    }


def generate_report(analysis: Dict, output_path: Path):
    """Generate markdown audit report."""
    lines = [
        "# Allowed Paths Overlap Audit Report",
        "",
        f"**Generated**: 2026-01-22",
        "",
        "## Summary",
        "",
        f"- **Total unique path patterns**: {analysis['total_paths']}",
        f"- **Overlapping path patterns**: {analysis['overlapping_paths']}",
        f"- **Shared library violations**: {len(analysis['shared_lib_violations'])}",
        "",
        "## Shared Library Single-Writer Enforcement",
        "",
        "The following directories require single-writer governance:",
        "",
    ]

    for lib, owner in SHARED_LIBS.items():
        lines.append(f"- `{lib}` - Owner: {owner}")

    lines.extend([
        "",
        "## Shared Library Violations",
        "",
    ])

    if not analysis["shared_lib_violations"]:
        lines.append("✓ **No violations found** - All taskcards respect single-writer rules")
    else:
        lines.append(
            f"⚠️ **{len(analysis['shared_lib_violations'])} taskcard(s) violate single-writer rules**:"
        )
        lines.append("")

        for tc_id, violations in sorted(analysis["shared_lib_violations"].items()):
            lines.append(f"### {tc_id}")
            lines.append("")
            for path, owner in violations:
                lines.append(f"- Path `{path}` overlaps with shared lib owned by {owner}")
            lines.append("")

        lines.extend([
            "**Required action**: Update the above taskcards to remove shared lib paths",
            "from their `allowed_paths` unless they are the designated owner.",
            "",
        ])

    lines.extend([
        "## Critical Path Overlap Analysis (Zero Tolerance)",
        "",
    ])

    if not analysis["critical_overlaps"]:
        lines.append("✓ **No critical overlaps** - All src/** and repo-root files have single ownership")
    else:
        lines.append(
            f"❌ **{len(analysis['critical_overlaps'])} CRITICAL overlap(s) found** - MUST BE FIXED:"
        )
        lines.append("")

        for path, tc_list in sorted(analysis["critical_overlaps"].items()):
            lines.append(f"### `{path}`")
            lines.append("")
            lines.append(f"Used by: {', '.join(sorted(tc_list))}")
            lines.append("")

        lines.extend([
            "**Required action**: Remove critical overlaps immediately.",
            "Critical paths (zero tolerance for overlaps):",
            "- All `src/**` paths",
            "- Repo-root files: README.md, Makefile, pyproject.toml, .gitignore",
            "",
        ])

    lines.extend([
        "## All Path Overlaps (Including Non-Critical)",
        "",
    ])

    if not analysis["overlaps"]:
        lines.append("✓ **No overlapping paths** - All taskcards have isolated allowed_paths")
    else:
        lines.append(
            f"ℹ️ **{len(analysis['overlaps'])} path pattern(s) used by multiple taskcards**:"
        )
        lines.append("")

        for path, tc_list in sorted(analysis["overlaps"].items()):
            is_critical = is_critical_path(path)
            status = "❌ CRITICAL" if is_critical else "ℹ️ Non-critical"
            lines.append(f"### `{path}` - {status}")
            lines.append("")
            lines.append(f"Used by: {', '.join(sorted(tc_list))}")
            lines.append("")

        lines.extend([
            "**Note**: Some overlap is acceptable for:",
            "- Reports paths (each taskcard writes to its own subdirectory)",
            "- Test paths (if properly scoped by module)",
            "",
            "**Action required for critical overlaps only** (src/**, repo-root files).",
            "",
        ])

    lines.extend([
        "## Recommendations",
        "",
        "### High Priority",
        "",
        "1. **Fix shared library violations** immediately",
        "2. **Review implementation code overlaps** - ensure no merge conflicts possible",
        "3. **Tighten path patterns** - use specific patterns over wildcards where possible",
        "",
        "### Medium Priority",
        "",
        "1. **Split overlapping test directories** - use `tests/unit/<module>/test_<tc_id>_*.py` pattern",
        "2. **Document intentional overlaps** - add comments in taskcard frontmatter",
        "",
        "### Low Priority",
        "",
        "1. **Monitor reports/** overlap** - acceptable as long as each TC has unique subdirectory",
        "",
        "## Audit Trail",
        "",
        "This audit was performed by `tools/audit_allowed_paths.py` on 2026-01-22.",
        "Re-run after updating taskcard frontmatter to verify fixes.",
        "",
        "**Command**: `python tools/audit_allowed_paths.py`",
        "",
    ])

    output_path.write_text("\n".join(lines), encoding="utf-8")


def main():
    """Main audit routine."""
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent

    print("Auditing allowed_paths in all taskcards...")
    print()

    # Find all taskcards
    taskcards = find_taskcards(repo_root)
    if not taskcards:
        print("ERROR: No taskcards found")
        return 1

    print(f"Found {len(taskcards)} taskcard(s)")

    # Read metadata from all taskcards
    taskcards_data = []
    for tc_path in taskcards:
        try:
            content = tc_path.read_text(encoding="utf-8")
            frontmatter = extract_frontmatter(content)
            if frontmatter:
                taskcards_data.append(frontmatter)
            else:
                print(f"Warning: {tc_path.name} has no valid frontmatter")
        except Exception as e:
            print(f"Warning: Failed to read {tc_path.name}: {e}")

    if not taskcards_data:
        print("ERROR: No valid taskcard metadata found")
        return 1

    # Analyze overlaps
    analysis = analyze_overlap(taskcards_data)

    # Generate report
    output_path = repo_root / "reports" / "swarm_allowed_paths_audit.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    generate_report(analysis, output_path)

    print()
    print(f"Report generated: {output_path.relative_to(repo_root)}")
    print()
    print("Summary:")
    print(f"  Total unique paths: {analysis['total_paths']}")
    print(f"  Overlapping paths: {analysis['overlapping_paths']}")
    print(f"  Critical overlaps: {analysis['critical_overlapping_paths']}")
    print(f"  Shared lib violations: {len(analysis['shared_lib_violations'])}")

    has_violations = False

    if analysis["shared_lib_violations"]:
        print()
        print("[FAIL] Shared library violations found")
        has_violations = True

    if analysis["critical_overlaps"]:
        print()
        print("[FAIL] Critical path overlaps found (src/** or repo-root files)")
        for path, tc_list in sorted(analysis["critical_overlaps"].items()):
            print(f"  {path}: {', '.join(sorted(tc_list))}")
        has_violations = True

    if has_violations:
        print()
        print("Review report and fix taskcards before proceeding")
        return 1
    else:
        print()
        print("[OK] No violations detected")
        return 0


if __name__ == "__main__":
    sys.exit(main())
