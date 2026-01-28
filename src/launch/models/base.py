"""Base model classes for stable serialization and schema validation.

All models implement stable to_dict() and from_dict() patterns for deterministic
serialization per specs/10_determinism_and_caching.md.

Spec references:
- specs/11_state_and_events.md (State and Event models)
- specs/01_system_contract.md (Artifact contracts)
- specs/10_determinism_and_caching.md (Deterministic serialization)
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional


class BaseModel(ABC):
    """Abstract base for all data models.

    Provides stable serialization and validation hooks.
    Subclasses must implement to_dict() and from_dict().
    """

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary with stable ordering.

        Returns:
            Dictionary representation with deterministic field ordering.
        """
        pass

    @classmethod
    @abstractmethod
    def from_dict(cls, data: Dict[str, Any]) -> BaseModel:
        """Deserialize from dictionary.

        Args:
            data: Dictionary representation

        Returns:
            Model instance
        """
        pass

    def to_json(self, *, indent: int = 2, sort_keys: bool = True) -> str:
        """Serialize to JSON string with stable formatting.

        Args:
            indent: JSON indentation level
            sort_keys: Sort dictionary keys for determinism

        Returns:
            JSON string
        """
        return json.dumps(self.to_dict(), indent=indent, sort_keys=sort_keys, ensure_ascii=False) + '\n'

    @classmethod
    def from_json(cls, json_str: str) -> BaseModel:
        """Deserialize from JSON string.

        Args:
            json_str: JSON string

        Returns:
            Model instance
        """
        data = json.loads(json_str)
        return cls.from_dict(data)

    @classmethod
    def load(cls, path: Path) -> BaseModel:
        """Load model from JSON file.

        Args:
            path: Path to JSON file

        Returns:
            Model instance
        """
        return cls.from_json(path.read_text(encoding='utf-8'))

    def save(self, path: Path) -> None:
        """Save model to JSON file atomically.

        Args:
            path: Destination path
        """
        from ..io.atomic import atomic_write_text
        atomic_write_text(path, self.to_json())

    def validate_schema(self, schema: Dict[str, Any]) -> None:
        """Validate model against JSON schema.

        Args:
            schema: JSON schema dictionary

        Raises:
            ValueError: If validation fails
        """
        from ..io.schema_validation import validate
        validate(self.to_dict(), schema, context=self.__class__.__name__)


class Artifact(BaseModel):
    """Base class for all artifact models.

    Artifacts are schema-validated outputs written by workers.
    Per specs/01_system_contract.md, all artifacts must include schema_version.
    """

    def __init__(self, schema_version: str):
        self.schema_version = schema_version

    def to_dict(self) -> Dict[str, Any]:
        """Base implementation includes schema_version.

        Subclasses should call super().to_dict() and extend.
        """
        return {"schema_version": self.schema_version}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Artifact:
        """Base implementation - subclasses must override."""
        raise NotImplementedError(f"{cls.__name__}.from_dict() must be implemented")

    def validate_schema_file(self, schema_path: Path) -> None:
        """Validate artifact against schema file.

        Args:
            schema_path: Path to schema file

        Raises:
            ValueError: If validation fails
        """
        from ..io.schema_validation import load_schema, validate
        schema = load_schema(schema_path)
        validate(self.to_dict(), schema, context=str(schema_path))
