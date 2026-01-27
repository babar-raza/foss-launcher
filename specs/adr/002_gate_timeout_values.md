# ADR-002: Validation Gate Timeout Values

**Status**: Proposed (requires load testing)
**Date**: 2026-01-27
**Context**: Pre-implementation decision for specs/09_validation_gates.md:84-120

## Decision

Profile-based gate timeout values:
- **local**: 30 seconds
- **ci**: 60 seconds
- **prod**: 120 seconds

## Rationale

- **Local profile**: Fast feedback for developers, short timeout acceptable (code changes expected)
- **CI profile**: Medium timeout for CI runners with variable performance
- **Prod profile**: Long timeout for complex sites with thousands of pages

**Alternatives considered**:
- Uniform timeout (60s): Rejected, too slow for local, too fast for prod
- Per-gate timeouts: Rejected for complexity, profile-based is simpler

## Validation Plan

- Load testing (TC-560): Test with sites of varying sizes (10 pages, 100 pages, 1000 pages)
- Measure: 95th percentile gate execution time
- Target: 95th percentile < 50% of timeout value (safety margin)
- Tuning: If 95th percentile exceeds 50% of timeout, increase timeout values

## Consequences

- Gates may timeout on very large sites in local profile (acceptable trade-off for fast feedback)
- Gates may be slower than necessary in prod profile (acceptable for safety)
