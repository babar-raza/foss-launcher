"""Centralized prompt library for LLM-driven content generation.

All LLM prompts are loaded via PromptLoader from this directory.
Prompt files use YAML frontmatter + text body format.

Spec references:
- specs/21_worker_contracts.md 'Prompt Library Contract'
- specs/schemas/prompt_frontmatter.schema.json

Folder structure:
    system/      - System role prompts (content_architect, technical_writer, etc.)
    pages/       - Page-role prompts (comprehensive_guide, faq, tutorial, etc.)
    synthesis/   - W2 synthesis prompts (workflow_steps, faq_entries, etc.)
    review/      - W5.5 review prompts (api_verification, licensing_review, etc.)
    fragments/   - Shared fragments injected into multiple prompts
"""
from __future__ import annotations

import hashlib
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# YAML frontmatter delimiter
_FRONTMATTER_DELIMITER = "---"


@dataclass
class PromptResult:
    """Result of loading and rendering a prompt template."""

    text: str
    """Rendered prompt text with variables substituted."""

    metadata: Dict[str, Any]
    """Parsed YAML frontmatter (version, description, etc.)."""

    version: str
    """Content hash of the raw template (for A/B tracking)."""

    strategy: Dict[str, Any]
    """LLM call strategy from frontmatter (temperature, max_tokens, etc.)."""

    name: str = ""
    """Prompt name (e.g., 'pages/comprehensive_guide')."""


def _parse_frontmatter(raw: str) -> tuple:
    """Parse YAML frontmatter from prompt template.

    Returns:
        (metadata_dict, body_text) tuple.
    """
    raw = raw.strip()
    if not raw.startswith(_FRONTMATTER_DELIMITER):
        # No frontmatter — treat entire content as body
        return {}, raw

    # Find end of frontmatter
    end_idx = raw.find(_FRONTMATTER_DELIMITER, len(_FRONTMATTER_DELIMITER))
    if end_idx == -1:
        return {}, raw

    frontmatter_str = raw[len(_FRONTMATTER_DELIMITER):end_idx].strip()
    body = raw[end_idx + len(_FRONTMATTER_DELIMITER):].strip()

    # Parse YAML (using simple parser to avoid heavy dependency)
    metadata = _parse_yaml_simple(frontmatter_str)
    return metadata, body


def _parse_yaml_simple(text: str) -> Dict[str, Any]:
    """Simple YAML parser for prompt frontmatter.

    Handles: strings, numbers, booleans, lists, nested objects.
    For full YAML support, callers can use PyYAML if available.
    """
    try:
        import yaml
        return yaml.safe_load(text) or {}
    except ImportError:
        pass

    # Fallback: minimal key-value parser
    result: Dict[str, Any] = {}
    for line in text.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip()
            if val.startswith("[") and val.endswith("]"):
                # Simple list
                items = val[1:-1].split(",")
                result[key] = [i.strip().strip("\"'") for i in items if i.strip()]
            elif val.lower() in ("true", "false"):
                result[key] = val.lower() == "true"
            elif val.replace(".", "", 1).isdigit():
                result[key] = float(val) if "." in val else int(val)
            else:
                result[key] = val.strip("\"'")
    return result


