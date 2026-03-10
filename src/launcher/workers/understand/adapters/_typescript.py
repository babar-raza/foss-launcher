"""TypeScript/JavaScript platform adapter — wraps existing tree-sitter extraction."""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from launcher.models.product import ProductIdentity
from launcher.workers.understand.adapters._base import PlatformExtractor

logger = logging.getLogger(__name__)


class TypeScriptExtractor(PlatformExtractor):
    """TypeScript/JS adapter wrapping the existing ts_analyzer.

    In Phase 2 this is a thin wrapper with no behavior change.
    Phase 3 will enhance extraction depth (typed methods, properties, enums).
    """

    @property
    def platform_id(self) -> str:
        return "typescript"

    @property
    def file_extensions(self) -> list[str]:
        return [".ts", ".tsx", ".js", ".jsx", ".mjs"]

    def detect_package_root(self, repo_dir: Path, product: ProductIdentity) -> str:
        """Detect package root from package.json main/module field."""
        pkg_json = repo_dir / "package.json"
        if pkg_json.exists():
            try:
                data = json.loads(pkg_json.read_text(encoding="utf-8", errors="replace"))
                main = data.get("main", "") or data.get("module", "")
                if main:
                    candidate = str(Path(main).parent) if "/" in main else ""
                    if candidate and (repo_dir / candidate).is_dir():
                        return candidate
                    # Fallback: src/ directory
                    src_dir = repo_dir / "src"
                    if src_dir.is_dir() and any(src_dir.rglob("*.ts")):
                        return "src"
            except Exception:
                pass

        # Fallback: src/ if it has TS files
        src_dir = repo_dir / "src"
        if src_dir.is_dir() and any(src_dir.rglob("*.ts")):
            return "src"

        return ""

    def extract_class_details(
        self,
        file_path: Path,
        repo_dir: Path,
        product: ProductIdentity,
    ) -> list[dict]:
        """Delegate to code_analyzer.analyze_file_safe() for TS/JS files.

        The shared code_analyzer already dispatches to ts_analyzer for
        non-Python files.
        """
        from launcher.shared.code_analyzer import analyze_file_safe

        result = analyze_file_safe(file_path, repo_dir=repo_dir)
        if not result:
            return []
        return result.get("classes", [])

    def build_import_allowlist(
        self,
        repo_dir: Path,
        package_root: str,
        product: ProductIdentity,
    ) -> list[str]:
        """Build import allowlist from package.json exports."""
        allowlist: list[str] = []
        if product.canonical_import:
            allowlist.append(product.canonical_import)

        pkg_json = repo_dir / "package.json"
        if pkg_json.exists():
            try:
                data = json.loads(pkg_json.read_text(encoding="utf-8", errors="replace"))
                name = data.get("name", "")
                if name:
                    allowlist.append(name)
                exports = data.get("exports", {})
                if isinstance(exports, dict):
                    for key in exports:
                        if key != "." and isinstance(key, str):
                            allowlist.append(f"{name}/{key.lstrip('./')}")
            except Exception:
                pass

        return allowlist
