"""Drift detector — four deterministic passes comparing repo truth to knowledge baseline.

All functions are pure (no I/O side effects) except write_drift_baseline() which
writes a YAML file. No LLM calls anywhere in this module.

Pass 1 — SHA check: compare baseline SHA to current repo SHA.
Pass 2 — Claim staleness: verify evidence anchors still hold in the repo.
Pass 3 — New capabilities: detect API members / formats not in knowledge baseline.
Pass 4 — Code freshness: check live content pages for outdated imports/API calls.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml as _yaml
except ImportError:
    _yaml = None  # type: ignore[assignment]

from launcher.workers.verify.content_parser import (
    extract_api_calls,
    extract_code_blocks,
    extract_imports,
    normalize_import,
)

logger = logging.getLogger(__name__)

# -------------------------------------------------------------------------------
# Pass 1: SHA check
# -------------------------------------------------------------------------------


def pass1_sha_check(
    knowledge_dir: Path,
    current_repo_sha: str,
) -> tuple[bool, str]:
    """Compare current repo SHA to the baseline recorded in drift_baseline.yaml.

    Args:
        knowledge_dir: Path to ``knowledge/{family}/{platform}/``.
        current_repo_sha: Current HEAD commit SHA from the ScoutBundle.

    Returns:
        Tuple ``(is_clean, baseline_sha)``.
        ``is_clean`` is True when the baseline exists and its SHA matches the
        current SHA — meaning no drift is possible.
        ``baseline_sha`` is the SHA stored in the baseline, or ``""`` when no
        baseline exists.
    """
    baseline_path = knowledge_dir / "drift_baseline.yaml"
    if not baseline_path.exists():
        logger.debug("[Verify/P1] No drift_baseline.yaml — treating as new_product")
        return False, ""

    try:
        if _yaml is None:
            # Fall back to regex if yaml is unavailable
            text = baseline_path.read_text(encoding="utf-8")
            m = re.search(r"repo_sha_at_verify:\s*['\"]?(\w+)['\"]?", text)
            baseline_sha = m.group(1) if m else ""
        else:
            data = _yaml.safe_load(baseline_path.read_text(encoding="utf-8")) or {}
            baseline_sha = data.get("repo_sha_at_verify", "")
    except Exception as exc:
        logger.warning("[Verify/P1] Failed to read drift_baseline.yaml: %s", exc)
        return False, ""

    is_clean = bool(baseline_sha) and baseline_sha == current_repo_sha
    if is_clean:
        logger.debug("[Verify/P1] SHA unchanged (%s) — clean", current_repo_sha[:12])
    else:
        logger.debug(
            "[Verify/P1] SHA changed: baseline=%s current=%s",
            baseline_sha[:12] if baseline_sha else "none",
            current_repo_sha[:12],
        )
    return is_clean, baseline_sha


# -------------------------------------------------------------------------------
# Pass 2: Claim staleness
# -------------------------------------------------------------------------------


def pass2_claim_staleness(
    knowledge_dir: Path,
    clone_cache_dir: Path,
    current_file_tree: list[str],
) -> list[dict[str, Any]]:
    """Check claim evidence anchors against the current repo state.

    For each claim in ``knowledge/claims.json``:
    - If ``evidence[].source_file`` is not in ``current_file_tree`` →
      stale with reason ``"source_deleted"``.
    - If the file exists in the clone cache and the evidence anchor text
      (``snippet``) is no longer found in the file → stale with reason
      ``"evidence_changed"``.

    Args:
        knowledge_dir: Path to ``knowledge/{family}/{platform}/``.
        clone_cache_dir: Root of the intake clone cache (used to read source files).
        current_file_tree: Flat list of relative file paths in the current repo.

    Returns:
        List of stale claim dicts with keys ``claim_id``, ``reason``,
        ``affected_pages`` (always ``[]`` — pages are linked in pass4).
    """
    claims_path = knowledge_dir / "claims.json"
    if not claims_path.exists():
        logger.debug("[Verify/P2] No claims.json — skipping claim staleness check")
        return []

    try:
        claims = json.loads(claims_path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("[Verify/P2] Failed to read claims.json: %s", exc)
        return []

    current_tree_set = set(current_file_tree)
    stale: list[dict[str, Any]] = []

    for claim in claims:
        claim_id = claim.get("claim_id", "?")
        evidence_list = claim.get("evidence", [])
        for ev in evidence_list:
            if not isinstance(ev, dict):
                continue
            source_file = ev.get("source_file", "")
            if not source_file:
                continue

            # Check if source file still exists in the repo tree
            if source_file not in current_tree_set:
                stale.append({
                    "claim_id": claim_id,
                    "reason": "source_deleted",
                    "affected_pages": [],
                })
                logger.debug(
                    "[Verify/P2] Claim %s stale: source_deleted (%s)",
                    claim_id, source_file,
                )
                break  # one stale evidence is enough to mark the claim stale

            # Check if anchor text still present in file
            anchor_text = ev.get("snippet", "")
            if not anchor_text:
                continue

            # Try to read file from clone cache to verify anchor
            try:
                # clone_cache_dir may contain multiple repo dirs; find the right one
                # by looking for the source_file path in any subdirectory
                file_content = _read_from_clone_cache(clone_cache_dir, source_file)
                if file_content is not None and anchor_text not in file_content:
                    stale.append({
                        "claim_id": claim_id,
                        "reason": "evidence_changed",
                        "affected_pages": [],
                    })
                    logger.debug(
                        "[Verify/P2] Claim %s stale: evidence_changed (%s)",
                        claim_id, source_file,
                    )
                    break
            except Exception as exc:
                logger.debug(
                    "[Verify/P2] Cannot read %s from clone cache: %s", source_file, exc
                )

    logger.debug("[Verify/P2] Found %d stale claims", len(stale))
    return stale


def _read_from_clone_cache(clone_cache_dir: Path, relative_path: str) -> str | None:
    """Attempt to read a file from any repo subdirectory in the clone cache.

    Tries all first-level subdirectories of clone_cache_dir.  Returns the
    file content as a string, or None if not found.
    """
    if not clone_cache_dir.exists():
        return None
    for repo_dir in clone_cache_dir.iterdir():
        if not repo_dir.is_dir():
            continue
        candidate = repo_dir / relative_path
        if candidate.exists():
            try:
                return candidate.read_text(encoding="utf-8", errors="replace")
            except OSError:
                pass
    return None


# -------------------------------------------------------------------------------
# Pass 3: New capabilities
# -------------------------------------------------------------------------------


def pass3_new_capabilities(
    knowledge_dir: Path,
    current_api_surface: dict[str, Any],
    current_format_matrix: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Detect capabilities in the current repo not present in the knowledge baseline.

    Compares:
    - ``current_api_surface.import_allowlist`` vs ``knowledge/api_surface.json``
    - ``current_format_matrix`` vs ``knowledge/formats.md`` (parsed)

    Args:
        knowledge_dir: Path to ``knowledge/{family}/{platform}/``.
        current_api_surface: Current api_surface dict from ScoutBundle / understand.
        current_format_matrix: Current format_matrix list from the understand output.

    Returns:
        List of new capability dicts with keys ``kind``, ``identifier``,
        ``source_file``, ``suggested_page_roles``.
    """
    new_caps: list[dict[str, Any]] = []

    # --- API member comparison ---
    baseline_api_path = knowledge_dir / "api_surface.json"
    if baseline_api_path.exists():
        try:
            baseline_api = json.loads(baseline_api_path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning("[Verify/P3] Failed to read api_surface.json: %s", exc)
            baseline_api = {}
    else:
        baseline_api = {}

    current_identifiers: set[str] = set(current_api_surface.get("api_identifiers", []))
    current_imports: set[str] = set(current_api_surface.get("import_allowlist", []))
    baseline_imports: set[str] = set(baseline_api.get("import_allowlist", []))

    for new_import in sorted(current_imports - baseline_imports):
        new_caps.append({
            "kind": "api_member",
            "identifier": new_import,
            "source_file": "",
            "suggested_page_roles": ["api_reference", "workflow_page"],
        })
        logger.debug("[Verify/P3] New import: %s", new_import)

    # Also check for new public classes
    baseline_classes: set[str] = set(baseline_api.get("public_classes", []))
    current_classes: set[str] = set(current_api_surface.get("public_classes", []))
    for new_class in sorted(current_classes - baseline_classes):
        new_caps.append({
            "kind": "api_member",
            "identifier": new_class,
            "source_file": "",
            "suggested_page_roles": ["api_reference", "reference_object_page"],
        })
        logger.debug("[Verify/P3] New class: %s", new_class)

    # --- Format comparison ---
    baseline_formats = _parse_formats_md(knowledge_dir / "formats.md")
    for fmt in current_format_matrix:
        fmt_name = fmt.get("name", fmt.get("format", "")).upper()
        if fmt_name and fmt_name not in baseline_formats:
            new_caps.append({
                "kind": "format",
                "identifier": fmt_name,
                "source_file": "",
                "suggested_page_roles": ["workflow_page", "howto_article"],
            })
            logger.debug("[Verify/P3] New format: %s", fmt_name)

    logger.debug("[Verify/P3] Found %d new capabilities", len(new_caps))
    return new_caps


def _parse_formats_md(formats_path: Path) -> set[str]:
    """Extract format names from a knowledge/formats.md table.

    Returns a set of uppercase format names.
    """
    if not formats_path.exists():
        return set()
    formats: set[str] = set()
    try:
        for line in formats_path.read_text(encoding="utf-8").splitlines():
            if "|" in line and not line.strip().startswith("|---"):
                parts = [p.strip() for p in line.split("|")]
                if len(parts) >= 2 and parts[1] and not parts[1].startswith("Format"):
                    formats.add(parts[1].upper())
    except Exception as exc:
        logger.warning("[Verify/P3] Failed to parse formats.md: %s", exc)
    return formats


# -------------------------------------------------------------------------------
# Pass 4: Code freshness
# -------------------------------------------------------------------------------


def pass4_code_freshness(
    content_index_path: Path,
    content_repo_dir: Path,
    current_import_allowlist: list[str],
    current_api_identifiers: list[str],
) -> list[dict[str, Any]]:
    """Check live content pages for outdated imports and API calls.

    Reads each page listed in content_index.yaml with status=live,
    extracts code blocks, and checks:
    - Imports against ``current_import_allowlist``
    - API calls against ``current_api_identifiers``

    Args:
        content_index_path: Path to ``knowledge/content_index.yaml``.
        content_repo_dir: Root of the aspose.org/content repository.
        current_import_allowlist: Import strings from current api_surface.
        current_api_identifiers: API identifiers from current api_surface.

    Returns:
        List of outdated code example dicts with keys ``content_path``,
        ``page_role``, ``issues``.
    """
    if not content_index_path.exists():
        logger.debug("[Verify/P4] No content_index.yaml — skipping code freshness check")
        return []
    if not content_repo_dir.exists():
        logger.debug(
            "[Verify/P4] content_repo_dir not found (%s) — skipping", content_repo_dir
        )
        return []
    if _yaml is None:
        logger.debug("[Verify/P4] yaml unavailable — skipping code freshness check")
        return []

    try:
        index_data = _yaml.safe_load(content_index_path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        logger.warning("[Verify/P4] Failed to read content_index.yaml: %s", exc)
        return []

    pages = index_data.get("pages", [])
    import_set = set(current_import_allowlist)
    identifier_set = set(current_api_identifiers)
    outdated: list[dict[str, Any]] = []

    for page_entry in pages:
        if page_entry.get("status") != "live":
            continue
        content_path = page_entry.get("content_path", "")
        page_role = page_entry.get("page_role", "")
        md_file = content_repo_dir / (content_path + ".md")
        if not md_file.exists():
            continue

        try:
            md_text = md_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        blocks = extract_code_blocks(md_text)
        issues: list[dict[str, str]] = []

        for block in blocks:
            lang = block["language"]
            code = block["code"]

            # Check imports
            for stmt in extract_imports(code, lang):
                normalized = normalize_import(stmt, lang)
                if normalized and import_set and normalized not in import_set:
                    # Only flag if we have an allowlist to compare against
                    issues.append({
                        "issue_type": "outdated_import",
                        "old_value": stmt,
                        "new_value": "",
                    })

            # Check API calls (only when we have identifiers to compare)
            if identifier_set:
                for api_call in extract_api_calls(code, lang):
                    member = api_call.split(".", 1)[1] if "." in api_call else api_call
                    if api_call not in identifier_set and member not in identifier_set:
                        issues.append({
                            "issue_type": "outdated_api_call",
                            "old_value": api_call,
                            "new_value": "",
                        })

        if issues:
            outdated.append({
                "content_path": content_path,
                "page_role": page_role,
                "issues": issues,
            })
            logger.debug(
                "[Verify/P4] %s: %d issue(s)", content_path, len(issues)
            )

    logger.debug("[Verify/P4] Found %d pages with outdated code", len(outdated))
    return outdated


# -------------------------------------------------------------------------------
# Synthesis helpers
# -------------------------------------------------------------------------------


def compute_drift_status(
    baseline_exists: bool,
    stale_claims: list[dict[str, Any]],
    new_capabilities: list[dict[str, Any]],
    outdated_code: list[dict[str, Any]],
) -> str:
    """Derive the overall drift_status from pass findings.

    Rules:
    - ``new_product``: no baseline exists
    - ``major``: any stale claims or outdated code examples
    - ``minor``: only new capabilities, no stale claims
    - ``clean``: nothing detected (baseline SHA matched — should have been caught in pass1)

    Args:
        baseline_exists: True when a drift_baseline.yaml was found.
        stale_claims: Output of pass2.
        new_capabilities: Output of pass3.
        outdated_code: Output of pass4.

    Returns:
        One of ``"clean"``, ``"minor"``, ``"major"``, ``"new_product"``.
    """
    if not baseline_exists:
        return "new_product"
    if stale_claims or outdated_code:
        return "major"
    if new_capabilities:
        return "minor"
    return "clean"


def compute_page_drift_actions(
    content_index: dict[str, Any],
    stale_claims: list[dict[str, Any]],
    new_capabilities: list[dict[str, Any]],
    outdated_code: list[dict[str, Any]],
) -> dict[str, str]:
    """Decide per-page action based on drift findings.

    Decision tree per page:
    - ``create``:    page not in content_index with status=live
    - ``update``:    page has stale claims or outdated code examples
    - ``enhance``:   page is live + no stale claims + new capabilities exist
    - ``no-change``: page is live + no stale claims + no new capabilities

    Args:
        content_index: Loaded content_index.yaml data dict.
        stale_claims: Output of pass2.
        new_capabilities: Output of pass3.
        outdated_code: Output of pass4.

    Returns:
        Dict mapping content_path → action string.
    """
    # Build index of live pages
    live_pages: dict[str, dict[str, Any]] = {}
    for page_entry in content_index.get("pages", []):
        cp = page_entry.get("content_path", "")
        if cp and page_entry.get("status") == "live":
            live_pages[cp] = page_entry

    # Build set of pages with stale claims (via affected_pages or all live pages)
    stale_claim_pages: set[str] = set()
    for sc in stale_claims:
        for cp in sc.get("affected_pages", []):
            stale_claim_pages.add(cp)

    # Build set of pages with outdated code
    outdated_pages: set[str] = set()
    for oc in outdated_code:
        cp = oc.get("content_path", "")
        if cp:
            outdated_pages.add(cp)

    has_new_caps = bool(new_capabilities)
    actions: dict[str, str] = {}

    for cp, _entry in live_pages.items():
        if cp in stale_claim_pages or cp in outdated_pages:
            actions[cp] = "update"
        elif has_new_caps:
            actions[cp] = "enhance"
        else:
            actions[cp] = "no-change"

    return actions


def write_drift_baseline(
    knowledge_dir: Path,
    family: str,
    platform: str,
    repo_sha: str,
    claims: list[dict[str, Any]],
    format_matrix: list[dict[str, Any]],
) -> None:
    """Write drift_baseline.yaml to knowledge_dir for use in the next verify run.

    Fingerprints each claim (claim_id + evidence source_files) and each format
    (format name + can_import/can_export) so the next run can detect changes.

    Args:
        knowledge_dir: Path to ``knowledge/{family}/{platform}/``.
        family: Product family identifier.
        platform: Platform identifier.
        repo_sha: Current HEAD commit SHA.
        claims: List of claim dicts from claims.json.
        format_matrix: Current format_matrix from api_surface.
    """
    if _yaml is None:
        logger.debug("[Verify] yaml unavailable — skipping drift_baseline write")
        return

    import hashlib

    def _fp(text: str) -> str:
        return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]

    claim_fingerprints: dict[str, str] = {}
    for claim in claims:
        cid = claim.get("claim_id", "")
        text = claim.get("text", "")
        evidence_files = "|".join(
            str(ev.get("source_file", ""))
            for ev in claim.get("evidence", [])
            if isinstance(ev, dict)
        )
        claim_fingerprints[cid] = _fp(f"{text}|{evidence_files}")

    format_fingerprints: dict[str, str] = {}
    for fmt in format_matrix:
        name = fmt.get("name", fmt.get("format", "?")).upper()
        can_imp = str(fmt.get("can_import", False))
        can_exp = str(fmt.get("can_export", False))
        format_fingerprints[name] = _fp(f"{can_imp}|{can_exp}")

    baseline: dict[str, Any] = {
        "family": family,
        "platform": platform,
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "repo_sha_at_verify": repo_sha,
        "claim_fingerprints": claim_fingerprints,
        "format_fingerprints": format_fingerprints,
    }

    try:
        knowledge_dir.mkdir(parents=True, exist_ok=True)
        baseline_path = knowledge_dir / "drift_baseline.yaml"
        baseline_path.write_text(
            _yaml.dump(baseline, default_flow_style=False, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        logger.info("[Verify] Wrote drift_baseline.yaml → %s", baseline_path)
    except Exception as exc:
        logger.warning("[Verify] Failed to write drift_baseline.yaml: %s", exc)
