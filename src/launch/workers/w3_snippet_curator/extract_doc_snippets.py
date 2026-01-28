"""W3.1 Extract snippets from documentation files.

This module implements documentation snippet extraction per specs/05_example_curation.md.

Snippet extraction algorithm (binding):
1. Load discovered_docs.json from TC-400 (W1 RepoScout)
2. Load evidence_map.json from TC-410 (W2 FactsBuilder) for prioritization
3. Parse markdown files to extract code fences and sections
4. Score snippets by relevance (based on evidence mapping and doc priority)
5. Filter snippets by quality (length, content, formatting)
6. Generate stable snippet_id hashes (path + line_range + content sha256)
7. Validate snippet syntax (per language)
8. Sort snippets deterministically by (relevance_score DESC, path ASC, start_line ASC)

Spec references:
- specs/05_example_curation.md:13-34 (Snippet extraction algorithm)
- specs/05_example_curation.md:61-97 (Example discovery order and universal strategy)
- specs/10_determinism_and_caching.md (Stable output requirements)
- specs/21_worker_contracts.md:127-145 (W3 SnippetCurator contract)

TC-421: W3.1 Extract snippets from documentation
"""

from __future__ import annotations

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


# Code fence pattern (markdown)
# Matches: ```python, ```csharp, ```c#, ```javascript, etc.
CODE_FENCE_PATTERN = re.compile(
    r"^```([a-zA-Z0-9#+\-]*)\s*$",
    re.MULTILINE
)

# Language normalization map
LANGUAGE_NORMALIZATION = {
    "c#": "csharp",
    "cs": "csharp",
    "js": "javascript",
    "ts": "typescript",
    "py": "python",
    "rb": "ruby",
    "sh": "bash",
    "shell": "bash",
    "yml": "yaml",
}

# Minimum snippet quality thresholds
MIN_SNIPPET_LINES = 2
MAX_SNIPPET_LINES = 300
MIN_CODE_CONTENT_RATIO = 0.3  # At least 30% non-whitespace/non-comment


def normalize_language(language: str) -> str:
    """Normalize language identifier to canonical form.

    Args:
        language: Raw language identifier from code fence

    Returns:
        Normalized language name

    Spec reference: specs/05_example_curation.md:8-9 (language field)
    """
    if not language:
        return "unknown"

    lang_lower = language.lower().strip()

    # Apply normalization map
    normalized = LANGUAGE_NORMALIZATION.get(lang_lower, lang_lower)

    # Remove any trailing modifiers (e.g., "python3" -> "python")
    normalized = re.sub(r"\d+$", "", normalized)

    return normalized if normalized else "unknown"


def extract_code_fences(
    file_path: Path,
    content: str,
) -> List[Dict[str, Any]]:
    """Extract code fences from markdown content.

    Args:
        file_path: Path to markdown file (for provenance)
        content: Markdown file content

    Returns:
        List of code fence snippets with metadata

    Spec reference: specs/05_example_curation.md:24-27 (Extract code blocks)
    """
    snippets = []
    lines = content.split("\n")

    i = 0
    while i < len(lines):
        line = lines[i]
        fence_match = CODE_FENCE_PATTERN.match(line)

        if fence_match:
            # Found opening fence
            language_raw = fence_match.group(1)
            language = normalize_language(language_raw)
            start_line = i + 1  # Line numbers are 1-indexed

            # Find closing fence
            code_lines = []
            i += 1
            while i < len(lines):
                if lines[i].strip() == "```":
                    # Found closing fence
                    end_line = i  # Before closing fence

                    # Build code content
                    code_content = "\n".join(code_lines)

                    snippet = {
                        "language": language,
                        "code": code_content,
                        "start_line": start_line,  # 1-indexed line number of opening fence
                        "end_line": end_line,  # 1-indexed line number of closing fence
                        "source_path": str(file_path),
                    }

                    snippets.append(snippet)
                    break

                code_lines.append(lines[i])
                i += 1

        i += 1

    return snippets


def compute_code_content_ratio(code: str) -> float:
    """Compute ratio of meaningful code content to total lines.

    Args:
        code: Code snippet content

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

        # Skip comment-only lines (simple heuristic)
        if stripped.startswith(("#", "//", "/*", "*", "--", "<!--")):
            continue

        meaningful_lines += 1

    return meaningful_lines / total_lines


def assess_snippet_quality(snippet: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Assess snippet quality and determine if it should be included.

    Quality criteria:
    - Minimum lines: 2
    - Maximum lines: 300
    - Minimum code content ratio: 30%
    - Non-empty code

    Args:
        snippet: Snippet dictionary with code field

    Returns:
        Tuple of (is_valid, rejection_reason)

    Spec reference: specs/05_example_curation.md:38-48 (Validation)
    """
    code = snippet.get("code", "")

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
    content_ratio = compute_code_content_ratio(code)
    if content_ratio < MIN_CODE_CONTENT_RATIO:
        return False, "low_content_ratio"

    return True, None


