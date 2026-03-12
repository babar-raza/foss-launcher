"""File classification and binary detection for repository scouting.

Classifies every file in a cloned repo into one of seven categories
(source, doc, config, test, example, ci, asset) and detects binary files
so the bulk reader can skip them.

Used by scout.py during Phase A of the Understand worker.
"""
from __future__ import annotations

from pathlib import Path

from launcher.models.understanding import FileCategory

# ---------------------------------------------------------------------------
# Language detection by file extension
# ---------------------------------------------------------------------------

LANG_BY_EXT: dict[str, str] = {
    # Python
    ".py": "python", ".pyi": "python",
    # Java / Kotlin
    ".java": "java", ".kt": "kotlin",
    # C# / F# / VB.NET
    ".cs": "csharp", ".fs": "fsharp", ".vb": "vbnet",
    # JavaScript / TypeScript
    ".js": "javascript", ".mjs": "javascript", ".cjs": "javascript",
    ".ts": "typescript", ".tsx": "typescript", ".jsx": "javascript",
    # Go
    ".go": "go",
    # Rust
    ".rs": "rust",
    # Ruby
    ".rb": "ruby",
    # PHP
    ".php": "php",
    # C / C++
    ".c": "c", ".h": "c", ".cpp": "cpp", ".hpp": "cpp", ".cc": "cpp",
    # Swift / Objective-C
    ".swift": "swift", ".m": "objc",
    # Dart
    ".dart": "dart",
    # Scala
    ".scala": "scala",
    # Shell
    ".sh": "shell", ".bash": "shell", ".zsh": "shell",
    ".ps1": "powershell", ".psm1": "powershell",
    # SQL
    ".sql": "sql",
    # Lua
    ".lua": "lua",
    # R
    ".r": "r", ".R": "r",
    # Perl
    ".pl": "perl", ".pm": "perl",
}

# ---------------------------------------------------------------------------
# Binary file detection
# ---------------------------------------------------------------------------

BINARY_EXTENSIONS: frozenset[str] = frozenset({
    # Images
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".svg", ".webp", ".tiff", ".tif",
    # Fonts
    ".woff", ".woff2", ".ttf", ".otf", ".eot",
    # Documents (non-text)
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    # Archives
    ".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".rar",
    # Compiled / object
    ".exe", ".dll", ".so", ".dylib", ".a", ".lib", ".o", ".obj",
    ".class", ".jar", ".war", ".ear",
    ".wasm", ".pyc", ".pyo", ".pyd",
    # Media
    ".mp3", ".mp4", ".wav", ".ogg", ".flac", ".avi", ".mkv", ".mov",
    # Database
    ".db", ".sqlite", ".sqlite3",
    # Other binary
    ".bin", ".dat", ".nupkg", ".snk", ".pfx",
})

_NULL_CHECK_BYTES = 8192


def is_binary(path: Path) -> bool:
    """Detect whether a file is binary.

    Uses two checks:
    1. Known binary extensions (fast path).
    2. Null-byte heuristic on the first 8KB (fallback for unknown extensions).
    """
    if path.suffix.lower() in BINARY_EXTENSIONS:
        return True
    try:
        chunk = path.read_bytes()[:_NULL_CHECK_BYTES]
        return b"\x00" in chunk
    except (OSError, PermissionError):
        return True  # treat unreadable files as binary


# ---------------------------------------------------------------------------
# File classification
# ---------------------------------------------------------------------------

DOC_EXTENSIONS: frozenset[str] = frozenset({
    ".md", ".rst", ".adoc", ".asciidoc", ".textile",
})

DOC_EXTENSIONS_LOOSE: frozenset[str] = frozenset({".txt"})

_DOC_DIR_NAMES: frozenset[str] = frozenset({
    "docs", "doc", "documentation", "guide", "guides", "wiki",
})

_EXAMPLE_PATTERNS: frozenset[str] = frozenset({
    "example", "examples", "sample", "samples", "demo", "demos",
    "tutorial", "tutorials", "quickstart", "howto",
})

_TEST_PATTERNS: frozenset[str] = frozenset({
    "test", "tests", "spec", "specs", "__tests__",
    "test_", "_test", "testing",
})

_TEST_FILE_MARKERS: tuple[str, ...] = (
    "test_", "_test.", ".test.", ".spec.", "_spec.",
    "Test.java", "Test.cs", "Test.go", "_test.go", "_test.py",
    "Tests.java", "Tests.cs",
)

_CI_PATTERNS: tuple[str, ...] = (
    ".github/workflows/", ".github/actions/",
    ".gitlab-ci", ".circleci/",
    "Jenkinsfile", "azure-pipelines",
    ".travis.yml", "appveyor.yml",
    "bitbucket-pipelines.yml",
    "Taskfile.yml",
)

_CONFIG_EXTENSIONS: frozenset[str] = frozenset({
    ".yml", ".yaml", ".toml", ".ini", ".cfg", ".conf",
    ".json", ".xml", ".properties", ".env",
})

