"""Gate 12: Patch Conflicts.

Validates that patch_bundle.json has no merge conflicts.

Per specs/09_validation_gates.md (patch conflict detection).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple


def execute_gate(run_dir: Path, profile: str) -> Tuple[bool, List[Dict[str, Any]]]:
    """Execute Gate 12: Patch Conflicts.

    Validates that patch_bundle.json has no merge conflict markers.

    Args:
        run_dir: Run directory path
        profile: Validation profile (local, ci, prod)

    Returns:
        Tuple of (gate_passed, issues)
    """
    issues = []

    # Conflict marker definitions
    # Full 7-character markers to avoid false positives
    conflict_markers = ["<<<<<<<", ">>>>>>>"]
    # Separator marker (check for 7+ equals on a line)
    separator_marker = "======="

    # Load patch_bundle.json if it exists
    patch_bundle_path = run_dir / "artifacts" / "patch_bundle.json"
    if patch_bundle_path.exists():
        try:
            with patch_bundle_path.open() as f:
                patch_bundle = json.load(f)
        except Exception as e:
            issues.append(
                {
                    "issue_id": "patch_conflicts_bundle_invalid",
                    "gate": "gate_12_patch_conflicts",
                    "severity": "error",
                    "message": f"Failed to load patch_bundle.json: {e}",
                    "error_code": "GATE_PATCH_BUNDLE_INVALID",
                    "status": "OPEN",
                }
            )
            return False, issues

        # Check for conflict markers in patch content
        patches = patch_bundle.get("patches", [])
        for patch in patches:
            if isinstance(patch, dict):
                patch_id = patch.get("patch_id", "unknown")
                target_file = patch.get("target_file", "unknown")
                content = patch.get("content", "")

                # Check for merge conflict markers
                for marker in conflict_markers:
                    if marker in str(content):
                        issues.append(
                            {
                                "issue_id": f"patch_conflict_{patch_id}",
                                "gate": "gate_12_patch_conflicts",
                                "severity": "blocker",
                                "message": f"Merge conflict marker '{marker}' found in patch for {target_file}",
                                "error_code": "GATE_PATCH_CONFLICT_MARKER",
                                "files": [target_file],
                                "status": "OPEN",
                            }
                        )
                        break  # Only report once per patch

    # Also check actual files for conflict markers
    site_dir = run_dir / "work" / "site"
    if site_dir.exists():
        md_files = sorted(site_dir.rglob("*.md"))

        for md_file in md_files:
            try:
                content = md_file.read_text(encoding="utf-8")

                # Check for conflict markers (must be at start of line)
                lines = content.split("\n")
                found_conflict = False

                for i, line in enumerate(lines, start=1):
                    line_stripped = line.strip()

                    # Check for HEAD/branch markers at start of line
                    if line_stripped.startswith("<<<<<<<") or line_stripped.startswith(">>>>>>>"):
                        issues.append(
                            {
                                "issue_id": f"patch_conflict_file_{md_file.name}_{i}",
                                "gate": "gate_12_patch_conflicts",
                                "severity": "blocker",
                                "message": f"Merge conflict marker found in {md_file.name} at line {i}",
                                "error_code": "GATE_PATCH_CONFLICT_MARKER",
                                "location": {
                                    "path": str(md_file),
                                    "line": i,
                                },
                                "status": "OPEN",
                            }
                        )
                        found_conflict = True
                        break

                    # Check for separator (7+ equals at start of line)
                    if line_stripped.startswith(separator_marker):
                        issues.append(
                            {
                                "issue_id": f"patch_conflict_file_{md_file.name}_{i}",
                                "gate": "gate_12_patch_conflicts",
                                "severity": "blocker",
                                "message": f"Merge conflict separator found in {md_file.name} at line {i}",
                                "error_code": "GATE_PATCH_CONFLICT_MARKER",
                                "location": {
                                    "path": str(md_file),
                                    "line": i,
                                },
                                "status": "OPEN",
                            }
                        )
                        found_conflict = True
                        break

                if found_conflict:
                    pass  # Already reported

            except Exception:
                # Error reading file - will be caught by other gates
                pass

    # Gate passes if no issues (conflict markers are always blockers)
    gate_passed = len(issues) == 0

    return gate_passed, issues
