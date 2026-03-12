from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class LauncherBaseModel(BaseModel):
    """Base model for all launcher domain objects.

    Enforces:
    - No extra fields (typo-proof).
    - Immutability (frozen).
    - Deterministic JSON serialization (sorted keys).
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        ser_json_timedelta="float",
    )

    def model_dump_json(self, **kwargs: object) -> str:  # type: ignore[override]
        """Serialize to JSON with sorted keys for deterministic output."""
        import json
        # Pydantic v2 doesn't support sort_keys; do it manually
        kwargs.pop("sort_keys", None)  # type: ignore[arg-type]
        data = self.model_dump(mode="json")
        indent = kwargs.pop("indent", None)  # type: ignore[arg-type]
        return json.dumps(data, sort_keys=True, indent=indent, ensure_ascii=False)
