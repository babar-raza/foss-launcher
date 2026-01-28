# ADR-003: Contradiction Resolution Priority Difference Threshold (≥2)

**Status**: Proposed
**Date**: 2026-01-27
**Context**: Pre-implementation decision for specs/03_product_facts_and_evidence.md:138-146

## Decision

Contradictions are auto-resolved when priority difference ≥ 2. Priority difference of 1 requires manual review.

## Rationale

- **Evidence priority hierarchy**: Priority 1 (Manifests) > Priority 2 (Code) > ... > Priority 7 (README)
- **Threshold rationale**: Priority difference of 2 means evidence sources are 2+ levels apart (e.g., Manifest vs. Docs), suggesting clear quality difference
- **Manual review for priority_diff == 1**: Adjacent priorities (e.g., Code vs. Tests) may have similar reliability, worth manual review

**Example**:
- Manifest (priority 1) contradicts README (priority 7): priority_diff = 6 → auto-resolve (use Manifest)
- Code (priority 2) contradicts Tests (priority 3): priority_diff = 1 → manual review

## Alternatives Considered

- Threshold ≥ 1: Too aggressive, would auto-resolve close priority differences
- Threshold ≥ 3: Too conservative, would require manual review too often

## Validation Plan

- Pilot phase (TC-520): Review all manual review cases to verify threshold appropriateness
- If >20% of manual reviews are "obvious" (one source clearly better), reduce threshold to ≥1
- If <5% of auto-resolutions are incorrect, threshold is appropriate

## Consequences

- Some contradictions require manual review (acceptable for quality)
- Threshold may be tuned based on pilot data
