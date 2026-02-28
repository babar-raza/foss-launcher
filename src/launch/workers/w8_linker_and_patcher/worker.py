"""TC-450: W6 LinkerAndPatcher worker implementation.

This module implements the W6 LinkerAndPatcher that converts drafts into patches
and applies them to the site worktree deterministically.

W6 LinkerAndPatcher performs:
1. Load page_plan.json from TC-430 (W4 IAPlanner)
2. Load draft_manifest.json and draft files from TC-440 (W5 SectionWriter)
3. Generate patch bundle (create_file, update_by_anchor, update_frontmatter_keys)
4. Apply patches to site worktree (respecting allowed_paths)
5. Generate navigation files (_data/navigation.yml, _data/products.yml)
6. Emit events and write patch_bundle.json + diff_report.md

Output artifacts:
- patch_bundle.json (schema-validated per specs/schemas/patch_bundle.schema.json)
- diff_report.md (human-readable diff summary)
- Modified files in site worktree (tracked by git)

Spec references:
- specs/08_patch_engine.md (Patch application algorithm)
- specs/22_navigation_and_existing_content_update.md (Navigation updates)
- specs/21_worker_contracts.md:228-251 (W6 LinkerAndPatcher contract)
- specs/10_determinism_and_caching.md (Stable output requirements)
- specs/11_state_and_events.md (Event emission)

TC-450: W6 LinkerAndPatcher
"""

from __future__ import annotations

import datetime
import difflib
import fnmatch
import hashlib
import json
import re
import shutil
import uuid
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

from ...io.run_layout import RunLayout
from ...io.artifact_store import ArtifactStore
from ...models.event import (
    Event,
    EVENT_WORK_ITEM_STARTED,
    EVENT_WORK_ITEM_FINISHED,
    EVENT_ARTIFACT_WRITTEN,
    EVENT_ISSUE_OPENED,
    EVENT_RUN_FAILED,
)

# Patch engine telemetry events (specs/08_patch_engine.md:139).
# Defined locally because src/launch/models/ is owned by TC-250.
EVENT_PATCH_ENGINE_STARTED = "PATCH_ENGINE_STARTED"
EVENT_PATCH_ENGINE_COMPLETED = "PATCH_ENGINE_COMPLETED"
EVENT_PATCH_APPLIED = "PATCH_APPLIED"
EVENT_PATCH_SKIPPED = "PATCH_SKIPPED"
from ...io.atomic import atomic_write_json, atomic_write_text
from ...util.logging import get_logger
from .._shared.content_sanitizer import (
    absolutize_links,
    fix_code_fences,
    fix_inline_heading,
    fix_missing_space_after_period,
    fix_sentence_heading,
    strip_boilerplate_sentences,
    strip_pipeline_comments,
)

logger = get_logger()


class LinkerAndPatcherError(Exception):
    """Base exception for W6 LinkerAndPatcher errors."""
    pass


class LinkerNoDraftsError(LinkerAndPatcherError):
    """No drafts found in run directory."""
    pass


class LinkerPatchConflictError(LinkerAndPatcherError):
    """Patch application conflict detected."""
    pass


class LinkerAllowedPathsViolationError(LinkerAndPatcherError):
    """Patch targets file outside allowed_paths."""
    pass


class LinkerFrontmatterViolationError(LinkerAndPatcherError):
    """Patched file frontmatter violates schema."""
    pass


class LinkerWriteFailedError(LinkerAndPatcherError):
    """File system write failure."""
    pass


# Per specs/21_worker_contracts.md:1033 — patches applied by section order then path.
_SECTION_ORDER = {"products": 0, "docs": 1, "kb": 2, "reference": 3, "blog": 4}


def _section_index_from_path(output_path: str) -> int:
    """Extract section order index from an output_path.

    Detects section from subdomain in the path (e.g. docs.aspose.org → 1).
    Unknown sections sort last (index 99).
    """
    path_lower = output_path.replace("\\", "/").lower()
    for sec_name, sec_order in _SECTION_ORDER.items():
        if f"{sec_name}.aspose.org" in path_lower:
            return sec_order
    return 99


def emit_event(
    run_layout: RunLayout,
    run_id: str,
    trace_id: str,
    span_id: str,
    event_type: str,
    payload: Dict[str, Any],
) -> None:
    """Emit a single event to events.ndjson.

    TC-1033: Delegates to ArtifactStore.emit_event for centralized event emission.

    Args:
        run_layout: Run directory layout
        run_id: Run identifier
        trace_id: Trace ID for telemetry
        span_id: Span ID for telemetry
        event_type: Event type constant
        payload: Event payload dictionary
    """
    store = ArtifactStore(run_dir=run_layout.run_dir)
    store.emit_event(
        event_type,
        payload,
        run_id=run_id,
        trace_id=trace_id,
        span_id=span_id,
    )


def load_page_plan(artifacts_dir: Path) -> Dict[str, Any]:
    """Load page_plan.json from artifacts directory.

    TC-1033: Delegates to ArtifactStore.load_artifact for centralized I/O.

    Args:
        artifacts_dir: Path to artifacts directory

    Returns:
        Page plan dictionary

    Raises:
        LinkerAndPatcherError: If page_plan.json is missing or invalid
    """
    store = ArtifactStore(run_dir=artifacts_dir.parent)
    try:
        return store.load_artifact("page_plan.json", validate_schema=False)
    except FileNotFoundError:
        raise LinkerAndPatcherError(f"Missing required artifact: {artifacts_dir / 'page_plan.json'}")
    except json.JSONDecodeError as e:
        raise LinkerAndPatcherError(f"Invalid JSON in page_plan.json: {e}")


def load_draft_manifest(artifacts_dir: Path) -> Dict[str, Any]:
    """Load draft_manifest.json from artifacts directory.

    TC-1033: Delegates to ArtifactStore.load_artifact for centralized I/O.

    Args:
        artifacts_dir: Path to artifacts directory

    Returns:
        Draft manifest dictionary

    Raises:
        LinkerAndPatcherError: If draft_manifest.json is missing or invalid
    """
    store = ArtifactStore(run_dir=artifacts_dir.parent)
    try:
        return store.load_artifact("draft_manifest.json", validate_schema=False)
    except FileNotFoundError:
        raise LinkerAndPatcherError(f"Missing required artifact: {artifacts_dir / 'draft_manifest.json'}")
    except json.JSONDecodeError as e:
        raise LinkerAndPatcherError(f"Invalid JSON in draft_manifest.json: {e}")


