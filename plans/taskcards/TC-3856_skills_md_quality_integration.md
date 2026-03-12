---
id: TC-3856
title: "skills.md — Content Quality Standards Integration"
status: In-Progress
priority: High
owner: agent
updated: "2026-03-08"
tags: [quality, generation, evaluation, prompts]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-3856_skills_md_quality_integration.md
  - skills.md
  - configs/pipeline.yaml
  - src/launcher/models/run_config.py
  - src/launcher/shared/skills_loader.py
  - src/launcher/workers/generate/section_prompt.py
  - src/launcher/prompts/section_writer.txt
  - src/launcher/workers/generate/worker.py
  - src/launcher/workers/evaluate/llm_review.py
  - src/launcher/prompts/review_prompt.txt
  - src/launcher/workers/evaluate/worker.py
evidence_required:
  - reports/TC-3856/evidence.md
---

# Taskcard TC-3856 — skills.md Content Quality Standards Integration

## Objective

Create a `skills.md` quality-standards document and wire it into both the
generation and evaluation pipeline stages so that every LLM call is guided
by domain-specific quality standards, pushing generated content toward
consistent A-grade output without requiring per-session prompt engineering.

## Required spec references

- `specs/worker_generate.md` (Sandwich model, pre-LLM prompt construction)
- `specs/worker_evaluate.md` (Phase B LLM review, grading criteria)
- `specs/system_contract.md` (Config-driven pipeline, contract boundaries)

## Scope

### In scope
- `skills.md` document at project root (quality standards, anti-patterns, per-role depth)
- `SkillsConfig` pydantic model in `run_config.py`
- `skills:` block in `configs/pipeline.yaml` (opt-in, defaulting enabled when file exists)
- `skills_loader.py` — loads generation block and evaluation block from `skills.md`
- `section_writer.txt` — `{skills_block}` placeholder injection
- `section_prompt.py` — `skills_block` parameter added, loader called
- `generate/worker.py` — loads skills once per worker run, passes to prompt builder
- `review_prompt.txt` — `{skills_criteria_block}` placeholder injection
- `llm_review.py` — `skills_criteria` parameter added
- `evaluate/worker.py` — loads skills criteria once, passes to `_run_llm_review`

### Out of scope
- New deterministic gates (separate taskcard)
- Per-page-role sub-files in `specs/skills/` (future extension)
- Skills effect on heal directives or outline builder (separate taskcards)
- Any schema changes to `specs/schemas/` (not required)

## Inputs

- Existing `src/launcher/prompts/section_writer.txt` (64-line prompt template)
- Existing `src/launcher/prompts/review_prompt.txt` (94-line review rubric)
- `src/launcher/workers/generate/section_prompt.py` (prompt builder)
- `src/launcher/workers/generate/worker.py` (calls `build_section_prompt`)
- `src/launcher/workers/evaluate/llm_review.py` (Phase B review)
- `src/launcher/workers/evaluate/worker.py` (calls `_run_llm_review`)
- `src/launcher/models/run_config.py` (RunConfig model)
- `configs/pipeline.yaml` (pipeline topology + defaults)

## Outputs

- `skills.md` — quality standards document (project root)
- `src/launcher/shared/skills_loader.py` — loader module
- Modified `run_config.py` — `SkillsConfig` + `RunConfig.skills` field
- Modified `pipeline.yaml` — `skills:` block
- Modified `section_writer.txt` — `{skills_block}` placeholder
- Modified `section_prompt.py` — `skills_block` param, loader call removed (caller provides)
- Modified `generate/worker.py` — loads skills, passes to prompt builder
- Modified `review_prompt.txt` — `{skills_criteria_block}` placeholder
- Modified `llm_review.py` — `skills_criteria` param
- Modified `evaluate/worker.py` — loads skills criteria, passes to `_run_llm_review`

## Allowed paths

