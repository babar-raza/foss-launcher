"""Ruleset model for validation ruleset configuration.

Typed container for the ruleset configuration (e.g., ruleset.v1.yaml).
Contains style rules, truth rules, editing rules, Hugo configuration,
claims configuration, section requirements, and family overrides.

Spec references:
- specs/schemas/ruleset.schema.json (Schema definition)
- specs/rulesets/ruleset.v1.yaml (Canonical ruleset)
- specs/10_determinism_and_caching.md (Deterministic serialization)

TC-1030: Typed Artifact Models -- Foundation
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import Artifact


class StyleRules:
    """Style rules for content generation.

    Per specs/schemas/ruleset.schema.json#style.
    """

    def __init__(
        self,
        tone: str,
        audience: str,
        forbid_marketing_superlatives: bool,
        # Optional
        forbid_em_dash: Optional[bool] = None,
        prefer_short_sentences: Optional[bool] = None,
        forbid_weasel_words: Optional[List[str]] = None,
    ):
        self.tone = tone
        self.audience = audience
        self.forbid_marketing_superlatives = forbid_marketing_superlatives
        self.forbid_em_dash = forbid_em_dash
        self.prefer_short_sentences = prefer_short_sentences
        self.forbid_weasel_words = forbid_weasel_words

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary with stable field ordering."""
        result: Dict[str, Any] = {
            "audience": self.audience,
            "forbid_marketing_superlatives": self.forbid_marketing_superlatives,
            "tone": self.tone,
        }
        if self.forbid_em_dash is not None:
            result["forbid_em_dash"] = self.forbid_em_dash
        if self.prefer_short_sentences is not None:
            result["prefer_short_sentences"] = self.prefer_short_sentences
        if self.forbid_weasel_words is not None:
            result["forbid_weasel_words"] = sorted(self.forbid_weasel_words)
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> StyleRules:
        """Deserialize from dictionary."""
        return cls(
            tone=data["tone"],
            audience=data["audience"],
            forbid_marketing_superlatives=data["forbid_marketing_superlatives"],
            forbid_em_dash=data.get("forbid_em_dash"),
            prefer_short_sentences=data.get("prefer_short_sentences"),
            forbid_weasel_words=data.get("forbid_weasel_words"),
        )


class TruthRules:
    """Truth rules for content validation.

    Per specs/schemas/ruleset.schema.json#truth.
    """

    def __init__(
        self,
        no_uncited_facts: bool,
        forbid_inferred_formats: bool,
        # Optional
        allow_external_citations: Optional[bool] = None,
        allow_inference: Optional[bool] = None,
    ):
        self.no_uncited_facts = no_uncited_facts
        self.forbid_inferred_formats = forbid_inferred_formats
        self.allow_external_citations = allow_external_citations
        self.allow_inference = allow_inference

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary with stable field ordering."""
        result: Dict[str, Any] = {
            "forbid_inferred_formats": self.forbid_inferred_formats,
            "no_uncited_facts": self.no_uncited_facts,
        }
        if self.allow_external_citations is not None:
            result["allow_external_citations"] = self.allow_external_citations
        if self.allow_inference is not None:
            result["allow_inference"] = self.allow_inference
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TruthRules:
        """Deserialize from dictionary."""
        return cls(
            no_uncited_facts=data["no_uncited_facts"],
            forbid_inferred_formats=data["forbid_inferred_formats"],
            allow_external_citations=data.get("allow_external_citations"),
            allow_inference=data.get("allow_inference"),
        )


class EditingRules:
    """Editing rules for content modification.

    Per specs/schemas/ruleset.schema.json#editing.
    """

    def __init__(
        self,
        diff_only: bool,
        forbid_full_rewrite_existing_files: bool,
        # Optional
        forbid_deleting_existing_files: Optional[bool] = None,
    ):
        self.diff_only = diff_only
        self.forbid_full_rewrite_existing_files = forbid_full_rewrite_existing_files
        self.forbid_deleting_existing_files = forbid_deleting_existing_files

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary with stable field ordering."""
        result: Dict[str, Any] = {
            "diff_only": self.diff_only,
            "forbid_full_rewrite_existing_files": self.forbid_full_rewrite_existing_files,
        }
        if self.forbid_deleting_existing_files is not None:
            result["forbid_deleting_existing_files"] = self.forbid_deleting_existing_files
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> EditingRules:
        """Deserialize from dictionary."""
        return cls(
            diff_only=data["diff_only"],
            forbid_full_rewrite_existing_files=data["forbid_full_rewrite_existing_files"],
            forbid_deleting_existing_files=data.get("forbid_deleting_existing_files"),
        )


