# Pilot Program

## Overview

The pilot program validates the v2 pipeline against two real-world products
before expanding to the full family matrix. Pilots exercise all 5 workers,
all quality gates, and all template variants. A pilot must achieve GO criteria
before the pipeline is considered production-ready.

---

## Pilot Configurations

### Pilot 1: aspose-cells-foss-python

| Field | Value |
|-------|-------|
| Family | `cells` |
| Platform | `python` |
| Display name | Aspose.Cells FOSS for Python |
| Repo URL | `https://github.com/aspose-cells/Aspose.Cells-for-Python-via-.NET` |
| Canonical import | `aspose_cells_foss` |
| Category | Spreadsheet processing |
| Config file | `configs/pilots/aspose-cells-foss-python.yaml` |

**Why this pilot**: Rich API surface, extensive documentation, many code
examples. Represents a Tier A (rich) repository. Tests the pipeline's ability
to handle large volumes of claims and code snippets.

### Pilot 2: aspose-note-foss-python

| Field | Value |
|-------|-------|
| Family | `note` |
| Platform | `python` |
| Display name | Aspose.Note FOSS for Python |
| Repo URL | `https://github.com/aspose-note/Aspose.Note-for-Python-via-.NET` |
| Canonical import | `aspose_note_foss` |
| Category | Digital notebook processing |
| Config file | `configs/pilots/aspose-note-foss-python.yaml` |

**Why this pilot**: Smaller API surface, fewer examples. Represents a Tier B/C
(partial/thin) repository. Tests the pipeline's ability to generate quality
content with limited source material.

---

## Shared Pilot Settings

Both pilots share identical LLM and output configuration:

```yaml
launch_tier: auto
validation_profile: pilot

llm:
  primary:
    base_url: "https://llm.professionalize.com/v1"
    model: "qwen3-next/oss"
  fallback:
    base_url: "http://127.0.0.1:11434/v1"
    model: "gemma3:12b"
  temperature: 0.0
  max_tokens: 6000
  max_concurrency: 4

output:
  goal: draft
  run_dir: "runs/"
```

### launch_tier: auto

When set to `auto`, the Understand worker resolves the tier based on repository
richness scoring:

| Tier | Score range | Criteria |
|------|:-----------:|----------|
| A (full) | 70+ | Docs + examples + API docs present |
| B (core) | 30-69 | Partial docs or examples |
| C (minimal) | 0-29 | Code only, no docs or examples |

The richness tier maps to launch tier: A=full, B=core, C=minimal.

### validation_profile: pilot

The `pilot` profile applies stricter validation than `local`:
- All safety-critical gates are enforced (not just warnings).
- Severity escalations are active.
- GO/NO_GO criteria are evaluated.

---

## Validation Criteria

### GO Criteria

A pilot run achieves GO when all thresholds are met:

| Criterion | Threshold | Description |
|-----------|:---------:|-------------|
| A+B rate | >= 50% | At least half of pages grade A or B |
| D+F rate | <= 30% | No more than 30% of pages grade D or F |
| Claim coverage | >= 70% | At least 70% of public claims used in content |
| Gate pass rate | 100% | All safety-critical gates pass |
| Schema validation | 100% | All artifacts pass schema validation |

### NO_GO Actions

When a pilot run produces NO_GO:
1. Review the `evaluation_report.json` for `root_cause_diagnosis`.
2. File taskcards for each root cause.
3. Fix the responsible upstream worker (not the symptoms).
4. Re-run the pilot.

### NEEDS_HUMAN_REVIEW

When the Evaluate worker cannot determine root cause or `max_re_runs` is
exhausted, the verdict is NEEDS_HUMAN_REVIEW. A human must inspect the output,
make manual checkpoint edits if needed, and resume.

---

## Phase Progression

The pilot program advances through phases. Each phase addresses the top blockers
from the previous phase's content review.

### Phase Structure

| Phase | Goal | Entry criteria | Exit criteria |
|-------|------|---------------|---------------|
| 1 | Scaffold | Plan approved | Repo structure, schemas, pipeline.yaml in place |
| 2 | Workers | Phase 1 done | All 5 workers implemented, tests pass |
| 3 | Quality tuning | Phase 2 done | First pilot run produces evaluation report |
| 4 | Blocker fixes | Phase 3 done | Top blockers addressed, D+F rate improving |
| 5 | Content quality | Phase 4 done | Both pilots reviewed, taskcards for remaining issues |
| 6 | Regression fixes | Phase 5 done | Regressions from Phase 5 fixed |
| 7 | GO | Phase 6 done | Both pilots achieve GO criteria |

### Phase Review

At the end of each phase:
1. Run both pilots.
2. Grade all generated pages using the content review protocol.
3. Compare metrics against previous phase.
4. Identify top blockers for the next phase.
5. File taskcards.

---

## Content Review Protocol

Each generated page is reviewed against 7 checks:

| Check | What it verifies |
|-------|-----------------|
| Frontmatter | Required fields present, correct types, valid URL |
| Structure | Heading hierarchy, section count, no empty sections |
| Alignment | Content matches heading, claims used correctly |
| Code | Correct imports, valid syntax, demonstrates claimed feature |
| Density | Sufficient word count, no placeholder content |
| Spec leakage | No internal API details, no raw JSON in prose |
| SEO | Meta description present, keywords used naturally |

### Grading Scale

| Grade | Meaning |
|-------|---------|
| A | Publication-ready, no issues |
| B | Minor issues, acceptable for publication |
| C | Moderate issues, needs improvement but not blocking |
| D | Major issues, not publishable |
| F | Critical issues, fundamentally broken |

---

## Expected Page Counts

Based on the ruleset, each pilot generates approximately:

| Section | Cells (full) | Note (core) |
|---------|:------------:|:-----------:|
| Products | 1 | 1 |
| Docs | 5-7 | 4-5 |
| KB | 9-12 | 9-11 |
| Reference | 4-7 | 2-4 |
| Blog | 2-3 | 2 |
| **Total** | **21-30** | **18-23** |
