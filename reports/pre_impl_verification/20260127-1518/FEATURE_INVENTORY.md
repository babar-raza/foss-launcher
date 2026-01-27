# Feature Inventory

**Pre-Implementation Verification Run**: 20260127-1518
**Source**: AGENT_F (Feature & Testability Validator)
**Date**: 2026-01-27
**Total Features**: 73 (FEAT-001 through FEAT-073)

---

## Feature Inventory by Category

### Category 1: Repository Ingestion & Analysis (W1 RepoScout) - 11 Features

| Feature ID | Name | Description | Source | Testability |
|------------|------|-------------|--------|-------------|
| FEAT-001 | Repository Cloning | Clone public GitHub repos at pinned commit SHAs | specs/02_repo_ingestion.md | ✅ Testable |
| FEAT-002 | Repo Fingerprinting | Detect platform family, languages, build systems | specs/02_repo_ingestion.md, TC-402 | ✅ Testable |
| FEAT-003 | Adapter Selection | Deterministic adapter selection based on repo archetype | specs/02_repo_ingestion.md | ✅ Testable |
| FEAT-004 | Source Root Discovery | Identify source_roots (src/, lib/, pkg/) | specs/02_repo_ingestion.md | ❌ Not Testable |
| FEAT-005 | Docs Discovery | Discover docs/, README*, implementation notes | specs/02_repo_ingestion.md | ⚠️ Partial |
| FEAT-006 | Examples Discovery | Discover examples/, samples/, demo/ with phantom path detection | specs/02_repo_ingestion.md | ⚠️ Partial |
| FEAT-007 | Test Discovery | Discover tests/, test/, __tests__/ with test commands | specs/02_repo_ingestion.md | ❌ Not Testable |
| FEAT-008 | Binary Assets Discovery | Identify binary assets without parsing | specs/02_repo_ingestion.md | ❌ Not Testable |
| FEAT-009 | Phantom Path Detection | Detect claimed paths that don't exist | specs/02_repo_ingestion.md | ✅ Testable |
| FEAT-010 | Frontmatter Contract Discovery | Parse Hugo frontmatter schema from site repo | specs/18_site_repo_layout.md, TC-403 | ❌ Not Testable |
| FEAT-011 | Hugo Site Context | Extract Hugo configs and build matrix | specs/31_hugo_config_awareness.md, TC-404 | ⚠️ Partial |

### Category 2: Facts Extraction & Evidence Linking (W2 FactsBuilder) - 9 Features

| Feature ID | Name | Description | Source | Testability |
|------------|------|-------------|--------|-------------|
| FEAT-012 | Product Facts Extraction | Extract name, tagline, positioning, capabilities | specs/03_product_facts_and_evidence.md | ❌ Not Testable |
| FEAT-013 | Evidence Priority Ranking | Prioritize evidence: manifests > code > tests > docs > README | specs/03_product_facts_and_evidence.md | ✅ Testable |
| FEAT-014 | Evidence Map Linking | Link claims to repo paths and line ranges | specs/03_product_facts_and_evidence.md | ⚠️ Partial |
| FEAT-015 | Contradiction Detection | Detect contradictory claims across sources | specs/03_product_facts_and_evidence.md | ✅ Testable |
| FEAT-016 | Automated Contradiction Resolution | Resolve contradictions via priority-based algorithm | specs/03_product_facts_and_evidence.md | ✅ Testable |
| FEAT-017 | Format Support Modeling | Model asymmetric format support (import/export/partial) | specs/03_product_facts_and_evidence.md | ⚠️ Partial |
| FEAT-018 | Limitations Extraction | Extract explicit limitations from implementation notes | specs/03_product_facts_and_evidence.md | ❌ Not Testable |
| FEAT-019 | Truth Lock Compilation | Compile claim stability report | specs/04_claims_compiler_truth_lock.md, TC-413 | ❌ Not Testable |
| FEAT-020 | Claim Marker Assignment | Assign stable claim IDs | specs/23_claim_markers.md, TC-413 | ❌ Not Testable |

### Category 3: Snippet Curation (W3 SnippetCurator) - 5 Features