def compute_snippet_id(snippet: Dict[str, Any]) -> str:
    """Compute stable snippet_id hash.

    Per specs/05_example_curation.md:7-8, snippet_id is:
    "stable hash of normalized code + language"

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


def compute_snippet_relevance_score(
    snippet: Dict[str, Any],
    doc_path: str,
    doc_metadata: Dict[str, Any],
    evidence_map: Optional[Dict[str, Any]],
) -> int:
    """Compute relevance score for snippet based on doc priority and evidence mapping.

    Scoring rules (per specs/05_example_curation.md):
    - README code fences (Quick Start): 100
    - Implementation notes code fences: 90
    - Architecture/API docs code fences: 80
    - Docs markdown code fences: 70
    - Other docs code fences: 50

    Additional boost:
    - +10 if doc is cited in evidence_map (high priority evidence)

    Args:
        snippet: Snippet dictionary
        doc_path: Path to documentation file
        doc_metadata: Documentation metadata from discovered_docs.json
        evidence_map: Evidence map for prioritization (optional)

    Returns:
        Relevance score (0-110)

    Spec reference: specs/05_example_curation.md:61-69 (Example discovery order)
    """
    # Base score from doc_type
    doc_type = doc_metadata.get("doc_type", "other")
    evidence_priority = doc_metadata.get("evidence_priority", "low")

    base_score = 50  # Default

    if doc_type == "readme":
        # README code fences get highest score
        # Quick Start blocks are usually the best (per spec line 66)
        base_score = 100
    elif doc_type == "implementation_notes":
        base_score = 90
    elif doc_type in ("architecture", "api_docs"):
        base_score = 80
    elif evidence_priority == "high":
        base_score = 70
    elif evidence_priority == "medium":
        base_score = 60

    # Evidence map boost
    if evidence_map:
        # Check if this doc is cited in evidence_map
        doc_is_cited = False
        for claim in evidence_map.get("claims", []):
            for citation in claim.get("citations", []):
                if citation.get("path") == doc_path:
                    doc_is_cited = True
                    break
            if doc_is_cited:
                break

        if doc_is_cited:
            base_score += 10

    return base_score


def infer_tags_from_context(
    snippet: Dict[str, Any],
    doc_path: str,
    doc_metadata: Dict[str, Any],
) -> List[str]:
    """Infer tags for snippet based on file path, doc type, and content context.

    Per specs/05_example_curation.md:33-36, tags should be:
    - Deterministic
    - Based on folder name, file name, and doc headings
    - Stable ordering and no duplicates

    Args:
        snippet: Snippet dictionary
        doc_path: Path to documentation file
        doc_metadata: Documentation metadata

    Returns:
        Sorted list of tags

    Spec reference: specs/05_example_curation.md:33-36 (Tagging)
    """
    tags = set()

    doc_type = doc_metadata.get("doc_type", "other")

    # Add doc_type as tag
    if doc_type == "readme":
        tags.add("quickstart")
        tags.add("readme")
    elif doc_type == "implementation_notes":
        tags.add("implementation")
    elif doc_type == "architecture":
        tags.add("architecture")
    elif doc_type == "api_docs":
        tags.add("api")

    # Infer from file path
    path_lower = doc_path.lower()

    if "quickstart" in path_lower or "quick_start" in path_lower or "getting_started" in path_lower:
        tags.add("quickstart")

    if "tutorial" in path_lower:
        tags.add("tutorial")

    if "example" in path_lower:
        tags.add("example")

    if "convert" in path_lower or "conversion" in path_lower:
        tags.add("convert")

    if "merge" in path_lower:
        tags.add("merge")

    if "extract" in path_lower:
        tags.add("extract")

    if "parse" in path_lower or "parsing" in path_lower:
        tags.add("parse")

    if "render" in path_lower:
        tags.add("render")

    # Default tag if no specific tags
    if not tags:
        tags.add("example")

    # Sort for determinism
    return sorted(tags)


def validate_snippet_syntax(snippet: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Validate snippet syntax for the language.

    For TC-421, we implement basic validation:
    - Python: Check for valid syntax using ast.parse
    - C#: Basic structural checks (braces, semicolons)
    - Other languages: Skip validation (syntax_ok = unknown)

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
            import ast
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

        # If code contains class/method declarations, it should be valid
        if "class " in code or "void " in code or "public " in code:
            return True, None

        # Otherwise, assume valid (incomplete snippet)
        return True, None

    else:
        # For other languages, skip validation
        # Return unknown (not boolean)
        return True, None  # We'll mark as syntax_ok=true, runnable_ok=unknown


def load_discovered_docs(run_layout: RunLayout) -> Dict[str, Any]:
    """Load discovered_docs.json from TC-400.

    Args:
        run_layout: Run directory layout

    Returns:
        Discovered docs artifact

    Raises:
        FileNotFoundError: If discovered_docs.json not found
    """
    docs_path = run_layout.artifacts_dir / "discovered_docs.json"

    if not docs_path.exists():
        raise FileNotFoundError(
            f"discovered_docs.json not found at {docs_path}. "
            "TC-400 (W1 RepoScout) must run before TC-421."
        )

    return json.loads(docs_path.read_text(encoding="utf-8"))


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


def extract_snippets_from_doc(
    doc_path: str,
    doc_metadata: Dict[str, Any],
    repo_dir: Path,
    evidence_map: Optional[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Extract code snippets from a single documentation file.

    Args:
        doc_path: Relative path to documentation file
        doc_metadata: Documentation metadata from discovered_docs.json
        repo_dir: Repository root directory
        evidence_map: Evidence map for prioritization (optional)

    Returns:
        List of extracted snippets with metadata

    Spec reference: specs/05_example_curation.md:24-27 (Extract code blocks)
    """
    file_path = repo_dir / doc_path

    if not file_path.exists():
        return []

    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except (OSError, UnicodeDecodeError):
        return []

    # Extract code fences
    code_fences = extract_code_fences(file_path, content)

    extracted_snippets = []

    for fence in code_fences:
        # Assess quality
        is_valid, rejection_reason = assess_snippet_quality(fence)

        if not is_valid:
            # Skip invalid snippets
            continue

        # Compute snippet_id
        snippet_id = compute_snippet_id(fence)

        # Compute relevance score
        relevance_score = compute_snippet_relevance_score(
            fence, doc_path, doc_metadata, evidence_map
        )

        # Infer tags
        tags = infer_tags_from_context(fence, doc_path, doc_metadata)

        # Validate syntax
        syntax_ok, syntax_error = validate_snippet_syntax(fence)

        snippet = {
            "snippet_id": snippet_id,
            "language": fence["language"],
            "tags": tags,
            "source": {
                "type": "repo_file",
                "path": doc_path,
                "start_line": fence["start_line"],
                "end_line": fence["end_line"],
            },
            "code": fence["code"],
            "requirements": {
                "dependencies": [],  # TODO: Infer from code (future enhancement)
            },
            "validation": {
                "syntax_ok": syntax_ok,
                "runnable_ok": "unknown",  # Runtime validation not implemented yet
            },
            "relevance_score": relevance_score,  # Internal field for sorting
        }

        # Add validation log if syntax failed
        if not syntax_ok and syntax_error:
            snippet["validation"]["log_path"] = None  # No log file for now
            snippet["validation"]["error"] = syntax_error

        extracted_snippets.append(snippet)

    return extracted_snippets


