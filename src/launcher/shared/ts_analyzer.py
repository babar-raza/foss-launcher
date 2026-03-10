"""Universal code analyzer using tree-sitter.

Handles all languages except Python (which uses stdlib ``ast`` for deeper
analysis).  Every language gets AST-level parsing via tree-sitter grammars,
with language-specific doc-comment extraction and a generic fallback for
unlisted languages.

Key design decisions
--------------------
* **Dual-parser strategy** — Python keeps ``ast``; everything else goes here.
* **No query API** — tree-sitter v0.25 changed the query interface; we use
  recursive traversal which is stable across versions.
* **Language-specific doc comments** — Javadoc, XML doc, JSDoc, GoDoc, PHPDoc,
  rustdoc, YARD are each handled; unknown languages skip doc extraction.
* **Generic fallback** — any tree-sitter grammar gets basic class/function
  extraction even without a dedicated handler.
"""

from __future__ import annotations

import re
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Lazy imports — tree-sitter is optional at import time so the rest of the
# package doesn't crash if it's not installed.
# ---------------------------------------------------------------------------
_ts_available: bool | None = None


def _ensure_ts() -> bool:
    global _ts_available
    if _ts_available is not None:
        return _ts_available
    with _parser_lock:
        if _ts_available is not None:
            return _ts_available
        try:
            import tree_sitter  # noqa: F401
            _ts_available = True
        except ImportError:
            logger.warning("tree_sitter_not_installed")
            _ts_available = False
    return _ts_available


# ---------------------------------------------------------------------------
# Result dataclass — matches the shape produced by code_analyzer.py for Python
# ---------------------------------------------------------------------------


@dataclass
class AnalysisResult:
    """Uniform output from code analysis, matching Python analyzer shape."""

    classes: list[dict[str, Any]] = field(default_factory=list)
    functions: list[dict[str, Any]] = field(default_factory=list)
    constants: list[dict[str, Any]] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    exports: list[str] = field(default_factory=list)
    module_path: str = ""
    language: str = ""


# ---------------------------------------------------------------------------
# Language loading
# ---------------------------------------------------------------------------

# Map from our internal language name to tree-sitter-language-pack name
_LANG_PACK_ALIASES: dict[str, str] = {
    "csharp": "_c_sharp_separate",  # sentinel — handled specially
    "c_sharp": "_c_sharp_separate",
    "cs": "_c_sharp_separate",
}

# Cache for loaded parsers (guarded by _parser_lock)
_parser_cache: dict[str, Any] = {}
_parser_lock = threading.Lock()


def _resolve_lang_name(language: str) -> str:
    """Normalise language name for tree-sitter lookup."""
    lang = language.lower().strip()
    return _LANG_PACK_ALIASES.get(lang, lang)


def _get_parser(language: str):
    """Return a tree-sitter Parser for *language*.

    Thread-safe: uses ``_parser_lock`` to guard the shared cache so
    concurrent calls from :pymod:`concurrent.futures.ThreadPoolExecutor`
    don't race on parser initialization.
    """
    if not _ensure_ts():
        return None

    resolved = _resolve_lang_name(language)

    # Fast path: parser already cached (read under lock)
    with _parser_lock:
        if resolved in _parser_cache:
            return _parser_cache[resolved]

    # Slow path: create parser (outside lock to avoid holding it during I/O)
    from tree_sitter import Language, Parser  # noqa: E402

    parser = None
    if resolved == "_c_sharp_separate":
        try:
            import tree_sitter_c_sharp as _tsc
            lang_obj = Language(_tsc.language())
            parser = Parser(lang_obj)
        except ImportError:
            logger.warning("tree_sitter_c_sharp_not_installed")
            return None
    else:
        try:
            from tree_sitter_language_pack import get_parser as _get  # noqa: E402
            parser = _get(resolved)
        except (LookupError, ImportError):
            logger.debug("no_tree_sitter_grammar", language=language)
            return None

    # Store under lock (another thread may have raced — use setdefault)
    with _parser_lock:
        _parser_cache.setdefault(resolved, parser)
        return _parser_cache[resolved]


# ---------------------------------------------------------------------------
# AST Traversal helpers
# ---------------------------------------------------------------------------


def _collect_nodes(root, type_name: str) -> list:
    """Depth-first collect all nodes of *type_name*."""
    result: list = []
    stack = [root]
    while stack:
        node = stack.pop()
        if node.type == type_name:
            result.append(node)
        stack.extend(reversed(node.children))
    return result


def _collect_nodes_multi(root, type_names: set[str]) -> list:
    """Depth-first collect all nodes whose type is in *type_names*."""
    result: list = []
    stack = [root]
    while stack:
        node = stack.pop()
        if node.type in type_names:
            result.append(node)
        stack.extend(reversed(node.children))
    return result


