"""TC-1034: Frontmatter discovery builder for W1 RepoScout.

Scans discovered documentation files for YAML frontmatter blocks, extracts
field contracts per section (products, docs, reference, kb, blog), and
returns a typed FrontmatterContract model.

Algorithm:
1. Group discovered docs by section (subdomain root)
2. For each section, parse YAML frontmatter from markdown files
3. Compute required keys (present in all files), optional keys, key types
4. Return FrontmatterContract with section-level summaries

Spec references:
- specs/schemas/frontmatter_contract.schema.json
- specs/21_worker_contracts.md:54-95 (W1 RepoScout contract)
- specs/10_determinism_and_caching.md (Deterministic serialization)

TC-1034: W1 Stub Artifact Enrichment
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ...models.frontmatter import FrontmatterContract, SectionContract

logger = logging.getLogger(__name__)

# YAML frontmatter delimiter pattern
_FRONTMATTER_RE = re.compile(
    r"\A---\s*\n(.*?)\n---\s*\n",
    re.DOTALL,
)

# Known section names mapping from subdomain roots
SECTION_NAMES = ["blog", "docs", "kb", "products", "reference"]

# Standard Hugo/Aspose frontmatter fields
KNOWN_FRONTMATTER_FIELDS = {
    "title", "description", "weight", "url", "aliases",
    "type", "layout", "draft", "date", "lastmod",
    "tags", "categories", "keywords", "slug", "linktitle",
    "menu", "outputs", "cascade", "params",
}


def _infer_key_type(value: Any) -> str:
    """Infer the frontmatter key type from a parsed YAML value.

    Maps Python types to schema-compatible type strings per
    frontmatter_contract.schema.json#$defs/sectionContract/key_types.

    Args:
        value: A parsed YAML value.

    Returns:
        One of the valid key type strings.
    """
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        # Check if it looks like a date (YYYY-MM-DD or ISO 8601)
        if re.match(r"^\d{4}-\d{2}-\d{2}", value):
            return "date"
        return "string"
    if isinstance(value, list):
        if all(isinstance(item, str) for item in value):
            return "array_string"
        return "unknown"
    if isinstance(value, dict):
        return "object"
    return "unknown"


def _parse_yaml_frontmatter_simple(text: str) -> Optional[Dict[str, Any]]:
    """Parse YAML frontmatter from a markdown file using a simple line-based parser.

    This avoids external YAML library dependencies by parsing simple key-value
    pairs from frontmatter blocks. Handles:
    - String values (with or without quotes)
    - Boolean values (true/false)
    - Integer and float values
    - Simple list values (using [a, b, c] syntax or multi-line - item syntax)
    - Date values (YYYY-MM-DD format)

    Args:
        text: Full markdown file content.

    Returns:
        Dictionary of parsed frontmatter fields, or None if no frontmatter found.
    """
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return None

    frontmatter_block = match.group(1)
    result: Dict[str, Any] = {}
    current_key: Optional[str] = None
    current_list: Optional[List[str]] = None

    for line in frontmatter_block.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # Check for list continuation (- item)
        if current_key is not None and current_list is not None and stripped.startswith("- "):
            item = stripped[2:].strip().strip("'\"")
            current_list.append(item)
            continue
        else:
            # Flush any pending list
            if current_key is not None and current_list is not None:
                result[current_key] = current_list
                current_key = None
                current_list = None

        # Parse key: value lines
        colon_idx = stripped.find(":")
        if colon_idx < 1:
            continue

        key = stripped[:colon_idx].strip()
        value_str = stripped[colon_idx + 1:].strip()

        # Skip keys with dots or special chars (nested TOML-style)
        if "." in key or " " in key:
            continue

        if not value_str:
            # Could be start of a multi-line list or object
            current_key = key
            current_list = []
            continue

        # Parse the value
        value = _parse_simple_value(value_str)
        result[key] = value

    # Flush any trailing list
    if current_key is not None and current_list is not None:
        result[current_key] = current_list

    return result if result else None


def _parse_simple_value(value_str: str) -> Any:
    """Parse a simple YAML value string into a Python object.

    Args:
        value_str: The raw value string from YAML.

    Returns:
        Parsed Python value.
    """
    # Remove inline comments
    if " #" in value_str:
        value_str = value_str[:value_str.index(" #")].strip()

    # Quoted string
    if (value_str.startswith('"') and value_str.endswith('"')) or \
       (value_str.startswith("'") and value_str.endswith("'")):
        return value_str[1:-1]

    # Inline list [a, b, c]
    if value_str.startswith("[") and value_str.endswith("]"):
        inner = value_str[1:-1].strip()
        if not inner:
            return []
        items = [item.strip().strip("'\"") for item in inner.split(",")]
        return [item for item in items if item]

    # Boolean
    lower = value_str.lower()
    if lower == "true":
        return True
    if lower == "false":
        return False

    # Integer
    try:
        return int(value_str)
    except ValueError:
        pass

    # Float
    try:
        return float(value_str)
    except ValueError:
        pass

    # Date-like string (YYYY-MM-DD...)
    if re.match(r"^\d{4}-\d{2}-\d{2}", value_str):
        return value_str

    # Default: string
    return value_str


def _classify_section(
    file_path: str,
    site_layout: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """Classify a documentation file path into a section name.

    Uses the site_layout subdomain_roots to determine which section a file
    belongs to based on its path.

    Args:
        file_path: Relative file path (forward-slash separated).
        site_layout: site_layout dict from run_config (optional).

    Returns:
        Section name (e.g. "docs", "products") or None if unclassified.
    """
    normalized = file_path.replace("\\", "/").lower()

    # Try subdomain roots from site_layout
    if site_layout:
        subdomain_roots = site_layout.get("subdomain_roots", {})
        for section_name, root_path in sorted(subdomain_roots.items()):
            root_normalized = root_path.replace("\\", "/").lower()
            if normalized.startswith(root_normalized):
                return section_name

    # Fallback: infer from known subdomain patterns
    for section in SECTION_NAMES:
        if f"{section}.aspose." in normalized or f"/{section}/" in normalized:
            return section

    return None


def build_frontmatter_contract(
    repo_dir: Path,
    discovered_docs: Dict[str, Any],
    run_config_dict: Dict[str, Any],
    resolved_metadata: Dict[str, Any],
) -> Dict[str, Any]:
    """Build frontmatter contract by scanning discovered docs for YAML frontmatter.

    Scans all markdown files listed in discovered_docs, parses their YAML
    frontmatter, groups by section, and computes required/optional keys and
    key types per section.

    Args:
        repo_dir: Path to cloned repository root.
        discovered_docs: The discovered_docs.json artifact dict.
        run_config_dict: Run configuration dictionary (for site_layout).
        resolved_metadata: Resolved refs metadata (for site_repo_url + site_sha).

    Returns:
        Dictionary suitable for writing as frontmatter_contract.json.
        Conforms to frontmatter_contract.schema.json.
    """
    site_layout = run_config_dict.get("site_layout", {})
    site_repo_url = run_config_dict.get(
        "site_repo_url",
        resolved_metadata.get("site", {}).get("repo_url", "https://unknown.site"),
    )
    site_sha = resolved_metadata.get("site", {}).get(
        "resolved_sha",
        resolved_metadata.get("repo", {}).get("resolved_sha", "0000000"),
    )

    # Collect frontmatter per section
    section_frontmatters: Dict[str, List[Dict[str, Any]]] = {
        name: [] for name in SECTION_NAMES
    }

    # Get doc entrypoint details from discovered_docs
    # doc_entrypoint_details has dicts with "path" keys;
    # doc_entrypoints is a flat list of path strings.
    # Use doc_entrypoint_details if available, fall back to doc_entrypoints.
    doc_entries = discovered_docs.get("doc_entrypoint_details", [])
    if not doc_entries:
        doc_entries = discovered_docs.get("doc_entrypoints", [])

    for entry in doc_entries:
        # Handle both dict entries (doc_entrypoint_details) and string entries (doc_entrypoints)
        if isinstance(entry, dict):
            rel_path = entry.get("path", entry.get("relative_path", ""))
        else:
            rel_path = str(entry)
        if not rel_path:
            continue

        # Only process markdown files
        if not rel_path.lower().endswith((".md", ".markdown")):
            continue

        # Classify into section
        section = _classify_section(rel_path, site_layout)
        if section is None:
            continue

        # Read and parse frontmatter
        file_path = repo_dir / rel_path
        if not file_path.exists():
            continue

        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            logger.debug("Could not read %s, skipping", file_path)
            continue

        fm = _parse_yaml_frontmatter_simple(content)
        if fm:
            section_frontmatters[section].append(fm)

    # Build section contracts
    sections: Dict[str, SectionContract] = {}
    for section_name in SECTION_NAMES:
        fms = section_frontmatters[section_name]
        sections[section_name] = _build_section_contract(fms)

    contract = FrontmatterContract(
        schema_version="1.0",
        site_repo_url=site_repo_url,
        site_sha=site_sha,
        sections=sections,
    )

    return contract.to_dict()


def _build_section_contract(
    frontmatters: List[Dict[str, Any]],
) -> SectionContract:
    """Build a SectionContract from a list of parsed frontmatter dictionaries.

    Computes:
    - sample_size: number of files analyzed
    - required_keys: keys present in ALL files
    - optional_keys: keys present in SOME but not all files
    - key_types: inferred type for each key
    - default_values: most common value for optional keys (if deterministic)

    Args:
        frontmatters: List of parsed frontmatter dicts.

    Returns:
        SectionContract instance.
    """
    if not frontmatters:
        # Empty section - return minimal contract with standard Hugo fields
        return SectionContract(
            sample_size=1,
            required_keys=["title"],
            optional_keys=sorted(["description", "draft", "weight"]),
            key_types={
                "description": "string",
                "draft": "boolean",
                "title": "string",
                "weight": "integer",
            },
        )

    sample_size = len(frontmatters)

    # Count occurrences of each key
    key_counts: Dict[str, int] = {}
    key_type_votes: Dict[str, Dict[str, int]] = {}

    for fm in frontmatters:
        for key, value in fm.items():
            key_counts[key] = key_counts.get(key, 0) + 1
            inferred = _infer_key_type(value)
            if key not in key_type_votes:
                key_type_votes[key] = {}
            key_type_votes[key][inferred] = key_type_votes[key].get(inferred, 0) + 1

    # Determine required vs optional keys
    required_keys = sorted(
        k for k, count in key_counts.items() if count == sample_size
    )
    optional_keys = sorted(
        k for k, count in key_counts.items() if count < sample_size
    )

    # Determine key types (most common type wins)
    key_types: Dict[str, str] = {}
    for key in sorted(set(required_keys) | set(optional_keys)):
        if key in key_type_votes:
            votes = key_type_votes[key]
            # Pick the type with the most votes (deterministic tie-break: sorted)
            best_type = sorted(votes.items(), key=lambda x: (-x[1], x[0]))[0][0]
            key_types[key] = best_type

    return SectionContract(
        sample_size=sample_size,
        required_keys=required_keys,
        optional_keys=optional_keys,
        key_types=key_types,
    )
