"""Snippet extraction, code block parsing, AST validation, embedding index, and doc context builder."""
from __future__ import annotations

import ast
import hashlib
import logging
import os
import re
import textwrap
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

# BPW-02: Minimum fenced-block snippet count before test file promotion kicks in.
_MIN_SNIPPETS_FOR_TEST_PROMOTION: int = 8

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
_META_DOC_EXACT_NAMES: frozenset[str] = frozenset({
    "agents.md", "claude.md", "copilot-instructions.md", "llms.md",
})
_META_DOC_ROOT_KEYWORDS: frozenset[str] = frozenset({
    "readiness", "implementation", "summary", "status", "backlog",
    "roadmap", "plan", "notes",
})
_CLI_SNIPPET_LANGS: frozenset[str] = frozenset({
    "bash", "shell", "sh", "console", "powershell", "pwsh", "cmd",
})
_TEST_NOISE_IMPORT_MODULES: frozenset[str] = frozenset({
    "unittest", "pytest", "sys",
})
_TEST_NOISE_LINE_RE = re.compile(
    r"^\s*(?:self\.(?:assert\w+|fail|skipTest)\(|assert\b|print\(|sys\.path\.insert\(|unittest\.main\()"
)
_TEST_ELSE_RE = re.compile(r"^\s*else:\s*$")
_TEST_MAX_SLICE_CHARS = 1_400

# ---------------------------------------------------------------------------
# C# test method slicing constants (TC-UND-04)
# ---------------------------------------------------------------------------
_CS_TEST_ATTR_RE = re.compile(
    r"^\s*\[(?:Test|Fact|Theory|TestMethod|TestCase)\b",
)
_CS_ASSERT_LINE_RE = re.compile(
    r"^\s*(?:Assert\.\w+|ClassicAssert\.\w+)\s*[\(;]"
)
_CS_TEST_MAX_SLICE_CHARS = 1_400
_CS_TEST_USING_PREFIXES: frozenset[str] = frozenset({
    "NUnit.Framework", "Xunit", "Microsoft.VisualStudio.TestTools.UnitTesting",
    "Moq", "FluentAssertions", "NSubstitute",
})
# Strip string literal contents before brace-counting to avoid miscounts (SR-UND04-02)
_CS_STRING_LITERAL_RE = re.compile(r'"[^"\\]*(?:\\.[^"\\]*)*"')

_SNIPPET_OPERATION_HINTS: tuple[str, ...] = (
    ".open(",
    ".save(",
    ".render(",
    "create_",
    "add_child_node",
    "import_scene(",
    "from_file(",
)

# ---------------------------------------------------------------------------
# SR-06: Java test method slicing constants
# ---------------------------------------------------------------------------
_JAVA_TEST_ATTR_RE = re.compile(r"^\s*@Test\b")
_JAVA_ASSERT_LINE_RE = re.compile(
    r"^\s*(?:assert(?:Equals|NotNull|Null|True|False|That|Throws|Same|NotSame|ArrayEquals)\s*[\(;]"
    r"|verify\s*\("
    r"|when\s*\()",
    re.IGNORECASE,
)
_JAVA_TEST_IMPORT_PREFIXES: frozenset[str] = frozenset({
    "org.junit", "org.mockito", "org.hamcrest", "org.assertj",
    "junit.framework", "org.testng",
})

# ---------------------------------------------------------------------------
# TC-CPP-404: C++ test method slicing constants (Google Test / Catch2)
# ---------------------------------------------------------------------------
_CPP_TEST_MACRO_RE = re.compile(
    r"^\s*(?:TEST|TEST_F|TEST_P|TEST_CASE|SCENARIO)\s*\("
)
_CPP_ASSERT_LINE_RE = re.compile(
    r"^\s*(?:ASSERT_|EXPECT_|REQUIRE\s*\(|CHECK\s*\(|REQUIRE_THAT|CHECK_THAT)",
    re.IGNORECASE,
)

# Language markers: characteristic token patterns that identify a code snippet
# language. Used by tests to verify language detection.
_LANG_MARKERS: dict[str, list[str]] = {
    "java": [
        "import ", "public class ", "public static void main",
        "System.out.println", "new ", ";",
    ],
    "csharp": [
        "using ", "namespace ", "public class ", "static void Main", "Console.WriteLine",
    ],
    "python": [
        "import ", "def ", "class ", "print(", "if __name__",
    ],
    "cpp": [
        "#include ", "namespace ", "int main(", "std::", "->",
    ],
}

# Fraction of _MAX_SOURCE_CHARS reserved for README files
_README_BUDGET_FRACTION = 0.4

# Directory names for relevance scoring
_DOC_DIR_NAMES: frozenset[str] = frozenset({"docs", "doc", "documentation"})
_EXAMPLE_DIR_NAMES: frozenset[str] = frozenset({"examples", "example", "samples", "sample", "demo", "demos"})


def _dedup_key(code: str) -> str:
    """Return a 24-char hex content hash used to deduplicate identical snippets (TC-4063).

    Extended from 16 to 24 chars (96 bits) to reduce collision probability at scale
    from ~3e-15 to ~6e-24 at 1000 snippets.
    """
    return hashlib.sha256(code.encode("utf-8", errors="replace")).hexdigest()[:24]


def _normalized_stem(rel_path: str) -> str:
    return Path(rel_path).stem.lower().replace("-", "").replace("_", "")


