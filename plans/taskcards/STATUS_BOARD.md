# Taskcard Status Board

> **Auto-generated** by `tools/generate_status_board.py`
> **Do not edit manually** - all changes will be overwritten
> **Single source of truth**: taskcard YAML frontmatter

Last generated: 2026-01-28 13:42:22 UTC

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
| TC-250 | Shared libraries governance and single-writer enforcement | In-Progress | MODELS_AGENT | TC-200 | src/launch/models/**, tests/unit/models/**, reports/agents/**/TC-250/** | reports/agents/<agent>/TC-250/report.md, reports/agents/<agent>/TC-250/self_review.md, Test output: model validation tests | 2026-01-28 |
| TC-300 | Orchestrator graph wiring and run loop | Ready | unassigned | TC-200 | 5 paths | reports/agents/<agent>/TC-300/report.md, reports/agents/<agent>/TC-300/self_review.md | 2026-01-22 |
| TC-400 | W1 RepoScout (clone + fingerprint + Hugo/site discovery) | Ready | unassigned | TC-401, TC-402, TC-403, TC-404 | 5 paths | reports/agents/<agent>/TC-400/report.md, reports/agents/<agent>/TC-400/self_review.md | 2026-01-22 |
| TC-401 | W1.1 Clone inputs and resolve SHAs deterministically | Ready | unassigned | TC-200, TC-300 | 4 paths | reports/agents/<agent>/TC-401/report.md, reports/agents/<agent>/TC-401/self_review.md | 2026-01-22 |
| TC-402 | W1.2 Deterministic repo fingerprinting and inventory | Ready | unassigned | TC-200, TC-300 | src/launch/workers/w1_repo_scout/fingerprint.py, tests/unit/workers/test_tc_402_fingerprint.py, reports/agents/**/TC-402/** | reports/agents/<agent>/TC-402/report.md, reports/agents/<agent>/TC-402/self_review.md | 2026-01-22 |
| TC-403 | W1.3 Frontmatter contract discovery (deterministic) | Ready | unassigned | TC-200, TC-300 | src/launch/workers/w1_repo_scout/frontmatter.py, tests/unit/workers/test_tc_403_frontmatter.py, reports/agents/**/TC-403/** | reports/agents/<agent>/TC-403/report.md, reports/agents/<agent>/TC-403/self_review.md | 2026-01-22 |
| TC-404 | W1.4 Hugo config scan and site_context build matrix inference | Ready | unassigned | TC-200, TC-300 | src/launch/workers/w1_repo_scout/hugo_scan.py, tests/unit/workers/test_tc_404_hugo_scan.py, reports/agents/**/TC-404/** | reports/agents/<agent>/TC-404/report.md, reports/agents/<agent>/TC-404/self_review.md | 2026-01-22 |
| TC-410 | W2 FactsBuilder (ProductFacts + EvidenceMap) | Ready | unassigned | TC-411, TC-412, TC-413 | 5 paths | reports/agents/<agent>/TC-410/report.md, reports/agents/<agent>/TC-410/self_review.md | 2026-01-22 |
| TC-411 | W2.1 Extract ProductFacts catalog deterministically | Ready | unassigned | TC-400 | 4 paths | reports/agents/<agent>/TC-411/report.md, reports/agents/<agent>/TC-411/self_review.md | 2026-01-22 |
| TC-412 | W2.2 Build EvidenceMap linking facts and sources | Ready | unassigned | TC-400 | src/launch/workers/w2_facts_builder/evidence_map.py, tests/unit/workers/test_tc_412_evidence_map.py, reports/agents/**/TC-412/** | reports/agents/<agent>/TC-412/report.md, reports/agents/<agent>/TC-412/self_review.md | 2026-01-22 |
| TC-413 | W2.3 TruthLock compile (minimal claim groups) | Ready | unassigned | TC-400 | src/launch/workers/w2_facts_builder/truth_lock.py, tests/unit/workers/test_tc_413_truth_lock.py, reports/agents/**/TC-413/** | reports/agents/<agent>/TC-413/report.md, reports/agents/<agent>/TC-413/self_review.md | 2026-01-22 |
| TC-420 | W3 SnippetCurator (snippet_catalog.json) | Ready | unassigned | TC-421, TC-422 | 5 paths | reports/agents/<agent>/TC-420/report.md, reports/agents/<agent>/TC-420/self_review.md | 2026-01-22 |
| TC-421 | W3.1 Snippet inventory and tagging | Ready | unassigned | TC-400 | 4 paths | reports/agents/<agent>/TC-421/report.md, reports/agents/<agent>/TC-421/self_review.md | 2026-01-22 |
| TC-422 | W3.2 Snippet selection and normalization rules | Ready | unassigned | TC-400 | src/launch/workers/w3_snippet_curator/selection.py, tests/unit/workers/test_tc_422_snippet_selection.py, reports/agents/**/TC-422/** | reports/agents/<agent>/TC-422/report.md, reports/agents/<agent>/TC-422/self_review.md | 2026-01-22 |
| TC-430 | W4 IAPlanner (page_plan.json) | Ready | unassigned | TC-410, TC-420 | 4 paths | reports/agents/<agent>/TC-430/report.md, reports/agents/<agent>/TC-430/self_review.md | 2026-01-22 |
| TC-440 | W5 SectionWriter (draft Markdown with claim markers) | Ready | unassigned | TC-430 | 4 paths | reports/agents/<agent>/TC-440/report.md, reports/agents/<agent>/TC-440/self_review.md | 2026-01-22 |
| TC-450 | W6 LinkerAndPatcher (PatchBundle + apply to site worktree) | Ready | unassigned | TC-440 | 4 paths | reports/agents/<agent>/TC-450/report.md, reports/agents/<agent>/TC-450/self_review.md | 2026-01-22 |
| TC-460 | W7 Validator (all gates → validation_report.json) | Ready | unassigned | TC-450 | 4 paths | reports/agents/<agent>/TC-460/report.md, reports/agents/<agent>/TC-460/self_review.md | 2026-01-22 |
| TC-470 | W8 Fixer (targeted one-issue fix loop) | Ready | unassigned | TC-460 | 4 paths | reports/agents/<agent>/TC-470/report.md, reports/agents/<agent>/TC-470/self_review.md | 2026-01-22 |
| TC-480 | W9 PRManager (commit service → PR) | Ready | unassigned | TC-470 | src/launch/workers/w9_pr_manager/**, tests/unit/workers/test_tc_480_pr_manager.py, reports/agents/**/TC-480/** | reports/agents/<agent>/TC-480/report.md, reports/agents/<agent>/TC-480/self_review.md | 2026-01-22 |
| TC-500 | Clients & Services (telemetry, commit service, LLM provider) | Ready | unassigned | TC-200, TC-300 | src/launch/clients/**, tests/unit/clients/test_tc_500_services.py, reports/agents/**/TC-500/** | reports/agents/<agent>/TC-500/report.md, reports/agents/<agent>/TC-500/self_review.md | 2026-01-22 |
| TC-510 | MCP server | Ready | unassigned | TC-300 | 4 paths | reports/agents/<agent>/TC-510/report.md, reports/agents/<agent>/TC-510/self_review.md | 2026-01-22 |
| TC-511 | MCP quickstart from product URL (launch_start_run_from_product_url) | Ready | unassigned | TC-510, TC-540 | src/launch/mcp/tools/start_run_from_product_url.py, tests/unit/mcp/test_tc_511_start_run_from_product_url.py, reports/agents/**/TC-511/** | reports/agents/<agent>/TC-511/report.md, reports/agents/<agent>/TC-511/self_review.md, Test output: MCP tool responds with run_id for valid product URL | 2026-01-23 |
| TC-512 | MCP quickstart from GitHub repo URL (launch_start_run_from_github_repo_url) | Ready | unassigned | TC-510, TC-540, TC-401 | 5 paths | 4 items | 2026-01-23 |
| TC-520 | Pilots and regression harness | Ready | unassigned | TC-300, TC-460 | 6 paths | reports/agents/<agent>/TC-520/report.md, reports/agents/<agent>/TC-520/self_review.md | 2026-01-23 |
| TC-522 | Pilot E2E CLI execution and determinism verification | Ready | unassigned | TC-520, TC-530, TC-560 | scripts/run_pilot_e2e.py, tests/e2e/test_tc_522_pilot_cli.py, reports/agents/**/TC-522/** | reports/agents/<agent>/TC-522/report.md, reports/agents/<agent>/TC-522/self_review.md, artifacts/pilot_e2e_cli_report.json | 2026-01-23 |
| TC-523 | Pilot E2E MCP execution and determinism verification | Ready | unassigned | TC-520, TC-510, TC-560 | scripts/run_pilot_e2e_mcp.py, tests/e2e/test_tc_523_pilot_mcp.py, reports/agents/**/TC-523/** | reports/agents/<agent>/TC-523/report.md, reports/agents/<agent>/TC-523/self_review.md, artifacts/pilot_e2e_mcp_report.json | 2026-01-23 |
| TC-530 | CLI entrypoints and runbooks | Ready | unassigned | TC-300, TC-460 | 6 paths | reports/agents/<agent>/TC-530/report.md, reports/agents/<agent>/TC-530/self_review.md | 2026-01-22 |
| TC-540 | Content Path Resolver (Hugo content layout + blog localization rules) | Ready | unassigned | TC-400 | 5 paths | reports/agents/<agent>/TC-540/report.md, reports/agents/<agent>/TC-540/self_review.md | 2026-01-22 |
| TC-550 | Hugo Config Awareness (derive build constraints + language matrix) | Ready | unassigned | TC-400 | 4 paths | reports/agents/<agent>/TC-550/report.md, reports/agents/<agent>/TC-550/self_review.md | 2026-01-22 |
| TC-560 | Determinism and Reproducibility Harness (golden runs) | Ready | unassigned | TC-200, TC-300 | 5 paths | reports/agents/<agent>/TC-560/report.md, reports/agents/<agent>/TC-560/self_review.md | 2026-01-22 |
| TC-570 | Validation Gates (schema, links, Hugo smoke, policy) | Ready | unassigned | TC-460, TC-550 | 8 paths | reports/agents/<agent>/TC-570/report.md, reports/agents/<agent>/TC-570/self_review.md | 2026-01-22 |
| TC-571 | W7.x Policy gate: No manual content edits | Ready | unassigned | TC-460, TC-201 | src/launch/validators/policy_gate.py, tests/unit/validators/test_tc_571_policy_gate.py, reports/agents/**/TC-571/** | reports/agents/<agent>/TC-571/report.md, reports/agents/<agent>/TC-571/self_review.md | 2026-01-22 |
| TC-580 | Observability and Evidence Packaging (reports index + evidence zip) | Ready | unassigned | TC-300, TC-460 | 4 paths | reports/agents/<agent>/TC-580/report.md, reports/agents/<agent>/TC-580/self_review.md | 2026-01-22 |
| TC-590 | Security and Secrets Handling (redaction + lightweight scan) | Ready | unassigned | TC-300 | 5 paths | reports/agents/<agent>/TC-590/report.md, reports/agents/<agent>/TC-590/self_review.md | 2026-01-22 |
| TC-600 | Failure Recovery and Backoff (retry, resume, idempotency) | Ready | unassigned | TC-300 | 4 paths | reports/agents/<agent>/TC-600/report.md, reports/agents/<agent>/TC-600/self_review.md | 2026-01-22 |
| TC-601 | Windows Reserved Names Validation Gate | Done | hygiene-agent | TC-571 | 5 paths | reports/agents/hygiene-agent/H1_WINDOWS_RESERVED_NAMES/report.md, reports/agents/hygiene-agent/H1_WINDOWS_RESERVED_NAMES/self_review.md | 2026-01-24 |
| TC-602 | Specs README Navigation Update | Done | docs-agent | - | specs/README.md, reports/agents/docs-agent/** | reports/agents/docs-agent/H3_SPECS_README_SYNC/report.md, reports/agents/docs-agent/H3_SPECS_README_SYNC/self_review.md | 2026-01-24 |

## Summary

- **Total taskcards**: 41
- **Done**: 5
- **In-Progress**: 1
- **Ready**: 35
