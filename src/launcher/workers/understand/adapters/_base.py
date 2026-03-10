"""Abstract base class for platform-specific extraction adapters."""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from launcher.models.product import (
    ClassBrief,
    FormatRecord,
    ProductIdentity,
)


class PlatformExtractor(ABC):
    """Abstract interface for platform-specific extraction logic.

    Each platform implements this to provide:
    - Deep class/method/property/enum extraction (typed)
    - Package root detection
    - Import allowlist generation

    Adding a platform = implementing one subclass + registering in __init__.py.
    """

    @property
    @abstractmethod
    def platform_id(self) -> str:
        """Platform identifier, e.g. 'python', 'typescript', 'dotnet'."""

    @property
    @abstractmethod
    def file_extensions(self) -> list[str]:
        """Source file extensions, e.g. ['.py'], ['.ts', '.tsx', '.js']."""

    @abstractmethod
    def detect_package_root(self, repo_dir: Path, product: ProductIdentity) -> str:
        """Return relative path to the main package directory.

        Returns empty string when no root can be detected.
        """

    @abstractmethod
    def extract_class_details(
        self,
        file_path: Path,
        repo_dir: Path,
        product: ProductIdentity,
    ) -> list[dict]:
        """Extract class information from a single source file.

        Returns a list of dicts compatible with code_analyzer output format:
        ``{"name", "docstring", "methods", "properties", "method_details",
        "property_details", "is_enum", "enum_members"}``.

        The caller (_api_surface.py) builds ClassBrief from these dicts.
        """

    @abstractmethod
    def build_import_allowlist(
        self,
        repo_dir: Path,
        package_root: str,
        product: ProductIdentity,
    ) -> list[str]:
        """Return valid import statements for this product."""

    def extract_format_capabilities(
        self,
        file_path: Path,
        class_name: str,
    ) -> list[FormatRecord]:
        """Extract format capability flags from source (e.g. getter bodies).

        Default returns empty list. Override for platforms where format
        capabilities are expressed as getter properties.
        """
        return []
