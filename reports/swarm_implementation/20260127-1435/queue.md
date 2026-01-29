# Swarm Queue — <TS> (Asia/Karachi)

Source of truth:
- Taskcards: `plans/taskcards/*.md`
- Status board: `plans/taskcards/STATUS_BOARD.md`
- Contract: `plans/taskcards/00_TASKCARD_CONTRACT.md`

Non-negotiables:
- Implement ONLY taskcards.
- Enforce each taskcard `allowed_paths`.
- Enforce single-writer areas:
  - `src/launch/io/**`, `src/launch/util/**` → TC-200 only
  - `src/launch/models/**` → TC-250 only
  - `src/launch/clients/**` → TC-500 only

Known blocker:
- `OPEN_QUESTIONS.md` → `OQ-BATCH-001` (Batch semantics). Do NOT guess.

---

## Wave 0 — Preflight (Supervisor)
- [ ] Forensics snapshot: `python scripts/forensics_catalog.py`
- [ ] Install: `make install-uv`
- [ ] Gates:
  - [ ] `python tools/validate_swarm_ready.py`
  - [ ] `python scripts/validate_spec_pack.py`
  - [ ] `python scripts/validate_plans.py`
  - [ ] `python tools/validate_taskcards.py`
  - [ ] `python tools/check_markdown_links.py`
- [ ] Record outputs: `reports/swarm_implementation/<TS>/milestones/preflight.md`

---

## Wave 1 — Foundation (mostly sequential)
- [ ] TC-100 — owner: FOUNDATION_AGENT — branch: `feat/TC-100-...`
- [ ] TC-200 — owner: FOUNDATION_AGENT — branch: `feat/TC-200-...`
- [ ] TC-201 — owner: FOUNDATION_AGENT — branch: `feat/TC-201-...`
- [ ] TC-250 — owner: MODELS_AGENT — branch: `feat/TC-250-...`
- [ ] TC-300 — owner: ORCHESTRATOR_AGENT — branch: `feat/TC-300-...`
- [ ] TC-500 — owner: CLIENTS_AGENT — branch: `feat/TC-500-...`

Gate after Wave 1:
- [ ] `python tools/validate_swarm_ready.py`
- [ ] `python -m pytest -q`
- [ ] Save: `reports/swarm_implementation/<TS>/milestones/wave_1_gate_outputs.md`

---

## Wave 2 — Workers (parallel where safe)
### W1
- [ ] TC-401 — owner: W1_AGENT
- [ ] TC-402 — owner: W1_AGENT
- [ ] TC-403 — owner: W1_AGENT
- [ ] TC-404 — owner: W1_AGENT
- [ ] TC-400 — owner: W1_AGENT (integrator)

### W2
- [ ] TC-411 — owner: W2_AGENT
- [ ] TC-412 — owner: W2_AGENT
- [ ] TC-413 — owner: W2_AGENT
- [ ] TC-410 — owner: W2_AGENT (integrator)

### W3
- [ ] TC-421 — owner: W3_AGENT
- [ ] TC-422 — owner: W3_AGENT
- [ ] TC-420 — owner: W3_AGENT (integrator)

### W4–W6
- [ ] TC-430 — owner: W4toW6_AGENT
- [ ] TC-440 — owner: W4toW6_AGENT
- [ ] TC-450 — owner: W4toW6_AGENT

Gate after Wave 2 (same as Wave 1, save wave_2 file)

---

## Wave 3 — Validation + Fix + PR
- [ ] TC-460 — owner: VALIDATION_AGENT
- [ ] TC-570 — owner: VALIDATION_AGENT
- [ ] TC-571 — owner: VALIDATION_AGENT
- [ ] TC-470 — owner: FIXER_AGENT
- [ ] TC-480 — owner: PR_AGENT

Gate after Wave 3

---

## Wave 4 — MCP + CLI + Pilots + Harnesses
- [ ] TC-510 — owner: MCP_AGENT
- [ ] TC-511 — owner: MCP_AGENT
- [ ] TC-512 — owner: MCP_AGENT
- [ ] TC-530 — owner: CLI_AGENT
- [ ] TC-520 — owner: PILOTS_AGENT
- [ ] TC-522 — owner: PILOTS_AGENT
- [ ] TC-523 — owner: PILOTS_AGENT
- [ ] TC-540 — owner: HUGO_AGENT
- [ ] TC-550 — owner: HUGO_AGENT
- [ ] TC-560 — owner: DETERMINISM_AGENT
- [ ] TC-580 — owner: OBS_AGENT
- [ ] TC-590 — owner: SECURITY_AGENT
- [ ] TC-600 — owner: RECOVERY_AGENT

Final gate after Wave 4

---

## Acceptance artifacts per taskcard (mandatory)
For each TC:
- `reports/agents/<agent_id>/<TC-ID>/report.md`
- `reports/agents/<agent_id>/<TC-ID>/self_review.md`
