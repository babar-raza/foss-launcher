---
name: understand-audit
description: Audit Understand-phase output for a FOSS repo — verifies claim provenance, API surface accuracy, snippet validity, and import path consistency before generation begins.
---

# SKL-201: understand-audit

You are performing a structured audit of the Understand-phase output for a
specific FOSS product repository.

## Context

The Understand worker (Phase A Scout → Phase B Extract → Phase C Plan) has
produced an understanding bundle. Before downstream generation runs, you must
verify that the evidence in this bundle is accurate, complete, and strong
enough to support A-grade documentation output.

This audit is authoritative. Do not proceed with generation if this audit
finds critical weaknesses.

## Required inputs

You must have access to all of the following before starting:
- Cloned repository on disk
- `understanding_bundle.json` for the current run
- `extraction_audit.json` (if present)
- `richness_tier` field value and `claim_provenance_counts` from the bundle

## What to do

1. Read `claim_provenance_counts`. If `llm_fallback / total > 50%`, this is a
   critical finding. If `> 80%`, this is a blocker — do not proceed with
   generation until root cause is addressed.

2. Open the cloned repository. For each claim in the bundle:
   - Verify the `evidence.source_file` exists on disk
   - Verify the quoted snippet is present at the stated line range
   - Verify the claim text is supported by what is actually in the source

3. Inspect `api_surface.class_briefs`. For each class entry:
   - Check that the class exists in the actual source code
   - Check that listed methods are real (not getter properties listed as
     callable methods)
   - Check that the canonical import in snippets matches the actual module path

4. Check for contradictions across artifacts:
   - Import path in snippets vs `canonical_import` in frontmatter
   - Class names in IR files vs actual repo class names
   - Entity descriptions that mix two different classes

5. Record findings at the artifact + field level. General comments are
   insufficient.

## Output you must produce

- Detailed assessment: what exists, what is missing, what is weak, what is
  unreliable — item by item, not a summary
- Every finding must name the specific artifact, field, and line reference
- Concrete improvement tasks broken into smallest practical units
- Ordered task list to reach A-grade Understand output

## Constraints

- Do not declare "good enough" based on claim count alone
- `llm_fallback > 50%` is always a finding requiring a concrete fix plan
- Contradictions between artifacts must be called out explicitly
- Every proposed fix must name the smallest code change that addresses it

## Escalation rules

- If `llm_fallback > 80%` and the repo has no docstrings, stop and flag the
  repo as unsuitable for automated generation; escalate to human to confirm scope
- If the API surface returns zero public classes, stop and check whether the
  AST extractor supports the target language before re-running
- If after two full Understand re-runs the provenance distribution does not
  improve, invoke SKL-207 (hallucination-reduce) for root-cause analysis

## Verification

After fixes are applied and Understand is re-run:
- `claim_provenance_counts.docstring` count must increase
- `llm_fallback` count must decrease
- `api_surface.class_briefs` entries must reflect actual AST output
- No evidence anchor must point to a non-existent source file
