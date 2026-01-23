#!/usr/bin/env python3
"""
Add E2E verification and Integration boundary sections to all taskcards.
"""

import re
from pathlib import Path

# Map taskcard ID to appropriate E2E verification and integration boundary content
TASKCARD_E2E_DATA = {
    "TC-100": {
        "e2e_command": "python -m pytest tests/unit/ -v --tb=short\npython -m launch.cli --version",
        "artifacts": [
            "src/launch/__init__.py (package marker)",
            "pyproject.toml (valid package config)",
        ],
        "success": ["Exit code 0", "Package version displayed"],
        "upstream": "None (bootstrap task)",
        "downstream": "TC-200 (schemas), TC-300 (orchestrator)",
        "contracts": "pyproject.toml validates against PEP 517/518",
    },
    "TC-200": {
        "e2e_command": "python -m pytest tests/unit/io/ -v\npython -c \"from launch.io.run_config import load_and_validate_run_config; print('OK')\"",
        "artifacts": [
            "specs/schemas/run_config.schema.json (validates against JSON Schema draft)",
            "specs/schemas/page_plan.schema.json",
        ],
        "success": ["All schema files compile", "Example configs validate"],
        "upstream": "TC-100 (package structure)",
        "downstream": "All workers consume schemas via TC-200 I/O layer",
        "contracts": "run_config.schema.json, page_plan.schema.json, validation_report.schema.json",
    },
    "TC-201": {
        "e2e_command": "python -c \"from launch.io.run_config import load_and_validate_run_config; cfg = {'allow_manual_edits': True}; print('OK')\"",
        "artifacts": [
            "src/launch/io/run_config.py (allow_manual_edits field)",
        ],
        "success": ["allow_manual_edits flag recognized", "Policy gate respects flag"],
        "upstream": "TC-200 (run_config schema)",
        "downstream": "TC-571 (policy gate), TC-450 (patcher)",
        "contracts": "run_config.schema.json includes allow_manual_edits boolean",
    },
    "TC-250": {
        "e2e_command": "python -m pytest tests/unit/models/ -v",
        "artifacts": [
            "src/launch/models/product_facts.py",
            "src/launch/models/evidence_map.py",
        ],
        "success": ["Model validation tests pass", "Single-writer violations detected by linter"],
        "upstream": "TC-200 (base schemas)",
        "downstream": "TC-411..TC-413 (facts workers), TC-430..TC-440 (planning workers)",
        "contracts": "ProductFacts, EvidenceMap, TruthLock model schemas",
    },
    "TC-300": {
        "e2e_command": "python -m launch.cli status --run-id test_run\npython -c \"from launch.orchestrator import run_loop; print('OK')\"",
        "artifacts": [
            "src/launch/orchestrator/__init__.py",
            "src/launch/orchestrator/run_loop.py",
        ],
        "success": ["State machine initializes", "Event emission works"],
        "upstream": "TC-200 (schemas), TC-100 (package)",
        "downstream": "All workers (W1-W9), TC-510 (MCP), TC-530 (CLI)",
        "contracts": "specs/11_state_and_events.md state transitions",
    },
    "TC-400": {
        "e2e_command": "python -m launch.workers.w1_repo_scout --config specs/pilots/pilot-aspose-3d-foss-python/run_config.pinned.yaml --dry-run",
        "artifacts": [
            "artifacts/repo_profile.json (schema: repo_profile.schema.json)",
            "artifacts/site_context.json",
        ],
        "success": ["repo_profile.json validates", "site_context.json validates"],
        "upstream": "TC-300 (orchestrator dispatches W1)",
        "downstream": "TC-410 (W2 FactsBuilder), TC-420 (W3 Snippets)",
        "contracts": "repo_profile.schema.json, site_context.schema.json",
    },
    "TC-401": {
        "e2e_command": "python -m launch.workers.w1_repo_scout.clone --repo https://github.com/aspose-3d/Aspose.3D-for-Python-via-.NET --ref main --dry-run",
        "artifacts": [
            "workdir/repos/<sha>/ (cloned repo)",
            "artifacts/resolved_refs.json",
        ],
        "success": ["Clone completes", "SHA deterministically resolved"],
        "upstream": "TC-300 (RunConfig with github_repo_url)",
        "downstream": "TC-402 (fingerprint), TC-403 (frontmatter), TC-404 (Hugo scan)",
        "contracts": "specs/02_repo_ingestion.md clone contract",
    },
    "TC-402": {
        "e2e_command": "python -m launch.workers.w1_repo_scout.fingerprint --workdir workdir/repos/<sha>",
        "artifacts": [
            "artifacts/repo_fingerprint.json",
            "artifacts/file_inventory.json",
        ],
        "success": ["Fingerprint is deterministic (run twice, compare hashes)", "Inventory sorted deterministically"],
        "upstream": "TC-401 (cloned repo)",
        "downstream": "TC-411 (facts extraction uses inventory)",
        "contracts": "repo_profile.schema.json fingerprint fields",
    },
    "TC-403": {
        "e2e_command": "python -m launch.workers.w1_repo_scout.frontmatter --site-dir workdir/site",
        "artifacts": [
            "artifacts/frontmatter_contracts.json",
        ],
        "success": ["Frontmatter patterns discovered", "Output deterministic"],
        "upstream": "TC-401 (site repo cloned)",
        "downstream": "TC-440 (SectionWriter uses frontmatter contracts)",
        "contracts": "specs/examples/frontmatter_models.md patterns",
    },
    "TC-404": {
        "e2e_command": "python -m launch.workers.w1_repo_scout.hugo_scan --site-dir workdir/site",
        "artifacts": [
            "artifacts/site_context.json (schema: site_context.schema.json)",
            "artifacts/build_matrix.json",
        ],
        "success": ["Hugo config parsed", "Layout mode detected per section"],
        "upstream": "TC-401 (site repo cloned)",
        "downstream": "TC-540 (path resolver), TC-550 (Hugo awareness)",
        "contracts": "specs/31_hugo_config_awareness.md detection rules",
    },
    "TC-410": {
        "e2e_command": "python -m launch.workers.w2_facts_builder --config specs/pilots/pilot-aspose-3d-foss-python/run_config.pinned.yaml",
        "artifacts": [
            "artifacts/product_facts.json (schema: product_facts.schema.json)",
            "artifacts/evidence_map.json",
            "artifacts/truth_lock.json",
        ],
        "success": ["ProductFacts validates", "EvidenceMap links all claims"],
        "upstream": "TC-400 (repo_profile)",
        "downstream": "TC-430 (IAPlanner), TC-460 (Validator TruthLock gate)",
        "contracts": "product_facts.schema.json, evidence_map.schema.json, truth_lock.schema.json",
    },
    "TC-411": {
        "e2e_command": "python -m launch.workers.w2_facts_builder.extract --repo-profile artifacts/repo_profile.json",
        "artifacts": [
            "artifacts/product_facts.json",
        ],
        "success": ["ProductFacts deterministic", "No hallucinated facts"],
        "upstream": "TC-402 (repo_profile with inventory)",
        "downstream": "TC-412 (evidence linking)",
        "contracts": "product_facts.schema.json",
    },
    "TC-412": {
        "e2e_command": "python -m launch.workers.w2_facts_builder.evidence --product-facts artifacts/product_facts.json",
        "artifacts": [
            "artifacts/evidence_map.json",
        ],
        "success": ["All facts have source evidence", "Links are valid file:line references"],
        "upstream": "TC-411 (product_facts)",
        "downstream": "TC-413 (TruthLock compile)",
        "contracts": "evidence_map.schema.json",
    },
    "TC-413": {
        "e2e_command": "python -m launch.workers.w2_facts_builder.truth_lock --evidence-map artifacts/evidence_map.json",
        "artifacts": [
            "artifacts/truth_lock.json",
        ],
        "success": ["All claims compiled with evidence", "No orphaned claims"],
        "upstream": "TC-412 (evidence_map)",
        "downstream": "TC-460 (TruthLock validation gate)",
        "contracts": "truth_lock.schema.json",
    },
    "TC-420": {
        "e2e_command": "python -m launch.workers.w3_snippet_curator --config specs/pilots/pilot-aspose-3d-foss-python/run_config.pinned.yaml",
        "artifacts": [
            "artifacts/snippet_catalog.json (schema: snippet_catalog.schema.json)",
        ],
        "success": ["Snippets inventoried", "Tags assigned deterministically"],
        "upstream": "TC-400 (repo_profile with file inventory)",
        "downstream": "TC-430 (IAPlanner selects snippets)",
        "contracts": "snippet_catalog.schema.json",
    },
    "TC-421": {
        "e2e_command": "python -m launch.workers.w3_snippet_curator.inventory --repo-dir workdir/repos/<sha>",
        "artifacts": [
            "artifacts/snippet_inventory.json",
        ],
        "success": ["All code examples found", "Deterministic ordering"],
        "upstream": "TC-401 (cloned repo)",
        "downstream": "TC-422 (selection rules)",
        "contracts": "snippet_catalog.schema.json inventory fields",
    },
    "TC-422": {
        "e2e_command": "python -m launch.workers.w3_snippet_curator.select --inventory artifacts/snippet_inventory.json",
        "artifacts": [
            "artifacts/snippet_catalog.json",
        ],
        "success": ["Selection rules applied", "Output deterministic"],
        "upstream": "TC-421 (snippet inventory)",
        "downstream": "TC-430 (IAPlanner)",
        "contracts": "specs/05_example_curation.md selection rules",
    },
    "TC-430": {
        "e2e_command": "python -m launch.workers.w4_ia_planner --config specs/pilots/pilot-aspose-3d-foss-python/run_config.pinned.yaml",
        "artifacts": [
            "artifacts/page_plan.json (schema: page_plan.schema.json)",
        ],
        "success": ["page_plan.json validates", "All sections planned"],
        "upstream": "TC-410 (facts), TC-420 (snippets), TC-404 (site_context)",
        "downstream": "TC-440 (SectionWriter)",
        "contracts": "page_plan.schema.json",
    },
    "TC-440": {
        "e2e_command": "python -m launch.workers.w5_section_writer --page-plan artifacts/page_plan.json",
        "artifacts": [
            "artifacts/draft_sections/*.md (with claim markers)",
        ],
        "success": ["All planned sections written", "Claim markers present"],
        "upstream": "TC-430 (page_plan)",
        "downstream": "TC-450 (LinkerAndPatcher)",
        "contracts": "specs/23_claim_markers.md marker format",
    },
    "TC-450": {
        "e2e_command": "python -m launch.workers.w6_linker_patcher --draft-dir artifacts/draft_sections --site-dir workdir/site",
        "artifacts": [
            "artifacts/patch_bundle.json",
            "workdir/site/content/**/*.md (patched files)",
        ],
        "success": ["Patches apply cleanly", "No out-of-fence writes"],
        "upstream": "TC-440 (draft sections), TC-540 (path resolver)",
        "downstream": "TC-460 (Validator)",
        "contracts": "specs/08_patch_engine.md patch format",
    },
    "TC-460": {
        "e2e_command": "python -m launch.workers.w7_validator --site-dir workdir/site --config specs/pilots/pilot-aspose-3d-foss-python/run_config.pinned.yaml",
        "artifacts": [
            "artifacts/validation_report.json (schema: validation_report.schema.json)",
        ],
        "success": ["All gates run", "Report validates against schema"],
        "upstream": "TC-450 (patched site)",
        "downstream": "TC-470 (Fixer), TC-480 (PRManager)",
        "contracts": "validation_report.schema.json, specs/09_validation_gates.md",
    },
    "TC-470": {
        "e2e_command": "python -m launch.workers.w8_fixer --validation-report artifacts/validation_report.json --site-dir workdir/site",
        "artifacts": [
            "artifacts/fix_log.json",
            "artifacts/validation_report.json (updated)",
        ],
        "success": ["Issue fixed or marked unfixable", "Re-validation runs"],
        "upstream": "TC-460 (validation_report with issues)",
        "downstream": "TC-460 (re-validation), TC-480 (PRManager)",
        "contracts": "specs/09_validation_gates.md fix loop rules",
    },
    "TC-480": {
        "e2e_command": "python -m launch.workers.w9_pr_manager --site-dir workdir/site --config specs/pilots/pilot-aspose-3d-foss-python/run_config.pinned.yaml --dry-run",
        "artifacts": [
            "artifacts/pr_request.json",
        ],
        "success": ["PR payload generated", "Commit message follows template"],
        "upstream": "TC-460 (validation_report.ok=true)",
        "downstream": "Commit service (external)",
        "contracts": "specs/12_pr_and_release.md, specs/17_github_commit_service.md",
    },
    "TC-500": {
        "e2e_command": "python -m pytest tests/unit/clients/ -v\npython -c \"from launch.clients.telemetry import TelemetryClient; print('OK')\"",
        "artifacts": [
            "src/launch/clients/telemetry.py",
            "src/launch/clients/commit_service.py",
            "src/launch/clients/llm_provider.py",
        ],
        "success": ["Client initialization works", "Fallback behavior tested"],
        "upstream": "TC-200 (config schemas)",
        "downstream": "All workers (emit telemetry), TC-480 (commit service)",
        "contracts": "specs/16_local_telemetry_api.md, specs/17_github_commit_service.md",
    },
    "TC-510": {
        "e2e_command": "python -m launch.mcp.server --port 8787 &\ncurl http://localhost:8787/health",
        "artifacts": [
            "src/launch/mcp/server.py",
            "src/launch/mcp/tools/*.py",
        ],
        "success": ["Server starts", "Health endpoint responds", "Tools registered"],
        "upstream": "TC-300 (orchestrator run_loop)",
        "downstream": "MCP clients (Claude, etc.)",
        "contracts": "specs/14_mcp_endpoints.md, specs/24_mcp_tool_schemas.md",
    },
    "TC-520": {
        "e2e_command": "python scripts/run_pilot.py --pilot pilot-aspose-3d-foss-python --dry-run",
        "artifacts": [
            "artifacts/pilot_run_report.json",
            "Compare: expected_page_plan.json vs actual page_plan.json",
        ],
        "success": ["Pilot completes", "Output matches expected artifacts"],
        "upstream": "TC-300 (full pipeline)",
        "downstream": "Regression harness (CI)",
        "contracts": "specs/13_pilots.md determinism requirements",
    },
    "TC-530": {
        "e2e_command": "python -m launch.cli --help\npython -m launch.cli run --config specs/pilots/pilot-aspose-3d-foss-python/run_config.pinned.yaml --dry-run",
        "artifacts": [
            "src/launch/cli/__main__.py",
        ],
        "success": ["CLI help displays", "Dry-run completes"],
        "upstream": "TC-300 (orchestrator)",
        "downstream": "Human operators, CI pipelines",
        "contracts": "CLI argument spec in docs/",
    },
    "TC-540": {
        "e2e_command": "python -c \"from launch.workers.path_resolver import resolve_content_path; print(resolve_content_path('docs', 'cells', 'en', 'python', 'v2'))\"",
        "artifacts": [
            "src/launch/workers/path_resolver.py",
        ],
        "success": ["V1 paths resolve correctly", "V2 paths include platform segment", "Products use /{locale}/{platform}/"],
        "upstream": "TC-404 (site_context with layout_mode)",
        "downstream": "TC-450 (patcher uses resolved paths)",
        "contracts": "specs/32_platform_aware_content_layout.md path rules",
    },
    "TC-550": {
        "e2e_command": "python -c \"from launch.workers.hugo_awareness import parse_hugo_config; print('OK')\"",
        "artifacts": [
            "src/launch/workers/hugo_awareness.py",
        ],
        "success": ["Hugo config parsed", "Build constraints extracted"],
        "upstream": "TC-404 (Hugo scan)",
        "downstream": "TC-570 (Hugo smoke gate)",
        "contracts": "specs/31_hugo_config_awareness.md",
    },
    "TC-560": {
        "e2e_command": "python scripts/determinism_harness.py --pilot pilot-aspose-3d-foss-python --runs 2",
        "artifacts": [
            "artifacts/determinism_report.json",
        ],
        "success": ["Two runs produce identical outputs", "Hash comparison passes"],
        "upstream": "TC-520 (pilot infrastructure)",
        "downstream": "CI golden-run comparison",
        "contracts": "specs/10_determinism_and_caching.md requirements",
    },
    "TC-570": {
        "e2e_command": "python -m launch.validators --site-dir workdir/site --gates schema,links,hugo,platform",
        "artifacts": [
            "artifacts/gate_results/*.json",
        ],
        "success": ["All specified gates run", "Results captured per gate"],
        "upstream": "TC-460 (validator orchestration)",
        "downstream": "TC-470 (fixer consumes gate failures)",
        "contracts": "specs/09_validation_gates.md gate definitions",
    },
    "TC-571": {
        "e2e_command": "python -m launch.validators.policy_gate --site-dir workdir/site --config specs/pilots/pilot-aspose-3d-foss-python/run_config.pinned.yaml",
        "artifacts": [
            "artifacts/policy_gate_result.json",
        ],
        "success": ["Manual edit detection works", "allow_manual_edits flag respected"],
        "upstream": "TC-460 (validator), TC-201 (emergency mode flag)",
        "downstream": "TC-470 (fixer cannot fix policy violations)",
        "contracts": "plans/policies/no_manual_content_edits.md",
    },
    "TC-580": {
        "e2e_command": "python -m launch.observability.package --run-id test_run --output evidence_bundle.zip",
        "artifacts": [
            "evidence_bundle.zip (contains all run artifacts)",
            "artifacts/reports_index.json",
        ],
        "success": ["Bundle created", "All artifacts included"],
        "upstream": "TC-300 (run completion)",
        "downstream": "Audit trail, debugging",
        "contracts": "specs/11_state_and_events.md evidence requirements",
    },
    "TC-590": {
        "e2e_command": "python -m launch.security.scan --config specs/pilots/pilot-aspose-3d-foss-python/run_config.pinned.yaml",
        "artifacts": [
            "artifacts/security_scan.json",
        ],
        "success": ["No secrets in output", "Redaction applied"],
        "upstream": "TC-200 (config with secret env vars)",
        "downstream": "TC-480 (PR manager redacts sensitive data)",
        "contracts": "specs/security scanning rules",
    },
    "TC-600": {
        "e2e_command": "python -m launch.recovery.test_backoff --simulate-failure",
        "artifacts": [
            "artifacts/recovery_log.json",
        ],
        "success": ["Retry logic triggered", "Exponential backoff applied", "State resumable"],
        "upstream": "TC-300 (orchestrator state management)",
        "downstream": "All workers (can be retried)",
        "contracts": "specs/10_determinism_and_caching.md idempotency rules",
    },
}


