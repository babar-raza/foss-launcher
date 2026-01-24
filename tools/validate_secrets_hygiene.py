#!/usr/bin/env python3
"""
Secrets Hygiene Validator (Gate L)

Validates that no secrets appear in logs/artifacts/reports per Guarantee E.

Scans for secret patterns using regex and basic entropy analysis.

See: specs/34_strict_compliance_guarantees.md (Guarantee E)

Exit codes:
  0 - No secrets detected (or no runs to scan)
  1 - Secrets detected or scan failed
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple


# Secret detection patterns
SECRET_PATTERNS = [
    (r"ghp_[A-Za-z0-9]{36}", "GitHub Personal Access Token"),
    (r"github_pat_[A-Za-z0-9_]{82}", "GitHub Fine-Grained PAT"),
    (r"gho_[A-Za-z0-9]{36}", "GitHub OAuth Token"),
    (r"ghu_[A-Za-z0-9]{36}", "GitHub User-to-Server Token"),
    (r"ghs_[A-Za-z0-9]{36}", "GitHub Server-to-Server Token"),
    (r"ghr_[A-Za-z0-9]{36}", "GitHub Refresh Token"),
    (r"Bearer\s+[A-Za-z0-9._\-]{20,}", "Bearer Token"),
    (r"(?i)api[_\-]?key[\"\']?\s*[:=]\s*[\"\']?([A-Za-z0-9_\-]{32,})[\"\']?", "API Key (generic)"),
    (r"(?i)secret[\"\']?\s*[:=]\s*[\"\']?([A-Za-z0-9_\-]{20,})[\"\']?", "Secret (generic)"),
    (r"(?i)password[\"\']?\s*[:=]\s*[\"\']?([A-Za-z0-9_\-@!#$%^&*]{8,})[\"\']?", "Password (generic)"),
    (r"(?i)token[\"\']?\s*[:=]\s*[\"\']?([A-Za-z0-9._\-]{20,})[\"\']?", "Token (generic)"),
    (r"-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----", "Private Key"),
    (r"AKIA[0-9A-Z]{16}", "AWS Access Key ID"),
]

# Paths to exclude from scanning (known false positives)
EXCLUDE_PATTERNS = [
    "**/PHASE7/*/validate_swarm_ready.txt",  # Contains description of secret patterns
    "**/validate_secrets_hygiene.py",  # This file contains patterns
]


def calculate_entropy(s: str) -> float:
    """Calculate Shannon entropy of a string."""
    import math
    from collections import Counter

    if not s:
        return 0.0

    counts = Counter(s)
    total = len(s)
    entropy = -sum((count / total) * math.log2(count / total) for count in counts.values())
    return entropy


def scan_file_for_secrets(file_path: Path) -> List[Tuple[int, str, str]]:
    """
    Scan a file for secret patterns.
    Returns list of (line_number, pattern_name, matched_text).
    """
    violations = []

    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return violations

    lines = content.split("\n")

    for i, line in enumerate(lines, 1):
        for pattern, name in SECRET_PATTERNS:
            matches = re.finditer(pattern, line)
            for match in matches:
                matched_text = match.group(0)

                # Basic entropy check (high entropy suggests real secret)
                entropy = calculate_entropy(matched_text)

                # For generic patterns, require higher entropy
                if "generic" in name and entropy < 3.5:
                    continue

                # Redact the secret for output
                if len(matched_text) > 20:
                    redacted = matched_text[:8] + "***REDACTED***"
                else:
                    redacted = "***REDACTED***"

                violations.append((i, name, redacted))

    return violations


def should_scan_file(file_path: Path, repo_root: Path) -> bool:
    """Check if file should be scanned (exclude known false positives)."""
    try:
        relative_path = file_path.relative_to(repo_root)
    except ValueError:
        return False

    relative_str = str(relative_path)

    for pattern in EXCLUDE_PATTERNS:
        import fnmatch

        if fnmatch.fnmatch(relative_str, pattern):
            return False

    return True


def main():
    """Main validation routine."""
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent

    print("=" * 70)
    print("SECRETS HYGIENE VALIDATION (Gate L)")
    print("=" * 70)
    print(f"Repository: {repo_root}")
    print()

    runs_dir = repo_root / "runs"

    if not runs_dir.exists() or not list(runs_dir.iterdir()):
        print("Note: No runs/ directory found (or empty)")
        print("  Secrets scan only applies when runs exist")
        print()
        print("=" * 70)
        print("RESULT: Secrets scan skipped (no runs to scan)")
        print("=" * 70)
        return 0

    # Collect all files to scan
    files_to_scan = []

    # Scan logs/
    logs_pattern = runs_dir / "**" / "logs" / "**" / "*"
    for file_path in runs_dir.glob("**/logs/**/*"):
        if file_path.is_file() and should_scan_file(file_path, repo_root):
            files_to_scan.append(file_path)

    # Scan reports/
    for file_path in runs_dir.glob("**/reports/**/*"):
        if file_path.is_file() and should_scan_file(file_path, repo_root):
            files_to_scan.append(file_path)

    # Scan artifacts/
    for file_path in runs_dir.glob("**/artifacts/**/*"):
        if file_path.is_file() and should_scan_file(file_path, repo_root):
            files_to_scan.append(file_path)

    print(f"Scanning {len(files_to_scan)} file(s) for secret patterns...")
    print()

    violations = []
    for file_path in files_to_scan:
        file_violations = scan_file_for_secrets(file_path)
        if file_violations:
            violations.append((file_path, file_violations))

    if violations:
        print("SECRETS DETECTED:")
        print()
        for file_path, file_violations in violations:
            relative = file_path.relative_to(repo_root)
            print(f"[FAIL] {relative}")
            for line_num, pattern_name, redacted in file_violations:
                print(f"  Line {line_num}: {pattern_name} - {redacted}")
        print()
        print("=" * 70)
        print(f"RESULT: Secrets hygiene validation FAILED ({len(violations)} file(s) with secrets)")
        print()
        print("Action required:")
        print("  - Remove secrets from logs/reports/artifacts")
        print("  - Use redaction in logging utilities")
        print("  - Review secret management practices")
        print("=" * 70)
        return 1
    else:
        print("  PASS: No secrets detected")
        print()
        print("=" * 70)
        print("RESULT: Secrets hygiene validation PASSED")
        print()
        print(f"Scanned {len(files_to_scan)} file(s) in runs/ directory")
        print("No secret patterns detected")
        print("=" * 70)
        return 0


if __name__ == "__main__":
    sys.exit(main())
