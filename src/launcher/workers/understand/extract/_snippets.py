"""Snippet extraction, code block parsing, AST validation, embedding index, and doc context builder."""
from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any

from launcher.models.claims import Claim, Snippet
from launcher.models.product import ApiSurface, ProductIdentity
from launcher.models.understanding import RepoInfo
from launcher.orchestrator.worker_contract import WorkerContext
from launcher.workers.understand.file_classifier import is_vendored
from launcher.workers.understand.extract._linking import _link_snippet_to_claims

logger = logging.getLogger(__name__)

_SNIPPET_SAMPLE_MAX: int = 30
_SNIPPET_CHAR_BUDGET: int = 3_000  # Reduced from 8K: large prompts cause LLM read timeouts

_MAX_EMBEDDING_CHUNKS = 250

_RELEVANCE_SCORES: dict[str, int] = {
    "root_readme": 100,
    "nested_readme": 70,
    "root_doc": 90,
    "docs_dir": 80,
    "example_doc": 60,
    "other_doc": 40,
}

_EXCLUDED_DOC_NAMES: frozenset[str] = frozenset({
    "changelog.md", "changes.md", "history.md", "release_notes.md",
    "agents.md",  # internal AI coding conventions, not user documentation
})

# Fraction of _MAX_SOURCE_CHARS reserved for README files
_README_BUDGET_FRACTION = 0.4

# Directory names for relevance scoring
_DOC_DIR_NAMES: frozenset[str] = frozenset({"docs", "doc", "documentation"})
_EXAMPLE_DIR_NAMES: frozenset[str] = frozenset({"examples", "example", "samples", "sample", "demo", "demos"})

# ---------------------------------------------------------------------------
# Narrative extractors — split to _narratives.py (TC-3908-H4)
# ---------------------------------------------------------------------------
from launcher.workers.understand.extract._narratives import (  # noqa: F401
    _MAX_CLAIM_TEXT_LENGTH_EXTRACT,
    _MULTI_STMT_RE,
    _is_parameter_description,
    _is_code_like,
    _is_prose_like,
    _decompose_code_block_into_steps,
    _extract_use_case_narratives,
    _extract_tutorial_narratives,
)


# ---------------------------------------------------------------------------
# Core doc context and snippet extraction
# ---------------------------------------------------------------------------


def _score_doc_path(rel_path: str) -> int:
    """Return a relevance score for a documentation path."""
    lower = rel_path.lower().replace("\\", "/")
    name = Path(lower).name
    parts = Path(lower).parts

    # README files
    if name.startswith("readme"):
        if len(parts) == 1:
            return _RELEVANCE_SCORES["root_readme"]
        return _RELEVANCE_SCORES["nested_readme"]

    # Root-level docs (single path component)
    if len(parts) == 1:
        return _RELEVANCE_SCORES["root_doc"]

    # Files under a docs/ directory
    if any(p in _DOC_DIR_NAMES for p in parts[:-1]):
        return _RELEVANCE_SCORES["docs_dir"]

    # Example files
    if any(p in _EXAMPLE_DIR_NAMES for p in parts[:-1]):
        return _RELEVANCE_SCORES["example_doc"]

    return _RELEVANCE_SCORES["other_doc"]


