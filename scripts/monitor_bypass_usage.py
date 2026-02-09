#!/usr/bin/env python3
"""
Bypass Usage Monitor

Analyzes git commit history to track --no-verify hook bypass frequency.
Helps maintain governance compliance by identifying bypass patterns.

Usage:
    # Show bypass statistics for last 100 commits
    python scripts/monitor_bypass_usage.py

    # Analyze specific date range
    python scripts/monitor_bypass_usage.py --since "2026-02-01" --until "2026-02-09"

    # Generate detailed report
    python scripts/monitor_bypass_usage.py --detailed --output bypass_report.md

    # Check specific branch
    python scripts/monitor_bypass_usage.py --branch feature/tc910
"""

import argparse
import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

# Repo root
REPO_ROOT = Path(__file__).parent.parent

# Bypass indicators (case-insensitive patterns)
BYPASS_PATTERNS = [
    r"no.verify",
    r"no-verify",
    r"--no-verify",
    r"skip.*hook",
    r"bypass.*hook",
    r"without.*hook",
    r"disable.*hook",
]


def get_git_log(since: str = None, until: str = None, branch: str = None, max_count: int = 100) -> List[Dict]:
    """
    Retrieve git commit log with messages and metadata.

    Returns list of dicts with keys: hash, author, date, message
    """
    cmd = ["git", "log", "--format=%H%n%an%n%ai%n%B%n---END---"]

    if branch:
        cmd.append(branch)

    if since:
        cmd.append(f"--since={since}")

    if until:
        cmd.append(f"--until={until}")

    if max_count:
        cmd.append(f"--max-count={max_count}")

    try:
        result = subprocess.run(
            cmd,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',  # Replace problematic characters
            check=True
        )

        # Parse commits
        commits = []
        raw_commits = result.stdout.split("---END---\n")

        for raw in raw_commits:
            if not raw.strip():
                continue

            lines = raw.strip().split("\n")
            if len(lines) < 4:
                continue

            commit_hash = lines[0]
            author = lines[1]
            date = lines[2]
            message = "\n".join(lines[3:])

            commits.append({
                "hash": commit_hash,
                "author": author,
                "date": date,
                "message": message
            })

        return commits

    except subprocess.CalledProcessError as e:
        print(f"Error running git log: {e}", file=sys.stderr)
        return []


def detect_bypass(commit_message: str) -> Tuple[bool, List[str]]:
    """
    Check if commit message contains bypass indicators.

    Returns (is_bypass, matched_patterns)
    """
    matched = []
    message_lower = commit_message.lower()

    for pattern in BYPASS_PATTERNS:
        if re.search(pattern, message_lower, re.IGNORECASE):
            matched.append(pattern)

    return (len(matched) > 0, matched)


def analyze_commits(commits: List[Dict]) -> Dict:
    """
    Analyze commits for bypass usage.

    Returns statistics dict
    """
    stats = {
        "total_commits": len(commits),
        "bypass_commits": [],
        "bypass_count": 0,
        "bypass_rate": 0.0,
        "authors": defaultdict(int),
        "patterns": defaultdict(int),
        "timeline": defaultdict(int),  # Bypasses by date
    }

    for commit in commits:
        is_bypass, patterns = detect_bypass(commit["message"])

        if is_bypass:
            stats["bypass_count"] += 1
            stats["authors"][commit["author"]] += 1

            # Track patterns
            for pattern in patterns:
                stats["patterns"][pattern] += 1

            # Track timeline (by date)
            commit_date = commit["date"].split()[0]  # YYYY-MM-DD
            stats["timeline"][commit_date] += 1

            # Store full commit info
            stats["bypass_commits"].append({
                "hash": commit["hash"][:8],
                "author": commit["author"],
                "date": commit_date,
                "message": commit["message"].split("\n")[0][:80],  # First line, truncated
                "patterns": patterns
            })

    # Calculate bypass rate
    if stats["total_commits"] > 0:
        stats["bypass_rate"] = (stats["bypass_count"] / stats["total_commits"]) * 100

    return stats


def print_summary(stats: Dict):
    """Print summary statistics to console"""
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("🔍 BYPASS USAGE MONITOR")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"\nAnalyzed: {stats['total_commits']} commits")
    print(f"Bypasses detected: {stats['bypass_count']} ({stats['bypass_rate']:.1f}%)")
    print()

    if stats["bypass_count"] == 0:
        print("✅ No hook bypasses detected")
        return

    # Authors
    print("Bypasses by author:")
    for author, count in sorted(stats["authors"].items(), key=lambda x: x[1], reverse=True):
        print(f"  {author}: {count}")
    print()

    # Patterns
    print("Bypass patterns detected:")
    for pattern, count in sorted(stats["patterns"].items(), key=lambda x: x[1], reverse=True):
        print(f"  {pattern}: {count}")
    print()

    # Timeline
    print("Bypass timeline:")
    for date, count in sorted(stats["timeline"].items()):
        print(f"  {date}: {count}")
    print()


