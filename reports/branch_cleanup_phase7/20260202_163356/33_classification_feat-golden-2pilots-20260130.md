# Branch Classification: feat/golden-2pilots-20260130

## Overview
- **Commits**: 12
- **Files Changed**: 708
- **Branch Type**: **MIXED** (src, tests, templates, docs, specs)

## File Distribution

### Source Code (src/)
- `src/launch/workers/w4_ia_planner/worker.py` - W4 IA planner changes
- `src/launch/workers/w1_repo_scout/clone.py` - Clone handling
- `src/launch/workers/_git/clone_helpers.py` - Git clone helper functions
- `src/launch/workers/_git/repo_url_validator.py` - Repository URL validation
- `src/launch/workers/_shared/policy_check.py` - Policy validation
- `src/launch/mcp/server.py` - MCP server
- `src/launch/mcp/tools.py` - MCP tools
- `src/launch/models/run_config.py` - Run configuration model

### Tests (tests/)
- `tests/e2e/test_tc_903_vfv.py` - E2E VFV test
- `tests/unit/mcp/test_tc_510_server_setup.py` - MCP setup test
- `tests/unit/workers/test_tc_400_repo_scout.py` - Repo scout test
- `tests/unit/workers/test_tc_401_clone.py` - Clone test
- `tests/unit/workers/test_tc_430_ia_planner.py` - IA planner test
- `tests/unit/workers/test_tc_902_w4_template_enumeration.py` - W4 template enumeration test
- `tests/unit/workers/w4/test_tc_925_config_loading.py` - Config loading test
- `tests/unit/tools/test_audit_taskcard_evidence.py` - Audit test
- `tests/unit/tools/test_validate_taskcard_readiness.py` - Validation test

### Templates (specs/templates/)
**MASSIVE template expansion** - 564 template files added:
- 3d product templates (blog, docs, kb, products, reference)
- note product templates (blog, docs, kb, products, reference)
- Templates for multiple domains: blog.aspose.org, docs.aspose.org, kb.aspose.org, products.aspose.org, reference.aspose.org

### Documentation & Specs
- `docs/AI_GOVERNANCE_QUICK_REFERENCE.md` - AI governance docs
- `docs/_audit/` - System audit files (4 files)
- `specs/` - System specs, rulesets, schemas
- `specs/pilots/pilot-aspose-3d-foss-python/run_config.pinned.yaml` - Pilot config
- `specs/rulesets/ruleset.v1.yaml` - Ruleset definitions
- `specs/schemas/` - JSON schemas (ruleset, run_config)

### Taskcards (plans/taskcards/)
34 taskcard files including:
- TC-700: Template packs 3d/note
- TC-701: W4 family-aware paths
- TC-702: Validation report determinism
- TC-703: Pilot VFV harness
- TC-900-925: Various fixes and enhancements

### Reports & Evidence
- `reports/agents/` - Agent execution reports (multiple agents)
- `reports/branch_cleanup_phase2/` - Branch cleanup evidence
- `reports/work_summary_8d/` - 8-day work summary
- `artifacts/` - Pilot execution artifacts (11 JSON files)

### Configuration & Hooks
- `.claude_code_rules` - Claude Code configuration
- `.github/workflows/ai-governance-check.yml` - GitHub Actions workflow
- `.gitignore` - Git ignore rules
- `config/network_allowlist.yaml` - Network allowlist config
- `hooks/` - Git hooks (4 files)

### Scripts & Tools
- `scripts/run_multi_pilot_vfv.py` - Multi-pilot VFV runner
- `scripts/run_pilot_vfv.py` - Single pilot VFV runner
- `tools/audit_taskcard_evidence.py` - Audit tool
- `tools/validate_swarm_ready.py` - Swarm validation
- `tools/validate_taskcard_readiness.py` - Taskcard validation

## Key Themes

1. **W4 (IA Planner) Fixes**: Multiple fixes to W4 path handling, run_config loading, and inventory handling
2. **Golden Process Foundation**: Template packs and VFV harness for golden capture
3. **FOSS Repo Clone Workarounds**: Fixes for git clone --branch issues with SHA refs
4. **Taskcard Formalization**: TC-700-703 taskcards and evidence promotion to reports/
5. **MCP Server Changes**: Lazy imports to avoid pywintypes dependency

## W4-Related Changes
- Path construction (family + subdomain)
- `load_and_validate_run_config` signature fixes
- Inventory handling (list vs dict)
- Run config object handling
- Template enumeration with quotas

## Integration Risk Assessment
- **High complexity**: 708 files, 12 commits
- **Multiple subsystems**: Workers, MCP, tests, templates, docs
- **Template expansion**: 564 new template files (likely high merge conflict risk if templates exist in main)
- **Core worker changes**: W4 ia_planner modifications
- **Test coverage**: Includes unit and e2e tests
