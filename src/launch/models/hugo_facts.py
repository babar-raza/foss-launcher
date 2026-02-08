"""HugoFacts model for Hugo configuration facts artifact.

Typed container for the hugo_facts.json artifact derived from Hugo site
configuration parsing. Contains language settings, permalink patterns,
output formats, taxonomies, and source file tracking.

Spec references:
- specs/schemas/hugo_facts.schema.json (Schema definition)
- specs/21_worker_contracts.md:54-95 (W1 RepoScout contract)
- specs/10_determinism_and_caching.md (Deterministic serialization)

TC-1030: Typed Artifact Models -- Foundation
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .base import Artifact


class HugoFacts(Artifact):
    """Hugo configuration facts artifact.

    Contains parsed Hugo site configuration facts: language settings,
    permalink patterns, output formats, taxonomies, and source files.
    Per specs/schemas/hugo_facts.schema.json.
    """

    def __init__(
        self,
        schema_version: str,
        languages: List[str],
        default_language: str,
        default_language_in_subdir: bool,
        permalinks: Dict[str, str],
        outputs: Dict[str, List[str]],
        taxonomies: Dict[str, str],
        source_files: List[str],
    ):
        super().__init__(schema_version)
        self.languages = languages
        self.default_language = default_language
        self.default_language_in_subdir = default_language_in_subdir
        self.permalinks = permalinks
        self.outputs = outputs
        self.taxonomies = taxonomies
        self.source_files = source_files

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary with stable field ordering."""
        result = super().to_dict()
        result.update({
            "default_language": self.default_language,
            "default_language_in_subdir": self.default_language_in_subdir,
            "languages": sorted(self.languages),
            "outputs": {
                k: sorted(v) for k, v in sorted(self.outputs.items())
            },
            "permalinks": dict(sorted(self.permalinks.items())),
            "source_files": sorted(self.source_files),
            "taxonomies": dict(sorted(self.taxonomies.items())),
        })
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> HugoFacts:
        """Deserialize from dictionary."""
        return cls(
            schema_version=data.get("schema_version", "1.0"),
            languages=data["languages"],
            default_language=data["default_language"],
            default_language_in_subdir=data["default_language_in_subdir"],
            permalinks=data.get("permalinks", {}),
            outputs=data.get("outputs", {}),
            taxonomies=data.get("taxonomies", {}),
            source_files=data.get("source_files", []),
        )

    def validate(self) -> bool:
        """Validate required fields and types.

        Returns:
            True if valid, raises ValueError otherwise.
        """
        if not self.languages:
            raise ValueError("languages must be a non-empty list")
        if not self.default_language:
            raise ValueError("default_language is required and must be non-empty")
        if not isinstance(self.default_language_in_subdir, bool):
            raise ValueError("default_language_in_subdir must be a boolean")
        if not isinstance(self.permalinks, dict):
            raise ValueError("permalinks must be a dictionary")
        if not isinstance(self.outputs, dict):
            raise ValueError("outputs must be a dictionary")
        if not isinstance(self.taxonomies, dict):
            raise ValueError("taxonomies must be a dictionary")
        if not isinstance(self.source_files, list):
            raise ValueError("source_files must be a list")
        return True