def _child_by_type(node, type_name: str):
    """Return first child of *type_name*, or None."""
    for c in node.children:
        if c.type == type_name:
            return c
    return None


def _child_text(node, field_name: str) -> str:
    """Return text of the first child matching *field_name* (by field or type)."""
    child = node.child_by_field_name(field_name) if hasattr(node, "child_by_field_name") else None
    if child is None:
        child = _child_by_type(node, field_name)
    return child.text.decode() if child else ""


def _identifier_text(node) -> str:
    """Extract the identifier name from a declaration node."""
    name_node = node.child_by_field_name("name")
    if name_node:
        return name_node.text.decode()
    # Try common identifier node types across languages
    for id_type in ("identifier", "type_identifier", "simple_identifier",
                    "name", "constant"):
        ident = _child_by_type(node, id_type)
        if ident:
            return ident.text.decode()
    return ""


def _prev_sibling_comment(node) -> str | None:
    """Walk backwards to find a doc comment immediately before *node*.

    Also checks the parent's previous sibling for languages like Go where
    ``type_spec`` is wrapped in ``type_declaration`` and the comment is a
    sibling of the outer wrapper.
    """
    prev = node.prev_named_sibling
    if prev is not None and prev.type in ("comment", "block_comment", "line_comment"):
        return prev.text.decode()
    # Check parent's previous sibling (e.g. Go: comment -> type_declaration -> type_spec)
    if prev is None and node.parent is not None:
        parent_prev = node.parent.prev_named_sibling
        if parent_prev is not None and parent_prev.type in ("comment", "block_comment", "line_comment"):
            return parent_prev.text.decode()
    return None


# ---------------------------------------------------------------------------
# Doc comment parsing
# ---------------------------------------------------------------------------

# Patterns that identify doc comments vs regular comments
_DOC_PATTERNS: dict[str, re.Pattern] = {
    "javadoc": re.compile(r"^/\*\*"),  # /** ... */
    "xml_doc": re.compile(r"^///"),  # /// <summary>
    "jsdoc": re.compile(r"^/\*\*"),  # same as Javadoc
    "godoc": re.compile(r"^//"),  # any // before exported decl
    "phpdoc": re.compile(r"^/\*\*"),  # same as Javadoc
    "rustdoc": re.compile(r"^///"),  # /// rustdoc
    "rustmod": re.compile(r"^//!"),  # //! module doc
    "yard": re.compile(r"^#"),  # # YARD
}

# Which doc style each language uses
_LANG_DOC_STYLE: dict[str, str] = {
    "java": "javadoc",
    "c_sharp": "xml_doc",
    "_c_sharp_separate": "xml_doc",
    "csharp": "xml_doc",
    "cs": "xml_doc",
    "javascript": "jsdoc",
    "typescript": "jsdoc",
    "go": "godoc",
    "php": "phpdoc",
    "rust": "rustdoc",
    "ruby": "yard",
}


def _is_doc_comment(text: str, language: str) -> bool:
    """Check if a comment string is a doc comment for *language*."""
    resolved = _resolve_lang_name(language)
    style = _LANG_DOC_STYLE.get(resolved)
    if style is None:
        return False
    pattern = _DOC_PATTERNS.get(style)
    if pattern is None:
        return False
    return bool(pattern.match(text.strip()))


def _strip_doc_comment(text: str) -> str:
    """Strip doc-comment delimiters and return clean text."""
    lines = text.strip().splitlines()
    cleaned: list[str] = []
    for line in lines:
        s = line.strip()
        # Strip Javadoc/JSDoc/PHPDoc delimiters
        if s.startswith("/**"):
            s = s[3:]
        if s.endswith("*/"):
            s = s[:-2]
        if s.startswith("*"):
            s = s[1:]
        # Strip C# XML doc
        if s.startswith("///"):
            s = s[3:]
        # Strip Go/Rust line doc
        if s.startswith("//!") or s.startswith("///"):
            s = s[3:]
        elif s.startswith("//"):
            s = s[2:]
        # Strip Ruby YARD
        if s.startswith("#"):
            s = s[1:]
        cleaned.append(s.strip())
    return " ".join(c for c in cleaned if c).strip()


def _extract_first_sentence(text: str) -> str:
    """Extract the first sentence from doc comment text."""
    clean = _strip_doc_comment(text)
    # Remove XML tags (C# <summary>, <param>, etc.)
    clean = re.sub(r"<[^>]+>", "", clean)
    # First sentence ends at period followed by space or end
    m = re.match(r"([^.]+\.)", clean)
    return m.group(1).strip() if m else clean[:200].strip()


# ---------------------------------------------------------------------------
# Language-specific extraction
# ---------------------------------------------------------------------------

