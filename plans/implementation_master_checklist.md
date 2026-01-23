# Implementation Master Checklist

> **Purpose**: Single source of truth for implementation readiness and completion verification.
> **Binding**: All items MUST pass before declaring Phase 8 complete.

## Pre-Flight Readiness

### Repository Structure
- [ ] All directories exist per `specs/18_site_repo_layout.md`
- [ ] All schemas present in `specs/schemas/`
- [ ] Canonical pilot configs exist in `specs/pilots/<pilot_id>/`
- [ ] Template structure follows `specs/07_section_templates.md`

### Tooling
- [ ] `tools/validate_taskcards.py` passes: `python tools/validate_taskcards.py`
- [ ] `tools/validate_platform_layout.py` passes: `python tools/validate_platform_layout.py`
- [ ] `tools/check_markdown_links.py` passes: `python tools/check_markdown_links.py`
- [ ] `tools/validate_swarm_ready.py` passes: `python tools/validate_swarm_ready.py`
- [ ] `scripts/validate_spec_pack.py` passes (requires jsonschema): `python scripts/validate_spec_pack.py`

### Taskcard Coverage
- [ ] All 39 taskcards pass validation
- [ ] Every pipeline stage has implementing taskcard (see `plans/traceability_matrix.md`)
- [ ] All taskcards have `## E2E verification` section with concrete commands
- [ ] All taskcards have `## Integration boundary proven` section

---

## Taskcard Inventory (39 Total)

### Bootstrap (5)
| ID | Title | Status |
|----|-------|--------|
| TC-100 | Bootstrap repo for deterministic implementation | Ready |
| TC-200 | Schemas and IO foundations | Ready |
| TC-201 | Emergency mode flag (allow_manual_edits) | Ready |
| TC-250 | Shared libraries governance | Ready |
| TC-300 | Orchestrator graph wiring and run loop | Ready |

### W1 RepoScout (5)
| ID | Title | Status |
|----|-------|--------|
| TC-400 | W1 RepoScout end-to-end integration | Ready |
| TC-401 | Clone inputs and resolve SHAs | Ready |
| TC-402 | Repo fingerprint and inventory | Ready |
| TC-403 | Frontmatter contract discovery | Ready |
| TC-404 | Hugo config scan and site_context | Ready |

### W2 FactsBuilder (4)
| ID | Title | Status |
|----|-------|--------|
| TC-410 | W2 FactsBuilder end-to-end integration | Ready |
| TC-411 | Extract ProductFacts catalog | Ready |
| TC-412 | Build EvidenceMap | Ready |
| TC-413 | TruthLock compile | Ready |

### W3 SnippetCurator (3)
| ID | Title | Status |
|----|-------|--------|
| TC-420 | W3 SnippetCurator end-to-end integration | Ready |
| TC-421 | Snippet inventory and tagging | Ready |
| TC-422 | Snippet selection rules | Ready |

### Workers W4-W9 (6)
| ID | Title | Status |
|----|-------|--------|
| TC-430 | W4 IAPlanner (page_plan.json) | Ready |
| TC-440 | W5 SectionWriter | Ready |
| TC-450 | W6 LinkerAndPatcher | Ready |
| TC-460 | W7 Validator | Ready |
| TC-470 | W8 Fixer | Ready |
| TC-480 | W9 PRManager | Ready |

### Cross-cutting (7)
| ID | Title | Status |
|----|-------|--------|
| TC-500 | Clients and services | Ready |
| TC-510 | MCP server | Ready |
| TC-511 | MCP quickstart from URL | Ready |
| TC-512 | MCP quickstart from GitHub repo URL | Ready |
| TC-520 | Pilots and regression | Ready |
| TC-522 | Pilot E2E CLI | Ready |
| TC-523 | Pilot E2E MCP | Ready |
| TC-530 | CLI entrypoints and runbooks | Ready |

### Additional Hardening (9)
| ID | Title | Status |
|----|-------|--------|
| TC-540 | Content Path Resolver | Ready |
| TC-550 | Hugo Config Awareness | Ready |
| TC-560 | Determinism harness | Ready |
| TC-570 | Validation gates | Ready |
| TC-571 | Policy gate: No manual edits | Ready |
| TC-580 | Observability and evidence bundle | Ready |
| TC-590 | Security and secrets handling | Ready |
| TC-600 | Failure recovery and backoff | Ready |

---

## Pipeline Stage Coverage

| Stage | Implementing TC | Validating TC |
|-------|-----------------|---------------|
| Ingest/Clone | TC-401, TC-402 | TC-400 |
| Analyze/Facts | TC-411, TC-412, TC-413 | TC-410 |
| Plan | TC-430 | TC-520, TC-522 |
| Template | TC-440 | TC-520, TC-522 |
| Write | TC-440, TC-450 | TC-460 |
| Validate | TC-460, TC-570, TC-571 | TC-522, TC-523 |
| Commit/PR | TC-480 | TC-520 |
| Telemetry | TC-500, TC-580 | TC-510 |
| MCP | TC-510, TC-511, TC-512 | TC-523 |

---

## Gate Commands (Run in Order)

```bash
# 1. Taskcard validation
python tools/validate_taskcards.py

# 2. Platform layout validation
python tools/validate_platform_layout.py

# 3. Markdown links check
python tools/check_markdown_links.py

# 4. Swarm readiness
python tools/validate_swarm_ready.py

# 5. Spec pack validation (requires jsonschema)
python scripts/validate_spec_pack.py

# 6. Generate status board (verification)
python tools/generate_status_board.py
```

---

## Completion Criteria

### All Gates Pass
- [ ] All 5 validation gates exit 0
- [ ] STATUS_BOARD.md generated with 39 taskcards

### Evidence Produced
- [ ] `reports/phase-6_2_to_8_orchestrator/gate_outputs/` contains all gate outputs
- [ ] `plans/taskcards/STATUS_BOARD.md` is up-to-date
- [ ] `plans/traceability_matrix.md` maps all specs to taskcards

### Ready for Swarm
- [ ] No circular dependencies in taskcards
- [ ] All depends_on references resolve to valid taskcard IDs
- [ ] Landing order defined in `plans/taskcards/INDEX.md`

---

## Quick Reference

### Key Files
- Taskcard template: `plans/_templates/taskcard.md`
- Taskcard contract: `plans/taskcards/00_TASKCARD_CONTRACT.md`
- Traceability matrix: `plans/traceability_matrix.md`
- Status board: `plans/taskcards/STATUS_BOARD.md`
- Index: `plans/taskcards/INDEX.md`

### Validation Tools
- `tools/validate_taskcards.py` — Schema and content validation
- `tools/validate_platform_layout.py` — V2 layout compliance
- `tools/check_markdown_links.py` — Link integrity
- `tools/validate_swarm_ready.py` — Dependency graph validation
- `scripts/validate_spec_pack.py` — Schema validation
- `tools/generate_status_board.py` — Status board generation
- `tools/validate_pilots_contract.py` — Pilots canonical path validation
- `tools/validate_mcp_contract.py` — MCP quickstart tools validation

### Report Locations
- Phase reports: `reports/phase-*/`
- Agent reports: `reports/agents/<agent>/<TC-ID>/`
- Templates: `reports/templates/`
