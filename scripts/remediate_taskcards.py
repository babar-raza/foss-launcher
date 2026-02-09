#!/usr/bin/env python3
"""
Taskcard Remediation Script

Automatically fixes common validation issues across all taskcards:
- status: Complete → Done
- evidence_required: true/false → list
- updated: date object → "YYYY-MM-DD" string
- Missing E2E verification section
- Missing Integration boundary section
- Body/frontmatter allowed_paths mismatch

Usage:
    # Preview changes
    python scripts/remediate_taskcards.py --dry-run

    # Apply fixes with backup
    python scripts/remediate_taskcards.py --apply --backup

    # Generate report
    python scripts/remediate_taskcards.py --dry-run --report remediation_report.md
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple
import yaml
import shutil
from datetime import date

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

# Repo root
REPO_ROOT = Path(__file__).parent.parent
TASKCARDS_DIR = REPO_ROOT / "plans" / "taskcards"


def extract_frontmatter(content: str) -> Tuple[Dict | None, str, str, str]:
    """
    Extract YAML frontmatter from markdown content.
    Returns (frontmatter_dict, yaml_str, body_content, error_message)
    """
    if not content.startswith("---\n"):
        return None, "", "", "No YAML frontmatter found (must start with ---)"

    # Find the closing ---
    match = re.match(r"^---\n(.*?)\n---\n(.*)", content, re.DOTALL)
    if not match:
        return None, "", "", "Malformed YAML frontmatter (no closing ---)"

    yaml_content = match.group(1)
    body = match.group(2)
    try:
        data = yaml.safe_load(yaml_content)
        if not isinstance(data, dict):
            return None, "", "", "YAML frontmatter must be a dictionary"
        return data, yaml_content, body, ""
    except yaml.YAMLError as e:
        return None, "", "", f"YAML parse error: {e}"


def detect_issues(taskcard_path: Path) -> Dict[str, Any]:
    """Scan taskcard and return detected issues"""
    issues = {
        "status_complete": False,
        "yaml_type_date": [],
        "yaml_type_bool": [],
        "missing_e2e": False,
        "missing_integration": False,
        "body_mismatch": False,
        "missing_failure_modes": False,
    }

    try:
        content = taskcard_path.read_text(encoding="utf-8")
        frontmatter, yaml_str, body, error = extract_frontmatter(content)

        if error:
            issues["parse_error"] = error
            return issues

        # Check status: Complete
        if frontmatter.get("status") == "Complete":
            issues["status_complete"] = True

        # Check YAML type errors
        for field in ["updated", "created"]:
            if field in frontmatter and isinstance(frontmatter[field], date):
                issues["yaml_type_date"].append(field)

        for field in ["evidence_required"]:
            if field in frontmatter and isinstance(frontmatter[field], bool):
                issues["yaml_type_bool"].append(field)

        # Check missing sections
        if "## E2E verification" not in content:
            issues["missing_e2e"] = True

        if "## Integration boundary proven" not in content:
            issues["missing_integration"] = True

        # Check body/frontmatter allowed_paths mismatch
        if frontmatter and "allowed_paths" in frontmatter:
            body_paths = extract_body_allowed_paths(body)
            fm_paths = frontmatter["allowed_paths"]
            if isinstance(fm_paths, list) and body_paths != fm_paths:
                issues["body_mismatch"] = True

        # Check failure modes count
        failure_modes_match = re.search(r"## Failure modes\n(.*?)(?=^## |\Z)", content, re.MULTILINE | re.DOTALL)
        if failure_modes_match:
            failure_modes_text = failure_modes_match.group(1)
            # Count numbered items (1., 2., 3., etc.)
            numbered_items = re.findall(r"^\d+\.", failure_modes_text, re.MULTILINE)
            if len(numbered_items) < 3:
                issues["missing_failure_modes"] = True
        else:
            issues["missing_failure_modes"] = True

    except Exception as e:
        issues["exception"] = str(e)

    return issues


def extract_body_allowed_paths(body: str) -> List[str]:
    """Extract allowed paths from the body ## Allowed paths section."""
    match = re.search(r"^## Allowed paths\n(.*?)(?=^## |\Z)", body, re.MULTILINE | re.DOTALL)
    if not match:
        return []

    section = match.group(1)
    paths = []

    # Extract paths from bullet points or lines starting with `-` or `*`
    for line in section.split("\n"):
        line = line.strip()
        if line.startswith("- ") or line.startswith("* "):
            # Remove markdown formatting (backticks, bold, etc.)
            path = line[2:].strip()
            path = re.sub(r"`([^`]+)`", r"\1", path)  # Remove backticks
            path = re.sub(r"\*\*([^*]+)\*\*", r"\1", path)  # Remove bold
            # Split on colon or dash if there's a description
            if ":" in path:
                path = path.split(":")[0].strip()
            if " - " in path:
                path = path.split(" - ")[0].strip()
            if path:
                paths.append(path)

    return paths


