# Baseline Inventory — Phase 6.2 to 8 Orchestrator

Generated: 2026-01-23

## Gate Status (Baseline)

| Gate | Description | Status |
|------|-------------|--------|
| A1 | Spec pack validation | FAIL (env issue: jsonschema not in system Python) |
| A2 | Plans validation | PASS |
| B | Taskcard validation + path enforcement | PASS |
| C | Status board generation | PASS |
| D | Markdown link integrity | PASS |
| E | Allowed paths audit | PASS |
| F | Platform layout consistency (V2) | PASS |

**Note:** Gate A1 failure is due to `jsonschema` package being installed in user site-packages, not system Python. All repo-internal validations pass.

---

## Templates Inventory

### Location
`specs/templates/`

### V1 Templates (Legacy - No Platform Segment)

| Subdomain | Path Pattern |
|-----------|--------------|
| docs | `specs/templates/docs.aspose.org/<family>/<locale>/<section>/` |
| kb | `specs/templates/kb.aspose.org/<family>/<locale>/<converter>/` |
| products | `specs/templates/products.aspose.org/<family>/<locale>/<converter>/` |
| reference | `specs/templates/reference.aspose.org/<family>/<locale>/` |
| blog | `specs/templates/blog.aspose.org/<family>/<post_slug>/` |

### V2 Templates (Platform-Aware)

| Subdomain | Path Pattern |
|-----------|--------------|
| docs | `specs/templates/docs.aspose.org/<family>/<locale>/__PLATFORM__/<section>/` |
| kb | `specs/templates/kb.aspose.org/<family>/<locale>/__PLATFORM__/<topic>/` |
| products | `specs/templates/products.aspose.org/<family>/<locale>/__PLATFORM__/<converter>/` |
| reference | `specs/templates/reference.aspose.org/<family>/<locale>/__PLATFORM__/` |
| blog | `specs/templates/blog.aspose.org/<family>/__PLATFORM__/<post_slug>/` |

### Template Docs
- `specs/templates/README.md` — binding contract for V1/V2 templates
- `specs/07_section_templates.md` — template selection rules

---

## Config Templates Inventory

### Location
`configs/`

### Product Config Template
- Path: `configs/products/_template.run_config.yaml`
- Contains: `target_platform`, `layout_mode` fields (V2 ready)

### Pilot Config Template
- Path: `configs/pilots/_template.pinned.run_config.yaml`
- Contains: `target_platform`, `layout_mode` fields (V2 ready)

---

## Pilots Inventory

### Location
`specs/pilots/`

### Pilots List
| Pilot | Config | Expected Artifacts |
|-------|--------|-------------------|
| pilot-aspose-3d-foss-python | `run_config.pinned.yaml` | `expected_page_plan.json`, `expected_validation_report.json` |
| pilot-aspose-note-foss-python | `run_config.pinned.yaml` | `expected_page_plan.json`, `expected_validation_report.json` |

---

## MCP Specs/Tools Inventory

### Specs
- `specs/14_mcp_endpoints.md` — minimum MCP tool surface
- `specs/24_mcp_tool_schemas.md` — authoritative tool schemas and error contract

### Tools Defined
- `launch_start_run`
- `launch_get_status`
- `launch_get_artifact`
- `launch_validate`
- `launch_fix_next`
- `launch_resume`
- `launch_cancel`
- `launch_open_pr`
- `launch_list_runs`

**Missing:** `launch_quickstart_public_repo` (URL-only quick launch)

---

## Plans/Prompts Inventory

### Plans
- `plans/00_orchestrator_master_prompt.md` — swarm orchestrator instructions
- `plans/README.md` — plans index
- `plans/traceability_matrix.md` — spec-to-taskcard mapping
- `plans/acceptance_test_matrix.md` — acceptance test mapping
- `plans/swarm_coordination_playbook.md` — coordination rules

### Prompts
- **No prompts folder exists** — needs to be created in Sub-Phase 6

### Templates
- `plans/_templates/taskcard.md` — taskcard template (missing E2E verification section)

---

## Taskcards Inventory

### Location
`plans/taskcards/`

### Count
35 taskcards total

### Taskcard Groups
| Group | IDs | Description |
|-------|-----|-------------|
| Bootstrap | TC-100, TC-200, TC-201, TC-250, TC-300 | Repo setup and foundations |
| W1 RepoScout | TC-400, TC-401, TC-402, TC-403, TC-404 | Repository ingestion |
| W2 Facts | TC-410, TC-411, TC-412, TC-413 | Facts and evidence |
| W3 Snippets | TC-420, TC-421, TC-422 | Snippet curation |
| W4-W9 Workers | TC-430..TC-480 | Core worker pipeline |
| Cross-cutting | TC-500, TC-510, TC-520, TC-530 | Services and pilots |
| Hardening | TC-540..TC-600 | Additional critical hardening |

### Missing Taskcards (to be created)
- TC-511 — MCP quickstart from URL
- TC-522 — Pilot E2E CLI
- TC-523 — Pilot E2E MCP

---

## Validation Tools

| Tool | Purpose |
|------|---------|
| `tools/validate_swarm_ready.py` | Master validation runner |
| `tools/validate_taskcards.py` | Taskcard schema validation |
| `tools/validate_platform_layout.py` | V2 platform layout checks |
| `tools/check_markdown_links.py` | Internal link integrity |
| `tools/audit_allowed_paths.py` | Path overlap detection |
| `tools/generate_status_board.py` | Status board generation |

---

## Identified Gaps (Pre-Hardening)

1. **Prompt Library**: Does not exist (`plans/prompts/`)
2. **Master Checklist**: Does not exist (`plans/implementation_master_checklist.md`)
3. **E2E Verification Sections**: Missing from taskcard template and most taskcards
4. **MCP Quick Launch**: Tool not specified in MCP specs
5. **Pilot E2E Taskcards**: TC-522, TC-523 do not exist
