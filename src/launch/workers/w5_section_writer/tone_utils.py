"""Tone prompt enhancement for W5 SectionWriter.

Adapted from content-generator src/utils/tone_utils.py:37.
Reference: build_section_prompt_enhancement().

TC-2391: Declarative tone control system — injects editorial voice and
structural constraints into LLM prompts based on page role.
"""
from pathlib import Path
from typing import Optional

try:
    import yaml
    _YAML_AVAILABLE = True
except ImportError:  # pragma: no cover
    _YAML_AVAILABLE = False

STRUCTURE_DIRECTIVES = {
    "step_by_step": "Use numbered steps. Each step must have exactly one action.",
    "prose_with_subheadings": "Use H3 subheadings every 2-3 paragraphs. Prose only, no bullets.",
    "problem_solution_pairs": (
        "For each problem: H3 heading -> symptom description -> root cause -> solution steps."
    ),
    "qa_pairs": "Format as Q: / A: pairs. Answer must begin with a direct sentence.",
    "segmented_walkthrough": (
        "Use H3 section per workflow stage. Each stage: explanation then code."
    ),
    "bullets_with_description": "Each bullet: **term**: one-sentence description.",
}

_TONE_CONFIG: Optional[dict] = None  # Module-level singleton


def load_tone_config(path: Optional[str] = None) -> dict:
    """Load tone_config.yaml from module directory (cached).

    Falls back to empty dict if yaml is not installed or file is missing.

    Args:
        path: Optional explicit path to a tone_config.yaml file.
              When None, resolves relative to this module's directory.

    Returns:
        Parsed tone config dict, or {} on any error.
    """
    global _TONE_CONFIG
    if _TONE_CONFIG is not None:
        return _TONE_CONFIG
    if not _YAML_AVAILABLE:
        _TONE_CONFIG = {}
        return _TONE_CONFIG
    config_path = Path(path) if path else (Path(__file__).parent / "tone_config.yaml")
    try:
        _TONE_CONFIG = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except Exception:
        _TONE_CONFIG = {}
    return _TONE_CONFIG


def _reset_tone_config_cache() -> None:
    """Reset the module-level cache (used in tests to reload fresh config)."""
    global _TONE_CONFIG
    _TONE_CONFIG = None


def build_section_prompt_enhancement(
    tone_config: dict,
    page_role: str,
    base_prompt: str,
) -> str:
    """Append tone + structure directives to an existing LLM prompt.

    Adapted from content-generator tone_utils.py:37.
    Returns base_prompt unchanged if tone_config is empty or if the
    page_role (and default) are missing from section_controls.

    Args:
        tone_config: Loaded tone config dict (from load_tone_config()).
        page_role: Page role string (e.g. "tutorial", "faq", "api_reference").
                   Unknown roles fall back to the "default" section control.
        base_prompt: The existing LLM prompt text to enhance.

    Returns:
        base_prompt with editorial directives appended, or base_prompt
        unchanged when config is empty/missing.
    """
    if not tone_config:
        return base_prompt

    global_voice = tone_config.get("global_voice", {})
    section_controls = tone_config.get("section_controls", {})
    # Prefer exact role match, fall back to "default"
    section = section_controls.get(page_role) or section_controls.get("default", {})
    if not section:
        return base_prompt

    pov = global_voice.get("pov", "second_person")
    formality = global_voice.get("formality", "professional_conversational")
    tech_depth = global_voice.get("technical_depth", "intermediate")
    tone = section.get("tone", "informative")
    structure_key = section.get("structure", "prose_with_subheadings")
    structure_directive = STRUCTURE_DIRECTIVES.get(structure_key, "")
    word_count = section.get("word_count_target", "")
    required = section.get("required_elements", [])
    avoid = section.get("avoid_phrases", [])

    pov_map = {
        "second_person": "second person (use 'you', 'your')",
        "first_person": "first person (use 'I', 'we')",
        "third_person": "third person (avoid 'you')",
    }

    required_block = "\n".join(f"- {e}" for e in required) if required else "- (none)"
    avoid_block = ", ".join(f'"{p}"' for p in avoid) if avoid else "(none)"

    enhancement = (
        f"\n\n**TONE AND STYLE:**\n"
        f"- Write in {pov_map.get(pov, pov)} perspective\n"
        f"- Formality: {formality}\n"
        f"- Technical depth: {tech_depth} (assume developer audience)\n"
        f"- Section tone: {tone}\n"
        f"\n**STRUCTURE:**\n"
        f"- {structure_directive}\n"
        + (f"- Target length: {word_count}\n" if word_count else "")
        + f"\n**REQUIRED ELEMENTS (include all):**\n{required_block}\n"
        + f"\n**AVOID** these phrases: {avoid_block}\n"
    )

    return base_prompt + enhancement
