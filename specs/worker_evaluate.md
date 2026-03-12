# Worker: Evaluate

Worker ID: `evaluate`
Input schema: `content_manifest.schema.json`
Output schema: `evaluation_report.schema.json`

## Purpose

Assess every generated page for publication readiness. Produce an
EvaluationReport containing per-page grades, gate results, a GO/NO-GO verdict,
and root-cause diagnosis for any failures. Route re-runs to the responsible
worker.

## Phase A: Deterministic Checks

Eight deterministic gates run against each page. No LLM is used. Each gate
produces a `gate_result.schema.json` entry.

### 1. Frontmatter Validation

- All required fields present: `title`, `slug`, `weight`, `description`,
  `type`, `url`.
- `page_role` is a registered role in `rulesets/ruleset.yaml`.
- No raw JSON fragments in `title` or `description`.

### 2. Structure Validation

- Exactly one H1 (the page title).
- Heading hierarchy is monotonically increasing (no H4 after H2 without H3).
- No bare template-label headings (e.g., `## [Section Title]`).

### 3. Code Validation

- Every fenced code block specifies a language tag.
- Python code blocks parse without AST errors.
- All imports are in the `import_allowlist` from the UnderstandingBundle.
- Pages in `_CODE_REQUIRED_ROLES` have at least one code block.

### 4. Content Density

- Minimum word count per page role (e.g., howto_article >= 300, landing >= 150).
- No section is empty or contains only placeholder text.
- Prose-to-code ratio is between 0.3 and 5.0.

### 5. Spec Leakage

- No internal claim IDs, section IDs, or schema field names appear in the
  rendered Markdown.
- No `claim_id:`, `section_id:`, or `block_type:` strings in output.

### 6. Artifact Integrity

- Both `ir_path` and `md_path` exist on disk.
- The PageIR JSON is valid against `page_ir.schema.json`.
- Content hash of `md_path` matches the hash recorded at generation time.

### 7. Safety

- No profanity, PII patterns, or license-violating content.
- No external URLs pointing outside the product's known domains.
- No competitor product names used in promotional context.

### 8. SEO

- `description` meta field is 50-160 characters.
- Title is 20-70 characters.
- At least 2 of the page's `seo_keywords` appear in the body.
- Permalink is unique across the entire manifest.

## Phase B: LLM Evaluation

After deterministic checks, run a typed LLM evaluation per page using the
sandwich model:

- **Pre-LLM**: Build a prompt containing the rendered Markdown, the page's
  assigned claims, and the grading rubric.
- **LLM**: Ask for a structured JSON response with `grade` (A-F),
  `findings[]`, and `metrics`.
- **Post-LLM**: Validate the response against `self_review_result.schema.json`.
  If the LLM response is unparseable, default to grade C and log the error.

The LLM evaluation checks:

1. **Accuracy** -- Claims are faithfully represented; no hallucinated features.
2. **Completeness** -- All assigned claims are covered.
3. **Tone** -- Professional, consistent, free of marketing fluff.
4. **Readability** -- Clear structure, no wall-of-text sections.

## Grading Criteria

| Grade | Definition |
|-------|-----------|
| A | Publication-ready. Zero critical/high findings. All gates pass. |
| B | Minor issues only. Zero critical findings, at most 2 high findings. All safety-critical gates pass. |
| C | Moderate issues. No critical findings. Some compensating gates may fail. |
| D | Significant issues. One or more high findings, or a safety-critical gate failure that can be root-caused. |
| F | Unpublishable. Critical findings, multiple gate failures, or structural corruption. |

The final grade for each page is `min(deterministic_grade, llm_grade)` -- the
more severe grade wins.

## GO/NO-GO Thresholds

The overall verdict is computed from aggregate metrics:

| Criterion | Threshold | Field |
|-----------|-----------|-------|
| D+F rate | <= 30% of pages | `go_criteria.df_rate` |
| A+B rate | >= 50% of pages | `go_criteria.ab_rate` |
| Critical findings | 0 across all pages | `go_criteria.critical_count` |
| Safety gate | 100% pass rate | `go_criteria.safety_pass_rate` |
| Claim coverage | >= 0.80 | `go_criteria.claim_coverage` |

If all thresholds are met: `verdict: GO`.
If any threshold is missed: `verdict: NO_GO`.
If safety gate passes but other thresholds are borderline (within 5%):
`verdict: NEEDS_HUMAN_REVIEW`.

## Root-Cause Diagnosis Format

For every page graded D or F, produce a diagnosis entry:

```json
{
  "issue": "Missing code examples in howto_article page",
  "responsible_worker": "generate",
  "responsible_phase": "per-section sandwich",
  "root_cause": "LLM did not produce code blocks despite _CODE_REQUIRED_ROLES",
  "fix": "Re-run generate for this page with strengthened code constraint",
  "affected_pages": ["how-to-open-a-file"]
}
```

Each diagnosis must name exactly one `responsible_worker` and one
`responsible_phase`. The `fix` field must be actionable.

