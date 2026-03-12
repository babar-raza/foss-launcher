# CB — Circuit Breaker Intelligent Recovery: Healing Gap Index

**Source taskcard**: TC-3815 (circuit breaker intelligent recovery)
**Self-review date**: 2026-03-07
**Context**: TC-3815 added probe timeout, exponential backoff, and backoff reset to the circuit breaker. Self-review identified 8 concrete gaps ranging from missing integration tests to config validation to observability holes.

## Gap Table

| Gap ID | Description | Severity | Taskcard |
|--------|-------------|----------|----------|
| CB-G1 | No integration test for `llm_provider.py` probe timeout change | High | CB-01 |
| CB-G2 | No config validation — nonsensical values silently misbehave | High | CB-02 |
| CB-G3 | No log on successful probe recovery (silent recovery) | Medium | CB-03 |
| CB-G4 | Probe failure log is `info` level, should be `warning` | Low | CB-03 |
| CB-G5 | Redundant backoff reset in both `record_success()` and `_transition_to(CLOSED)` | Low | CB-04 |
| CB-G6 | Tests access private attributes (`_current_recovery_timeout`, `_probe_failures`) | Medium | CB-04 |
| CB-G7 | Taskcard TC-3815 `allowed_paths` has wrong test path | Low | CB-05 |
| CB-G8 | No spec/doc update for new recovery behavior | Medium | CB-05 |

## Taskcard Summary

| Taskcard | Title | Gaps Fixed |
|----------|-------|------------|
| CB-01 | LLM provider integration test for probe timeout | CB-G1 |
| CB-02 | Circuit breaker config validation | CB-G2 |
| CB-03 | Recovery observability (logs on success + severity fix) | CB-G3, CB-G4 |
| CB-04 | Test quality + redundant reset cleanup | CB-G5, CB-G6 |
| CB-05 | Taskcard + spec alignment | CB-G7, CB-G8 |
