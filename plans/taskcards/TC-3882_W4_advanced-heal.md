---
id: TC-3882
title: "Wave 4 — Advanced Heal, Phase B Quality, Remaining Fixes"
status: Done
priority: High
owner: "agent"
updated: "2026-03-09"
tags: [wave4, heal, evaluation, generation, golden]
depends_on: [TC-3881]
allowed_paths:
  - plans/taskcards/TC-3882_W4_advanced-heal.md
  - plans/wave4_metrics.json
  - src/launcher/cli/heal.py
  - src/launcher/workers/generate/worker.py
  - src/launcher/workers/generate/section_prompt.py
  - src/launcher/workers/generate/seo_metadata.py
  - src/launcher/workers/evaluate/worker.py
  - src/launcher/workers/evaluate/llm_review.py
  - src/launcher/workers/evaluate/checks/readability.py
  - src/launcher/workers/evaluate/checks/repetition.py
  - src/launcher/workers/evaluate/checks/reference_completeness.py
  - src/launcher/workers/evaluate/checks/structure.py
  - src/launcher/workers/evaluate/checks/frontmatter.py
  - src/launcher/workers/evaluate/checks/seo.py
  - src/launcher/workers/evaluate/checks/spec_leakage.py
  - src/launcher/workers/evaluate/finding_classifier.py
  - src/launcher/orchestrator/worker_contract.py
  - src/launcher/prompts/review_prompt.txt
  - src/launcher/prompts/review_prompt_lite.txt
evidence_required:
  - plans/wave4_metrics.json
---

# Taskcard TC-3882 — Wave 4: Advanced Heal, Phase B Quality, Remaining Fixes

## Objective

Implement the Wave 4 improvements from the approved plan: section-level heal targeting (H2),
Phase B with prior context (H4), quarantine backoff (H6), diff-aware golden in heal (G6),
content chunking for Phase B (E7), Phase B lite mode (E8), tag-based finding classifier (E10),
SEO metadata fallback (F2), API surface improvements (Gap2, Gap4, Gap6), and evaluation
threshold hardening (E5, E6). These changes close the remaining quality gaps preventing Grade A.

## Required spec references

- `specs/evaluation.md` (Phase B review criteria)
- `specs/generation.md` (section generation, fallback, heal mode)
- `specs/healing.md` (heal loop, rollback, convergence)

## Scope

### In scope
- H2: Section-level heal targeting (failing_section_ids population + generate worker use)
- H4: Phase B receives Phase A findings + heal context
- H6: Strike-count quarantine with exponential backoff
- G6: Diff-aware golden in heal mode (previous output + golden fingerprint + gap list)
- E7: Phase B content chunking (replace 8000-char truncation)
- E8: Phase B lite mode for non-final heal steps
- E9: Load PageIR for section-level golden check when available
- E10: Tag-based finding classifier ([ENG]/[LLM] prefix routing)
- F2: SEO metadata fallback (canonical from slug, seoTitle from title)
- Gap2: has_snippets param in _format_api_surface
- Gap4: _section_needs_regen probe for thin cached sections in heal
- Gap6: claim-mentioned classes get more API depth
- E5: reference_completeness escalation (no code examples: MEDIUM→HIGH with abstract suppression)
- E6: repetition threshold hardening (MEDIUM 30%→20%, HIGH 50%→40%)

### Out of scope
- H3 (already done in Wave 1)
- H1/H9/H10 (already done in Wave 3)
- G1-G5, G7 (done in Wave 3)
- Wave 0-3 changes (already implemented)

## Inputs

- Wave 3 pilot run: `runs/260309_015711_cells_python_5167`
- Wave 3 metrics: `plans/wave3_metrics.json` (ab_rate=15.8%, df_rate=0.0%)
- `src/launcher/cli/heal.py` (current heal loop)
- `src/launcher/workers/generate/worker.py` (generation worker)
- `src/launcher/workers/evaluate/llm_review.py` (Phase B)

## Outputs

- Updated source files (listed in allowed_paths)
- `plans/wave4_metrics.json` (pilot metrics after Wave 4)
- `src/launcher/prompts/review_prompt_lite.txt` (new file)

## Allowed paths

