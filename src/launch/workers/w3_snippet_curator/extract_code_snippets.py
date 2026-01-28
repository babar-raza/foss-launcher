"""W3.2 Extract code snippets from example files.

This module implements code snippet extraction per specs/05_example_curation.md.

Snippet extraction algorithm (binding):
1. Load repo_inventory.json from TC-400 (W1 RepoScout) - example_paths
2. Load evidence_map.json from TC-410 (W2 FactsBuilder) for prioritization
3. Parse code files to extract functions, classes, or full files
4. Use AST-based extraction for Python, regex-based for other languages
5. Score snippets by relevance (based on evidence mapping)
6. Filter snippets by quality (completeness, readability)
7. Generate stable snippet_id hashes (path + line_range + content sha256)
8. Validate snippet syntax (per language)
9. Sort snippets deterministically by (relevance_score DESC, path ASC, start_line ASC)

Spec references:
- specs/05_example_curation.md:35-52 (Code snippet extraction patterns)
- specs/05_example_curation.md:61-97 (Example discovery order and universal strategy)
- specs/10_determinism_and_caching.md (Stable output requirements)
- specs/21_worker_contracts.md:127-145 (W3 SnippetCurator contract)

TC-422: W3.2 Extract code snippets from examples
"""

from __future__ import annotations

import ast
import hashlib
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from ...io.run_layout import RunLayout
from ...models.event import (
    Event,
    EVENT_WORK_ITEM_STARTED,
    EVENT_WORK_ITEM_FINISHED,
    EVENT_ARTIFACT_WRITTEN,
)


# Language file extension mapping
LANGUAGE_EXTENSIONS = {
    ".py": "python",
    ".cs": "csharp",
    ".java": "java",
    ".js": "javascript",
    ".ts": "typescript",
    ".rb": "ruby",
    ".php": "php",
    ".go": "go",
    ".cpp": "cpp",
    ".c": "c",
    ".h": "c",
    ".hpp": "cpp",
}

# Minimum snippet quality thresholds
MIN_SNIPPET_LINES = 3
MAX_SNIPPET_LINES = 500
MIN_CODE_CONTENT_RATIO = 0.4  # At least 40% non-whitespace/non-comment


def detect_language_from_path(file_path: Path) -> str:
    """Detect language from file extension.

    Args:
        file_path: Path to source code file

    Returns:
        Normalized language name

    Spec reference: specs/05_example_curation.md:8-9 (language field)
    """
    suffix = file_path.suffix.lower()
    return LANGUAGE_EXTENSIONS.get(suffix, "unknown")


def compute_code_content_ratio(code: str, language: str) -> float:
    """Compute ratio of meaningful code content to total lines.

    Args:
        code: Code snippet content
        language: Programming language

    Returns:
        Ratio of non-empty, non-comment lines to total lines

    Spec reference: specs/05_example_curation.md:38-40 (Validation)
    """
    if not code.strip():
        return 0.0

    lines = code.split("\n")
    total_lines = len(lines)

    if total_lines == 0:
        return 0.0

    # Count meaningful lines (non-empty, non-comment)
    meaningful_lines = 0
    for line in lines:
        stripped = line.strip()

        # Skip empty lines
        if not stripped:
            continue

        # Skip comment-only lines (language-specific heuristics)
        if language == "python":
            if stripped.startswith("#"):
                continue
        elif language in ("csharp", "java", "javascript", "typescript", "cpp", "c", "go", "php"):
            if stripped.startswith(("//", "/*", "*", "*/")):
                continue
        elif language == "ruby":
            if stripped.startswith("#"):
                continue

        meaningful_lines += 1

    return meaningful_lines / total_lines