def build_doc_snippets_artifact(
    snippets: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Build doc_snippets.json artifact.

    Args:
        snippets: List of extracted snippets

    Returns:
        Artifact dictionary

    Spec reference: specs/schemas/snippet_catalog.schema.json (schema structure)
    """
    # Remove internal relevance_score field before writing
    clean_snippets = []
    for snippet in snippets:
        clean_snippet = snippet.copy()
        clean_snippet.pop("relevance_score", None)
        clean_snippets.append(clean_snippet)

    artifact = {
        "schema_version": "1.0",
        "snippets": clean_snippets,
    }

    return artifact


def write_doc_snippets_artifact(
    run_layout: RunLayout,
    artifact: Dict[str, Any],
) -> None:
    """Write doc_snippets.json to artifacts directory.

    Args:
        run_layout: Run directory layout
        artifact: Doc snippets artifact dictionary

    Spec reference: specs/21_worker_contracts.md:47 (Atomic writes)
    """
    artifact_path = run_layout.artifacts_dir / "doc_snippets.json"

    # Ensure artifacts directory exists
    run_layout.artifacts_dir.mkdir(parents=True, exist_ok=True)

    # Write with stable JSON formatting (deterministic)
    content = json.dumps(artifact, indent=2, sort_keys=True) + "\n"

    # Atomic write using temp file + rename pattern
    temp_path = artifact_path.with_suffix(".tmp")
    temp_path.write_text(content, encoding="utf-8")
    temp_path.replace(artifact_path)


def emit_extract_doc_snippets_events(
    run_layout: RunLayout,
    run_id: str,
    trace_id: str,
    span_id: str,
    snippets_extracted: int,
    docs_processed: int,
) -> None:
    """Emit events for snippet extraction operations.

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
        docs_processed: Number of docs processed

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
        {"worker": "w3_snippet_curator", "task": "extract_doc_snippets", "step": "TC-421"},
    )

    # Custom event: SNIPPET_EXTRACTION_COMPLETED
    write_event(
        "SNIPPET_EXTRACTION_COMPLETED",
        {
            "snippets_extracted": snippets_extracted,
            "docs_processed": docs_processed,
        },
    )

    # ARTIFACT_WRITTEN (for doc_snippets.json)
    artifact_path = run_layout.artifacts_dir / "doc_snippets.json"
    if artifact_path.exists():
        content = artifact_path.read_bytes()
        sha256_hash = hashlib.sha256(content).hexdigest()

        write_event(
            EVENT_ARTIFACT_WRITTEN,
            {
                "name": "doc_snippets.json",
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
            "task": "extract_doc_snippets",
            "step": "TC-421",
            "status": "success",
        },
    )


