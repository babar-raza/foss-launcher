"""FrontmatterContract model for W1 frontmatter discovery artifact.

Typed container for the frontmatter_contract.json artifact produced by W1
RepoScout. Contains discovered frontmatter field contracts per site section.

Spec references:
- specs/schemas/frontmatter_contract.schema.json (Schema definition)
- specs/21_worker_contracts.md:54-95 (W1 RepoScout contract)
- specs/10_determinism_and_caching.md (Deterministic serialization)

TC-1030: Typed Artifact Models -- Foundation
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .base import Artifact


class SectionContract:
    """Frontmatter contract for a single site section.

    Per specs/schemas/frontmatter_contract.schema.json#$defs/sectionContract.
    """

    # Valid key types per schema
    VALID_KEY_TYPES = {
        "string", "integer", "number", "boolean",
        "date", "array_string", "object", "unknown",
    }

    def __init__(
        self,
        sample_size: int,
        required_keys: List[str],
        optional_keys: List[str],
        key_types: Dict[str, str],
        default_values: Optional[Dict[str, Any]] = None,
    ):
        self.sample_size = sample_size
        self.required_keys = required_keys
        self.optional_keys = optional_keys
        self.key_types = key_types
        self.default_values = default_values

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary with stable field ordering."""
        result: Dict[str, Any] = {
            "key_types": dict(sorted(self.key_types.items())),
            "optional_keys": sorted(self.optional_keys),
            "required_keys": sorted(self.required_keys),
            "sample_size": self.sample_size,
        }
        if self.default_values is not None:
            result["default_values"] = dict(sorted(
                (k, v) for k, v in self.default_values.items()
            ))
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SectionContract:
        """Deserialize from dictionary."""
        return cls(
            sample_size=data["sample_size"],
            required_keys=data["required_keys"],
            optional_keys=data["optional_keys"],
            key_types=data["key_types"],
            default_values=data.get("default_values"),
        )


class FrontmatterContract(Artifact):
    """Frontmatter contract artifact produced by W1 RepoScout.

    Contains discovered frontmatter field contracts for each site section
    (products, docs, reference, kb, blog).
    Per specs/schemas/frontmatter_contract.schema.json.
    """

    SECTION_NAMES = ["blog", "docs", "kb", "products", "reference"]

    def __init__(
        self,
        schema_version: str,
        site_repo_url: str,
        site_sha: str,
        sections: Dict[str, SectionContract],
    ):
        super().__init__(schema_version)
        self.site_repo_url = site_repo_url
        self.site_sha = site_sha
        self.sections = sections

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary with stable field ordering."""
        result = super().to_dict()
        result.update({
            "sections": {
                name: self.sections[name].to_dict()
                for name in sorted(self.sections.keys())
            },
            "site_repo_url": self.site_repo_url,
            "site_sha": self.site_sha,
        })
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> FrontmatterContract:
        """Deserialize from dictionary."""
        sections_data = data.get("sections", {})
        sections = {
            name: SectionContract.from_dict(section_data)
            for name, section_data in sections_data.items()
        }
        return cls(
            schema_version=data.get("schema_version", "1.0"),
            site_repo_url=data["site_repo_url"],
            site_sha=data["site_sha"],
            sections=sections,
        )

    def validate(self) -> bool:
        """Validate required fields and types.

        Returns:
            True if valid, raises ValueError otherwise.
        """
        if not self.site_repo_url:
            raise ValueError("site_repo_url is required and must be non-empty")
        if not self.site_sha:
            raise ValueError("site_sha is required and must be non-empty")
        required_sections = {"products", "docs", "reference", "kb", "blog"}
        missing = required_sections - set(self.sections.keys())
        if missing:
            raise ValueError(f"Missing required sections: {sorted(missing)}")
        for name, section in self.sections.items():
            if section.sample_size < 1:
                raise ValueError(
                    f"Section '{name}' sample_size must be >= 1, got {section.sample_size}"
                )
            for key, key_type in section.key_types.items():
                if key_type not in SectionContract.VALID_KEY_TYPES:
                    raise ValueError(
                        f"Section '{name}' key '{key}' has invalid type '{key_type}'. "
                        f"Valid types: {sorted(SectionContract.VALID_KEY_TYPES)}"
                    )
        return True
