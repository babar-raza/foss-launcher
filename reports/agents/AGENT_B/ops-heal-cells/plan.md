# Agent B — Ops Heal Cells: Plan
<!-- Session: jiggly-puzzling-mccarthy | 2026-02-27T06:50Z -->

## Scope
Operational validation of triage→heal loop on Cells pilot. No code changes.

## Target
Run: r_20260226T220459Z_launch_pilot-aspose-cells-foss-python_c47529c_default_b5399032

## Steps
1. Pre-flight (snapshot BEFORE_HEAL)
2. Run triage → capture output
3. Run heal --dry-run → capture heal_plan.json
4. Run heal --live → capture console + heal_plan.json
5. Before/after gate comparison
6. HEAL event extraction from events.ndjson
7. Post-heal triage
8. Write reports/ops/heal_iteration_20260227_<ts>.md

## Assumptions
- Run locked: NO (verified)
- Prior heal: NO (verified)
- 3 failing gates: gate_4, gate_17, gate_kb_howto_structure (14 errors, 213 warns)
- Recursion limit fixed (TC-2960): YES

## Acceptance
- heal_plan.json written with >=1 step
- evidence report written
- before/after counts documented
