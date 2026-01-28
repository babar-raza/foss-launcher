# ADR-001: MCP Inference Confidence Threshold (80%)

**Status**: Proposed (requires pilot validation)
**Date**: 2026-01-27
**Context**: Pre-implementation decision for specs/24_mcp_tool_schemas.md:227-231

## Decision

The `launch_start_run_from_github_repo_url` MCP tool uses an 80% confidence threshold for automatic inference of `product_slug` and `target_platform`.

## Rationale

- **Conservative threshold**: Reduces risk of incorrect inference leading to wrong site generation
- **Trade-off**: Prefers asking user for clarification (ambiguous response) over proceeding with low-confidence inference
- **Alternatives considered**:
  - 90%: Too strict, would reject many valid repos with minor ambiguity
  - 70%: Too permissive, higher risk of incorrect inference
  - 80%: Balanced middle ground

## Validation Plan

- Pilot phase (TC-520): Test with 20+ representative repos
- Measure: False positive rate (incorrect inference) and false negative rate (unnecessary ambiguity)
- Target: <5% false positive rate
- Tuning: If false positive rate >5%, increase threshold to 85% or 90%

## Consequences

- May require manual clarification for repos with ambiguous signals (e.g., multi-product repos)
- Threshold may be overridden via optional `confidence_threshold` parameter in future versions
