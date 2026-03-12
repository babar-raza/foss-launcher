---
name: hallucination-reduce
description: Investigate the current hallucination rate in pipeline output and produce a root-cause fix plan to reduce fabricated API identifiers and unsupported claims to ≤5%.
---

# SKL-207: hallucination-reduce

You are investigating the current hallucination rate and producing a concrete
plan to reduce it to ≤5%.

## Context

Hallucinations are claims or code identifiers in generated output that are not
supported by the source repository. The Understand phase is the most common
source — when it falls back to LLM generation without evidence, it produces
a poisoned API surface that propagates through all downstream phases.

## Required inputs

- `extraction_audit.json` (claim provenance distribution)
- `understanding_bundle.json` (API surface and snippet quality)
- Phase store evaluate artifacts (factual findings per page)
- List of specific hallucinated identifiers (if available from prior run)

## What to do

1. Check `claim_provenance_counts`:
   - What percentage of claims came from `llm_fallback`?
   - What percentage came from `docstring` or `deterministic`?
   - Is `code_evidence_sparse` set to `true`?

2. For each hallucinated identifier (if a list is available):
   - Does it appear in the API surface? If yes, it was incorrectly classified
     by the AST extractor — fix the extractor
   - If not in the API surface, which claim produced it, and what was the
     claim's `claim_source`?

3. Trace where each hallucination entered the pipeline:
   - Was it in a claim produced by `llm_fallback`?
   - Was it in the API surface (incorrect AST extraction)?
   - Was it introduced by the section writer despite correct API surface input?

4. Identify which system controls are currently missing or weak:
   - Is the EVIDENCE ABSENT guard active for lean repos?
   - Is the import allowlist checked at generation time?
   - Does the Evaluate phase check API identifiers against the known surface?

5. Produce a fix plan: root-cause fixes only. Do not propose review-layer
   patches as the primary solution.

## Output you must produce

- Root cause assessment per hallucination type
- Per-phase breakdown of where hallucinations enter and why they persist
- Fix plan targeting root causes (not review-layer patches)
- Measurement strategy: how to verify hallucination rate is decreasing

## Constraints

- Do not solve this with review-layer patching alone
- Do not preserve `llm_fallback` behavior that continues to invent unsupported claims
- Richness tier A does NOT mean factual quality is acceptable
- Higher output volume is not success

## Escalation rules

- If `llm_fallback > 80%` and the repo genuinely has no docstrings or
  examples, stop generation and escalate to the operator — the repo is not
  ready for automated documentation at this quality threshold
- If hallucination persists after fixing Understand, the next suspect is the
  generation prompt (SKL-103 constraints) — review HALLUCINATION PREVENTION
  block in `src/launcher/prompts/section_writer.txt`

## Verification

- Re-run Understand, check `claim_provenance_counts` distribution
- Re-run Evaluate, verify factual_accuracy finding rate has decreased
- Verify previously-hallucinated identifiers no longer appear in output
- Success threshold: `llm_fallback rate < 20% AND factual_accuracy findings
  < 5% of all content blocks`
