---
id: TC-3876
title: "Planner: derive section headings from golden when golden.enabled=true"
status: In-Progress
priority: High
owner: "claude-agent"
updated: "2026-03-09"
tags: [golden, planner, sections, content-density, quality]
depends_on: [TC-3875]
allowed_paths:
  - plans/taskcards/TC-3876_planner_golden_driven_sections.md
  - src/launcher/workers/planner/
  - tests/unit/workers/test_planner_golden_sections.py
evidence_required:
  - reports/TC-3876/evidence.md
---

# Taskcard TC-3876 — Planner: derive section headings from golden when golden.enabled=true

## Objective

When `golden.enabled=true`, every planned page's section headings must come from
the corresponding golden file instead of the generic page skeleton. This guarantees:
1. The golden reference block in section prompts always matches (exact heading match).
2. `enforce_block_spec` always finds a matching golden spec.
3. Generated pages structurally mirror A-grade exemplars.

Current state: planner uses `page_skeletons.py` headings; golden headings differ →
`_load_golden_for_role` returns empty for most sections → golden has no effect.

## Required spec references

- `src/launcher/shared/golden_loader.py` — `GoldenIndex`, `GoldenPage`
- `src/launcher/workers/planner/` — planner worker builds skeletons
- `src/launcher/shared/page_skeletons.py` — generic fallback skeletons

## Scope

### In scope
- Load GoldenIndex in the planner worker when `config.golden.enabled`
- For each planned page, if its `page_role` maps to a golden page, derive
  `SkeletonSection` objects from the golden file's section headings (with
  appropriate `min_words`, `max_words`, `content_hint` inferred from golden spec)
- Fall back to existing page_skeletons when no golden page exists for the role

### Out of scope
- No changes to `GoldenIndex` or `golden_loader.py`
- No changes to generate worker or section_prompt.py
- No changes to the golden file content

## Inputs

- `src/launcher/workers/planner/` — planner worker
- `src/launcher/shared/golden_loader.py` — GoldenIndex API
- `src/launcher/models/run_config.py` — GoldenConfig (TC-3875)

## Outputs

- Modified planner worker: when `golden.enabled`, skeleton sections derived from golden
- `tests/unit/workers/test_planner_golden_sections.py` — unit tests

## Allowed paths

- `src/launcher/workers/planner/`
- `tests/unit/workers/test_planner_golden_sections.py`

### Allowed paths rationale
Planner worker and its tests only.

## Implementation steps

### Step 1: Load GoldenIndex in planner worker

In the planner worker, after loading `RunConfig.golden`, load GoldenIndex:
```python
golden_index = None
if config.golden.enabled:
    from launcher.shared.golden_loader import GoldenIndex
    golden_index = GoldenIndex.load(Path(config.golden.dir))
```

### Step 2: Derive skeleton from golden page

For each planned page with `page_role`, if `golden_index.select_for_tier(page_role, richness_tier)` returns a page:
- Extract section headings from the GoldenPage.sections list
- Build `SkeletonSection` objects using heading, `golden_section.word_count * 0.7` as min_words, `golden_section.word_count * 1.5` as max_words, and `golden_section.excerpt[:200]` as content_hint

### Step 3: Fall back to page_skeletons when no golden match

When `golden_index` is None or `select_for_tier` returns None, use existing skeleton.

### Step 4: Unit tests

Test: GoldenIndex produces SkeletonSections with correct headings; fallback fires when role not in golden.

## Failure modes

### Failure mode 1: Golden page has no sections (empty file)
**Detection**: `golden_page.sections` is empty list
**Resolution**: Fall back to existing page_skeleton — log warning
**Gate**: `if not golden_page.sections: use_fallback()`

### Failure mode 2: Golden min_words > generated content → always fails density check
**Detection**: Content density high findings remain after fix
**Resolution**: Scale min_words factor from 0.7 down if needed; tune from pilot results
**Gate**: Review content_density high count in next pilot run

### Failure mode 3: Planner context doesn't have RunConfig.golden
**Detection**: `getattr(config, 'golden', None)` returns None
**Resolution**: GoldenConfig defaults to `enabled=False` — falls back gracefully
**Gate**: Unit test with no golden config in RunConfig

## Task-specific review checklist

1. [ ] Planner loads GoldenIndex when `config.golden.enabled=True`
2. [ ] Each page role mapped to golden page uses golden section headings
3. [ ] Pages with no golden match fall back to page_skeletons (no crash)
4. [ ] `SkeletonSection` min/max words derived from golden section word_count
5. [ ] `content_hint` uses golden section excerpt
6. [ ] Unit tests cover: golden match, no-golden fallback, empty sections
7. [ ] Full test suite passes

## Deliverables

1. Modified planner worker (`src/launcher/workers/planner/`)
2. New `tests/unit/workers/test_planner_golden_sections.py`

## Acceptance checks

1. [ ] Next pilot run shows `_load_golden_for_role` finding sections (no "unmatched" warnings)
2. [ ] Golden reference blocks appear in section prompts
3. [ ] `enforce_block_spec` activates for matched sections
4. [ ] Unit tests pass

## Self-review

### Verification results
- [ ] Tests: X/X PASS

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_planner_golden_sections.py -v
```

## Integration boundary proven

**Upstream**: RunConfig.golden (TC-3875) enables GoldenIndex loading
**Downstream**: SkeletonSection headings → section_prompt._build_golden_reference_block → LLM prompt
**Contract**: SkeletonSection.heading matches GoldenPage.sections[i].heading exactly