# Node types that represent class-like declarations per language
_CLASS_TYPES: dict[str, set[str]] = {
    "java": {"class_declaration", "interface_declaration", "enum_declaration", "annotation_type_declaration"},
    "_c_sharp_separate": {"class_declaration", "interface_declaration", "enum_declaration", "struct_declaration", "record_declaration"},
    "javascript": {"class_declaration"},
    "typescript": {"class_declaration", "interface_declaration", "type_alias_declaration", "enum_declaration"},
    "go": {"type_declaration", "type_spec"},
    "php": {"class_declaration", "interface_declaration", "trait_declaration", "enum_declaration"},
    "rust": {"struct_item", "enum_item", "trait_item", "impl_item"},
    "ruby": {"class", "module"},
    "kotlin": {"class_declaration", "object_declaration", "interface_declaration"},
    "dart": {"class_definition"},
    "scala": {"class_definition", "object_definition", "trait_definition"},
}

# Node types for function-like declarations
_FUNC_TYPES: dict[str, set[str]] = {
    "java": {"method_declaration", "constructor_declaration"},
    "_c_sharp_separate": {"method_declaration", "constructor_declaration", "property_declaration"},
    "javascript": {"function_declaration", "method_definition", "arrow_function"},
    "typescript": {"function_declaration", "method_definition", "arrow_function"},
    "go": {"function_declaration", "method_declaration"},
    "php": {"function_definition", "method_declaration"},
    "rust": {"function_item"},
    "ruby": {"method", "singleton_method"},
    "kotlin": {"function_declaration"},
    "dart": {"function_signature", "method_signature"},
    "scala": {"function_definition"},
}

# Node types for import statements
_IMPORT_TYPES: dict[str, set[str]] = {
    "java": {"import_declaration"},
    "_c_sharp_separate": {"using_directive"},
    "javascript": {"import_statement"},
    "typescript": {"import_statement"},
    "go": {"import_declaration"},
    "php": {"namespace_use_declaration"},
    "rust": {"use_declaration"},
    "ruby": {"call"},  # require/require_relative are method calls
    "kotlin": {"import_header"},
    "dart": {"import_or_export"},
    "scala": {"import_declaration"},
}

# Node types for package/namespace/module declarations
_MODULE_TYPES: dict[str, set[str]] = {
    "java": {"package_declaration"},
    "_c_sharp_separate": {"namespace_declaration"},
    "javascript": set(),
    "typescript": set(),
    "go": {"package_clause"},
    "php": {"namespace_definition"},
    "rust": {"mod_item"},
    "ruby": {"module"},
    "kotlin": {"package_header"},
    "dart": {"library_name"},
    "scala": {"package_clause"},
}


def _is_public(node, language: str) -> bool:
    """Check if a declaration node is public/exported."""
    resolved = _resolve_lang_name(language)

    # Go: exported = starts with uppercase
    if resolved == "go":
        name = _identifier_text(node)
        return bool(name and name[0].isupper())

    # Rust: check for 'pub' in visibility_modifier
    if resolved == "rust":
        for c in node.children:
            if c.type == "visibility_modifier":
                return True
        return False

    # JS/TS: check if parent is export_statement
    if resolved in ("javascript", "typescript"):
        parent = node.parent
        return parent is not None and parent.type in ("export_statement", "export_default_declaration")

    # Ruby: everything is public unless after private/protected
    if resolved == "ruby":
        return True

    # Java, C#, PHP, Kotlin: check modifier child nodes for 'public' keyword
    for c in node.children:
        if c.type in ("modifiers", "modifier", "access_modifier"):
            # Check for a 'public' sub-node inside the modifiers container
            for sub in c.children:
                if sub.type == "public" or sub.text.decode().strip() == "public":
                    return True
            # Fallback: if modifiers node itself is just "public"
            if c.text.decode().strip() == "public":
                return True
    # Also check direct 'public' keyword children
    for c in node.children:
        if c.type == "public":
            return True

    return False


def _extract_constant_value(node) -> str | None:
    """Try to extract a constant value from a field/variable declaration."""
    # Look for assignment-like children
    for c in node.children:
        if c.type in ("=", "variable_declarator", "init_declarator"):
            # Get the value part
            for sub in c.children:
                if sub.type in (
                    "string_literal", "number_literal", "integer_literal",
                    "decimal_integer_literal", "float_literal", "true", "false",
                    "string", "number", "integer",
                ):
                    return sub.text.decode().strip('"\'')
    return None


# ---------------------------------------------------------------------------
# Import normalization
# ---------------------------------------------------------------------------