def compute_content_hash(content: str) -> str:
    """Compute SHA256 hash of content for idempotency checks.

    Args:
        content: Content to hash

    Returns:
        Hex-encoded SHA256 hash
    """
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def validate_allowed_path(
    target_path: Path,
    site_worktree: Path,
    allowed_paths: Optional[List[str]] = None,
) -> bool:
    """Validate that target path is within allowed_paths.

    Per specs/08_patch_engine.md:116, patches must not write outside allowed_paths.

    Args:
        target_path: Target file path (absolute)
        site_worktree: Site worktree root (absolute)
        allowed_paths: List of allowed path patterns (relative to site root)

    Returns:
        True if path is allowed, False otherwise
    """
    if not allowed_paths:
        # If no restrictions, allow all paths within site_worktree
        try:
            target_path.relative_to(site_worktree)
            return True
        except ValueError:
            return False

    # Check if target_path is within any allowed pattern
    try:
        relative_path = target_path.relative_to(site_worktree)
    except ValueError:
        return False

    relative_str = str(relative_path).replace("\\", "/")

    for allowed_pattern in allowed_paths:
        # Normalize pattern to POSIX
        normalized_pattern = allowed_pattern.replace("\\", "/").rstrip("/")

        # If pattern has glob metacharacters, use fnmatch; otherwise prefix match
        if any(c in normalized_pattern for c in ("*", "?", "[")):
            if fnmatch.fnmatch(relative_str, normalized_pattern):
                return True
        else:
            if relative_str.startswith(normalized_pattern):
                return True

    return False


def parse_frontmatter(content: str) -> Tuple[Optional[str], str]:
    """Parse YAML frontmatter from markdown content.

    Args:
        content: Markdown content with optional frontmatter

    Returns:
        Tuple of (frontmatter_yaml, body_content)
        frontmatter_yaml is None if no frontmatter present
    """
    lines = content.split("\n")
    if not lines or lines[0].strip() != "---":
        return None, content

    # Find closing ---
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            frontmatter = "\n".join(lines[1:i])
            body = "\n".join(lines[i+1:])
            return frontmatter, body

    # No closing ---, treat as regular content
    return None, content


def update_frontmatter(
    content: str,
    updates: Dict[str, Any],
) -> str:
    """Update frontmatter keys in markdown content.

    Per specs/08_patch_engine.md:48-55, frontmatter updates are idempotent:
    - If key exists with same value → skip
    - If key exists with different value → update
    - If key does not exist → add

    Args:
        content: Markdown content with frontmatter
        updates: Dictionary of frontmatter key updates

    Returns:
        Updated markdown content
    """
    frontmatter_yaml, body = parse_frontmatter(content)

    if frontmatter_yaml is None:
        # No frontmatter, create new one
        import yaml
        new_frontmatter = yaml.dump(updates, default_flow_style=False, sort_keys=True)
        return f"---\n{new_frontmatter}---\n{body}"

    # Parse existing frontmatter
    import yaml
    try:
        frontmatter_dict = yaml.safe_load(frontmatter_yaml) or {}
    except yaml.YAMLError:
        # Invalid YAML, create new frontmatter
        frontmatter_dict = {}

    # Apply updates
    for key, value in updates.items():
        frontmatter_dict[key] = value

    # Serialize back
    new_frontmatter = yaml.dump(frontmatter_dict, default_flow_style=False, sort_keys=True)
    return f"---\n{new_frontmatter}---\n{body}"


def find_anchor_in_content(content: str, anchor: str) -> Optional[int]:
    """Find anchor heading in markdown content.

    Per specs/08_patch_engine.md:36-46, anchors are markdown headings.

    Args:
        content: Markdown content
        anchor: Heading text (e.g., "## Installation", "Installation")

    Returns:
        Line number (0-indexed) where anchor is found, or None if not found
    """
    lines = content.split("\n")

    # Normalize anchor (strip leading #)
    normalized_anchor = anchor.lstrip("#").strip()

    for i, line in enumerate(lines):
        # Check if line is a heading
        if line.strip().startswith("#"):
            # Extract heading text
            heading_text = re.sub(r"^#+\s*", "", line).strip()
            if heading_text == normalized_anchor:
                return i

    return None


def insert_content_at_anchor(
    content: str,
    anchor: str,
    new_content: str,
) -> str:
    """Insert content under an anchor heading.

    Per specs/08_patch_engine.md:36-46, content is inserted after the anchor heading.

    Args:
        content: Markdown content
        anchor: Heading text
        new_content: Content to insert

    Returns:
        Updated content

    Raises:
        LinkerPatchConflictError: If anchor not found
    """
    anchor_line = find_anchor_in_content(content, anchor)
    if anchor_line is None:
        raise LinkerPatchConflictError(f"Anchor not found: {anchor}")

    lines = content.split("\n")

    # Find the next heading or end of file
    next_heading_line = len(lines)
    for i in range(anchor_line + 1, len(lines)):
        if lines[i].strip().startswith("#"):
            next_heading_line = i
            break

    # Insert new content after anchor heading
    # Add blank line, then new content
    insert_position = anchor_line + 1
    new_lines = lines[:insert_position] + ["", new_content, ""] + lines[insert_position:]

    return "\n".join(new_lines)


def replace_content_under_anchor(
    content: str,
    anchor: str,
    new_content: str,
) -> str:
    """Replace content under an anchor heading.

    Replaces ALL content from the anchor heading until the next
    same-or-higher-level heading (or end of file).

    Per specs/08_patch_engine.md:36-46.

    Args:
        content: Markdown content
        anchor: Heading text (e.g., "## Installation" or "Installation")
        new_content: Replacement content for the section

    Returns:
        Updated content with section replaced

    Raises:
        LinkerPatchConflictError: If anchor not found
    """
    anchor_line = find_anchor_in_content(content, anchor)
    if anchor_line is None:
        raise LinkerPatchConflictError(f"Anchor not found: {anchor}")

    lines = content.split("\n")

    # Determine heading level of anchor
    anchor_heading = lines[anchor_line]
    anchor_level = len(anchor_heading) - len(anchor_heading.lstrip("#"))

    # Find the next heading at same or higher level (fewer or equal # chars)
    next_section_line = len(lines)
    for i in range(anchor_line + 1, len(lines)):
        stripped = lines[i].strip()
        if stripped.startswith("#"):
            heading_hashes = len(stripped) - len(stripped.lstrip("#"))
            if heading_hashes <= anchor_level:
                next_section_line = i
                break

    # Build result: keep anchor heading, replace everything between it
    # and the next section
    result_lines = (
        lines[:anchor_line + 1]
        + ["", new_content, ""]
        + lines[next_section_line:]
    )

    return "\n".join(result_lines)


