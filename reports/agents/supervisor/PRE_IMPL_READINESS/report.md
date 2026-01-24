# Pre-Implementation Readiness Baseline Report

**Date**: 2026-01-24
**Branch**: `chore/pre_impl_readiness_sweep`
**Supervisor**: Orchestrator Agent

## Executive Summary

Performed baseline validation sweep before implementation start. All automated gates **PASSED**, but identified 3 areas requiring hardening to eliminate ambiguity and prevent future policy drift.

## Baseline Environment

### Virtual Environment
- **Status**: ✅ COMPLIANT
- **Location**: `.venv` at repo root
- **Python**: C:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\.venv
- **Dependencies**: Installed via `uv sync --frozen` (deterministic)

### Validation Results

Executed three canonical validation commands:

#### 1. Spec Pack Validation
```bash
python scripts/validate_spec_pack.py
```
**Result**: `SPEC PACK VALIDATION OK`

#### 2. Plans Validation
```bash
python scripts/validate_plans.py
```
**Result**: `PLANS VALIDATION OK`

#### 3. Swarm Readiness Validation
```bash
python tools/validate_swarm_ready.py
```
**Result**: `SUCCESS: All gates passed - repository is swarm-ready`

**Gates Summary** (19 gates total):
- ✅ Gate 0: Virtual environment policy (.venv enforcement)
- ✅ Gate A1: Spec pack validation
- ✅ Gate A2: Plans validation (zero warnings)
- ✅ Gate B: Taskcard validation + path enforcement
- ✅ Gate C: Status board generation
- ✅ Gate D: Markdown link integrity
- ✅ Gate E: Allowed paths audit (zero violations + zero critical overlaps)
- ✅ Gate F: Platform layout consistency (V2)
- ✅ Gate G: Pilots contract (canonical path consistency)
- ✅ Gate H: MCP contract (quickstart tools in specs)
- ✅ Gate I: Phase report integrity (gate outputs + change logs)
- ✅ Gate J: Pinned refs policy (Guarantee A: no floating branches/tags)
- ✅ Gate K: Supply chain pinning (Guarantee C: frozen deps)
- ✅ Gate L: Secrets hygiene (Guarantee E: secrets scan - STUB)
- ✅ Gate M: No placeholders in production (Guarantee E)
- ✅ Gate N: Network allowlist (Guarantee D: allowlist exists)
- ✅ Gate O: Budget config (Guarantees F/G: budget config - STUB)
- ✅ Gate P: Taskcard version locks (Guarantee K)
- ✅ Gate Q: CI parity (Guarantee H: canonical commands)
- ✅ Gate R: Untrusted code policy (Guarantee J: parse-only - STUB)

**Total Taskcards**: 39 validated, all OK

## Identified Hardening Opportunities

While all gates pass, three areas require hardening to prevent future drift:

### H1: Windows Reserved Filenames (Preventive)
**Status**: ⚠️ NO BLOCKER (NUL file does not exist)
**Action**: Add preventive gate to reject Windows reserved device names

**Evidence**:
- File `NUL` does NOT exist at repo root (verified via `ls`, `git status`, `find`)
- Windows reserves: NUL, CON, PRN, AUX, COM1-9, LPT1-9
- Current gates do not prevent these names from being added

**Required Outcome**:
- Implement `tools/validate_windows_reserved_names.py`
- Integrate into `tools/validate_swarm_ready.py` as Gate S
- Add to CI workflow
- Add tests

### H2: Pinned Refs Policy Inconsistency (Spec ↔ Schema Alignment)
**Status**: ⚠️ AMBIGUITY DETECTED
**Action**: Align spec/schema/gate/configs for Guarantee A (pinned refs)

**Evidence**:
- Spec specs/34_strict_compliance_guarantees.md:56 mentions `allow_floating_refs: true` as exception
- Schema `specs/schemas/run_config.schema.json` does NOT contain `allow_floating_refs` field
- Gate J passes (but may not enforce the exception semantics correctly)
- Pilot configs use `launch_tier: minimal` but spec text is ambiguous on whether this implies floating refs allowed

**Required Outcome**:
1. Decide: Should `allow_floating_refs` field exist in schema?
2. If YES: Add to schema + update gate logic
3. If NO: Remove from spec text + clarify how dev/pilot configs are distinguished
4. Ensure gate behavior matches spec wording exactly
5. Update pilot configs to align with final decision
6. Add tests for edge cases

### H3: specs/README.md Navigation Drift
**Status**: ⚠️ STALE NAVIGATION
**Action**: Update specs/README.md to list all existing specs

**Evidence**:
Actual spec files vs README.md listing:
- ✅ Listed: 00-27 (most), 29-31
- ❌ Missing: 00_environment_policy.md
- ❌ Missing: 28_coordination_and_handoffs.md
- ❌ Missing: 32_platform_aware_content_layout.md
- ❌ Missing: 33_public_url_mapping.md
- ❌ Missing: 34_strict_compliance_guarantees.md

**Required Outcome**:
- Add missing specs to navigation table
- Verify link integrity passes after update
- Consider adding a gate to detect future drift (compare ls output vs README)

## Next Steps

Following the orchestration protocol:

1. **Delegate** H1, H2, H3 to specialized agents (hygiene-agent, policy-agent, docs-agent)
2. **Review** each agent's evidence report + self-review (12D rubric)
3. **Re-validate** via `python tools/validate_swarm_ready.py` after each fix
4. **Publish** orchestrator master review with GO/NO-GO decision
5. **If GO**: Begin implementation per `plans/00_orchestrator_master_prompt.md`

## Full Validation Output

See persisted file for complete gate output:
`C:\Users\prora\.claude\projects\c--Users-prora-OneDrive-Documents-GitHub-foss-launcher\c59f0a60-d213-4972-a44f-e207f7c9b12b\tool-results\toolu_01VDmo3wH8QxiThM7MSFA34E.txt`

---

**Supervisor Notes**:
- Zero tolerance for ambiguity applies
- Each hardening task requires micro-taskcard if outside existing allowed_paths
- Evidence bundle mandatory for each task
- Write-fence discipline enforced
