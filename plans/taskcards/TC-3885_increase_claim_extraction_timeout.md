---
id: TC-3885
title: "Increase claim extraction read timeout to fix LLM timeout-induced deterministic fallback"
status: In-Progress
priority: High
owner: "agent"
updated: "2026-03-09"
tags: [understand, extract, timeout, claims, content_density]
depends_on: [TC-3884]
allowed_paths:
  - plans/taskcards/TC-3885_increase_claim_extraction_timeout.md
  - src/launcher/workers/understand/extract.py
  - tests/unit/workers/understand/
evidence_required:
  - reports/TC-3885/evidence.md
---

# Taskcard TC-3885 — Increase claim extraction read timeout

## Objective

The `extract_claims_from_repo` LLM call consistently times out after 240 seconds when using
`qwen3-next` with `max_tokens=20_000`. The primary endpoint fails, `gemma3:12b` fallback
returns an empty/invalid response (76 chars, 0 claim_ids), and the deterministic fallback
produces only 33 weak claims. This causes 22 `content_density HIGH` findings across 19 pages,
preventing the A+B rate from reaching ≥50% (GO criterion).

Root cause: at ~50-80 tokens/sec, generating 20K completion tokens requires 250-400 seconds —
exceeding the hard-coded 240s read timeout.

Fix: increase the per-call timeout for claim extraction from 240s to 480s.

## Required spec references

- `specs/03_understand_worker.md` (claim extraction pipeline)

## Scope

### In scope
- Change `timeout=240` to `timeout=480` at the claim extraction LLM call site in `extract.py`

### Out of scope
- Changing `max_tokens` (TC-3884 already set this to 20_000)
- Changing snippet budget or prompt size
- Changing the fallback model or deterministic fallback logic
- Any other workers or LLM call sites

## Inputs

- `src/launcher/workers/understand/extract.py` — `extract_claims_from_repo` function, line 1284

## Outputs

- Fixed extract.py with 480s timeout for claim extraction LLM call

## Allowed paths

- plans/taskcards/TC-3885_increase_claim_extraction_timeout.md
- src/launcher/workers/understand/extract.py
- tests/unit/workers/understand/

### Allowed paths rationale
- extract.py — contains the LLM call with the hardcoded timeout
- tests/ — test coverage for the change

## Implementation steps

### Step 1: Update extract.py timeout

In `extract_claims_from_repo`, change:
```python
timeout=240,  # Claim extraction prompt is large; allow 2× default read timeout
```
to:
```python
timeout=480,  # TC-3885: 20K-token response at 50 tok/s needs ~400s; 480s gives headroom
```

### Step 2: Run tests

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/ -v
```

## Failure modes

### Failure mode 1: 480s timeout still insufficient

**Detection**: Evidence shows `finish_reason=length` or fallback still fires
**Resolution**: Investigate actual throughput of qwen3-next; consider chunking claims
**Gate**: pilot run evidence file shows `endpoint_used=primary` and `finish_reason=stop`

### Failure mode 2: 480s timeout blocks pipeline for too long

**Detection**: Understand phase takes >8 minutes causing user frustration
**Resolution**: Accept as acceptable one-time cost (claim extraction happens once per run)
**Gate**: n/a — this is a UX tradeoff, not a correctness issue

### Failure mode 3: Test suite has timeout-sensitive unit tests

**Detection**: Unit tests fail due to mock timeout value mismatch
**Resolution**: Update mock expectations to match new 480s timeout
**Gate**: pytest

## Task-specific review checklist

1. [ ] `timeout=480` used at claim extraction call site
2. [ ] Comment explains the reasoning (token count × throughput estimate)
3. [ ] No other LLM call sites changed
4. [ ] Tests pass
5. [ ] Evidence file from pilot shows `endpoint_used=primary` and claims > 33
6. [ ] Taskcard marked Done when pilot confirms claims ≥ 50

## Deliverables

1. `src/launcher/workers/understand/extract.py` — timeout increased from 240 to 480

## Acceptance checks

1. [ ] Pilot run evidence `extract-claims-cells.json` shows `endpoint_used=primary`
2. [ ] Pilot run understand_checkpoint shows ≥ 50 public claims
3. [ ] `content_density` HIGHs drop to < 5 in evaluate_checkpoint
4. [ ] All unit tests pass

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Evidence captured: reports/TC-3885/evidence.md

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/ -v
```

## Integration boundary proven

**Upstream**: Scout provides code snippets → claim extraction sends to LLM
**Downstream**: Planner/generate uses claims for content density
**Contract**: ≥50 public claims → content_density HIGHs eliminated → A+B rate improves