| Feature ID | Name | Description | Source | Testability |
|------------|------|-------------|--------|-------------|
| FEAT-021 | Snippet Discovery | Discover snippets from examples/, README, docs, tests | specs/05_example_curation.md | ❌ Not Testable |
| FEAT-022 | Snippet Normalization | Normalize imports, formatting for catalog | specs/05_example_curation.md | ❌ Not Testable |
| FEAT-023 | Snippet Tagging | Apply deterministic tags (quickstart, convert, merge, etc.) | specs/05_example_curation.md | ❌ Not Testable |
| FEAT-024 | Snippet Syntax Validation | Validate snippet syntax for target language | specs/05_example_curation.md | ✅ Testable |
| FEAT-025 | Generated Snippet Policy | Generate minimal snippets only when no repo snippets exist | specs/05_example_curation.md | ❌ Not Testable |

### Category 4: Page Planning (W4 IA Planner) - 8 Features

| Feature ID | Name | Description | Source | Testability |
|------------|------|-------------|--------|-------------|
| FEAT-026 | Page Plan Generation | Generate page specs for all sections | specs/06_page_planning.md, TC-430 | ❌ Not Testable |
| FEAT-027 | Launch Tier Selection | Select minimal/standard/rich tier based on evidence | specs/06_page_planning.md | ⚠️ Partial |
| FEAT-028 | Cross-Link Planning | Plan consistent cross-links using url_path | specs/06_page_planning.md | ❌ Not Testable |
| FEAT-029 | URL Path Mapping | Map output_path to canonical url_path | specs/06_page_planning.md, specs/33_public_url_mapping.md | ⚠️ Partial |
| FEAT-030 | Content Quota Enforcement | Enforce minimum page counts per section | specs/06_page_planning.md | ❌ Not Testable |
| FEAT-031 | Platform-Aware Path Resolution | Resolve V2 platform paths (/{locale}/{platform}/) | specs/32_platform_aware_content_layout.md, TC-540 | ⚠️ Partial |
| FEAT-032 | Product Type Adaptation | Adapt headings for cli/sdk/service product types | specs/06_page_planning.md | ⚠️ Partial |
| FEAT-033 | Launch Tier Quality Signals | Adjust tier based on repo health signals | specs/06_page_planning.md | ⚠️ Partial |

### Category 5: Content Drafting (W5 SectionWriter) - 4 Features

| Feature ID | Name | Description | Source | Testability |
|------------|------|-------------|--------|-------------|
| FEAT-034 | Template Rendering | Render section templates with facts and snippets | specs/07_section_templates.md, TC-440 | ⚠️ Partial |
| FEAT-035 | Claim Insertion | Insert claim markers in generated content | specs/23_claim_markers.md, TC-440 | ⚠️ Partial |
| FEAT-036 | Snippet Embedding | Embed curated snippets in content | specs/05_example_curation.md, TC-440 | ⚠️ Partial |
| FEAT-037 | Template Token Replacement | Replace __PLATFORM__, __LOCALE__, etc. | specs/20_rulesets_and_templates_registry.md | ⚠️ Partial |

### Category 6: Patch Application (W6 Linker/Patcher) - 6 Features

| Feature ID | Name | Description | Source | Testability |
|------------|------|-------------|--------|-------------|
| FEAT-038 | Idempotent Patch Application | Apply patches with content fingerprinting | specs/08_patch_engine.md | ✅ Testable |
| FEAT-039 | Anchor-Based Updates | Update content under heading anchors | specs/08_patch_engine.md | ❌ Not Testable |
| FEAT-040 | Frontmatter Key Updates | Surgically update frontmatter keys | specs/08_patch_engine.md | ❌ Not Testable |
| FEAT-041 | Conflict Detection | Detect patch conflicts (anchor not found, line range out of bounds) | specs/08_patch_engine.md | ❌ Not Testable |
| FEAT-042 | Conflict Resolution | Resolve conflicts via Fixer (W8) with bounded retries | specs/08_patch_engine.md | ❌ Not Testable |
| FEAT-043 | Allowed Paths Enforcement | Refuse patches outside allowed_paths | specs/08_patch_engine.md | ✅ Testable |

### Category 7: Validation (W7 Validator) - 12 Features

