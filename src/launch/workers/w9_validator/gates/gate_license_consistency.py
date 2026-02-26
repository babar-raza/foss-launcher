"""Gate: License Consistency (TC-2870).

Validates that all pages referencing a license agree with the canonical
license from shared_facts.json. Prevents LLM from hallucinating license
terms (e.g., saying "MIT" when the product is "Freemium" licensed).

Severity: error in ci/prod (blocker in prod), warn in local.
graceful_artifact_skip: True — Phase 2 tightened: CI/prod now fails
if shared_facts.json is missing or corrupted.  Local still passes.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

# License identifiers we scan for in page content.
_LICENSE_NAMES_RE = re.compile(
    r"\b("
    r"MIT|Apache(?:\s*2(?:\.0)?)?|GPL(?:v[23])?|LGPL|BSD|MPL|ISC|AGPL|"
    r"Freemium|Commercial|Proprietary|EUPL|Unlicense|CC0|CDDL|EPL|"
    r"Artistic|Zlib|BSL|SSPL"
    r")\b",
    re.IGNORECASE,
)

# Phrases that claim open-source / free licensing
_FREE_CLAIM_RE = re.compile(
    r"\b(free\s+(?:and\s+)?open[- ]?source|"
    r"open[- ]?source\s+(?:license|software|library|package|tool)|"
    r"free\s+(?:license|software|library|package|tool)|"
    r"no[- ]?cost\s+(?:license|software|library|package))\b",
    re.IGNORECASE,
)

# Licenses that are NOT open-source / free
_COMMERCIAL_SPDX_IDS = frozenset({
    "commercial", "proprietary", "freemium",
})


def execute_gate(
    run_dir: Path, profile: str,
) -> Tuple[bool, List[Dict[str, Any]]]:
    """Execute license consistency gate.

    Args:
        run_dir: Run directory path
        profile: Validation profile (local, ci, prod)

    Returns:
        Tuple of (gate_passed, issues)
    """
    issues: List[Dict[str, Any]] = []

    # Load shared_facts.json
    sf_path = run_dir / "artifacts" / "shared_facts.json"
    if not sf_path.exists():
        # Phase 2: CI/prod must have shared_facts for license validation
        if profile in ("ci", "prod"):
            sev = "blocker" if profile == "prod" else "error"
            return False, [
                {
                    "issue_id": "license_no_shared_facts",
                    "gate": "gate_license_consistency",
                    "severity": sev,
                    "message": "No shared_facts.json found — cannot validate license consistency",
                    "error_code": "LICENSE_SHARED_FACTS_MISSING",
                    "status": "OPEN",
                }
            ]
        return True, [
            {
                "issue_id": "license_no_shared_facts",
                "gate": "gate_license_consistency",
                "severity": "info",
                "message": "No shared_facts.json found, skipping license consistency check",
                "error_code": "LICENSE_SHARED_FACTS_MISSING",
                "status": "OPEN",
            }
        ]

    try:
        with open(sf_path, "r", encoding="utf-8") as f:
            shared_facts = json.load(f)
    except (json.JSONDecodeError, OSError):
        # Phase 2: CI/prod must have readable shared_facts
        if profile in ("ci", "prod"):
            sev = "blocker" if profile == "prod" else "error"
            return False, [
                {
                    "issue_id": "license_shared_facts_error",
                    "gate": "gate_license_consistency",
                    "severity": sev,
                    "message": "Error reading shared_facts.json — cannot validate license consistency",
                    "error_code": "LICENSE_SHARED_FACTS_ERROR",
                    "status": "OPEN",
                }
            ]
        return True, [
            {
                "issue_id": "license_shared_facts_error",
                "gate": "gate_license_consistency",
                "severity": "info",
                "message": "Error reading shared_facts.json, skipping license check",
                "error_code": "LICENSE_SHARED_FACTS_ERROR",
                "status": "OPEN",
            }
        ]

    # Check if license info exists
    license_info = shared_facts.get("license", {})
    canonical_spdx = (license_info.get("spdx_id", "") or "").strip()
    canonical_name = (license_info.get("name", "") or "").strip()

    if not canonical_spdx and not canonical_name:
        # Phase 2: In CI/prod, report that license info is absent
        if profile in ("ci", "prod"):
            return True, [
                {
                    "issue_id": "license_no_canonical",
                    "gate": "gate_license_consistency",
                    "severity": "warn",
                    "message": "shared_facts.json has no license information — license consistency not checked",
                    "error_code": "LICENSE_NO_CANONICAL",
                    "status": "OPEN",
                }
            ]
        return True, []  # Local: nothing to check

    canonical_lower = (canonical_spdx or canonical_name).lower()
    is_commercial = canonical_lower in _COMMERCIAL_SPDX_IDS

    # Scan markdown files
    site_dir = run_dir / "work" / "site"
    if not site_dir.exists():
        return True, []

    md_files = sorted(site_dir.rglob("*.md"))

    for md_file in md_files:
        try:
            content = md_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        # Check for license name contradictions
        for match in _LICENSE_NAMES_RE.finditer(content):
            mentioned = match.group(1).strip()
            if not _is_license_match(mentioned, canonical_spdx, canonical_name):
                severity = _escalate_severity("error", profile)
                issues.append({
                    "issue_id": f"license_contradiction_{md_file.stem}_{match.start()}",
                    "gate": "gate_license_consistency",
                    "severity": severity,
                    "message": (
                        f"Page mentions `{mentioned}` license but canonical is "
                        f"`{canonical_spdx or canonical_name}`"
                    ),
                    "error_code": "LICENSE_CONTRADICTION",
                    "location": {"path": str(md_file)},
                    "status": "OPEN",
                })

        # Check for "free/open-source" claims on commercial licenses
        if is_commercial:
            for match in _FREE_CLAIM_RE.finditer(content):
                severity = _escalate_severity("error", profile)
                issues.append({
                    "issue_id": f"license_free_claim_{md_file.stem}_{match.start()}",
                    "gate": "gate_license_consistency",
                    "severity": severity,
                    "message": (
                        f"Page claims `{match.group(0)}` but canonical license is "
                        f"`{canonical_spdx or canonical_name}` (commercial)"
                    ),
                    "error_code": "LICENSE_FREE_CLAIM_COMMERCIAL",
                    "location": {"path": str(md_file)},
                    "status": "OPEN",
                })

    gate_passed = not any(
        i.get("severity") in ("blocker", "error") for i in issues
    )
    return gate_passed, issues


def _is_license_match(mentioned: str, canonical_spdx: str, canonical_name: str) -> bool:
    """Check if a mentioned license matches the canonical license.

    Case-insensitive comparison with common alias handling.
    """
    mentioned_lower = mentioned.lower().strip()
    spdx_lower = canonical_spdx.lower().strip()
    name_lower = canonical_name.lower().strip()

    # Direct match
    if mentioned_lower == spdx_lower or mentioned_lower == name_lower:
        return True

    # Normalize Apache variations: "Apache 2.0", "Apache 2", "Apache"
    if "apache" in mentioned_lower and "apache" in (spdx_lower + name_lower):
        return True

    # Normalize GPL variations: "GPLv2", "GPLv3", "GPL"
    if mentioned_lower.startswith("gpl") and (spdx_lower.startswith("gpl") or name_lower.startswith("gpl")):
        return True

    return False


def _escalate_severity(base_severity: str, profile: str) -> str:
    """Escalate severity based on profile.

    prod: error -> blocker
    ci: error stays error
    local: error -> warn
    """
    if profile == "prod" and base_severity == "error":
        return "blocker"
    if profile == "local" and base_severity == "error":
        return "warn"
    return base_severity