- plans/taskcards/TC-3856_skills_md_quality_integration.md
- skills.md
- configs/pipeline.yaml
- src/launcher/models/run_config.py
- src/launcher/shared/skills_loader.py
- src/launcher/workers/generate/section_prompt.py
- src/launcher/prompts/section_writer.txt
- src/launcher/workers/generate/worker.py
- src/launcher/workers/evaluate/llm_review.py
- src/launcher/prompts/review_prompt.txt
- src/launcher/workers/evaluate/worker.py

### Allowed paths rationale
- `skills.md` — new quality-standards document, project root (not a protected path)
- `configs/pipeline.yaml` — opt-in control block (`skills: enabled/path`)
- `run_config.py` — adds `SkillsConfig` model field to `RunConfig`
- `skills_loader.py` — new shared module, loads/parses `skills.md`
- `section_prompt.py` — adds `skills_block: str = ""` parameter to `build_section_prompt`
- `section_writer.txt` — adds `{skills_block}` format variable
- `generate/worker.py` — loads skills at startup, passes to `build_section_prompt`
- `llm_review.py` — adds `skills_criteria: str = ""` parameter
- `review_prompt.txt` — adds `{skills_criteria_block}` format variable
- `evaluate/worker.py` — loads skills criteria, passes to `_run_llm_review`

## Implementation steps

### Step 1: Create skills.md at project root

Write a structured quality-standards document with three named sections:
- `## GENERATION STANDARDS` — injected into section_writer.txt pre-LLM
- `## EVALUATION CRITERIA` — injected into review_prompt.txt pre-LLM
- `## ANTI-PATTERNS` — referenced by both sections for what to avoid

### Step 2: Add SkillsConfig to run_config.py

```python
class SkillsConfig(LauncherBaseModel):
    enabled: bool = True
    path: str = "skills.md"
```
Add `skills: SkillsConfig = Field(default_factory=SkillsConfig)` to `RunConfig`.

### Step 3: Add skills block to pipeline.yaml

```yaml
skills:
  enabled: true
  path: "skills.md"
```

### Step 4: Create src/launcher/shared/skills_loader.py

Two public functions:
- `load_generation_block(skills_path, page_role) -> str` — extracts GENERATION STANDARDS section
- `load_evaluation_block(skills_path, page_role) -> str` — extracts EVALUATION CRITERIA section

Both return empty string if file missing or disabled.

### Step 5: Modify section_writer.txt

Add `{skills_block}` immediately before the `STRICT RULES:` block. When empty
(skills disabled or file missing), renders as empty string with no visible gap.

### Step 6: Modify section_prompt.py

Add `skills_block: str = ""` parameter to `build_section_prompt`. Pass it to
`template.format(... skills_block=skills_block ...)`.

### Step 7: Modify generate/worker.py

Load skills once per worker run using `skills_loader.load_generation_block`.
Pass `skills_block=skills_block` to `build_section_prompt`.

### Step 8: Modify review_prompt.txt

Add `{skills_criteria_block}` after the 10-point checklist and before the
OUTPUT FORMAT section.

### Step 9: Modify llm_review.py

Add `skills_criteria: str = ""` parameter to `llm_review_page`. Pass it to
`prompt_template.format(... skills_criteria_block=skills_criteria ...)`.

### Step 10: Modify evaluate/worker.py

Load skills criteria once per worker run using `skills_loader.load_evaluation_block`.
Pass it to `llm_review_page` via `_run_llm_review`.

## Failure modes

### Failure mode 1: skills.md missing at configured path

**Detection**: `FileNotFoundError` or empty string return from `load_generation_block`
**Resolution**: `skills_loader` returns `""` when file missing — pipeline continues
unaffected. Log a DEBUG message noting skills not loaded.
**Gate**: No gate — graceful degradation is the correct behavior.

### Failure mode 2: skills_block causes template.format() KeyError

