# Gate Outputs

This file records all gate check outputs throughout the merge process.

## Baseline Gates
(After merging gpt-reviewed into staging - already up to date)

### Staging Branch
`integrate/main-e2e-20260128-0837` at commit `c8dab0cc`

### Gate: validate_swarm_ready.py
**Status**: ✅ ALL GATES PASSED

All 20 gates passed:
- Gate 0: Virtual environment policy (.venv enforcement)
- Gate A1: Spec pack validation
- Gate A2: Plans validation (zero warnings)
- Gate B: Taskcard validation + path enforcement
- Gate C: Status board generation
- Gate D: Markdown link integrity
- Gate E: Allowed paths audit (zero violations + zero critical overlaps)
- Gate F: Platform layout consistency (V2)
- Gate G: Pilots contract (canonical path consistency)
- Gate H: MCP contract (quickstart tools in specs)
- Gate I: Phase report integrity (gate outputs + change logs)
- Gate J: Pinned refs policy (Guarantee A: no floating branches/tags)
- Gate K: Supply chain pinning (Guarantee C: frozen deps)
- Gate L: Secrets hygiene (Guarantee E: secrets scan)
- Gate M: No placeholders in production (Guarantee E)
- Gate N: Network allowlist (Guarantee D: allowlist exists)
- Gate O: Budget config (Guarantees F/G: budget config)
- Gate P: Taskcard version locks (Guarantee K)
- Gate Q: CI parity (Guarantee H: canonical commands)
- Gate R: Untrusted code policy (Guarantee J: parse-only)
- Gate S: Windows reserved names prevention

### Gate: pytest
**Status**: ✅ PASSED (with PYTHONHASHSEED=0)

All 157 tests passed.

## Wave Gates
(After each wave merge)

## Final Main Gates
(After landing staging into main)

---

(Outputs will be added as gates are executed)