def _is_polluted_doc_path(rel_path: str) -> bool:
    lower = rel_path.lower().replace("\\", "/")
    name = Path(lower).name
    if name in _META_DOC_EXACT_NAMES:
        return True
    if "/" not in lower and _normalized_stem(lower) != "readme":
        return any(keyword in _normalized_stem(lower) for keyword in _META_DOC_ROOT_KEYWORDS)
    return False


def _public_symbol_names(api_surface: ApiSurface | None) -> set[str]:
    if api_surface is None:
        return set()
    names = set(getattr(api_surface, "public_classes", []) or [])
    for brief in getattr(api_surface, "class_briefs", []) or []:
        name = getattr(brief, "name", "")
        if name:
            names.add(name)
    for enum in getattr(api_surface, "enums", []) or []:
        name = getattr(enum, "name", "")
        if name:
            names.add(name)
    return names


def _is_product_import_path(module: str, allowlist_set: set[str], allow_roots: set[str]) -> bool:
    root = module.split(".")[0]
    if root in allow_roots:
        return True
    return root == "aspose" and any(entry.startswith("aspose.") for entry in allowlist_set)


def _module_import_block_for_test(code: str) -> str:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return ""

    imports: list[str] = []
    seen: set[str] = set()
    for node in tree.body:
        if not isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        if isinstance(node, ast.Import):
            module_names = [alias.name.split(".")[0] for alias in node.names]
            if any(name in _TEST_NOISE_IMPORT_MODULES for name in module_names):
                continue
        elif isinstance(node, ast.ImportFrom):
            module_root = (node.module or "").split(".")[0]
            if node.level > 0 or module_root in _TEST_NOISE_IMPORT_MODULES:
                continue

        segment = ast.get_source_segment(code, node)
        if not segment:
            continue
        cleaned = segment.strip()
        if not cleaned or cleaned in seen:
            continue
        imports.append(cleaned)
        seen.add(cleaned)

    return "\n".join(imports)


def _sanitize_python_test_body(body_text: str) -> str:
    if "try:" in body_text or "except " in body_text:
        return ""

    cleaned_lines: list[str] = []
    lines = body_text.splitlines()
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            cleaned_lines.append("")
            continue
        if _TEST_NOISE_LINE_RE.match(line):
            continue
        if _TEST_ELSE_RE.match(line):
            next_non_empty = ""
            for follow in lines[idx + 1:]:
                if follow.strip():
                    next_non_empty = follow
                    break
            if next_non_empty and _TEST_NOISE_LINE_RE.match(next_non_empty):
                continue
        cleaned_lines.append(line.rstrip())

    return "\n".join(cleaned_lines).strip()


def _score_python_test_slice(code: str, api_surface: ApiSurface) -> int:
    public_symbols = _public_symbol_names(api_surface)
    score = 0
    for symbol in list(public_symbols)[:200]:
        if symbol and symbol in code:
            score += 6
    lower = code.lower()
    for hint in _SNIPPET_OPERATION_HINTS:
        if hint.lower() in lower:
            score += 12
    score -= max(len(code) - 600, 0) // 120
    return score


def _extract_python_test_slices(
    code: str,
    api_surface: ApiSurface,
    *,
    max_slices: int = 2,
) -> list[str]:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []

    lines = code.splitlines()
    import_block = _module_import_block_for_test(code)
    candidates: list[tuple[int, str]] = []

    def _append_candidate(node: ast.AST) -> None:
        body = getattr(node, "body", [])
        if not body:
            return
        start = getattr(body[0], "lineno", 0)
        end = getattr(node, "end_lineno", 0)
        if not start or not end:
            return
        body_text = textwrap.dedent("\n".join(lines[start - 1:end]))
        cleaned_body = _sanitize_python_test_body(body_text)
        if not cleaned_body or len(cleaned_body) > _TEST_MAX_SLICE_CHARS:
            return
        candidate = cleaned_body if not import_block else f"{import_block}\n\n{cleaned_body}"
        if not _validate_python_syntax(candidate):
            return
        score = _score_python_test_slice(candidate, api_surface)
        if score <= 0:
            return
        candidates.append((score, candidate))

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
            _append_candidate(node)
        elif isinstance(node, ast.ClassDef):
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name.startswith("test_"):
                    _append_candidate(child)

    seen: set[str] = set()
    selected: list[str] = []
    for _, candidate in sorted(candidates, key=lambda item: item[0], reverse=True):
        digest = _dedup_key(candidate)
        if digest in seen:
            continue
        seen.add(digest)
        selected.append(candidate)
        if len(selected) >= max_slices:
            break
    return selected


# ---------------------------------------------------------------------------
# C# test method slicing (TC-UND-04) — mirrors Python path above
# ---------------------------------------------------------------------------


def _extract_csharp_using_block(code: str) -> str:
    """Extract using directives from C# file, filtering test-framework imports."""
    usings: list[str] = []
    for line in code.splitlines():
        stripped = line.strip()
        if not stripped.startswith("using "):
            continue
        # Extract the namespace (e.g., "Aspose.Cells" from "using Aspose.Cells;")
        ns = stripped.removeprefix("using ").rstrip(";").strip()
        if any(ns.startswith(prefix) for prefix in _CS_TEST_USING_PREFIXES):
            continue
        usings.append(stripped)
    return "\n".join(usings)


def _sanitize_csharp_test_body(body_text: str) -> str:
    """Remove assertion lines and try/catch from C# test method body."""
    if "try" in body_text and "catch" in body_text:
        return ""

    cleaned: list[str] = []
    for line in body_text.splitlines():
        stripped = line.strip()
        if not stripped:
            cleaned.append("")
            continue
        if _CS_ASSERT_LINE_RE.match(line):
            continue
        cleaned.append(line.rstrip())

    return "\n".join(cleaned).strip()