# Patterns for Aspose-style imports per language
_IMPORT_PATTERNS: dict[str, re.Pattern] = {
    "java": re.compile(r"^import\s+(com\.aspose\.\w+)", re.MULTILINE),
    "_c_sharp_separate": re.compile(r"^using\s+(Aspose\.\w+)", re.MULTILINE),
    "javascript": re.compile(r'^(?:.*(?:require|from))\s*[("\'](@aspose/\w+)', re.MULTILINE),
    "typescript": re.compile(r'^(?:.*(?:require|from))\s*[("\'](@aspose/\w+)', re.MULTILINE),
    "go": re.compile(r'(?:^import\s+|^\s+)"(github\.com/aspose/\w+)"', re.MULTILINE),
    "php": re.compile(r"^use\s+(Aspose\\\w+)", re.MULTILINE),
    "rust": re.compile(r"^use\s+(aspose_\w+)", re.MULTILINE),
    "ruby": re.compile(r"^require\s+['\"]?(aspose[-_]\w+)", re.MULTILINE),
    # TC-3870: fill gaps for Kotlin, Dart, Scala
    "kotlin": re.compile(r"^import\s+(com\.aspose\.[a-zA-Z0-9._]+)", re.MULTILINE),
    "dart": re.compile(r"^import\s+'package:(aspose[a-zA-Z0-9_./]+)'", re.MULTILINE),
    "scala": re.compile(r"^import\s+(com\.aspose\.[a-zA-Z0-9._]+)", re.MULTILINE),
}


def normalize_imports(code: str, language: str, canonical_import: str) -> str:
    """Rewrite Aspose-style imports to the canonical import for *language*."""
    resolved = _resolve_lang_name(language)
    pattern = _IMPORT_PATTERNS.get(resolved)
    if pattern is None or not canonical_import:
        return code

    def _replacer(m: re.Match) -> str:
        original = m.group(0)
        old_pkg = m.group(1)
        return original.replace(old_pkg, canonical_import)

    return pattern.sub(_replacer, code)


def normalize_imports_ast(code: str, language: str, canonical_import: str) -> str:
    """Rewrite ``@aspose/*`` imports using tree-sitter AST (byte-precise).

    Replaces the regex-based :func:`normalize_imports` for JavaScript and
    TypeScript.  The regex ``(@aspose/\\w+)`` is hyphen-blind: it truncates
    ``@aspose/3d-foss`` to ``@aspose/3d``, then replaces, producing
    ``@aspose/3d-foss-foss``.  This function uses tree-sitter to locate the
    exact string node for each ``import_statement`` and performs a byte-level
    replacement — no character-class fragility.

    Falls back to :func:`normalize_imports` when:
    - ``language`` is not JavaScript or TypeScript
    - The tree-sitter grammar is unavailable at runtime

    Args:
        code: Source code string to normalize.
        language: Language tag (e.g. ``"typescript"``, ``"javascript"``).
        canonical_import: The correct import path (e.g. ``"@aspose/3d-foss"``).

    Returns:
        Normalized code string.  If ``canonical_import`` already matches every
        ``@aspose/*`` import in the code, the original string is returned
        unchanged (no copy).
    """
    resolved = _resolve_lang_name(language)

    if resolved not in ("javascript", "typescript"):
        return normalize_imports(code, language, canonical_import)

    parser = _get_parser(language)
    if parser is None or not canonical_import:
        # Graceful degradation: tree-sitter unavailable → fall back to regex
        return normalize_imports(code, language, canonical_import)

    code_bytes = code.encode("utf-8", errors="replace")
    tree = parser.parse(code_bytes)

    # Collect (start_byte, end_byte, replacement_bytes) for each wrong specifier.
    # Applied in reverse byte order so earlier positions are not shifted.
    replacements: list[tuple[int, int, bytes]] = []
    for node in _collect_nodes(tree.root_node, "import_statement"):
        for child in node.children:
            if child.type == "string":
                raw = child.text.decode("utf-8", errors="replace")  # e.g. "'@aspose/3d-foss'"
                inner = raw.strip("'\"")                             # e.g.  "@aspose/3d-foss"
                if inner.startswith("@aspose/") and inner != canonical_import:
                    new_raw = raw.replace(inner, canonical_import, 1)
                    replacements.append(
                        (child.start_byte, child.end_byte, new_raw.encode("utf-8"))
                    )

    # TR-02: CommonJS require() — call_expression with require as callee.
    # Node chain: call_expression → identifier("require") + arguments → string
    for node in _collect_nodes(tree.root_node, "call_expression"):
        func_node = _child_by_type(node, "identifier")
        if func_node is None:
            continue
        if func_node.text.decode("utf-8", errors="replace") != "require":
            continue
        args_node = _child_by_type(node, "arguments")
        if args_node is None:
            continue
        for arg_child in args_node.children:
            if arg_child.type == "string":
                raw = arg_child.text.decode("utf-8", errors="replace")
                inner = raw.strip("'\"")
                if inner.startswith("@aspose/") and inner != canonical_import:
                    new_raw = raw.replace(inner, canonical_import, 1)
                    replacements.append(
                        (arg_child.start_byte, arg_child.end_byte, new_raw.encode("utf-8"))
                    )
                break  # only the first string argument matters

    if not replacements:
        return code

    result = bytearray(code_bytes)
    for start, end, new_bytes in sorted(replacements, reverse=True):
        result[start:end] = new_bytes
    return result.decode("utf-8", errors="replace")


