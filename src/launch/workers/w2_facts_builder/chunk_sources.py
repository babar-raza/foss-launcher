"""KB source chunking for retrieval-augmented generation (TC-2383).

Splits documentation files at semantic boundaries (headings, paragraphs).
Complements W3 SnippetCurator -- W3 handles code files via AST; this handles
prose documents (markdown, rst, txt, yaml) and Python source (class/function
docstrings) for grounding W5 generators.
"""
from __future__ import annotations

import ast
import hashlib
import re
from pathlib import Path
from typing import Any, Dict, Iterator, List

MIN_CHUNK_TOKENS = 30
TARGET_CHUNK_TOKENS = 1000
OVERLAP_TOKENS = 200
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5MB cap

# Prose/config formats + Python source (docstrings provide grounding for W5)
CHUNK_EXTENSIONS = {".md", ".rst", ".txt", ".yaml", ".yml", ".py"}

SKIP_PATTERNS = [
    r"test_", r"_test\.", r"\.min\.js$", r"node_modules", r"\.venv",
    r"__pycache__", r"\.git", r"\.pytest_cache",
    # Internal governance/CI files — not user-facing documentation
    r"AGENTS\.md$", r"CONTRIBUTING\.md$", r"CODEOWNERS$",
    r"\.github[/\\]", r"\.claude[/\\]", r"\.cursor[/\\]",
    r"CODE_OF_CONDUCT", r"SECURITY\.md$",
    r"[/\\]plans[/\\]", r"[/\\]reports[/\\]agents[/\\]",
]


def chunk_source_files(repo_dir: Path, max_chunks: int = 2000) -> List[Dict[str, Any]]:
    """Chunk prose documentation files at semantic boundaries.

    Returns list of chunk dicts:
        chunk_id, file_path, text, heading_context, token_count
    """
    chunks: List[Dict[str, Any]] = []
    for file_path in _iter_source_files(repo_dir):
        try:
            file_chunks = _chunk_file(file_path, repo_dir)
            chunks.extend(file_chunks)
            if len(chunks) >= max_chunks:
                chunks = chunks[:max_chunks]
                break
        except Exception:
            continue
    return chunks


def retrieve_relevant_chunks(query: str, chunks: List[Dict], top_k: int = 5) -> List[Dict]:
    """Retrieve top-K chunks most relevant to a query using TF-IDF cosine similarity.

    Falls back to first K chunks if embeddings unavailable.
    """
    if not chunks:
        return []
    try:
        from launch.workers._shared.embeddings import tfidf_cosine_similarity
        scores = [tfidf_cosine_similarity(query, c["text"]) for c in chunks]
        ranked = sorted(zip(scores, chunks), key=lambda x: -x[0])
        return [c for _, c in ranked[:top_k]]
    except Exception:
        return chunks[:top_k]


def _iter_source_files(repo_dir: Path) -> Iterator[Path]:
    for path in sorted(repo_dir.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix not in CHUNK_EXTENSIONS:
            continue
        rel = str(path.relative_to(repo_dir))
        if any(re.search(p, rel) for p in SKIP_PATTERNS):
            continue
        try:
            if path.stat().st_size > MAX_FILE_SIZE_BYTES:
                continue
        except OSError:
            continue
        yield path


def _chunk_file(file_path: Path, repo_dir: Path) -> List[Dict[str, Any]]:
    try:
        text = file_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    if not text.strip():
        return []
    rel_path = str(file_path.relative_to(repo_dir))
    suffix = file_path.suffix.lower()
    if suffix == ".py":
        return _chunk_python_file(text, rel_path)
    elif suffix in {".yaml", ".yml"}:
        return _chunk_yaml(text, rel_path)
    else:
        return _chunk_by_headings(text, rel_path)


def _chunk_by_headings(text: str, rel_path: str) -> List[Dict[str, Any]]:
    """Split markdown/rst/txt at H1-H3 heading boundaries."""
    sections = re.split(r'(?m)(?=^#{1,3} )', text)
    chunks = []
    for section in sections:
        section = section.strip()
        if not section:
            continue
        m = re.match(r'^(#{1,3}) (.+)', section)
        heading_context = m.group(2).strip() if m else ""
        token_count = len(section.split())
        if token_count < MIN_CHUNK_TOKENS:
            continue
        if token_count <= TARGET_CHUNK_TOKENS:
            chunks.append(_make_chunk(section, rel_path, heading_context))
        else:
            sub_chunks = _sub_chunk_paragraphs(section, rel_path, heading_context)
            chunks.extend(sub_chunks)
    return chunks


def _sub_chunk_paragraphs(
    section_text: str,
    rel_path: str,
    heading_context: str,
) -> List[Dict[str, Any]]:
    """Split a long section at paragraph boundaries."""
    paragraphs = re.split(r'\n\n+', section_text)
    chunks = []
    current_parts: List[str] = []
    current_tokens = 0
    for para in paragraphs:
        para_tokens = len(para.split())
        if current_tokens + para_tokens > TARGET_CHUNK_TOKENS and current_parts:
            chunks.append(_make_chunk("\n\n".join(current_parts), rel_path, heading_context))
            current_parts = [para]
            current_tokens = para_tokens
        else:
            current_parts.append(para)
            current_tokens += para_tokens
    if current_parts and current_tokens >= MIN_CHUNK_TOKENS:
        chunks.append(_make_chunk("\n\n".join(current_parts), rel_path, heading_context))
    return chunks


def _chunk_yaml(text: str, rel_path: str, lines_per_chunk: int = 50) -> List[Dict[str, Any]]:
    """Chunk YAML in blocks of N lines."""
    lines = text.splitlines()
    chunks = []
    for i in range(0, len(lines), lines_per_chunk):
        block = "\n".join(lines[i:i + lines_per_chunk]).strip()
        if len(block.split()) < MIN_CHUNK_TOKENS:
            continue
        m = re.search(r'^([a-zA-Z_][a-zA-Z0-9_]*):', block, re.MULTILINE)
        heading_context = m.group(1) if m else ""
        chunks.append(_make_chunk(block, rel_path, heading_context))
    return chunks


def _chunk_python_file(text: str, rel_path: str) -> List[Dict[str, Any]]:
    """Extract class/function definitions with docstrings as chunks.

    Each chunk = signature line + docstring. Provides API grounding for W5
    without duplicating the full code extraction done by W3 SnippetCurator.
    """
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []

    chunks: List[Dict[str, Any]] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        docstring = ast.get_docstring(node)
        if not docstring:
            continue
        # Build signature line
        if isinstance(node, ast.ClassDef):
            sig = f"class {node.name}"
            bases = [_unparse_name(b) for b in node.bases]
            if bases:
                sig += f"({', '.join(bases)})"
        else:
            sig = f"def {node.name}(...)"
        chunk_text = f"{sig}\n\n{docstring}"
        if len(chunk_text.split()) < MIN_CHUNK_TOKENS:
            continue
        chunks.append(_make_chunk(chunk_text, rel_path, node.name))
    return chunks


def _unparse_name(node: ast.expr) -> str:
    """Best-effort name extraction from an AST expression node."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{_unparse_name(node.value)}.{node.attr}"
    try:
        return ast.unparse(node)
    except Exception:
        return "..."


def _make_chunk(text: str, rel_path: str, heading_context: str) -> Dict[str, Any]:
    chunk_id = hashlib.sha256(
        f"{rel_path}:{heading_context}:{text[:60]}".encode()
    ).hexdigest()[:16]
    return {
        "chunk_id": chunk_id,
        "file_path": rel_path,
        "text": text,
        "heading_context": heading_context,
        "token_count": len(text.split()),
    }