def _score_csharp_test_slice(code: str, api_surface: ApiSurface) -> int:
    """Score a C# test slice by API surface coverage and operation hints."""
    public_symbols = _public_symbol_names(api_surface)
    score = 0
    for symbol in list(public_symbols)[:200]:
        if symbol and symbol in code:
            score += 6
    lower = code.lower()
    for hint in _SNIPPET_OPERATION_HINTS:
        if hint.lower() in lower:
            score += 12
    score -= max(len(code) - 600, 0) // 120
    return score


def _extract_csharp_test_slices_regex(
    code: str,
    api_surface: ApiSurface,
    *,
    max_slices: int = 2,
) -> list[str]:
    """Regex fallback for C# test method extraction when tree-sitter is unavailable.

    Finds [Test]/[Fact]/[TestMethod] attributes, then extracts the following
    method body by balanced brace counting.
    """
    lines = code.splitlines()
    using_block = _extract_csharp_using_block(code)
    candidates: list[tuple[int, str]] = []

    i = 0
    while i < len(lines):
        if not _CS_TEST_ATTR_RE.match(lines[i]):
            i += 1
            continue

        # Find method signature (skip additional attributes)
        method_start = i + 1
        while method_start < len(lines) and lines[method_start].strip().startswith("["):
            method_start += 1

        # Find opening brace
        brace_line = method_start
        while brace_line < len(lines) and "{" not in lines[brace_line]:
            brace_line += 1
        if brace_line >= len(lines):
            i = method_start + 1
            continue

        # Count braces to find method end — strip string literals first (SR-UND04-02)
        depth = 0
        method_end = brace_line
        for j in range(brace_line, len(lines)):
            stripped_line = _CS_STRING_LITERAL_RE.sub('""', lines[j])
            depth += stripped_line.count("{") - stripped_line.count("}")
            if depth == 0:
                method_end = j
                break

        # Extract body (between outermost braces)
        body_lines = lines[brace_line + 1:method_end]
        body_text = textwrap.dedent("\n".join(body_lines))
        cleaned = _sanitize_csharp_test_body(body_text)

        if cleaned and len(cleaned) <= _CS_TEST_MAX_SLICE_CHARS:
            candidate = f"{using_block}\n\n{cleaned}" if using_block else cleaned
            score = _score_csharp_test_slice(candidate, api_surface)
            if score > 0:
                candidates.append((score, candidate))

        i = method_end + 1

    # Dedup and select top slices
    seen: set[str] = set()
    selected: list[str] = []
    for _, candidate in sorted(candidates, key=lambda item: item[0], reverse=True):
        digest = _dedup_key(candidate)
        if digest in seen:
            continue
        seen.add(digest)
        selected.append(candidate)
        if len(selected) >= max_slices:
            break
    logger.info(
        "csharp_test_slicing [TC-UND-04]: path=regex candidates=%d selected=%d",
        len(candidates), len(selected),
    )
    return selected


def _extract_csharp_test_slices(
    code: str,
    api_surface: ApiSurface,
    *,
    max_slices: int = 2,
) -> list[str]:
    """Extract individual test method bodies from a C# test file.

    TC-UND-04: Uses tree-sitter C# parser to find method_declaration nodes
    preceded by test attributes ([Test], [Fact], [TestMethod]). Falls back
    to regex-based extraction if tree-sitter C# is unavailable.
    """
    # Try tree-sitter first — _get_parser is module-level, not an instance method
    try:
        from launcher.shared.ts_analyzer import _get_parser as _ts_get_parser
        parser = _ts_get_parser("csharp")
        if parser is None:
            raise ImportError("C# tree-sitter parser not available")
    except ImportError:
        return _extract_csharp_test_slices_regex(code, api_surface, max_slices=max_slices)

    tree = parser.parse(code.encode("utf-8", errors="replace"))
    lines = code.splitlines()
    using_block = _extract_csharp_using_block(code)
    candidates: list[tuple[int, str]] = []

    def _walk(node):
        if node.type == "method_declaration":
            _process_method(node)
        for child in node.children:
            _walk(child)

    def _has_test_attribute(node) -> bool:
        """Check if a method has a test attribute.

        In tree-sitter C#, attribute_list nodes are direct children of
        method_declaration, NOT siblings. Check the method's own children first,
        then fall back to line-based scanning for robustness.
        """
        # Primary: attribute_list is a direct child of method_declaration in C# AST
        for child in node.children:
            if child.type == "attribute_list":
                attr_text = code[child.start_byte:child.end_byte]
                if _CS_TEST_ATTR_RE.search(attr_text):
                    return True
        # Fallback: scan preceding lines (catches edge cases)
        start_line = node.start_point[0]
        for look_back in range(max(0, start_line - 5), start_line):
            if _CS_TEST_ATTR_RE.match(lines[look_back]):
                return True
        return False

    def _process_method(node):
        if not _has_test_attribute(node):
            return
        # Find the block (body) child
        body_node = None
        for child in node.children:
            if child.type == "block":
                body_node = child
                break
        if body_node is None:
            return

        # Extract body content (inside braces)
        body_start = body_node.start_point[0] + 1  # skip opening brace line
        body_end = body_node.end_point[0]  # closing brace line
        if body_start >= body_end:
            return

        body_lines = lines[body_start:body_end]
        body_text = textwrap.dedent("\n".join(body_lines))
        cleaned = _sanitize_csharp_test_body(body_text)

        if cleaned and len(cleaned) <= _CS_TEST_MAX_SLICE_CHARS:
            candidate = f"{using_block}\n\n{cleaned}" if using_block else cleaned
            score = _score_csharp_test_slice(candidate, api_surface)
            if score > 0:
                candidates.append((score, candidate))

    _walk(tree.root_node)

    # Dedup and select top slices
    seen: set[str] = set()
    selected: list[str] = []
    for _, candidate in sorted(candidates, key=lambda item: item[0], reverse=True):
        digest = _dedup_key(candidate)
        if digest in seen:
            continue
        seen.add(digest)
        selected.append(candidate)
        if len(selected) >= max_slices:
            break
    logger.info(
        "csharp_test_slicing [TC-UND-04]: path=tree_sitter candidates=%d selected=%d",
        len(candidates), len(selected),
    )
    return selected


