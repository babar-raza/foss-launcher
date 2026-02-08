---
id: TC-982
title: "Fix W5 fallback content generation - claim distribution and snippet matching"
status: Complete
priority: High
owner: "Agent-B (Implementation)"
updated: "2026-02-05"
tags: ["w5", "content-quality", "claims", "snippets", "pilot-fix"]
depends_on: ["TC-980"]
allowed_paths:
  - plans/taskcards/TC-982_fix_w5_fallback_content_generation.md
  - src/launch/workers/w5_section_writer/worker.py
  - tests/unit/workers/test_w5_specialized_generators.py
evidence_required:
  - reports/agents/agent_b/TC-982/evidence.md
  - reports/agents/agent_b/TC-982/self_review.md
spec_ref: "fad128dc63faba72bad582ddbc15c19a4c29d684"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# Taskcard TC-982 — Fix W5 Fallback Content Generation

## Objective
Improve W5 SectionWriter's `_generate_fallback_content()` to distribute claims evenly across headings and broaden snippet matching, so non-template pages have actual content paragraphs instead of empty headings.

## Problem Statement
When `llm_client` is None (always the case), `_generate_fallback_content()` reuses the same first 2 claims for every heading (line 932). Snippet matching only triggers for exact heading names (line 941: `"example"`, `"code example"`, `"quickstart"`, `"getting started"`). After TC-980 fixes claim assignment, claims will be available but poorly distributed.

Full investigation: `C:\Users\prora\.claude\plans\deep-weaving-dongarra.md` (RC-4 section)

## Required spec references
- specs/07_section_templates.md (section content requirements)
- specs/08_content_distribution_strategy.md (claim distribution per page)
- specs/09_validation_gates.md (Gate 7 content quality, Gate 14 content distribution)

## Scope

### In scope
- Distribute claims evenly across headings instead of repeating first 2
- Broaden snippet matching to include partial keyword matches
- Ensure Gate 7 content quality minimum length is met
- Update tests

### Out of scope
- LLM-based content generation
- Template-driven page content (handled by token substitution)
- Claim assignment in W4 (TC-980)

## Inputs
- claims list (will be non-empty after TC-980)
- snippets list from snippet_catalog
- required_headings from page_plan

## Outputs
- Modified `_generate_fallback_content()` with even claim distribution
- Broadened snippet matching
- Non-template pages with >100 chars content per heading
- Updated tests

## Allowed paths
- plans/taskcards/TC-982_fix_w5_fallback_content_generation.md
- src/launch/workers/w5_section_writer/worker.py
- tests/unit/workers/test_w5_specialized_generators.py

### Allowed paths rationale
TC-982 modifies W5 fallback content generation and its tests.

## Implementation steps

### Step 1: Fix claim distribution across headings (lines 930-936)
Replace:
```python
heading_claims = claims[:2]
```
With even distribution:
```python
if claims and required_headings:
    claims_per_heading = max(1, len(claims) // len(required_headings))
    start_idx = i * claims_per_heading
    heading_claims = claims[start_idx:start_idx + claims_per_heading]
else:
    heading_claims = []
```
Note: `i` is the heading index from the loop.

### Step 2: Broaden snippet matching (line 941)
Replace:
```python
if snippets and heading.lower() in ["example", "code example", "quickstart", "getting started"]:
```
With:
```python
heading_lower = heading.lower()
snippet_keywords = ["example", "code", "quickstart", "started", "usage", "install", "features", "overview"]
if snippets and any(kw in heading_lower for kw in snippet_keywords):
```

### Step 3: Distribute snippets across headings too
Instead of always using `snippets[0]`, rotate:
```python
snippet_idx = i % len(snippets) if snippets else 0
snippet = snippets[snippet_idx] if snippets else None
```

### Step 4: Ensure minimum content length
After generating content, add a brief section summary if content is very short:
```python
if len(heading_claims) == 0 and purpose:
    lines.append(f"{purpose}")
    lines.append("")
```

