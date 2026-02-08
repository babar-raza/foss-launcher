"""PatchBundle model for W6 LinkerAndPatcher output artifact.

Typed container for the patch_bundle.json artifact produced by W6 LinkerAndPatcher.
Contains the set of patches (create, update, delete) to be applied to the site worktree.

Spec references:
- specs/schemas/patch_bundle.schema.json (Schema definition)
- specs/08_patch_engine.md (Patch application algorithm)
- specs/21_worker_contracts.md:228-251 (W6 LinkerAndPatcher contract)
- specs/10_determinism_and_caching.md (Deterministic serialization)

TC-1031: Typed Artifact Models -- Worker Models
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .base import Artifact


VALID_PATCH_TYPES = {
    "create_file",
    "update_file_range",
    "update_by_anchor",
    "update_frontmatter_keys",
    "delete_file",
}


class Patch:
    """A single patch operation.

    Per specs/schemas/patch_bundle.schema.json#/$defs/patch.
    """

    def __init__(
        self,
        patch_id: str,
        patch_type: str,
        path: str,
        content_hash: str,
        # Optional fields (depend on patch_type)
        new_content: Optional[str] = None,
        anchor: Optional[str] = None,
        start_line: Optional[int] = None,
        end_line: Optional[int] = None,
        frontmatter_updates: Optional[Dict[str, Any]] = None,
        expected_before_hash: Optional[str] = None,
    ):
        self.patch_id = patch_id
        self.patch_type = patch_type
        self.path = path
        self.content_hash = content_hash
        self.new_content = new_content
        self.anchor = anchor
        self.start_line = start_line
        self.end_line = end_line
        self.frontmatter_updates = frontmatter_updates
        self.expected_before_hash = expected_before_hash

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary with stable field ordering."""
        result: Dict[str, Any] = {
            "content_hash": self.content_hash,
            "patch_id": self.patch_id,
            "path": self.path,
            "type": self.patch_type,
        }
        if self.new_content is not None:
            result["new_content"] = self.new_content
        if self.anchor is not None:
            result["anchor"] = self.anchor
        if self.start_line is not None:
            result["start_line"] = self.start_line
        if self.end_line is not None:
            result["end_line"] = self.end_line
        if self.frontmatter_updates is not None:
            result["frontmatter_updates"] = self.frontmatter_updates
        if self.expected_before_hash is not None:
            result["expected_before_hash"] = self.expected_before_hash
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Patch:
        """Deserialize from dictionary."""
        return cls(
            patch_id=data["patch_id"],
            patch_type=data["type"],
            path=data["path"],
            content_hash=data["content_hash"],
            new_content=data.get("new_content"),
            anchor=data.get("anchor"),
            start_line=data.get("start_line"),
            end_line=data.get("end_line"),
            frontmatter_updates=data.get("frontmatter_updates"),
            expected_before_hash=data.get("expected_before_hash"),
        )


class PatchBundle(Artifact):
    """Patch bundle artifact produced by W6 LinkerAndPatcher.

    Contains the set of patches to apply to the site worktree.
    Per specs/schemas/patch_bundle.schema.json.
    """

    def __init__(
        self,
        schema_version: str,
        patches: Optional[List[Patch]] = None,
    ):
        super().__init__(schema_version)
        self.patches = patches or []

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary with stable field ordering."""
        result = super().to_dict()
        result["patches"] = [p.to_dict() for p in self.patches]
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PatchBundle:
        """Deserialize from dictionary."""
        patches_data = data.get("patches", [])
        patches = [Patch.from_dict(p) for p in patches_data]
        return cls(
            schema_version=data.get("schema_version", "1.0"),
            patches=patches,
        )

    def validate(self) -> bool:
        """Validate required fields and types.

        Returns:
            True if valid, raises ValueError otherwise.
        """
        if not isinstance(self.patches, list):
            raise ValueError("patches must be a list")
        for patch in self.patches:
            if not patch.patch_id:
                raise ValueError("Each patch must have a non-empty patch_id")
            if patch.patch_type not in VALID_PATCH_TYPES:
                raise ValueError(
                    f"patch type must be one of {VALID_PATCH_TYPES}, "
                    f"got '{patch.patch_type}'"
                )
            if not patch.path:
                raise ValueError("Each patch must have a non-empty path")
            if not patch.content_hash:
                raise ValueError("Each patch must have a non-empty content_hash")
        return True
