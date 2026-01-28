#!/usr/bin/env python3
"""
AGENT_L Link and TODO Checker
Systematically audits repository markdown files for:
- Broken internal links
- TODO/TBD/FIXME markers
- Consistency issues
"""

import os
import re
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict

@dataclass
class LinkIssue:
    file_path: str
    line_num: int
    link_text: str
    link_target: str
    issue_type: str  # "broken", "external", "valid"
    severity: str  # "BLOCKER", "WARNING", "INFO"
    context: str

@dataclass
class TodoIssue:
    file_path: str
    line_num: int
    marker_type: str  # "TODO", "TBD", "FIXME", "XXX", "HACK"
    severity: str  # "BLOCKER", "WARNING", "INFO"
    context: str

class RepoAuditor:
    def __init__(self, repo_root: str):
        self.repo_root = Path(repo_root)
        self.link_issues: List[LinkIssue] = []
        self.todo_issues: List[TodoIssue] = []
        self.scanned_files: List[str] = []
        self.stats = {
            "total_files": 0,
            "total_links": 0,
            "broken_links": 0,
            "external_links": 0,
            "valid_links": 0,
            "total_todos": 0,
            "blocker_issues": 0,
            "warning_issues": 0,
            "info_issues": 0
        }

        # Patterns
        self.link_pattern = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
        self.todo_pattern = re.compile(r'\b(TODO|TBD|FIXME|XXX|HACK)\b', re.IGNORECASE)

        # Exclude patterns
        self.exclude_dirs = {'.venv', 'node_modules', '.git', '__pycache__', '.pytest_cache'}

    def is_excluded(self, path: Path) -> bool:
        """Check if path should be excluded from scanning."""
        parts = path.parts
        return any(excl in parts for excl in self.exclude_dirs)

    def find_markdown_files(self) -> List[Path]:
        """Find all markdown files in repo."""
        md_files = []
        for md_file in self.repo_root.rglob("*.md"):
            if not self.is_excluded(md_file):
                md_files.append(md_file)
        return sorted(md_files)

    def classify_severity(self, file_path: Path, marker_type: str) -> str:
        """Classify severity of TODO/TBD marker based on file location."""
        path_str = str(file_path)

        # BLOCKER: TODOs in binding specs
        if '/specs/' in path_str and not '/specs/templates/' in path_str and not '/specs/pilots/' in path_str:
            return "BLOCKER"

        # WARNING: TODOs in plans
        if '/plans/' in path_str:
            return "WARNING"

        # INFO: TODOs elsewhere
        return "INFO"

    def resolve_link_target(self, source_file: Path, link_target: str) -> Tuple[bool, Path]:
        """
        Resolve a link target relative to source file.
        Returns (exists, resolved_path)
        """
        # Skip external links
        if link_target.startswith(('http://', 'https://', 'mailto:', 'ftp://')):
            return True, None  # External links assumed valid

        # Skip anchors only (same-file links)
        if link_target.startswith('#'):
            return True, None  # Assume valid (checking anchors requires parsing)

        # Remove anchor fragments
        if '#' in link_target:
            link_target = link_target.split('#')[0]

        # Empty after removing anchor means same-file link
        if not link_target:
            return True, None

        # Handle absolute paths (repo-relative, starting with /)
        if link_target.startswith('/'):
            # Treat as repo-relative path
            target_path = (self.repo_root / link_target.lstrip('/')).resolve()
        else:
            # Resolve relative path from source file location
            source_dir = source_file.parent
            target_path = (source_dir / link_target).resolve()

        # Check if target exists
        exists = target_path.exists()
        return exists, target_path

    def is_placeholder_link(self, link_text: str, link_target: str, context: str) -> bool:
        """Check if link is a placeholder/example in documentation."""
        # Common placeholder patterns
        placeholders = ['path', 'url', 'file.md', 'XX_', '__', 'example', 'placeholder']

        # Check if in code block or backticks
        if context.strip().startswith(('```', '`')) or '`[' in context:
            return True

        # Check for placeholder text
        for placeholder in placeholders:
            if placeholder in link_text.lower() or placeholder in link_target.lower():
                return True

        return False

    def check_links_in_file(self, file_path: Path):
        """Check all markdown links in a file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return

        rel_path = file_path.relative_to(self.repo_root)
        in_code_block = False

        for line_num, line in enumerate(lines, start=1):
            # Track code block state
            if line.strip().startswith('```'):
                in_code_block = not in_code_block

            for match in self.link_pattern.finditer(line):
                link_text = match.group(1)
                link_target = match.group(2)
                self.stats["total_links"] += 1

                # Skip external links (just count them)
                if link_target.startswith(('http://', 'https://', 'mailto:', 'ftp://')):
                    self.stats["external_links"] += 1
                    continue

                # Skip placeholder/example links in code blocks
                if in_code_block or self.is_placeholder_link(link_text, link_target, line):
                    self.stats["valid_links"] += 1
                    continue

                # Check if link resolves
                exists, resolved_path = self.resolve_link_target(file_path, link_target)

                if not exists and resolved_path is not None:
                    # Broken internal link
                    self.stats["broken_links"] += 1
                    self.stats["blocker_issues"] += 1
                    issue = LinkIssue(
                        file_path=str(rel_path),
                        line_num=line_num,
                        link_text=link_text,
                        link_target=link_target,
                        issue_type="broken",
                        severity="BLOCKER",
                        context=line.strip()
                    )
                    self.link_issues.append(issue)
                else:
                    self.stats["valid_links"] += 1

    def check_todos_in_file(self, file_path: Path):
        """Check for TODO/TBD markers in a file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return

        rel_path = file_path.relative_to(self.repo_root)

        for line_num, line in enumerate(lines, start=1):
            # Skip code blocks (simple heuristic: lines starting with 4 spaces or tab)
            if line.startswith(('    ', '\t')):
                continue

            for match in self.todo_pattern.finditer(line):
                marker_type = match.group(1).upper()
                self.stats["total_todos"] += 1

                severity = self.classify_severity(file_path, marker_type)

                if severity == "BLOCKER":
                    self.stats["blocker_issues"] += 1
                elif severity == "WARNING":
                    self.stats["warning_issues"] += 1
                else:
                    self.stats["info_issues"] += 1

                issue = TodoIssue(
                    file_path=str(rel_path),
                    line_num=line_num,
                    marker_type=marker_type,
                    severity=severity,
                    context=line.strip()
                )
                self.todo_issues.append(issue)

    def scan_all(self):
        """Scan all markdown files for links and TODOs."""
        md_files = self.find_markdown_files()
        self.stats["total_files"] = len(md_files)

        print(f"Scanning {len(md_files)} markdown files...")

        for i, md_file in enumerate(md_files):
            if (i + 1) % 50 == 0:
                print(f"  Progress: {i + 1}/{len(md_files)}")

            rel_path = md_file.relative_to(self.repo_root)
            self.scanned_files.append(str(rel_path))

            self.check_links_in_file(md_file)
            self.check_todos_in_file(md_file)

        print(f"Scan complete: {len(md_files)} files processed")

    def generate_report(self) -> str:
        """Generate markdown report."""
        report = []
        report.append("# AGENT_L Repository Professionalism Audit Report")
        report.append("")
        report.append(f"**Generated:** {os.environ.get('DATE', '2026-01-27')}")
        report.append(f"**Repository Root:** `{self.repo_root}`")
        report.append("")

        # Summary
        report.append("## Executive Summary")
        report.append("")
        report.append(f"- **Files Scanned:** {self.stats['total_files']}")
        report.append(f"- **Total Links Checked:** {self.stats['total_links']}")
        report.append(f"  - Valid Internal Links: {self.stats['valid_links']}")
        report.append(f"  - External Links: {self.stats['external_links']}")
        report.append(f"  - **BROKEN Links: {self.stats['broken_links']}** {'⚠️' if self.stats['broken_links'] > 0 else '✓'}")
        report.append(f"- **TODO Markers Found:** {self.stats['total_todos']}")
        report.append("")

        # Severity breakdown
        report.append("## Issue Severity Breakdown")
        report.append("")
        report.append(f"- **BLOCKER Issues:** {self.stats['blocker_issues']} (broken links + TODOs in binding specs)")
        report.append(f"- **WARNING Issues:** {self.stats['warning_issues']} (TODOs in plans)")
        report.append(f"- **INFO Issues:** {self.stats['info_issues']} (TODOs in docs/reference)")
        report.append("")

        # GO/NO-GO
        if self.stats['broken_links'] > 0:
            report.append("## ❌ GO/NO-GO: **NO-GO**")
            report.append("")
            report.append(f"**Reason:** {self.stats['broken_links']} broken internal links found (BLOCKER per contract)")
        else:
            report.append("## ✅ GO/NO-GO: **GO**")
            report.append("")
            report.append("All internal links are valid.")
        report.append("")

        # Link issues
        if self.link_issues:
            report.append("## Broken Links (BLOCKER)")
            report.append("")
            for issue in sorted(self.link_issues, key=lambda x: (x.file_path, x.line_num)):
                report.append(f"### `{issue.file_path}:{issue.line_num}`")
                report.append(f"- **Link Text:** `{issue.link_text}`")
                report.append(f"- **Target:** `{issue.link_target}`")
                report.append(f"- **Context:** `{issue.context}`")
                report.append("")

        # TODO issues by severity
        if self.todo_issues:
            report.append("## TODO/TBD Markers")
            report.append("")

            blockers = [t for t in self.todo_issues if t.severity == "BLOCKER"]
            warnings = [t for t in self.todo_issues if t.severity == "WARNING"]
            infos = [t for t in self.todo_issues if t.severity == "INFO"]

            if blockers:
                report.append("### BLOCKER: TODOs in Binding Specs")
                report.append("")
                for issue in sorted(blockers, key=lambda x: (x.file_path, x.line_num)):
                    report.append(f"- **`{issue.file_path}:{issue.line_num}`** [{issue.marker_type}]")
                    report.append(f"  - Context: `{issue.context}`")
                report.append("")

            if warnings:
                report.append("### WARNING: TODOs in Plans")
                report.append("")
                for issue in sorted(warnings, key=lambda x: (x.file_path, x.line_num)):
                    report.append(f"- **`{issue.file_path}:{issue.line_num}`** [{issue.marker_type}]")
                    report.append(f"  - Context: `{issue.context}`")
                report.append("")

            if infos:
                report.append("### INFO: TODOs in Other Files")
                report.append("")
                # Group by file to reduce noise
                by_file = defaultdict(list)
                for issue in infos:
                    by_file[issue.file_path].append(issue)

                for file_path in sorted(by_file.keys()):
                    issues = by_file[file_path]
                    report.append(f"- **`{file_path}`** ({len(issues)} markers)")
                    for issue in sorted(issues, key=lambda x: x.line_num):
                        report.append(f"  - Line {issue.line_num}: `{issue.marker_type}` - {issue.context[:80]}")
                report.append("")

        # Files scanned
        report.append("## Files Scanned")
        report.append("")
        report.append(f"Total: {len(self.scanned_files)} files")
        report.append("")
        report.append("<details><summary>Show all files</summary>")
        report.append("")
        for f in self.scanned_files:
            report.append(f"- `{f}`")
        report.append("")
        report.append("</details>")
        report.append("")

        return "\n".join(report)

    def generate_gaps_report(self) -> str:
        """Generate structured gaps report."""
        gaps = []
        gaps.append("# Repository Professionalism Gaps")
        gaps.append("")
        gaps.append("## Summary")
        gaps.append("")
        gaps.append(f"- **Total Gaps:** {len(self.link_issues) + len(self.todo_issues)}")
        gaps.append(f"- **BLOCKER Gaps:** {self.stats['blocker_issues']}")
        gaps.append(f"- **WARNING Gaps:** {self.stats['warning_issues']}")
        gaps.append(f"- **INFO Gaps:** {self.stats['info_issues']}")
        gaps.append("")

        gap_num = 1

        # Link gaps
        for issue in sorted(self.link_issues, key=lambda x: (x.file_path, x.line_num)):
            gaps.append(f"## L-GAP-{gap_num:03d} | {issue.severity} | Broken Internal Link")
            gaps.append(f"**File:** `{issue.file_path}:{issue.line_num}`")
            gaps.append(f"**Issue:** Link to `[{issue.link_text}]({issue.link_target})` is broken")
            gaps.append(f"**Evidence:**")
            gaps.append(f"```")
            gaps.append(f"{issue.context}")
            gaps.append(f"```")
            gaps.append(f"**Impact:** Documentation is unnavigable, breaks user onboarding")
            gaps.append(f"**Proposed Fix:** Fix link to correct path OR remove if target deleted")
            gaps.append("")
            gap_num += 1

        # TODO gaps (only BLOCKER and WARNING)
        critical_todos = [t for t in self.todo_issues if t.severity in ["BLOCKER", "WARNING"]]
        for issue in sorted(critical_todos, key=lambda x: (x.severity, x.file_path, x.line_num)):
            gap_type = "TODO Marker in Binding Spec" if issue.severity == "BLOCKER" else "TODO Marker in Plan"
            gaps.append(f"## L-GAP-{gap_num:03d} | {issue.severity} | {gap_type}")
            gaps.append(f"**File:** `{issue.file_path}:{issue.line_num}`")
            gaps.append(f"**Issue:** {issue.marker_type} marker indicates incomplete work")
            gaps.append(f"**Evidence:**")
            gaps.append(f"```")
            gaps.append(f"{issue.context}")
            gaps.append(f"```")
            impact = "Spec incompleteness blocks implementation" if issue.severity == "BLOCKER" else "Plan incompleteness may affect coordination"
            gaps.append(f"**Impact:** {impact}")
            gaps.append(f"**Proposed Fix:** Complete section or convert {issue.marker_type} to tracked gap")
            gaps.append("")
            gap_num += 1

        if gap_num == 1:
            gaps.append("**No critical gaps found.**")
            gaps.append("")

        return "\n".join(gaps)

    def save_results(self, output_dir: str):
        """Save all results to output directory."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Save report
        report = self.generate_report()
        with open(output_path / "REPORT.md", 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"Report saved to {output_path / 'REPORT.md'}")

        # Save gaps
        gaps = self.generate_gaps_report()
        with open(output_path / "GAPS.md", 'w', encoding='utf-8') as f:
            f.write(gaps)
        print(f"Gaps saved to {output_path / 'GAPS.md'}")

        # Save raw data as JSON
        data = {
            "stats": self.stats,
            "link_issues": [asdict(i) for i in self.link_issues],
            "todo_issues": [asdict(i) for i in self.todo_issues],
            "scanned_files": self.scanned_files
        }
        with open(output_path / "audit_data.json", 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        print(f"Raw data saved to {output_path / 'audit_data.json'}")

def main():
    repo_root = "c:/Users/prora/OneDrive/Documents/GitHub/foss-launcher"
    output_dir = "c:/Users/prora/OneDrive/Documents/GitHub/foss-launcher/reports/pre_impl_verification/20260127-1724/agents/AGENT_L"

    print("=" * 80)
    print("AGENT_L - Repository Professionalism Auditor")
    print("=" * 80)
    print()

    auditor = RepoAuditor(repo_root)
    auditor.scan_all()

    print()
    print("=" * 80)
    print("Scan Results")
    print("=" * 80)
    print(f"Broken Links: {auditor.stats['broken_links']}")
    print(f"TODO Markers: {auditor.stats['total_todos']}")
    print(f"BLOCKER Issues: {auditor.stats['blocker_issues']}")
    print()

    auditor.save_results(output_dir)

    print()
    print("=" * 80)
    print("Audit Complete")
    print("=" * 80)

if __name__ == "__main__":
    main()