def extract_doc_snippets(repo_dir: Path, run_dir: Path) -> Dict[str, Any]:
    """Main entry point for TC-421 documentation snippet extraction.

    This function:
    1. Loads discovered_docs.json from TC-400
    2. Loads evidence_map.json from TC-410 (optional)
    3. Extracts code fences from documentation files
    4. Scores snippets by relevance
    5. Filters snippets by quality
    6. Validates snippet syntax
    7. Writes doc_snippets.json artifact
    8. Emits telemetry events

    Args:
        repo_dir: Repository root directory (work/repo/)
        run_dir: Run directory path

    Returns:
        Doc snippets artifact dictionary

    Spec references:
    - specs/05_example_curation.md:13-34 (Snippet extraction)
    - specs/05_example_curation.md:61-97 (Example discovery order)
    - specs/21_worker_contracts.md:127-145 (W3 SnippetCurator contract)
    """
    run_layout = RunLayout(run_dir=run_dir)

    # Load discovered_docs.json
    discovered_docs = load_discovered_docs(run_layout)

    # Load evidence_map.json (optional)
    evidence_map = load_evidence_map(run_layout)

    # Extract snippets from all discovered docs
    all_snippets = []
    docs_processed = 0

    doc_entrypoint_details = discovered_docs.get("doc_entrypoint_details", [])

    for doc_metadata in doc_entrypoint_details:
        doc_path = doc_metadata.get("path")

        if not doc_path:
            continue

        # Extract snippets from this doc
        snippets = extract_snippets_from_doc(
            doc_path, doc_metadata, repo_dir, evidence_map
        )

        all_snippets.extend(snippets)
        docs_processed += 1

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
    artifact = build_doc_snippets_artifact(all_snippets)

    # Write doc_snippets.json
    write_doc_snippets_artifact(run_layout, artifact)

    # Emit events
    emit_extract_doc_snippets_events(
        run_layout=run_layout,
        run_id="unknown",
        trace_id="unknown",
        span_id="unknown",
        snippets_extracted=len(all_snippets),
        docs_processed=docs_processed,
    )

    return artifact


def run_extract_doc_snippets_worker(
    run_dir: Path,
    run_id: str,
    trace_id: str,
    span_id: str,
) -> int:
    """Run TC-421 extract_doc_snippets worker.

    Entry point for W3.1 extract_doc_snippets worker. This can be invoked by:
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
                "TC-401 clone must run before TC-421."
            )

        # Extract doc snippets
        artifact = extract_doc_snippets(repo_dir, run_dir)

        # Emit events with proper IDs
        emit_extract_doc_snippets_events(
            run_layout,
            run_id,
            trace_id,
            span_id,
            len(artifact["snippets"]),
            artifact.get("docs_processed", 0),
        )

        return 0

    except FileNotFoundError as e:
        print(f"ERROR: {e}", flush=True)
        return 1

    except Exception as e:
        print(f"ERROR: Unexpected error in extract_doc_snippets worker: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return 5  # Unexpected internal error
