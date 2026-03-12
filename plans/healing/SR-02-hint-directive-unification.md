# SR-02: Unify `_PLACEHOLDER_HINTS` and `_STRUCTURE_DIRECTIVES`

**Status**: Done (run_20260306_235748)
**Gap**: Two parallel hint systems can produce contradictory LLM guidance. `_PLACEHOLDER_HINTS` (in `template_loader.py`) provides `content_hint` + word counts, while `_STRUCTURE_DIRECTIVES` (in `section_prompt.py`) provides output-shape instructions. Both are injected into the same prompt but are authored independently with no cross-validation.

## Scope

- `src/launcher/content/template_loader.py` — `_PLACEHOLDER_HINTS`
- `src/launcher/workers/generate/section_prompt.py` — `_STRUCTURE_DIRECTIVES`
- `src/launcher/prompts/section_writer.txt` — prompt template consuming both

## Acceptance Checks

1. For every `__BODY_*__` placeholder that maps to a heading, the `content_hint` and `structure_directive` are semantically aligned (no contradictions)
2. A mapping table documents the relationship: placeholder → heading → hint → directive
3. Word-count ranges in `_PLACEHOLDER_HINTS` are consistent with directive complexity (e.g., a table directive shouldn't have `max_words=100`)
4. Single source of truth: either unify into one registry or add a cross-validation test

## Deliverables

| # | File | Change |
|---|------|--------|
| 1 | `section_prompt.py` | Add `DIRECTIVE_REGISTRY` combining heading, content_hint, min/max words, and structure_directive in one place (or cross-reference) |
| 2 | `template_loader.py` | Align `_PLACEHOLDER_HINTS` word counts with directive complexity |
| 3 | `tests/unit/content/test_template_loader.py` | Test that every placeholder hint heading has a matching directive |
| 4 | `tests/unit/workers/test_generate.py` | Test that content_hint and structure_directive don't contradict |

## Hard Rules

- Do NOT break the prompt template format — `{content_hint}` and `{structure_directive}` must still resolve
- Do NOT change public function signatures
- If unifying, the merged registry must be importable from both modules without circular imports

## Cross-Validation Results (run_20260306_235748)

### Contradictions Fixed

| Placeholder | Old Range | New Range | Reason |
|---|---|---|---|
| CONSTRUCTORS | 50-200 | 100-400 | Table with 3 columns needs more words |
| PROPERTIES | 50-400 | 80-400 | Table min was below useful threshold |
| METHODS | 50-400 | 80-400 | Table min was below useful threshold |
| TROUBLESHOOTING | 50-200 | 100-400 | H3 problem-solution pairs are verbose |
| KEY_MEMBERS | 50-300 | 80-300 | Table min was below useful threshold |

### Missing Directives Added

| Key | Source |
|---|---|
| code samples | __BODY_CODE_SAMPLES__ placeholder (alias of "code examples") |
| core concepts | PAGE_ROLE_SKELETONS comprehensive_guide |
| implementation | PAGE_ROLE_SKELETONS comprehensive_guide |
| advanced usage | PAGE_ROLE_SKELETONS comprehensive_guide |
| constructor | PAGE_ROLE_SKELETONS reference_object_page (singular) |
| example | PAGE_ROLE_SKELETONS reference_object_page (singular) |

### Verification

626 tests passed, 0 failed. Full evidence at
`reports/agents/agent_d/SR-02/run_20260306_235748/evidence.md`.
