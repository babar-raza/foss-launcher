"""
Content module - Path resolution and content organization for Hugo sites.

This module provides utilities for mapping logical page identifiers to Hugo
content paths and public URLs.
"""

from .path_resolver import (
    ContentPathResolver,
    ContentStyle,
    HugoConfig,
    PageIdentifier,
    generate_slug,
    parse_content_path,
    resolve_content_path,
    resolve_permalink,
)
from .template_registry import resolve_ruleset_path, resolve_templates_root

__all__ = [
    "ContentPathResolver",
    "ContentStyle",
    "HugoConfig",
    "PageIdentifier",
    "generate_slug",
    "parse_content_path",
    "resolve_content_path",
    "resolve_permalink",
    "resolve_ruleset_path",
    "resolve_templates_root",
]