def inject_see_also_section(
    content: str,
    related_pages: List[Dict[str, Any]],
    all_pages: List[Dict[str, Any]],
) -> str:
    """TC-1743: Inject 'See Also' section with related page links.

    Idempotent: if '## See Also' already exists, does not duplicate.

    Args:
        content: Draft markdown content.
        related_pages: List of {slug, section, overlap_score} from page_plan.
        all_pages: All pages for resolving titles and URLs.

    Returns:
        Content with See Also section appended (or unchanged if already present).
    """
    if not related_pages:
        return content

    # Idempotent: skip if already has See Also
    if "## See Also" in content or "## Related Pages" in content:
        return content

    # Build slug → page lookup
    slug_lookup = {p.get("slug", ""): p for p in all_pages}

    # TC-2103: Section-to-subdomain mapping for absolute URLs
    _section_subdomains = {
        "docs": "docs.aspose.org",
        "reference": "reference.aspose.org",
        "kb": "kb.aspose.org",
        "blog": "blog.aspose.org",
        "products": "products.aspose.org",
    }

    links = []
    for rp in related_pages:
        slug = rp.get("slug", "")
        page = slug_lookup.get(slug, {})
        title = page.get("title", slug.replace("-", " ").title())
        url = page.get("url_path", "")
        if url:
            # TC-2103: Absolutize relative URLs using target page's section
            section = page.get("section", "docs")
            subdomain = _section_subdomains.get(section, "docs.aspose.org")
            if url.startswith("/") and not url.startswith("http"):
                url = f"https://{subdomain}{url}"
            links.append(f"- [{title}]({url})")
        else:
            links.append(f"- {title}")

    if not links:
        return content

    see_also = "\n\n## See Also\n\n" + "\n".join(links) + "\n"
    return content.rstrip() + see_also


def _strip_forbidden_topic_headings(content: str, forbidden_topics: List[str]) -> str:
    """Remove markdown heading sections whose title contains a forbidden topic.

    TC-2356: Prevents Gate 14 FORBIDDEN_TOPIC errors caused by LLM non-determinism.
    Strips the heading line and all content until the next heading at the same or
    higher level (i.e. fewer or equal '#' characters).

    Args:
        content: Markdown page content.
        forbidden_topics: List of topic strings (e.g. ["installation"]).

    Returns:
        Content with forbidden-topic sections removed.
    """
    if not forbidden_topics:
        return content

    forbidden_lower = [t.lower().replace("_", " ") for t in forbidden_topics]
    lines = content.split("\n")
    result: List[str] = []
    skip_level: Optional[int] = None  # heading depth being skipped

    for line in lines:
        heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading_match:
            level = len(heading_match.group(1))
            heading_text = heading_match.group(2).lower()

            # If we were skipping, check whether this heading ends the skip
            if skip_level is not None and level <= skip_level:
                skip_level = None

            if skip_level is None:
                # Check whether this heading starts a forbidden section
                if any(f in heading_text for f in forbidden_lower):
                    skip_level = level
                    continue  # drop this heading line
                result.append(line)
        else:
            if skip_level is None:
                result.append(line)

    return "\n".join(result)


def _split_into_sections(body: str) -> Dict[str, str]:
    """Split markdown body into {heading_text: section_content} dict.

    Returns ordered dict of heading -> content-under-heading.
    Content before the first heading is keyed as "" (empty string).
    """
    sections: Dict[str, str] = {}
    current_heading = ""
    current_lines: List[str] = []

    for line in body.split("\n"):
        m = re.match(r"^(#{1,6})\s+(.+)$", line)
        if m:
            # Save previous section
            sections[current_heading] = "\n".join(current_lines)
            current_heading = m.group(2).strip()
            current_lines = []
        else:
            current_lines.append(line)

    # Save last section
    sections[current_heading] = "\n".join(current_lines)
    return sections


def _slugify(heading: str) -> str:
    """Create a short slug from a heading for use in patch_id."""
    return re.sub(r"[^a-z0-9]+", "_", heading.lower()).strip("_")[:30]


def _generate_update_patches_for_existing(
    existing_content: str,
    draft_content: str,
    page_id: str,
    output_path: str,
) -> List[Dict[str, Any]]:
    """Generate granular update patches for an existing file.

    Per specs/08_patch_engine.md:17-23:
    1. If only frontmatter differs: emit update_frontmatter_keys
    2. If body sections differ: emit update_by_anchor per changed section
    3. If no headings in draft: fall back to update_file_range for entire body

    Args:
        existing_content: Current content of the target file
        draft_content: New content from the draft
        page_id: Page identifier for patch_id generation
        output_path: Target file path

    Returns:
        List of patch dictionaries
    """
    import yaml as _yaml

    patches: List[Dict[str, Any]] = []

    existing_fm_yaml, existing_body = parse_frontmatter(existing_content)
    draft_fm_yaml, draft_body = parse_frontmatter(draft_content)

    # Step 1: Frontmatter diff
    if draft_fm_yaml is not None:
        existing_fm = {}
        draft_fm = {}
        try:
            existing_fm = _yaml.safe_load(existing_fm_yaml or "") or {}
        except Exception:
            pass
        try:
            draft_fm = _yaml.safe_load(draft_fm_yaml) or {}
        except Exception:
            pass

        fm_updates = {
            k: v for k, v in draft_fm.items()
            if existing_fm.get(k) != v
        }
        if fm_updates:
            patches.append({
                "patch_id": f"update_fm_{page_id}",
                "type": "update_frontmatter_keys",
                "path": output_path,
                "frontmatter_updates": fm_updates,
                "content_hash": compute_content_hash(draft_content),
            })

    # Step 2: Body diff by sections
    existing_sections = _split_into_sections(existing_body)
    draft_sections = _split_into_sections(draft_body)

    # Filter out preamble key "" — only process named headings
    named_draft_sections = {k: v for k, v in draft_sections.items() if k}

    if named_draft_sections:
        for heading, section_content in named_draft_sections.items():
            existing_section = existing_sections.get(heading)
            if existing_section is not None:
                # Heading exists in both files — update via anchor if content changed
                if existing_section.strip() != section_content.strip():
                    patches.append({
                        "patch_id": f"update_anchor_{page_id}_{_slugify(heading)}",
                        "type": "update_by_anchor",
                        "path": output_path,
                        "anchor": heading,
                        "new_content": section_content,
                        "content_hash": compute_content_hash(section_content),
                    })
            else:
                # New heading not in existing file — append at end via
                # update_file_range to avoid LinkerPatchConflictError from
                # replace_content_under_anchor (anchor not found).
                existing_lines = existing_content.split("\n")
                total_lines = len(existing_lines)
                # Determine heading level from draft sections
                draft_lines = draft_body.split("\n")
                heading_prefix = "## "
                for dl in draft_lines:
                    stripped = dl.strip()
                    if stripped.lstrip("#").strip() == heading:
                        heading_prefix = stripped[: len(stripped) - len(stripped.lstrip("#"))] + " "
                        break
                append_content = f"\n{heading_prefix}{heading}\n\n{section_content}"
                patches.append({
                    "patch_id": f"append_{page_id}_{_slugify(heading)}",
                    "type": "update_file_range",
                    "path": output_path,
                    "start_line": total_lines,
                    "end_line": total_lines,
                    "new_content": append_content,
                    "content_hash": compute_content_hash(append_content),
                })
    else:
        # No headings in draft body — fall back to update_file_range
        existing_lines = existing_content.split("\n")
        fm_line_count = len(existing_lines) - len(existing_body.split("\n"))
        body_line_count = len(existing_body.split("\n"))
        if body_line_count > 0:
            patches.append({
                "patch_id": f"update_range_{page_id}",
                "type": "update_file_range",
                "path": output_path,
                "start_line": fm_line_count + 1,
                "end_line": fm_line_count + body_line_count,
                "new_content": draft_body,
                "content_hash": compute_content_hash(draft_body),
            })

    return patches