### Step 5: Run tests
```bash
.venv/Scripts/python.exe -m pytest tests/unit/workers/test_w5_specialized_generators.py -v
.venv/Scripts/python.exe -m pytest tests/ -x --tb=short
```

## Failure modes

### Failure mode 1: IndexError on claim distribution
**Detection:** IndexError when claims_per_heading * heading_index exceeds claims length
**Resolution:** Use min(start_idx + claims_per_heading, len(claims)) as upper bound
**Spec/Gate:** Gate 7 content quality

### Failure mode 2: Snippet rotation produces wrong language for heading
**Detection:** Python snippet under "Troubleshooting" heading
**Resolution:** Only rotate snippets for code-related headings; skip for non-code headings
**Spec/Gate:** specs/07_section_templates.md

### Failure mode 3: Tests assert exact fallback content format
**Detection:** Test failures comparing old empty-section output
**Resolution:** Update test expectations to include distributed claims
**Spec/Gate:** Gate T test determinism

## Task-specific review checklist
1. [ ] Claims distributed evenly (not all same first 2)
2. [ ] No heading gets more claims than available
3. [ ] Snippet matching broadened to 8+ keywords
4. [ ] Snippets rotated across headings
5. [ ] Minimum content length met (>100 chars)
6. [ ] Claim markers use `[claim: claim_id]` format (Gate 14 compatible)
7. [ ] All tests pass
8. [ ] No IndexError with empty claims or empty headings

## Deliverables
- Modified `src/launch/workers/w5_section_writer/worker.py`
- Updated tests
- Evidence at `reports/agents/agent_b/TC-982/evidence.md`
- Self-review at `reports/agents/agent_b/TC-982/self_review.md`

## Acceptance checks
1. [ ] Non-template pages have >100 chars content body
2. [ ] Different headings get different claims
3. [ ] Snippet appears under at least one heading per page (if snippets available)
4. [ ] GATE_CONTENT_QUALITY_MIN_LENGTH warning eliminated
5. [ ] All tests pass

## Preconditions / dependencies
- TC-980 completed (claims now available in required_claim_ids)
- Python venv activated

## Test plan
1. Unit test: fallback content with 10 claims, 4 headings -> ~2-3 claims per heading
2. Unit test: fallback content with 0 claims -> purpose text as fallback
3. Unit test: snippet matching with "Key Features" heading -> triggers
4. Run pilot to verify non-empty page content

## Self-review
### 12D Checklist
1. **Determinism:** Claim distribution is index-based (deterministic for same input)
2. **Dependencies:** No new dependencies
3. **Documentation:** TC-982 taskcard
4. **Data preservation:** All claims used; just distributed differently
5. **Deliberate design:** Even distribution via integer division; round-robin snippets
6. **Detection:** Gate 7 content quality min length; Gate 14 claim counts
7. **Diagnostics:** W5 logger already logs draft generation
8. **Defensive coding:** Empty claims/headings/snippets all handled
9. **Direct testing:** Unit tests + pilot verification
10. **Deployment safety:** Only affects fallback path (no LLM regression)
11. **Delta tracking:** Modified _generate_fallback_content() only
12. **Downstream impact:** W7 validator sees non-empty content

### Verification results
- [ ] Tests: PASS
- [ ] Overview page: >100 chars content
- [ ] FAQ page: claims under each heading

## E2E verification
```bash
.venv/Scripts/python.exe -m pytest tests/ -x --tb=short
.venv/Scripts/python.exe scripts/run_pilot.py --pilot pilot-aspose-3d-foss-python --output runs/pilot_3d_tc982.json
```

## Integration boundary proven
**Upstream:** W4 provides page_plan with required_claim_ids; W2/W3 provide product_facts and snippet_catalog
**Downstream:** W6 LinkerAndPatcher applies generated drafts to content_preview; W7 validates
**Contract:** Drafts must have valid frontmatter, claim markers in `[claim: id]` format, >100 chars body

## Evidence Location
`reports/agents/agent_b/TC-982/`
