"""RepoInventory model for W1 repo inventory artifact.

Typed container for the repo_inventory.json artifact produced by W1 RepoScout.
Contains repository fingerprint, file tree, language detection, and metadata.

Spec references:
- specs/schemas/repo_inventory.schema.json (Schema definition)
- specs/02_repo_ingestion.md (Repo profiling)
- specs/21_worker_contracts.md:54-95 (W1 RepoScout contract)
- specs/10_determinism_and_caching.md (Deterministic serialization)

TC-1030: Typed Artifact Models -- Foundation
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .base import Artifact


class RepoFingerprint:
    """Repository fingerprint metadata.

    Per specs/schemas/repo_inventory.schema.json#fingerprint.
    """

    def __init__(
        self,
        default_branch: Optional[str] = None,
        latest_release_tag: Optional[str] = None,
        license_path: Optional[str] = None,
        primary_languages: Optional[List[str]] = None,
    ):
        self.default_branch = default_branch
        self.latest_release_tag = latest_release_tag
        self.license_path = license_path
        self.primary_languages = primary_languages or []

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary with stable field ordering."""
        result: Dict[str, Any] = {}
        if self.default_branch is not None:
            result["default_branch"] = self.default_branch
        if self.latest_release_tag is not None:
            result["latest_release_tag"] = self.latest_release_tag
        if self.license_path is not None:
            result["license_path"] = self.license_path
        result["primary_languages"] = sorted(self.primary_languages)
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> RepoFingerprint:
        """Deserialize from dictionary."""
        return cls(
            default_branch=data.get("default_branch"),
            latest_release_tag=data.get("latest_release_tag"),
            license_path=data.get("license_path"),
            primary_languages=data.get("primary_languages", []),
        )


class PublicApiScope:
    """Public API scope definition.

    Per specs/schemas/repo_inventory.schema.json#repo_profile/public_api_scope.
    """

    def __init__(
        self,
        public_roots: Optional[List[str]] = None,
        internal_prefixes: Optional[List[str]] = None,
        policy: Optional[str] = None,
    ):
        self.public_roots = public_roots or []
        self.internal_prefixes = internal_prefixes or []
        self.policy = policy

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        result: Dict[str, Any] = {}
        if self.public_roots:
            result["public_roots"] = sorted(self.public_roots)
        if self.internal_prefixes:
            result["internal_prefixes"] = sorted(self.internal_prefixes)
        if self.policy is not None:
            result["policy"] = self.policy
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PublicApiScope:
        """Deserialize from dictionary."""
        return cls(
            public_roots=data.get("public_roots", []),
            internal_prefixes=data.get("internal_prefixes", []),
            policy=data.get("policy"),
        )