def _build_doc_contexts(
    repo_dir: Path,
    repo_info: RepoInfo,
    repo_content: dict[str, str] | None = None,
) -> list[dict[str, str]]:
    """Build focused context strings for LLM extraction.

    Uses bulk-read repo_content when available (avoids re-reading from disk).
    Each entry has keys ``path`` and ``content`` (truncated to keep total
    under the LLM context budget).

    Applies relevance scoring to prioritise README and high-value docs,
    excludes vendored paths and changelog files, and reserves 40% of the
    budget for README files.
    """
    # Import here to avoid circular dependency at module level
    from launcher.workers.understand.extract._llm import _MAX_SOURCE_CHARS

    # --- Collect unique candidate paths ---
    added: set[str] = set()
    candidate_paths: list[str] = []

    def _add(path: str) -> None:
        if path not in added:
            candidate_paths.append(path)
            added.add(path)

    # README files from file_tree (may not be in doc_paths)
    for p in repo_info.file_tree:
        if Path(p).name.lower().startswith("readme"):
            _add(p)

    # Doc paths
    for p in repo_info.doc_paths:
        _add(p)

    # Example files
    for p in repo_info.example_paths:
        _add(p)

    # Source files (for docstring/comment extraction)
    for p in repo_info.source_paths:
        _add(p)

    # --- Filter: exclude vendored and changelog files ---
    filtered: list[str] = []
    for p in candidate_paths:
        if is_vendored(p):
            continue
        if Path(p).name.lower() in _EXCLUDED_DOC_NAMES:
            continue
        filtered.append(p)

    # --- Score and sort by relevance (descending) ---
    scored = sorted(filtered, key=lambda p: _score_doc_path(p), reverse=True)

    # --- Two-pass budget allocation ---
    readme_budget = int(_MAX_SOURCE_CHARS * _README_BUDGET_FRACTION)
    total_budget = _MAX_SOURCE_CHARS

    contexts: list[dict[str, str]] = []
    readme_used = 0
    non_readme_used = 0

    def _read_content(rel_path: str) -> str | None:
        """Try repo_content dict first, then fall back to disk read."""
        if repo_content and rel_path in repo_content:
            return repo_content[rel_path]
        file_path = repo_dir / rel_path
        if not file_path.exists() or not file_path.is_file():
            return None
        try:
            return file_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return None

    # Pass 1: README files (up to readme_budget)
    remaining_paths: list[str] = []
    for rel_path in scored:
        if Path(rel_path).name.lower().startswith("readme"):
            if readme_used >= readme_budget:
                remaining_paths.append(rel_path)
                continue
            content = _read_content(rel_path)
            if content is None:
                continue
            remaining = readme_budget - readme_used
            if len(content) > remaining:
                content = content[:remaining]
            contexts.append({"path": rel_path, "content": content})
            readme_used += len(content)
        else:
            remaining_paths.append(rel_path)

    # Pass 2: non-README docs with remaining budget (60% + unused README budget)
    pass2_budget = total_budget - readme_used
    for rel_path in remaining_paths:
        if non_readme_used >= pass2_budget:
            break
        content = _read_content(rel_path)
        if content is None:
            continue
        remaining = pass2_budget - non_readme_used
        if len(content) > remaining:
            content = content[:remaining]
        contexts.append({"path": rel_path, "content": content})
        non_readme_used += len(content)

    logger.info(
        "doc_context_budget readme_chars=%d other_chars=%d files=%d",
        readme_used,
        non_readme_used,
        len(contexts),
    )

    # Additional context enrichment: extract tutorial and use-case narratives
    enriched_contexts: list[dict[str, str]] = []
    for ctx in contexts:
        content = ctx.get("content", "")
        source_file = ctx.get("path", "")
        # Tutorial narratives (prose + code structures)
        try:
            tutorials = _extract_tutorial_narratives(content, source_file)
            enriched_contexts.extend(tutorials)
        except Exception:
            pass
        # Use-case narratives (bullet lists and prose paragraphs)
        try:
            use_cases = _extract_use_case_narratives(content, source_file)
            enriched_contexts.extend(use_cases)
        except Exception:
            pass

    if enriched_contexts:
        logger.info("doc_context_enrichment added=%d contexts", len(enriched_contexts))
        contexts.extend(enriched_contexts)

    return contexts


