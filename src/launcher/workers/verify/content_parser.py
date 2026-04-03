"""Content parser — extract code blocks and API references from markdown.

Pure functions used by the Verify worker's drift detection passes.
No LLM calls, no I/O — all functions accept strings and return structured data.
"""
from __future__ import annotations

import re
from typing import Any


# Fenced code block pattern: ```lang\n...\n```
_FENCE_RE = re.compile(
    r"```(?P<lang>[^\n`]*)\n(?P<code>.*?)```",
    re.DOTALL,
)

# Python import patterns
_PY_IMPORT_RE = re.compile(r"^\s*(?:import\s+\S+|from\s+\S+\s+import\s+\S+)", re.MULTILINE)

# Java import pattern
_JAVA_IMPORT_RE = re.compile(r"^\s*import\s+[\w.]+;", re.MULTILINE)

# C# using pattern
_CS_USING_RE = re.compile(r"^\s*using\s+[\w.]+;", re.MULTILINE)

# API call pattern: SomeClass.someMethod( or SomeClass.property
_API_CALL_RE = re.compile(r"\b([A-Z][A-Za-z0-9_]*)\s*\.\s*([a-z_][A-Za-z0-9_]*)")


def extract_code_blocks(md_text: str) -> list[dict[str, Any]]:
    """Extract fenced code blocks from a markdown string.

    Args:
        md_text: Raw markdown content.

    Returns:
        List of dicts with keys:
          - ``language`` (str): Language tag from the fence (e.g. ``"python"``).
          - ``code`` (str): Block body without the fence delimiters.
          - ``line_start`` (int): 1-based line number of the opening fence.
    """
    blocks: list[dict[str, Any]] = []
    for match in _FENCE_RE.finditer(md_text):
        lang = match.group("lang").strip().lower()
        code = match.group("code")
        # Compute line_start from position in text
        line_start = md_text[: match.start()].count("\n") + 1
        blocks.append({"language": lang, "code": code, "line_start": line_start})
    return blocks


def extract_imports(code: str, language: str) -> list[str]:
    """Extract import/using statements from a code block.

    Supports Python, Java, and C# (csharp/cs/dotnet).

    Args:
        code: Code block body text.
        language: Language tag (e.g. ``"python"``, ``"java"``, ``"csharp"``).

    Returns:
        List of import statement strings, stripped of leading/trailing whitespace.
    """
    lang = language.lower()
    if lang in ("python", "py"):
        return [m.group(0).strip() for m in _PY_IMPORT_RE.finditer(code)]
    if lang in ("java",):
        return [m.group(0).strip() for m in _JAVA_IMPORT_RE.finditer(code)]
    if lang in ("csharp", "cs", "c#", "dotnet"):
        return [m.group(0).strip() for m in _CS_USING_RE.finditer(code)]
    return []


def extract_api_calls(code: str, language: str) -> list[str]:
    """Extract likely API method/property call tokens from a code block.

    Uses a heuristic: ``SomeClass.memberName`` patterns where the class name
    starts with an uppercase letter.  Returns unique tokens sorted alphabetically.

    Args:
        code: Code block body text.
        language: Language tag (informational only — same heuristic applied).

    Returns:
        Sorted list of unique ``"ClassName.memberName"`` strings found in the code.
    """
    found: set[str] = set()
    for match in _API_CALL_RE.finditer(code):
        cls = match.group(1)
        member = match.group(2)
        # Skip very common non-API identifiers
        if cls.lower() in {"true", "false", "none", "null", "self", "this"}:
            continue
        found.add(f"{cls}.{member}")
    return sorted(found)


def normalize_import(stmt: str, language: str) -> str:
    """Return a canonical representation of an import statement.

    For Python: returns the top-level module name (e.g. ``"import aspose.threed"``
    → ``"aspose.threed"``; ``"from aspose.threed import Scene"`` → ``"aspose.threed"``).
    For Java: strips ``import `` prefix and trailing ``;``, preserves case
    (e.g. ``"import com.aspose.threed.Scene;"`` → ``"com.aspose.threed.Scene"``).
    For C#: strips ``using `` prefix and trailing ``;``, preserves case
    (e.g. ``"using Aspose.ThreeD;"`` → ``"Aspose.ThreeD"``).
    For unknown languages: returns ``""`` (cannot normalize safely).

    Args:
        stmt: Raw import statement string.
        language: Language tag.

    Returns:
        Normalized string for allowlist comparison.
    """
    lang = language.lower()
    stripped = stmt.strip()
    if lang in ("python", "py"):
        if stripped.startswith("from "):
            # from X import Y → X
            parts = stripped.split()
            return parts[1] if len(parts) >= 2 else stripped
        if stripped.startswith("import "):
            parts = stripped.split()
            return parts[1] if len(parts) >= 2 else stripped
        return stripped
    if lang in ("java",):
        # "import com.aspose.threed.Scene;" → "com.aspose.threed.Scene"
        result = stripped
        if result.startswith("import "):
            result = result[len("import "):]
        if result.endswith(";"):
            result = result[:-1]
        return result.strip()
    if lang in ("csharp", "cs", "c#", "dotnet"):
        # "using Aspose.ThreeD;" → "Aspose.ThreeD"
        result = stripped
        if result.startswith("using "):
            result = result[len("using "):]
        if result.endswith(";"):
            result = result[:-1]
        return result.strip()
    # Unknown language: cannot normalize safely
    return ""
