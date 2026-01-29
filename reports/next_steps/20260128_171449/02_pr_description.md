# Pull Request — TC-300: Complete FOSS Launcher Implementation

## Summary

This PR merges the complete FOSS Launcher implementation from `impl/tc300-wire-orchestrator-20260128` into `main`. This includes the orchestrator graph wiring (TC-300), all 9 worker implementations (W1-W9), client services, MCP server, CLI tooling, validation gates, and comprehensive E2E hardening.

**Branch**: `impl/tc300-wire-orchestrator-20260128` → `main`
**Commits**: 135 commits ahead of main
**Merge Type**: Fast-forward (cleanly ahead, no conflicts)
**Validation**: ✅ All gates pass, 1417 tests pass

## What Changed

### Core Orchestrator (TC-300) ⭐

**Graph Wiring**:
- Implemented LangGraph-based orchestrator with StateGraph
- Wired all 9 workers (W1-W9) as graph nodes
- Implemented proper state transitions and artifact flow per [specs/state-graph.md](../../../specs/state-graph.md)
- Added invoker dispatch logic for worker execution
- Fixed snapshot `old_state` persistence bug
- Implemented W3 automatic insertion when `product_facts` is missing
- Added placeholder SHA resolution in W1 clone logic

**W1 Enhancements** (TC-401/403/404):
- TC-401: Clone repository and resolve SHAs deterministically
- TC-403: Documentation discovery with frontmatter contract scanning
- TC-404: Examples discovery and Hugo site context extraction
- Artifacts: `repo_inventory.json`, `frontmatter_index.json`, `site_context.json`, `hugo_facts.json`

**State Management**:
- Proper `RunState` schema with event log
- Atomic snapshot persistence
- Artifact index tracking
- Event emission for observability

### Workers W2-W9

All workers implemented per their taskcards:
- **W2 FactsBuilder** (TC-410-413): Extract product facts, evidence mapping, contradiction detection
- **W3 SnippetCurator** (TC-420-422): Extract doc/code snippets with tagging
- **W4 IAPlanner** (TC-430): Page planning and IA structure
- **W5 SectionWriter** (TC-440): LLM-based content generation with claim markers
- **W6 LinkerAndPatcher** (TC-450): Apply patches to site worktree
- **W7 Validator** (TC-460): Run all validation gates (schema, links, Hugo smoke, policy)
- **W8 Fixer** (TC-470): Targeted one-issue fix loop
- **W9 PRManager** (TC-480): Commit service integration and PR creation

### Client Services (TC-500)

- LLM provider client (Anthropic API)
- HTTP client with retry/backoff
- Commit service client for PR orchestration
- Telemetry API client

### MCP Server (TC-510-512)

- FastAPI-based MCP server implementation
- Tool handlers for quickstart workflows
- Integration with orchestrator run loop

### CLI & Tooling (TC-530)

- `launch run` — Execute pilot with config
- `launch validate` — Run validation gates
- Runbooks for pilot execution

### Content Processing (TC-540, TC-550)

- Content path resolver (Hugo layout rules)
- Hugo config parser (language matrix extraction)

### Quality Assurance

- **Determinism harness** (TC-560): Golden run verification
- **Validation gates** (TC-570-571): Schema, links, Hugo smoke, policy checks
- **Security** (TC-590): Secret detection, redaction, file scanning
- **Observability** (TC-580): Evidence packaging, reports index, run summaries
- **Resilience** (TC-600): Retry policies, checkpoint/resume, idempotency

### CI & Hardening

- CI enforcement on main (gates + tests must pass)
- E2E dry-run execution validated
- Full spec pack compliance
- 1417 tests with comprehensive coverage

## Risk Notes

**Risk Level**: LOW

**Mitigations**:
- ✅ All validation gates pass
- ✅ 1417 tests pass (10 skipped)
- ✅ Branch cleanly ahead of main (no merge conflicts)
- ✅ Deterministic test framework enforces non-flaky tests
- ✅ Comprehensive evidence artifacts in [reports/](../../../reports/)

**Known Limitations**:
- Mock E2E not yet implemented (Stage 2 follow-up)
- Real pilot requires external LLM/commit-service (offline mode TBD)
- PYTHONHASHSEED warning (should be '0' for determinism, currently None)

## Rollback Notes

If issues arise post-merge, rollback to previous main:

```bash
git checkout main
git reset --hard c8dab0cc1845996f5618a8f0f65489e1b462f06c
git push origin main --force-with-lease
```

## How to Run

### Validate Spec Pack

```bash
make validate
```

Expected: `SPEC PACK VALIDATION OK`

### Run Tests

```bash
make test
```

Expected: 1417+ tests pass

### Run Pilot (requires external services)

```bash
.venv/Scripts/python.exe -m launch run --config pilots/example_pilot.yml
```

**Note**: Real pilot execution requires LLM provider and commit service. Mock E2E implementation is planned in follow-up work.

## Evidence Paths

All implementation evidence is organized in the repository:

### TC-300 Implementation Evidence
- [reports/impl/20260128_162921/](../../../reports/impl/20260128_162921/) — Orchestrator implementation

### Per-Taskcard Evidence
- [reports/agents/ORCHESTRATOR_AGENT/TC-300/](../../../reports/agents/ORCHESTRATOR_AGENT/TC-300/)
- [reports/agents/W1_AGENT/TC-401/](../../../reports/agents/W1_AGENT/TC-401/)
- [reports/agents/W1_AGENT/TC-403/](../../../reports/agents/W1_AGENT/TC-403/)
- [reports/agents/W1_AGENT/TC-404/](../../../reports/agents/W1_AGENT/TC-404/)
- (See [plans/taskcards/STATUS_BOARD.md](../../../plans/taskcards/STATUS_BOARD.md) for full list)

### Validation Outputs
- [reports/next_steps/20260128_171449/pre_merge_gates/validate_output.txt](./pre_merge_gates/validate_output.txt)
- [reports/next_steps/20260128_171449/pre_merge_gates/test_output.txt](./pre_merge_gates/test_output.txt)

### Hardening Evidence
- [reports/bundles/20260128-1849/main_ci_evidence_20260128-1849.tar.gz](../../../reports/bundles/20260128-1849/main_ci_evidence_20260128-1849.tar.gz) — CI enforcement evidence

## Status Board

All 41 taskcards marked as **Done**:
- See [plans/taskcards/STATUS_BOARD.md](../../../plans/taskcards/STATUS_BOARD.md)

## Cleanup Actions

During merge preparation:
- Removed `launcher.zip` (5.3MB local archive) from git tracking
- Added to `.gitignore` to prevent future accidental commits
- Evidence archives in `reports/bundles/` retained (80K, 31K)

## Next Steps (Post-Merge)

1. **Mock E2E Implementation** (Stage 2)
   - Add LLM mock provider
   - Add offline commit service mode
   - Add git clone fixtures
   - Add determinism verification test

2. **Real Pilot Runbook** (Stage 3)
   - Dry-run execution guide
   - Live-run execution guide
   - Environment variable setup

3. **Follow-up Taskcards**
   - TC-580: Evidence bundling enhancements
   - TC-530: Runbook improvements

---

**Generated**: 2026-01-28 17:14:49 UTC
**Merge Plan**: [01_merge_plan.md](01_merge_plan.md)