class PromptLoader:
    """Load and render prompt templates from the centralized prompt library.

    Usage:
        loader = PromptLoader("src/launch/prompts")
        result = loader.load("pages/comprehensive_guide",
                            product_name="Aspose.3D",
                            audience="Python developers")
        prompt_text = result.text
        temperature = result.strategy.get("temperature", 0.1)
    """

    def __init__(self, base_path: str = "src/launch/prompts"):
        self._base = Path(base_path)
        self._cache: Dict[str, tuple] = {}  # name -> (metadata, body, version)

    def _resolve_path(self, name: str) -> Path:
        """Resolve prompt name to file path.

        Tries .txt then .md extensions.
        """
        for ext in (".txt", ".md", ".yaml", ""):
            path = self._base / f"{name}{ext}"
            if path.exists():
                return path
        # Try without extension (exact match)
        path = self._base / name
        if path.exists():
            return path
        raise FileNotFoundError(
            f"Prompt template not found: {name} (searched in {self._base})"
        )

    def _load_raw(self, name: str) -> tuple:
        """Load and cache a raw prompt template.

        Returns:
            (metadata, body, version) tuple.
        """
        if name in self._cache:
            return self._cache[name]

        path = self._resolve_path(name)
        raw = path.read_text(encoding="utf-8")
        version = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:8]
        metadata, body = _parse_frontmatter(raw)
        self._cache[name] = (metadata, body, version)
        return metadata, body, version

    def load(self, name: str, **kwargs: Any) -> PromptResult:
        """Load a prompt template, validate required variables, and render.

        Args:
            name: Prompt name relative to base (e.g., "pages/comprehensive_guide").
            **kwargs: Template variables to substitute.

        Returns:
            PromptResult with rendered text and metadata.

        Raises:
            FileNotFoundError: If prompt template doesn't exist.
            ValueError: If required variables are missing.
        """
        metadata, body, version = self._load_raw(name)

        # Validate required variables
        missing = self.validate_variables(name, kwargs)
        if missing:
            logger.warning(
                "Prompt '%s' missing required variables: %s (will use empty string)",
                name, missing,
            )

        # Build substitution dict: required + optional with defaults
        subs = {}
        for var in metadata.get("required_variables", []):
            subs[var] = kwargs.get(var, "")
        for var in metadata.get("optional_variables", []):
            subs[var] = kwargs.get(var, "")
        # Also include any extra kwargs
        subs.update(kwargs)

        # Render template (simple {var} substitution)
        text = body
        for key, val in subs.items():
            placeholder = "{" + key + "}"
            if isinstance(val, (list, dict)):
                val = str(val)
            text = text.replace(placeholder, str(val) if val is not None else "")

        strategy = metadata.get("strategy", {})

        return PromptResult(
            text=text,
            metadata=metadata,
            version=version,
            strategy=strategy,
            name=name,
        )

    def load_with_fragments(
        self,
        name: str,
        fragments: List[str],
        **kwargs: Any,
    ) -> PromptResult:
        """Load a prompt template and inject shared fragments.

        Fragments are appended to the prompt body before variable substitution.

        Args:
            name: Prompt name.
            fragments: List of fragment names (e.g., ["fragments/anti_hallucination"]).
            **kwargs: Template variables.

        Returns:
            PromptResult with fragments injected.
        """
        # Load main template
        metadata, body, version = self._load_raw(name)

        # Load and append fragments
        fragment_texts = []
        for frag_name in fragments:
            try:
                _, frag_body, _ = self._load_raw(frag_name)
                fragment_texts.append(frag_body)
            except FileNotFoundError:
                logger.warning("Fragment not found: %s", frag_name)

        if fragment_texts:
            body = body + "\n\n" + "\n\n".join(fragment_texts)

        # Validate and render
        missing = []
        for var in metadata.get("required_variables", []):
            if var not in kwargs:
                missing.append(var)
        if missing:
            logger.warning(
                "Prompt '%s' missing required variables: %s", name, missing,
            )

        subs = {}
        for var in metadata.get("required_variables", []):
            subs[var] = kwargs.get(var, "")
        for var in metadata.get("optional_variables", []):
            subs[var] = kwargs.get(var, "")
        subs.update(kwargs)

        text = body
        for key, val in subs.items():
            placeholder = "{" + key + "}"
            if isinstance(val, (list, dict)):
                val = str(val)
            text = text.replace(placeholder, str(val) if val is not None else "")

        strategy = metadata.get("strategy", {})

        return PromptResult(
            text=text,
            metadata=metadata,
            version=version,
            strategy=strategy,
            name=name,
        )

    def validate_variables(self, name: str, provided: Dict[str, Any]) -> List[str]:
        """Check required variables are present.

        Returns:
            List of missing variable names (empty if all present).
        """
        metadata, _, _ = self._load_raw(name)
        required = metadata.get("required_variables", [])
        return [v for v in required if v not in provided]

    def get_version(self, name: str) -> str:
        """Get content hash for version tracking."""
        _, _, version = self._load_raw(name)
        return version

    def list_prompts(self, category: Optional[str] = None) -> List[str]:
        """List available prompt templates.

        Args:
            category: Optional subdirectory filter (e.g., "pages", "system").

        Returns:
            List of prompt names relative to base.
        """
        search_dir = self._base / category if category else self._base
        if not search_dir.exists():
            return []

        results = []
        for path in search_dir.rglob("*"):
            if path.is_file() and path.suffix in (".txt", ".md", ".yaml"):
                rel = path.relative_to(self._base)
                name = str(rel).replace("\\", "/")
                # Strip extension
                name = name.rsplit(".", 1)[0]
                results.append(name)
        return sorted(results)