def print_detailed(stats: Dict):
    """Print detailed bypass information"""
    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("DETAILED BYPASS REPORT")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

    for i, commit in enumerate(stats["bypass_commits"], 1):
        print(f"{i}. Commit {commit['hash']}")
        print(f"   Author: {commit['author']}")
        print(f"   Date: {commit['date']}")
        print(f"   Message: {commit['message']}")
        print(f"   Patterns: {', '.join(commit['patterns'])}")
        print()


def generate_markdown_report(stats: Dict, output_path: Path):
    """Generate markdown report file"""
    with output_path.open("w", encoding="utf-8") as f:
        f.write("# Bypass Usage Report\n\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Repository:** {REPO_ROOT.name}\n\n")

        f.write("---\n\n")

        # Summary
        f.write("## Summary\n\n")
        f.write(f"- **Total commits analyzed:** {stats['total_commits']}\n")
        f.write(f"- **Bypasses detected:** {stats['bypass_count']} ({stats['bypass_rate']:.1f}%)\n\n")

        if stats["bypass_count"] == 0:
            f.write("✅ No hook bypasses detected in analyzed commits.\n")
            return

        # Authors
        f.write("## Bypasses by Author\n\n")
        f.write("| Author | Count |\n")
        f.write("|--------|-------|\n")
        for author, count in sorted(stats["authors"].items(), key=lambda x: x[1], reverse=True):
            f.write(f"| {author} | {count} |\n")
        f.write("\n")

        # Patterns
        f.write("## Bypass Patterns\n\n")
        f.write("| Pattern | Occurrences |\n")
        f.write("|---------|-------------|\n")
        for pattern, count in sorted(stats["patterns"].items(), key=lambda x: x[1], reverse=True):
            f.write(f"| `{pattern}` | {count} |\n")
        f.write("\n")

        # Timeline
        f.write("## Timeline\n\n")
        f.write("| Date | Bypasses |\n")
        f.write("|------|----------|\n")
        for date, count in sorted(stats["timeline"].items()):
            f.write(f"| {date} | {count} |\n")
        f.write("\n")

        # Detailed commits
        f.write("## Detailed Commit List\n\n")
        for i, commit in enumerate(stats["bypass_commits"], 1):
            f.write(f"### {i}. Commit `{commit['hash']}`\n\n")
            f.write(f"- **Author:** {commit['author']}\n")
            f.write(f"- **Date:** {commit['date']}\n")
            f.write(f"- **Message:** {commit['message']}\n")
            f.write(f"- **Patterns:** {', '.join(f'`{p}`' for p in commit['patterns'])}\n\n")

        f.write("---\n\n")
        f.write("## Recommendations\n\n")

        if stats["bypass_rate"] > 10:
            f.write("⚠️ **HIGH BYPASS RATE** (>10%)\n\n")
            f.write("- Review enforcement mechanisms\n")
            f.write("- Investigate reasons for frequent bypasses\n")
            f.write("- Consider stricter CI/CD validation\n")
        elif stats["bypass_rate"] > 5:
            f.write("⚠️ **MODERATE BYPASS RATE** (5-10%)\n\n")
            f.write("- Monitor bypass patterns\n")
            f.write("- Ensure bypasses are justified (emergency fixes)\n")
        else:
            f.write("✅ **LOW BYPASS RATE** (<5%)\n\n")
            f.write("- Enforcement appears effective\n")
            f.write("- Continue monitoring\n")


def main():
    parser = argparse.ArgumentParser(description="Monitor git hook bypass usage")
    parser.add_argument("--since", help="Analyze commits since date (YYYY-MM-DD)")
    parser.add_argument("--until", help="Analyze commits until date (YYYY-MM-DD)")
    parser.add_argument("--branch", help="Specific branch to analyze (default: current)")
    parser.add_argument("--max-count", type=int, default=100, help="Max commits to analyze (default: 100)")
    parser.add_argument("--detailed", action="store_true", help="Show detailed commit list")
    parser.add_argument("--output", help="Generate markdown report to file")

    args = parser.parse_args()

    # Get commits
    commits = get_git_log(
        since=args.since,
        until=args.until,
        branch=args.branch,
        max_count=args.max_count
    )

    if not commits:
        print("No commits found to analyze", file=sys.stderr)
        sys.exit(1)

    # Analyze
    stats = analyze_commits(commits)

    # Print summary
    print_summary(stats)

    # Print detailed if requested
    if args.detailed:
        print_detailed(stats)

    # Generate report if requested
    if args.output:
        output_path = Path(args.output)
        generate_markdown_report(stats, output_path)
        print(f"\n📄 Report saved to: {output_path}")

    # Exit with warning code if bypass rate is high
    if stats["bypass_rate"] > 10:
        print("\n⚠️  WARNING: High bypass rate detected (>10%)")
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
