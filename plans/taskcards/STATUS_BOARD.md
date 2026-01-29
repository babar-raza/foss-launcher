# Taskcard Status Board

> **Auto-generated** by `tools/generate_status_board.py`
> **Do not edit manually** - all changes will be overwritten
> **Single source of truth**: taskcard YAML frontmatter

<<<<<<< HEAD
Last generated: 2026-02-02 13:23:57 UTC
=======
Last generated: 2026-01-29 21:46:09 UTC
>>>>>>> c666914 (feat: Phase N0 taskcard hygiene + golden capture prep (TC-633))

## Status Values

- **Draft**: Taskcard under development, not ready for implementation
- **Ready**: Taskcard complete and ready for agent pickup
- **In-Progress**: Currently being implemented by an agent
- **Blocked**: Cannot proceed due to dependencies or unresolved issues
- **Done**: Implementation complete and accepted

## Taskcards

| ID | Title | Status | Owner | Depends On | Allowed Paths | Evidence Required | Updated |
|---|---|---|---|---|---|---|---|
| TC-100 | Bootstrap repo for deterministic implementation | Done | FOUNDATION_AGENT | - | 6 paths | 4 items | 2026-01-27 |
| TC-200 | Schemas and IO foundations | Done | FOUNDATION_AGENT | TC-100 | 6 paths | 4 items | 2026-01-27 |
| TC-201 | Emergency mode flag (allow_manual_edits) and policy plumbing | Done | FOUNDATION_AGENT | TC-200 | 5 paths | reports/agents/<agent>/TC-201/report.md, reports/agents/<agent>/TC-201/self_review.md | 2026-01-27 |
| TC-250 | Shared libraries governance and single-writer enforcement | Done | MODELS_AGENT | TC-200 | src/launch/models/**, tests/unit/models/**, reports/agents/**/TC-250/** | reports/agents/<agent>/TC-250/report.md, reports/agents/<agent>/TC-250/self_review.md, Test output: model validation tests | 2026-01-28 |
| TC-300 | Orchestrator graph wiring and run loop | Done | ORCHESTRATOR_AGENT | TC-200 | 5 paths | reports/agents/<agent>/TC-300/report.md, reports/agents/<agent>/TC-300/self_review.md | 2026-01-28 |
| TC-400 | W1 RepoScout (clone + fingerprint + Hugo/site discovery) | Done | W1_AGENT | TC-401, TC-402, TC-403, TC-404 | 5 paths | reports/agents/<agent>/TC-400/report.md, reports/agents/<agent>/TC-400/self_review.md | 2026-01-28 |
| TC-401 | W1.1 Clone inputs and resolve SHAs deterministically | Done | W1_AGENT | TC-200, TC-300 | 4 paths | reports/agents/<agent>/TC-401/report.md, reports/agents/<agent>/TC-401/self_review.md | 2026-01-28 |
| TC-402 | W1.2 Deterministic repo fingerprinting and inventory | Done | W1_AGENT | TC-200, TC-300 | src/launch/workers/w1_repo_scout/fingerprint.py, tests/unit/workers/test_tc_402_fingerprint.py, reports/agents/**/TC-402/** | reports/agents/<agent>/TC-402/report.md, reports/agents/<agent>/TC-402/self_review.md | 2026-01-28 |
| TC-403 | W1.3 Frontmatter contract discovery (deterministic) | Done | W1_AGENT | TC-200, TC-300 | src/launch/workers/w1_repo_scout/frontmatter.py, tests/unit/workers/test_tc_403_frontmatter.py, reports/agents/**/TC-403/** | reports/agents/<agent>/TC-403/report.md, reports/agents/<agent>/TC-403/self_review.md | 2026-01-28 |
| TC-404 | W1.4 Hugo config scan and site_context build matrix inference | Done | W1_AGENT | TC-200, TC-300 | src/launch/workers/w1_repo_scout/hugo_scan.py, tests/unit/workers/test_tc_404_hugo_scan.py, reports/agents/**/TC-404/** | reports/agents/<agent>/TC-404/report.md, reports/agents/<agent>/TC-404/self_review.md | 2026-01-28 |
| TC-410 | W2 FactsBuilder (ProductFacts + EvidenceMap) | Done | W2_AGENT | TC-411, TC-412, TC-413 | 4 paths | reports/agents/<agent>/TC-410/report.md, reports/agents/<agent>/TC-410/self_review.md | 2026-01-28 |
| TC-411 | W2.1 Extract ProductFacts catalog deterministically | Done | W2_AGENT | TC-400 | 4 paths | reports/agents/<agent>/TC-411/report.md, reports/agents/<agent>/TC-411/self_review.md | 2026-01-28 |
| TC-412 | W2.2 Build EvidenceMap linking facts and sources | Done | W2_AGENT | TC-400, TC-411 | src/launch/workers/w2_facts_builder/map_evidence.py, tests/unit/workers/test_tc_412_map_evidence.py, reports/agents/**/TC-412/** | reports/agents/<agent>/TC-412/report.md, reports/agents/<agent>/TC-412/self_review.md | 2026-01-28 |
| TC-413 | W2.3 Detect contradictions and compute similarity scores | Done | W2_AGENT | TC-411, TC-412 | src/launch/workers/w2_facts_builder/detect_contradictions.py, tests/unit/workers/test_tc_413_detect_contradictions.py, reports/agents/**/TC-413/** | reports/agents/<agent>/TC-413/report.md, reports/agents/<agent>/TC-413/self_review.md | 2026-01-28 |
| TC-420 | W3 SnippetCurator (snippet_catalog.json) | Done | W3_AGENT | TC-421, TC-422 | 5 paths | reports/agents/<agent>/TC-420/report.md, reports/agents/<agent>/TC-420/self_review.md | 2026-01-28 |
| TC-421 | W3.1 Snippet inventory and tagging | Done | W3_AGENT | TC-400 | src/launch/workers/w3_snippet_curator/extract_doc_snippets.py, tests/unit/workers/test_tc_421_extract_doc_snippets.py, reports/agents/**/TC-421/** | reports/agents/<agent>/TC-421/report.md, reports/agents/<agent>/TC-421/self_review.md | 2026-01-28 |
| TC-422 | W3.2 Extract code snippets from examples | Done | W3_AGENT | TC-400, TC-410 | src/launch/workers/w3_snippet_curator/extract_code_snippets.py, tests/unit/workers/test_tc_422_extract_code_snippets.py, reports/agents/**/TC-422/** | reports/agents/<agent>/TC-422/report.md, reports/agents/<agent>/TC-422/self_review.md | 2026-01-28 |
| TC-430 | W4 IAPlanner (page_plan.json) | Done | W4_AGENT | TC-410, TC-420 | 4 paths | reports/agents/<agent>/TC-430/report.md, reports/agents/<agent>/TC-430/self_review.md | 2026-01-28 |
| TC-440 | W5 SectionWriter (draft Markdown with claim markers) | Done | W5_AGENT | TC-430 | 4 paths | reports/agents/<agent>/TC-440/report.md, reports/agents/<agent>/TC-440/self_review.md | 2026-01-28 |
| TC-450 | W6 LinkerAndPatcher (PatchBundle + apply to site worktree) | Done | W6_AGENT | TC-440 | 4 paths | reports/agents/<agent>/TC-450/report.md, reports/agents/<agent>/TC-450/self_review.md | 2026-01-28 |
| TC-460 | W7 Validator (all gates → validation_report.json) | Done | W7_AGENT | TC-450 | 4 paths | reports/agents/<agent>/TC-460/report.md, reports/agents/<agent>/TC-460/self_review.md | 2026-01-28 |
| TC-470 | W8 Fixer (targeted one-issue fix loop) | Done | W8_AGENT | TC-460 | 4 paths | reports/agents/<agent>/TC-470/report.md, reports/agents/<agent>/TC-470/self_review.md | 2026-01-28 |
| TC-480 | W9 PRManager (commit service → PR) | Done | W9_AGENT | TC-470 | src/launch/workers/w9_pr_manager/**, tests/unit/workers/test_tc_480_pr_manager.py, reports/agents/**/TC-480/** | reports/agents/<agent>/TC-480/report.md, reports/agents/<agent>/TC-480/self_review.md | 2026-01-28 |
| TC-500 | Clients & Services (telemetry, commit service, LLM provider) | Done | CLIENTS_AGENT | TC-200, TC-300 | src/launch/clients/**, tests/unit/clients/test_tc_500_services.py, reports/agents/**/TC-500/** | reports/agents/<agent>/TC-500/report.md, reports/agents/<agent>/TC-500/self_review.md | 2026-01-28 |
| TC-510 | MCP server | Done | MCP_AGENT | TC-300 | 4 paths | reports/agents/<agent>/TC-510/report.md, reports/agents/<agent>/TC-510/self_review.md | 2026-01-28 |
| TC-511 | MCP quickstart from product URL (launch_start_run_from_product_url) | Done | MCP_AGENT | TC-510, TC-540 | src/launch/mcp/tools/start_run_from_product_url.py, tests/unit/mcp/test_tc_511_start_run_from_product_url.py, reports/agents/**/TC-511/** | reports/agents/<agent>/TC-511/report.md, reports/agents/<agent>/TC-511/self_review.md, Test output: MCP tool responds with run_id for valid product URL | 2026-01-28 |
| TC-512 | MCP quickstart from GitHub repo URL (launch_start_run_from_github_repo_url) | Done | MCP_AGENT | TC-510, TC-540, TC-401 | 5 paths | 4 items | 2026-01-28 |
| TC-520 | Pilots and regression harness | Done | TELEMETRY_AGENT | TC-300, TC-460 | 6 paths | reports/agents/<agent>/TC-520/report.md, reports/agents/<agent>/TC-520/self_review.md | 2026-01-28 |
| TC-522 | Pilot E2E CLI execution and determinism verification | Done | TELEMETRY_AGENT | TC-520, TC-530, TC-560 | scripts/run_pilot_e2e.py, tests/e2e/test_tc_522_pilot_cli.py, reports/agents/**/TC-522/** | reports/agents/<agent>/TC-522/report.md, reports/agents/<agent>/TC-522/self_review.md, artifacts/pilot_e2e_cli_report.json | 2026-01-28 |
| TC-523 | Pilot E2E MCP execution and determinism verification | Done | TELEMETRY_AGENT | TC-520, TC-510, TC-560 | scripts/run_pilot_e2e_mcp.py, tests/e2e/test_tc_523_pilot_mcp.py, reports/agents/**/TC-523/** | reports/agents/<agent>/TC-523/report.md, reports/agents/<agent>/TC-523/self_review.md, artifacts/pilot_e2e_mcp_report.json | 2026-01-28 |
| TC-530 | CLI entrypoints and runbooks | Done | CLI_AGENT | TC-300, TC-460 | 6 paths | reports/agents/<agent>/TC-530/report.md, reports/agents/<agent>/TC-530/self_review.md | 2026-01-28 |
| TC-540 | Content Path Resolver (Hugo content layout + blog localization rules) | Done | CONTENT_AGENT | TC-400 | 5 paths | reports/agents/<agent>/TC-540/report.md, reports/agents/<agent>/TC-540/self_review.md | 2026-01-28 |
| TC-550 | Hugo Config Awareness (derive build constraints + language matrix) | Done | CONTENT_AGENT | TC-400 | src/launch/content/hugo_config.py, tests/unit/content/test_tc_550_hugo_config.py, reports/agents/CONTENT_AGENT/TC-550/** | reports/agents/CONTENT_AGENT/TC-550/report.md, reports/agents/CONTENT_AGENT/TC-550/self_review.md | 2026-01-28 |
| TC-560 | Determinism and Reproducibility Harness (golden runs) | Done | DETERMINISM_AGENT | TC-200, TC-300 | 5 paths | reports/agents/<agent>/TC-560/report.md, reports/agents/<agent>/TC-560/self_review.md | 2026-01-28 |
| TC-570 | Validation Gates (schema, links, Hugo smoke, policy) | Done | W7_AGENT | TC-460, TC-550 | 8 paths | reports/agents/<agent>/TC-570/report.md, reports/agents/<agent>/TC-570/self_review.md | 2026-01-28 |
| TC-571 | W7.x Policy gate: No manual content edits | Done | W7_AGENT | TC-460, TC-201 | src/launch/validators/policy_gate.py, tests/unit/validators/test_tc_571_policy_gate.py, reports/agents/**/TC-571/** | reports/agents/<agent>/TC-571/report.md, reports/agents/<agent>/TC-571/self_review.md | 2026-01-28 |
| TC-580 | Observability and Evidence Packaging (reports index + evidence zip) | Done | OBSERVABILITY_AGENT | TC-300, TC-460 | 4 paths | reports/agents/<agent>/TC-580/report.md, reports/agents/<agent>/TC-580/self_review.md | 2026-01-28 |
| TC-590 | Security and Secrets Handling (redaction + lightweight scan) | Done | SECURITY_AGENT | TC-300 | 5 paths | reports/agents/<agent>/TC-590/report.md, reports/agents/<agent>/TC-590/self_review.md | 2026-01-28 |
| TC-600 | Failure Recovery and Backoff (retry, resume, idempotency) | Done | RESILIENCE_AGENT | TC-300 | 4 paths | reports/agents/<agent>/TC-600/report.md, reports/agents/<agent>/TC-600/self_review.md | 2026-01-28 |
| TC-601 | Windows Reserved Names Validation Gate | Done | hygiene-agent | TC-571 | 5 paths | reports/agents/hygiene-agent/H1_WINDOWS_RESERVED_NAMES/report.md, reports/agents/hygiene-agent/H1_WINDOWS_RESERVED_NAMES/self_review.md | 2026-01-24 |
| TC-602 | Specs README Navigation Update | Done | docs-agent | - | specs/README.md, reports/agents/docs-agent/** | reports/agents/docs-agent/H3_SPECS_README_SYNC/report.md, reports/agents/docs-agent/H3_SPECS_README_SYNC/self_review.md | 2026-01-24 |
| TC-603 | Taskcard status hygiene - correct TC-520 and TC-522 status | In-Progress | HYGIENE_AGENT | - | 4 paths | reports/agents/<agent>/TC-603/report.md, reports/agents/<agent>/TC-603/self_review.md | 2026-01-29 |
| TC-604 | Taskcard closeout for TC-520 and TC-522 | In-Progress | CLOSEOUT_AGENT | TC-520, TC-522 | 6 paths | reports/agents/<agent>/TC-604/report.md, reports/agents/<agent>/TC-604/self_review.md | 2026-01-29 |
| TC-630 | Golden capture for pilot-aspose-3d-foss-python | In-Progress | PILOT_E2E_AGENT | - | 4 paths | 4 items | 2026-01-29 |
| TC-631 | Offline-safe PR manager (W9) | In-Progress | PILOT_E2E_AGENT | TC-480 | src/launch/workers/w9_pr_manager/worker.py, tests/unit/workers/test_tc_480_pr_manager.py, reports/agents/**/TC-631/** | 4 items | 2026-01-29 |
| TC-632 | Pilot 3D config truth verification | In-Progress | PILOT_E2E_AGENT | - | specs/pilots/pilot-aspose-3d-foss-python/run_config.pinned.yaml, reports/agents/**/TC-632/** | 4 items | 2026-01-29 |
| TC-633 | Taskcard hygiene for TC-630/631/632 (Gate A2/B fixes) | In-Progress | VSCODE_AGENT | - | 6 paths | reports/agents/<agent>/TC-633/report.md, reports/agents/<agent>/TC-633/self_review.md, validate_swarm_ready.py 21/21 PASS after fixes | 2026-01-29 |
| TC-709 | Fix time-sensitive test in test_tc_523_metadata_endpoints | Done | HYGIENE_AGENT | - | tests/unit/telemetry_api/test_tc_523_metadata_endpoints.py, reports/agents/**/TC-709/** | reports/agents/<agent>/TC-709/report.md | 2026-01-30 |

## Summary

- **Total taskcards**: 48
- **Done**: 43
- **In-Progress**: 5