**Detection**: `KeyError` in `build_section_prompt` during `template.format()`
**Resolution**: The `{skills_block}` placeholder must be added to `section_writer.txt`
before the loader is wired in. If placeholder is missing, add it. Verify with a
unit test that calls `build_section_prompt` with `skills_block=""`.
**Gate**: Covered by existing generate worker tests.

### Failure mode 3: skills_criteria_block causes KeyError in review_prompt.txt

**Detection**: `KeyError` in `llm_review_page` during `prompt_template.format()`
**Resolution**: Verify `{skills_criteria_block}` placeholder exists in `review_prompt.txt`
before wiring. Test with `skills_criteria=""`.
**Gate**: Covered by existing evaluate worker tests.

### Failure mode 4: skills content bloats prompt beyond LLM context window

**Detection**: LLM returns empty/truncated response, or `max_tokens` errors in logs
**Resolution**: Keep GENERATION STANDARDS section under 400 words. Keep EVALUATION
CRITERIA section under 200 words. Add token-budget warning to skills_loader if
block exceeds 800 chars.
**Gate**: Monitor via existing LLM telemetry.

### Failure mode 5: skills.md format variable conflict with existing prompts

**Detection**: `KeyError` or `IndexError` during `template.format()` if skills.md
contains unescaped `{` or `}` characters
**Resolution**: `skills_loader` must escape braces: `text.replace("{", "{{").replace("}", "}}")`
before returning the block for prompt injection.
**Gate**: Unit test with brace-containing skills content.

## Task-specific review checklist

1. [ ] `skills.md` contains exactly three sections: GENERATION STANDARDS, EVALUATION CRITERIA, ANTI-PATTERNS
2. [ ] `skills_loader.py` returns `""` when `skills.md` is absent (no exception raised)
3. [ ] `skills_loader.py` escapes `{` and `}` in loaded text to prevent format-string collisions
4. [ ] `build_section_prompt` signature change is backwards-compatible (`skills_block=""` default)
5. [ ] `llm_review_page` signature change is backwards-compatible (`skills_criteria=""` default)
6. [ ] `section_writer.txt` renders correctly when `skills_block=""` (no double blank lines)
7. [ ] `review_prompt.txt` renders correctly when `skills_criteria_block=""` (no double blank lines)
8. [ ] `RunConfig.skills` defaults to `SkillsConfig(enabled=True, path="skills.md")`
9. [ ] `pipeline.yaml` `skills:` block added and parseable by `RunConfig`
10. [ ] All existing tests pass (PYTHONHASHSEED=0)

## Deliverables

1. `skills.md` at project root
2. `src/launcher/shared/skills_loader.py`
3. Modified files: `run_config.py`, `pipeline.yaml`, `section_writer.txt`,
   `section_prompt.py`, `generate/worker.py`, `review_prompt.txt`,
   `llm_review.py`, `evaluate/worker.py`

## Acceptance checks

1. [ ] `.venv/Scripts/python.exe -m pytest tests/ -x -q` passes with PYTHONHASHSEED=0
2. [ ] `skills_loader.load_generation_block(Path("skills.md"), "howto_article")` returns non-empty string
3. [ ] `skills_loader.load_generation_block(Path("nonexistent.md"), "")` returns `""`
4. [ ] `build_section_prompt(..., skills_block="")` runs without error
5. [ ] `llm_review_page(..., skills_criteria="")` runs without error

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] No KeyError in prompt formatting with empty skills blocks
- [ ] Evidence captured: reports/TC-3856/evidence.md

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

**Expected results**:
- All tests pass
- No regressions in generate or evaluate worker tests

## Integration boundary proven

**Upstream**: `RunConfig` carries `SkillsConfig` → workers read `config.skills`
**Downstream**: `build_section_prompt` and `llm_review_page` receive pre-loaded
string blocks — zero runtime I/O in the hot path after worker startup
**Contract**: `skills_loader` returns plain `str` (empty or content); callers
treat empty string as "skills not active" with no behavioural change