def _extract_snippets(
    repo_dir: Path,
    repo_info: RepoInfo,
    product: ProductIdentity,
    api_surface: ApiSurface,
    claims: list[Claim],
) -> list[Snippet]:
    """Find code blocks in docs and examples, AST-validate Python snippets.

    Scans doc files and example files for fenced code blocks (```python ...```).
    Each block is AST-validated and linked to matching claims by keyword overlap.
    """
    snippets: list[Snippet] = []

    # Collect code blocks from doc files
    all_paths = list(repo_info.doc_paths) + list(repo_info.example_paths)
    # Check for standalone example files in any source language
    from launcher.workers.understand.file_classifier import LANG_BY_EXT
    _source_exts = set(LANG_BY_EXT.keys())
    source_examples = [
        p for p in repo_info.example_paths
        if any(p.endswith(ext) for ext in _source_exts)
    ]

    # Extract fenced code blocks from markdown/rst files
    for rel_path in all_paths:
        file_path = repo_dir / rel_path
        if not file_path.exists() or not file_path.is_file():
            continue
        if not any(rel_path.endswith(ext) for ext in (".md", ".rst", ".txt", ".adoc")):
            continue

        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        blocks = _extract_fenced_code_blocks(content)
        for lang, code in blocks:
            if not code.strip():
                continue

            # Determine language — use product lang_tag as default, not "python"
            effective_lang = lang.lower() if lang else getattr(product, "lang_tag", "python") or "python"

            # Validate snippets — Python via ast, others via tree-sitter
            source_type: str = "extracted"
            if effective_lang == "python":
                if not _validate_python_syntax(code):
                    logger.debug(
                        "Skipping invalid Python snippet from %s", rel_path
                    )
                    continue
                # Normalize imports against allowlist
                code = _normalize_snippet_imports(code, api_surface, product)
            else:
                # Validate non-Python snippets via tree-sitter
                try:
                    from launcher.shared.ts_analyzer import analyzer as _ts_analyzer
                    if not _ts_analyzer.validate_snippet(code, effective_lang):
                        logger.debug(
                            "Skipping invalid %s snippet from %s", effective_lang, rel_path
                        )
                        continue
                    # Normalize non-Python imports
                    from launcher.shared.ts_analyzer import normalize_imports as _ts_normalize
                    canonical = getattr(product, "canonical_import", "") or ""
                    if canonical:
                        code = _ts_normalize(code, effective_lang, canonical)
                except ImportError:
                    pass  # tree-sitter not available — skip validation

            # Filter markdown headings stored as code (### text is valid Python comment)
            if _is_heading_only(code):
                logger.debug("Skipping heading-only snippet from %s", rel_path)
                continue

            # Link snippet to claims by keyword overlap
            linked_claim_ids = _link_snippet_to_claims(code, claims)

            snippets.append(Snippet(
                code=code.strip(),
                language=effective_lang,
                source_type=source_type,
                claim_ids=linked_claim_ids,
            ))

    # Extract entire source example files as snippets (all languages)
    for rel_path in source_examples:
        file_path = repo_dir / rel_path
        if not file_path.exists():
            continue
        try:
            code = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        if not code.strip():
            continue

        # Detect language from file extension
        file_ext = Path(rel_path).suffix.lower()
        file_lang = LANG_BY_EXT.get(file_ext, "python")

        # Validate syntax
        if file_lang == "python":
            if not _validate_python_syntax(code):
                logger.debug("Skipping invalid Python example %s", rel_path)
                continue
            code = _normalize_snippet_imports(code, api_surface, product)
        else:
            try:
                from launcher.shared.ts_analyzer import analyzer as _ts_analyzer
                if not _ts_analyzer.validate_snippet(code, file_lang):
                    logger.debug("Skipping invalid %s example %s", file_lang, rel_path)
                    continue
                from launcher.shared.ts_analyzer import normalize_imports as _ts_normalize
                canonical = getattr(product, "canonical_import", "") or ""
                if canonical:
                    code = _ts_normalize(code, file_lang, canonical)
            except ImportError:
                pass  # tree-sitter not available

        # Filter heading-only snippets
        if _is_heading_only(code):
            continue

        linked_claim_ids = _link_snippet_to_claims(code, claims)

        snippets.append(Snippet(
            code=code.strip(),
            language=file_lang,
            source_type="extracted",
            claim_ids=linked_claim_ids,
        ))

    logger.info("Extracted %d valid code snippets", len(snippets))
    return snippets


def _extract_fenced_code_blocks(content: str) -> list[tuple[str, str]]:
    """Extract fenced code blocks from markdown content.

    Returns list of (language, code) tuples.
    """
    blocks: list[tuple[str, str]] = []
    pattern = re.compile(r"```(\w*)\s*\n(.*?)```", re.DOTALL)
    for match in pattern.finditer(content):
        lang = match.group(1) or ""
        code = match.group(2)
        blocks.append((lang, code))
    return blocks


def _is_heading_only(code: str) -> bool:
    """Return True if the entire code block is a single markdown heading.

    Markdown headings (### text) are valid Python syntax because # starts a
    comment. Without this filter, docs with ```python\\n### Heading\\n``` blocks
    inject heading text as code snippets with language: python.
    """
    stripped = code.strip()
    return bool(re.match(r"^#{1,6}\s+\S", stripped)) and "\n" not in stripped


def _validate_python_syntax(code: str) -> bool:
    """Validate Python code via ast.parse(). Returns True if syntax is valid."""
    import ast
    try:
        ast.parse(code)
        return True
    except SyntaxError:
        return False