# ---------------------------------------------------------------------------
# TC-4004: Enhanced extraction helpers for typed methods/properties/enums
# ---------------------------------------------------------------------------


def _extract_method_params(method_node) -> list[dict[str, str]]:
    """Extract method parameters with type annotations from a method node.

    Works for TypeScript, JavaScript, Java, C# method declarations.
    Returns list of {"name": str, "type_annotation": str}.
    """
    params: list[dict[str, str]] = []
    # Find formal_parameters or parameter_list child
    param_list = None
    for c in method_node.children:
        if c.type in ("formal_parameters", "parameter_list", "parameters",
                       "formal_parameter_list"):
            param_list = c
            break
    if not param_list:
        return params

    for p in param_list.children:
        if p.type in ("(", ")", ","):
            continue
        if p.type in ("required_parameter", "optional_parameter",
                       "formal_parameter", "parameter",
                       "rest_parameter", "simple_formal_parameter"):
            pname = ""
            ptype = ""
            for sub in p.children:
                if sub.type in ("identifier", "property_identifier"):
                    pname = sub.text.decode()
                elif sub.type in ("type_annotation", "type_identifier",
                                   "predefined_type"):
                    raw = sub.text.decode()
                    # Strip leading ": " from type annotations
                    ptype = raw.lstrip(":").strip()
            if pname and pname != "self" and pname != "this":
                params.append({"name": pname, "type_annotation": ptype})
    return params


def _extract_return_type(method_node) -> str:
    """Extract return type annotation from a method/function node."""
    # Check for return_type field (used by tree-sitter TypeScript)
    ret = method_node.child_by_field_name("return_type")
    if ret:
        return ret.text.decode().lstrip(":").strip()
    # Also check for type_annotation child after parameter list
    after_params = False
    for c in method_node.children:
        if c.type in ("formal_parameters", "parameter_list"):
            after_params = True
            continue
        if after_params and c.type in ("type_annotation",):
            return c.text.decode().lstrip(":").strip()
        if c.type in ("{", "block", "statement_block"):
            break
    return ""


def _extract_type_annotation(node) -> str:
    """Extract type annotation from a property/field node."""
    for c in node.children:
        if c.type in ("type_annotation", "type_identifier", "predefined_type"):
            return c.text.decode().lstrip(":").strip()
    return ""


def _has_modifier(node, modifier: str) -> bool:
    """Check if a method/property node has a specific modifier keyword."""
    for c in node.children:
        if c.type == modifier:
            return True
        if c.type in ("modifiers", "modifier", "accessibility_modifier"):
            for sub in c.children:
                if sub.type == modifier or sub.text.decode().strip() == modifier:
                    return True
    return False


def _is_getter_method(method_node) -> bool:
    """Check if a method is a getter (get keyword)."""
    for c in method_node.children:
        if c.type == "get":
            return True
        if c.text.decode().strip() == "get" and c.type in ("property_identifier", "identifier"):
            # This is the method name "get", not a getter keyword
            return False
    return False


def _extract_enum_value(member_node) -> str:
    """Extract the value from an enum member assignment."""
    found_eq = False
    for c in member_node.children:
        if c.type == "=" or c.text.decode().strip() == "=":
            found_eq = True
            continue
        if found_eq:
            return c.text.decode().strip().rstrip(",")
    return ""


# ---------------------------------------------------------------------------
# Main analyzer class
# ---------------------------------------------------------------------------


