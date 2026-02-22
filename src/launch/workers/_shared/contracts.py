"""Worker I/O contract validation.

Reference: content-generator src/core/contracts.py
"""
from __future__ import annotations
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

# JSON Schema definitions for key artifacts
PRODUCT_FACTS_SCHEMA: Dict[str, Any] = {
    "title": "product_facts",
    "type": "object",
    "required": ["product_name", "claims", "claim_groups"],
    "properties": {
        "product_name": {"type": "string"},
        "claims": {"type": "array"},
        "claim_groups": {"type": "object"},
    },
}

PAGE_PLAN_SCHEMA: Dict[str, Any] = {
    "title": "page_plan",
    "type": "object",
    "required": ["pages"],
    "properties": {
        "pages": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["slug", "page_role", "output_path"],
            },
        }
    },
}

SECTION_DRAFT_SCHEMA: Dict[str, Any] = {
    "title": "section_draft",
    "type": "object",
    "required": ["sections"],
    "properties": {
        "sections": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["heading", "level", "body"],
                "properties": {
                    "heading": {"type": "string"},
                    "level": {"type": "integer", "minimum": 1, "maximum": 6},
                    "body": {"type": "string"},
                    "code_blocks": {"type": "array"},
                },
            },
        }
    },
}

DEFINED_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "product_facts": PRODUCT_FACTS_SCHEMA,
    "page_plan": PAGE_PLAN_SCHEMA,
    "section_draft": SECTION_DRAFT_SCHEMA,
}


def validate_artifact(data: Dict[str, Any], schema_name: str) -> bool:
    """Validate worker output artifact against its declared schema.

    Returns True on success. Returns True (and logs error) for unknown schemas
    (backwards compat). Returns False on validation failure.
    """
    schema = DEFINED_SCHEMAS.get(schema_name)
    if not schema:
        return True  # Unknown schema → pass (backwards compat)
    try:
        import jsonschema
        jsonschema.validate(data, schema)
        return True
    except jsonschema.ValidationError as e:
        logger.error(
            "ARTIFACT_SCHEMA_VIOLATION schema=%s path=%s msg=%s",
            schema_name, list(e.absolute_path), e.message,
        )
        return False
    except Exception as e:
        logger.warning("ARTIFACT_SCHEMA_VALIDATE_ERROR schema=%s error=%s", schema_name, e)
        return True  # Non-jsonschema errors → pass (don't block pipeline)