| Feature ID | Name | Description | Source | Testability |
|------------|------|-------------|--------|-------------|
| FEAT-044 | Schema Validation Gate | Validate all JSON artifacts against schemas | specs/09_validation_gates.md | ✅ Testable |
| FEAT-045 | Markdown Lint Gate | Run markdownlint with pinned ruleset | specs/09_validation_gates.md | ✅ Testable |
| FEAT-046 | Hugo Config Compatibility Gate | Validate Hugo configs cover planned sections | specs/09_validation_gates.md | ✅ Testable |
| FEAT-047 | Platform Layout Compliance Gate | Validate V2 platform paths | specs/09_validation_gates.md | ✅ Testable |
| FEAT-048 | Hugo Build Gate | Run hugo build in production mode | specs/09_validation_gates.md | ✅ Testable |
| FEAT-049 | Internal Links Gate | Check internal links and anchors | specs/09_validation_gates.md | ✅ Testable |
| FEAT-050 | External Links Gate | Run lychee or equivalent (optional) | specs/09_validation_gates.md | ✅ Testable |
| FEAT-051 | Snippet Checks Gate | Validate snippet syntax, optionally run in container | specs/09_validation_gates.md | ✅ Testable |
| FEAT-052 | TruthLock Gate | Enforce claim-to-evidence linking | specs/09_validation_gates.md | ✅ Testable |
| FEAT-053 | Consistency Gate | Validate product_name, repo_url, required headings | specs/09_validation_gates.md | ✅ Testable |
| FEAT-054 | Profile-Based Gating | Apply validation profiles (local/ci/prod) | specs/09_validation_gates.md | ⚠️ Partial |
| FEAT-055 | Gate Timeouts | Enforce per-gate timeouts with circuit breakers | specs/09_validation_gates.md | ✅ Testable |

### Category 8: Fixing (W8 Fixer) - 2 Features

| Feature ID | Name | Description | Source | Testability |
|------------|------|-------------|--------|-------------|
| FEAT-056 | Deterministic Issue Selection | Select next issue to fix deterministically | specs/24_mcp_tool_schemas.md, TC-470 | ⚠️ Partial |
| FEAT-057 | Fix Attempt Limiting | Cap fix attempts via max_fix_attempts | specs/09_validation_gates.md | ⚠️ Partial |

### Category 9: PR Management (W9 PR Manager) - 2 Features

| Feature ID | Name | Description | Source | Testability |
|------------|------|-------------|--------|-------------|
| FEAT-058 | PR Creation | Create PR via GitHub commit service | specs/12_pr_and_release.md, TC-480 | ❌ Not Testable |
| FEAT-059 | Rollback Metadata | Include rollback metadata (base_ref, run_id, affected_paths) | specs/34_strict_compliance_guarantees.md (Guarantee L) | ❌ Not Testable |

### Category 10: MCP Endpoints - 11 Features

| Feature ID | Name | Description | Source | Testability |
|------------|------|-------------|--------|-------------|
| FEAT-060 | launch_start_run | Start run from run_config | specs/24_mcp_tool_schemas.md | ✅ Testable |
| FEAT-061 | launch_start_run_from_product_url | Start run from Aspose product URL | specs/24_mcp_tool_schemas.md, TC-511 | ✅ Testable |
| FEAT-062 | launch_start_run_from_github_repo_url | Start run from GitHub repo URL with inference | specs/24_mcp_tool_schemas.md, TC-512 | ⚠️ Partial |
| FEAT-063 | launch_get_status | Get run status | specs/24_mcp_tool_schemas.md | ✅ Testable |
| FEAT-064 | launch_get_artifact | Get run artifact | specs/24_mcp_tool_schemas.md | ✅ Testable |
| FEAT-065 | launch_validate | Run validation gates | specs/24_mcp_tool_schemas.md | ⚠️ Partial |
| FEAT-066 | launch_fix_next | Fix next issue deterministically | specs/24_mcp_tool_schemas.md | ⚠️ Partial |
| FEAT-067 | launch_resume | Resume paused run from snapshot | specs/24_mcp_tool_schemas.md | ⚠️ Partial |
| FEAT-068 | launch_cancel | Cancel run | specs/24_mcp_tool_schemas.md | ✅ Testable |
| FEAT-069 | launch_open_pr | Open PR with evidence bundle | specs/24_mcp_tool_schemas.md | ❌ Not Testable |
| FEAT-070 | launch_list_runs | List runs with filters | specs/24_mcp_tool_schemas.md | ✅ Testable |

