"""LLM-based formatting review and fix for W7 Phase 0.

Detects and fixes 7 formatting defect types (FQ-1 through FQ-7) in a
single LLM call per page. Runs as Phase 0 in the W7 review loop,
before the existing 36-check cycle, so checks run on already-improved content.

Defect codes:
    FQ-1 NAKED_CODE:     Code lines outside fences              → error
    FQ-2 FAQ_CONCAT:     Q&A concatenated on same line          → warn
    FQ-3 TRUNCATED:      Bullet ending mid-sentence             → error
    FQ-4 DOUBLE_HEADING: H2 heading + paragraph on same line    → error
    FQ-5 KEYWORD_COLON:  Colon in YAML keywords list item       → warn
    FQ-6 CLAIM_COMMENT:  <!-- claim: UUID --> visible in body   → warn
    FQ-7 INCOHERENT:     Structurally broken sentence/bullet    → error

TC-2360: W7 Phase 0 LLM formatting review and fix.
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Defect code → check name prefix (for issue routing in scoring)
_DEFECT_CHECK = {
    "FQ-1": "formatting_quality.naked_code",
    "FQ-2": "formatting_quality.faq_concat",
    "FQ-3": "formatting_quality.truncated_sentence",
    "FQ-4": "formatting_quality.double_heading",
    "FQ-5": "formatting_quality.keyword_colon",
    "FQ-6": "formatting_quality.claim_comment",
    "FQ-7": "formatting_quality.incoherent_sentence",
}

# Lazy-loaded prompt loader for centralized prompts (mirrors llm_regen.py pattern)
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
    """Load format_fixer.txt.

    Tries the centralized PromptLoader first (consistent with other W7 modules),
    then falls back to the local prompts directory (same pattern as W5 generators).
    """
    loader = _get_prompt_loader()
    if loader is not None:
        try:
            _, body, _ = loader._load_raw("w7_content_reviewer/prompts/format_fixer")
            if body:
                return body
        except Exception:
            pass

    # Fallback: load from local prompts directory (always exists)
    local_path = Path(__file__).parent.parent / "prompts" / "format_fixer.txt"
    try:
        return local_path.read_text(encoding="utf-8")
    except Exception as exc:
        logger.warning("[W7 FmtFix] Could not load format_fixer.txt: %s", exc)
        return None


def run_llm_format_fix(
    drafts_dir: Path,
    llm_client: Optional[Any],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Run LLM formatting review+fix on all draft pages (Phase 0).

    Each page gets a single LLM call. The LLM simultaneously detects and
    fixes formatting defects, returning both a defect list and the corrected
    page content. If the LLM is unavailable the function returns immediately
    with empty lists — no exception is raised and no pages are modified.

    Args:
        drafts_dir: Directory containing draft .md files.
        llm_client:  Initialised LLM client, or None for graceful skip.

    Returns:
        Tuple of (issues, fix_results):
          - issues: List of issue dicts in standard W7 format.
          - fix_results: List of fix-result dicts (one per page fixed).
    """
    if llm_client is None:
        logger.info("[W7 FmtFix] llm_client unavailable — skipping Phase 0 format fix")
        return [], []

    system_text = _load_system_prompt()
    if not system_text:
        return [], []

    all_issues: List[Dict[str, Any]] = []
    fix_results: List[Dict[str, Any]] = []

    draft_files = sorted(drafts_dir.rglob("*.md"))
    for draft_path in draft_files:
        issues, fix = _process_one_page(draft_path, system_text, llm_client)
        all_issues.extend(issues)
        if fix is not None:
            fix_results.append(fix)

    fixed_count = sum(1 for f in fix_results if f.get("success"))
    logger.info(
        "[W7 FmtFix] Processed %d pages: %d defects, %d pages fixed",
        len(draft_files), len(all_issues), fixed_count,
    )
    return all_issues, fix_results


def _process_one_page(
    draft_path: Path,
    system_text: str,
    llm_client: Any,
) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """Run format detect+fix on one draft page.

    Args:
        draft_path:  Path to the markdown file.
        system_text: Loaded format_fixer.txt prompt text.
        llm_client:  Initialised LLM client.

    Returns:
        (issues, fix_result) — fix_result is None when nothing was attempted.
    """
    try:
        original = draft_path.read_text(encoding="utf-8")
    except Exception as exc:
        logger.warning("[W7 FmtFix] Could not read %s: %s", draft_path, exc)
        return [], None

    try:
        response = llm_client.chat_completion(
            messages=[
                {"role": "system", "content": system_text},
                {"role": "user", "content": original},
            ],
            call_id=f"w7_format_fix_{draft_path.stem}",
            temperature=0.0,
            max_tokens=8192,
        )
        raw = response.get("content", "")
    except Exception as exc:
        logger.warning("[W7 FmtFix] LLM call failed for %s: %s", draft_path.name, exc)
        return [], None

    # Strip accidental markdown fences around the JSON (common LLM habit)
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.MULTILINE)
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.warning("[W7 FmtFix] JSON parse failed for %s: %s", draft_path.name, exc)
        return [], None

    defects: List[Dict] = parsed.get("defects") or []
    fixed_content: Optional[str] = parsed.get("fixed_content")

    # Write fixed content to disk when the LLM produced a non-trivial change
    fix_result: Optional[Dict[str, Any]] = None
    if fixed_content and fixed_content.strip() != original.strip():
        try:
            draft_path.write_text(fixed_content, encoding="utf-8")
            fix_result = {
                "issue_id": f"fmt_fix_{draft_path.stem}",
                "fix_type": "llm_format_fix",
                "files_changed": [str(draft_path)],
                "success": True,
            }
            logger.info("[W7 FmtFix] Fixed %d defect(s) in %s", len(defects), draft_path.name)
        except Exception as exc:
            fix_result = {
                "issue_id": f"fmt_fix_{draft_path.stem}",
                "fix_type": "llm_format_fix",
                "files_changed": [],
                "success": False,
                "error": str(exc),
            }

    # Convert defects to standard W7 issue dicts
    slug = draft_path.stem
    was_fixed = bool(fix_result and fix_result.get("success"))
    issues: List[Dict[str, Any]] = []
    for d in defects:
        code = d.get("code", "FQ-?")
        line_no = d.get("line_approximate", 0)
        issues.append({
            "issue_id": (
                f"formatting_quality_{code.lower().replace('-', '_')}_{slug}_{line_no}"
            ),
            "check": _DEFECT_CHECK.get(code, f"formatting_quality.{code.lower()}"),
            "severity": d.get("severity", "warn"),
            "message": f"[{code}] {d.get('excerpt', '')[:120]}",
            "location": {"path": str(draft_path), "line": line_no},
            "auto_fixable": True,
            "suggested_fix": (
                "Applied by LLM format fixer" if was_fixed
                else "LLM fix not applied"
            ),
        })

    return issues, fix_result