# ---------------------------------------------------------------------------
# SR-06: Java test method slicing — mirrors C# path above
# ---------------------------------------------------------------------------


def _extract_java_import_block(code: str) -> str:
    """Extract import statements from Java file, filtering test-framework imports."""
    imports: list[str] = []
    for line in code.splitlines():
        stripped = line.strip()
        if not stripped.startswith("import "):
            continue
        # Extract the package prefix (e.g., "org.junit" from "import org.junit.Test;")
        pkg = stripped.removeprefix("import ").rstrip(";").strip()
        if any(pkg.startswith(prefix) for prefix in _JAVA_TEST_IMPORT_PREFIXES):
            continue
        imports.append(stripped)
    return "\n".join(imports)


def _sanitize_java_test_body(lines: list[str]) -> str:
    """Remove assertion and mock lines from Java test method body."""
    cleaned: list[str] = []
    for line in lines:
        if _JAVA_ASSERT_LINE_RE.match(line):
            continue
        cleaned.append(line.rstrip())
    return "\n".join(cleaned).strip()


def _validate_java_regex(code: str) -> bool:
    """Return True if code looks like valid Java (has at least one structural marker)."""
    java_markers = (
        r"\bclass\s+\w+",
        r"\bimport\s+[\w.]+;",
        r"\bpublic\s+static\s+void\b",
        r"\bnew\s+\w+\s*\(",
    )
    return any(re.search(pattern, code) for pattern in java_markers)


def _extract_java_test_slices(
    code: str,
    api_surface: object,
    *,
    max_slices: int = 2,
) -> list[str]:
    """Extract individual test methods from a Java test file.

    Extracts methods annotated with @Test, strips assertion noise,
    and returns the top-scoring slices (by API surface coverage).

    Parameters
    ----------
    code:
        Full content of a Java test file.
    api_surface:
        Object with ``public_classes``, ``public_methods``, ``import_allowlist``.
    max_slices:
        Maximum number of slices to return.
    """
    if not code.strip():
        return []

    import_block = _extract_java_import_block(code)
    lines = code.splitlines()
    candidates: list[tuple[int, str]] = []

    # TC-UND-209: observability counters for snippet filtering
    _n_test_methods = 0
    _n_nonempty_body = 0
    _n_api_hit = 0
    _n_size_ok = 0

    i = 0
    while i < len(lines):
        line = lines[i]
        if not _JAVA_TEST_ATTR_RE.match(line):
            i += 1
            continue

        # Found @Test — find the method declaration on the next non-blank line
        _n_test_methods += 1
        method_start = i + 1
        while method_start < len(lines) and not lines[method_start].strip():
            method_start += 1

        if method_start >= len(lines):
            break

        # Find the opening brace
        brace_search = method_start
        depth = 0
        body_start = -1
        while brace_search < len(lines):
            for ch in lines[brace_search]:
                if ch == "{":
                    depth += 1
                    if body_start < 0:
                        body_start = brace_search
                elif ch == "}":
                    depth -= 1
                    if depth == 0 and body_start >= 0:
                        body_end = brace_search
                        body_lines = lines[body_start + 1:body_end]
                        cleaned = _sanitize_java_test_body(body_lines)
                        if cleaned:
                            _n_nonempty_body += 1
                            # Score by how many public API symbols appear
                            public_classes = getattr(api_surface, "public_classes", []) or []
                            score = sum(1 for cls in public_classes if cls in cleaned) * 6
                            if score > 0:
                                _n_api_hit += 1
                                if len(cleaned) <= _TEST_MAX_SLICE_CHARS:
                                    _n_size_ok += 1
                                    snippet = (
                                        f"{import_block}\n\n{cleaned}" if import_block else cleaned
                                    )
                                    candidates.append((score, snippet))
                        i = body_end + 1
                        body_start = -1
                        depth = 0
                        break
            else:
                brace_search += 1
                continue
            break
        else:
            i += 1

    # Select top-scoring unique slices
    seen: set[str] = set()
    selected: list[str] = []
    for _, candidate in sorted(candidates, key=lambda item: item[0], reverse=True):
        digest = _dedup_key(candidate)
        if digest in seen:
            continue
        seen.add(digest)
        selected.append(candidate)
        if len(selected) >= max_slices:
            break

    # TC-UND-209: structured observability for snippet filtering pipeline
    logger.debug(
        "[Snippets] java_test_slicing: @Test=%d nonempty_body=%d api_hit=%d "
        "size_ok=%d candidates=%d selected=%d",
        _n_test_methods, _n_nonempty_body, _n_api_hit,
        _n_size_ok, len(candidates), len(selected),
    )

    return selected