def fix_status_complete_to_done(content: str) -> str:
    """Replace status: Complete with status: Done in frontmatter"""
    # Use regex to match frontmatter section only
    pattern = r'^(---\n.*?)(^status:\s*Complete\s*$)(.*?\n---)'
    replacement = r'\1status: Done\3'
    return re.sub(pattern, replacement, content, flags=re.MULTILINE | re.DOTALL)


def fix_yaml_type_date_to_string(frontmatter: Dict, yaml_str: str) -> str:
    """Convert date objects to YYYY-MM-DD strings in YAML"""
    modified_yaml = yaml_str

    for field in ["updated", "created"]:
        if field in frontmatter and isinstance(frontmatter[field], date):
            date_obj = frontmatter[field]
            date_str = date_obj.strftime('%Y-%m-%d')
            # Replace the date object representation with string
            pattern = rf'^{field}:\s*{re.escape(str(date_obj))}$'
            replacement = f'{field}: "{date_str}"'
            modified_yaml = re.sub(pattern, replacement, modified_yaml, flags=re.MULTILINE)

    return modified_yaml


def fix_yaml_type_bool_to_list(frontmatter: Dict, yaml_str: str, tc_id: str, owner: str) -> str:
    """Convert bool to list for evidence_required"""
    modified_yaml = yaml_str

    if "evidence_required" in frontmatter and isinstance(frontmatter["evidence_required"], bool):
        bool_val = frontmatter["evidence_required"]

        if bool_val:
            # Infer standard evidence paths
            agent = owner.lower().replace("-", "_").replace(" ", "_")
            evidence_list = [
                f"reports/agents/{agent}/{tc_id}/evidence.md",
                f"reports/agents/{agent}/{tc_id}/self_review.md"
            ]
            evidence_yaml = "\n".join(f"  - {path}" for path in evidence_list)
            replacement = f"evidence_required:\n{evidence_yaml}"
        else:
            replacement = "evidence_required: []"

        # Replace the bool value
        pattern = r'^evidence_required:\s*(true|false)\s*$'
        modified_yaml = re.sub(pattern, replacement, modified_yaml, flags=re.MULTILINE)

    return modified_yaml


def inject_missing_e2e_section(content: str) -> str:
    """Insert E2E verification section template before final sections"""
    # Template for E2E verification
    e2e_template = """
## E2E verification

```bash
# TODO: Add concrete verification command
.venv/Scripts/python.exe -m pytest tests/unit/workers/test_*.py -x
```

**Expected artifacts:**
- TODO: Specify expected output files/results

**Expected results:**
- TODO: Define success criteria
"""

    # Find insertion point (before ## Integration boundary or at end)
    if "## Integration boundary proven" in content:
        return content.replace("## Integration boundary proven", e2e_template.strip() + "\n\n## Integration boundary proven")
    else:
        # Insert before last section or at end
        last_section_match = re.search(r'(^## [^\n]+\n.*?)(\Z)', content, re.MULTILINE | re.DOTALL)
        if last_section_match:
            return content.rstrip() + "\n\n" + e2e_template.strip() + "\n"
        else:
            return content + "\n" + e2e_template.strip() + "\n"


