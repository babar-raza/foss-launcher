# Evidence: TC-2391 — Tone Control System for W5 SectionWriter

**Agent**: W5_AGENT
**Taskcard**: TC-2391
**Date**: 2026-02-20
**Status**: Done

## Summary

Implemented a declarative tone control system for W5 SectionWriter. Every `generate_*_content()` function now injects editorial voice and structural constraints into its LLM prompt based on page role, adapting from the content-generator reference implementation.

## Files Created

### `src/launch/workers/w5_section_writer/tone_config.yaml`

YAML configuration with 12 section controls (tutorial, api_reference, troubleshooting, faq, feature_showcase, workflow_page, comprehensive_guide, best_practices, getting_started, landing, blog, default) plus `global_voice` block (pov: second_person, formality: professional_conversational, technical_depth: intermediate).

Each section control defines:
- `tone`: editorial voice guidance
- `structure`: one of 6 structure directives (step_by_step, prose_with_subheadings, problem_solution_pairs, qa_pairs, segmented_walkthrough, bullets_with_description)
- `word_count_target`: target length range
- `required_elements`: list of content elements the LLM must include
- `avoid_phrases`: list of phrases to avoid

### `src/launch/workers/w5_section_writer/tone_utils.py`

Two public functions:
- `load_tone_config(path=None) -> dict` — loads and caches tone_config.yaml; falls back to `{}` if yaml is not installed or file is missing; module-level singleton with `_reset_tone_config_cache()` for test isolation
- `build_section_prompt_enhancement(tone_config, page_role, base_prompt) -> str` — appends TONE AND STYLE, STRUCTURE, REQUIRED ELEMENTS, AVOID blocks; unknown roles fall back to `default` section control; empty config returns `base_prompt` unchanged

STRUCTURE_DIRECTIVES dict maps structure keys to human-readable formatting instructions.

## Files Modified

### `src/launch/workers/w5_section_writer/generators/content_generators.py`

Added at module level (after existing imports):
```python
from ..tone_utils import load_tone_config, build_section_prompt_enhancement
_TONE_CONFIG = load_tone_config()
```

Integrated tone enhancement into 14 generators by calling `build_section_prompt_enhancement()` immediately before each LLM call. All integrations use `page.get("page_role", "<role_default>")` to read the page role from the page dict.

Generators enhanced:
1. `generate_tutorial_content` — before `_call_llm_for_content()`, default role: "tutorial"
2. `generate_feature_showcase_content` — before `_call_llm_for_content()`, default role: "feature_showcase"
3. `generate_troubleshooting_content` — before `_call_llm_for_content()`, default role: "troubleshooting"
4. `generate_faq_content` — before `_call_llm_for_content()`, default role: "faq"
5. `generate_best_practices_content` — before `_call_llm_for_content()`, default role: "best_practices"
6. `generate_comprehensive_guide_content` — before `_call_llm_for_content()`, default role: "comprehensive_guide"
7. `generate_blog_content` — before `_call_llm_for_content()`, default role: "blog"
8. `generate_performance_content` — before `_call_llm_for_content()`, default role: "best_practices"
9. `generate_workflow_page_content` — before `chat_completion()`, default role: "workflow_page"
10. `generate_landing_content` — before `chat_completion()`, default role: "landing"
11. `generate_api_reference_content` — before `chat_completion()`, default role: "api_reference"
12. `generate_format_conversion_content` — before `chat_completion()`, default role: "tutorial"
13. `generate_howto_article_content` — before `chat_completion()`, default role: "tutorial"
14. `generate_feature_blog_content` — before `chat_completion()`, default role: "blog"

`generate_toc_content()` was intentionally excluded — structural nav pages do not benefit from tone control.
`generate_getting_started_content()` does not call the LLM (fully deterministic) — not enhanced.

### `tests/unit/workers/test_tc_440_section_writer.py`

Added `TestToneControlSystem` class with 5 tests:
1. `test_tone_config_loads` — YAML loads, has `global_voice` and `section_controls` keys, 12+ entries
2. `test_build_enhancement_tutorial` — result contains "numbered steps" for tutorial role
3. `test_build_enhancement_api_reference` — result contains "method signature" for api_reference role
4. `test_build_enhancement_missing_role` — unknown role falls back to default, returns enhanced prompt
5. `test_build_enhancement_no_config` — empty dict returns base_prompt unchanged

## Test Results

```
5 passed (tone tests):
  tests/unit/workers/test_tc_440_section_writer.py::TestToneControlSystem::test_tone_config_loads
  tests/unit/workers/test_tc_440_section_writer.py::TestToneControlSystem::test_build_enhancement_tutorial
  tests/unit/workers/test_tc_440_section_writer.py::TestToneControlSystem::test_build_enhancement_api_reference
  tests/unit/workers/test_tc_440_section_writer.py::TestToneControlSystem::test_build_enhancement_missing_role
  tests/unit/workers/test_tc_440_section_writer.py::TestToneControlSystem::test_build_enhancement_no_config

Full suite: 4602 passed, 9 skipped, 1 warning (0 failures, 0 regressions)
```

## Acceptance Checks

- [x] `tone_config.yaml` loads without error
- [x] `build_section_prompt_enhancement("tutorial", ...)` returns prompt containing "numbered steps"
- [x] `build_section_prompt_enhancement("api_reference", ...)` returns prompt containing "method signature"
- [x] Unknown page_role falls back to `default` tone config
- [x] Empty/missing config gracefully returns base_prompt
- [x] All 5 tests pass; full suite has 0 regressions
- [x] No existing generator tests broken
