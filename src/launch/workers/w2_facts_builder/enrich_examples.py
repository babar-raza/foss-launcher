"""TC-1044: Example enrichment for W2 FactsBuilder.

Enriches discovered examples with metadata extracted from code analysis:
description from docstrings/comments, complexity from LOC, and audience
level inference.

Spec: specs/05_example_curation.md (Example enrichment)
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List


def enrich_example(
    example_file: Dict[str, Any],
    repo_dir: Path,
    claims: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Enrich example with metadata from code analysis.

    Args:
        example_file: Example file dictionary from discovered_examples
        repo_dir: Repository root directory
        claims: List of claims (for future cross-referencing)

    Returns:
        Enriched example dictionary with description, complexity, audience_level
    """
    file_path = repo_dir / example_file.get('path', '')
    content = ""
    try:
        if file_path.exists():
            content = file_path.read_text(encoding='utf-8', errors='ignore')
    except Exception:
        pass

    description = _extract_description_from_code(content)
    complexity = _analyze_code_complexity(content)
    audience_level = _infer_audience_level(complexity, description)

    result = {
        "example_id": example_file.get('example_id', ''),
        "title": example_file.get('title', example_file.get('path', '').split('/')[-1]),
        "file_path": example_file.get('path', ''),
        "description": description or "Code example demonstrating product usage",
        "complexity": complexity,
        "audience_level": audience_level,
        "tags": example_file.get('tags', []),
        "primary_snippet_id": example_file.get('primary_snippet_id', ''),
    }
    return result


def _extract_description_from_code(content: str) -> str:
    """Extract description from code docstrings or comments.

    Checks (in order):
    1. Triple-double-quoted docstring
    2. Triple-single-quoted docstring
    3. First line comment (# ...)

    Args:
        content: File content

    Returns:
        Extracted description or empty string
    """
    if not content:
        return ""
    match = re.search(r'"""(.*?)"""', content, re.DOTALL)
    if match:
        return match.group(1).strip().split('\n')[0]
    match = re.search(r"'''(.*?)'''", content, re.DOTALL)
    if match:
        return match.group(1).strip().split('\n')[0]
    match = re.search(r'#\s*(.*?)$', content, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return ""


def _analyze_code_complexity(content: str) -> str:
    """Analyze code complexity based on non-empty, non-comment lines.

    Args:
        content: File content

    Returns:
        Complexity level: 'trivial', 'simple', 'moderate', or 'complex'
    """
    if not content:
        return "trivial"
    lines = [l for l in content.split('\n') if l.strip() and not l.strip().startswith('#')]
    loc = len(lines)
    if loc < 10:
        return "trivial"
    elif loc < 50:
        return "simple"
    elif loc < 200:
        return "moderate"
    return "complex"


def _infer_audience_level(complexity: str, description: str) -> str:
    """Infer audience level from complexity and description keywords.

    Args:
        complexity: Complexity level string
        description: Example description

    Returns:
        Audience level: 'beginner', 'intermediate', or 'advanced'
    """
    desc_lower = description.lower()
    if complexity in ["trivial", "simple"] and any(
        kw in desc_lower for kw in ['beginner', 'basic', 'intro', 'hello']
    ):
        return "beginner"
    elif any(kw in desc_lower for kw in ['advanced', 'expert', 'custom', 'complex']):
        return "advanced"
    elif complexity in ["trivial", "simple"]:
        return "beginner"
    return "intermediate"
