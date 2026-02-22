"""Gate 16: Content Hygiene.

Detects residual pipeline artifacts and structural anomalies in generated
content that indicate incomplete post-processing or LLM output corruption.

RCA context: LLM-generated content sometimes retains internal pipeline markers
(claim tags, raw parameter dumps), produces fragmented code fences, or emits
corrupted/repeated code snippets.  Gate 16 catches these before publication.

Per specs/09_validation_gates.md (content hygiene requirements).
"""

from __future__ import annotations

import re
from typing import Any, Dict, List


# ---------------------------------------------------------------------------
# Detector 1: Visible claim markers  (G16-001, BLOCKER)
# ---------------------------------------------------------------------------

def _detect_visible_claim_markers(
    content: str,
    page_path: str,
) -> List[Dict[str, Any]]:
    """Find ``[claim: ...]`` markers that leaked into rendered content.

    Claim markers are internal pipeline annotations and must never be visible
    in published output.  HTML-comment markers (``<!-- claim: ... -->``) and
    frontmatter are excluded because they are invisible to readers.

    Args:
        content: Full page content (markdown).
        page_path: File path for error reporting.

    Returns:
        List of BLOCKER issue dicts, one per leaked marker.
    """
    issues: List[Dict[str, Any]] = []

    # Strip frontmatter so markers inside it are ignored.
    body = _strip_frontmatter(content)

    # Strip HTML comments so ``<!-- claim: id -->`` is not flagged.
    body = re.sub(r"<!--.*?-->", "", body, flags=re.DOTALL)

    pattern = re.compile(r"\[claim:\s*[a-fA-F0-9_-]+\]")

    for match in pattern.finditer(body):
        # Compute line number in the *original* content for accurate reporting.
        # We search the original content for the same match position.
        line_num = content[: content.find(match.group())].count("\n") + 1

        issues.append({
            "issue_id": f"gate16_visible_claim_marker_{_slug(page_path)}_{line_num}",
            "gate": "gate_16_content_hygiene",
            "severity": "blocker",
            "message": f"Visible claim marker in rendered content: {match.group()}",
            "error_code": "G16-001",
            "location": {"path": page_path, "line": line_num},
            "status": "OPEN",
        })

    return issues


# ---------------------------------------------------------------------------
# Detector 2: Raw claim dump  (G16-002, ERROR)
# ---------------------------------------------------------------------------

_PARAM_DEF_RE = re.compile(r"^\w+\s*\([^)]*\)\s*:")
_COND_RETURN_RE = re.compile(r"^[A-Z]_\w+\s+if\s+")


def _detect_raw_claim_dump(
    content: str,
    page_path: str,
) -> List[Dict[str, Any]]:
    """Detect bullet lists that look like raw API parameter definitions.

    When the LLM fails to synthesise claims into prose, the output often
    degenerates into a long bullet list of parameter signatures verbatim
    from the API surface.  This detector fires when > 60 % of bullets in a
    block match parameter-definition patterns and the list has more than 3
    items.

    Args:
        content: Full page content (markdown).
        page_path: File path for error reporting.

    Returns:
        List of ERROR issue dicts.
    """
    issues: List[Dict[str, Any]] = []

    body = _strip_frontmatter(content)
    lines = body.split("\n")

    bullet_block: List[str] = []
    block_start_line = 0

    def _check_block() -> None:
        """Evaluate the accumulated bullet block."""
        if len(bullet_block) <= 3:
            return

        param_like = sum(
            1
            for b in bullet_block
            if _PARAM_DEF_RE.search(b) or _COND_RETURN_RE.search(b)
        )

        ratio = param_like / len(bullet_block)
        if ratio > 0.6:
            issues.append({
                "issue_id": f"gate16_raw_claim_dump_{_slug(page_path)}_{block_start_line}",
                "gate": "gate_16_content_hygiene",
                "severity": "error",
                "message": (
                    f"Raw claim dump detected: {param_like}/{len(bullet_block)} "
                    f"bullets ({ratio:.0%}) match parameter-definition patterns"
                ),
                "error_code": "G16-002",
                "location": {"path": page_path, "line": block_start_line},
                "status": "OPEN",
            })

    # Count from original content line numbers (including frontmatter).
    fm_offset = _frontmatter_line_count(content)

    for idx, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith(("- ", "* ", "+ ")):
            if not bullet_block:
                block_start_line = fm_offset + idx + 1
            bullet_block.append(stripped[2:].strip())
        else:
            _check_block()
            bullet_block = []

    # Final block at end-of-file.
    _check_block()

    return issues


