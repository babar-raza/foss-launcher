---
id: TC-3886
title: "Fix content_density false positives in review prompt for code/link/troubleshoot sections"
status: In-Progress
priority: High
owner: "agent"
updated: "2026-03-09"
tags: [evaluate, review_prompt, content_density, false_positive]
depends_on: [TC-3885]
allowed_paths:
  - plans/taskcards/TC-3886_fix_content_density_false_positives_in_review_prompt.md
  - src/launcher/prompts/review_prompt.txt
  - tests/
evidence_required:
  - reports/TC-3886/evidence.md
---

# Taskcard TC-3886 — Fix content_density false positives in review prompt

## Objective

The `recommended` (LLM reviewer) is generating `content_density HIGH` findings for sections
that are intentionally short or code/link-focused:
- "Code Example" sections with brief intro + code block (the code IS the content)
- "See Also" sections with link lists (the links ARE the content)
- Troubleshooting sub-sections that cover a specific error with 1 clear paragraph
- Format reference tables (the table IS the content, no prose needed)

These false positives cause 26 `content_density HIGH` findings across 19 pages, contributing
to C grades on pages that should be B. The fix is to update criterion 6 in `review_prompt.txt`
to specify section-type-aware expectations.

## Required spec references

- `specs/09_quality_evaluation.md` (content_density definition)

## Scope

### In scope
- Update criterion 6 (CONTENT DENSITY) in `src/launcher/prompts/review_prompt.txt`
- Narrow the criterion to target narrative sections, not code/link/reference sections

### Out of scope
- Changing other review criteria (factual_accuracy, completeness, etc.)
- Changing the grader thresholds
- Changing the generate worker

## Inputs

- `src/launcher/prompts/review_prompt.txt` — criterion 6 definition

## Outputs

- Updated review_prompt.txt with more precise content_density guidance

## Allowed paths

- plans/taskcards/TC-3886_fix_content_density_false_positives_in_review_prompt.md
- src/launcher/prompts/review_prompt.txt

### Allowed paths rationale
- review_prompt.txt — contains criterion 6 that generates false positives

## Implementation steps

### Step 1: Update criterion 6 in review_prompt.txt

Change criterion 6 from:
```
6. CONTENT DENSITY: Each section has substantive prose. No placeholder text,
   no "[Content to be generated]", no empty sections.
```

To:
```
6. CONTENT DENSITY: Narrative/explanatory sections must have substantive prose
   (at least 2 sentences of explanation, not just a code block or list).
   IMPORTANT EXCEPTIONS — do NOT flag these as thin:
   - "Code Example" / "Example" sections: a brief 1-sentence intro + working code is correct.
   - "See Also" / "References" / "Related" sections: link lists are the correct content.
   - "Supported Formats" / "Format Reference" tables: tables are the correct content.
   - Troubleshooting sub-sections covering a specific error: 1 clear paragraph (problem
     + solution) is sufficient — do not require 2+ paragraphs for each specific error.
   DO flag: empty sections, "[Content to be generated]" placeholder, narrative sections
   (Overview, Introduction, Prerequisites, Getting Started) with only 1 sentence or a
   bullet list where paragraphs are expected.
```

## Failure modes

### Failure mode 1: False negatives (genuinely thin sections not flagged)

**Detection**: Narrative sections with 1 sentence pass review
**Resolution**: The updated criterion still explicitly targets narrative sections; only
code/link/table/troubleshoot exceptions are carved out
**Gate**: Review of pilot run page quality

### Failure mode 2: LLM ignores the guidance

**Detection**: content_density HIGHs still appear for Code Example/See Also sections
**Resolution**: Make the exceptions even more explicit; add specific examples
**Gate**: Pilot run evaluate_checkpoint

### Failure mode 3: Review prompt becomes too long

**Detection**: skills_loader warns about truncation
**Resolution**: If prompt is truncated, trim other less-critical sections
**Gate**: Log: "[skills] Block truncated" warning check

## Task-specific review checklist

1. [ ] Criterion 6 updated with section-type exceptions
2. [ ] "Code Example" sections explicitly exempted
3. [ ] "See Also/References" sections explicitly exempted
4. [ ] "Supported Formats/tables" explicitly exempted
5. [ ] Troubleshooting sub-sections explicitly exempted (1 paragraph sufficient)
6. [ ] DO-flag list still includes narrative sections and placeholders
7. [ ] review_prompt.txt length not significantly increased

## Deliverables

1. `src/launcher/prompts/review_prompt.txt` — updated criterion 6

## Acceptance checks

1. [ ] Pilot run shows reduced content_density HIGHs on howto pages
2. [ ] "See Also" sections no longer flagged
3. [ ] "Code Example" sections no longer flagged
4. [ ] Narrative thin sections still flagged appropriately
5. [ ] A+B rate improves compared to TC-3885 run

## Self-review

### Verification results
- [ ] Implemented: review_prompt.txt updated
- [ ] Evidence captured: reports/TC-3886/evidence.md

## E2E verification

Run pilot and compare evaluate_checkpoint content_density HIGH count vs TC-3885 run (26).

## Integration boundary proven

**Upstream**: Generate worker produces content with Code Example / See Also sections
**Downstream**: Grader uses content_density HIGHs for grade assignment
**Contract**: False-positive CD HIGHs eliminated → pages with 1 other HIGH reach Grade B
