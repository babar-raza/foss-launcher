"""Template loader — resolves and reads Hugo page templates.

v2 templates are **family-independent**. The directory layout uses
``__FAMILY__`` in place of a family slug so any product family can use the
same template set. Placeholder tokens (``__UPPER_SNAKE__``) are substituted
at generation time by the Generate worker.

Resolution strategy:
  1. Search the subdomain tree for ``{page_role}.variant-{variant}.md``
  2. Search for ``{page_role}.md``
  3. If variant != standard, search for ``{page_role}.variant-standard.md``
  4. Return ``None`` if nothing found
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from launcher.shared.page_skeletons import SkeletonSection

# Root of the specs/templates tree relative to project root.
_SPECS_ROOT = Path(__file__).resolve().parents[3] / "specs" / "templates"

SECTION_SUBDOMAIN_MAP: dict[str, str] = {
    "products": "products.aspose.org",
    "docs": "docs.aspose.org",
    "kb": "kb.aspose.org",
    "reference": "reference.aspose.org",
    "blog": "blog.aspose.org",
}

_TIER_VARIANT_MAP: dict[str, str] = {
    "A": "standard",
    "B": "standard",
    "C": "minimal",
}

# Map page_role names to template filename stems (when they differ).
_ROLE_TEMPLATE_NAME: dict[str, str] = {
    "api_reference": "reference",
    "reference_object_page": "reference",
    "workflow_page": "feature",
    "howto_article": "howto",
    "toc": "_index",
}

# Map __BODY_*__ placeholders to (content_hint, min_words, max_words).
_PLACEHOLDER_HINTS: dict[str, tuple[str, int, int]] = {
    "__BODY_INTRO__": ("Introduction and overview", 50, 200),
    "__BODY_KEY_FEATURES__": ("Key features as a bulleted list", 100, 300),
    "__BODY_PREREQUISITES__": ("Required setup and dependencies", 30, 100),
    "__BODY_CODE_SAMPLES__": ("Runnable code examples", 50, 300),
    "__BODY_NOTES__": ("Notes, remarks, and best practices", 30, 200),
    "__BODY_SEE_ALSO__": ("Related links and references", 0, 100),
    "__BODY_STEPS__": ("Step-by-step instructions with code", 100, 400),
    "__BODY_CONSTRUCTORS__": ("Constructor signatures and parameters", 100, 400),
    "__BODY_PROPERTIES__": ("Property table: name, type, description", 80, 400),
    "__BODY_METHODS__": ("Method table: signature, return, description", 80, 400),
    "__BODY_TROUBLESHOOTING__": ("Common issues and solutions", 100, 400),
    "__BODY_KEY_MEMBERS__": ("Key class members and methods", 80, 300),
    "__BODY_SYSTEM_REQUIREMENTS__": ("System requirements and dependencies", 30, 100),
    "__BODY_PACKAGE_INSTALL__": ("Package manager installation steps", 30, 200),
    "__BODY_MANUAL_INSTALL__": ("Manual installation steps", 30, 200),
    "__BODY_VERIFY_INSTALL__": ("Installation verification steps", 30, 100),
}

_PLACEHOLDER_RE = re.compile(r"^__[A-Z0-9_]+__$")

# Whether the subdomain uses a __PLATFORM__ level in its template tree.
_SECTION_HAS_PLATFORM: dict[str, bool] = {
    "products": False,
    "docs": True,
    "kb": True,
    "reference": True,
    "blog": True,
}

# Default subfolder when no template matches, keyed by page_role.
_ROLE_DEFAULT_FOLDER: dict[str, str] = {
    "landing": "",
    "toc": "",
    "workflow_page": "developer-guide",
    "comprehensive_guide": "developer-guide",
    "tutorial": "developer-guide",
    "best_practices": "developer-guide",
    "performance_guide": "developer-guide",
    "feature_showcase": "developer-guide",
    "format_conversion": "developer-guide",
    "howto_article": "",
    "faq": "",
    "troubleshooting": "",
    "api_reference": "",
    "reference_object_page": "",
    "blog_announcement": "",
    "feature_blog": "",
}


def select_template(
    section: str,
    page_role: str,
    tier: str,
    *,
    family: str = "",
) -> Path | None:
    """Select a Hugo template for the given parameters.

    Templates are family-independent (``__FAMILY__``). The *family* parameter is
    accepted for backward compatibility but ignored during resolution —
    all families share the same template set.

    Searches the entire subdomain ``__FAMILY__`` tree recursively so
    templates in nested directories (e.g. ``getting-started/installation.md``)
    are found regardless of nesting depth.

    Parameters
    ----------
    section:
        Logical site section (``products``, ``docs``, ``kb``, ``reference``, ``blog``).
    page_role:
        The page kind / role slug (e.g. ``feature``, ``howto``, ``installation``).
    tier:
        Richness tier (``A``, ``B``, or ``C``).
    family:
        Product family slug (ignored — templates are generic).

    Returns
    -------
    Path | None
        Absolute path to the matching template, or ``None`` if nothing found.
    """
    subdomain = SECTION_SUBDOMAIN_MAP.get(section)
    if subdomain is None:
        return None

    variant = _TIER_VARIANT_MAP.get(tier, "standard")
    generic_root = _SPECS_ROOT / subdomain / "__FAMILY__"
    if not generic_root.exists():
        return None

    # Map page_role to template filename stem
    stem = _ROLE_TEMPLATE_NAME.get(page_role, page_role)

    # Build candidate filenames in priority order
    filenames = [
        f"{stem}.variant-{variant}.md",
        f"{stem}.md",
    ]
    if variant != "standard":
        filenames.append(f"{stem}.variant-standard.md")

    # Search for each filename in the tree
    for filename in filenames:
        matches = list(generic_root.rglob(filename))
        if matches:
            return matches[0]

    return None


def resolve_content_path(
    section: str,
    page_role: str,
    slug: str,
    family: str,
    platform: str,
    tier: str,
) -> str:
    """Compute the hierarchical content path for a page.

    Returns a forward-slash-separated path **without** file extension,
    e.g. ``docs.aspose.org/cells/python/getting-started/installation``.

    When a matching template exists its filesystem path determines the
    folder structure.  Otherwise a default folder is derived from
    ``_ROLE_DEFAULT_FOLDER``.
    """
    subdomain = SECTION_SUBDOMAIN_MAP.get(section, f"{section}.aspose.org")

    # Try to derive the folder from the matching template path
    template = select_template(section, page_role, tier)
    folder = ""
    if template is not None:
        folder, tmpl_has_platform = _folder_from_template(template, subdomain)
        has_platform = tmpl_has_platform
    else:
        folder = _ROLE_DEFAULT_FOLDER.get(page_role, "")
        has_platform = _SECTION_HAS_PLATFORM.get(section, True)

    # Build path segments
    parts: list[str] = [subdomain, family]
    if has_platform:
        parts.append(platform)
    if folder:
        parts.append(folder)
    parts.append(slug)
    return "/".join(parts)


def _folder_from_template(template: Path, subdomain: str) -> tuple[str, bool]:
    """Extract the subfolder and platform flag from a template's filesystem path.

    Given ``…/docs.aspose.org/__FAMILY__/__PLATFORM__/getting-started/installation.md``
    returns ``("getting-started", True)``.

    Given ``…/docs.aspose.org/__FAMILY__/_index.md``
    returns ``("", False)`` — no ``__PLATFORM__`` in the path.
    """
    subdomain_root = _SPECS_ROOT / subdomain
    try:
        rel = template.relative_to(subdomain_root)
    except ValueError:
        return "", False

    parts = list(rel.parts)
    has_platform = "__PLATFORM__" in parts

    # Strip placeholder directories (__FAMILY__, __PLATFORM__) and filename
    filtered = [
        p for p in parts[:-1]
        if not (p.startswith("__") and p.endswith("__"))
    ]
    return "/".join(filtered), has_platform


def load_template(path: Path) -> str:
    """Read and return the contents of a template file.

    Raises
    ------
    FileNotFoundError
        If *path* does not exist.
    """
    return path.read_text(encoding="utf-8")


def substitute_placeholders(
    template: str,
    values: dict[str, str],
) -> str:
    """Replace ``__UPPER_SNAKE__`` placeholders with provided values.

    Only replaces tokens present in *values*. Unknown tokens are left
    as-is so downstream gates can detect leakage.
    """
    result = template
    for token, value in values.items():
        key = token if token.startswith("__") else f"__{token.upper()}__"
        result = result.replace(key, value)
    return result


def list_templates(section: str) -> list[Path]:
    """List all template files available for a given section."""
    subdomain = SECTION_SUBDOMAIN_MAP.get(section)
    if subdomain is None:
        return []

    base_dir = _SPECS_ROOT / subdomain / "__FAMILY__"
    if not base_dir.exists():
        return []

    return sorted(base_dir.rglob("*.md"))


def extract_template_sections(content: str) -> list[SkeletonSection]:
    """Parse H2 headings and ``__BODY_*__`` placeholders from template content.

    Returns a list of :class:`SkeletonSection` objects matching the template
    structure.  The ``See Also`` section is marked optional; all others are
    required.
    """
    # Split off frontmatter
    body = _split_frontmatter(content)[1]

    sections: list[SkeletonSection] = []
    for line in body.split("\n"):
        m = re.match(r"^##\s+(.+)$", line)
        if m and not line.lstrip().startswith("###"):
            heading = m.group(1).strip()
            sections.append(heading)  # type: ignore[arg-type]  # collect first

    # Now build SkeletonSection objects by scanning for placeholders
    result: list[SkeletonSection] = []
    lines = body.split("\n")
    for heading_text in sections:
        # Find the placeholder after this heading
        hint, min_w, max_w = "Section content", 30, 200
        heading_line_idx = None
        for idx, line in enumerate(lines):
            if re.match(rf"^##\s+{re.escape(heading_text)}\s*$", line):
                heading_line_idx = idx
                break
        if heading_line_idx is not None:
            for idx in range(heading_line_idx + 1, min(heading_line_idx + 4, len(lines))):
                stripped = lines[idx].strip()
                if stripped in _PLACEHOLDER_HINTS:
                    hint, min_w, max_w = _PLACEHOLDER_HINTS[stripped]
                    break
                if _PLACEHOLDER_RE.match(stripped):
                    hint, min_w, max_w = "Section content", 30, 200
                    break

        required = heading_text.lower() != "see also"
        result.append(SkeletonSection(heading_text, 2, required, hint, min_w, max_w))

    return result


def extract_template_frontmatter(
    content: str,
) -> tuple[dict[str, Any], frozenset[str]]:
    """Parse YAML frontmatter from template, separating real values from placeholders.

    Returns:
        (concrete_values, required_placeholder_keys) where:
        - concrete_values: keys with real values from the template.
        - required_placeholder_keys: keys declared in the template with placeholder
          values (``__UPPER_SNAKE__``) — the caller MUST populate these before rendering.

    No overlap: a key appears in exactly one of the two outputs.
    Neither output contains ``None`` values.
    """
    fm_text = _split_frontmatter(content)[0]
    if not fm_text:
        return {}, frozenset()

    # Strip comment-only lines before parsing
    clean_lines = [
        line for line in fm_text.split("\n")
        if not line.strip().startswith("#")
    ]
    clean_text = "\n".join(clean_lines)

    try:
        parsed = yaml.safe_load(clean_text)
    except yaml.YAMLError:
        return {}, frozenset()

    if not isinstance(parsed, dict):
        return {}, frozenset()

    # Separate real values from placeholder tokens
    result: dict[str, Any] = {}
    placeholder_keys: set[str] = set()
    for key, value in parsed.items():
        if isinstance(value, str) and _PLACEHOLDER_RE.match(value):
            placeholder_keys.add(key)
            continue
        if isinstance(value, list) and all(
            isinstance(v, str) and _PLACEHOLDER_RE.match(v) for v in value
        ):
            placeholder_keys.add(key)
            continue
        result[key] = value

    return result, frozenset(placeholder_keys)


def _split_frontmatter(content: str) -> tuple[str, str]:
    """Split template into (frontmatter_text, body_text)."""
    if not content.startswith("---"):
        return "", content
    parts = content.split("---", 2)
    if len(parts) < 3:
        return "", content
    return parts[1], parts[2]