class TreeSitterAnalyzer:
    """Universal code analyzer using tree-sitter.

    Handles any language except Python (which uses stdlib ``ast`` for
    deeper analysis).  Falls back gracefully if tree-sitter is not
    installed or a grammar is unavailable.
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze_file(
        self,
        file_path: str | Path,
        language: str,
        repo_dir: str | Path | None = None,
    ) -> AnalysisResult:
        """Analyse a source file and return structured results."""
        file_path = Path(file_path)
        if not file_path.exists():
            return AnalysisResult(language=language)

        try:
            code = file_path.read_bytes()
        except (OSError, UnicodeDecodeError):
            return AnalysisResult(language=language)

        parser = _get_parser(language)
        if parser is None:
            return AnalysisResult(language=language)

        tree = parser.parse(code)
        root = tree.root_node
        resolved = _resolve_lang_name(language)
        rel_path = str(file_path.relative_to(repo_dir)) if repo_dir and file_path.is_relative_to(Path(repo_dir)) else str(file_path)

        result = AnalysisResult(language=language)

        # Extract module path
        result.module_path = self._extract_module_path(root, resolved)

        # Extract classes
        class_types = _CLASS_TYPES.get(resolved, {"class_declaration"})
        class_nodes = _collect_nodes_multi(root, class_types)
        for node in class_nodes:
            cls = self._extract_class(node, resolved, rel_path, language)
            if cls:
                result.classes.append(cls)

        # Extract top-level functions (not methods inside classes)
        func_types = _FUNC_TYPES.get(resolved, {"function_declaration"})
        func_nodes = _collect_nodes_multi(root, func_types)
        for node in func_nodes:
            # Skip methods inside classes (already captured)
            if self._is_inside_class(node, class_types):
                continue
            func = self._extract_function(node, resolved, rel_path, language)
            if func:
                result.functions.append(func)

        # Extract imports
        result.imports = self._extract_imports(root, resolved)

        # Extract exports
        result.exports = self._extract_exports(root, resolved, class_nodes, func_nodes, language)

        # Extract constants
        result.constants = self._extract_constants(root, resolved)

        return result

    def validate_snippet(self, code: str, language: str) -> bool:
        """Parse *code* with tree-sitter and return True if it has no errors."""
        parser = _get_parser(language)
        if parser is None:
            # Can't validate — assume valid (graceful degradation)
            return True
        tree = parser.parse(code.encode("utf-8", errors="replace"))
        return not tree.root_node.has_error

    def extract_doc_comments(
        self, file_path: str | Path, language: str
    ) -> list[dict[str, Any]]:
        """Extract doc comments from a file, each with its associated declaration."""
        file_path = Path(file_path)
        if not file_path.exists():
            return []
        try:
            code = file_path.read_bytes()
        except (OSError, UnicodeDecodeError):
            return []

        parser = _get_parser(language)
        if parser is None:
            return []

        tree = parser.parse(code)
        return self._walk_doc_comments(tree.root_node, language)

    def extract_imports_from_code(self, code: str, language: str) -> list[str]:
        """Extract import statements from a code string."""
        parser = _get_parser(language)
        if parser is None:
            return []
        tree = parser.parse(code.encode("utf-8", errors="replace"))
        resolved = _resolve_lang_name(language)
        return self._extract_imports(tree.root_node, resolved)

    def extract_exports_from_code(self, code: str, language: str) -> list[str]:
        """Extract exported/public names from a code string."""
        parser = _get_parser(language)
        if parser is None:
            return []
        tree = parser.parse(code.encode("utf-8", errors="replace"))
        resolved = _resolve_lang_name(language)
        class_types = _CLASS_TYPES.get(resolved, {"class_declaration"})
        func_types = _FUNC_TYPES.get(resolved, {"function_declaration"})
        class_nodes = _collect_nodes_multi(tree.root_node, class_types)
        func_nodes = _collect_nodes_multi(tree.root_node, func_types)
        return self._extract_exports(tree.root_node, resolved, class_nodes, func_nodes, language)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _extract_module_path(self, root, resolved: str) -> str:
        mod_types = _MODULE_TYPES.get(resolved, set())
        for mt in mod_types:
            nodes = _collect_nodes(root, mt)
            for node in nodes:
                # Java: package com.aspose.cells;
                if resolved == "java":
                    # scoped_identifier or identifier child
                    for c in node.children:
                        if c.type in ("scoped_identifier", "identifier"):
                            return c.text.decode()
                # C#: namespace Aspose.Cells { ... }
                if resolved == "_c_sharp_separate":
                    name = node.child_by_field_name("name")
                    if name:
                        return name.text.decode()
                # Go: package main
                if resolved == "go":
                    ident = _child_by_type(node, "package_identifier")
                    if ident:
                        return ident.text.decode()
                # PHP: namespace Aspose\Cells;
                if resolved == "php":
                    name = node.child_by_field_name("name")
                    if name:
                        return name.text.decode()
                # Kotlin: package com.aspose.cells
                if resolved == "kotlin":
                    ident = _child_by_type(node, "identifier")
                    if ident:
                        return ident.text.decode()
                # Generic: try text extraction
                text = node.text.decode()
                # Extract the path after the keyword
                for kw in ("package", "namespace", "module", "library"):
                    if kw in text:
                        rest = text.split(kw, 1)[1].strip().rstrip(";{").strip()
                        if rest:
                            return rest
        return ""

    def _extract_class(self, node, resolved: str, rel_path: str, language: str) -> dict[str, Any] | None:
        name = _identifier_text(node)
        if not name:
            return None

        doc = _prev_sibling_comment(node)
        docstring = ""
        if doc and _is_doc_comment(doc, language):
            docstring = _extract_first_sentence(doc)

        # TC-4004: Detect enum declarations
        is_enum = node.type in ("enum_declaration", "enum_item")

        # Extract base classes
        bases: list[str] = []
        for c in node.children:
            if c.type in ("superclass", "super_class", "class_heritage",
                          "supertype_list", "extends_type", "type_list",
                          "base_list", "superinterfaces"):
                bases.append(c.text.decode())
            elif c.type in ("superclass_clause",):
                bases.append(c.text.decode())

        # Extract methods, properties, and enum members from class body
        func_types = _FUNC_TYPES.get(resolved, {"method_declaration"})
        methods: list[str] = []
        method_details: list[dict[str, Any]] = []
        property_details: list[dict[str, Any]] = []
        enum_members: list[dict[str, Any]] = []
        properties: list[str] = []

        for c in node.children:
            # Look inside class body
            body = c if c.type in ("class_body", "declaration_list", "block",
                                    "enum_body", "interface_body",
                                    "trait_body", "impl_body") else None
            if body:
                for member in body.children:
                    # Methods / method_definition
                    if member.type in func_types:
                        mname = _identifier_text(member)
                        if mname:
                            methods.append(mname)
                            mdoc = _prev_sibling_comment(member)
                            mdocstring = ""
                            if mdoc and _is_doc_comment(mdoc, language):
                                mdocstring = _extract_first_sentence(mdoc)

                            # TC-4004: Extract parameters and return type
                            params = _extract_method_params(member)
                            return_type = _extract_return_type(member)
                            is_static = _has_modifier(member, "static")
                            is_async = _has_modifier(member, "async")
                            is_getter = _is_getter_method(member)

                            method_details.append({
                                "name": mname,
                                "docstring": mdocstring,
                                "docstring_snippet": mdocstring,
                                "start_line": member.start_point[0],
                                "parameters": params,
                                "return_type": return_type,
                                "is_static": is_static,
                                "is_async": is_async,
                                "is_getter": is_getter,
                                "kind": "staticmethod" if is_static else "",
                            })

                    # TC-4004: Property/field declarations
                    elif member.type in (
                        "public_field_definition", "field_definition",
                        "property_declaration", "field_declaration",
                        "property_signature",
                    ):
                        pname = _identifier_text(member)
                        if pname and not pname.startswith("_"):
                            properties.append(pname)
                            ptype = _extract_type_annotation(member)
                            pdoc = _prev_sibling_comment(member)
                            pdocstring = ""
                            if pdoc and _is_doc_comment(pdoc, language):
                                pdocstring = _extract_first_sentence(pdoc)
                            is_readonly = _has_modifier(member, "readonly")
                            property_details.append({
                                "name": pname,
                                "type_annotation": ptype,
                                "is_readonly": is_readonly,
                                "docstring_snippet": pdocstring,
                            })

                # TC-4004: Enum members from enum_body (TS-specific)
                if is_enum and body.type == "enum_body":
                    for member in body.children:
                        if member.type in ("{", "}", ","):
                            continue
                        ename = ""
                        evalue = ""
                        for sub in member.children:
                            if sub.type in ("property_identifier", "identifier"):
                                ename = sub.text.decode()
                            elif sub.type == "=":
                                pass
                            elif sub.type not in (",",) and ename:
                                evalue = sub.text.decode().strip()
                        if not ename:
                            # Fallback: use the member text directly
                            raw = member.text.decode().strip().rstrip(",")
                            if "=" in raw:
                                ename, evalue = raw.split("=", 1)
                                ename = ename.strip()
                                evalue = evalue.strip()
                            elif raw and raw[0].isalpha():
                                ename = raw
                        if ename:
                            # Avoid duplicates
                            if not any(em["name"] == ename for em in enum_members):
                                enum_members.append({"name": ename, "value": evalue})

        return {
            "name": name,
            "docstring": docstring,
            "bases": bases,
            "methods": methods,
            "method_details": method_details,
            "properties": properties,
            "property_details": property_details,
            "is_enum": is_enum,
            "enum_members": enum_members,
            "source_file": rel_path,
            "start_line": node.start_point[0],
            "module": "",
        }

    def _extract_function(self, node, resolved: str, rel_path: str, language: str) -> dict[str, Any] | None:
        name = _identifier_text(node)
        if not name:
            return None

        doc = _prev_sibling_comment(node)
        docstring = ""
        if doc and _is_doc_comment(doc, language):
            docstring = _extract_first_sentence(doc)

        # Try to get return type
        return_type = ""
        ret_node = node.child_by_field_name("return_type") or node.child_by_field_name("type")
        if ret_node:
            return_type = ret_node.text.decode()

        return {
            "name": name,
            "signature": node.text.decode().split("{")[0].strip() if "{" in node.text.decode() else name,
            "docstring": docstring,
            "return_type": return_type,
            "start_line": node.start_point[0],
            "source_file": rel_path,
        }

    def _is_inside_class(self, node, class_types: set[str]) -> bool:
        parent = node.parent
        while parent:
            if parent.type in class_types:
                return True
            if parent.type in ("class_body", "declaration_list", "impl_body",
                              "trait_body", "interface_body", "enum_body"):
                return True
            parent = parent.parent
        return False

    def _extract_imports(self, root, resolved: str) -> list[str]:
        import_types = _IMPORT_TYPES.get(resolved, set())
        results: list[str] = []
        for it in import_types:
            nodes = _collect_nodes(root, it)
            for node in nodes:
                text = node.text.decode().strip()
                # Ruby: filter to only require/require_relative calls
                if resolved == "ruby" and it == "call":
                    if not text.startswith(("require", "require_relative")):
                        continue
                results.append(text)
        return results

    def _extract_exports(self, root, resolved: str,
                          class_nodes: list, func_nodes: list,
                          language: str) -> list[str]:
        exports: list[str] = []
        for node in class_nodes:
            if _is_public(node, language):
                name = _identifier_text(node)
                if name:
                    exports.append(name)
        for node in func_nodes:
            if _is_public(node, language):
                name = _identifier_text(node)
                if name:
                    exports.append(name)
        return exports

    def _extract_constants(self, root, resolved: str) -> list[dict[str, Any]]:
        constants: list[dict[str, Any]] = []

        # Java: public static final
        if resolved == "java":
            fields = _collect_nodes(root, "field_declaration")
            for f in fields:
                mods = _child_by_type(f, "modifiers")
                if mods and "static" in mods.text.decode() and "final" in mods.text.decode():
                    name = ""
                    decl = _child_by_type(f, "variable_declarator")
                    if decl:
                        name = _identifier_text(decl)
                    val = _extract_constant_value(f)
                    if name:
                        constants.append({"name": name, "value": val or ""})

        # C#: public const, public static readonly
        if resolved == "_c_sharp_separate":
            fields = _collect_nodes(root, "field_declaration")
            for f in fields:
                text = f.text.decode()
                if "const " in text or "static readonly" in text:
                    decl = _child_by_type(f, "variable_declaration")
                    if decl:
                        var = _child_by_type(decl, "variable_declarator")
                        if var:
                            name = _identifier_text(var)
                            val = _extract_constant_value(var)
                            if name:
                                constants.append({"name": name, "value": val or ""})

        # JS/TS: const UPPER = ...
        if resolved in ("javascript", "typescript"):
            for node_type in ("variable_declaration", "lexical_declaration"):
                nodes = _collect_nodes(root, node_type)
                for n in nodes:
                    text = n.text.decode()
                    if text.startswith("const "):
                        decl = _child_by_type(n, "variable_declarator")
                        if decl:
                            name = _identifier_text(decl)
                            if name and name.isupper():
                                val = _extract_constant_value(decl)
                                constants.append({"name": name, "value": val or ""})

        # Go: const blocks
        if resolved == "go":
            specs = _collect_nodes(root, "const_spec")
            for spec in specs:
                name = _identifier_text(spec)
                if name and name[0].isupper():
                    val = _extract_constant_value(spec)
                    constants.append({"name": name, "value": val or ""})

        # Rust: pub const
        if resolved == "rust":
            items = _collect_nodes(root, "const_item")
            for item in items:
                vis = _child_by_type(item, "visibility_modifier")
                if vis:
                    name = _identifier_text(item)
                    if name:
                        val = _extract_constant_value(item)
                        constants.append({"name": name, "value": val or ""})

        return constants

    def _walk_doc_comments(self, root, language: str) -> list[dict[str, Any]]:
        """Walk the AST and pair doc comments with their declarations."""
        results: list[dict[str, Any]] = []
        resolved = _resolve_lang_name(language)
        class_types = _CLASS_TYPES.get(resolved, {"class_declaration"})
        func_types = _FUNC_TYPES.get(resolved, {"function_declaration"})
        decl_types = class_types | func_types

        for child in root.children:
            # Handle namespace/class body recursion
            if child.type in ("namespace_declaration", "declaration_list",
                             "class_body", "program", "source_file"):
                results.extend(self._walk_doc_comments(child, language))
                continue

            # Check for body containers that have declarations
            for sub in child.children:
                if sub.type in ("declaration_list", "class_body", "block"):
                    results.extend(self._walk_doc_comments(sub, language))

            if child.type not in decl_types:
                continue

            doc = _prev_sibling_comment(child)
            if doc and _is_doc_comment(doc, language):
                name = _identifier_text(child)
                results.append({
                    "name": name,
                    "doc_comment": doc,
                    "first_sentence": _extract_first_sentence(doc),
                    "kind": "class" if child.type in class_types else "function",
                    "line": child.start_point[0],
                })

        return results


# Module-level singleton
analyzer = TreeSitterAnalyzer()
