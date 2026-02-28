"""Page resolver for W7 ContentReviewer.

Provides deterministic page resolution from draft file paths to page_plan entries.
Fixes the md_file.stem bug where index.md files all resolve to slug "index" instead
of their correct parent directory slug.

TC-3500: W7 ContentReviewer Hardening — PageResolver
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class ResolvedPage:
    """Resolved page entry from page_plan.json.

    Provides stable slug, section, and metadata for a draft file,
    avoiding the md_file.stem bug for index.md files.
    """

    slug: str
    section: str
    rel_path: str          # drafts_dir-relative, forward slashes
    title: str
    page_role: str
    claim_ids: List[str]   # from page_plan entry (may be empty)
    page_entry: Dict[str, Any]  # raw page_plan dict


class PageResolver:
    """Resolves draft file paths to page_plan entries.

    Resolution algorithm (priority order):
    1. Exact output_path / draft_path suffix match
    2. Slug + section disambiguation
    3. Filename match
    4. Slug-only match (first hit)

    For index.md files, the slug is derived from the parent directory name
    instead of md_file.stem (which would always return "index").
    """

    def __init__(self, page_plan: Dict[str, Any], drafts_dir: Path) -> None:
        self._drafts_dir = drafts_dir
        self._pages: List[Dict[str, Any]] = page_plan.get("pages", [])
        self._cache: Dict[str, Optional[ResolvedPage]] = {}

    def resolve(self, md_file: Path) -> Optional[ResolvedPage]:
        """Resolve a draft file to its page_plan entry.

        Args:
            md_file: Absolute path to a draft markdown file.

        Returns:
            ResolvedPage if found in page_plan, None otherwise.
        """
        rel_path = str(md_file.relative_to(self._drafts_dir)).replace("\\", "/")
        if rel_path in self._cache:
            return self._cache[rel_path]
        result = self._do_resolve(md_file, rel_path)
        self._cache[rel_path] = result
        return result

    def resolve_all(self) -> Dict[str, ResolvedPage]:
        """Resolve all draft files and return the cache.

        Returns:
            Dict mapping rel_path to ResolvedPage (excludes None entries).
        """
        for md_file in sorted(self._drafts_dir.rglob("*.md")):
            self.resolve(md_file)
        return {k: v for k, v in self._cache.items() if v is not None}

    @staticmethod
    def derive_slug(md_file: Path) -> str:
        """Derive slug from a draft file path.

        For index.md: returns parent directory name.
        For other files: returns stem (filename without extension).
        """
        if md_file.name == "index.md" or md_file.name == "_index.md":
            return md_file.parent.name
        return md_file.stem

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _do_resolve(
        self, md_file: Path, rel_path: str,
    ) -> Optional[ResolvedPage]:
        parts = rel_path.split("/")
        section = parts[0] if len(parts) > 1 else ""
        slug = self.derive_slug(md_file)

        matched = self._match_page(slug, section, rel_path, md_file.name)
        if matched is None:
            return None

        return ResolvedPage(
            slug=matched.get("slug", slug),
            section=matched.get("section", section),
            rel_path=rel_path,
            title=matched.get("title", ""),
            page_role=matched.get("page_role", ""),
            claim_ids=matched.get("claim_ids", []),
            page_entry=matched,
        )

    def _match_page(
        self,
        slug: str,
        section: str,
        rel_path: str,
        filename: str,
    ) -> Optional[Dict[str, Any]]:
        # Priority 1: output_path or draft_path suffix match
        for page in self._pages:
            op = page.get("output_path", "").replace("\\", "/")
            dp = page.get("draft_path", "").replace("\\", "/")
            if op and (rel_path == op or rel_path.endswith("/" + op)):
                return page
            if dp and (rel_path == dp or rel_path.endswith("/" + dp)):
                return page

        # Priority 2: slug + section disambiguation
        for page in self._pages:
            page_slug = page.get("slug", "")
            page_filename = page.get("filename", "")
            if page_slug == slug or page_filename == filename:
                page_section = page.get("section", "")
                if section and page_section and section != page_section:
                    continue
                return page

        # Priority 3: slug-only match (no section filter, first hit)
        for page in self._pages:
            if page.get("slug") == slug:
                return page

        return None
