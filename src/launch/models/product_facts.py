"""ProductFacts and EvidenceMap models.

These models represent extracted facts and their evidence citations.

Spec references:
- specs/03_product_facts_and_evidence.md (Facts extraction and evidence)
- specs/schemas/product_facts.schema.json (ProductFacts schema)
- specs/schemas/evidence_map.schema.json (EvidenceMap schema)
- specs/21_worker_contracts.md (W2 FactsBuilder contract)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .base import Artifact


class ProductFacts(Artifact):
    """Product facts extracted from repository.

    Contains structured facts about the product with stable claim IDs.
    Per specs/schemas/product_facts.schema.json.
    """

    def __init__(
        self,
        schema_version: str,
        product_name: str,
        product_slug: str,
        repo_url: str,
        repo_sha: str,
        positioning: Dict[str, Any],
        supported_platforms: List[str],
        claims: List[Dict[str, Any]],
        claim_groups: Dict[str, Any],
        supported_formats: List[Dict[str, Any]],
        workflows: List[Dict[str, Any]],
        api_surface_summary: Dict[str, List[str]],
        example_inventory: List[Dict[str, Any]],
        # Optional fields
        version: Optional[str] = None,
        license: Optional[Dict[str, Any]] = None,
        distribution: Optional[List[Dict[str, Any]]] = None,
        runtime_requirements: Optional[Dict[str, Any]] = None,
        dependencies: Optional[Dict[str, Any]] = None,
        limitations: Optional[List[str]] = None,
        repository_health: Optional[Dict[str, Any]] = None,
        code_structure: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(schema_version)
        self.product_name = product_name
        self.product_slug = product_slug
        self.repo_url = repo_url
        self.repo_sha = repo_sha
        self.positioning = positioning
        self.supported_platforms = supported_platforms
        self.claims = claims
        self.claim_groups = claim_groups
        self.supported_formats = supported_formats
        self.workflows = workflows
        self.api_surface_summary = api_surface_summary
        self.example_inventory = example_inventory

        # Optional fields
        self.version = version
        self.license = license
        self.distribution = distribution
        self.runtime_requirements = runtime_requirements
        self.dependencies = dependencies
        self.limitations = limitations
        self.repository_health = repository_health
        self.code_structure = code_structure

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary with stable field ordering."""
        result = super().to_dict()
        result.update({
            "product_name": self.product_name,
            "product_slug": self.product_slug,
            "repo_url": self.repo_url,
            "repo_sha": self.repo_sha,
            "positioning": self.positioning,
            "supported_platforms": self.supported_platforms,
            "claims": self.claims,
            "claim_groups": self.claim_groups,
            "supported_formats": self.supported_formats,
            "workflows": self.workflows,
            "api_surface_summary": self.api_surface_summary,
            "example_inventory": self.example_inventory,
        })

        # Add optional fields if present
        if self.version is not None:
            result["version"] = self.version
        if self.license is not None:
            result["license"] = self.license
        if self.distribution is not None:
            result["distribution"] = self.distribution
        if self.runtime_requirements is not None:
            result["runtime_requirements"] = self.runtime_requirements
        if self.dependencies is not None:
            result["dependencies"] = self.dependencies
        if self.limitations is not None:
            result["limitations"] = self.limitations
        if self.repository_health is not None:
            result["repository_health"] = self.repository_health
        if self.code_structure is not None:
            result["code_structure"] = self.code_structure

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ProductFacts:
        """Deserialize from dictionary."""
        return cls(
            schema_version=data["schema_version"],
            product_name=data["product_name"],
            product_slug=data["product_slug"],
            repo_url=data["repo_url"],
            repo_sha=data["repo_sha"],
            positioning=data["positioning"],
            supported_platforms=data["supported_platforms"],
            claims=data["claims"],
            claim_groups=data["claim_groups"],
            supported_formats=data["supported_formats"],
            workflows=data["workflows"],
            api_surface_summary=data["api_surface_summary"],
            example_inventory=data["example_inventory"],
            version=data.get("version"),
            license=data.get("license"),
            distribution=data.get("distribution"),
            runtime_requirements=data.get("runtime_requirements"),
            dependencies=data.get("dependencies"),
            limitations=data.get("limitations"),
            repository_health=data.get("repository_health"),
            code_structure=data.get("code_structure"),
        )


class EvidenceMap(Artifact):
    """Evidence map linking claims to source citations.

    Maps claim IDs to their evidence anchors in the repository.
    Per specs/schemas/evidence_map.schema.json.
    """

    def __init__(
        self,
        schema_version: str,
        repo_url: str,
        repo_sha: str,
        claims: List[Dict[str, Any]],
        contradictions: Optional[List[Dict[str, Any]]] = None,
    ):
        super().__init__(schema_version)
        self.repo_url = repo_url
        self.repo_sha = repo_sha
        self.claims = claims
        self.contradictions = contradictions or []

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary with stable field ordering."""
        result = super().to_dict()
        result.update({
            "repo_url": self.repo_url,
            "repo_sha": self.repo_sha,
            "claims": self.claims,
        })
        if self.contradictions:
            result["contradictions"] = self.contradictions
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> EvidenceMap:
        """Deserialize from dictionary."""
        return cls(
            schema_version=data["schema_version"],
            repo_url=data["repo_url"],
            repo_sha=data["repo_sha"],
            claims=data["claims"],
            contradictions=data.get("contradictions", []),
        )
