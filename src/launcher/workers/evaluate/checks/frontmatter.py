"""Check 1: Frontmatter validation."""
from __future__ import annotations

import re

import yaml

from launcher.models.evaluation import Finding
from launcher.shared.page_skeletons import PAGE_ROLE_SKELETONS

_REQUIRED_FIELDS = {"title"}
_RECOMMENDED_FIELDS = {"description", "slug", "type", "url"}
_VALID_ROLES = set(PAGE_ROLE_SKELETONS.keys())


def check_frontmatter(content: str, slug: str) -> list[Finding]:
    """Validate Hugo YAML frontmatter."""
    findings: list[Finding] = []

    # Extract frontmatter
    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        findings.append(
            Finding(
                check="frontmatter",
                message="No frontmatter found",
                severity="critical",
                location=slug,
            )
        )
        return findings

    try:
        fm = yaml.safe_load(match.group(1))
    except yaml.YAMLError as e:
        findings.append(
            Finding(
                check="frontmatter",
                message=f"Invalid YAML: {e}",
                severity="critical",
                location=slug,
            )
        )
        return findings

    if not isinstance(fm, dict):
        findings.append(
            Finding(
                check="frontmatter",
                message="Frontmatter is not a dict",
                severity="critical",
                location=slug,
            )
        )
        return findings

    for field in sorted(_REQUIRED_FIELDS):
        if field not in fm or not fm[field]:
            findings.append(
                Finding(
                    check="frontmatter",
                    # TC-3882 Wave 4 (E10): [ENG] prefix for unambiguous engineering-only routing.
                    message=f"[ENG] Missing required field: {field}",
                    severity="high",
                    location=slug,
                )
            )

    for field in sorted(_RECOMMENDED_FIELDS):
        if field not in fm:
            findings.append(
                Finding(
                    check="frontmatter",
                    message=f"Missing recommended field: {field}",
                    severity="low",
                    location=slug,
                )
            )

    # Validate page_role against canonical skeleton registry
    role = fm.get("page_role")
    if not role:
        findings.append(
            Finding(
                check="frontmatter",
                # TC-3882 Wave 4 (E10): [ENG] prefix — missing page_role is a planner issue.
                message="[ENG] Missing page_role",
                severity="high",
                location=slug,
            )
        )
    elif role not in _VALID_ROLES:
        findings.append(
            Finding(
                check="frontmatter",
                # TC-3882 Wave 4 (E10): [ENG] prefix — unknown role is a config/planner issue.
                # Without [ENG], keyword match would incorrectly classify as llm_fixable.
                message=f"[ENG] Unknown page_role: {role}",
                severity="high",
                location=slug,
            )
        )

    return findings
