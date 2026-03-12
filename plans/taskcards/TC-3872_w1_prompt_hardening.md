---
id: TC-3872
title: "Wave 1: Prompt Hardening — Template-Label Headings + Artifact Phrases + Spec Vocab"
status: In-Progress
priority: High
owner: "Agent-B"
updated: "2026-03-09"
tags: [wave-1, prompts, section-validator, quality]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-3872_w1_prompt_hardening.md
  - src/launcher/prompts/section_writer.txt
  - src/launcher/prompts/claim_extractor.txt
  - src/launcher/workers/generate/section_validator.py
  - src/launcher/shared/classify_claims.py
  - tests/generate/test_section_validator.py
  - tests/shared/test_classify_claims.py
  - reports/TC-3872/evidence.md
evidence_required:
  - reports/TC-3872/evidence.md
---

# Taskcard TC-3872 — Wave 1: Prompt Hardening

## Objective

Apply three prompt/post-LLM engineering fixes that eliminate the most common D-grade
and C-grade findings: template-label headings, LLM artifact phrases, and spec vocabulary
leakage. All fixes are low-risk (prompts + deterministic post-LLM stripping).

## Required spec references

- `specs/worker_generate.md` (Section: section_writer prompt, STRICT RULES)
- `specs/worker_evaluate.md` (Section: check_structure, check_artifacts, check_spec_leakage)

## Scope

### In scope
- W1-S1: Template-label heading prevention (section_writer.txt STRICT RULES + section_validator.py)
- W1-S2: LLM artifact phrase strip (section_writer.txt STRICT RULES + section_validator.py)
- W1-S6: Spec vocabulary triple-layer defense (classify_claims.py + claim_extractor.txt + section_writer.txt)

### Out of scope
- Dict-literal artifacts (TC-3873)
- SEO metadata (TC-3873)
- Import normalization (TC-3870/TC-3873)
- Snippet ranking (TC-3874)

## Inputs

- `src/launcher/prompts/section_writer.txt` — current STRICT RULES block
- `src/launcher/prompts/claim_extractor.txt` — current EXCLUSIONS block
- `src/launcher/workers/generate/section_validator.py` — `_validate_block`
- `src/launcher/shared/classify_claims.py` — `_INTERNAL_PATTERNS`
- `src/launcher/workers/evaluate/checks/spec_leakage.py` — `_INTERNAL_TERMS`
- `src/launcher/workers/evaluate/checks/structure.py` — `_TEMPLATE_LABEL_PATTERNS`
- `src/launcher/workers/evaluate/checks/artifacts.py` — `_ARTIFACT_PHRASES`

## Outputs

- Updated `section_writer.txt` with hardened STRICT RULES
- Updated `claim_extractor.txt` with spec vocabulary EXCLUSIONS
- Updated `section_validator.py` with deterministic strips
- Updated `classify_claims.py` with synced `_INTERNAL_PATTERNS`
- `reports/TC-3872/evidence.md`

## Allowed paths

- plans/taskcards/TC-3872_w1_prompt_hardening.md
- src/launcher/prompts/section_writer.txt
- src/launcher/prompts/claim_extractor.txt
- src/launcher/workers/generate/section_validator.py
- src/launcher/shared/classify_claims.py
- tests/generate/test_section_validator.py
- tests/shared/test_classify_claims.py
- reports/TC-3872/evidence.md

### Allowed paths rationale
Prompt files: add prohibition rules. section_validator.py: add strip functions.
classify_claims.py: sync internal patterns. Tests: verify strip behavior.

## Implementation steps

### Step 1: Read all source files

Read:
- `src/launcher/prompts/section_writer.txt` (full)
- `src/launcher/prompts/claim_extractor.txt` (full)
- `src/launcher/workers/generate/section_validator.py` (focus on `_validate_block`)
- `src/launcher/shared/classify_claims.py` (focus on `_INTERNAL_PATTERNS`)
- `src/launcher/workers/evaluate/checks/spec_leakage.py` (`_INTERNAL_TERMS`)
- `src/launcher/workers/evaluate/checks/structure.py` (`_TEMPLATE_LABEL_PATTERNS`)
- `src/launcher/workers/evaluate/checks/artifacts.py` (`_ARTIFACT_PHRASES`)

### Step 2: W1-S1 — Template-label heading prevention

**section_writer.txt**: Find the STRICT RULES block. Add after the existing "Do NOT insert placeholder text" rule:
```
- NEVER output a heading block (`##`, `###`, etc.) whose text is the literal content_hint or section heading `{section_heading}`. NEVER repeat a skeleton label as a heading.
- Heading text MUST be descriptive and specific — never a generic label like "Overview", "Introduction", "Section", or any value from: [section title], [content], TBD, TODO, fill in
```

**section_validator.py**: In `_validate_block`, for `BlockType.heading` blocks, add a check:
```python
# Import _TEMPLATE_LABEL_PATTERNS from checks.structure (or define locally if circular)
_HEADING_LABEL_PATTERNS = ["section title", "content to be generated", "tbd", "todo", "fill in", "section heading", "section content"]
heading_text = content.lstrip("#").strip().lower()
if any(pat in heading_text for pat in _HEADING_LABEL_PATTERNS):
    return None  # drop this block