def _extract_cpp_include_block(code: str) -> str:
    """TC-CPP-404: Extract #include lines from C++ source."""
    includes: list[str] = []
    for line in code.splitlines():
        stripped = line.strip()
        if stripped.startswith("#include"):
            # Skip test framework includes
            if any(fw in stripped for fw in ("gtest", "catch2", "catch.hpp", "gmock")):
                continue
            includes.append(stripped)
    return "\n".join(includes)


def _sanitize_cpp_test_body(lines: list[str]) -> str:
    """TC-CPP-404: Strip assertion macros from C++ test body."""
    cleaned: list[str] = []
    for line in lines:
        if _CPP_ASSERT_LINE_RE.match(line):
            continue
        stripped = line.strip()
        if not stripped or stripped in ("{", "}"):
            continue
        cleaned.append(line)
    return "\n".join(cleaned).strip()


def _extract_cpp_test_slices(
    code: str,
    api_surface: object,
    *,
    max_slices: int = 2,
) -> list[str]:
    """TC-CPP-404: Extract individual test cases from C++ test files.

    Supports Google Test (TEST, TEST_F, TEST_P) and Catch2 (TEST_CASE, SCENARIO).
    Extracts test bodies, strips assertion noise, scores by API surface coverage.
    """
    if not code.strip():
        return []

    include_block = _extract_cpp_include_block(code)
    lines = code.splitlines()
    candidates: list[tuple[int, str]] = []

    i = 0
    while i < len(lines):
        line = lines[i]
        if not _CPP_TEST_MACRO_RE.match(line):
            i += 1
            continue

        # Found a test macro — track brace depth to extract body
        depth = 0
        body_start = -1
        brace_search = i
        while brace_search < len(lines):
            for ch in lines[brace_search]:
                if ch == "{":
                    depth += 1
                    if body_start < 0:
                        body_start = brace_search
                elif ch == "}":
                    depth -= 1
                    if depth == 0 and body_start >= 0:
                        body_end = brace_search
                        body_lines = lines[body_start + 1:body_end]
                        cleaned = _sanitize_cpp_test_body(body_lines)
                        if cleaned:
                            public_classes = getattr(api_surface, "public_classes", []) or []
                            score = sum(1 for cls in public_classes if cls in cleaned) * 6
                            if score > 0 and len(cleaned) <= _TEST_MAX_SLICE_CHARS:
                                snippet = (
                                    f"{include_block}\n\n{cleaned}" if include_block else cleaned
                                )
                                candidates.append((score, snippet))
                        i = body_end + 1
                        body_start = -1
                        depth = 0
                        break
            else:
                brace_search += 1
                continue
            break
        else:
            i += 1

    # Select top-scoring unique slices
    seen: set[str] = set()
    selected: list[str] = []
    for _, candidate in sorted(candidates, key=lambda item: item[0], reverse=True):
        digest = _dedup_key(candidate)
        if digest in seen:
            continue
        seen.add(digest)
        selected.append(candidate)
        if len(selected) >= max_slices:
            break

    return selected