class HugoRules:
    """Hugo-specific rules.

    Per specs/schemas/ruleset.schema.json#hugo.
    """

    def __init__(
        self,
        allow_shortcodes: Optional[List[str]] = None,
        forbid_raw_html_except_claim_markers: Optional[bool] = None,
    ):
        self.allow_shortcodes = allow_shortcodes
        self.forbid_raw_html_except_claim_markers = forbid_raw_html_except_claim_markers

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        result: Dict[str, Any] = {}
        if self.allow_shortcodes is not None:
            result["allow_shortcodes"] = sorted(self.allow_shortcodes)
        if self.forbid_raw_html_except_claim_markers is not None:
            result["forbid_raw_html_except_claim_markers"] = self.forbid_raw_html_except_claim_markers
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> HugoRules:
        """Deserialize from dictionary."""
        return cls(
            allow_shortcodes=data.get("allow_shortcodes"),
            forbid_raw_html_except_claim_markers=data.get("forbid_raw_html_except_claim_markers"),
        )


class ClaimsRules:
    """Claims configuration rules.

    Per specs/schemas/ruleset.schema.json#claims.
    """

    def __init__(
        self,
        marker_style: Optional[str] = None,
        html_comment_prefix: Optional[str] = None,
        remove_markers_on_publish: Optional[bool] = None,
    ):
        self.marker_style = marker_style
        self.html_comment_prefix = html_comment_prefix
        self.remove_markers_on_publish = remove_markers_on_publish

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        result: Dict[str, Any] = {}
        if self.marker_style is not None:
            result["marker_style"] = self.marker_style
        if self.html_comment_prefix is not None:
            result["html_comment_prefix"] = self.html_comment_prefix
        if self.remove_markers_on_publish is not None:
            result["remove_markers_on_publish"] = self.remove_markers_on_publish
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ClaimsRules:
        """Deserialize from dictionary."""
        return cls(
            marker_style=data.get("marker_style"),
            html_comment_prefix=data.get("html_comment_prefix"),
            remove_markers_on_publish=data.get("remove_markers_on_publish"),
        )


class MandatoryPage:
    """A mandatory page entry in a section.

    Per specs/schemas/ruleset.schema.json#$defs/sectionMinPages/mandatory_pages/items.
    """

    def __init__(self, slug: str, page_role: str):
        self.slug = slug
        self.page_role = page_role

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "page_role": self.page_role,
            "slug": self.slug,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MandatoryPage:
        """Deserialize from dictionary."""
        return cls(slug=data["slug"], page_role=data["page_role"])


class OptionalPagePolicy:
    """An optional page policy entry.

    Per specs/schemas/ruleset.schema.json#$defs/sectionMinPages/optional_page_policies/items.
    """

    def __init__(self, page_role: str, source: str, priority: int):
        self.page_role = page_role
        self.source = source
        self.priority = priority

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "page_role": self.page_role,
            "priority": self.priority,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> OptionalPagePolicy:
        """Deserialize from dictionary."""
        return cls(
            page_role=data["page_role"],
            source=data["source"],
            priority=data["priority"],
        )


class StyleBySection:
    """Per-section style overrides.

    Per specs/schemas/ruleset.schema.json#$defs/sectionMinPages/style_by_section.
    """

    def __init__(
        self,
        tone: Optional[str] = None,
        voice: Optional[str] = None,
    ):
        self.tone = tone
        self.voice = voice

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        result: Dict[str, Any] = {}
        if self.tone is not None:
            result["tone"] = self.tone
        if self.voice is not None:
            result["voice"] = self.voice
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> StyleBySection:
        """Deserialize from dictionary."""
        return cls(tone=data.get("tone"), voice=data.get("voice"))


class LimitsBySection:
    """Per-section content limits.

    Per specs/schemas/ruleset.schema.json#$defs/sectionMinPages/limits_by_section.
    """

    def __init__(
        self,
        max_words: Optional[int] = None,
        max_headings: Optional[int] = None,
        max_code_blocks: Optional[int] = None,
    ):
        self.max_words = max_words
        self.max_headings = max_headings
        self.max_code_blocks = max_code_blocks

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        result: Dict[str, Any] = {}
        if self.max_words is not None:
            result["max_words"] = self.max_words
        if self.max_headings is not None:
            result["max_headings"] = self.max_headings
        if self.max_code_blocks is not None:
            result["max_code_blocks"] = self.max_code_blocks
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> LimitsBySection:
        """Deserialize from dictionary."""
        return cls(
            max_words=data.get("max_words"),
            max_headings=data.get("max_headings"),
            max_code_blocks=data.get("max_code_blocks"),
        )