class RepoProfile:
    """Repository profile with build and language information.

    Per specs/schemas/repo_inventory.schema.json#repo_profile.
    """

    def __init__(
        self,
        platform_family: str,
        primary_languages: List[str],
        build_systems: List[str],
        package_manifests: List[str],
        recommended_test_commands: List[str],
        example_locator: str,
        doc_locator: str,
        # Optional fields
        source_layout: Optional[str] = None,
        public_api_entrypoints: Optional[List[str]] = None,
        example_generation_hints: Optional[List[str]] = None,
        repo_archetype: Optional[str] = None,
        public_api_scope: Optional[PublicApiScope] = None,
    ):
        self.platform_family = platform_family
        self.primary_languages = primary_languages
        self.build_systems = build_systems
        self.package_manifests = package_manifests
        self.recommended_test_commands = recommended_test_commands
        self.example_locator = example_locator
        self.doc_locator = doc_locator
        self.source_layout = source_layout
        self.public_api_entrypoints = public_api_entrypoints
        self.example_generation_hints = example_generation_hints
        self.repo_archetype = repo_archetype
        self.public_api_scope = public_api_scope

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary with stable field ordering."""
        result: Dict[str, Any] = {
            "build_systems": sorted(self.build_systems),
            "doc_locator": self.doc_locator,
            "example_locator": self.example_locator,
            "package_manifests": sorted(self.package_manifests),
            "platform_family": self.platform_family,
            "primary_languages": sorted(self.primary_languages),
            "recommended_test_commands": sorted(self.recommended_test_commands),
        }
        if self.source_layout is not None:
            result["source_layout"] = self.source_layout
        if self.public_api_entrypoints is not None:
            result["public_api_entrypoints"] = sorted(self.public_api_entrypoints)
        if self.example_generation_hints is not None:
            result["example_generation_hints"] = sorted(self.example_generation_hints)
        if self.repo_archetype is not None:
            result["repo_archetype"] = self.repo_archetype
        if self.public_api_scope is not None:
            result["public_api_scope"] = self.public_api_scope.to_dict()
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> RepoProfile:
        """Deserialize from dictionary."""
        public_api_scope_data = data.get("public_api_scope")
        return cls(
            platform_family=data["platform_family"],
            primary_languages=data["primary_languages"],
            build_systems=data["build_systems"],
            package_manifests=data["package_manifests"],
            recommended_test_commands=data["recommended_test_commands"],
            example_locator=data["example_locator"],
            doc_locator=data["doc_locator"],
            source_layout=data.get("source_layout"),
            public_api_entrypoints=data.get("public_api_entrypoints"),
            example_generation_hints=data.get("example_generation_hints"),
            repo_archetype=data.get("repo_archetype"),
            public_api_scope=(
                PublicApiScope.from_dict(public_api_scope_data)
                if public_api_scope_data is not None
                else None
            ),
        )


class PhantomPath:
    """A path claimed in documentation but not present in repo.

    Per specs/schemas/repo_inventory.schema.json#phantom_paths/items.
    """

    def __init__(
        self,
        claimed_path: str,
        source_file: str,
        source_line: Optional[int] = None,
        claim_context: Optional[str] = None,
    ):
        self.claimed_path = claimed_path
        self.source_file = source_file
        self.source_line = source_line
        self.claim_context = claim_context

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        result: Dict[str, Any] = {
            "claimed_path": self.claimed_path,
            "source_file": self.source_file,
        }
        if self.source_line is not None:
            result["source_line"] = self.source_line
        if self.claim_context is not None:
            result["claim_context"] = self.claim_context
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PhantomPath:
        """Deserialize from dictionary."""
        return cls(
            claimed_path=data["claimed_path"],
            source_file=data["source_file"],
            source_line=data.get("source_line"),
            claim_context=data.get("claim_context"),
        )


class DocEntrypointDetail:
    """Detailed information about a discovered documentation file.

    Per specs/schemas/repo_inventory.schema.json#doc_entrypoint_details/items.
    """

    def __init__(
        self,
        path: str,
        doc_type: str,
        evidence_priority: Optional[str] = None,
    ):
        self.path = path
        self.doc_type = doc_type
        self.evidence_priority = evidence_priority

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        result: Dict[str, Any] = {
            "doc_type": self.doc_type,
            "path": self.path,
        }
        if self.evidence_priority is not None:
            result["evidence_priority"] = self.evidence_priority
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> DocEntrypointDetail:
        """Deserialize from dictionary."""
        return cls(
            path=data["path"],
            doc_type=data["doc_type"],
            evidence_priority=data.get("evidence_priority"),
        )


class RepoInventory(Artifact):
    """Repository inventory artifact produced by W1 RepoScout.

    Contains repository fingerprint, file tree, language detection, and metadata.
    Per specs/schemas/repo_inventory.schema.json.
    """

    def __init__(
        self,
        schema_version: str,
        repo_url: str,
        repo_sha: str,
        fingerprint: RepoFingerprint,
        repo_profile: RepoProfile,
        paths: List[str],
        doc_entrypoints: List[str],
        example_paths: List[str],
        # Optional fields
        source_roots: Optional[List[str]] = None,
        test_roots: Optional[List[str]] = None,
        doc_roots: Optional[List[str]] = None,
        example_roots: Optional[List[str]] = None,
        binary_assets: Optional[List[str]] = None,
        phantom_paths: Optional[List[PhantomPath]] = None,
        inferred_product_type: Optional[str] = None,
        doc_entrypoint_details: Optional[List[DocEntrypointDetail]] = None,
        # Extra fields from fingerprint computation (not in schema but in worker output)
        repo_fingerprint: Optional[str] = None,
        file_count: Optional[int] = None,
        total_bytes: Optional[int] = None,
    ):
        super().__init__(schema_version)
        self.repo_url = repo_url
        self.repo_sha = repo_sha
        self.fingerprint = fingerprint
        self.repo_profile = repo_profile
        self.paths = paths
        self.doc_entrypoints = doc_entrypoints
        self.example_paths = example_paths
        # Optional
        self.source_roots = source_roots or []
        self.test_roots = test_roots or []
        self.doc_roots = doc_roots or []
        self.example_roots = example_roots or []
        self.binary_assets = binary_assets or []
        self.phantom_paths = phantom_paths or []
        self.inferred_product_type = inferred_product_type
        self.doc_entrypoint_details = doc_entrypoint_details
        self.repo_fingerprint = repo_fingerprint
        self.file_count = file_count
        self.total_bytes = total_bytes

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary with stable field ordering."""
        result = super().to_dict()
        result.update({
            "repo_url": self.repo_url,
            "repo_sha": self.repo_sha,
            "fingerprint": self.fingerprint.to_dict(),
            "repo_profile": self.repo_profile.to_dict(),
            "paths": sorted(self.paths),
            "doc_entrypoints": sorted(self.doc_entrypoints),
            "example_paths": sorted(self.example_paths),
        })

        # Optional list fields (always include if non-empty)
        if self.source_roots:
            result["source_roots"] = sorted(self.source_roots)
        if self.test_roots:
            result["test_roots"] = sorted(self.test_roots)
        if self.doc_roots:
            result["doc_roots"] = sorted(self.doc_roots)
        if self.example_roots:
            result["example_roots"] = sorted(self.example_roots)
        if self.binary_assets:
            result["binary_assets"] = sorted(self.binary_assets)
        if self.phantom_paths:
            result["phantom_paths"] = [p.to_dict() for p in self.phantom_paths]
        if self.inferred_product_type is not None:
            result["inferred_product_type"] = self.inferred_product_type
        if self.doc_entrypoint_details is not None:
            result["doc_entrypoint_details"] = [d.to_dict() for d in self.doc_entrypoint_details]

        # Extra fingerprint fields
        if self.repo_fingerprint is not None:
            result["repo_fingerprint"] = self.repo_fingerprint
        if self.file_count is not None:
            result["file_count"] = self.file_count
        if self.total_bytes is not None:
            result["total_bytes"] = self.total_bytes

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> RepoInventory:
        """Deserialize from dictionary."""
        fingerprint_data = data.get("fingerprint", {})
        repo_profile_data = data.get("repo_profile", {})

        phantom_paths_data = data.get("phantom_paths", [])
        phantom_paths = []
        for p in phantom_paths_data:
            if isinstance(p, dict):
                phantom_paths.append(PhantomPath.from_dict(p))

        doc_details_data = data.get("doc_entrypoint_details")
        doc_details = None
        if doc_details_data is not None:
            doc_details = [DocEntrypointDetail.from_dict(d) for d in doc_details_data]

        return cls(
            schema_version=data.get("schema_version", "1.0"),
            repo_url=data["repo_url"],
            repo_sha=data["repo_sha"],
            fingerprint=RepoFingerprint.from_dict(fingerprint_data),
            repo_profile=RepoProfile.from_dict(repo_profile_data),
            paths=data.get("paths", []),
            doc_entrypoints=data.get("doc_entrypoints", []),
            example_paths=data.get("example_paths", []),
            source_roots=data.get("source_roots", []),
            test_roots=data.get("test_roots", []),
            doc_roots=data.get("doc_roots", []),
            example_roots=data.get("example_roots", []),
            binary_assets=data.get("binary_assets", []),
            phantom_paths=phantom_paths,
            inferred_product_type=data.get("inferred_product_type"),
            doc_entrypoint_details=doc_details,
            repo_fingerprint=data.get("repo_fingerprint"),
            file_count=data.get("file_count"),
            total_bytes=data.get("total_bytes"),
        )

    def validate(self) -> bool:
        """Validate required fields and types.

        Returns:
            True if valid, raises ValueError otherwise.
        """
        if not self.repo_url:
            raise ValueError("repo_url is required and must be non-empty")
        if not self.repo_sha:
            raise ValueError("repo_sha is required and must be non-empty")
        if not isinstance(self.paths, list):
            raise ValueError("paths must be a list")
        if not isinstance(self.doc_entrypoints, list):
            raise ValueError("doc_entrypoints must be a list")
        if not isinstance(self.example_paths, list):
            raise ValueError("example_paths must be a list")
        if self.inferred_product_type is not None:
            valid_types = {"sdk", "library", "cli", "service", "plugin", "tool", "other"}
            if self.inferred_product_type not in valid_types:
                raise ValueError(
                    f"inferred_product_type must be one of {valid_types}, "
                    f"got '{self.inferred_product_type}'"
                )
        return True