def _unknown_product_import_symbols(
    code: str,
    allowlist_set: set[str],
    allow_roots: set[str],
    public_symbols: set[str],
) -> list[str]:
    if not public_symbols:
        return []
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []

    unknown: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        module = node.module or ""
        if node.level > 0 or not module or not _is_product_import_path(module, allowlist_set, allow_roots):
            continue
        for alias in node.names:
            if alias.name == "*":
                continue
            if alias.name not in public_symbols and alias.name not in unknown:
                unknown.append(alias.name)
    return unknown


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
        if Path(p).name.lower() in _EXCLUDED_DOC_NAMES or _is_polluted_doc_path(p):
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
        """Try repo_content dict first, then fall back to disk read.

        TC-4056 Fix 3: The disk-read fallback (used on resume/heal re-runs when
        context.repo_content is not populated) must go through sanitize_input to
        match the same sanitization applied by Scout on the original run.
        Without this, LLM sees unsanitized content (secrets, tokens) on re-runs.
        """
        if repo_content and rel_path in repo_content:
            return repo_content[rel_path]
        file_path = repo_dir / rel_path
        if not file_path.exists() or not file_path.is_file():
            return None
        try:
            from launcher.shared.input_sanitizer import sanitize_input as _sanitize
            # IU-05: Log disk reads so heal re-run traces show which files bypassed the cache.
            logger.debug("[Extract] repo_content miss; sanitized disk read for %s", rel_path)
            raw = file_path.read_text(encoding="utf-8", errors="replace")
            return _sanitize(raw, max_chars=100_000).text
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

    Note:
        ``Snippet.line_start`` and ``Snippet.line_end`` are always ``None`` for
        fenced code blocks — position within the source file is not tracked during
        extraction. Use ``Snippet.source_file`` for traceability back to the
        originating file. See TC-4063 for rationale.
    """
    snippets: list[Snippet] = []
    # TC-4063: Deduplicate by content hash — same code block in README + docs/ → keep first
    seen_hashes: set[str] = set()
    dedup_skipped: int = 0
    # Collect code blocks from doc files
    all_paths = list(repo_info.doc_paths) + list(repo_info.example_paths)
    # Check for standalone example files in any source language
    from launcher.workers.understand.file_classifier import LANG_BY_EXT
    _source_exts = set(LANG_BY_EXT.keys())
    source_examples = [
        p for p in repo_info.example_paths
        if any(p.endswith(ext) for ext in _source_exts)
    ]
    if not source_examples:
        source_examples = [
            p for p in repo_info.test_paths
            if any(p.endswith(ext) for ext in _source_exts)
        ][:20]

    # Extract fenced code blocks from markdown/rst files
    for rel_path in all_paths:
        if _is_polluted_doc_path(rel_path):
            continue
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
        # TC-4080: Per-file logging — makes snippet extraction failures diagnosable
        # without running a debugger. README.md is especially important to log at INFO.
        _is_readme = Path(rel_path).name.lower().startswith("readme")
        _per_file_log = logger.info if _is_readme else logger.debug
        _per_file_log("[Snippets] %s: %d fenced block(s) found", rel_path, len(blocks))
        added_for_file = 0

        for lang, code in blocks:
            if not code.strip():
                logger.debug("[Snippets] %s: skipping empty block", rel_path)
                continue
            if lang.lower() in _CLI_SNIPPET_LANGS:
                logger.debug("[Snippets] %s: skipping CLI/install block (lang=%r)", rel_path, lang)
                continue

            # Determine language — use product lang_tag as default, not "python"
            effective_lang = lang.lower() if lang else getattr(product, "lang_tag", "python") or "python"

            # Validate snippets — Python via ast, others via tree-sitter
            source_type: str = "extracted"
            if effective_lang == "python":
                if not _validate_python_syntax(code):
                    logger.debug(
                        "[Snippets] %s: skipping invalid Python syntax (lang=%r)", rel_path, lang
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
                            "[Snippets] %s: skipping invalid %s snippet", rel_path, effective_lang
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
                logger.debug("[Snippets] %s: skipping heading-only block", rel_path)
                continue

            # TC-4063: Skip duplicate code blocks (same content from different files)
            h = _dedup_key(code.strip())
            if h in seen_hashes:
                logger.debug("[Snippets] %s: skipping duplicate (hash=%s)", rel_path, h)
                dedup_skipped += 1
                continue
            seen_hashes.add(h)

            # Link snippet to claims by keyword overlap
            linked_claim_ids = _link_snippet_to_claims(code, claims)

            snippets.append(Snippet(
                code=code.strip(),
                language=effective_lang,
                source_type=source_type,
                source_file=rel_path,
                claim_ids=linked_claim_ids,
            ))
            added_for_file += 1

        if blocks:
            _per_file_log("[Snippets] %s: %d/%d block(s) added", rel_path, added_for_file, len(blocks))

    # BPW-02: When fenced code block extraction yields few snippets AND example files
    # are sparse, also include test files as source_examples for the second pass.
    if len(snippets) < _MIN_SNIPPETS_FOR_TEST_PROMOTION and source_examples:
        _test_candidates = [
            p for p in repo_info.test_paths
            if any(p.endswith(ext) for ext in _source_exts)
            and p not in set(source_examples)
        ][:20]
        if _test_candidates:
            logger.info(
                "[Snippets] BPW-02: promoting %d test files (snippet_count=%d < %d)",
                len(_test_candidates), len(snippets), _MIN_SNIPPETS_FOR_TEST_PROMOTION,
            )
            source_examples = list(source_examples) + _test_candidates

    # BPW-02b: When no example directory exists, test files are the primary snippet
    # source. The initial fallback (lines above) caps at 20; promote remaining
    # test files here without a snippet-count threshold.
    if not repo_info.example_paths and repo_info.test_paths:
        _test_bpw02b = [
            p for p in repo_info.test_paths
            if any(p.endswith(ext) for ext in _source_exts)
            and p not in set(source_examples)
        ][:20]
        if _test_bpw02b:
            logger.info(
                "[Snippets] BPW-02b: promoting %d more test files (no example_paths, snippet_count=%d)",
                len(_test_bpw02b), len(snippets),
            )
            source_examples = list(source_examples) + _test_bpw02b

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
        candidate_codes = [code]
        if rel_path in set(repo_info.test_paths):
            if file_lang == "python":
                candidate_codes = _extract_python_test_slices(code, api_surface) or []
            elif file_lang == "csharp":
                candidate_codes = _extract_csharp_test_slices(code, api_surface) or []
            elif file_lang == "java":
                candidate_codes = _extract_java_test_slices(code, api_surface) or []
            elif file_lang == "cpp":
                candidate_codes = _extract_cpp_test_slices(code, api_surface) or []
            if not candidate_codes:
                logger.debug("Skipping test fallback %s: no reviewable product usage slices", rel_path)
                continue

        for candidate_code in candidate_codes:
            normalized_code = candidate_code

            # Validate syntax
            if file_lang == "python":
                if not _validate_python_syntax(normalized_code):
                    logger.debug("Skipping invalid Python example %s", rel_path)
                    continue
                normalized_code = _normalize_snippet_imports(normalized_code, api_surface, product)
            else:
                try:
                    from launcher.shared.ts_analyzer import analyzer as _ts_analyzer
                    if not _ts_analyzer.validate_snippet(normalized_code, file_lang):
                        logger.debug("Skipping invalid %s example %s", file_lang, rel_path)
                        continue
                    from launcher.shared.ts_analyzer import normalize_imports as _ts_normalize
                    canonical = getattr(product, "canonical_import", "") or ""
                    if canonical:
                        normalized_code = _ts_normalize(normalized_code, file_lang, canonical)
                except ImportError:
                    pass  # tree-sitter not available

            # Filter heading-only snippets
            if _is_heading_only(normalized_code):
                continue

            # TC-4063: Skip duplicate code blocks
            h = _dedup_key(normalized_code.strip())
            if h in seen_hashes:
                logger.debug("Skipping duplicate example file %s (hash=%s)", rel_path, h)
                dedup_skipped += 1
                continue
            seen_hashes.add(h)

            linked_claim_ids = _link_snippet_to_claims(normalized_code, claims)

            snippets.append(Snippet(
                code=normalized_code.strip(),
                language=file_lang,
                source_type="extracted",
                source_file=rel_path,
                claim_ids=linked_claim_ids,
            ))

    # UND-1 (TC-5205): Extract individual Python test function bodies from test files
    # that were NOT already processed via BPW-02 promotion. This is additive — dedup
    # via shared seen_hashes prevents double-counting files already in source_examples.
    test_snippets = _extract_test_snippets(
        repo_dir, repo_info, product, api_surface, claims, seen_hashes
    )
    if test_snippets:
        snippets.extend(test_snippets)
        logger.info(
            "[Snippets] UND-1: added=%d test-function snippets (TC-5205)",
            len(test_snippets),
        )

    logger.info(
        "snippet_extraction: extracted=%d dedup_skipped=%d",
        len(snippets),
        dedup_skipped,
    )
    return snippets


# ---------------------------------------------------------------------------
# UND-1 (TC-5205): Python test function snippet extraction
# ---------------------------------------------------------------------------

_UND1_MAX_TEST_FILES: int = 20
_UND1_MAX_SLICES_PER_FILE: int = 3
_UND1_MAX_NONCOMMENT_LINES: int = 60
_UND1_MIN_NONCOMMENT_LINES: int = 3


def _extract_test_snippets(
    repo_dir: "Path",
    repo_info: "RepoInfo",
    product: "ProductIdentity",
    api_surface: "ApiSurface",
    claims: "list",
    seen_hashes: "set[str]",
) -> "list[Snippet]":
    """UND-1 (TC-5205): Extract individual test_ function bodies from Python test files.

    Finds Python test files in repo_info.test_paths, extracts functions with the
    ``test_`` prefix, strips boilerplate (assertions, setUp/tearDown calls), applies
    quality scoring via _score_python_test_slice(), and returns valid Snippet objects.

    Quality criteria:
    - Function name starts with ``test_``
    - After boilerplate stripping: 3 ≤ non-comment lines ≤ 60
    - _score_python_test_slice() > 0 (must reference a public API symbol or hint)
    - ast.parse() succeeds on the candidate code

    Deduplication uses the shared seen_hashes set from the parent _extract_snippets()
    call so files already promoted via BPW-02 are not double-counted.
    """
    from launcher.workers.understand.file_classifier import LANG_BY_EXT

    snippets: "list[Snippet]" = []

    # Only process Python test files not already covered as source_examples above
    python_test_paths = [
        p for p in (repo_info.test_paths or [])
        if LANG_BY_EXT.get(Path(p).suffix.lower(), "") == "python"
    ][:_UND1_MAX_TEST_FILES]

    if not python_test_paths:
        return snippets

    logger.debug("[UND-1] candidate test files: %d", len(python_test_paths))

    for rel_path in python_test_paths:
        file_path = repo_dir / rel_path
        if not file_path.exists() or not file_path.is_file():
            continue
        try:
            code = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        if not code.strip():
            continue

        # Use existing extractor — max_slices=3 per file for UND-1
        slices = _extract_python_test_slices(code, api_surface, max_slices=_UND1_MAX_SLICES_PER_FILE)
        if not slices:
            continue

        for candidate in slices:
            # Length guard: count non-comment, non-empty lines
            nc_lines = [
                ln for ln in candidate.splitlines()
                if ln.strip() and not ln.strip().startswith("#")
            ]
            if len(nc_lines) > _UND1_MAX_NONCOMMENT_LINES:
                logger.debug("[UND-1] %s: slice too long (%d lines), skipping", rel_path, len(nc_lines))
                continue
            if len(nc_lines) < _UND1_MIN_NONCOMMENT_LINES:
                logger.debug("[UND-1] %s: slice too short (%d lines), skipping", rel_path, len(nc_lines))
                continue

            # Syntax validation (already done in _extract_python_test_slices but guard here too)
            if not _validate_python_syntax(candidate):
                continue

            # Normalize imports
            normalized = _normalize_snippet_imports(candidate, api_surface, product)

            # Dedup against shared hash set
            h = _dedup_key(normalized.strip())
            if h in seen_hashes:
                logger.debug("[UND-1] %s: duplicate slice (hash=%s), skipping", rel_path, h)
                continue
            seen_hashes.add(h)

            linked_claim_ids = _link_snippet_to_claims(normalized, claims)

            snippets.append(Snippet(
                code=normalized.strip(),
                language="python",
                source_type="extracted",
                source_file=rel_path,
                claim_ids=linked_claim_ids,
                syntax_valid=True,
            ))

    logger.debug("[UND-1] extracted %d test-function snippets from %d files", len(snippets), len(python_test_paths))
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
    """Normalize Python imports to the runtime-facing import path.

    Handles: import X, import X as Y, from X import Y, and removes
    non-FOSS modules like aspose.pydrawing.
    """
    target_import = product.runtime_import or product.canonical_import
    if not target_import:
        return code

    lines = code.split("\n")
    normalized: list[str] = []

    for line in lines:
        import_match = re.match(r"^(\s*)(import|from)\s+([\w.]+)", line)
        if import_match:
            indent = import_match.group(1)
            keyword = import_match.group(2)
            module = import_match.group(3)
            canonical_import = product.canonical_import or ""
            dotted_canonical = canonical_import.replace("_", ".", 1) if canonical_import else ""

            # Remove non-FOSS modules
            if "pydrawing" in module.lower():
                continue

            # Rewrite Aspose imports to the runtime-facing import contract.
            rewrite_prefixes = tuple(
                prefix for prefix in (
                    product.runtime_import or "",
                    canonical_import,
                    dotted_canonical,
                ) if prefix
            )
            rewritten_module = ""
            for prefix in rewrite_prefixes:
                if module == prefix or module.startswith(prefix + "."):
                    rewritten_module = target_import + module[len(prefix):]
                    break
            if not rewritten_module and (
                module.startswith("aspose.")
                or module == "aspose"
                or module == canonical_import
            ):
                rewritten_module = target_import
            if rewritten_module:
                if keyword == "import":
                    rest = line[import_match.end():]
                    normalized.append(f"{indent}import {rewritten_module}{rest}")
                else:
                    after_module = line[import_match.end():]
                    normalized.append(f"{indent}from {rewritten_module}{after_module}")
                continue

        normalized.append(line)

    return "\n".join(normalized)


def _uses_private_python_api(code: str) -> bool:
    """Return True when code references underscore-prefixed Python API members."""
    return bool(re.search(r"\._[A-Za-z]\w*", code))


def _validate_snippet_imports(
    snippets: "list[Snippet]",
    import_allowlist: "list[str]",
    api_surface: ApiSurface | None = None,
) -> "tuple[list[Snippet], int]":
    """Validate snippet import lines against import_allowlist.

    Returns (valid_snippets, invalid_count).
    Only validates Python snippets. Non-Python snippets pass through.
    Empty allowlist -> all snippets pass.
    TC-HAL-07
    """
    if not import_allowlist:
        return snippets, 0

    allowlist_set = set(import_allowlist)
    allow_roots = {entry.split(".")[0] for entry in allowlist_set if entry}
    public_symbols = _public_symbol_names(api_surface)
    valid: list[Snippet] = []
    invalid_count = 0

    for snippet in snippets:
        lang = (snippet.language or "").lower()
        if lang not in ("python", "py", ""):
            valid.append(snippet)
            continue

        # Extract import module paths from the snippet code
        import_paths = [
            p for pair in re.findall(
                r'(?:from\s+([\w.]+)\s+import|^import\s+([\w.]+))',
                snippet.code,
                re.MULTILINE,
            )
            for p in pair if p
        ]

        if not import_paths:
            if _uses_private_python_api(snippet.code):
                invalid_count += 1
                logger.debug("snippet_private_api_invalid [TC-4255]: source=%s", getattr(snippet, "source_file", ""))
                continue
            valid.append(snippet)
            continue

        product_imports = [
            imp for imp in import_paths if _is_product_import_path(imp, allowlist_set, allow_roots)
        ]
        if not product_imports:
            if _uses_private_python_api(snippet.code):
                invalid_count += 1
                logger.debug("snippet_private_api_invalid [TC-4255]: source=%s", getattr(snippet, "source_file", ""))
                continue
            valid.append(snippet)
            continue

        unknown_symbols = _unknown_product_import_symbols(
            snippet.code,
            allowlist_set,
            allow_roots,
            public_symbols,
        )

        def _allowed(imp: str) -> bool:
            if imp in allowlist_set:
                return True
            # prefix matching: imp=aspose.threed.scene, allowlist has aspose.threed -> OK
            return any(
                imp.startswith(a + ".") or a.startswith(imp + ".")
                for a in allowlist_set
            )

        if (
            all(_allowed(imp) for imp in product_imports)
            and not _uses_private_python_api(snippet.code)
            and not unknown_symbols
        ):
            valid.append(snippet)
        else:
            invalid_count += 1
            logger.debug(
                "snippet_import_invalid: imports=%s unknown_symbols=%s allowlist=%s [TC-HAL-07]",
                import_paths[:3], unknown_symbols[:3], list(allowlist_set)[:3],
            )

    return valid, invalid_count


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
            raw_env = getattr(llm_cfg, "api_key_env", None)
            api_key_env = raw_env if isinstance(raw_env, str) else None
            api_key = os.environ.get(api_key_env or "litellm_key", "")
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
            try:
                embedding_index.save(out)
            except (OSError, IOError) as exc:
                logger.warning(
                    "Phase B.4: could not write embedding_index.json (disk error) — "
                    "pipeline continues without embedding artifact: %s", exc,
                )
            else:
                logger.info(
                    "Phase B.4: embedding index saved (%d vectors) -> %s",
                    len(embedding_index), out,
                )
            return

    # Fallback: try run_dir
    run_dir = getattr(context, "run_dir", None)
    if run_dir is not None:
        out = Path(run_dir) / "artifacts" / "embedding_index.json"
        try:
            out.parent.mkdir(parents=True, exist_ok=True)
            embedding_index.save(out)
        except (OSError, IOError) as exc:
            logger.warning(
                "Phase B.4: could not write embedding_index.json via run_dir "
                "(disk error) — pipeline continues without embedding artifact: %s", exc,
            )
        else:
            logger.info(
                "Phase B.4: embedding index saved (%d vectors) -> %s",
                len(embedding_index), out,
            )