## Re-Run Routing

When verdict is `NO_GO`, the pipeline runner reads `re_run_targets` from
`pipeline.yaml` and routes re-runs:

1. **Understand** -- If root cause is in claim extraction, richness
   classification, or page planning.
2. **Generate** -- If root cause is in content generation, template selection,
   or BlockIR assembly.

Re-runs are capped at `max_re_runs: 2` (from pipeline.yaml). Each re-run
increments the run counter. If the cap is reached and verdict is still NO_GO,
the pipeline halts and emits a `pipeline_halted` event.

Re-runs must regenerate from scratch (Rule 6: no patching). The responsible
worker re-executes fully for the affected pages.

## Output Validation

The EvaluationReport is validated against `evaluation_report.schema.json`
before checkpoint. Validation failure is a hard error.

---

## Extended Spec (v2 Detail Addendum)

### Purpose (Extended)

Quality gate. Two-phase: deterministic checks + typed LLM evaluation. Does NOT mutate content. Produces `evaluation_report.json` with GO / NO-GO / NEEDS_HUMAN_REVIEW verdict.

### Phase A — Deterministic Checks (Extended Gate Table)

| # | Check | Gate Files | Severity |
|---|-------|-----------|---------|
| 1 | Frontmatter validation | `gate_frontmatter_schema.py` | CRITICAL |
| 2 | Heading structure | `gate_heading_hierarchy.py`, `gate_template_heading_substitution.py` | ERROR |
| 3 | Code examples | `gate_code_syntax_valid.py`, `gate_code_fence_api_validity.py`, `gate_import_allowlist.py` | CRITICAL |
| 4 | Content density | `gate_content_density.py`, `gate_intra_page_repetition.py` | ERROR |
| 5 | Spec leakage | `gate_spec_leakage.py`, `gate_api_hallucination.py` | ERROR |
| 6 | LLM artifacts | `gate_llm_artifact_phrases.py`, `gate_scaffold_leak.py` | WARNING |
| 7 | Safety gates | `gate_xss_prevention.py`, `gate_sensitive_data_leak.py` | CRITICAL (always) |
| 8 | SEO quality | `gate_markdown_lint.py` + inline SEO checks | WARNING |

### Phase B — Typed LLM Evaluation (Sandwich)

- **Pre-LLM**: Build `LLMInputEnvelope` with file content + Phase A findings + evaluation criteria
- **LLM** (temp=0.0): Single call per file → `LLMReviewResult` with alignment, coherence, usefulness scores
- **Post-LLM**: Cross-validate LLM scores against Phase A findings; assign A-F grade per file

### GO Criteria (Extended)

| Metric | Threshold |
|--------|-----------|
| CRITICAL findings | 0 |
| Files at A or B | ≥ 80% |
| Files at D or F | 0% |
| Code examples in workflow roles | 100% |
| Canonical imports in code blocks | 100% |

### Self-Review Assertions

| check_id | Severity | Rule |
|----------|----------|------|
| `report.all_pages_graded` | BLOCKER | Every page in content_bundle has a grade entry |
| `report.critical_blockers` | BLOCKER | If verdict == GO, zero CRITICAL findings exist |
| `report.diagnosis_complete` | BLOCKER | If NO-GO, every D/F file has ≥ 1 root_cause_diagnosis entry |
| `report.go_criteria_evaluated` | BLOCKER | All 5 GO criteria have pass/fail values |
| `report.grade_distribution` | WARNING | Grade distribution sums to 100% of pages |

### Human Escalation Protocol (NEEDS_HUMAN_REVIEW)

Triggered when `verdict == "NO-GO"` after `re_run_count >= 2`.

**Output file**: `runs/<run_id>/escalation.json`

```json
{
  "verdict": "NEEDS_HUMAN_REVIEW",
  "run_id": "20260308-cells-python-a1b2c3",
  "re_run_count": 2,
  "unresolved_issues": [
    {
      "issue": "Spec-internal claims on getting-started page",
      "grade": "F",
      "page_id": "docs-getting-started",
      "responsible_worker": "understand",
      "root_cause": "Visibility filter not excluding binary format claims",
      "suggested_fix": "Remove claims with kind='binary_format_detail' from understanding_bundle.json"
    }
  ],
  "artifacts_to_edit": [
    {"path": "runs/<run_id>/understanding_bundle.json", "action": "Remove or reclassify listed claims"}
  ],
  "resume_command": "launch run --resume-from understand --run-id 20260308-cells-python-a1b2c3"
}
```

**Exit codes**: `0` = GO · `1` = internal error · `2` = NEEDS_HUMAN_REVIEW

**Human action**: Read `escalation.json` → edit artifact → run `resume_command`.

### Tests (Extended)

- `tests/unit/workers/test_evaluate_self_review.py`
- `tests/unit/test_go_criteria.py`
- `tests/integration/test_evaluate_v1_output.py` (evaluate v1 output → expect NO-GO with diagnosis)
