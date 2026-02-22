"""Shared execution context with lazy artifact loading.

``GateContext`` is created once per validation run and passed to every
adapter.  Artifacts are loaded on first access and cached for reuse.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class GateContext:
    """Lazy-loaded, cached context shared across all gates in one run.

    Provides *strict* accessors (raise on missing artifact) and *safe*
    accessors (return ``{}`` on missing) to match the two patterns in
    the original ``execute_validator()``.
    """

    def __init__(
        self,
        run_dir: Path,
        run_config: Dict[str, Any],
        profile: str,
    ) -> None:
        self.run_dir = run_dir
        self.run_config = run_config
        self.profile = profile

        # Lazy-load caches
        self._page_plan: Optional[Dict[str, Any]] = None
        self._page_plan_loaded: bool = False
        self._page_plan_error: Optional[Exception] = None

        self._product_facts: Optional[Dict[str, Any]] = None
        self._product_facts_loaded: bool = False
        self._product_facts_error: Optional[Exception] = None

        self._md_files_site: Optional[List[Path]] = None
        self._md_files_content: Optional[List[Path]] = None
        self._pages_with_roles: Optional[List[Dict[str, Any]]] = None

        self._llm_client: Any = None
        self._llm_client_loaded: bool = False

        # Skip-group cascade flag
        self.artifact_block_skip: bool = False

    # ── strict artifact accessors ─────────────────────────────────────

    def get_page_plan(self) -> Dict[str, Any]:
        """Load ``page_plan.json``.  Raises on missing artifact."""
        if not self._page_plan_loaded:
            self._page_plan_loaded = True
            try:
                self._page_plan = self._load_artifact("page_plan.json")
            except Exception as exc:
                self._page_plan_error = exc
                raise
        if self._page_plan_error is not None:
            raise self._page_plan_error
        assert self._page_plan is not None  # for type-checker
        return self._page_plan

    def get_product_facts(self) -> Dict[str, Any]:
        """Load ``product_facts.json``.  Raises on missing artifact."""
        if not self._product_facts_loaded:
            self._product_facts_loaded = True
            try:
                self._product_facts = self._load_artifact("product_facts.json")
            except Exception as exc:
                self._product_facts_error = exc
                raise
        if self._product_facts_error is not None:
            raise self._product_facts_error
        assert self._product_facts is not None
        return self._product_facts

    # ── safe artifact accessors (match locals() fallback) ─────────────

    def get_page_plan_safe(self) -> Dict[str, Any]:
        """Load page_plan.json, returning ``{}`` on failure.

        Matches ``page_plan if "page_plan" in locals() ... else {}``
        at worker.py line 1285-1286.
        """
        try:
            return self.get_page_plan()
        except Exception:
            return {}

    def get_product_facts_safe(self) -> Dict[str, Any]:
        """Load product_facts.json, returning ``{}`` on failure.

        Matches ``product_facts if "product_facts" in locals() else {}``
        at worker.py line 1280.
        """
        try:
            return self.get_product_facts()
        except Exception:
            return {}

    # ── file-list accessors ───────────────────────────────────────────

    def get_md_files_site(self) -> List[Path]:
        """Markdown files under ``work/site`` (sorted, deterministic).

        Used by gates 16 / 18 / 19 (pages assembly).
        """
        if self._md_files_site is None:
            from ..workers.w9_validator.worker import find_markdown_files

            self._md_files_site = find_markdown_files(
                self.run_dir / "work" / "site"
            )
        return self._md_files_site

    def get_md_files_content(self) -> List[Path]:
        """Markdown files under ``work/site/content``.

        Used by gates 17 / 20.  Matches ``list(rglob("*.md"))`` at
        worker.py line 1369 (unsorted — order is filesystem-dependent).
        """
        if self._md_files_content is None:
            content_dir = self.run_dir / "work" / "site" / "content"
            self._md_files_content = (
                list(content_dir.rglob("*.md"))
                if content_dir.exists()
                else []
            )
        return self._md_files_content

    # ── derived data ──────────────────────────────────────────────────

    def get_pages_with_roles(self) -> List[Dict[str, Any]]:
        """Build ``[{path, content, page_role}]`` for gates 16/18/19.

        Uses *safe* artifact loading so that missing ``page_plan.json``
        yields role-less pages (matches worker.py lines 1280-1305).
        """
        if self._pages_with_roles is None:
            page_plan = self.get_page_plan_safe()
            md_files = self.get_md_files_site()
            site_dir = self.run_dir / "work" / "site"

            pages: List[Dict[str, Any]] = []
            for md_file in md_files:
                try:
                    file_content = md_file.read_text(encoding="utf-8")
                    page_role = ""
                    rel_path = str(
                        md_file.relative_to(site_dir)
                    ).replace("\\", "/")
                    for pg in page_plan.get("pages", []):
                        if pg.get("output_path", "") == rel_path:
                            page_role = pg.get("page_role", "")
                            break
                    pages.append(
                        {
                            "path": str(md_file),
                            "content": file_content,
                            "page_role": page_role,
                        }
                    )
                except Exception:
                    pass  # matches worker.py line 1304
            self._pages_with_roles = pages
        return self._pages_with_roles

    def get_llm_client(self) -> Any:
        """Build LLM client from ``run_config``.

        Returns ``None`` when the LLM is unavailable.
        Matches worker.py lines 1356-1366.
        """
        if not self._llm_client_loaded:
            self._llm_client_loaded = True
            llm_cfg = self.run_config.get("llm", {})
            if llm_cfg.get("api_base_url") or llm_cfg.get("endpoint"):
                try:
                    from launch.clients.llm_provider import (
                        create_llm_client_from_config,
                    )

                    self._llm_client = create_llm_client_from_config(
                        run_config=self.run_config,
                        run_dir=self.run_dir,
                    )
                except Exception:
                    pass  # gate passes gracefully without LLM
        return self._llm_client

    # ── simple helpers ────────────────────────────────────────────────

    def get_repo_root(self) -> Path:
        """Repository root (two levels above run_dir)."""
        return self.run_dir.parent.parent

    def get_site_content_dir(self) -> Path:
        """``RUN_DIR/work/site``."""
        return self.run_dir / "work" / "site"

    def get_max_parallel_g17(self) -> int:
        """Max parallel files for gate 17.  Matches worker.py line 1371."""
        return max(1, min(8, self.run_config.get("max_parallel_files_g17", 4)))

    # ── internal ──────────────────────────────────────────────────────

    def _load_artifact(self, name: str) -> Dict[str, Any]:
        """Delegate to the existing ``load_json_artifact``."""
        from ..workers.w9_validator.worker import load_json_artifact

        return load_json_artifact(self.run_dir, name)
