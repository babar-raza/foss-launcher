"""LLM-based dimension checkers with offline fallback (TC-2535).

Three checkers that use LLM calls for semantic quality assessment:
    RD-01: Hallucination detection
    RD-09: Readability assessment
    RD-11: Code example quality

Each checker:
- Constructs a focused prompt (< 2000 tokens input)
- Requests JSON schema output from LLM
- Validates response against expected schema
- Retries up to 2 times on schema parse failure
- Falls back to score=5 (neutral) if LLM is unavailable or all retries fail
- Returns DimensionResult with score, issues, and evidence

Offline fallback: when no LLM client is available, all three checkers
return score=5 with a note "LLM review not available".
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

from ..rubric import DimensionResult, Issue, SCORE_ACCEPTABLE

logger = logging.getLogger(__name__)

# Maximum content length sent to LLM (chars)
_MAX_CONTENT_LEN = 3000

# Maximum retries on LLM parse failure
_MAX_RETRIES = 2

# Neutral offline fallback score
_FALLBACK_SCORE = SCORE_ACCEPTABLE  # 5


def _truncate(text: str, max_len: int = _MAX_CONTENT_LEN) -> str:
    """Truncate text to max_len with marker."""
    if len(text) <= max_len:
        return text
    return text[:max_len] + "\n... [truncated]"


def _offline_result(dimension_id: str, name: str) -> DimensionResult:
    """Return a neutral offline fallback result."""
    return DimensionResult(
        dimension_id=dimension_id,
        name=name,
        score=_FALLBACK_SCORE,
        issues=[Issue(
            severity="info",
            message="LLM review not available -- using neutral fallback score",
        )],
        evidence="LLM review not available",
    )


def _call_llm(
    llm_client: Any,
    prompt: str,
    max_retries: int = _MAX_RETRIES,
) -> Optional[Dict[str, Any]]:
    """Call LLM and parse JSON response with retry logic.

    Args:
        llm_client: Object with a ``chat(prompt) -> str`` method.
        prompt: The prompt to send.
        max_retries: Maximum retries on parse failure.

    Returns:
        Parsed JSON dict, or None if all retries exhausted.
    """
    last_error = ""
    for attempt in range(1 + max_retries):
        try:
            if attempt > 0:
                # Add error feedback for retries
                retry_prompt = (
                    f"{prompt}\n\n"
                    f"IMPORTANT: Your previous response was not valid JSON. "
                    f"Error: {last_error}. Please respond with valid JSON only."
                )
            else:
                retry_prompt = prompt

            response = llm_client.chat(retry_prompt)
            # Try to extract JSON from response (may be wrapped in markdown code block)
            json_str = response.strip()
            if json_str.startswith("```"):
                # Strip markdown code fence
                lines = json_str.splitlines()
                json_str = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

            return json.loads(json_str)

        except json.JSONDecodeError as e:
            last_error = str(e)
            logger.debug("LLM JSON parse failure (attempt %d/%d): %s", attempt + 1, max_retries + 1, e)
        except Exception as e:
            logger.debug("LLM call failure (attempt %d/%d): %s", attempt + 1, max_retries + 1, e)
            last_error = str(e)

    return None


# ---------------------------------------------------------------------------
# RD-01: Hallucination
# ---------------------------------------------------------------------------

def check_hallucination(
    content: str,
    product_facts: Optional[Dict[str, Any]] = None,
    claims: Optional[List[Dict[str, Any]]] = None,
    llm_client: Any = None,
) -> DimensionResult:
    """RD-01: Detect claims not grounded in evidence.

    Args:
        content: Page markdown content.
        product_facts: Product facts JSON data.
        claims: List of claim dicts with at least 'claim_id' and 'text'.
        llm_client: Optional LLM client. If None, returns offline fallback.

    Returns:
        DimensionResult with hallucination assessment.
    """
    if llm_client is None:
        return _offline_result("RD-01", "Hallucination")

    # Build evidence summary from claims
    evidence_lines: List[str] = []
    if claims:
        for c in claims[:20]:  # Limit to 20 claims
            evidence_lines.append(f"- {c.get('claim_id', '?')}: {c.get('text', '')}")

    evidence_text = "\n".join(evidence_lines) if evidence_lines else "No claims provided."
    truncated_content = _truncate(content)

    prompt = (
        "You are a technical documentation reviewer. Given the following evidence "
        "claims and generated content, identify any statements in the content that "
        "are NOT grounded in the evidence.\n\n"
        f"## Evidence Claims\n{evidence_text}\n\n"
        f"## Generated Content\n{truncated_content}\n\n"
        "Respond with JSON only:\n"
        '{"score": <0-10>, "hallucinated_claims": [{"claim": "<text>", "reason": "<why>"}], '
        '"grounded_claim_count": <int>, "total_claim_count": <int>}'
    )

    result = _call_llm(llm_client, prompt)
    if result is None:
        return _offline_result("RD-01", "Hallucination")

    try:
        score = max(0, min(10, int(result.get("score", _FALLBACK_SCORE))))
        hallucinated = result.get("hallucinated_claims", [])
        issues = [
            Issue(
                severity="error",
                message=f"Hallucinated: {h.get('claim', '?')} -- {h.get('reason', '')}",
            )
            for h in hallucinated
        ]
        grounded = result.get("grounded_claim_count", 0)
        total = result.get("total_claim_count", 0)
        return DimensionResult(
            dimension_id="RD-01",
            name="Hallucination",
            score=score,
            issues=issues,
            evidence=f"{grounded}/{total} claims grounded in evidence.",
        )
    except (TypeError, ValueError):
        return _offline_result("RD-01", "Hallucination")


# ---------------------------------------------------------------------------
# RD-09: Readability
# ---------------------------------------------------------------------------

def check_readability(
    content: str,
    llm_client: Any = None,
) -> DimensionResult:
    """RD-09: Coherent flow, no raw claim dumps.

    Args:
        content: Page markdown content.
        llm_client: Optional LLM client. If None, returns offline fallback.

    Returns:
        DimensionResult with readability assessment.
    """
    if llm_client is None:
        return _offline_result("RD-09", "Readability")

    truncated_content = _truncate(content)
    prompt = (
        "You are a technical documentation reviewer. Evaluate the readability "
        "of this technical documentation. Check for:\n"
        "1. Coherent narrative flow between sections\n"
        "2. No raw data/claim dumps (bulleted lists of facts without context)\n"
        "3. Proper transitions between paragraphs\n"
        "4. Consistent tone and voice\n\n"
        f"## Content\n{truncated_content}\n\n"
        "Respond with JSON only:\n"
        '{"score": <0-10>, "issues": [{"type": "<issue_type>", "location": "<where>", '
        '"reason": "<why>"}], "flow_quality": "<poor|fair|good|excellent>", '
        '"sentence_variety": "<low|moderate|high>"}'
    )

    result = _call_llm(llm_client, prompt)
    if result is None:
        return _offline_result("RD-09", "Readability")

    try:
        score = max(0, min(10, int(result.get("score", _FALLBACK_SCORE))))
        raw_issues = result.get("issues", [])
        issues = [
            Issue(
                severity="warning",
                message=f"{i.get('type', 'readability')}: {i.get('reason', '')}",
                location=i.get("location", ""),
            )
            for i in raw_issues
        ]
        flow = result.get("flow_quality", "unknown")
        return DimensionResult(
            dimension_id="RD-09",
            name="Readability",
            score=score,
            issues=issues,
            evidence=f"Flow quality: {flow}.",
        )
    except (TypeError, ValueError):
        return _offline_result("RD-09", "Readability")


# ---------------------------------------------------------------------------
# RD-11: Code example quality
# ---------------------------------------------------------------------------

_CODE_BLOCK_RE = re.compile(r"```(\w*)\n(.*?)```", re.DOTALL)


def check_code_example_quality(
    content: str,
    product_facts: Optional[Dict[str, Any]] = None,
    llm_client: Any = None,
) -> DimensionResult:
    """RD-11: Code examples have correct imports, are runnable, demonstrate feature.

    Args:
        content: Page markdown content.
        product_facts: Product facts JSON data (for import verification).
        llm_client: Optional LLM client. If None, returns offline fallback.

    Returns:
        DimensionResult with code example quality assessment.
    """
    # Extract code blocks
    blocks = _CODE_BLOCK_RE.findall(content)
    if not blocks:
        return DimensionResult(
            dimension_id="RD-11",
            name="Code example quality",
            score=5,
            issues=[Issue(
                severity="info",
                message="No code examples found in page",
            )],
            evidence="No code blocks to evaluate.",
        )

    if llm_client is None:
        return _offline_result("RD-11", "Code example quality")

    # Build code summary for LLM
    code_summary = []
    for i, (lang, code) in enumerate(blocks[:5]):  # Limit to 5 blocks
        code_summary.append(f"### Example {i+1} ({lang or 'unknown'}):\n```{lang}\n{code.strip()}\n```")

    code_text = "\n\n".join(code_summary)
    package_name = ""
    if product_facts:
        package_name = product_facts.get("package_name", "")

    prompt = (
        "You are a technical documentation reviewer. Evaluate these code examples "
        "for correctness and quality:\n"
        "1. Do they have proper import statements?\n"
        "2. Are they syntactically correct and runnable?\n"
        "3. Do they demonstrate the feature they claim to?\n"
        f"{f'4. The package name is: {package_name}' if package_name else ''}\n\n"
        f"## Code Examples\n{code_text}\n\n"
        "Respond with JSON only:\n"
        '{"score": <0-10>, "examples_found": <int>, "issues": ['
        '{"example_index": <int>, "problem": "<desc>", "severity": "<error|warning|info>"}], '
        '"has_correct_imports": <bool>, "demonstrates_feature": <bool>}'
    )

    result = _call_llm(llm_client, prompt)
    if result is None:
        return _offline_result("RD-11", "Code example quality")

    try:
        score = max(0, min(10, int(result.get("score", _FALLBACK_SCORE))))
        raw_issues = result.get("issues", [])
        issues = [
            Issue(
                severity=i.get("severity", "warning"),
                message=f"Example {i.get('example_index', '?')}: {i.get('problem', '')}",
            )
            for i in raw_issues
        ]
        has_imports = result.get("has_correct_imports", True)
        demos_feature = result.get("demonstrates_feature", True)
        return DimensionResult(
            dimension_id="RD-11",
            name="Code example quality",
            score=score,
            issues=issues,
            evidence=f"{len(blocks)} code block(s); imports={'yes' if has_imports else 'no'}, demonstrates={'yes' if demos_feature else 'no'}.",
        )
    except (TypeError, ValueError):
        return _offline_result("RD-11", "Code example quality")
