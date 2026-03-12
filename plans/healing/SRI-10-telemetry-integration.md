# SRI-10: Add Telemetry/Observability to Intake Commands

**Status:** Done
**Gap linkage:** Intake port self-review, Dimension 9 (Observability)
**Role:** Observability
**Scope:** Wire intake CLI commands into v2's telemetry system

---

## Problem

Intake CLI commands (scan, classify, generate, onboard) produce no telemetry events. V2 has a telemetry system (`src/launcher/clients/telemetry.py`, `src/launcher/state/event_log.py`) but intake operations are invisible to it. In production, operators need to know: how many repos were scanned, how many configs generated, what errors occurred.

## Acceptance Checks

- [x] `intake scan` emits event with org count, repo count, elapsed time
- [x] `intake onboard` emits event with batch stats (scanned, eligible, generated, skipped)
- [x] Events use v2's `EventLog` or `TelemetryClient` (not ad-hoc logging)
- [x] Telemetry is opt-in (no crash if telemetry endpoint unavailable)
- [x] Unit test mocks telemetry client and verifies event shape

## Deliverables

1. Updated CLI commands with telemetry calls
2. Event schema definition (or reuse existing event types)
3. Test proving events are emitted

## Hard Rules

- Telemetry failure must not block CLI operation
- Use existing v2 telemetry infrastructure, don't create parallel system
- No PII in events (repo URLs are public, so acceptable)

## Review Dimensions

- Event completeness
- Failure isolation
- Schema consistency with existing events

## Runbook

1. Read `src/launcher/clients/telemetry.py` and `src/launcher/models/event.py`
2. Define intake event types (scan_complete, onboard_complete)
3. Add telemetry calls to CLI commands
4. Add try/except around telemetry (graceful degradation)
5. Test with mock telemetry client