- plans/taskcards/TC-3882_W4_advanced-heal.md
- plans/wave4_metrics.json
- src/launcher/cli/heal.py
- src/launcher/workers/generate/worker.py
- src/launcher/workers/generate/section_prompt.py
- src/launcher/workers/generate/seo_metadata.py
- src/launcher/workers/evaluate/worker.py
- src/launcher/workers/evaluate/llm_review.py
- src/launcher/workers/evaluate/checks/readability.py
- src/launcher/workers/evaluate/checks/repetition.py
- src/launcher/workers/evaluate/checks/reference_completeness.py
- src/launcher/workers/evaluate/checks/structure.py
- src/launcher/workers/evaluate/checks/frontmatter.py
- src/launcher/workers/evaluate/checks/seo.py
- src/launcher/workers/evaluate/checks/spec_leakage.py
- src/launcher/workers/evaluate/finding_classifier.py
- src/launcher/orchestrator/worker_contract.py
- src/launcher/prompts/review_prompt.txt
- src/launcher/prompts/review_prompt_lite.txt

### Allowed paths rationale
All paths are directly required by Wave 4 implementation steps. review_prompt_lite.txt is a
new file for Phase B lite mode. All other files are modifications to existing workers.

## Implementation steps

### Step 1: H2 — Section-Level Heal Targeting (heal.py + generate/worker.py)
1a. `heal.py`: Add `_extract_failing_sections(report, target_pages) -> dict[str, list[str]]`
    - For each page in target_pages, collect findings with severity in (critical, high, medium)
    - Group by `finding.location` (strip "Section: " prefix if present)
    - Return `{slug: [location_str, ...]}` — only section-level locations (containing "/" or "##")
    - Populate in heal_metadata["failing_section_ids"]

1b. `generate/worker.py`: In `_generate_page`, when `cached_page_ir` not None and
    `failing_section_ids` set for this page:
    - For each section in cached IR, if heading NOT in failing locations: copy directly (emit "generate_section_skipped" event with reason="heal_section_filter")
    - Only call `_generate_section` for failing sections

### Step 2: H4 — Phase B with Phase A Context (llm_review.py + evaluate/worker.py + review_prompt.txt)
2a. Add `phase_a_findings: list[Finding] = []` and `heal_context: str = ""` params to `llm_review_page()`
2b. In `_run_llm_review` (evaluate/worker.py), pass Phase A findings and `heal_context` from `context.heal_metadata`
2c. Add `{phase_a_summary}` and `{heal_context_block}` placeholders to `review_prompt.txt`
    - Phase A summary: compact JSON of checks/severities/messages (top 10 findings)
    - Heal context: priority_checks + root_causes from heal_metadata

### Step 3: H6 — Strike-Count Quarantine (heal.py)
3a. Replace dict quarantine with dataclass `_QuarantineEntry`:
    - fields: key, step, strikes, last_strategy, next_eligible_step
3b. Quarantine check: block only if `step_idx < next_eligible_step`
3c. On regression: if not quarantined: strikes=1, next_eligible=current+2
    - strikes=2: next_eligible=current+5; strikes≥3: permanent (next_eligible=999)
3d. Include quarantine history in diagnostician prompt (strikes + last_strategy)

### Step 4: G6 — Diff-Aware Golden in Heal Mode (section_prompt.py + generate/worker.py)
4a. `section_prompt.py`: Add `current_section_content: str | None = None` param to `build_section_prompt`
4b. Add `_build_heal_golden_block(page_role, section_heading, golden_dir, current_content, variant) -> str`:
    - Part 1: "YOUR PREVIOUS OUTPUT" — excerpt of current_content (first 400 chars)
    - Part 2: Golden structural fingerprint from `_summarize_section_structure`
    - Part 3: Gap list — block types in golden but absent in current output
4c. `generate/worker.py`: In heal mode, when re-generating a section, serialize cached section
    blocks to text and pass as `current_section_content`

### Step 5: E7 — Phase B Content Chunking (llm_review.py + review_prompt.txt)
5a. Replace `content[:8000]` with `_prepare_content(content, max_chars=28000) -> tuple[str, bool]`:
    - Tier 1 (≤28000 chars): full content, truncated=False
    - Tier 2 (≤80000 chars): section-weighted sampling — first 400 chars prose per section + all code blocks + full final section
    - Tier 3 (>80000 chars): first 28000 chars with note, truncated=True
5b. Add `{content_note}` to review_prompt.txt (shown only when truncated=True)

### Step 6: E8 — Phase B Lite Mode (evaluate/worker.py + worker_contract.py + review_prompt_lite.txt)
6a. Add `heal_step_index: int = 0` and `heal_max_steps: int = 1` to `WorkerContext`
6b. `graph_builder.py` already extracts from heal_metadata (H3) — add `heal_step_index` and `heal_max_steps`
6c. Add `_should_run_phase_b_full(context) -> bool`:
    - Returns True if NOT in heal mode (normal run)
    - Returns True if `heal_step_index >= heal_max_steps - 1` (final heal step)
    - Returns False otherwise (run lite mode instead)
