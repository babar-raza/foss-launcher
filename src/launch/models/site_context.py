"""SiteContext model for W1 site context artifact.

Typed container for the site_context.json artifact produced by W1 RepoScout.
Contains site repository metadata, workflows repository metadata, and Hugo
configuration discovery results.

Spec references:
- specs/schemas/site_context.schema.json (Schema definition)
- specs/21_worker_contracts.md:54-95 (W1 RepoScout contract)
- specs/10_determinism_and_caching.md (Deterministic serialization)

TC-1030: Typed Artifact Models -- Foundation
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .base import Artifact


class RepoRef:
    """Repository reference with URL, ref, and resolved SHA.

    Used for both site and workflows repository references.
    Per specs/schemas/site_context.schema.json#site and #workflows.
    """

    def __init__(
        self,
        repo_url: str,
        requested_ref: str,
        resolved_sha: str,
        clone_path: Optional[str] = None,
    ):
        self.repo_url = repo_url
        self.requested_ref = requested_ref
        self.resolved_sha = resolved_sha
        self.clone_path = clone_path

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary with stable field ordering."""
        result: Dict[str, Any] = {
            "repo_url": self.repo_url,
            "requested_ref": self.requested_ref,
            "resolved_sha": self.resolved_sha,
        }
        if self.clone_path is not None:
            result["clone_path"] = self.clone_path
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> RepoRef:
        """Deserialize from dictionary."""
        return cls(
            repo_url=data["repo_url"],
            requested_ref=data["requested_ref"],
            resolved_sha=data["resolved_sha"],
            clone_path=data.get("clone_path"),
        )


class HugoConfigFile:
    """A single Hugo configuration file entry.

    Per specs/schemas/site_context.schema.json#hugo/config_files/items.
    """

    def __init__(
        self,
        path: str,
        sha256: str,
        bytes_: int,
        ext: str,
    ):
        self.path = path
        self.sha256 = sha256
        self.bytes = bytes_
        self.ext = ext

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "bytes": self.bytes,
            "ext": self.ext,
            "path": self.path,
            "sha256": self.sha256,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> HugoConfigFile:
        """Deserialize from dictionary."""
        return cls(
            path=data["path"],
            sha256=data["sha256"],
            bytes_=data["bytes"],
            ext=data["ext"],
        )


class BuildMatrixEntry:
    """A single build matrix entry.

    Per specs/schemas/site_context.schema.json#hugo/build_matrix/items.
    """

    def __init__(
        self,
        subdomain: str,
        family: str,
        config_path: str,
    ):
        self.subdomain = subdomain
        self.family = family
        self.config_path = config_path

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "config_path": self.config_path,
            "family": self.family,
            "subdomain": self.subdomain,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> BuildMatrixEntry:
        """Deserialize from dictionary."""
        return cls(
            subdomain=data["subdomain"],
            family=data["family"],
            config_path=data["config_path"],
        )


class HugoConfig:
    """Hugo configuration discovery results.

    Per specs/schemas/site_context.schema.json#hugo.
    """

    def __init__(
        self,
        config_root: str,
        config_files: List[HugoConfigFile],
        build_matrix: List[BuildMatrixEntry],
    ):
        self.config_root = config_root
        self.config_files = config_files
        self.build_matrix = build_matrix

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary with stable field ordering."""
        return {
            "build_matrix": [e.to_dict() for e in self.build_matrix],
            "config_files": [f.to_dict() for f in self.config_files],
            "config_root": self.config_root,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> HugoConfig:
        """Deserialize from dictionary."""
        return cls(
            config_root=data["config_root"],
            config_files=[HugoConfigFile.from_dict(f) for f in data.get("config_files", [])],
            build_matrix=[BuildMatrixEntry.from_dict(e) for e in data.get("build_matrix", [])],
        )


class SiteContext(Artifact):
    """Site context artifact produced by W1 RepoScout.

    Contains site repository metadata, workflows repository metadata, and Hugo
    configuration discovery results.
    Per specs/schemas/site_context.schema.json.
    """

    def __init__(
        self,
        schema_version: str,
        site: RepoRef,
        workflows: RepoRef,
        hugo: HugoConfig,
    ):
        super().__init__(schema_version)
        self.site = site
        self.workflows = workflows
        self.hugo = hugo

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary with stable field ordering."""
        result = super().to_dict()
        result.update({
            "hugo": self.hugo.to_dict(),
            "site": self.site.to_dict(),
            "workflows": self.workflows.to_dict(),
        })
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SiteContext:
        """Deserialize from dictionary."""
        return cls(
            schema_version=data.get("schema_version", "1.0"),
            site=RepoRef.from_dict(data["site"]),
            workflows=RepoRef.from_dict(data["workflows"]),
            hugo=HugoConfig.from_dict(data["hugo"]),
        )

    def validate(self) -> bool:
        """Validate required fields and types.

        Returns:
            True if valid, raises ValueError otherwise.
        """
        if not self.site.repo_url:
            raise ValueError("site.repo_url is required and must be non-empty")
        if not self.site.requested_ref:
            raise ValueError("site.requested_ref is required and must be non-empty")
        if len(self.site.resolved_sha) < 7:
            raise ValueError("site.resolved_sha must be at least 7 characters")
        if not self.workflows.repo_url:
            raise ValueError("workflows.repo_url is required and must be non-empty")
        if not self.workflows.requested_ref:
            raise ValueError("workflows.requested_ref is required and must be non-empty")
        if len(self.workflows.resolved_sha) < 7:
            raise ValueError("workflows.resolved_sha must be at least 7 characters")
        if not self.hugo.config_root:
            raise ValueError("hugo.config_root is required and must be non-empty")
        return True
