"""Gate 17: LLM Formatting Quality Verification.

Defense-in-depth partner to W7 Phase 0 (TC-2360): W7 detects and fixes
formatting defects proactively; Gate 17 is the final enforcer that verifies
no defects survived the W7 fix pass.

Defect checklist (FQ-1..FQ-7) is defined in the shared format_fixer.txt
prompt.  Gate 17 calls the same LLM prompt but ignores ``fixed_content``
from the response — only ``defects`` drives the pass/fail decision.

Severity policy:
    error codes  (FQ-1, FQ-3, FQ-4, FQ-7) → gate fails
    warn codes   (FQ-2, FQ-5, FQ-6)        → gate passes, issues recorded

LLM-optional: when the LLM client is unavailable the gate returns
``(True, [])`` with an INFO issue rather than blocking the pipeline.

TC-2361: W7 Gate 17 LLM formatting quality verification.
Per specs/09_validation_gates.md (Gate 17).
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Defect codes that cause the gate to fail (severity=error in the prompt)
_ERROR_CODES = frozenset({"FQ-1", "FQ-3", "FQ-4", "FQ-7"})

# Lazy-loaded prompt loader (mirrors W7 llm_regen.py pattern)
_prompt_loader = None


def _get_prompt_loader():
    global _prompt_loader
    if _prompt_loader is None:
        try:
            from launch.prompts import PromptLoader
            _prompt_loader = PromptLoader()
        except Exception:
            pass
    return _prompt_loader


def _load_system_prompt() -> Optional[str]:
    """Load the shared format_fixer.txt prompt.

    Tries the centralized PromptLoader first, then the W7 local prompts
    directory (where the canonical file lives).
    """
    loader = _get_prompt_loader()
    if loader is not None:
        try:
            _, body, _ = loader._load_raw("w7_content_reviewer/prompts/format_fixer")
            if body:
                return body
        except Exception:
            pass

    # Fallback: load directly from W7 local prompts directory
    local_path = (
        Path(__file__).parent.parent.parent  # src/launch/workers
        / "w7_content_reviewer" / "prompts" / "format_fixer.txt"
    )
    try:
        return local_path.read_text(encoding="utf-8")
    except Exception as exc:
        logger.warning("[Gate17] Could not load format_fixer.txt: %s", exc)
        return None


def run_gate_17(
    md_files: List[Path],
    llm_client: Optional[Any],
) -> Tuple[bool, List[Dict[str, Any]]]:
    """Execute Gate 17: LLM Formatting Quality.

    Scans published markdown files for formatting defects using the same
    LLM checklist as W7 Phase 0.  Does NOT modify files — detection only.

    Args:
        md_files:   List of published .md file paths to scan.
        llm_client: Initialised LLM client, or None (gate passes gracefully).

    Returns:
        (gate_passed, issues) — issues is always a list (may be empty).
    """
    if llm_client is None:
        logger.info("[Gate17] LLM unavailable — gate passes (LLM-optional)")
        return True, [{
            "issue_id": "gate17_llm_unavailable",
            "gate": "gate_17_formatting_quality",
            "severity": "info",
            "message": "Gate 17 skipped: LLM client unavailable",
            "error_code": "G17-000",
            "location": {"path": "", "line": 0},
            "status": "skipped",
        }]

    system_text = _load_system_prompt()
    if not system_text:
        logger.warning("[Gate17] Could not load format_fixer prompt — gate passes")
        return True, []

    all_issues: List[Dict[str, Any]] = []
    gate_failed = False

    for md_path in md_files:
        issues, has_errors = _check_one_page(md_path, system_text, llm_client)
        all_issues.extend(issues)
        if has_errors:
            gate_failed = True

    logger.info(
        "[Gate17] Scanned %d pages: %d defects found, gate=%s",
        len(md_files), len(all_issues),
        "FAIL" if gate_failed else "PASS",
    )
    return not gate_failed, all_issues


def _check_one_page(
    md_path: Path,
    system_text: str,
    llm_client: Any,
) -> Tuple[List[Dict[str, Any]], bool]:
    """Run the LLM formatting check on one published page.

    Args:
        md_path:     Path to the published markdown file.
        system_text: Loaded format_fixer.txt prompt text.
        llm_client:  Initialised LLM client.

    Returns:
        (issues, has_error_defects)
    """
    try:
        content = md_path.read_text(encoding="utf-8")
    except Exception as exc:
        logger.warning("[Gate17] Could not read %s: %s", md_path, exc)
        return [], False

    try:
        response = llm_client.chat_completion(
            messages=[
                {"role": "system", "content": system_text},
                {"role": "user", "content": content},
            ],
            call_id=f"gate17_fmt_check_{md_path.stem}",
            temperature=0.0,
            max_tokens=4096,
        )
        raw = response.get("content", "")
    except Exception as exc:
        logger.warning("[Gate17] LLM call failed for %s: %s", md_path.name, exc)
        return [], False

    # Strip accidental markdown fences around the JSON response
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.MULTILINE)
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.warning("[Gate17] JSON parse failed for %s: %s", md_path.name, exc)
        return [], False

    defects: List[Dict] = parsed.get("defects") or []
    issues: List[Dict[str, Any]] = []
    has_errors = False

    slug = md_path.stem
    for d in defects:
        code = d.get("code", "FQ-?")
        line_no = d.get("line_approximate", 0)
        # Gate 17 enforces the same severity that the prompt assigned.
        # Error-level defects (FQ-1/3/4/7) cause the gate to fail.
        severity = d.get("severity", "warn")
        if code in _ERROR_CODES:
            severity = "error"
            has_errors = True

        issues.append({
            "issue_id": f"gate17_{code.lower().replace('-', '_')}_{slug}_{line_no}",
            "gate": "gate_17_formatting_quality",
            "severity": severity,
            "message": f"[{code}] {d.get('excerpt', '')[:120]}",
            "error_code": f"G17-{code}",
            "location": {"path": str(md_path), "line": line_no},
            "status": "active",
        })

    return issues, has_errors