def inject_missing_integration_section(content: str) -> str:
    """Insert Integration boundary section template at end"""
    integration_template = """
## Integration boundary proven

**Upstream:** TODO: Describe what provides input to this taskcard's work

**Downstream:** TODO: Describe what consumes output from this taskcard's work

**Boundary contract:** TODO: Specify input/output contract
"""

    return content.rstrip() + "\n\n" + integration_template.strip() + "\n"


def normalize_body_allowed_paths(content: str, frontmatter: Dict) -> str:
    """Replace body ## Allowed paths with exact frontmatter match"""
    if "allowed_paths" not in frontmatter:
        return content

    fm_paths = frontmatter["allowed_paths"]
    if not isinstance(fm_paths, list):
        return content

    # Create normalized body section
    normalized_section = "## Allowed paths\n\n"
    for path in fm_paths:
        normalized_section += f"- `{path}`\n"

    # Replace existing section
    pattern = r"^## Allowed paths\n(.*?)(?=^## |\Z)"
    replacement = normalized_section.rstrip()

    return re.sub(pattern, replacement, content, flags=re.MULTILINE | re.DOTALL)


def remediate_taskcard(
    taskcard_path: Path,
    dry_run: bool = True,
    backup: bool = True
) -> Dict[str, Any]:
    """Main remediation function for a single taskcard"""
    report = {
        "path": str(taskcard_path),
        "changes": [],
        "success": False,
    }

    try:
        content = taskcard_path.read_text(encoding="utf-8")
        original_content = content
        frontmatter, yaml_str, body, error = extract_frontmatter(content)

        if error:
            report["error"] = error
            return report

        # Detect issues
        issues = detect_issues(taskcard_path)

        # Apply fixes directly to content string
        # Fix 1: status Complete → Done
        if issues["status_complete"]:
            content = fix_status_complete_to_done(content)
            report["changes"].append("status: Complete → Done")

        # Fix 2: YAML type date → string (add quotes)
        if issues["yaml_type_date"]:
            for field in issues["yaml_type_date"]:
                # Match unquoted date in YAML
                pattern = rf'^({field}:\s*)(\d{{4}}-\d{{2}}-\d{{2}})\s*$'
                replacement = r'\1"\2"'
                content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
            report["changes"].append(f"Date fields to string: {', '.join(issues['yaml_type_date'])}")

        # Fix 3: YAML type bool → list
        if issues["yaml_type_bool"]:
            tc_id = frontmatter.get("id", "TC-XXX")
            owner = frontmatter.get("owner", "agent")
            agent = owner.lower().replace("-", "_").replace(" ", "_")

            for field in issues["yaml_type_bool"]:
                if field == "evidence_required":
                    bool_val = frontmatter.get(field, False)
                    if bool_val:
                        # Replace true with list
                        evidence_list = [
                            f"reports/agents/{agent}/{tc_id}/evidence.md",
                            f"reports/agents/{agent}/{tc_id}/self_review.md"
                        ]
                        replacement = f"{field}:\n  - {evidence_list[0]}\n  - {evidence_list[1]}"
                    else:
                        # Replace false with empty list
                        replacement = f"{field}: []"

                    # Replace in content
                    pattern = rf'^{field}:\s*(true|false)\s*$'
                    content = re.sub(pattern, replacement, content, flags=re.MULTILINE)

            report["changes"].append(f"Bool fields to list: {', '.join(issues['yaml_type_bool'])}")

        # Fix 4: Missing E2E section
        if issues["missing_e2e"]:
            content = inject_missing_e2e_section(content)
            report["changes"].append("Inject missing E2E verification section")

        # Fix 5: Missing Integration section
        if issues["missing_integration"]:
            content = inject_missing_integration_section(content)
            report["changes"].append("Inject missing Integration boundary section")

        # Fix 6: Body/frontmatter mismatch
        if issues["body_mismatch"]:
            content = normalize_body_allowed_paths(content, frontmatter)
            report["changes"].append("Normalize body allowed_paths to match frontmatter")

        # Only write if changes were made
        if content != original_content:
            if not dry_run:
                # Backup if requested
                if backup:
                    backup_path = taskcard_path.with_suffix(".md.backup")
                    shutil.copy2(taskcard_path, backup_path)
                    report["backup"] = str(backup_path)

                # Write modified content
                taskcard_path.write_text(content, encoding="utf-8")

            report["success"] = True
        else:
            report["changes"] = ["No changes needed"]
            report["success"] = True

    except Exception as e:
        report["error"] = str(e)

    return report


