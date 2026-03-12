"""Shared Jaccard similarity (D-4 pre-generation check + Gate 19 reuse)."""
from __future__ import annotations
import re
from typing import List, Set

SIMILARITY_THRESHOLD = 0.6

STOPWORDS = frozenset({
    "the", "and", "or", "of", "a", "an", "in", "is", "to", "for",
    "with", "that", "this", "are", "be", "have", "from", "by", "at",
    "as", "on", "it", "its", "not", "but", "can", "you", "we",
    "our", "your", "will", "all", "use", "used", "using", "how",
    "when", "what", "where", "which", "then", "also", "more",
    "than", "about", "has", "any", "each", "into", "between",
})


def compute_word_set(text: str) -> Set[str]:
    """Compute a filtered word set for Jaccard comparison."""
    body = strip_frontmatter(text)
    body = strip_code_blocks(body)
    return set(_tokenize(body))


def jaccard_similarity(set_a: Set[str], set_b: Set[str]) -> float:
    """Compute Jaccard similarity between two word sets."""
    if not set_a or not set_b:
        return 0.0
    union_size = len(set_a | set_b)
    return len(set_a & set_b) / union_size if union_size else 0.0


def strip_frontmatter(content: str) -> str:
    if not content.startswith("---"):
        return content
    end = content.find("\n---", 3)
    return content[end + 4:] if end != -1 else content


def strip_code_blocks(content: str) -> str:
    lines, in_block, result = content.split("\n"), False, []
    for line in lines:
        if line.strip().startswith("```") or line.strip().startswith("~~~"):
            in_block = not in_block
            result.append("")
        elif in_block:
            result.append("")
        else:
            result.append(line)
    return "\n".join(result)


def _tokenize(text: str) -> List[str]:
    return [w for w in re.findall(r"\b[a-z]{3,}\b", text.lower()) if w not in STOPWORDS]