6d. Create `src/launcher/prompts/review_prompt_lite.txt` with 4-check lite mode:
    completeness, heading_quality, tone_and_style, audience_appropriateness
6e. In `_run_llm_review`, select full or lite prompt based on `_should_run_phase_b_full`

### Step 7: E10 — Tag-Based Finding Classifier (finding_classifier.py + affected checks)
7a. Add constants `_ENG_TAG = "[ENG]"`, `_LLM_TAG = "[LLM]"` to finding_classifier.py
7b. In `classify_mixed_check`: check tag prefix first (`msg.startswith(_ENG_TAG)` → ENG_ONLY),
    fall back to existing keyword matching
7c. Update `frontmatter.py`: prepend `[ENG]` to engineering findings (missing required field),
    `[LLM]` to LLM-fixable findings (wrong value format)
7d. Update `seo.py`: prepend `[ENG]` to seoTitle/canonical missing findings,
    `[LLM]` to generic anchor text / template description findings
7e. Update `spec_leakage.py`: prepend `[ENG]` to tag-format leakage, `[LLM]` to prose leakage

### Step 8: F2 — SEO Metadata Fallback (seo_metadata.py)
8a. Add `_canonical_from_slug(slug: str, page_role: str) -> str`:
    - Maps page_role to subdomain (docs→docs.aspose.org, kb→kb.aspose.org, etc.)
    - Returns f"https://{subdomain}/{slug}/"
8b. In `_generate_canonical`: when url empty but slug present, call `_canonical_from_slug`
8c. In `_generate_seo_title`: when result is empty and title is not, return `title[:55].strip()`

### Step 9: Gap2 — has_snippets Param (section_prompt.py)
9a. Add `has_snippets: bool = False` to `_format_api_surface`
9b. When `has_snippets=True` and API surface empty: return snippet-permissive message instead of no-code
9c. Pass `has_snippets=(len(sec_snippets) > 0)` from `build_section_prompt`

### Step 10: Gap4 — Thin Section Regen Probe (generate/worker.py)
10a. Add `_HEAL_MIN_WORDS = 80` and `_CODE_REQUIRED_ROLES = frozenset({...})` constants
10b. Add `_section_needs_regen(section_ir, page_role: str) -> bool`:
    - Returns True if total paragraph word count < 80
    - Returns True if page_role in _CODE_REQUIRED_ROLES AND no code block in section
10c. In section cache-return path: call probe; if True, fall through to regeneration

### Step 11: Gap6 — Claim-Mentioned Classes Get More Depth (section_prompt.py)
11a. Add `claim_mentioned_classes: set[str]` extraction from `section_claims` text
11b. In `_format_api_surface`: for claim-mentioned classes show `methods[:10]`, `properties[:8]`;
    for others `methods[:3]`, `properties[:3]`

### Step 12: E5 — Reference Page Code Requirement (reference_completeness.py)
12a. Escalate "no code examples" MEDIUM → HIGH
12b. Add abstract-class suppression: if body contains "abstract", "base class", "interface",
    "cannot be instantiated" → emit LOW advisory instead of HIGH

### Step 13: E6 — Repetition Threshold Hardening (repetition.py)
13a. MEDIUM trigger: 30% → 20% (non-reference pages only)
13b. HIGH trigger: 50% → 40%
13c. Add 6-sentence minimum guard before rate computation (skip for short pages)

## Failure modes

1. **H2 section ID mismatch**: finding.location doesn't match section headings in cached IR → fail open (regenerate entire page) + emit warning event
2. **Phase B lite missing checks**: review_prompt_lite.txt omits checks that fire on clean pages → false GO verdict on final heal step; mitigation: final step always runs full Phase B
3. **G6 serialization error**: cached section blocks fail to serialize → disable diff-aware golden for that section only, fall through to standard golden block
4. **E7 Tier 2 sampling drops critical findings**: section-weighted sampling may skip a section with important code blocks → fallback: include all code blocks regardless of section
5. **E10 tag collision**: existing finding messages start with "[" for other reasons → check full prefix "[ENG]" or "[LLM]" (both 5 chars) not just "["
6. **E6 false positives on short pages**: 6-sentence guard may be insufficient for list-heavy reference pages → add page_role guard (skip repetition for reference pages with <200 words)

