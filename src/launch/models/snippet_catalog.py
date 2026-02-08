"""SnippetCatalog model for W3 SnippetCurator output artifact.

Typed container for the snippet_catalog.json artifact produced by W3 SnippetCurator.
Contains curated code snippets extracted from documentation and source files.

Spec references:
- specs/schemas/snippet_catalog.schema.json (Schema definition)
- specs/21_worker_contracts.md:127-145 (W3 SnippetCurator contract)
- specs/10_determinism_and_caching.md (Deterministic serialization)

TC-1031: Typed Artifact Models -- Worker Models
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .base import Artifact


class SnippetSource:
    """Source location for a snippet.

    Per specs/schemas/snippet_catalog.schema.json#/$defs/source.
    """

    def __init__(
        self,
        source_type: str,
        path: Optional[str] = None,
        start_line: Optional[int] = None,
        end_line: Optional[int] = None,
        prompt_hash: Optional[str] = None,
    ):
        self.source_type = source_type
        self.path = path
        self.start_line = start_line
        self.end_line = end_line
        self.prompt_hash = prompt_hash

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary with stable field ordering."""
        result: Dict[str, Any] = {"type": self.source_type}
        if self.path is not None:
            result["path"] = self.path
        if self.start_line is not None:
            result["start_line"] = self.start_line
        if self.end_line is not None:
            result["end_line"] = self.end_line
        if self.prompt_hash is not None:
            result["prompt_hash"] = self.prompt_hash
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SnippetSource:
        """Deserialize from dictionary."""
        return cls(
            source_type=data["type"],
            path=data.get("path"),
            start_line=data.get("start_line"),
            end_line=data.get("end_line"),
            prompt_hash=data.get("prompt_hash"),
        )


class SnippetValidation:
    """Validation status for a snippet.

    Per specs/schemas/snippet_catalog.schema.json#/$defs/validation.
    """

    def __init__(
        self,
        syntax_ok: bool,
        runnable_ok: Any = "unknown",
        log_path: Optional[str] = None,
    ):
        self.syntax_ok = syntax_ok
        self.runnable_ok = runnable_ok
        self.log_path = log_path

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary with stable field ordering."""
        result: Dict[str, Any] = {
            "runnable_ok": self.runnable_ok,
            "syntax_ok": self.syntax_ok,
        }
        if self.log_path is not None:
            result["log_path"] = self.log_path
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SnippetValidation:
        """Deserialize from dictionary."""
        return cls(
            syntax_ok=data["syntax_ok"],
            runnable_ok=data.get("runnable_ok", "unknown"),
            log_path=data.get("log_path"),
        )


class SnippetRequirements:
    """Runtime requirements for a snippet.

    Per specs/schemas/snippet_catalog.schema.json#snippet/requirements.
    """

    def __init__(
        self,
        dependencies: Optional[List[str]] = None,
        runtime_notes: Optional[str] = None,
    ):
        self.dependencies = dependencies or []
        self.runtime_notes = runtime_notes

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary with stable field ordering."""
        result: Dict[str, Any] = {
            "dependencies": sorted(self.dependencies),
        }
        if self.runtime_notes is not None:
            result["runtime_notes"] = self.runtime_notes
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SnippetRequirements:
        """Deserialize from dictionary."""
        return cls(
            dependencies=data.get("dependencies", []),
            runtime_notes=data.get("runtime_notes"),
        )


class Snippet:
    """A single curated code snippet.

    Per specs/schemas/snippet_catalog.schema.json#/$defs/snippet.
    """

    def __init__(
        self,
        snippet_id: str,
        language: str,
        tags: List[str],
        source: SnippetSource,
        code: str,
        requirements: SnippetRequirements,
        validation: SnippetValidation,
    ):
        self.snippet_id = snippet_id
        self.language = language
        self.tags = tags
        self.source = source
        self.code = code
        self.requirements = requirements
        self.validation = validation

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary with stable field ordering."""
        return {
            "code": self.code,
            "language": self.language,
            "requirements": self.requirements.to_dict(),
            "snippet_id": self.snippet_id,
            "source": self.source.to_dict(),
            "tags": sorted(self.tags),
            "validation": self.validation.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Snippet:
        """Deserialize from dictionary."""
        return cls(
            snippet_id=data["snippet_id"],
            language=data["language"],
            tags=data.get("tags", []),
            source=SnippetSource.from_dict(data["source"]),
            code=data["code"],
            requirements=SnippetRequirements.from_dict(data.get("requirements", {})),
            validation=SnippetValidation.from_dict(data.get("validation", {})),
        )


class SnippetCatalog(Artifact):
    """Snippet catalog artifact produced by W3 SnippetCurator.

    Contains curated code snippets from documentation and source files.
    Per specs/schemas/snippet_catalog.schema.json.
    """

    def __init__(
        self,
        schema_version: str,
        snippets: Optional[List[Snippet]] = None,
    ):
        super().__init__(schema_version)
        self.snippets = snippets or []

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary with stable field ordering."""
        result = super().to_dict()
        result["snippets"] = [s.to_dict() for s in self.snippets]
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SnippetCatalog:
        """Deserialize from dictionary."""
        snippets_data = data.get("snippets", [])
        snippets = [Snippet.from_dict(s) for s in snippets_data]
        return cls(
            schema_version=data.get("schema_version", "1.0"),
            snippets=snippets,
        )

    def validate(self) -> bool:
        """Validate required fields and types.

        Returns:
            True if valid, raises ValueError otherwise.
        """
        if not isinstance(self.snippets, list):
            raise ValueError("snippets must be a list")
        for snippet in self.snippets:
            if not snippet.snippet_id:
                raise ValueError("Each snippet must have a non-empty snippet_id")
            if not snippet.language:
                raise ValueError("Each snippet must have a non-empty language")
            if not isinstance(snippet.tags, list):
                raise ValueError("Each snippet must have tags as a list")
            if snippet.source.source_type not in ("repo_file", "generated"):
                raise ValueError(
                    f"snippet source type must be 'repo_file' or 'generated', "
                    f"got '{snippet.source.source_type}'"
                )
        return True