# ---------------------------------------------------------------------------
# Detector 3: Code-fence fragmentation  (G16-003, ERROR)
# ---------------------------------------------------------------------------

_FENCE_OPEN_RE = re.compile(r"^```\w*", re.MULTILINE)


def _detect_code_fence_fragmentation(
    content: str,
    page_path: str,
    page_role: str,
) -> List[Dict[str, Any]]:
    """Flag non-reference pages with an excessive number of code fences.

    Well-structured documentation consolidates examples.  More than 8 code
    fences on a single non-API-reference page usually indicates the LLM
    emitted many tiny, fragmented snippets instead of cohesive examples.

    ``api_reference`` pages are exempt because they legitimately contain
    many per-method examples.

    Args:
        content: Full page content (markdown).
        page_path: File path for error reporting.
        page_role: Page role string (e.g. ``"api_reference"``).

    Returns:
        List of ERROR issue dicts.
    """
    if page_role == "api_reference":
        return []

    # Role-aware thresholds: pages that legitimately contain many separate
    # code examples (one per section/step/issue) get a higher ceiling.
    # Two tiers: warn (soft) and error (hard).
    _HIGH_FENCE_ROLES = {
        "troubleshooting", "tutorial", "comprehensive_guide",
        "faq", "best_practices", "feature_showcase",
        "workflow_page",
    }
    if page_role in _HIGH_FENCE_ROLES:
        warn_threshold = 24
        error_threshold = 48
    else:
        warn_threshold = 8
        error_threshold = 16

    fence_count = len(_FENCE_OPEN_RE.findall(content))

    if fence_count > error_threshold:
        return [{
            "issue_id": f"gate16_code_fence_fragmentation_{_slug(page_path)}",
            "gate": "gate_16_content_hygiene",
            "severity": "error",
            "message": (
                f"Excessive code-fence fragmentation: {fence_count} fences "
                f"(threshold {error_threshold} for {page_role} pages)"
            ),
            "error_code": "G16-003",
            "location": {"path": page_path, "line": 1},
            "status": "OPEN",
        }]
    elif fence_count > warn_threshold:
        return [{
            "issue_id": f"gate16_code_fence_fragmentation_{_slug(page_path)}",
            "gate": "gate_16_content_hygiene",
            "severity": "warn",
            "message": (
                f"High code-fence count: {fence_count} fences "
                f"(warn threshold {warn_threshold} for {page_role} pages)"
            ),
            "error_code": "G16-003",
            "location": {"path": page_path, "line": 1},
            "status": "OPEN",
        }]

    return []


# ---------------------------------------------------------------------------
# Detector 4: Corrupted / repeated snippets  (G16-004, ERROR)
# ---------------------------------------------------------------------------

def _detect_corrupted_snippets(
    content: str,
    page_path: str,
) -> List[Dict[str, Any]]:
    """Detect lines repeated 3+ times consecutively inside code fences.

    LLM output corruption sometimes manifests as the same line being
    emitted many times in a row within a code block.  This detector
    scans each fenced code block for such repetitions.

    Args:
        content: Full page content (markdown).
        page_path: File path for error reporting.

    Returns:
        List of ERROR issue dicts, one per repeated block.
    """
    issues: List[Dict[str, Any]] = []
    lines = content.split("\n")

    in_code_block = False
    code_block_lines: List[str] = []
    code_block_start = 0

    for line_num_0, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            if in_code_block:
                # Closing fence -- analyse the block.
                _check_repeats(
                    code_block_lines,
                    code_block_start,
                    page_path,
                    issues,
                )
                in_code_block = False
                code_block_lines = []
            else:
                in_code_block = True
                code_block_start = line_num_0 + 1  # 1-based
                code_block_lines = []
        elif in_code_block:
            code_block_lines.append(line)

    return issues