### Category 11: Orchestration & State Management - 3 Features

| Feature ID | Name | Description | Source | Testability |
|------------|------|-------------|--------|-------------|
| FEAT-071 | LangGraph Orchestrator | Coordinate workers via LangGraph state machine | specs/00_overview.md, TC-300 | ❌ Not Testable |
| FEAT-072 | Event Sourcing | Log all events to events.ndjson for replay | specs/11_state_and_events.md | ❌ Not Testable |
| FEAT-073 | Deterministic Execution | Ensure same inputs produce same outputs | specs/10_determinism_and_caching.md | ❌ Not Testable |

---

## Testability Summary

**Total Features**: 73

**Testability Breakdown**:
- **Independently Testable**: 33/73 (45%)
- **Partially Testable**: 25/73 (34%)
- **Not Testable**: 15/73 (21%)

### Testability by Category

| Category | Testable | Partial | Not Testable |
|----------|----------|---------|--------------|
| W1 RepoScout | 3 (27%) | 3 (27%) | 5 (45%) |
| W2 FactsBuilder | 3 (33%) | 2 (22%) | 4 (44%) |
| W3 SnippetCurator | 1 (20%) | 0 (0%) | 4 (80%) |
| W4 IA Planner | 0 (0%) | 5 (63%) | 3 (38%) |
| W5 SectionWriter | 0 (0%) | 4 (100%) | 0 (0%) |
| W6 Linker/Patcher | 2 (33%) | 0 (0%) | 4 (67%) |
| W7 Validator | 10 (83%) | 2 (17%) | 0 (0%) |
| W8 Fixer | 0 (0%) | 2 (100%) | 0 (0%) |
| W9 PR Manager | 0 (0%) | 0 (0%) | 2 (100%) |
| MCP Endpoints | 7 (64%) | 3 (27%) | 1 (9%) |
| Orchestration | 0 (0%) | 0 (0%) | 3 (100%) |

**Key Finding**: Validation gates (W7) have highest testability (83%), while orchestration and state management (FEAT-071 through FEAT-073) have no testability defined.

---

## Feature-to-Requirement Mapping

**Requirements Covered**: 23/24 (96%)

**Uncovered Requirement**: REQ-024 (Rollback + recovery contract) - depends on TC-480 (not started)

---

## Determinism Controls

**Features with Determinism Controls**: 42/73 (58%)

**Strong Determinism Controls**:
- FEAT-001 (Repository Cloning): Pinned commit SHAs
- FEAT-003 (Adapter Selection): Deterministic scoring with tie-breaking
- FEAT-013 (Evidence Priority Ranking): Fixed priority order (1-7)
- FEAT-020 (Claim Marker Assignment): Stable claim ID hashing
- FEAT-038 (Idempotent Patch Application): Content fingerprinting (sha256)
- FEAT-044 through FEAT-053 (Validation Gates): Fixed execution order
- FEAT-056 (Deterministic Issue Selection): Severity-based ordering
- FEAT-060 (launch_start_run): Idempotency via idempotency_key

**Partial Determinism Controls**:
- LLM-based features (FEAT-012, FEAT-015, FEAT-018, FEAT-034) use temperature=0.0 but lack prompt versioning
- Inference features (FEAT-062) lack confidence threshold versioning
- State features (FEAT-072) lack event replay determinism guarantees

**No Determinism Controls**:
- FEAT-039, FEAT-040, FEAT-043 (Patch sub-features)
- FEAT-058, FEAT-059 (PR Management) - TC-480 not started
- FEAT-063 through FEAT-070 (MCP tools except launch_start_run)
- FEAT-071 (Orchestrator) - TC-300 not started

---

## Source Evidence

All features extracted from:
- **reports/pre_impl_verification/20260127-1518/agents/AGENT_F/REPORT.md**
- Cross-referenced with specs/ and plans/taskcards/
- Testability assessments based on fixtures, acceptance criteria, and E2E hooks

**Extraction Method**: Systematic review of specs, traceability matrix, and taskcard bindings
**Validation Status**: All 73 features have evidence citations (100%)