def generate_patches_from_drafts(
    draft_manifest: Dict[str, Any],
    page_plan: Dict[str, Any],
    run_dir: Path,
    site_worktree: Path,
    family: str = "",
    platform: str = "",
) -> List[Dict[str, Any]]:
    """Generate patch bundle from draft files.

    Per specs/08_patch_engine.md:6-23, patch types:
    - create_file: New page that doesn't exist
    - update_by_anchor: Add content to existing page under heading
    - update_frontmatter_keys: Update frontmatter keys

    Args:
        draft_manifest: Draft manifest dictionary
        page_plan: Page plan dictionary
        run_dir: Run directory path
        site_worktree: Site worktree path

    Returns:
        List of patch dictionaries
    """
    patches = []
    drafts = draft_manifest.get("drafts", [])

    # Sort drafts deterministically per specs/21_worker_contracts.md:1033
    # Section order first, then output_path within section
    drafts_sorted = sorted(
        drafts,
        key=lambda d: (_section_index_from_path(d["output_path"]), d["output_path"]),
    )

    # TC-1743: Build page lookup for See Also injection
    # TC-2356: Key by output_path (unique) to avoid slug collisions across sections
    #          (all _index.md pages share slug "index" but have distinct output_paths)
    all_pages = page_plan.get("pages", [])
    slug_to_page = {p.get("slug", ""): p for p in all_pages}  # fallback: last wins
    path_to_page = {p.get("output_path", ""): p for p in all_pages}  # preferred: unique

    for draft_entry in drafts_sorted:
        output_path = draft_entry["output_path"]
        draft_path = run_dir / draft_entry["draft_path"]

        # Read draft content
        if not draft_path.exists():
            logger.warning(f"[W6 LinkerAndPatcher] Draft file not found: {draft_path}")
            continue

        with open(draft_path, "r", encoding="utf-8") as f:
            draft_content = f.read()

        # TC-2356: Absolutize relative links using output_path for section detection.
        # output_path contains the site-relative path (e.g. content/docs.aspose.org/...)
        # so section detection is reliable here (unlike draft paths which lack subdomain).
        _section = "default"
        output_path_lower = output_path.replace("\\", "/")
        for _sec in ("docs", "reference", "kb", "blog", "products"):
            if f"{_sec}.aspose.org" in output_path_lower:
                _section = _sec
                break
        # Fix broken code fences (W7 auto-fixes can introduce new fence issues)
        try:
            draft_content = fix_code_fences(draft_content)
        except Exception as _fcf_exc:
            logger.warning("[W8] fix_code_fences failed for %s: %s", output_path, _fcf_exc)

        # Fix inline headings (W7 LLM can introduce text.## Heading patterns)
        try:
            draft_content = fix_inline_heading(draft_content)
            draft_content = fix_sentence_heading(draft_content)
            draft_content = fix_missing_space_after_period(draft_content)
        except Exception as _fih_exc:
            logger.warning("[W8] fix_inline/sentence_heading failed for %s: %s", output_path, _fih_exc)

        # Strip generic boilerplate filler text injected by W7 auto-fixes
        try:
            draft_content = strip_boilerplate_sentences(draft_content)
        except Exception as _sbs_exc:
            logger.warning("[W8] strip_boilerplate_sentences failed for %s: %s", output_path, _sbs_exc)

        try:
            draft_content = absolutize_links(draft_content, _section, family, platform)
        except Exception as _abs_exc:
            logger.warning("[W8] absolutize_links failed for %s: %s", output_path, _abs_exc)

        # TC-2356: Strip any remaining W7 pipeline review comments before patching
        try:
            draft_content = strip_pipeline_comments(draft_content)
        except Exception as _spc_exc:
            logger.warning("[W8] strip_pipeline_comments failed for %s: %s", output_path, _spc_exc)

        # TC-2356: Strip forbidden-topic heading sections before patching
        # Use output_path as primary key to avoid slug collisions (all _index.md = "index")
        draft_slug = draft_entry.get("slug", "")
        page_spec = path_to_page.get(output_path, slug_to_page.get(draft_slug, {}))
        forbidden = page_spec.get("content_strategy", {}).get("forbidden_topics", [])
        if forbidden:
            draft_content = _strip_forbidden_topic_headings(draft_content, forbidden)

        # TC-1743: Inject See Also section from related_pages
        related_pages = page_spec.get("related_pages", [])
        if related_pages:
            draft_content = inject_see_also_section(draft_content, related_pages, all_pages)

        # Compute target path in site worktree
        target_path = site_worktree / output_path

        # Generate patch based on whether file exists
        if not target_path.exists():
            # create_file patch
            patch = {
                "patch_id": f"create_{draft_entry['page_id']}",
                "type": "create_file",
                "path": output_path,
                "new_content": draft_content,
                "content_hash": compute_content_hash(draft_content),
            }
            patches.append(patch)
        else:
            # File exists — generate granular update patches
            # Per specs/08_patch_engine.md:17-23: prefer anchor > frontmatter > range

            # Read existing content
            with open(target_path, "r", encoding="utf-8") as f:
                existing_content = f.read()

            # Check if content already matches (idempotency)
            if compute_content_hash(existing_content) == compute_content_hash(draft_content):
                logger.info(f"[W8 LinkerAndPatcher] Content unchanged, skipping: {output_path}")
                continue

            # Generate granular patches (anchor + frontmatter + range fallback)
            update_patches = _generate_update_patches_for_existing(
                existing_content=existing_content,
                draft_content=draft_content,
                page_id=draft_entry["page_id"],
                output_path=output_path,
            )
            patches.extend(update_patches)

    # TC-1764: Generate delete_file patches for deleted pages (incremental mode)
    for page_spec in all_pages:
        if page_spec.get("page_status") == "deleted":
            output_path = page_spec.get("output_path", "")
            if not output_path:
                continue
            target_path = site_worktree / output_path
            if target_path.exists():
                # Read existing content for content_hash (schema requires it on all patches)
                with open(target_path, "r", encoding="utf-8") as f:
                    _del_content = f.read()
                page_id = f"{page_spec.get('section', 'unknown')}/{page_spec.get('slug', 'unknown')}"
                patch = {
                    "patch_id": f"delete_{page_id}",
                    "type": "delete_file",
                    "path": output_path,
                    "content_hash": compute_content_hash(_del_content),
                }
                patches.append(patch)
                logger.info(
                    f"[W6 LinkerAndPatcher] Generated delete patch for: {output_path}"
                )

    return patches