def _check_repeats(
    code_lines: List[str],
    block_start: int,
    page_path: str,
    issues: List[Dict[str, Any]],
) -> None:
    """Check a single code block for consecutively repeated lines.

    Args:
        code_lines: Lines inside the code fence (excluding fence markers).
        block_start: 1-based line number of the opening fence.
        page_path: File path for error reporting.
        issues: Accumulator list; detected issues are appended in-place.
    """
    if len(code_lines) < 3:
        return

    run_start = 0
    run_count = 1

    for i in range(1, len(code_lines)):
        normalised_prev = code_lines[i - 1].strip()
        normalised_curr = code_lines[i].strip()

        # Skip blank lines -- consecutive blanks are not meaningful corruption.
        if not normalised_curr:
            run_start = i
            run_count = 1
            continue

        if normalised_curr == normalised_prev:
            run_count += 1
        else:
            if run_count >= 3:
                repeat_line = block_start + run_start + 1  # 1-based
                issues.append({
                    "issue_id": (
                        f"gate16_corrupted_snippet_{_slug(page_path)}"
                        f"_{repeat_line}"
                    ),
                    "gate": "gate_16_content_hygiene",
                    "severity": "error",
                    "message": (
                        f"Corrupted snippet: line repeated {run_count} times "
                        f"consecutively in code block"
                    ),
                    "error_code": "G16-004",
                    "location": {"path": page_path, "line": repeat_line},
                    "status": "OPEN",
                })
            run_start = i
            run_count = 1

    # Handle trailing run.
    if run_count >= 3:
        repeat_line = block_start + run_start + 1
        issues.append({
            "issue_id": (
                f"gate16_corrupted_snippet_{_slug(page_path)}"
                f"_{repeat_line}"
            ),
            "gate": "gate_16_content_hygiene",
            "severity": "error",
            "message": (
                f"Corrupted snippet: line repeated {run_count} times "
                f"consecutively in code block"
            ),
            "error_code": "G16-004",
            "location": {"path": page_path, "line": repeat_line},
            "status": "OPEN",
        })


# ---------------------------------------------------------------------------
# Detector 5: LLM scaffolding leaks  (G16-005, BLOCKER)
# ---------------------------------------------------------------------------

def _detect_llm_scaffolding(
    content: str,
    page_path: str,
) -> List[Dict[str, Any]]:
    """Detect LLM prompt scaffolding leaked into rendered content.

    The LLM sometimes echoes back its prompt context, producing visible
    ``## Product Context`` or ``## Instructions`` sections with raw JSON
    or pipeline directives.  These must never appear in publication output.
    """
    issues: List[Dict[str, Any]] = []
    body = _strip_frontmatter(content)
    offset = _frontmatter_line_count(content)

    for i, line in enumerate(body.split('\n'), start=1):
        stripped = line.strip()
        if re.match(r'^##\s+Product\s+Context\s*$', stripped):
            issues.append({
                "issue_id": f"gate16_scaffolding_product_context_{_slug(page_path)}",
                "gate": "gate_16_content_hygiene",
                "severity": "blocker",
                "message": (
                    "LLM scaffolding leak: '## Product Context' section "
                    "with raw pipeline metadata visible in output"
                ),
                "error_code": "G16-005",
                "location": {"path": page_path, "line": offset + i},
                "status": "OPEN",
            })
        elif re.match(r'^##\s+Instructions\s*$', stripped):
            issues.append({
                "issue_id": f"gate16_scaffolding_instructions_{_slug(page_path)}",
                "gate": "gate_16_content_hygiene",
                "severity": "blocker",
                "message": (
                    "LLM scaffolding leak: '## Instructions' section "
                    "with pipeline directives visible in output"
                ),
                "error_code": "G16-005",
                "location": {"path": page_path, "line": offset + i},
                "status": "OPEN",
            })
    return issues


# ---------------------------------------------------------------------------
# Detector 6: Unmatched code fences  (G16-006, WARN)
# ---------------------------------------------------------------------------