def main():
    parser = argparse.ArgumentParser(description="Remediate taskcard validation issues")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without modifying files")
    parser.add_argument("--apply", action="store_true", help="Apply fixes to files")
    parser.add_argument("--backup", action="store_true", default=True, help="Create .md.backup files (default: true)")
    parser.add_argument("--no-backup", action="store_true", help="Skip creating backup files")
    parser.add_argument("--taskcard", help="Specific taskcard ID to remediate (e.g., TC-1010)")
    parser.add_argument("--report", help="Generate detailed report to file")

    args = parser.parse_args()

    # Validate arguments
    if not args.dry_run and not args.apply:
        print("ERROR: Must specify either --dry-run or --apply")
        sys.exit(1)

    if args.no_backup:
        args.backup = False

    # Find taskcards
    if args.taskcard:
        taskcard_files = list(TASKCARDS_DIR.glob(f"{args.taskcard}*.md"))
        if not taskcard_files:
            print(f"ERROR: Taskcard {args.taskcard} not found")
            sys.exit(1)
    else:
        taskcard_files = sorted(TASKCARDS_DIR.glob("TC-*.md"))
        # Exclude template and contract
        taskcard_files = [f for f in taskcard_files if "00_" not in f.name]

    print(f"Taskcard Remediation {'(DRY RUN)' if args.dry_run else ''}")
    print("=" * 60)
    print(f"Scanning: {len(taskcard_files)} taskcards\n")

    # Remediate each taskcard
    results = []
    issues_found = 0
    for taskcard_path in taskcard_files:
        issues = detect_issues(taskcard_path)
        has_issues = any(v for k, v in issues.items() if k != "parse_error" and v)

        if has_issues:
            issues_found += 1
            report = remediate_taskcard(taskcard_path, dry_run=args.dry_run, backup=args.backup)
            results.append(report)

    # Print summary
    print(f"\nIssues found: {issues_found} taskcards\n")

    if issues_found > 0:
        print("Summary by taskcard:")
        print("-" * 60)
        for result in results:
            if result["changes"] and result["changes"] != ["No changes needed"]:
                print(f"\n{Path(result['path']).name}:")
                for change in result["changes"]:
                    print(f"  [FIX] {change}")
                if "backup" in result:
                    print(f"  [BACKUP] {Path(result['backup']).name}")

        print("\n" + "=" * 60)
        if args.dry_run:
            print(f"\nWould modify {len(results)} files. Run with --apply to execute.")
        else:
            print(f"\n✅ Modified {len(results)} files successfully.")
            print("\nRun validation to verify:")
            print("  python tools/validate_taskcards.py")
    else:
        print("✅ No issues found. All taskcards are valid.")

    # Generate report if requested
    if args.report:
        report_path = Path(args.report)
        with report_path.open("w", encoding="utf-8") as f:
            f.write("# Taskcard Remediation Report\n\n")
            f.write(f"**Generated:** {date.today().strftime('%Y-%m-%d')}\n")
            f.write(f"**Mode:** {'DRY RUN' if args.dry_run else 'APPLY'}\n")
            f.write(f"**Scanned:** {len(taskcard_files)} taskcards\n")
            f.write(f"**Issues found:** {issues_found} taskcards\n\n")

            for result in results:
                if result["changes"] and result["changes"] != ["No changes needed"]:
                    f.write(f"## {Path(result['path']).name}\n\n")
                    for change in result["changes"]:
                        f.write(f"- {change}\n")
                    f.write("\n")

        print(f"\nReport saved to: {report_path}")

    sys.exit(0)


if __name__ == "__main__":
    main()
