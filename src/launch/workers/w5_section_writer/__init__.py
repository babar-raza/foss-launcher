"""
Worker W5: Section Writer

Generates documentation sections using templates and LLM per
specs/21_worker_contracts.md.

TC-440: W5 SectionWriter implementation complete.
"""

from .worker import (
    execute_section_writer,
    SectionWriterError,
    SectionWriterClaimMissingError,
    SectionWriterSnippetMissingError,
    SectionWriterTemplateError,
    SectionWriterUnfilledTokensError,
    SectionWriterLLMError,
)

__all__ = [
    "execute_section_writer",
    "SectionWriterError",
    "SectionWriterClaimMissingError",
    "SectionWriterSnippetMissingError",
    "SectionWriterTemplateError",
    "SectionWriterUnfilledTokensError",
    "SectionWriterLLMError",
]