def _detect_unmatched_fences(
    content: str,
    page_path: str,
) -> List[Dict[str, Any]]:
    """Detect odd (unmatched) code fence counts that corrupt downstream parsing.

    Every opening ``` must have a corresponding closing ```. An odd total
    fence count means the last fence has no pair — content after the last
    fence is incorrectly treated as inside a code block by all gate parsers
    that use the toggle pattern.

    Args:
        content: Full page content (markdown).
        page_path: File path for error reporting.

    Returns:
        List of WARN issue dicts.
    """
    body = _strip_frontmatter(content)
    fence_count = len(re.findall(r"^```", body, re.MULTILINE))

    if fence_count % 2 != 0:
        return [{
            "issue_id": f"gate16_unmatched_fence_{_slug(page_path)}",
            "gate": "gate_16_content_hygiene",
            "severity": "warn",
            "message": (
                f"Unmatched code fence: {fence_count} fence markers found "
                f"(must be even). Content after the last fence is parsed "
                f"incorrectly by all downstream checks."
            ),
            "error_code": "G16-006",
            "location": {"path": page_path, "line": 1},
            "status": "OPEN",
        }]

    return []


# ---------------------------------------------------------------------------
# Main gate entry point
# ---------------------------------------------------------------------------

def run_gate_16(
    pages: List[Dict[str, Any]],
    product_facts: Dict[str, Any],
    **kwargs: Any,
) -> List[Dict[str, Any]]:
    """Execute Gate 16: Content Hygiene.

    Runs all four content-hygiene detectors across every page and returns
    a consolidated list of issues.

    Args:
        pages: List of page dicts.  Each dict must contain at least:
            - ``path`` (str): File path or output_path.
            - ``content`` (str): Full markdown content of the page.
            - ``page_role`` (str): Role of the page (e.g. ``"api_reference"``).
        product_facts: Product facts dictionary (currently unused but
            reserved for future detectors that need claim data).
        **kwargs: Reserved for forward-compatible extension.

    Returns:
        List of issue dicts.  Each issue has keys: ``issue_id``, ``gate``,
        ``severity``, ``message``, ``error_code``, ``location`` (dict with
        ``path`` and ``line``), and ``status``.
    """
    all_issues: List[Dict[str, Any]] = []

    for page in pages:
        page_path = page.get("path", "unknown")
        content = page.get("content", "")
        page_role = page.get("page_role", "")

        # Detector 1 -- visible claim markers (BLOCKER)
        all_issues.extend(
            _detect_visible_claim_markers(content, page_path)
        )

        # Detector 2 -- raw claim dump (ERROR)
        all_issues.extend(
            _detect_raw_claim_dump(content, page_path)
        )

        # Detector 3 -- code-fence fragmentation (ERROR)
        all_issues.extend(
            _detect_code_fence_fragmentation(content, page_path, page_role)
        )

        # Detector 4 -- corrupted snippets (ERROR)
        all_issues.extend(
            _detect_corrupted_snippets(content, page_path)
        )

        # Detector 5 -- LLM scaffolding leaks (BLOCKER)
        all_issues.extend(
            _detect_llm_scaffolding(content, page_path)
        )

        # Detector 6 -- unmatched code fences (WARN)
        all_issues.extend(
            _detect_unmatched_fences(content, page_path)
        )

    return all_issues


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _slug(path: str) -> str:
    """Derive a short slug from a file path for use in issue IDs."""
    # Take last component, strip extension, replace non-alphanum with _
    name = path.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    name = name.rsplit(".", 1)[0] if "." in name else name
    return re.sub(r"[^a-zA-Z0-9_-]", "_", name)


def _strip_frontmatter(content: str) -> str:
    """Remove YAML frontmatter (``---`` delimited) from content."""
    match = re.match(r"^---\s*\n.*?\n---\s*\n", content, re.DOTALL)
    if match:
        return content[match.end():]
    return content


def _frontmatter_line_count(content: str) -> int:
    """Return the number of lines occupied by frontmatter (including fences)."""
    match = re.match(r"^---\s*\n.*?\n---\s*\n", content, re.DOTALL)
    if match:
        return match.group().count("\n")
    return 0