def _patch_type_priority(patch: Dict[str, Any]) -> int:
    """Return sort priority for deterministic patch application order.

    Lower number = applied first. Ordering prevents line-range OOB errors
    caused by applying content-shrinking patches (update_by_anchor) before
    line-range-based patches that were computed on the original file.

    Priority:
      0: create_file       — must exist before updates
      1: update_frontmatter_keys — safe: only frontmatter block
      2: update_file_range (append_*) — appends at computed end; safe before shrinks
      3: update_by_anchor  — can shrink content (may invalidate range patches)
      4: update_file_range (update_range_*) — positional: applied last to avoid OOB
      5: delete_file       — applied last
      99: unknown          — sort last

    TC-3520: Rationale: update_by_anchor can shrink content when it replaces
    a long section with a shorter one. append_ patches use line numbers computed
    from the original file. By applying append_ patches before update_by_anchor,
    we avoid the situation where update_by_anchor shortens the file, then the
    append_ patch's end_line > len(lines).
    """
    patch_type = patch.get("type", "")
    patch_id = patch.get("patch_id", "")

    if patch_type == "create_file":
        return 0
    elif patch_type == "update_frontmatter_keys":
        return 1
    elif patch_type == "update_file_range" and patch_id.startswith("append_"):
        return 2
    elif patch_type == "update_by_anchor":
        return 3
    elif patch_type == "update_file_range":
        return 4
    elif patch_type == "delete_file":
        return 5
    return 99


