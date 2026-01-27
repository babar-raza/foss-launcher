"""
Worker W3: Snippet Curator

Inventories, tags, and selects code snippets for documentation per
specs/21_worker_contracts.md.

Implementation:
- TC-420: W3 SnippetCurator integrator (worker.py)
- TC-421: Extract doc snippets (extract_doc_snippets.py)
- TC-422: Extract code snippets (extract_code_snippets.py)
"""

from .worker import (
    execute_snippet_curator,
    SnippetCuratorError,
    SnippetCuratorExtractionError,
    SnippetCuratorMergeError,
)
from .extract_doc_snippets import extract_doc_snippets
from .extract_code_snippets import extract_code_snippets

__all__ = [
    "execute_snippet_curator",
    "extract_doc_snippets",
    "extract_code_snippets",
    "SnippetCuratorError",
    "SnippetCuratorExtractionError",
    "SnippetCuratorMergeError",
]