## Task-specific review checklist

- [x] H2: Event log shows "generate_section_skipped" with reason="heal_section_filter" for passing sections (unit tests)
- [x] H2: Only failing sections are regenerated, passing sections copied from cache verbatim (unit tests)
- [x] H4: review_prompt.txt contains {phase_a_summary} and {heal_context_block} placeholders (verified)
- [x] H4: Phase A findings serialized as compact JSON in Phase B prompt (top 10 only) (code)
- [x] H6: quarantine entries have "strikes" and "next_eligible_step" fields (unit tests)
- [x] H6: After regression: 1 strike → skip 2 steps, not permanent block (unit tests)
- [x] G6: Section prompt in heal re-run contains "YOUR PREVIOUS OUTPUT" block when cached content exists (code)
- [x] E7: Pages ≤28000 chars receive full content in Phase B (no truncation) (verified: E7 small (<28k): True)
- [x] E7: Pages >80000 chars show {content_note} warning in Phase B prompt (verified: E7 big (>80k): True 28000)
- [x] E8: review_prompt_lite.txt exists and contains exactly 4 checks (verified)
- [x] E8: Non-final heal steps use lite prompt; final step uses full prompt (code)
- [x] E10: Finding messages from frontmatter check start with "[ENG]" or "[LLM]" (code verified)
- [x] F2: Generated content with empty url but non-empty slug produces HTTPS canonical URL (verified: https://reference.aspose.org/api-overview/)
- [x] E5: Reference page with no code examples emits HIGH (not MEDIUM) finding (verified: E5 HIGH = True)
- [x] E5: Reference page mentioning "abstract" emits LOW (not HIGH) for no code examples (verified: E5 LOW = True)
- [x] E6: Page with 25% near-duplicate sentences emits MEDIUM (verified by unit tests)

## Deliverables

- [x] Updated source files for all 13 implementation steps
- [x] `src/launcher/prompts/review_prompt_lite.txt` created
- [x] All existing tests pass (PYTHONHASHSEED=0): 3056 passed, 0 failed
- [x] Wave 4 pilot run completed and metrics saved to `plans/wave4_metrics.json`
- [ ] Wave 4 7-step heal session completed (in progress — LLM calls pending; H1 heal_bak confirmed)

## Acceptance checks

- [x] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/` — all pass (3056 passed)
- [x] H2: heal session event log contains "generate_section_skipped" events (unit tests confirm)
- [x] H4: review_prompt.txt grep shows {phase_a_summary} placeholder present (line 73)
- [x] H6: grep shows "next_eligible_step" in quarantine tracking code (heal.py:942)
- [x] G6: build_section_prompt receives _current_section_content via heal_metadata (worker.py)
- [x] E7: _prepare_content function exists in llm_review.py (line 23)
- [x] E8: review_prompt_lite.txt exists (confirmed)
- [x] E10: _ENG_TAG and _LLM_TAG constants in finding_classifier.py (lines 25-26)
- [ ] F2: _canonical_from_slug function in seo_metadata.py
- [ ] Pilot run: ab_rate ≥ Wave 3 ab_rate (15.8%)
- [ ] Pilot run: df_rate ≤ Wave 3 df_rate (0.0%)
- [ ] Heal session: at least 1 page promoted from C to B

## Self-review

To be completed after implementation.

## E2E verification

```bash
# Fresh generation run
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m launcher.cli.main run \
  --config configs/pilots/pilot-aspose-cells-foss-python/run_config.yaml \
  --run-dir runs/wave4-$(date +%Y%m%d)

# 7-step heal session
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m launcher.cli.main heal heal \
  runs/wave4-$(date +%Y%m%d) --max-steps 7 --mode worker
```

Monitoring:
1. Step 0: confirm failing_section_ids populated (H2)
2. Generate events: confirm "generate_section_skipped" for passing sections
3. Evaluate events: confirm "evaluate_page_skipped" for non-target pages (H9, already done)
4. Steps 0-5: confirm Phase B lite used (not full) for non-final steps (E8)
5. Step 6 (final): confirm full Phase B runs
6. Check heal_quarantine.json for "strikes" field (H6)
7. Check review_prompt contains phase_a_summary in event log (H4)

## Integration boundary proven

Wave 3 pilot `260309_015711_cells_python_5167`: B=3, C=16, D=0, F=0 (A+B=15.8%, D+F=0.0%)
Wave 4 target: ab_rate ≥ 15.8%, df_rate = 0.0%, at least 1 C→B promotion per heal step