_CONFIG_NAMES: frozenset[str] = frozenset({
    "pyproject.toml", "setup.py", "setup.cfg", "requirements.txt",
    "package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
    "pom.xml", "build.gradle", "build.gradle.kts", "settings.gradle",
    "Makefile", "CMakeLists.txt", "meson.build",
    "Cargo.toml", "Cargo.lock",
    "go.mod", "go.sum",
    "composer.json", "composer.lock",
    "Gemfile", "Gemfile.lock",
    "build.sbt",
    "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
    ".gitignore", ".gitattributes", ".editorconfig",
    "tsconfig.json", "tslint.json", ".eslintrc.json", ".prettierrc",
    "babel.config.js", "webpack.config.js", "vite.config.ts",
    "nuget.config", "Directory.Build.props", "global.json",
})

_VENDORED_DIRS: frozenset[str] = frozenset({
    "vendor", "third_party", "thirdparty", "external", "contrib",
    "node_modules", "__pycache__", ".git",
    "plugin", "plugins", "submodules",
})

# Multi-word directory patterns that indicate third-party integration examples.
# Matched against lowered path segments joined with spaces.
_INTEGRATION_DIR_PATTERNS: frozenset[str] = frozenset({
    "mainstream framework integration",
    "framework integration",
    "third party integration",
    "thirdparty integration",
})

_EXCLUDED_DIRS: frozenset[str] = frozenset({
    ".git", "__pycache__", "node_modules", ".venv", "venv",
    ".tox", "dist", "build", ".eggs", ".mypy_cache",
    ".pytest_cache", ".ruff_cache", "target",
})


def _first_pattern_index(parts: tuple[str, ...], patterns: frozenset[str]) -> int | None:
    for idx, part in enumerate(parts):
        if part in patterns:
            return idx
    return None


def has_example_dir(rel_path: str) -> bool:
    """Return True when the path lives under an example/demo/sample directory."""
    lower = rel_path.lower().replace("\\", "/")
    parts = Path(lower).parts[:-1]
    return _first_pattern_index(parts, _EXAMPLE_PATTERNS) is not None


def has_test_dir(rel_path: str) -> bool:
    """Return True when the path lives under a test/spec directory."""
    lower = rel_path.lower().replace("\\", "/")
    parts = Path(lower).parts[:-1]
    return _first_pattern_index(parts, _TEST_PATTERNS) is not None


def detect_language(rel_path: str) -> str:
    """Detect programming language from file extension."""
    ext = Path(rel_path).suffix.lower()
    return LANG_BY_EXT.get(ext, "")


def classify_file(rel_path: str) -> FileCategory:
    """Classify a repository file into a category.

    Classification priority (first match wins):
    1. CI — paths matching CI tool patterns
    2. Test — paths under test dirs or matching test file markers
    3. Example — paths under example/sample/demo dirs
    4. Doc — documentation files (.md, .rst, .adoc, or .txt in doc dirs)
    5. Config — manifest files, build configs, dotfiles
    6. Source — files with known code extensions
    7. Asset — everything else
    """
    lower = rel_path.lower().replace("\\", "/")
    parts = Path(lower).parts
    name = Path(lower).name
    ext = Path(lower).suffix

    # 1. CI
    for pattern in _CI_PATTERNS:
        if pattern in lower:
            return FileCategory.ci

    example_dir_index = _first_pattern_index(parts[:-1], _EXAMPLE_PATTERNS)
    test_dir_index = _first_pattern_index(parts[:-1], _TEST_PATTERNS)

    # 2. Example
    # Example/demo/sample directory context is stronger than filename-level test markers.
    # This preserves real usage files like examples/test_export.py as example evidence
    # while still treating tests/examples/foo.py as tests because the test dir appears first.
    if example_dir_index is not None and (
        test_dir_index is None or example_dir_index <= test_dir_index
    ):
        return FileCategory.example

    # 3. Test
    if test_dir_index is not None:
        return FileCategory.test
    if any(lower.endswith(marker) or marker in name for marker in _TEST_FILE_MARKERS):
        return FileCategory.test

    # 4. Doc
    if ext in DOC_EXTENSIONS:
        return FileCategory.doc
    if ext in DOC_EXTENSIONS_LOOSE and any(part in _DOC_DIR_NAMES for part in parts):
        return FileCategory.doc

    # 5. Config
    if name in _CONFIG_NAMES:
        return FileCategory.config
    if ext in _CONFIG_EXTENSIONS and not detect_language(rel_path):
        return FileCategory.config

    # 6. Source
    if detect_language(rel_path):
        return FileCategory.source

    # 7. Default
    return FileCategory.asset


def is_excluded_dir(dir_name: str) -> bool:
    """Check if a directory should be excluded from file tree walking."""
    return dir_name in _EXCLUDED_DIRS


def is_vendored(rel_path: str) -> bool:
    """Check if a path is under a vendored/third-party directory.

    Checks both single-word vendored directory names and multi-word
    integration directory patterns (e.g., "Mainstream Framework Integration").
    """
    lower_path = rel_path.lower().replace("\\", "/")
    parts = Path(lower_path).parts

    # Single-word vendored directory check
    if any(part in _VENDORED_DIRS for part in parts):
        return True

    # Multi-word integration directory pattern check.
    # Join consecutive path parts and check against patterns.
    for pattern in _INTEGRATION_DIR_PATTERNS:
        if pattern in lower_path:
            return True

    return False
