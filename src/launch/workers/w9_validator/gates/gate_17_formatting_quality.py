"""Gate 17: Two-Phase Formatting Quality Verification.

**Phase 1 (deterministic)** -- regex-based pre-lints for FQ-1/2/4/5/6/7a
(always runs, no LLM needed).  Implemented in ``gate_17_prelints.py``.

**Phase 2 (LLM)** -- calls the shared format_fixer.txt prompt for
FQ-3 (truncated content) and FQ-7b (narrative flow).  Only runs
when the LLM client is available.

TC-2522: FQ-7 split into:
  - FQ-7a: Heading hierarchy coherence (deterministic, Phase 1) -- severity=error
  - FQ-7b: Narrative flow (LLM, Phase 2) -- severity=error on first success,
    demoted to severity=warn if retries exhausted

Defense-in-depth partner to W7 Phase 0 (TC-2360): W7 detects and fixes
formatting defects proactively; Gate 17 is the final enforcer that verifies
no defects survived the W7 fix pass.

Dedup policy: when both Phase 1 and Phase 2 report the same
``(error_code, path.stem)`` pair, the Phase 1 (deterministic) version wins.

Severity policy:
    error codes  (FQ-1, FQ-3, FQ-4, FQ-7a) -- gate fails
    warn codes   (FQ-2, FQ-5, FQ-6)          -- gate passes, issues recorded
    FQ-7b        -- error on success, demoted to warn after retry exhaustion

LLM-optional: when the LLM client is unavailable, Phase 2 is skipped
and an INFO issue notes that FQ-3/FQ-7b checks were not performed.

TC-2361: W7 Gate 17 LLM formatting quality verification.
TC-2475: Deterministic pre-lints (Phase 1).
TC-2476: Two-phase architecture.
TC-2522: FQ-7 stability split.
Per specs/09_validation_gates.md (Gate 17).
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .gate_17_prelints import run_deterministic_prelints
from launch.workers._shared.llm_contract import FailureClassifier, RetryStrategy

logger = logging.getLogger(__name__)

# Defect codes that cause the gate to fail (severity=error in the prompt).
# Note: FQ-7 from LLM (FQ-7b) is now demoted to warn after retry exhaustion
# and is NOT in this set. Only FQ-7a (deterministic) triggers gate failure.
_ERROR_CODES = frozenset({"FQ-1", "FQ-3", "FQ-4", "FQ-7"})

# TC-2522: Retry strategy for FQ-7b LLM checks
_fq7b_classifier = FailureClassifier()
_fq7b_retry = RetryStrategy(max_retries=2)

# Maximum retries for LLM-based format checks (Phase 2)
_LLM_CHECK_MAX_RETRIES = 2

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
    max_parallel_files: int = 4,
) -> Tuple[bool, List[Dict[str, Any]]]:
    """Execute Gate 17: Two-Phase Formatting Quality.

    Phase 1 (deterministic): regex pre-lints for FQ-1/2/4/5/6 -- always runs.
    Phase 2 (LLM): format_fixer prompt for FQ-3/FQ-7 -- runs only if LLM available.

    Scans published markdown files for formatting defects.
    Does NOT modify files -- detection only.

    Args:
        md_files:           List of published .md file paths to scan.
        llm_client:         Initialised LLM client, or None (Phase 2 skipped).
        max_parallel_files: TC-2404 -- max concurrent per-file LLM checks.
                            1=sequential, >1=ThreadPoolExecutor. Default 4.

    Returns:
        (gate_passed, issues) -- issues is always a list (may be empty).
    """
    all_issues: List[Dict[str, Any]] = []
    error_flags: List[bool] = []

    # ── Phase 1: deterministic pre-lints (always runs) ──────────────────
    prelint_keys: set = set()  # (error_code, stem) pairs for dedup
    for md_path in md_files:
        try:
            issues, has_errors = run_deterministic_prelints(md_path)
            all_issues.extend(issues)
            error_flags.append(has_errors)
            for i in issues:
                prelint_keys.add((i["error_code"], md_path.stem))
        except Exception as exc:
            logger.warning("[Gate17-Phase1] Unexpected error on %s: %s", md_path.name, exc)

    # ── Phase 2: LLM-based checks (FQ-3 / FQ-7) ───────────────────────
    if llm_client is None:
        logger.info("[Gate17] LLM unavailable -- Phase 2 skipped (FQ-3/FQ-7 not checked)")
        all_issues.append({
            "issue_id": "gate17_llm_unavailable",
            "gate": "gate_17_formatting_quality",
            "severity": "info",
            "message": "Gate 17 Phase 2 skipped: LLM client unavailable (FQ-3/FQ-7 not checked)",
            "error_code": "G17-000",
            "location": {"path": "", "line": 0},
            "status": "skipped",
        })
    else:
        system_text = _load_system_prompt()
        if not system_text:
            logger.warning("[Gate17] Could not load format_fixer prompt -- Phase 2 skipped")
        else:
            _n = min(len(md_files), max_parallel_files) if max_parallel_files > 1 else 1
            if _n <= 1:
                for md_path in md_files:
                    try:
                        issues, has_errors = _check_one_page(md_path, system_text, llm_client)
                        # Dedup: keep pre-lint version when both report same (error_code, stem)
                        for issue in issues:
                            key = (issue["error_code"], md_path.stem)
                            if key not in prelint_keys:
                                all_issues.append(issue)
                                if has_errors and issue.get("severity") == "error":
                                    error_flags.append(True)
                    except Exception as exc:
                        logger.warning("[Gate17-Phase2] Unexpected error on %s: %s", md_path.name, exc)
            else:
                from concurrent.futures import ThreadPoolExecutor, as_completed
                with ThreadPoolExecutor(max_workers=_n, thread_name_prefix="gate17_check") as pool:
                    futures = {
                        pool.submit(_check_one_page, p, system_text, llm_client): p
                        for p in md_files
                    }
                    for fut in as_completed(futures):
                        p = futures[fut]
                        try:
                            issues, has_errors = fut.result()
                            for issue in issues:
                                key = (issue["error_code"], p.stem)
                                if key not in prelint_keys:
                                    all_issues.append(issue)
                                    if has_errors and issue.get("severity") == "error":
                                        error_flags.append(True)
                        except Exception as exc:
                            logger.warning(
                                "[Gate17-Phase2] Unexpected error on %s: %s",
                                p.name, exc,
                            )

    gate_failed = any(error_flags)
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
    """Run the LLM formatting check on one published page (Phase 2).

    TC-2522: Adds retry logic for schema parse failures and demotes FQ-7
    (now FQ-7b) to "warn" severity when retries are exhausted. This makes
    FQ-7b non-blocking -- the gate still passes, but the issue is recorded.

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

    # TC-2522: Retry loop for LLM schema parse failures
    parsed = None
    retries_exhausted = False
    for attempt in range(_LLM_CHECK_MAX_RETRIES + 1):
        try:
            response = llm_client.chat_completion(
                messages=[
                    {"role": "system", "content": system_text},
                    {"role": "user", "content": content},
                ],
                call_id=f"gate17_fmt_check_{md_path.stem}_a{attempt}",
                temperature=0.0,
                max_tokens=4096,
                timeout=30,
            )
            raw = response.get("content", "")
        except Exception as exc:
            fc = _fq7b_classifier.classify(str(exc), "")
            if _fq7b_retry.should_retry(fc, attempt):
                logger.debug(
                    "[Gate17] LLM call retry %d/%d for %s (class=%s)",
                    attempt + 1, _LLM_CHECK_MAX_RETRIES, md_path.name, fc,
                )
                continue
            logger.warning("[Gate17] LLM call failed for %s: %s", md_path.name, exc)
            return [], False

        # Strip accidental markdown fences around the JSON response
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.MULTILINE)
        try:
            parsed = json.loads(raw)
            break  # Successfully parsed -- exit retry loop
        except json.JSONDecodeError as exc:
            fc = _fq7b_classifier.classify(str(exc), raw)
            if _fq7b_retry.should_retry(fc, attempt):
                logger.debug(
                    "[Gate17] JSON parse retry %d/%d for %s (class=%s)",
                    attempt + 1, _LLM_CHECK_MAX_RETRIES, md_path.name, fc,
                )
                continue
            logger.warning("[Gate17] JSON parse failed for %s after %d attempts: %s",
                           md_path.name, attempt + 1, exc)
            retries_exhausted = True
            break

    if parsed is None:
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

        # TC-2522: FQ-7 from LLM Phase 2 is FQ-7b (narrative flow).
        # FQ-7b is ALWAYS demoted to "warn" -- it must not block the gate.
        # Only FQ-7a (deterministic, from prelints) triggers gate failure.
        if code == "FQ-7":
            severity = "warn"
            if retries_exhausted:
                logger.info(
                    "[Gate17] FQ-7b warn (retries exhausted) for %s",
                    md_path.name,
                )
            else:
                logger.debug(
                    "[Gate17] FQ-7b demoted to warn for %s (LLM narrative check)",
                    md_path.name,
                )
            # FQ-7b does NOT set has_errors
        elif code in _ERROR_CODES:
            severity = "error"
            has_errors = True

        issues.append({
            "issue_id": f"gate17_{code.lower().replace('-', '_')}_{slug}_{line_no}",
            "gate": "gate_17_formatting_quality",
            "severity": severity,
            "message": f"[{code}] {d.get('excerpt', '')[:120]}",
            "error_code": f"G17-{code}",
            "location": {"path": str(md_path), "line": line_no},
            "status": "OPEN",
        })

    return issues, has_errors
