"""Gate 5: Cross-Page Link Validity (TC-2830 upgrade).

Validates that all internal markdown links resolve to existing files.
TC-2830 extends to also check:
- Absolute internal links (/ paths) against a permalink index
- External link placeholders (example.com, localhost, TODO)
- Doubled path segments (/python/python/)

Per specs/09_validation_gates.md (Gate 6 Internal Links).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple
from urllib.parse import urlparse


# TC-2830: Placeholder domains that should never appear in published content
_PLACEHOLDER_DOMAINS = frozenset({
    "example.com", "example.org", "example.net",
    "localhost", "127.0.0.1", "0.0.0.0",
})

# TC-2830: Patterns in URLs that indicate placeholders
_PLACEHOLDER_URL_RE = re.compile(
    r'(?:TODO|FIXME|PLACEHOLDER|your-domain|your-api|change-me)',
    re.IGNORECASE,
)

# TC-2830: Doubled path segment pattern
_DOUBLED_SEGMENT_RE = re.compile(r'/([^/]+)/\1/')


def execute_gate(run_dir: Path, profile: str) -> Tuple[bool, List[Dict[str, Any]]]:
    """Execute Gate 5: Cross-Page Link Validity.

    Validates that all internal markdown links resolve to existing files.
    TC-2830: Also validates absolute links, placeholder URLs, and doubled paths.

    Args:
        run_dir: Run directory path
        profile: Validation profile (local, ci, prod)

    Returns:
        Tuple of (gate_passed, issues)
    """
    issues: List[Dict[str, Any]] = []

    # Find all markdown files
    site_dir = run_dir / "work" / "site"
    if not site_dir.exists():
        return True, []

    md_files = sorted(site_dir.rglob("*.md"))

    # TC-2830: Build permalink index from generated pages' frontmatter
    permalink_index = _build_permalink_index(md_files, site_dir)

    # Pattern to match markdown links: [text](url) or [text](url#anchor)
    link_pattern = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")

    for md_file in md_files:
        try:
            content = md_file.read_text(encoding="utf-8")

            # Skip code blocks
            lines = content.split("\n")
            in_code_block = False
            processed_content = []

            for line in lines:
                if line.strip().startswith("```"):
                    in_code_block = not in_code_block
                    continue
                if not in_code_block:
                    processed_content.append(line)

            content_no_code = "\n".join(processed_content)

            # Find all links
            for match in link_pattern.finditer(content_no_code):
                link_text = match.group(1)
                link_url = match.group(2)

                # Parse URL
                parsed = urlparse(link_url)

                # TC-2830: Check external links for placeholders
                if parsed.scheme in ["http", "https", "mailto", "ftp"]:
                    _check_external_link(
                        link_url, parsed, md_file, content, match, profile, issues
                    )
                    continue

                # TC-2830: Validate absolute internal links
                if link_url.startswith("/"):
                    _check_absolute_link(
                        link_url, md_file, content, match, profile,
                        permalink_index, issues,
                    )
                    continue

                # Extract path without anchor
                link_path = parsed.path
                if not link_path:
                    # Anchor-only link like #heading
                    continue

                # Resolve relative path (existing logic)
                try:
                    target_path = (md_file.parent / link_path).resolve()
                    target_exists = target_path.exists()

                    if not target_exists:
                        link_no_slash = link_path.rstrip("/")
                        if link_no_slash:
                            md_target = (md_file.parent / f"{link_no_slash}.md").resolve()
                            if md_target.exists():
                                target_exists = True
                            else:
                                index_target = (md_file.parent / link_no_slash / "_index.md").resolve()
                                if index_target.exists():
                                    target_exists = True
                                else:
                                    index_target = (md_file.parent / link_no_slash / "index.md").resolve()
                                    if index_target.exists():
                                        target_exists = True

                    if not target_exists:
                        line_num = content[: match.start()].count("\n") + 1
                        issues.append({
                            "issue_id": f"link_broken_{md_file.name}_{target_path.name}",
                            "gate": "gate_5_cross_page_link_validity",
                            "severity": "error",
                            "message": f"Broken internal link to '{link_path}' in {md_file.name}",
                            "error_code": "GATE_LINK_BROKEN_INTERNAL",
                            "location": {"path": str(md_file), "line": line_num},
                            "status": "OPEN",
                        })

                except Exception:
                    line_num = content[: match.start()].count("\n") + 1
                    issues.append({
                        "issue_id": f"link_invalid_{md_file.name}_{link_path}",
                        "gate": "gate_5_cross_page_link_validity",
                        "severity": "error",
                        "message": f"Invalid relative link '{link_path}' in {md_file.name}",
                        "error_code": "GATE_LINK_BROKEN_RELATIVE",
                        "location": {"path": str(md_file), "line": line_num},
                        "status": "OPEN",
                    })

        except Exception as e:
            issues.append({
                "issue_id": f"link_check_error_{md_file.name}",
                "gate": "gate_5_cross_page_link_validity",
                "severity": "error",
                "message": f"Error checking links in {md_file.name}: {e}",
                "error_code": "GATE_LINK_CHECK_ERROR",
                "location": {"path": str(md_file)},
                "status": "OPEN",
            })

    gate_passed = not any(
        issue["severity"] in ["blocker", "error"] for issue in issues
    )
    return gate_passed, issues


def _build_permalink_index(md_files: List[Path], site_dir: Path) -> Set[str]:
    """Build a set of known permalink paths from generated content.

    Reads frontmatter `url:` fields and also derives paths from filesystem.
    """
    permalinks: Set[str] = set()

    for md_file in md_files:
        # Derive path-based permalink from filesystem location
        try:
            rel = md_file.relative_to(site_dir)
            parts = list(rel.parts)
            # Remove "content" prefix if present
            if parts and parts[0] == "content":
                parts = parts[1:]
            # Remove filename, derive directory-based permalink
            if parts:
                if parts[-1] in ("_index.md", "index.md"):
                    parts = parts[:-1]
                elif parts[-1].endswith(".md"):
                    parts[-1] = parts[-1][:-3]
            permalink = "/" + "/".join(parts) + "/"
            permalinks.add(permalink.lower())
            # Also add without trailing slash
            permalinks.add(permalink.rstrip("/").lower())
        except ValueError:
            continue

        # Also try to read frontmatter url field
        try:
            text = md_file.read_text(encoding="utf-8", errors="replace")
            if text.startswith("---"):
                fm_end = text.find("\n---", 3)
                if fm_end > 0:
                    fm_text = text[3:fm_end]
                    for line in fm_text.splitlines():
                        line = line.strip()
                        if line.startswith("url:"):
                            url_val = line[4:].strip().strip("'\"")
                            if url_val:
                                permalinks.add(url_val.lower())
                                permalinks.add(url_val.rstrip("/").lower())
        except Exception:
            continue

    return permalinks


def _check_external_link(
    link_url: str,
    parsed: Any,
    md_file: Path,
    content: str,
    match: re.Match,
    profile: str,
    issues: List[Dict[str, Any]],
) -> None:
    """TC-2830: Check external links for placeholder patterns."""
    hostname = (parsed.hostname or "").lower()

    # Check placeholder domains
    if hostname in _PLACEHOLDER_DOMAINS:
        severity = "error" if profile != "local" else "warn"
        line_num = content[: match.start()].count("\n") + 1
        issues.append({
            "issue_id": f"link_placeholder_{md_file.name}_{line_num}",
            "gate": "gate_5_cross_page_link_validity",
            "severity": severity,
            "message": f"Placeholder URL '{link_url}' in {md_file.name}",
            "error_code": "GATE_LINK_PLACEHOLDER_URL",
            "location": {"path": str(md_file), "line": line_num},
            "status": "OPEN",
        })
        return

    # Check for placeholder keywords in URL
    if _PLACEHOLDER_URL_RE.search(link_url):
        severity = "warn"
        line_num = content[: match.start()].count("\n") + 1
        issues.append({
            "issue_id": f"link_placeholder_kw_{md_file.name}_{line_num}",
            "gate": "gate_5_cross_page_link_validity",
            "severity": severity,
            "message": f"URL contains placeholder keyword: '{link_url}' in {md_file.name}",
            "error_code": "GATE_LINK_PLACEHOLDER_KEYWORD",
            "location": {"path": str(md_file), "line": line_num},
            "status": "OPEN",
        })


def _check_absolute_link(
    link_url: str,
    md_file: Path,
    content: str,
    match: re.Match,
    profile: str,
    permalink_index: Set[str],
    issues: List[Dict[str, Any]],
) -> None:
    """TC-2830: Validate absolute internal links against permalink index."""
    # Strip anchor
    path = link_url.split("#")[0].split("?")[0]

    # Check for doubled path segments (e.g., /python/python/)
    doubled = _DOUBLED_SEGMENT_RE.search(path)
    if doubled:
        severity = "error" if profile != "local" else "warn"
        line_num = content[: match.start()].count("\n") + 1
        issues.append({
            "issue_id": f"link_doubled_{md_file.name}_{line_num}",
            "gate": "gate_5_cross_page_link_validity",
            "severity": severity,
            "message": f"Doubled path segment '{doubled.group(1)}' in '{link_url}'",
            "error_code": "GATE_LINK_DOUBLED_SEGMENT",
            "location": {"path": str(md_file), "line": line_num},
            "status": "OPEN",
        })
        return

    # Validate against permalink index (only if we have one)
    if not permalink_index:
        return  # No index built — skip validation

    path_lower = path.lower()
    if path_lower in permalink_index or path_lower.rstrip("/") in permalink_index:
        return  # Link resolves

    # Link doesn't resolve — emit warn (not error) since the index may be incomplete
    line_num = content[: match.start()].count("\n") + 1
    issues.append({
        "issue_id": f"link_abs_unresolved_{md_file.name}_{line_num}",
        "gate": "gate_5_cross_page_link_validity",
        "severity": "warn",
        "message": f"Absolute link '{link_url}' not found in permalink index",
        "error_code": "GATE_LINK_ABSOLUTE_UNRESOLVED",
        "location": {"path": str(md_file), "line": line_num},
        "status": "OPEN",
    })
