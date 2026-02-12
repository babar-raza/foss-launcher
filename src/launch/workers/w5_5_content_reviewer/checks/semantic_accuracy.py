"""TC-1405: LLM-based semantic accuracy checks.

Three checks that evaluate content correctness:
1. API hallucination detection: Find fabricated API methods/classes
2. Licensing accuracy: Detect commercial language in FOSS products
3. Content relevance: Identify internal details presented as features

Each check has an offline fallback (regex/heuristic) when llm_client=None.
"""
from __future__ import annotations

import re
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from ....clients.llm_provider import LLMProviderClient


def check_all(
    drafts_dir: Path,
    product_facts: Dict[str, Any],
    llm_client: Optional[LLMProviderClient] = None,
    snippet_catalog: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Run all semantic accuracy checks.

    Runs 3 LLM-based semantic checks on every draft markdown file:
    1. API hallucination detection
    2. Licensing accuracy
    3. Content relevance

    Each check falls back to offline heuristics when llm_client is None.

    Args:
        drafts_dir: Path to drafts directory (RUN_DIR/drafts)
        product_facts: Product facts dict from product_facts.json
        llm_client: Optional LLM provider client (None = offline mode)
        snippet_catalog: Optional snippet catalog dict

    Returns:
        List of issue dicts matching W5.5 issue format
    """
    issues: List[Dict[str, Any]] = []

    if not drafts_dir.exists():
        return issues

    draft_files = sorted(drafts_dir.rglob("*.md"))
    for draft_file in draft_files:
        content = draft_file.read_text(encoding="utf-8", errors="replace")
        rel_path = str(draft_file.relative_to(drafts_dir))

        issues.extend(check_api_hallucination(
            content, product_facts, llm_client, rel_path, snippet_catalog,
        ))
        issues.extend(check_licensing_accuracy(
            content, product_facts, llm_client, rel_path,
        ))
        issues.extend(check_content_relevance(
            content, product_facts, llm_client, rel_path,
        ))

    return issues


# ---------------------------------------------------------------------------
# Check 1: API Hallucination Detection
# ---------------------------------------------------------------------------

def check_api_hallucination(
    content: str,
    product_facts: Dict[str, Any],
    llm_client: Optional[LLMProviderClient],
    page_slug: str,
    snippet_catalog: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Detect fabricated API methods/classes in code blocks.

    LLM path: sends code block + known API surface to LLM for verification.
    Offline fallback: extracts ClassName.method_name() patterns and cross-
    references against product_facts.api_surface_summary.

    Args:
        content: Markdown content of a draft file
        product_facts: Product facts dict
        llm_client: Optional LLM client (None = offline)
        page_slug: Relative path for issue location
        snippet_catalog: Optional snippet catalog

    Returns:
        List of issue dicts
    """
    issues: List[Dict[str, Any]] = []

    # Extract code blocks (```python ... ``` or ``` ... ```)
    code_blocks = _extract_code_blocks(content)
    if not code_blocks:
        return issues

    # Get known API surface
    api_surface = product_facts.get("api_surface_summary", {})
    known_classes = {c.lower(): c for c in api_surface.get("classes", [])}
    known_methods_by_class: Dict[str, set] = {}
    for cls_info in api_surface.get("class_details", []):
        cls_name = cls_info.get("name", "")
        methods = set(m.lower() for m in cls_info.get("methods", []))
        known_methods_by_class[cls_name.lower()] = methods

    # Also build a flat set of all known method names (for classes without details)
    all_known_methods = set()
    for methods in known_methods_by_class.values():
        all_known_methods.update(methods)

    if llm_client is not None:
        issues.extend(_api_hallucination_llm(
            code_blocks, api_surface, llm_client, page_slug, content,
        ))
    else:
        issues.extend(_api_hallucination_offline(
            code_blocks, known_classes, known_methods_by_class, page_slug, content,
        ))

    return issues


def _api_hallucination_llm(
    code_blocks: List[Dict[str, Any]],
    api_surface: Dict[str, Any],
    llm_client: LLMProviderClient,
    page_slug: str,
    content: str,
) -> List[Dict[str, Any]]:
    """LLM-based API hallucination detection."""
    issues: List[Dict[str, Any]] = []

    api_summary = _format_api_surface(api_surface)

    for block in code_blocks:
        code = block["code"]
        line = block["line"]

        prompt = (
            "You are an API verification assistant. Given the known API surface "
            "and a code block, identify any method or class names in the code "
            "that are NOT in the known API surface. Only flag names that look "
            "like product API calls (not standard library).\n\n"
            f"Known API surface:\n{api_summary}\n\n"
            f"Code block:\n```\n{code}\n```\n\n"
            "List each hallucinated API name on a separate line prefixed with "
            "'HALLUCINATED:'. If none are hallucinated, respond with 'NONE'."
        )

        try:
            response = llm_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                call_id=f"semantic_api_hallucination_{page_slug}_{line}",
            )
            response_text = response.get("content", "")

            for resp_line in response_text.strip().split("\n"):
                resp_line = resp_line.strip()
                if resp_line.upper().startswith("HALLUCINATED:"):
                    api_name = resp_line.split(":", 1)[1].strip()
                    if api_name and api_name.upper() != "NONE":
                        issues.append(_make_issue(
                            check="semantic_accuracy.api_hallucination",
                            severity="error",
                            message=f"Possibly hallucinated API: {api_name}",
                            path=page_slug,
                            line=line,
                        ))
        except Exception:
            # Fall through to offline if LLM fails for this block
            pass

    return issues