def add_sections_to_taskcard(filepath: Path, tc_id: str) -> bool:
    """Add E2E verification and Integration boundary sections to a taskcard."""
    content = filepath.read_text(encoding='utf-8')

    # Check if sections already exist
    if "## E2E verification" in content and "## Integration boundary proven" in content:
        return False  # Already has sections

    data = TASKCARD_E2E_DATA.get(tc_id)
    if not data:
        print(f"Warning: No E2E data for {tc_id}")
        return False

    # Build the sections
    e2e_section = f"""## E2E verification
**Concrete command(s) to run:**
```bash
{data['e2e_command']}
```

**Expected artifacts:**
"""
    for artifact in data['artifacts']:
        e2e_section += f"- {artifact}\n"

    e2e_section += "\n**Success criteria:**\n"
    for criterion in data['success']:
        e2e_section += f"- [ ] {criterion}\n"

    e2e_section += "\n> If E2E harness not yet implemented, this defines the stub contract for TC-520/522/523.\n"

    integration_section = f"""## Integration boundary proven
What upstream/downstream wiring was validated:
- Upstream: {data['upstream']}
- Downstream: {data['downstream']}
- Contracts: {data['contracts']}
"""

    # Find insertion point (before ## Deliverables)
    if "## Deliverables" in content:
        content = content.replace(
            "## Deliverables",
            f"{e2e_section}\n{integration_section}\n## Deliverables"
        )
    elif "## Acceptance" in content:
        content = content.replace(
            "## Acceptance",
            f"{e2e_section}\n{integration_section}\n## Acceptance"
        )
    else:
        # Append at end
        content += f"\n{e2e_section}\n{integration_section}\n"

    filepath.write_text(content, encoding='utf-8')
    return True


def main():
    repo_root = Path(__file__).parent.parent
    taskcards_dir = repo_root / "plans" / "taskcards"

    updated = 0
    for tc_file in sorted(taskcards_dir.glob("TC-*.md")):
        # Extract TC ID from filename
        match = re.match(r"(TC-\d+)", tc_file.stem)
        if not match:
            continue

        tc_id = match.group(1)
        if add_sections_to_taskcard(tc_file, tc_id):
            print(f"Updated: {tc_file.name}")
            updated += 1
        else:
            print(f"Skipped: {tc_file.name}")

    print(f"\nTotal updated: {updated}")


if __name__ == "__main__":
    main()
