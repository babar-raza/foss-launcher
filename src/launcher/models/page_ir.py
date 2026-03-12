from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from .base import LauncherBaseModel


class BlockType(str, Enum):
    """Types of content blocks within a section."""

    paragraph = "paragraph"
    code = "code"
    list = "list"
    heading = "heading"
    table = "table"
    callout = "callout"


class BlockIR(LauncherBaseModel):
    """A single content block inside a section."""

    type: BlockType
    content: str = ""
    language: str | None = None
    claim_ids: list[str] = Field(default_factory=list)
    items: list[str] = Field(default_factory=list)
    level: int | None = None


class SectionIR(LauncherBaseModel):
    """A titled section containing ordered blocks."""

    section_id: str
    heading: str
    level: int = 2
    blocks: list[BlockIR] = Field(default_factory=list)


class PageIR(LauncherBaseModel):
    """Intermediate representation of a full documentation page."""

    page_id: str
    page_role: str
    title: str
    frontmatter: dict[str, Any] = Field(default_factory=dict)
    sections: list[SectionIR] = Field(default_factory=list)
