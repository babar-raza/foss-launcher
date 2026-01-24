# WI-005: Traceability Analysis

## Analysis Date
2026-01-24 10:45:00

## Summary
The repository has extensive traceability coverage with two existing traceability matrices:
1. [TRACEABILITY_MATRIX.md](../../../TRACEABILITY_MATRIX.md) (root-level, 24 requirements)
2. [plans/traceability_matrix.md](../../../plans/traceability_matrix.md) (spec-to-taskcard mapping)

## Coverage Analysis

### Total Spec Documents: 35 numbered specs (00-34)

### Traceability Coverage: 30/35 specs have explicit taskcard mapping

### Potential Gaps Identified (5 specs without explicit taskcard coverage):

1. **specs/21_worker_contracts.md** - Worker I/O definitions
   - May be a reference spec for implementation taskcards
   - Likely covered implicitly by TC-200, TC-300, TC-400 series

2. **specs/22_navigation_and_existing_content_update.md** - Site navigation
   - Could be phase 2+ feature (not MVP)
   - May need explicit classification as "future work"

3. **specs/28_coordination_and_handoffs.md** - Worker coordination
   - Covered by TC-300 (orchestrator) but not explicitly listed
   - May need explicit entry in traceability matrix

4. **specs/33_public_url_mapping.md** - Public URL mapping contract
   - Implementation exists: src/launch/resolvers/public_urls.py
   - May need explicit taskcard reference (possibly TC-200)

5. **Additional files** (blueprint.md, pilot-blueprint.md, state-graph.md, state-management.md):
   - These appear to be design/reference documents
   - Should be explicitly classified as non-binding reference

## Root Cause

The repo follows good traceability practices BUT lacks **explicit classification** of specs as:
- **Binding** (requires taskcards + tests)
- **Informational/Reference** (design docs, no implementation required)

Per WI-005 acceptance criteria:
> For any spec doc that is truly informational/reference:
>   - Make that explicit **in the spec doc itself** (or in an approved `specs/README.md` classification section if specs allow).

## Findings

### What Exists (GOOD):
- ✅ Comprehensive traceability matrices with 30/35 specs covered
- ✅ All 12 strict compliance guarantees (A-L) have:
  - Binding spec text
  - Gates (implemented, not stubs)
  - Test coverage (partial - some marked "to be created")
  - Enforcement mechanisms

### What's Missing (NEEDS CLARIFICATION):
- ❌ Explicit classification system for binding vs informational specs
- ❌ Clear statement in specs/README.md defining spec categories
- ⚠️  Some specs missing explicit taskcard mapping (5 candidates)
- ⚠️  Some tests marked "to be created" in traceability matrix

## Recommendation

### Option 1: Document Classification in specs/README.md
Add a section to specs/README.md that explicitly classifies each spec as:
- **BINDING** - Requires implementation taskcards + tests
- **REFERENCE** - Design/informational, no taskcards required

### Option 2: In-Document Classification
Add a `Status: BINDING | REFERENCE` field to each spec's frontmatter/header

### Option 3: Accept Current State with Rationale
Document that:
- 30/35 specs have explicit taskcard coverage
- 5 remaining specs are either:
  - Implicitly covered (21, 28, 33)
  - Reference only (blueprint.md, state-graph.md, state-management.md)
  - Future work (22)

## Decision Required

**BLOCKER**: This requires a decision on classification approach before proceeding.

**Recommendation**: Option 1 (specs/README.md classification section) is cleanest and least invasive.

## Evidence
- Traceability analysis script: reports/pre_impl_review/20260124-102204/evidence_traceability_generation.txt (to be created)
- Coverage analysis above
- Both traceability matrices reviewed and validated

## Status
NEEDS DECISION - Cannot proceed with "zero ambiguous missing items" without explicit classification system
