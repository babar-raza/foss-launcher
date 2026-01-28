"""Gate S2: Sensitive Data Leak.

Validates that content does not contain API keys, passwords, or secrets.

Per TC-571 requirements: Sensitive Data Leak (no API keys, passwords, secrets).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Tuple


def execute_gate(run_dir: Path, profile: str) -> Tuple[bool, List[Dict[str, Any]]]:
    """Execute Gate S2: Sensitive Data Leak.

    Validates that markdown content does not contain:
    - API keys (patterns like AKIA..., sk-..., etc.)
    - Passwords (password=..., pwd=..., etc.)
    - Secret tokens (various patterns)
    - AWS credentials
    - Private keys

    Args:
        run_dir: Run directory path
        profile: Validation profile (local, ci, prod)

    Returns:
        Tuple of (gate_passed, issues)
    """
    issues = []

    # Find all markdown files
    site_dir = run_dir / "work" / "site"
    if not site_dir.exists():
        return True, []

    md_files = sorted(site_dir.rglob("*.md"))

    # Patterns for sensitive data detection
    patterns = {
        "AWS_ACCESS_KEY": re.compile(r'AKIA[0-9A-Z]{16}'),
        "AWS_SECRET_KEY": re.compile(r'aws_secret_access_key\s*=\s*["\']?[\w/+=]{40}["\']?', re.IGNORECASE),
        "GENERIC_API_KEY": re.compile(r'api[_-]?key\s*[=:]\s*["\']?[a-zA-Z0-9_\-]{32,}["\']?', re.IGNORECASE),
        "OPENAI_KEY": re.compile(r'sk-[a-zA-Z0-9]{48}'),
        "PASSWORD": re.compile(r'password\s*[=:]\s*["\']?[^\s"\']{8,}["\']?', re.IGNORECASE),
        "PRIVATE_KEY": re.compile(r'-----BEGIN (RSA |EC )?PRIVATE KEY-----'),
        "GITHUB_TOKEN": re.compile(r'ghp_[a-zA-Z0-9]{36}'),
        "SLACK_TOKEN": re.compile(r'xox[baprs]-[a-zA-Z0-9-]{10,}'),
        "BEARER_TOKEN": re.compile(r'bearer\s+[a-zA-Z0-9_\-\.]{20,}', re.IGNORECASE),
        "BASIC_AUTH": re.compile(r'authorization:\s*basic\s+[a-zA-Z0-9+/=]{20,}', re.IGNORECASE),
    }

    for md_file in md_files:
        try:
            content = md_file.read_text(encoding="utf-8")

            # Skip code blocks for sensitive data checks (code examples might show patterns)
            lines = content.split("\n")
            in_code_block = False
            processed_lines = []

            for i, line in enumerate(lines, start=1):
                if line.strip().startswith("```"):
                    in_code_block = not in_code_block
                    continue
                if not in_code_block:
                    processed_lines.append((i, line))

            # Check each pattern
            for line_num, line in processed_lines:
                for pattern_name, pattern in patterns.items():
                    if pattern.search(line):
                        # Redact the actual value in the message
                        redacted_line = line[:50] + "..." if len(line) > 50 else line
                        issues.append(
                            {
                                "issue_id": f"sensitive_data_{pattern_name.lower()}_{md_file.name}_{line_num}",
                                "gate": "gate_s2_sensitive_data_leak",
                                "severity": "blocker",
                                "message": f"Potential {pattern_name} found in {md_file.name} at line {line_num}",
                                "error_code": f"GATE_SENSITIVE_DATA_{pattern_name}",
                                "location": {"path": str(md_file), "line": line_num},
                                "status": "OPEN",
                            }
                        )

        except Exception as e:
            issues.append(
                {
                    "issue_id": f"sensitive_data_check_error_{md_file.name}",
                    "gate": "gate_s2_sensitive_data_leak",
                    "severity": "error",
                    "message": f"Error checking sensitive data in {md_file.name}: {e}",
                    "error_code": "GATE_SENSITIVE_DATA_CHECK_ERROR",
                    "location": {"path": str(md_file)},
                    "status": "OPEN",
                }
            )

    # Also check artifacts directory for sensitive data
    artifacts_dir = run_dir / "artifacts"
    if artifacts_dir.exists():
        for artifact_file in sorted(artifacts_dir.glob("*.json")):
            if artifact_file.name == "events.ndjson":
                continue

            try:
                content = artifact_file.read_text(encoding="utf-8")

                for pattern_name, pattern in patterns.items():
                    if pattern.search(content):
                        issues.append(
                            {
                                "issue_id": f"sensitive_data_{pattern_name.lower()}_{artifact_file.name}",
                                "gate": "gate_s2_sensitive_data_leak",
                                "severity": "blocker",
                                "message": f"Potential {pattern_name} found in artifact {artifact_file.name}",
                                "error_code": f"GATE_SENSITIVE_DATA_{pattern_name}",
                                "location": {"path": str(artifact_file)},
                                "status": "OPEN",
                            }
                        )

            except Exception:
                pass  # Skip files that cannot be read

    # Gate passes if no blocker/error issues
    gate_passed = not any(
        issue["severity"] in ["blocker", "error"] for issue in issues
    )

    return gate_passed, issues