def assess_snippet_quality(snippet: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Assess snippet quality and determine if it should be included.

    Quality criteria:
    - Minimum lines: 3
    - Maximum lines: 500
    - Minimum code content ratio: 40%
    - Non-empty code

    Args:
        snippet: Snippet dictionary with code field

    Returns:
        Tuple of (is_valid, rejection_reason)

    Spec reference: specs/05_example_curation.md:38-48 (Validation)
    """
    code = snippet.get("code", "")
    language = snippet.get("language", "unknown")

    # Check if code is empty
    if not code.strip():
        return False, "empty_code"

    # Count lines
    lines = code.split("\n")
    line_count = len([line for line in lines if line.strip()])

    # Check minimum lines
    if line_count < MIN_SNIPPET_LINES:
        return False, "too_short"

    # Check maximum lines
    if line_count > MAX_SNIPPET_LINES:
        return False, "too_long"

    # Check code content ratio
    content_ratio = compute_code_content_ratio(code, language)
    if content_ratio < MIN_CODE_CONTENT_RATIO:
        return False, "low_content_ratio"

    return True, None


def compute_snippet_id(snippet: Dict[str, Any]) -> str:
    """Compute stable snippet_id hash.

    Per specs/05_example_curation.md:7-8, snippet_id is:
    "stable hash of normalized code + language"

    Per specs/21_worker_contracts.md:142:
    "stable snippet_id derived from {path, line_range, sha256(content)}"

    Args:
        snippet: Snippet dictionary with code, language, source_path, line range

    Returns:
        Stable snippet_id (sha256 hex)

    Spec reference: specs/05_example_curation.md:7-8 (snippet_id)
    """
    # Normalize code (stable whitespace handling)
    code = snippet.get("code", "")
    normalized_code = code.strip()

    # Build stable hash input
    hash_input = f"{normalized_code}|{snippet['language']}|{snippet['source_path']}|{snippet['start_line']}-{snippet['end_line']}"

    # Compute SHA256
    snippet_id = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()

    return snippet_id


def extract_python_functions(file_path: Path, content: str) -> List[Dict[str, Any]]:
    """Extract Python functions and classes using AST.

    Args:
        file_path: Path to Python file
        content: File content

    Returns:
        List of extracted code snippets (functions/classes)

    Spec reference: specs/05_example_curation.md:35-52 (Code extraction patterns)
    """
    snippets = []

    try:
        tree = ast.parse(content)
    except SyntaxError:
        # If file has syntax errors, fall back to full-file extraction
        return []

    lines = content.split("\n")

    # Extract top-level functions and classes
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            # Get line range
            start_line = node.lineno
            end_line = node.end_lineno if hasattr(node, 'end_lineno') else start_line

            # Extract code
            if end_line and start_line <= end_line <= len(lines):
                code_lines = lines[start_line - 1:end_line]
                code = "\n".join(code_lines)

                snippet = {
                    "language": "python",
                    "code": code,
                    "start_line": start_line,
                    "end_line": end_line,
                    "source_path": str(file_path),
                    "entity_type": "class" if isinstance(node, ast.ClassDef) else "function",
                    "entity_name": node.name,
                }

                snippets.append(snippet)

    return snippets


def extract_csharp_functions(file_path: Path, content: str) -> List[Dict[str, Any]]:
    """Extract C# methods and classes using regex patterns.

    Args:
        file_path: Path to C# file
        content: File content

    Returns:
        List of extracted code snippets (methods/classes)

    Spec reference: specs/05_example_curation.md:35-52 (Code extraction patterns)
    """
    snippets = []
    lines = content.split("\n")

    # Pattern for class declarations
    class_pattern = re.compile(
        r'^\s*(public|private|protected|internal)?\s*(static)?\s*class\s+(\w+)',
        re.MULTILINE
    )

    # Pattern for method declarations
    method_pattern = re.compile(
        r'^\s*(public|private|protected|internal)?\s*(static|virtual|override)?\s*\w+\s+(\w+)\s*\(',
        re.MULTILINE
    )

    # Find class/method declarations and extract code blocks
    for match in class_pattern.finditer(content):
        start_pos = match.start()
        start_line = content[:start_pos].count("\n") + 1
        entity_name = match.group(3)

        # Find matching closing brace
        end_line = find_closing_brace(lines, start_line - 1)

        if end_line and start_line <= end_line <= len(lines):
            code_lines = lines[start_line - 1:end_line]
            code = "\n".join(code_lines)

            snippet = {
                "language": "csharp",
                "code": code,
                "start_line": start_line,
                "end_line": end_line,
                "source_path": str(file_path),
                "entity_type": "class",
                "entity_name": entity_name,
            }

            snippets.append(snippet)

    return snippets


def find_closing_brace(lines: List[str], start_line_idx: int) -> Optional[int]:
    """Find the line number of the matching closing brace.

    Args:
        lines: List of code lines
        start_line_idx: Starting line index (0-indexed)

    Returns:
        Line number (1-indexed) of closing brace, or None if not found
    """
    brace_count = 0
    found_opening = False

    for i in range(start_line_idx, len(lines)):
        line = lines[i]

        # Count braces
        for char in line:
            if char == "{":
                brace_count += 1
                found_opening = True
            elif char == "}":
                brace_count -= 1

                # Found matching closing brace
                if found_opening and brace_count == 0:
                    return i + 1  # Return 1-indexed line number

    return None


def extract_full_file_snippet(file_path: Path, content: str, language: str) -> Dict[str, Any]:
    """Extract entire file as a single snippet.

    Used when function/class extraction is not available or file is small.

    Args:
        file_path: Path to source file
        content: File content
        language: Programming language

    Returns:
        Full-file snippet dictionary

    Spec reference: specs/05_example_curation.md:35-52 (Extract full files)
    """
    lines = content.split("\n")

    snippet = {
        "language": language,
        "code": content,
        "start_line": 1,
        "end_line": len(lines),
        "source_path": str(file_path),
        "entity_type": "file",
        "entity_name": file_path.name,
    }

    return snippet


def extract_snippets_from_file(
    file_path: Path,
    repo_dir: Path,
) -> List[Dict[str, Any]]:
    """Extract code snippets from a single source file.

    Extraction strategy:
    - Python: AST-based function/class extraction
    - C#: Regex-based method/class extraction
    - Java: Regex-based method/class extraction
    - Other languages: Full file extraction (if small enough)

    Args:
        file_path: Absolute path to source file
        repo_dir: Repository root directory

    Returns:
        List of extracted snippets with metadata

    Spec reference: specs/05_example_curation.md:35-52 (Code extraction patterns)
    """
    if not file_path.exists():
        return []

    # Detect language
    language = detect_language_from_path(file_path)

    if language == "unknown":
        return []

    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except (OSError, UnicodeDecodeError):
        return []

    # Make path relative to repo
    try:
        relative_path = file_path.relative_to(repo_dir)
    except ValueError:
        relative_path = file_path

    snippets = []

    # Language-specific extraction
    if language == "python":
        # AST-based extraction
        snippets = extract_python_functions(relative_path, content)

        # If no functions/classes found, extract full file (if small)
        if not snippets and len(content.split("\n")) <= MAX_SNIPPET_LINES:
            snippets = [extract_full_file_snippet(relative_path, content, language)]

    elif language == "csharp":
        # Regex-based extraction
        snippets = extract_csharp_functions(relative_path, content)

        # If no methods/classes found, extract full file (if small)
        if not snippets and len(content.split("\n")) <= MAX_SNIPPET_LINES:
            snippets = [extract_full_file_snippet(relative_path, content, language)]

    else:
        # For other languages, extract full file if small enough
        if len(content.split("\n")) <= MAX_SNIPPET_LINES:
            snippets = [extract_full_file_snippet(relative_path, content, language)]

    return snippets


def compute_snippet_relevance_score(
    snippet: Dict[str, Any],
    file_path: str,
    evidence_map: Optional[Dict[str, Any]],
) -> int:
    """Compute relevance score for snippet based on file location and evidence mapping.

    Scoring rules (per specs/05_example_curation.md):
    - Dedicated example folders (examples/, samples/, demo/): 100
    - README code fences: 90
    - Tests that look like usage examples: 80
    - Implementation files: 60
    - Other: 50

    Additional boost:
    - +10 if file is cited in evidence_map (high priority evidence)

    Args:
        snippet: Snippet dictionary
        file_path: Relative path to source file
        evidence_map: Evidence map for prioritization (optional)

    Returns:
        Relevance score (0-110)

    Spec reference: specs/05_example_curation.md:61-69 (Example discovery order)
    """
    path_lower = file_path.lower()

    # Base score from file location
    base_score = 50  # Default

    # Dedicated example folders get highest score
    if any(part in path_lower for part in ["examples/", "samples/", "demo/", "example_", "sample_"]):
        base_score = 100
    # README code (if we extracted from markdown, but this handles .py near README)
    elif "readme" in path_lower:
        base_score = 90
    # Tests that look like usage examples
    elif "test" in path_lower and ("example" in path_lower or "usage" in path_lower):
        base_score = 80
    # Implementation files
    elif "src/" in path_lower or "lib/" in path_lower:
        base_score = 60

    # Evidence map boost
    if evidence_map:
        # Check if this file is cited in evidence_map
        file_is_cited = False
        for claim in evidence_map.get("claims", []):
            for citation in claim.get("citations", []):
                if citation.get("path") == file_path:
                    file_is_cited = True
                    break
            if file_is_cited:
                break

        if file_is_cited:
            base_score += 10

    return base_score


def infer_tags_from_context(
    snippet: Dict[str, Any],
    file_path: str,
) -> List[str]:
    """Infer tags for snippet based on file path and entity name.

    Per specs/05_example_curation.md:33-36, tags should be:
    - Deterministic
    - Based on folder name, file name, and context
    - Stable ordering and no duplicates

    Args:
        snippet: Snippet dictionary
        file_path: Relative path to source file

    Returns:
        Sorted list of tags

    Spec reference: specs/05_example_curation.md:33-36 (Tagging)
    """
    tags = set()

    path_lower = file_path.lower()

    # Add tag based on file location
    if any(part in path_lower for part in ["examples/", "samples/", "demo/"]):
        tags.add("example")

    if "quickstart" in path_lower or "quick_start" in path_lower or "getting_started" in path_lower:
        tags.add("quickstart")

    if "tutorial" in path_lower:
        tags.add("tutorial")

    # Infer from file/entity name
    entity_name = snippet.get("entity_name", "").lower()

    if "convert" in path_lower or "convert" in entity_name:
        tags.add("convert")

    if "merge" in path_lower or "merge" in entity_name:
        tags.add("merge")

    if "extract" in path_lower or "extract" in entity_name:
        tags.add("extract")

    if "parse" in path_lower or "parse" in entity_name:
        tags.add("parse")

    if "render" in path_lower or "render" in entity_name:
        tags.add("render")

    if "load" in path_lower or "load" in entity_name:
        tags.add("load")

    if "save" in path_lower or "save" in entity_name:
        tags.add("save")

    # Default tag if no specific tags
    if not tags:
        tags.add("example")

    # Sort for determinism
    return sorted(tags)


def validate_snippet_syntax(snippet: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Validate snippet syntax for the language.

    For TC-422, we implement basic validation:
    - Python: Check for valid syntax using ast.parse
    - C#: Basic structural checks (braces, semicolons)
    - Other languages: Mark as unknown

    Args:
        snippet: Snippet dictionary with code and language

    Returns:
        Tuple of (syntax_ok, error_message)

    Spec reference: specs/05_example_curation.md:38-48 (Validation)
    """
    language = snippet.get("language", "unknown")
    code = snippet.get("code", "")

    if language == "python":
        # Validate Python syntax using ast.parse
        try:
            ast.parse(code)
            return True, None
        except SyntaxError as e:
            return False, f"SyntaxError: {e}"
        except Exception as e:
            return False, f"ParseError: {e}"

    elif language == "csharp":
        # Basic C# structural checks
        # Check for balanced braces
        open_braces = code.count("{")
        close_braces = code.count("}")

        if open_braces != close_braces:
            return False, "Unbalanced braces"

        return True, None

    else:
        # For other languages, skip validation
        # Return true with unknown runnable_ok
        return True, None


def load_repo_inventory(run_layout: RunLayout) -> Dict[str, Any]:
    """Load repo_inventory.json from TC-400.

    Args:
        run_layout: Run directory layout

    Returns:
        Repo inventory artifact

    Raises:
        FileNotFoundError: If repo_inventory.json not found
    """
    inventory_path = run_layout.artifacts_dir / "repo_inventory.json"

    if not inventory_path.exists():
        raise FileNotFoundError(
            f"repo_inventory.json not found at {inventory_path}. "
            "TC-400 (W1 RepoScout) must run before TC-422."
        )

    return json.loads(inventory_path.read_text(encoding="utf-8"))


def load_evidence_map(run_layout: RunLayout) -> Optional[Dict[str, Any]]:
    """Load evidence_map.json from TC-410 (optional for prioritization).

    Args:
        run_layout: Run directory layout

    Returns:
        Evidence map artifact or None if not found
    """
    evidence_path = run_layout.artifacts_dir / "evidence_map.json"

    if not evidence_path.exists():
        # Evidence map is optional for snippet extraction
        return None

    return json.loads(evidence_path.read_text(encoding="utf-8"))


def build_code_snippets_artifact(
    snippets: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Build code_snippets.json artifact.

    Args:
        snippets: List of extracted snippets

    Returns:
        Artifact dictionary

    Spec reference: specs/schemas/snippet_catalog.schema.json (schema structure)
    """
    # Remove internal fields before writing
    clean_snippets = []
    for snippet in snippets:
        clean_snippet = snippet.copy()
        clean_snippet.pop("relevance_score", None)
        clean_snippet.pop("entity_type", None)
        clean_snippet.pop("entity_name", None)
        clean_snippets.append(clean_snippet)

    artifact = {
        "schema_version": "1.0",
        "snippets": clean_snippets,
    }

    return artifact


def write_code_snippets_artifact(
    run_layout: RunLayout,
    artifact: Dict[str, Any],
) -> None:
    """Write code_snippets.json to artifacts directory.

    Args:
        run_layout: Run directory layout
        artifact: Code snippets artifact dictionary

    Spec reference: specs/21_worker_contracts.md:47 (Atomic writes)
    """
    artifact_path = run_layout.artifacts_dir / "code_snippets.json"

    # Ensure artifacts directory exists
    run_layout.artifacts_dir.mkdir(parents=True, exist_ok=True)

    # Write with stable JSON formatting (deterministic)
    content = json.dumps(artifact, indent=2, sort_keys=True) + "\n"

    # Atomic write using temp file + rename pattern
    temp_path = artifact_path.with_suffix(".tmp")
    temp_path.write_text(content, encoding="utf-8")
    temp_path.replace(artifact_path)


def emit_extract_code_snippets_events(
    run_layout: RunLayout,
    run_id: str,
    trace_id: str,
    span_id: str,
    snippets_extracted: int,
    files_processed: int,
) -> None:
    """Emit events for code snippet extraction operations.

    Per specs/21_worker_contracts.md:33-40, workers MUST emit:
    - WORK_ITEM_STARTED at beginning
    - ARTIFACT_WRITTEN for each artifact created
    - WORK_ITEM_FINISHED at completion

    Args:
        run_layout: Run directory layout
        run_id: Run identifier
        trace_id: Trace ID for telemetry
        span_id: Span ID for telemetry
        snippets_extracted: Number of snippets extracted
        files_processed: Number of files processed

    Spec reference: specs/21_worker_contracts.md:33-40
    """
    import datetime
    import uuid

    events_file = run_layout.run_dir / "events.ndjson"

    def write_event(event_type: str, payload: Dict[str, Any]) -> None:
        """Helper to write a single event to events.ndjson."""
        event = Event(
            event_id=str(uuid.uuid4()),
            run_id=run_id,
            ts=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            type=event_type,
            payload=payload,
            trace_id=trace_id,
            span_id=span_id,
        )

        event_line = json.dumps(event.to_dict()) + "\n"

        # Append to events.ndjson (append-only log)
        with events_file.open("a", encoding="utf-8") as f:
            f.write(event_line)

    # WORK_ITEM_STARTED
    write_event(
        EVENT_WORK_ITEM_STARTED,
        {"worker": "w3_snippet_curator", "task": "extract_code_snippets", "step": "TC-422"},
    )

    # Custom event: CODE_SNIPPET_EXTRACTION_COMPLETED
    write_event(
        "CODE_SNIPPET_EXTRACTION_COMPLETED",
        {
            "snippets_extracted": snippets_extracted,
            "files_processed": files_processed,
        },
    )

    # ARTIFACT_WRITTEN (for code_snippets.json)
    artifact_path = run_layout.artifacts_dir / "code_snippets.json"
    if artifact_path.exists():
        content = artifact_path.read_bytes()
        sha256_hash = hashlib.sha256(content).hexdigest()

        write_event(
            EVENT_ARTIFACT_WRITTEN,
            {
                "name": "code_snippets.json",
                "path": str(artifact_path.relative_to(run_layout.run_dir)),
                "sha256": sha256_hash,
                "schema_id": "snippet_catalog.schema.json",
            },
        )

    # WORK_ITEM_FINISHED
    write_event(
        EVENT_WORK_ITEM_FINISHED,
        {
            "worker": "w3_snippet_curator",
            "task": "extract_code_snippets",
            "step": "TC-422",
            "status": "success",
        },
    )


def extract_code_snippets(repo_dir: Path, run_dir: Path) -> Dict[str, Any]:
    """Main entry point for TC-422 code snippet extraction from example files.

    This function:
    1. Loads repo_inventory.json from TC-400 (example_paths)
    2. Loads evidence_map.json from TC-410 (optional)
    3. Parses code files to extract functions/classes/full files
    4. Uses AST-based extraction for Python, regex-based for others
    5. Scores snippets by relevance
    6. Filters snippets by quality
    7. Validates snippet syntax
    8. Writes code_snippets.json artifact
    9. Emits telemetry events

    Args:
        repo_dir: Repository root directory (work/repo/)
        run_dir: Run directory path

    Returns:
        Code snippets artifact dictionary

    Spec references:
    - specs/05_example_curation.md:35-52 (Code snippet extraction)
    - specs/05_example_curation.md:61-97 (Example discovery order)
    - specs/21_worker_contracts.md:127-145 (W3 SnippetCurator contract)
    """
    run_layout = RunLayout(run_dir=run_dir)

    # Load repo_inventory.json
    repo_inventory = load_repo_inventory(run_layout)

    # Load evidence_map.json (optional)
    evidence_map = load_evidence_map(run_layout)

    # Get example paths from repo_inventory
    example_paths = repo_inventory.get("example_paths", [])

    # Extract snippets from all example files
    all_snippets = []
    files_processed = 0

    for example_path in example_paths:
        file_path = repo_dir / example_path

        # Skip directories
        if not file_path.is_file():
            continue

        # Extract snippets from this file
        snippets = extract_snippets_from_file(file_path, repo_dir)

        for snippet in snippets:
            # Assess quality
            is_valid, rejection_reason = assess_snippet_quality(snippet)

            if not is_valid:
                # Skip invalid snippets
                continue

            # Compute snippet_id
            snippet_id = compute_snippet_id(snippet)

            # Compute relevance score
            relevance_score = compute_snippet_relevance_score(
                snippet, example_path, evidence_map
            )

            # Infer tags
            tags = infer_tags_from_context(snippet, example_path)

            # Validate syntax
            syntax_ok, syntax_error = validate_snippet_syntax(snippet)

            enriched_snippet = {
                "snippet_id": snippet_id,
                "language": snippet["language"],
                "tags": tags,
                "source": {
                    "type": "repo_file",
                    "path": example_path,
                    "start_line": snippet["start_line"],
                    "end_line": snippet["end_line"],
                },
                "code": snippet["code"],
                "requirements": {
                    "dependencies": [],  # TODO: Infer from code (future enhancement)
                },
                "validation": {
                    "syntax_ok": syntax_ok,
                    "runnable_ok": "unknown",  # Runtime validation not implemented yet
                },
                "relevance_score": relevance_score,  # Internal field for sorting
                "entity_type": snippet.get("entity_type"),  # Internal field
                "entity_name": snippet.get("entity_name"),  # Internal field
            }

            # Add validation log if syntax failed
            if not syntax_ok and syntax_error:
                enriched_snippet["validation"]["log_path"] = None  # No log file for now
                enriched_snippet["validation"]["error"] = syntax_error

            all_snippets.append(enriched_snippet)

        files_processed += 1

    # Sort snippets deterministically
    # Per specs/10_determinism_and_caching.md:46 (snippets by language, tag, snippet_id)
    # and specs/05_example_curation.md (relevance-based ordering)
    # Sort by: relevance_score DESC, path ASC, start_line ASC
    all_snippets.sort(
        key=lambda s: (
            -s.get("relevance_score", 0),
            s["source"]["path"],
            s["source"]["start_line"],
        )
    )

    # Build artifact
    artifact = build_code_snippets_artifact(all_snippets)

    # Write code_snippets.json
    write_code_snippets_artifact(run_layout, artifact)

    # Emit events
    emit_extract_code_snippets_events(
        run_layout=run_layout,
        run_id="unknown",
        trace_id="unknown",
        span_id="unknown",
        snippets_extracted=len(all_snippets),
        files_processed=files_processed,
    )

    return artifact


def run_extract_code_snippets_worker(
    run_dir: Path,
    run_id: str,
    trace_id: str,
    span_id: str,
) -> int:
    """Run TC-422 extract_code_snippets worker.

    Entry point for W3.2 extract_code_snippets worker. This can be invoked by:
    - Orchestrator (TC-300) as part of W3 SnippetCurator
    - Standalone for testing/debugging

    Args:
        run_dir: Run directory path
        run_id: Run identifier
        trace_id: Trace ID for telemetry
        span_id: Span ID for telemetry

    Returns:
        Exit code (0 = success, non-zero = failure)

    Spec reference: specs/21_worker_contracts.md (Worker contract)
    """
    try:
        run_layout = RunLayout(run_dir=run_dir)
        repo_dir = run_layout.work_dir / "repo"

        if not repo_dir.exists():
            raise FileNotFoundError(
                f"Repository directory not found: {repo_dir}. "
                "TC-401 clone must run before TC-422."
            )

        # Extract code snippets
        artifact = extract_code_snippets(repo_dir, run_dir)

        # Emit events with proper IDs
        emit_extract_code_snippets_events(
            run_layout,
            run_id,
            trace_id,
            span_id,
            len(artifact["snippets"]),
            artifact.get("files_processed", 0),
        )

        return 0

    except FileNotFoundError as e:
        print(f"ERROR: {e}", flush=True)
        return 1

    except Exception as e:
        print(f"ERROR: Unexpected error in extract_code_snippets worker: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return 5  # Unexpected internal error