class SectionConfig:
    """Section configuration with page requirements.

    Per specs/schemas/ruleset.schema.json#$defs/sectionMinPages.
    """

    def __init__(
        self,
        min_pages: int,
        max_pages: Optional[int] = None,
        style_by_section: Optional[StyleBySection] = None,
        limits_by_section: Optional[LimitsBySection] = None,
        mandatory_pages: Optional[List[MandatoryPage]] = None,
        optional_page_policies: Optional[List[OptionalPagePolicy]] = None,
    ):
        self.min_pages = min_pages
        self.max_pages = max_pages
        self.style_by_section = style_by_section
        self.limits_by_section = limits_by_section
        self.mandatory_pages = mandatory_pages or []
        self.optional_page_policies = optional_page_policies or []

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary with stable field ordering."""
        result: Dict[str, Any] = {
            "min_pages": self.min_pages,
        }
        if self.max_pages is not None:
            result["max_pages"] = self.max_pages
        if self.style_by_section is not None:
            result["style_by_section"] = self.style_by_section.to_dict()
        if self.limits_by_section is not None:
            result["limits_by_section"] = self.limits_by_section.to_dict()
        if self.mandatory_pages:
            result["mandatory_pages"] = [p.to_dict() for p in self.mandatory_pages]
        if self.optional_page_policies:
            result["optional_page_policies"] = [p.to_dict() for p in self.optional_page_policies]
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SectionConfig:
        """Deserialize from dictionary."""
        style_data = data.get("style_by_section")
        limits_data = data.get("limits_by_section")
        return cls(
            min_pages=data["min_pages"],
            max_pages=data.get("max_pages"),
            style_by_section=(
                StyleBySection.from_dict(style_data) if style_data else None
            ),
            limits_by_section=(
                LimitsBySection.from_dict(limits_data) if limits_data else None
            ),
            mandatory_pages=[
                MandatoryPage.from_dict(p)
                for p in data.get("mandatory_pages", [])
            ],
            optional_page_policies=[
                OptionalPagePolicy.from_dict(p)
                for p in data.get("optional_page_policies", [])
            ],
        )


class SectionOverride:
    """Family override for a section. Same structure as SectionConfig but no required fields.

    Per specs/schemas/ruleset.schema.json#$defs/sectionOverride.
    """

    def __init__(
        self,
        min_pages: Optional[int] = None,
        max_pages: Optional[int] = None,
        style_by_section: Optional[StyleBySection] = None,
        limits_by_section: Optional[LimitsBySection] = None,
        mandatory_pages: Optional[List[MandatoryPage]] = None,
        optional_page_policies: Optional[List[OptionalPagePolicy]] = None,
    ):
        self.min_pages = min_pages
        self.max_pages = max_pages
        self.style_by_section = style_by_section
        self.limits_by_section = limits_by_section
        self.mandatory_pages = mandatory_pages or []
        self.optional_page_policies = optional_page_policies or []

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        result: Dict[str, Any] = {}
        if self.min_pages is not None:
            result["min_pages"] = self.min_pages
        if self.max_pages is not None:
            result["max_pages"] = self.max_pages
        if self.style_by_section is not None:
            result["style_by_section"] = self.style_by_section.to_dict()
        if self.limits_by_section is not None:
            result["limits_by_section"] = self.limits_by_section.to_dict()
        if self.mandatory_pages:
            result["mandatory_pages"] = [p.to_dict() for p in self.mandatory_pages]
        if self.optional_page_policies:
            result["optional_page_policies"] = [p.to_dict() for p in self.optional_page_policies]
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SectionOverride:
        """Deserialize from dictionary."""
        style_data = data.get("style_by_section")
        limits_data = data.get("limits_by_section")
        return cls(
            min_pages=data.get("min_pages"),
            max_pages=data.get("max_pages"),
            style_by_section=(
                StyleBySection.from_dict(style_data) if style_data else None
            ),
            limits_by_section=(
                LimitsBySection.from_dict(limits_data) if limits_data else None
            ),
            mandatory_pages=[
                MandatoryPage.from_dict(p)
                for p in data.get("mandatory_pages", [])
            ],
            optional_page_policies=[
                OptionalPagePolicy.from_dict(p)
                for p in data.get("optional_page_policies", [])
            ],
        )


class FamilyOverride:
    """Per-family overrides for section configurations.

    Per specs/schemas/ruleset.schema.json#family_overrides/<family>.
    """

    def __init__(self, sections: Optional[Dict[str, SectionOverride]] = None):
        self.sections = sections or {}

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        result: Dict[str, Any] = {}
        if self.sections:
            result["sections"] = {
                name: override.to_dict()
                for name, override in sorted(self.sections.items())
            }
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> FamilyOverride:
        """Deserialize from dictionary."""
        sections_data = data.get("sections", {})
        return cls(
            sections={
                name: SectionOverride.from_dict(section_data)
                for name, section_data in sections_data.items()
            }
        )


class Ruleset(Artifact):
    """Validation ruleset configuration.

    Contains style rules, truth rules, editing rules, Hugo configuration,
    claims configuration, section requirements, and family overrides.
    Per specs/schemas/ruleset.schema.json.
    """

    def __init__(
        self,
        schema_version: str,
        style: StyleRules,
        truth: TruthRules,
        editing: EditingRules,
        sections: Dict[str, SectionConfig],
        # Optional
        hugo: Optional[HugoRules] = None,
        claims: Optional[ClaimsRules] = None,
        family_overrides: Optional[Dict[str, FamilyOverride]] = None,
    ):
        super().__init__(schema_version)
        self.style = style
        self.truth = truth
        self.editing = editing
        self.sections = sections
        self.hugo = hugo
        self.claims = claims
        self.family_overrides = family_overrides

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary with stable field ordering."""
        result = super().to_dict()
        result.update({
            "editing": self.editing.to_dict(),
            "sections": {
                name: self.sections[name].to_dict()
                for name in sorted(self.sections.keys())
            },
            "style": self.style.to_dict(),
            "truth": self.truth.to_dict(),
        })
        if self.hugo is not None:
            result["hugo"] = self.hugo.to_dict()
        if self.claims is not None:
            result["claims"] = self.claims.to_dict()
        if self.family_overrides:
            result["family_overrides"] = {
                name: override.to_dict()
                for name, override in sorted(self.family_overrides.items())
            }
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Ruleset:
        """Deserialize from dictionary."""
        sections_data = data.get("sections", {})
        sections = {
            name: SectionConfig.from_dict(section_data)
            for name, section_data in sections_data.items()
        }

        hugo_data = data.get("hugo")
        claims_data = data.get("claims")
        family_overrides_data = data.get("family_overrides")

        family_overrides = None
        if family_overrides_data:
            family_overrides = {
                name: FamilyOverride.from_dict(override_data)
                for name, override_data in family_overrides_data.items()
            }

        return cls(
            schema_version=data.get("schema_version", "1.0"),
            style=StyleRules.from_dict(data["style"]),
            truth=TruthRules.from_dict(data["truth"]),
            editing=EditingRules.from_dict(data["editing"]),
            sections=sections,
            hugo=HugoRules.from_dict(hugo_data) if hugo_data else None,
            claims=ClaimsRules.from_dict(claims_data) if claims_data else None,
            family_overrides=family_overrides,
        )

    @classmethod
    def load_from_yaml(cls, path: Path) -> Ruleset:
        """Load ruleset from YAML file.

        Args:
            path: Path to YAML file (e.g., specs/rulesets/ruleset.v1.yaml)

        Returns:
            Ruleset instance

        Raises:
            FileNotFoundError: If path does not exist
            ValueError: If YAML parsing fails
        """
        import yaml

        if not path.exists():
            raise FileNotFoundError(f"Ruleset file not found: {path}")

        content = path.read_text(encoding="utf-8")
        try:
            data = yaml.safe_load(content)
        except yaml.YAMLError as e:
            raise ValueError(f"Failed to parse YAML ruleset: {e}") from e

        if not isinstance(data, dict):
            raise ValueError(f"Ruleset YAML must be a mapping, got {type(data).__name__}")

        return cls.from_dict(data)

    def validate(self) -> bool:
        """Validate required fields and types.

        Returns:
            True if valid, raises ValueError otherwise.
        """
        required_sections = {"products", "docs", "reference", "kb", "blog"}
        missing = required_sections - set(self.sections.keys())
        if missing:
            raise ValueError(f"Missing required sections: {sorted(missing)}")

        for name, section in self.sections.items():
            if section.min_pages < 0:
                raise ValueError(
                    f"Section '{name}' min_pages must be >= 0, got {section.min_pages}"
                )
            if section.max_pages is not None and section.max_pages < 0:
                raise ValueError(
                    f"Section '{name}' max_pages must be >= 0, got {section.max_pages}"
                )

        if self.claims is not None and self.claims.marker_style is not None:
            valid_styles = {"html_comment", "frontmatter"}
            if self.claims.marker_style not in valid_styles:
                raise ValueError(
                    f"claims.marker_style must be one of {valid_styles}, "
                    f"got '{self.claims.marker_style}'"
                )

        return True
