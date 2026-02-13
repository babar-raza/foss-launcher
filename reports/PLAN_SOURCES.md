# Plan Sources Resolution — Content Quality Hardening Round 1

**Generated**: 2026-02-12T10:20:00Z
**Protocol**: Orchestrator Protocol Step 0 (Plan Sources Resolution)

---

## Primary Plan Source

**Path**: `C:\Users\prora\.claude\plans\virtual-scribbling-sifakis.md`
**Type**: Comprehensive V2-aware content quality plan
**Status**: READY FOR EXECUTION

**Why Selected**:
- Contains both Round 1 (TC-1401–1408) and Round 2 (TC-1501–1505)
- V2 Platform-Aware Layout compatibility already integrated
- Clear dependency graph and regression contract
- 8 taskcards addressing hallucinated APIs, code-as-claims, and structural issues
- Ready for autonomous swarm execution

**Key Sections**:
1. **Round 1** (8 taskcards, PENDING EXECUTION):
   - TC-1401: W2 Code-Grounded Claim Generation
   - TC-1402: W2 LLM Claim Classification
   - TC-1403: W5 Snippet-Anchored Generation
   - TC-1404: W5 Deterministic Post-Processing
   - TC-1405: W5.5 LLM Semantic Checks
   - TC-1406: W5.5 Factual Verifier Agent
   - TC-1407: W5.5 Deterministic Defense-in-Depth
   - TC-1408: Pilot Verification (final gate)

2. **Round 2** (5 taskcards, DEFERRED):
   - Will execute AFTER Round 1 completes
   - Addresses 16 content publication quality issues
   - V2 URL compatibility already integrated

---

## Execution Status

**Current Phase**: Round 1 Execution (TC-1401 through TC-1408)
**Baseline**: 2983 tests passed, 9 skipped, 0 failures
**Target**: Both pilots PASS with CQ≥5, TA≥4, U≥4

---

## Round 1 Issue Coverage

| Issue | TC-1401 | TC-1402 | TC-1403 | TC-1404 | TC-1405 | TC-1406 | TC-1407 |
|-------|---------|---------|---------|---------|---------|---------|---------|
| 1. Code-as-claims | | filter | | | S3 detect | | |
| 2. Claim markers | | | | fix | | | |
| 3. Hallucinated APIs | ground truth | | snippet-anchor | | S1 detect | rewrite | |
| 4. Collapsed FM | | | | fix | | | CQ-11 detect |
| 5. Unclosed fences | | | | fix | | | |
| 6. Wrong licensing | | | prompt | | S2 detect | rewrite | TA-14 + fix |
| 7. Placeholders | | | | fix + regex | | | |
| 8. Internal details | | filter | | | S3 detect | rewrite | |

---

## Dependency Graph

```
TC-1401 (W2 code claims)  ──┐
TC-1402 (W2 classification)  │  TC-1403 (W5 snippet-anchored) ──→ TC-1408 (pilot verify)
TC-1404 (W5 post-process)  ──┤                                         ↑
TC-1405 (W5.5 LLM checks)  ──┤  TC-1406 (W5.5 factual verifier)  ────┘
TC-1407 (W5.5 deterministic) ┘
```

**Parallel group A** (no dependencies): TC-1401, TC-1402, TC-1404, TC-1405, TC-1407
**Sequential B**: TC-1403 depends on TC-1401
**Sequential C**: TC-1406 depends on TC-1405
**Final**: TC-1408 depends on ALL

---

## Evidence Commands

```bash
# Baseline test suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x

# 3D pilot verification
PYTHONHASHSEED=0 .venv/Scripts/python.exe scripts/run_pilot.py --pilot pilot-aspose-3d-foss-python --output tmp/verify_3d_r1

# Note pilot verification
PYTHONHASHSEED=0 .venv/Scripts/python.exe scripts/run_pilot.py --pilot pilot-aspose-note-foss-python --output tmp/verify_note_r1

# Taskcard validation
python tools/validate_taskcards.py
```

---

## Next Steps

1. ✅ Plan sources resolved → Round 1 ready
2. ⏳ Create TASK_BACKLOG with 8 workstreams
3. ⏳ Spawn agents for parallel group A (5 agents)
4. ⏳ Monitor self-reviews, route if <4/5
5. ⏳ Execute sequential groups B & C
6. ⏳ Final pilot verification (TC-1408)
