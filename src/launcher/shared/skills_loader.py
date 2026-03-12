"""Skills document loader — TC-3856.

Loads the ``skills.md`` quality-standards document and extracts named
sections for injection into generation and evaluation prompts.

Design principles:
- Zero exceptions: always returns ``str``, empty when unavailable.
- Brace-safe: escapes ``{`` / ``}`` so the returned block can be used
  directly inside ``str.format()`` prompt templates.
- Stateless: callers own caching (workers load once at startup).
- Environment-agnostic: pure filesystem I/O, works in CLI / library /
  CI/CD contexts with no VS Code or agent dependencies.
- Token-safe: blocks are truncated at ``_MAX_BLOCK_CHARS`` (≈500 tokens)
  at the last newline boundary to prevent context-window overflow.

Control surface:
    Skills are enabled/disabled via ``RunConfig.skills`` (in run_config.yaml),
    NOT via pipeline.yaml.  The pipeline.yaml file does not parse into RunConfig.
    Example run_config.yaml entry::

        skills:
          enabled: true
          path: "skills.md"

    To disable skills for a specific run, set ``skills.enabled: false``.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

_GENERATION_HEADER = "## GENERATION STANDARDS"
_EVALUATION_HEADER = "## EVALUATION CRITERIA"

# Maximum characters for a skills block injected into a prompt.
# At ~4 chars/token this is ≈500 tokens — enough for meaningful guidance
# without risking context-window overflow on long prompts.
_MAX_BLOCK_CHARS = 2000


def load_generation_block(skills_path: Path, page_role: str = "") -> str:
    """Return the GENERATION STANDARDS section from skills.md.

    The returned string is safe for use in ``str.format()`` prompt templates —
    all literal braces are escaped.  Returns ``""`` when the file is missing,
    skills are empty, or any error occurs.

    Parameters
    ----------
    skills_path:
        Path to the skills document (typically ``Path("skills.md")``).
    page_role:
        The page role being generated.  Currently unused but reserved for
        future per-role section extraction.
    """
    text = _read_skills(skills_path)
    if not text:
        return ""
    block = _extract_section(text, _GENERATION_HEADER)
    if not block:
        logger.debug("[skills] GENERATION STANDARDS section not found in %s", skills_path)
        return ""
    return _format_for_prompt(block, label="QUALITY STANDARDS FOR THIS SECTION")


def load_evaluation_block(skills_path: Path, page_role: str = "") -> str:
    """Return the EVALUATION CRITERIA section from skills.md.

    The returned string is safe for use in ``str.format()`` prompt templates.
    Returns ``""`` when the file is missing or the section is absent.

    Parameters
    ----------
    skills_path:
        Path to the skills document.
    page_role:
        The page role being evaluated.  Reserved for future per-role extraction.
    """
    text = _read_skills(skills_path)
    if not text:
        return ""
    block = _extract_section(text, _EVALUATION_HEADER)
    if not block:
        logger.debug("[skills] EVALUATION CRITERIA section not found in %s", skills_path)
        return ""
    return _format_for_prompt(block, label="DOMAIN-SPECIFIC EVALUATION CRITERIA")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _read_skills(skills_path: Path) -> str:
    """Read skills.md, returning empty string on any error."""
    try:
        p = Path(skills_path)
        if not p.exists():
            logger.debug("[skills] File not found: %s — skills inactive", skills_path)
            return ""
        return p.read_text(encoding="utf-8")
    except Exception as exc:
        logger.warning("[skills] Could not read %s: %s", skills_path, exc)
        return ""


def _extract_section(text: str, header: str) -> str:
    """Extract the content of a named ## section from the document.

    Captures everything from the header line up to (but not including) the
    next ## section or end of file.  Returns empty string when not found.
    """
    # Escape the header for use in a regex
    escaped = re.escape(header)
    pattern = rf"{escaped}\s*\n(.*?)(?=\n##\s|\Z)"
    match = re.search(pattern, text, re.DOTALL)
    if not match:
        return ""
    return match.group(1).strip()


def _format_for_prompt(content: str, label: str) -> str:
    """Wrap content in a labelled block and escape braces for str.format().

    Truncates at the last newline boundary before ``_MAX_BLOCK_CHARS`` when
    content exceeds the budget, logging a WARNING with the original length.
    """
    safe = content.replace("{", "{{").replace("}", "}}")
    if len(safe) > _MAX_BLOCK_CHARS:
        original_len = len(safe)
        truncated = safe[:_MAX_BLOCK_CHARS].rsplit("\n", 1)[0]
        safe = truncated + "\n... [skills block truncated for token budget]"
        logger.warning(
            "[skills] Block truncated from %d to ~%d chars for prompt token budget",
            original_len, len(safe),
        )
    return (
        f"\n## {label}\n"
        f"{safe}\n"
        f"## END {label}\n"
    )
