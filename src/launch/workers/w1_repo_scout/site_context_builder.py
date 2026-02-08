"""TC-1034: Site context builder for W1 RepoScout.

Builds the site_context.json artifact from run_config, resolved_refs, and
Hugo configuration discovery. The site context provides downstream workers
with repository references and Hugo configuration file metadata.

Algorithm:
1. Extract site and workflows repo refs from resolved_metadata
2. Scan for Hugo configuration files in the site repository
3. Build config_files list with path, sha256, bytes, ext
4. Derive build_matrix from subdomain roots in site_layout
5. Return SiteContext model

Spec references:
- specs/schemas/site_context.schema.json
- specs/21_worker_contracts.md:54-95 (W1 RepoScout contract)
- specs/10_determinism_and_caching.md (Deterministic serialization)

TC-1034: W1 Stub Artifact Enrichment
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from ...io.hashing import sha256_file
from ...models.site_context import (
    BuildMatrixEntry,
    HugoConfig,
    HugoConfigFile,
    RepoRef,
    SiteContext,
)

logger = logging.getLogger(__name__)

# Hugo configuration file names (in priority order per Hugo docs)
HUGO_CONFIG_FILENAMES = [
    "hugo.toml",
    "hugo.yaml",
    "hugo.yml",
    "hugo.json",
    "config.toml",
    "config.yaml",
    "config.yml",
    "config.json",
]

# Hugo config directory patterns
HUGO_CONFIG_DIR_PATTERNS = [
    "config",
    "config/_default",
]


def _discover_hugo_config_files(site_dir: Path) -> List[Dict[str, Any]]:
    """Discover Hugo configuration files in the site directory.

    Scans for standard Hugo config filenames at the root and in config/
    subdirectories per Hugo's configuration lookup order.

    Args:
        site_dir: Path to the site repository root.

    Returns:
        Sorted list of config file metadata dicts with keys:
        path, sha256, bytes, ext.
    """
    config_files: List[Dict[str, Any]] = []
    seen_paths: set = set()

    # Check root-level config files
    for filename in HUGO_CONFIG_FILENAMES:
        candidate = site_dir / filename
        if candidate.is_file():
            rel_path = filename
            if rel_path not in seen_paths:
                seen_paths.add(rel_path)
                config_files.append(_make_config_entry(candidate, rel_path))

    # Check config directory patterns
    for dir_pattern in HUGO_CONFIG_DIR_PATTERNS:
        config_dir = site_dir / dir_pattern
        if config_dir.is_dir():
            for child in sorted(config_dir.iterdir()):
                if child.is_file() and child.suffix in (".toml", ".yaml", ".yml", ".json"):
                    rel_path = str(child.relative_to(site_dir)).replace("\\", "/")
                    if rel_path not in seen_paths:
                        seen_paths.add(rel_path)
                        config_files.append(_make_config_entry(child, rel_path))

    # Sort deterministically by path
    config_files.sort(key=lambda x: x["path"])
    return config_files


def _make_config_entry(file_path: Path, rel_path: str) -> Dict[str, Any]:
    """Create a config file metadata entry.

    Args:
        file_path: Absolute path to the config file.
        rel_path: Relative path from site root (forward-slash separated).

    Returns:
        Dict with path, sha256, bytes, ext.
    """
    file_bytes = file_path.stat().st_size
    file_hash = sha256_file(file_path)
    ext = file_path.suffix  # e.g. ".toml"
    return {
        "path": rel_path,
        "sha256": file_hash,
        "bytes": file_bytes,
        "ext": ext,
    }


def _build_build_matrix(
    site_layout: Dict[str, Any],
    family: str,
) -> List[Dict[str, Any]]:
    """Derive the Hugo build matrix from site_layout subdomain roots.

    Each subdomain root in the site_layout maps to a build matrix entry
    identifying which subdomain + family combination is served from which
    config path.

    Args:
        site_layout: site_layout dict from run_config.
        family: Product family slug (e.g. "3d", "note").

    Returns:
        Sorted list of build matrix entry dicts.
    """
    matrix: List[Dict[str, Any]] = []
    subdomain_roots = site_layout.get("subdomain_roots", {})

    for section_name, root_path in sorted(subdomain_roots.items()):
        # Extract subdomain from root path pattern
        # e.g. "content/products.aspose.org" -> "products.aspose.org"
        root_normalized = root_path.replace("\\", "/")
        parts = root_normalized.split("/")
        subdomain = parts[-1] if parts else section_name

        matrix.append({
            "subdomain": subdomain,
            "family": family,
            "config_path": root_normalized,
        })

    matrix.sort(key=lambda x: (x["subdomain"], x["family"]))
    return matrix


def build_site_context(
    run_config_dict: Dict[str, Any],
    resolved_metadata: Dict[str, Any],
    site_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Build site context artifact from run_config and resolved metadata.

    Extracts repository references, discovers Hugo configuration files,
    and builds the site context for downstream workers.

    Args:
        run_config_dict: Run configuration dictionary.
        resolved_metadata: Resolved refs metadata from clone_inputs().
        site_dir: Optional path to cloned site repository. If None, Hugo
                  config discovery is skipped (returns empty config_files).

    Returns:
        Dictionary suitable for writing as site_context.json.
        Conforms to site_context.schema.json.
    """
    # Extract site repo reference
    site_meta = resolved_metadata.get("site", {})
    site_ref = RepoRef(
        repo_url=site_meta.get(
            "repo_url",
            run_config_dict.get("site_repo_url", "https://unknown.site"),
        ),
        requested_ref=site_meta.get(
            "requested_ref",
            run_config_dict.get("site_ref", "HEAD"),
        ),
        resolved_sha=site_meta.get("resolved_sha", "0000000000000000000000000000000000000000"),
        clone_path=site_meta.get("clone_path"),
    )

    # Extract workflows repo reference
    workflows_meta = resolved_metadata.get("workflows", {})
    workflows_ref = RepoRef(
        repo_url=workflows_meta.get(
            "repo_url",
            run_config_dict.get("workflows_repo_url", "https://unknown.workflows"),
        ),
        requested_ref=workflows_meta.get(
            "requested_ref",
            run_config_dict.get("workflows_ref", "HEAD"),
        ),
        resolved_sha=workflows_meta.get(
            "resolved_sha", "0000000000000000000000000000000000000000"
        ),
        clone_path=workflows_meta.get("clone_path"),
    )

    # Discover Hugo config files
    config_files_raw: List[Dict[str, Any]] = []
    config_root = "."
    if site_dir and site_dir.is_dir():
        config_files_raw = _discover_hugo_config_files(site_dir)
        # Determine config root (directory containing primary config)
        if config_files_raw:
            first_path = config_files_raw[0]["path"]
            if "/" in first_path:
                config_root = first_path.rsplit("/", 1)[0]
            else:
                config_root = "."
        else:
            config_root = "."
    else:
        config_root = run_config_dict.get("site_layout", {}).get("content_root", ".")

    config_files = [
        HugoConfigFile(
            path=cf["path"],
            sha256=cf["sha256"],
            bytes_=cf["bytes"],
            ext=cf["ext"],
        )
        for cf in config_files_raw
    ]

    # Build build matrix
    site_layout = run_config_dict.get("site_layout", {})
    family = run_config_dict.get("family", "unknown")
    build_matrix_raw = _build_build_matrix(site_layout, family)
    build_matrix = [
        BuildMatrixEntry(
            subdomain=bm["subdomain"],
            family=bm["family"],
            config_path=bm["config_path"],
        )
        for bm in build_matrix_raw
    ]

    hugo_config = HugoConfig(
        config_root=config_root,
        config_files=config_files,
        build_matrix=build_matrix,
    )

    context = SiteContext(
        schema_version="1.0",
        site=site_ref,
        workflows=workflows_ref,
        hugo=hugo_config,
    )

    return context.to_dict()