```
IMPORTANT: Import from `checks/structure.py` if that list exists there. Do NOT duplicate.

### Step 3: W1-S2 — Artifact phrase strip

**section_writer.txt**: Extend the "Do NOT start with 'Let's explore'" rule to:
```
- NEVER use these phrases anywhere in your output (not just sentence openings): "Let's explore", "Let's dive into", "Happy coding", "In conclusion", "To summarize", "As mentioned earlier", "Feel free to", "Don't hesitate to", "I hope this helps", "Great question", "In this section we will"
```

**section_validator.py**: Add `_strip_artifact_phrases(content: str) -> str` function.
- Import `_ARTIFACT_PHRASES` from `src/launcher/workers/evaluate/checks/artifacts.py`
  (do NOT copy the list — import it)
- For each phrase in `_ARTIFACT_PHRASES`: strip at sentence boundaries
  (sentence start: preceded by `.` + space, or at string start)
- Call this in `_validate_block` for `BlockType.paragraph` blocks

### Step 4: W1-S6 — Spec vocabulary triple-layer defense

**Layer 1 — classify_claims.py**: Read `_INTERNAL_PATTERNS`. Compare against `_INTERNAL_TERMS`
in spec_leakage.py. Add any missing terms as word-boundary regex patterns.
Each term T should produce pattern: `r'\b' + re.escape(T) + r'\b'`

**Layer 2 — claim_extractor.txt**: Find EXCLUSIONS block (or add one if missing). Add:
```
- Claims containing specification vocabulary: wire protocol, vtable, opcode, byte offset,
  memory layout, serialization format, file format specification, internal API,
  private field, binary format — these are internal implementation details
```

**Layer 3 — section_writer.txt**: In STRICT RULES, add:
```
- NEVER use these internal technical terms in prose: wire protocol, vtable, opcode,
  byte offset, memory layout, serialization format, file format specification,
  internal API, private field, binary format
```

### Step 5: Run tests

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/generate/test_section_validator.py tests/shared/test_classify_claims.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q --tb=short
```

All 2944+ tests must pass.

## Failure modes

### Failure mode 1: Circular import — section_validator.py importing from checks/structure.py
**Detection**: Import error at runtime or test time
**Resolution**: Copy the minimal pattern list directly into section_validator.py as
`_HEADING_LABEL_PATTERNS = [...]` with a comment "# Keep in sync with checks/structure.py _TEMPLATE_LABEL_PATTERNS"
**Gate**: No circular import error; tests pass

### Failure mode 2: _strip_artifact_phrases strips too aggressively (removes valid content)
**Detection**: Test cases show legitimate sentences containing substrings of artifact phrases being stripped
**Resolution**: Use word-boundary matching: `re.sub(r'\b' + re.escape(phrase) + r'\b', '', content, flags=re.IGNORECASE)`
Only strip at sentence start (check `re.match` for phrase at start of sentence after `.`)
**Gate**: Test fixtures with legitimate content pass through unchanged

### Failure mode 3: spec vocabulary patterns conflict with technical documentation
**Detection**: Valid technical claims (e.g., "the library reads binary files") get classified as internal
**Resolution**: Use exact phrase matching (not substring) for multi-word terms.
"binary format" requires the whole phrase; "binary" alone should not be blocked.
**Gate**: classify_claims tests pass with correct visibility classification

## Task-specific review checklist

1. [ ] section_writer.txt STRICT RULES has template-label heading prohibition
2. [ ] section_writer.txt STRICT RULES has extended artifact phrase prohibition
3. [ ] section_writer.txt STRICT RULES has spec vocabulary prohibition
4. [ ] claim_extractor.txt has spec vocabulary EXCLUSIONS block
5. [ ] section_validator.py `_validate_block` drops template-label headings
6. [ ] section_validator.py `_strip_artifact_phrases` calls imported list (not copy)
7. [ ] classify_claims.py `_INTERNAL_PATTERNS` synced with spec_leakage.py `_INTERNAL_TERMS`
8. [ ] Docstrings updated for new/modified functions
9. [ ] Spec file updated if section_validator behavior changed
10. [ ] Schema description fields present for any new config fields
11. [ ] evidence.md: before/after diff of each file + test pass confirmation

## Deliverables

1. Updated `src/launcher/prompts/section_writer.txt`
2. Updated `src/launcher/prompts/claim_extractor.txt`
3. Updated `src/launcher/workers/generate/section_validator.py`
4. Updated `src/launcher/shared/classify_claims.py`
5. `reports/TC-3872/evidence.md`

## Acceptance checks

1. [ ] section_writer.txt has all 3 new prohibition blocks
2. [ ] section_validator.py drops template-label heading blocks in unit test
3. [ ] section_validator.py strips artifact phrases from paragraph content in unit test
4. [ ] classify_claims.py patterns sync confirmed (side-by-side table in evidence.md)
5. [ ] All 2944+ tests pass

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Evidence captured: reports/TC-3872/evidence.md
- [ ] Prompt changes do not break any existing prompt tests

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q --tb=short
```

**Expected results**:
- All 2944+ tests pass
- No regressions on existing section_validator or classify_claims tests

## Integration boundary proven

**Upstream**: LLM generates raw BlockIR JSON output
**Downstream**: `_validate_block` returns cleaned BlockIR; cleaned content enters SectionIR
**Contract**: `_validate_block(block_dict) -> BlockIR | None` — returns None to drop block