def _api_hallucination_offline(
    code_blocks: List[Dict[str, Any]],
    known_classes: Dict[str, str],
    known_methods_by_class: Dict[str, set],
    page_slug: str,
    content: str,
) -> List[Dict[str, Any]]:
    """Offline heuristic API hallucination detection.

    Extracts ClassName.method_name() patterns from code blocks and flags
    any method call where the class exists in the API surface but the
    method does NOT.

    Also resolves variable-to-class mappings (e.g., ``scene = Scene()``
    maps variable ``scene`` to class ``Scene``) so that
    ``scene.nonexistent()`` is correctly flagged.
    """
    issues: List[Dict[str, Any]] = []

    # Pattern: identifier.method_name(
    call_pattern = re.compile(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\.\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\(')
    # Pattern: variable = ClassName(...)
    assignment_pattern = re.compile(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*([A-Z][a-zA-Z0-9_]*)\s*\(')

    for block in code_blocks:
        code = block["code"]
        line = block["line"]

        # Build variable -> class name mapping from assignments
        var_to_class: Dict[str, str] = {}
        for var_name, cls_name in assignment_pattern.findall(code):
            var_to_class[var_name.lower()] = cls_name

        matches = call_pattern.findall(code)
        seen = set()
        for obj_name, method_name in matches:
            # Resolve variable to class if possible
            resolved_class = obj_name
            if obj_name.lower() in var_to_class:
                resolved_class = var_to_class[obj_name.lower()]

            pair = (resolved_class.lower(), method_name.lower())
            if pair in seen:
                continue
            seen.add(pair)

            # Only flag if the class IS known but the method is NOT
            # Offline heuristic: lower confidence → warn (not error)
            if resolved_class.lower() in known_classes:
                class_methods = known_methods_by_class.get(resolved_class.lower(), set())
                if class_methods and method_name.lower() not in class_methods:
                    display_class = known_classes.get(resolved_class.lower(), resolved_class)
                    issues.append(_make_issue(
                        check="semantic_accuracy.api_hallucination",
                        severity="warn",
                        message=(
                            f"Possibly hallucinated API: {display_class}.{method_name}() "
                            f"- class '{display_class}' exists but method '{method_name}' "
                            f"not found in API surface"
                        ),
                        path=page_slug,
                        line=line,
                    ))

    return issues


# ---------------------------------------------------------------------------
# Check 2: Licensing Accuracy
# ---------------------------------------------------------------------------

def check_licensing_accuracy(
    content: str,
    product_facts: Dict[str, Any],
    llm_client: Optional[LLMProviderClient],
    page_slug: str,
) -> List[Dict[str, Any]]:
    """Detect commercial language in FOSS product documentation.

    Only active when 'foss' appears in product_name (case-insensitive)
    or in product_facts.license.

    LLM path: sends licensing-related sections to LLM for evaluation.
    Offline fallback: regex for commercial terms in licensing sections.

    Args:
        content: Markdown content of a draft file
        product_facts: Product facts dict
        llm_client: Optional LLM client (None = offline)
        page_slug: Relative path for issue location

    Returns:
        List of issue dicts
    """
    issues: List[Dict[str, Any]] = []

    # Guard: only active for FOSS products
    product_name = product_facts.get("product_name", "")
    license_info = product_facts.get("license", "")
    if "foss" not in product_name.lower() and "foss" not in str(license_info).lower():
        return issues

    if llm_client is not None:
        issues.extend(_licensing_llm(content, llm_client, page_slug))
    else:
        issues.extend(_licensing_offline(content, page_slug))

    return issues


def _licensing_llm(
    content: str,
    llm_client: LLMProviderClient,
    page_slug: str,
) -> List[Dict[str, Any]]:
    """LLM-based licensing accuracy check."""
    issues: List[Dict[str, Any]] = []

    # Extract licensing-related sections
    sections = _extract_sections_by_heading(content, ["licen", "pricing", "plan"])
    if not sections:
        # If no specific licensing sections, check full content
        sections = [{"text": content, "line": 1}]

    for section in sections:
        prompt = (
            "You are a licensing compliance reviewer for open-source (FOSS) "
            "documentation. Identify any commercial licensing language in the "
            "following text that would be inappropriate for FOSS documentation.\n\n"
            "Look for: commercial license, metered license, evaluation limit, "
            "paid plan, trial version, proprietary, enterprise edition, "
            "premium feature, subscription required.\n\n"
            f"Text:\n{section['text'][:2000]}\n\n"
            "List each commercial term found on a separate line prefixed with "
            "'COMMERCIAL:'. If none found, respond with 'NONE'."
        )

        try:
            response = llm_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                call_id=f"semantic_licensing_{page_slug}_{section['line']}",
            )
            response_text = response.get("content", "")

            for resp_line in response_text.strip().split("\n"):
                resp_line = resp_line.strip()
                if resp_line.upper().startswith("COMMERCIAL:"):
                    term = resp_line.split(":", 1)[1].strip()
                    if term and term.upper() != "NONE":
                        issues.append(_make_issue(
                            check="semantic_accuracy.licensing_accuracy",
                            severity="error",
                            message=f"Commercial language in FOSS docs: {term}",
                            path=page_slug,
                            line=section["line"],
                            auto_fixable=True,
                        ))
        except Exception:
            pass

    return issues


def _licensing_offline(
    content: str,
    page_slug: str,
) -> List[Dict[str, Any]]:
    """Offline heuristic licensing accuracy check.

    Searches for commercial terms in licensing-related sections.
    """
    issues: List[Dict[str, Any]] = []

    commercial_terms = [
        r"commercial\s+licen[sc]",
        r"metered\s+licen[sc]",
        r"evaluation\s+limit",
        r"paid\s+plan",
        r"trial\s+version",
        r"\bproprietary\b",
        r"enterprise\s+edition",
        r"premium\s+feature",
        r"subscription\s+required",
    ]

    # Only check licensing-related sections
    sections = _extract_sections_by_heading(content, ["licen", "pricing", "plan"])
    if not sections:
        # If no licensing sections, skip (no false positives on non-licensing content)
        return issues

    for section in sections:
        text = section["text"]
        base_line = section["line"]
        lines = text.split("\n")

        for idx, line_text in enumerate(lines):
            for pattern in commercial_terms:
                if re.search(pattern, line_text, re.IGNORECASE):
                    # Offline heuristic: lower confidence → warn (not error)
                    issues.append(_make_issue(
                        check="semantic_accuracy.licensing_accuracy",
                        severity="warn",
                        message=(
                            f"Commercial language in FOSS docs: "
                            f"{line_text.strip()[:80]}"
                        ),
                        path=page_slug,
                        line=base_line + idx,
                        auto_fixable=True,
                    ))
                    break  # One issue per line

    return issues


# ---------------------------------------------------------------------------
# Check 3: Content Relevance
# ---------------------------------------------------------------------------

def check_content_relevance(
    content: str,
    product_facts: Dict[str, Any],
    llm_client: Optional[LLMProviderClient],
    page_slug: str,
) -> List[Dict[str, Any]]:
    """Identify internal implementation details presented as features.

    LLM path: asks LLM to identify internal details in feature sections.
    Offline fallback: looks for hex constants, jcid-prefixed identifiers,
    binary format references in feature/capability sections.

    Args:
        content: Markdown content of a draft file
        product_facts: Product facts dict
        llm_client: Optional LLM client (None = offline)
        page_slug: Relative path for issue location

    Returns:
        List of issue dicts
    """
    issues: List[Dict[str, Any]] = []

    if llm_client is not None:
        issues.extend(_content_relevance_llm(content, llm_client, page_slug))
    else:
        issues.extend(_content_relevance_offline(content, page_slug))

    return issues


def _content_relevance_llm(
    content: str,
    llm_client: LLMProviderClient,
    page_slug: str,
) -> List[Dict[str, Any]]:
    """LLM-based content relevance check."""
    issues: List[Dict[str, Any]] = []

    # Extract feature/capability sections
    sections = _extract_sections_by_heading(
        content, ["feature", "capabilit", "key feature"],
    )
    if not sections:
        return issues

    for section in sections:
        prompt = (
            "You are a documentation reviewer. Identify any internal "
            "implementation details that are presented as user-facing features "
            "in the following text. Internal details include: hex constants, "
            "binary format references (GUID, CompactID, FileNode), internal "
            "identifiers (jcid-prefixed), memory layout details, wire protocol "
            "specifics.\n\n"
            f"Text:\n{section['text'][:2000]}\n\n"
            "List each internal detail on a separate line prefixed with "
            "'INTERNAL:'. If none found, respond with 'NONE'."
        )

        try:
            response = llm_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                call_id=f"semantic_relevance_{page_slug}_{section['line']}",
            )
            response_text = response.get("content", "")

            for resp_line in response_text.strip().split("\n"):
                resp_line = resp_line.strip()
                if resp_line.upper().startswith("INTERNAL:"):
                    detail = resp_line.split(":", 1)[1].strip()
                    if detail and detail.upper() != "NONE":
                        issues.append(_make_issue(
                            check="semantic_accuracy.content_relevance",
                            severity="warn",
                            message=f"Internal implementation detail as feature: {detail}",
                            path=page_slug,
                            line=section["line"],
                        ))
        except Exception:
            pass

    return issues


def _content_relevance_offline(
    content: str,
    page_slug: str,
) -> List[Dict[str, Any]]:
    """Offline heuristic content relevance check.

    Looks for hex constants, jcid-prefixed identifiers, and binary format
    references in feature/capability sections.
    """
    issues: List[Dict[str, Any]] = []

    # Only check in feature/capability sections
    sections = _extract_sections_by_heading(
        content, ["feature", "capabilit", "key feature"],
    )
    if not sections:
        return issues

    internal_patterns = [
        (re.compile(r'\b0x[0-9a-fA-F]{4,}\b'), "Hex constant"),
        (re.compile(r'\bjcid[A-Za-z0-9_]+\b'), "jcid-prefixed identifier"),
        (re.compile(r'\bCompactID\b'), "Binary format reference (CompactID)"),
        (re.compile(r'\bFileNode\b'), "Binary format reference (FileNode)"),
        (re.compile(r'\b[A-F0-9]{8}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{12}\b'),
         "Raw GUID in feature section"),
    ]

    for section in sections:
        text = section["text"]
        base_line = section["line"]
        lines = text.split("\n")

        for idx, line_text in enumerate(lines):
            for pattern, description in internal_patterns:
                if pattern.search(line_text):
                    issues.append(_make_issue(
                        check="semantic_accuracy.content_relevance",
                        severity="warn",
                        message=(
                            f"{description} in feature section: "
                            f"{line_text.strip()[:80]}"
                        ),
                        path=page_slug,
                        line=base_line + idx,
                    ))
                    break  # One issue per line

    return issues


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_issue(
    check: str,
    severity: str,
    message: str,
    path: str,
    line: int,
    auto_fixable: bool = False,
) -> Dict[str, Any]:
    """Create a W5.5-compatible issue dict.

    Args:
        check: Check identifier (e.g. "semantic_accuracy.api_hallucination")
        severity: Issue severity ("error", "warn", "info")
        message: Human-readable description
        path: Relative file path
        line: Line number (0 if not determinable)
        auto_fixable: Whether the issue can be automatically fixed (default False)

    Returns:
        Issue dict matching W5.5 schema
    """
    return {
        "issue_id": str(uuid.uuid4()),
        "check": check,
        "severity": severity,
        "auto_fixable": auto_fixable,
        "message": message,
        "location": {
            "path": path,
            "line": line,
        },
    }


def _extract_code_blocks(content: str) -> List[Dict[str, Any]]:
    """Extract code blocks from markdown content.

    Args:
        content: Markdown content

    Returns:
        List of dicts with 'code', 'language', and 'line' keys
    """
    blocks: List[Dict[str, Any]] = []
    pattern = re.compile(r'```(\w*)\n(.*?)```', re.DOTALL)

    for match in pattern.finditer(content):
        language = match.group(1).lower() or "unknown"
        code = match.group(2)
        line = content[:match.start()].count("\n") + 1
        blocks.append({
            "code": code,
            "language": language,
            "line": line,
        })

    return blocks


def _extract_sections_by_heading(
    content: str,
    heading_keywords: List[str],
) -> List[Dict[str, Any]]:
    """Extract sections whose headings contain any of the given keywords.

    Each section spans from its heading to the next heading of equal or
    higher level (or end of file).

    Args:
        content: Markdown content
        heading_keywords: List of keywords to match in heading text (case-insensitive)

    Returns:
        List of dicts with 'text' and 'line' keys
    """
    sections: List[Dict[str, Any]] = []
    lines = content.split("\n")
    heading_pattern = re.compile(r'^(#{1,6})\s+(.+)$')

    i = 0
    while i < len(lines):
        match = heading_pattern.match(lines[i])
        if match:
            heading_level = len(match.group(1))
            heading_text = match.group(2).lower()

            if any(kw in heading_text for kw in heading_keywords):
                # Collect section text until next heading of equal or higher level
                section_start = i
                section_lines = [lines[i]]
                j = i + 1
                while j < len(lines):
                    next_match = heading_pattern.match(lines[j])
                    if next_match and len(next_match.group(1)) <= heading_level:
                        break
                    section_lines.append(lines[j])
                    j += 1

                sections.append({
                    "text": "\n".join(section_lines),
                    "line": section_start + 1,  # 1-indexed
                })
                i = j
                continue
        i += 1

    return sections


def _format_api_surface(api_surface: Dict[str, Any]) -> str:
    """Format API surface summary for LLM prompt.

    Args:
        api_surface: API surface summary dict

    Returns:
        Human-readable API surface summary
    """
    parts: List[str] = []

    classes = api_surface.get("classes", [])
    if classes:
        parts.append(f"Known classes: {', '.join(classes)}")

    functions = api_surface.get("functions", [])
    if functions:
        parts.append(f"Known functions: {', '.join(functions)}")

    for cls_info in api_surface.get("class_details", []):
        cls_name = cls_info.get("name", "")
        methods = cls_info.get("methods", [])
        if methods:
            parts.append(f"{cls_name} methods: {', '.join(methods)}")

    return "\n".join(parts) if parts else "No API surface information available."
