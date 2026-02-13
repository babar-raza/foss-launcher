---
id: TC-1505
title: "Synthesize Claims from Code-Only README Sections"
status: Done
priority: Normal
owner: "agent_b"
updated: "2026-02-13"
tags: ["w2", "extract-claims", "quickstart", "code-synthesis", "readme"]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-1505_quickstart_code_synthesis.md
  - src/launch/workers/w2_facts_builder/extract_claims.py
  - tests/unit/workers/test_tc_411_extract_claims.py
evidence_required:
  - "reports/agents/agent_b/TC-1505/evidence.md"
spec_ref: "7a2e753d308154582e85aea06a0cf85e2c91a5f2"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# Taskcard TC-1505 — Synthesize Claims from Code-Only README Sections

## Objective
When a structured README section (Quick Start, Getting Started, Installation) contains only code blocks with no extractable prose, synthesize a narrative claim describing what the code does, so that `quickstart_steps` and related claim groups are populated.

## Problem Statement
The Aspose.3D README's `## Quick Start` section (lines 38-60) contains ONLY a Python code block — no prose text. `_extract_section_claims()` skips code fence lines and code body lines fail prose filters. Result: zero claims extracted, zero `quickstart_steps`. The function also lacks `in_code_block` state tracking, so inner code lines fall through to filters instead of being properly collected.

## Scope

### In scope
- Add code block state tracking (`in_code_block`, `all_code_lines`) to `_extract_section_claims()`
- New helper `_synthesize_code_block_claim()` using AST-based extraction for Python, template fallback for other languages
- Pass `section_heading` from `extract_structured_sections_from_readme()` to `_extract_section_claims()`
- Ensure synthetic claims contain quickstart markers for worker.py grouping
- 5 new tests

### Out of scope
- LLM-based code summarization
- Modifying worker.py claim grouping logic
- Changes to non-README claim extraction

## Acceptance criteria
1. Code-only Quick Start section produces at least 1 synthetic claim
2. Synthetic claim has `section_kind='workflow'` and `source_type='readme_technical'`
3. Synthetic claim text contains quickstart markers (for worker.py grouping into `quickstart_steps`)
4. Sections with prose content do NOT produce synthetic claims (prose extraction takes priority)
5. All 5 new tests pass
6. All existing tests pass unchanged