def _normalize_snippet_imports(
    code: str,
    api_surface: ApiSurface,
    product: ProductIdentity,
) -> str:
    """Normalize all import statements to use the canonical import path.

    Handles: import X, import X as Y, from X import Y, and removes
    non-FOSS modules like aspose.pydrawing.
    """
    if not product.canonical_import:
        return code

    canonical = product.canonical_import
    lines = code.split("\n")
    normalized: list[str] = []

    for line in lines:
        import_match = re.match(r"^(\s*)(import|from)\s+([\w.]+)", line)
        if import_match:
            indent = import_match.group(1)
            keyword = import_match.group(2)
            module = import_match.group(3)

            # Remove non-FOSS modules
            if "pydrawing" in module.lower():
                continue

            # Rewrite aspose.* imports to canonical
            if module.startswith("aspose.") or module == "aspose":
                if keyword == "import":
                    rest = line[import_match.end():]
                    normalized.append(f"{indent}import {canonical}{rest}")
                else:
                    after_module = line[import_match.end():]
                    normalized.append(f"{indent}from {canonical}{after_module}")
                continue

        normalized.append(line)

    return "\n".join(normalized)


def _chunk_text(text: str, max_chars: int = 500) -> list[str]:
    """Split text into chunks of approximately max_chars at sentence boundaries."""
    if not text or len(text) <= max_chars:
        return [text] if text else []
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        if end < len(text):
            # Try to break at sentence boundary
            for sep in (". ", ".\n", "\n\n", "\n", " "):
                brk = text.rfind(sep, start + max_chars // 2, end)
                if brk > start:
                    end = brk + len(sep)
                    break
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = end
    return chunks


def _build_embedding_index(
    claims: list[Claim],
    doc_contexts: list[dict[str, Any]],
    context: WorkerContext,
) -> None:
    """Phase B.4: Build embedding index for claims + doc chunks.

    Writes ``embedding_index.json`` as a side artifact. Uses API embeddings
    if configured, otherwise falls back to TF-IDF vectors.
    """
    from launcher.shared.embeddings import EmbeddingClient, embed_texts

    texts: dict[str, str] = {}
    for claim in claims:
        texts[f"claim:{claim.claim_id}"] = claim.text

    chunk_count = 0
    for ctx in doc_contexts:
        content = ctx.get("content", "")
        path = ctx.get("path", "unknown")
        for i, chunk in enumerate(_chunk_text(content)):
            if chunk_count >= _MAX_EMBEDDING_CHUNKS:
                break
            texts[f"doc:{path}:{i}"] = chunk
            chunk_count += 1
        if chunk_count >= _MAX_EMBEDDING_CHUNKS:
            break

    if not texts:
        logger.info("Phase B.4: no texts to embed, skipping")
        return

    # Try API client if embedding endpoint is configured
    client = None
    llm_cfg = getattr(context, "llm_config", None)
    if llm_cfg is not None:
        embedding_cfg = getattr(llm_cfg, "embedding", None)
        if embedding_cfg is not None and embedding_cfg.base_url:
            api_key = os.environ.get(
                getattr(llm_cfg, "api_key_env", None) or "litellm_key", ""
            )
            client = EmbeddingClient(
                base_url=embedding_cfg.base_url,
                model=embedding_cfg.model,
                api_key=api_key,
            )
            if not client.is_available():
                logger.warning("embedding_api_unavailable_falling_back_to_tfidf")
                client = None

    embedding_index = embed_texts(texts, client=client)
    if embedding_index is None:
        logger.info("Phase B.4: embedding index empty, skipping artifact")
        return

    # Write artifact
    store = getattr(context, "store", None)
    if store is not None:
        artifacts_dir = getattr(store, "artifacts_dir", None)
        if artifacts_dir is not None:
            from pathlib import Path as _Path
            out = _Path(artifacts_dir) / "embedding_index.json"
            embedding_index.save(out)
            logger.info(
                "Phase B.4: embedding index saved (%d vectors) -> %s",
                len(embedding_index), out,
            )
            return

    # Fallback: try run_dir
    run_dir = getattr(context, "run_dir", None)
    if run_dir is not None:
        out = Path(run_dir) / "artifacts" / "embedding_index.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        embedding_index.save(out)
        logger.info(
            "Phase B.4: embedding index saved (%d vectors) -> %s",
            len(embedding_index), out,
        )