def apply_patch(
    patch: Dict[str, Any],
    site_worktree: Path,
    allowed_paths: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Apply a single patch to the site worktree.

    Per specs/08_patch_engine.md:25-70, patches must be applied idempotently
    with conflict detection.

    Args:
        patch: Patch dictionary
        site_worktree: Site worktree path
        allowed_paths: List of allowed path patterns

    Returns:
        Application result dictionary with:
        - status: "applied", "skipped", "conflict"
        - reason: Human-readable reason

    Raises:
        LinkerAllowedPathsViolationError: If path outside allowed_paths
        LinkerPatchConflictError: If patch conflicts with existing content
        LinkerWriteFailedError: If write operation fails
    """
    patch_type = patch["type"]
    path = patch["path"]
    target_path = site_worktree / path

    # Validate allowed paths
    if not validate_allowed_path(target_path, site_worktree, allowed_paths):
        raise LinkerAllowedPathsViolationError(
            f"Patch target outside allowed_paths: {path}"
        )

    # Handle different patch types
    if patch_type == "create_file":
        return _apply_create_file_patch(patch, target_path)
    elif patch_type == "update_by_anchor":
        return _apply_update_by_anchor_patch(patch, target_path)
    elif patch_type == "update_frontmatter_keys":
        return _apply_update_frontmatter_patch(patch, target_path)
    elif patch_type == "update_file_range":
        return _apply_update_file_range_patch(patch, target_path)
    elif patch_type == "delete_file":
        return _apply_delete_file_patch(patch, target_path)
    else:
        raise LinkerAndPatcherError(f"Unknown patch type: {patch_type}")


def _apply_create_file_patch(
    patch: Dict[str, Any],
    target_path: Path,
) -> Dict[str, Any]:
    """Apply create_file patch.

    Per specs/08_patch_engine.md:57-62:
    - If file exists and content_hash matches → skip (idempotent)
    - If file exists and content_hash differs → conflict
    - If file not exists → create

    Args:
        patch: Patch dictionary
        target_path: Target file path

    Returns:
        Application result dictionary
    """
    new_content = patch["new_content"]
    expected_hash = patch.get("expected_before_hash")
    content_hash = patch["content_hash"]

    if target_path.exists():
        # Check if content already matches
        with open(target_path, "r", encoding="utf-8") as f:
            existing_content = f.read()

        existing_hash = compute_content_hash(existing_content)

        if existing_hash == content_hash:
            # Already applied (idempotent)
            return {
                "status": "skipped",
                "reason": "Content already matches (idempotent)",
            }

        # Check expected_before_hash if provided
        if expected_hash and existing_hash != expected_hash:
            raise LinkerPatchConflictError(
                f"Content mismatch at {target_path}: expected {expected_hash}, got {existing_hash}"
            )

    # Create/update file
    try:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        return {
            "status": "applied",
            "reason": "File created/updated successfully",
        }
    except OSError as e:
        raise LinkerWriteFailedError(f"Failed to write {target_path}: {e}")


def _apply_delete_file_patch(
    patch: Dict[str, Any],
    target_path: Path,
) -> Dict[str, Any]:
    """Apply delete_file patch (TC-1764: incremental mode).

    Removes a file that was deleted in incremental mode (all claims deprecated).

    Args:
        patch: Patch dictionary
        target_path: Target file path

    Returns:
        Application result dictionary
    """
    if not target_path.exists():
        return {
            "status": "skipped",
            "reason": f"File already absent: {patch['path']}",
        }

    try:
        target_path.unlink()
        logger.info(f"[W6 LinkerAndPatcher] Deleted file: {target_path}")
        return {
            "status": "applied",
            "reason": f"Deleted: {patch['path']}",
        }
    except OSError as e:
        raise LinkerWriteFailedError(f"Failed to delete {target_path}: {e}")


def _apply_update_by_anchor_patch(
    patch: Dict[str, Any],
    target_path: Path,
) -> Dict[str, Any]:
    """Apply update_by_anchor patch.

    Per specs/08_patch_engine.md:36-46, insert content under anchor heading.

    Args:
        patch: Patch dictionary
        target_path: Target file path

    Returns:
        Application result dictionary
    """
    if not target_path.exists():
        raise LinkerPatchConflictError(f"Target file not found: {target_path}")

    anchor = patch["anchor"]
    new_content = patch["new_content"]

    # Read existing content
    with open(target_path, "r", encoding="utf-8") as f:
        existing_content = f.read()

    # Check if content already present (fuzzy match for idempotency)
    if new_content.strip() in existing_content:
        return {
            "status": "skipped",
            "reason": "Content already present under anchor (idempotent)",
        }

    # Replace content under anchor (spec 08:36-46: replace, not insert)
    try:
        updated_content = replace_content_under_anchor(existing_content, anchor, new_content)

        with open(target_path, "w", encoding="utf-8") as f:
            f.write(updated_content)

        return {
            "status": "applied",
            "reason": f"Content replaced under anchor: {anchor}",
        }
    except LinkerPatchConflictError:
        raise
    except OSError as e:
        raise LinkerWriteFailedError(f"Failed to write {target_path}: {e}")


def _apply_update_frontmatter_patch(
    patch: Dict[str, Any],
    target_path: Path,
) -> Dict[str, Any]:
    """Apply update_frontmatter_keys patch.

    Per specs/08_patch_engine.md:48-55, update frontmatter keys idempotently.

    Args:
        patch: Patch dictionary
        target_path: Target file path

    Returns:
        Application result dictionary
    """
    if not target_path.exists():
        raise LinkerPatchConflictError(f"Target file not found: {target_path}")

    frontmatter_updates = patch["frontmatter_updates"]

    # Read existing content
    with open(target_path, "r", encoding="utf-8") as f:
        existing_content = f.read()

    # Update frontmatter
    try:
        updated_content = update_frontmatter(existing_content, frontmatter_updates)

        # Check if anything changed
        if updated_content == existing_content:
            return {
                "status": "skipped",
                "reason": "Frontmatter already up-to-date (idempotent)",
            }

        with open(target_path, "w", encoding="utf-8") as f:
            f.write(updated_content)

        return {
            "status": "applied",
            "reason": f"Frontmatter keys updated: {list(frontmatter_updates.keys())}",
        }
    except OSError as e:
        raise LinkerWriteFailedError(f"Failed to write {target_path}: {e}")


def _apply_update_file_range_patch(
    patch: Dict[str, Any],
    target_path: Path,
) -> Dict[str, Any]:
    """Apply update_file_range patch.

    Per specs/08_patch_engine.md:20, replace line range in file.

    Args:
        patch: Patch dictionary
        target_path: Target file path

    Returns:
        Application result dictionary
    """
    if not target_path.exists():
        raise LinkerPatchConflictError(f"Target file not found: {target_path}")

    start_line = patch["start_line"]  # 1-indexed
    end_line = patch["end_line"]  # 1-indexed
    new_content = patch["new_content"]

    # Read existing content
    with open(target_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # TC-3520: Clamp append_ patches that exceed current file length.
    # This can happen when update_by_anchor ran first and shortened the file,
    # making the original end_line stale. For append-style patches, we treat
    # an out-of-bounds end_line as "append at end of file".
    patch_id = patch.get("patch_id", "")
    if patch_id.startswith("append_") and end_line > len(lines):
        logger.debug(
            "[W8] Clamping append patch %s: end_line=%d > file_len=%d — appending at EOF",
            patch_id, end_line, len(lines),
        )
        # Append at end of file (ignore stale line numbers)
        new_lines = lines + [new_content + "\n"]
        try:
            with open(target_path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
            return {
                "status": "applied",
                "reason": f"Append patch clamped to EOF (was line {patch['end_line']})",
            }
        except OSError as e:
            raise LinkerWriteFailedError(f"Failed to write {target_path}: {e}")

    # Validate line range
    if start_line < 1 or end_line > len(lines):
        raise LinkerPatchConflictError(
            f"Line range out of bounds: {start_line}-{end_line} (file has {len(lines)} lines)"
        )

    # Replace line range (convert to 0-indexed)
    new_lines = (
        lines[:start_line - 1] +
        [new_content + "\n"] +
        lines[end_line:]
    )

    # Write updated content
    try:
        with open(target_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)

        return {
            "status": "applied",
            "reason": f"Lines {start_line}-{end_line} updated",
        }
    except OSError as e:
        raise LinkerWriteFailedError(f"Failed to write {target_path}: {e}")


def generate_diff_report(
    patches: List[Dict[str, Any]],
    patch_results: List[Dict[str, Any]],
    site_worktree: Path,
) -> str:
    """Generate human-readable diff report.

    Per specs/21_worker_contracts.md:240, generate diff_report.md.

    Args:
        patches: List of patches
        patch_results: List of application results
        site_worktree: Site worktree path

    Returns:
        Markdown diff report
    """
    lines = [
        "# Patch Application Report",
        "",
        f"**Total Patches**: {len(patches)}",
        f"**Applied**: {sum(1 for r in patch_results if r['status'] == 'applied')}",
        f"**Skipped**: {sum(1 for r in patch_results if r['status'] == 'skipped')}",
        f"**Conflicts**: {sum(1 for r in patch_results if r['status'] == 'conflict')}",
        "",
        "## Patch Details",
        "",
    ]

    for patch, result in zip(patches, patch_results):
        patch_id = patch["patch_id"]
        patch_type = patch["type"]
        path = patch["path"]
        status = result["status"]
        reason = result["reason"]

        lines.append(f"### {patch_id}")
        lines.append(f"- **Type**: {patch_type}")
        lines.append(f"- **Path**: {path}")
        lines.append(f"- **Status**: {status}")
        lines.append(f"- **Reason**: {reason}")
        lines.append("")

    return "\n".join(lines)


# Module-level cache for patch_bundle schema (GAP-05: avoid re-reading per call)
_PATCH_BUNDLE_SCHEMA: Optional[Dict[str, Any]] = None


def _get_patch_bundle_schema() -> Optional[Dict[str, Any]]:
    """Return cached patch_bundle schema, loading from disk on first call."""
    global _PATCH_BUNDLE_SCHEMA
    if _PATCH_BUNDLE_SCHEMA is not None:
        return _PATCH_BUNDLE_SCHEMA
    schema_path = (
        Path(__file__).resolve().parents[4]
        / "specs" / "schemas" / "patch_bundle.schema.json"
    )
    if not schema_path.exists():
        logger.warning(f"[W8] Schema file not found: {schema_path} -- validation skipped")
        return None
    _PATCH_BUNDLE_SCHEMA = json.loads(schema_path.read_text(encoding="utf-8"))
    return _PATCH_BUNDLE_SCHEMA


def _validate_patch_bundle(patch_bundle: Dict[str, Any]) -> None:
    """Validate patch_bundle against patch_bundle.schema.json.

    Uses jsonschema if available; logs warning and skips if not.
    On validation failure, raises LinkerPatchConflictError (fail-fast).
    The caller should write the bundle artifact BEFORE calling this so
    the artifact remains available for inspection on failure.
    """
    try:
        import jsonschema as _jsonschema
    except ImportError:
        logger.warning("[W8] jsonschema not installed -- patch_bundle validation skipped")
        return

    schema = _get_patch_bundle_schema()
    if schema is None:
        return

    try:
        _jsonschema.validate(instance=patch_bundle, schema=schema)
        logger.info("[W8] patch_bundle.json passed schema validation")
    except _jsonschema.ValidationError as ve:
        logger.error(f"[W8] patch_bundle.json FAILED schema validation: {ve.message}")
        raise LinkerPatchConflictError(
            f"patch_bundle.json schema validation failed: {ve.message}"
        ) from ve
    except Exception as exc:
        logger.warning(f"[W8] patch_bundle schema validation error: {exc}")


def _classify_conflict(error: Exception) -> str:
    """Classify conflict error into one of the spec 08:74-79 categories.

    Prefers isinstance checks (resilient to message rewording) with
    string-based fallback for LinkerPatchConflictError subtypes.
    """
    # FileNotFoundError is a distinct class — match before string parsing
    if isinstance(error, FileNotFoundError):
        return "file_not_found"
    msg = str(error).lower()
    if "anchor" in msg and "not found" in msg:
        return "anchor_not_found"
    if "line range" in msg or "out of bounds" in msg:
        return "line_range_out_of_bounds"
    if "hash" in msg or "content mismatch" in msg:
        return "content_mismatch"
    if "allowed" in msg and "path" in msg:
        return "path_outside_allowed_paths"
    if "file not found" in msg or "target file" in msg:
        return "file_not_found"
    return "unknown"


def _extract_conflict_states(error: Exception) -> Tuple[str, str]:
    """Extract expected/actual state from error message."""
    msg = str(error)
    m = re.search(r"expected\s+(\S+),\s+got\s+(\S+)", msg)
    if m:
        return m.group(1), m.group(2)
    return msg, "conflict_detected"


def _suggest_fix(error: Exception, patch: Dict[str, Any]) -> str:
    """Generate diagnostic guidance for conflict resolution."""
    msg = str(error).lower()
    path = patch.get("path", "unknown")
    if "anchor not found" in msg:
        anchor = patch.get("anchor", "unknown")
        return f"Expected heading '{anchor}' not found in {path}. Check if heading was renamed or removed."
    if "content mismatch" in msg:
        return f"Content at {path} was modified externally. Re-run W5 to regenerate drafts."
    if "allowed_paths" in msg:
        return f"Patch targets {path} which is outside allowed_paths. Update run_config.allowed_paths."
    if "line range" in msg:
        return f"Line range in patch exceeds file length in {path}. File may have been truncated."
    if "target file not found" in msg:
        return f"File {path} does not exist. Ensure site worktree is initialized."
    return f"Conflict in {path}. Manual inspection required."


def execute_linker_and_patcher(
    run_dir: Path,
    run_config: Dict[str, Any],
) -> Dict[str, Any]:
    """Execute W6 LinkerAndPatcher worker.

    Converts drafts into patches and applies them to the site worktree
    deterministically.

    Per specs/08_patch_engine.md and specs/21_worker_contracts.md:228-251.

    Args:
        run_dir: Path to run directory
        run_config: Run configuration dictionary

    Returns:
        Dictionary containing:
        - status: "success" or "failed"
        - patch_bundle_path: Path to patch_bundle.json
        - diff_report_path: Path to diff_report.md
        - patches_applied: Number of patches applied
        - patches_skipped: Number of patches skipped

    Raises:
        LinkerAndPatcherError: If linking/patching fails
        LinkerNoDraftsError: If no drafts found
        LinkerAllowedPathsViolationError: If path validation fails
        LinkerPatchConflictError: If patch conflicts detected
    """
    run_layout = RunLayout(run_dir=run_dir)
    run_id = run_config.get("run_id", "unknown")
    trace_id = str(uuid.uuid4())
    span_id = str(uuid.uuid4())

    logger.info(f"[W6 LinkerAndPatcher] Starting patch generation and application for run {run_id}")

    # Emit start event
    emit_event(
        run_layout=run_layout,
        run_id=run_id,
        trace_id=trace_id,
        span_id=span_id,
        event_type=EVENT_WORK_ITEM_STARTED,
        payload={"worker": "w8_linker_and_patcher", "phase": "patch_generation"},
    )

    # Emit PATCH_ENGINE_STARTED (specs/08_patch_engine.md:139)
    emit_event(
        run_layout=run_layout,
        run_id=run_id,
        trace_id=trace_id,
        span_id=span_id,
        event_type=EVENT_PATCH_ENGINE_STARTED,
        payload={"worker": "w8_linker_and_patcher"},
    )

    try:
        # Load input artifacts
        page_plan = load_page_plan(run_layout.artifacts_dir)
        draft_manifest = load_draft_manifest(run_layout.artifacts_dir)

        # Check for drafts
        drafts = draft_manifest.get("drafts", [])
        if not drafts:
            raise LinkerNoDraftsError("No drafts found in draft_manifest.json")

        logger.info(f"[W6 LinkerAndPatcher] Processing {len(drafts)} drafts")

        # Get site worktree path
        site_worktree = run_layout.work_dir / "site"
        if not site_worktree.exists():
            raise LinkerAndPatcherError(f"Site worktree not found: {site_worktree}")

        # Get allowed_paths from run_config
        allowed_paths = run_config.get("allowed_paths")

        # Extract family and platform for link absolutization (TC-2356)
        _family = run_config.get("family", run_config.get("product_family", ""))
        _platform = run_config.get("target_platform", "")

        # Generate patches from drafts
        patches = generate_patches_from_drafts(
            draft_manifest=draft_manifest,
            page_plan=page_plan,
            run_dir=run_dir,
            site_worktree=site_worktree,
            family=_family,
            platform=_platform,
        )

        logger.info(f"[W6 LinkerAndPatcher] Generated {len(patches)} patches")

        # TC-3520: Sort patches by type priority to prevent line-range OOB errors.
        # create_file → update_frontmatter → append_ → update_by_anchor → update_range → delete
        patches = sorted(patches, key=_patch_type_priority)

        # Apply patches
        patch_results = []
        for patch in patches:
            try:
                result = apply_patch(
                    patch=patch,
                    site_worktree=site_worktree,
                    allowed_paths=allowed_paths,
                )
                patch_results.append(result)

                # Emit telemetry per spec 08:139
                if result["status"] == "applied":
                    emit_event(
                        run_layout=run_layout,
                        run_id=run_id,
                        trace_id=trace_id,
                        span_id=span_id,
                        event_type=EVENT_PATCH_APPLIED,
                        payload={
                            "patch_id": patch["patch_id"],
                            "path": patch["path"],
                            "type": patch["type"],
                        },
                    )
                elif result["status"] == "skipped":
                    emit_event(
                        run_layout=run_layout,
                        run_id=run_id,
                        trace_id=trace_id,
                        span_id=span_id,
                        event_type=EVENT_PATCH_SKIPPED,
                        payload={
                            "patch_id": patch["patch_id"],
                            "path": patch["path"],
                            "reason": "idempotent_skip",
                        },
                    )

            except (LinkerAllowedPathsViolationError, LinkerPatchConflictError) as e:
                logger.error(f"[W8 LinkerAndPatcher] Patch conflict: {e}")

                # Record conflict
                patch_results.append({
                    "status": "conflict",
                    "reason": str(e),
                })

                # Build structured conflict record (spec 08:84-88)
                conflict_reason = _classify_conflict(e)
                expected_state, actual_state = _extract_conflict_states(e)
                suggested_fix = _suggest_fix(e, patch)

                conflict_record = {
                    "patch_id": patch["patch_id"],
                    "conflict_reason": conflict_reason,
                    "expected_state": expected_state,
                    "actual_state": actual_state,
                    "file": patch.get("path", "unknown"),
                    "suggested_fix": suggested_fix,
                }

                # Write patch_conflicts.json (append if exists)
                conflicts_path = run_layout.artifacts_dir / "patch_conflicts.json"
                existing_conflicts = {"conflicts": []}
                if conflicts_path.exists():
                    try:
                        existing_conflicts = json.loads(
                            conflicts_path.read_text(encoding="utf-8")
                        )
                    except (json.JSONDecodeError, OSError):
                        pass
                existing_conflicts["conflicts"].append(conflict_record)
                atomic_write_json(conflicts_path, existing_conflicts)

                # Emit enriched blocker issue (with location.path + suggested_fix)
                emit_event(
                    run_layout=run_layout,
                    run_id=run_id,
                    trace_id=trace_id,
                    span_id=span_id,
                    event_type=EVENT_ISSUE_OPENED,
                    payload={
                        "issue_id": f"patch_conflict_{patch['patch_id']}",
                        "error_code": "LINKER_PATCHER_CONFLICT_UNRESOLVABLE",
                        "severity": "blocker",
                        "message": str(e),
                        "patch_id": patch["patch_id"],
                        "location": {"path": patch.get("path", "unknown")},
                        "suggested_fix": suggested_fix,
                    },
                )

                # Re-raise to halt execution
                raise

        # TC-952: Export content preview for user inspection
        # TC-1000: Fix double-content bug - patch["path"] already includes "content/"
        content_preview_dir = run_layout.run_dir / "content_preview"
        content_preview_dir.mkdir(parents=True, exist_ok=True)

        exported_files = []
        for idx, patch in enumerate(patches):
            if patch_results[idx]["status"] == "applied":
                source_path = site_worktree / patch["path"]
                if source_path.exists():
                    dest_path = content_preview_dir / patch["path"]
                    try:
                        dest_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(source_path, dest_path)
                        exported_files.append(str(dest_path.relative_to(run_layout.run_dir)))
                    except OSError as copy_err:
                        logger.warning(f"[W6] Skipping content preview for {patch['path']}: {copy_err}")

        logger.info(f"[W6] Exported {len(exported_files)} files to content_preview")

        # Build patch bundle
        patch_bundle = {
            "schema_version": "1.0",
            "patches": patches,
        }

        # Write patch bundle BEFORE validation so artifact is available
        # for inspection even if validation fails (fail-fast, GAP-02).
        patch_bundle_path = run_layout.artifacts_dir / "patch_bundle.json"
        atomic_write_json(patch_bundle_path, patch_bundle)

        # Validate against schema (fail-fast per spec 08)
        _validate_patch_bundle(patch_bundle)

        logger.info(f"[W6 LinkerAndPatcher] Wrote patch bundle: {patch_bundle_path}")

        # Emit artifact written event
        emit_event(
            run_layout=run_layout,
            run_id=run_id,
            trace_id=trace_id,
            span_id=span_id,
            event_type=EVENT_ARTIFACT_WRITTEN,
            payload={
                "artifact": "patch_bundle.json",
                "path": str(patch_bundle_path),
                "patch_count": len(patches),
            },
        )

        # Generate diff report
        diff_report = generate_diff_report(patches, patch_results, site_worktree)
        diff_report_path = run_layout.reports_dir / "diff_report.md"
        atomic_write_text(diff_report_path, diff_report)

        logger.info(f"[W6 LinkerAndPatcher] Wrote diff report: {diff_report_path}")

        # Count results
        applied_count = sum(1 for r in patch_results if r["status"] == "applied")
        skipped_count = sum(1 for r in patch_results if r["status"] == "skipped")

        # Emit PATCH_ENGINE_COMPLETED (specs/08_patch_engine.md:139)
        emit_event(
            run_layout=run_layout,
            run_id=run_id,
            trace_id=trace_id,
            span_id=span_id,
            event_type=EVENT_PATCH_ENGINE_COMPLETED,
            payload={
                "patches_applied": applied_count,
                "patches_skipped": skipped_count,
            },
        )

        # Emit completion event
        emit_event(
            run_layout=run_layout,
            run_id=run_id,
            trace_id=trace_id,
            span_id=span_id,
            event_type=EVENT_WORK_ITEM_FINISHED,
            payload={
                "worker": "w8_linker_and_patcher",
                "phase": "patch_generation",
                "status": "success",
                "patches_applied": applied_count,
                "patches_skipped": skipped_count,
            },
        )

        return {
            "status": "success",
            "patch_bundle_path": str(patch_bundle_path),
            "diff_report_path": str(diff_report_path),
            "patches_applied": applied_count,
            "patches_skipped": skipped_count,
            "content_preview_dir": str(content_preview_dir.relative_to(run_layout.run_dir)),
            "exported_files_count": len(exported_files),
        }

    except Exception as e:
        logger.error(f"[W6 LinkerAndPatcher] Patch generation failed: {e}")

        # Emit failure event
        emit_event(
            run_layout=run_layout,
            run_id=run_id,
            trace_id=trace_id,
            span_id=span_id,
            event_type=EVENT_RUN_FAILED,
            payload={
                "worker": "w8_linker_and_patcher",
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )

        raise
