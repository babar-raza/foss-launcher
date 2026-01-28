---
id: TC-511
title: "MCP quickstart from product URL (launch_start_run_from_product_url)"
status: Done
owner: "MCP_AGENT"
updated: "2026-01-28"
depends_on:
  - TC-510
  - TC-540
allowed_paths:
  - src/launch/mcp/tools/start_run_from_product_url.py
  - tests/unit/mcp/test_tc_511_start_run_from_product_url.py
  - reports/agents/**/TC-511/**
evidence_required:
  - reports/agents/<agent>/TC-511/report.md
  - reports/agents/<agent>/TC-511/self_review.md
  - "Test output: MCP tool responds with run_id for valid product URL"
spec_ref: f48fc5dbb12c5513f42aabc2a90e2b08c6170323
ruleset_version: ruleset.v1
templates_version: templates.v1
---

# Taskcard TC-511 — MCP quickstart from product URL (launch_start_run_from_product_url)

## Objective
Implement the `launch_start_run_from_product_url` MCP tool that accepts only an Aspose product page URL and derives the run_config automatically, enabling zero-configuration run initiation.

> **Note:** This tool was previously named `launch_start_run_from_url`. The explicit name clarifies it handles Aspose product URLs only. See TC-512 for GitHub repo URL quickstart.

## Required spec references
- specs/14_mcp_endpoints.md
- specs/24_mcp_tool_schemas.md
- specs/32_platform_aware_content_layout.md

## Scope
### In scope
- MCP tool `launch_start_run_from_product_url`
- Backward-compatible alias `launch_start_run_from_url`
- URL parsing and validation for Aspose product pages
- Automatic run_config derivation from URL
- Delegation to existing `launch_start_run`
- Error handling for invalid/unsupported URLs

### Out of scope
- Modifying existing `launch_start_run` tool
- GitHub repo URL quickstart (see TC-512)
- CLI quickstart (this is MCP only)
- New pilot creation

## Non-negotiables (binding for this task)
- **No improvisation:** if anything is unclear, write a blocker issue and stop.
- **Write fence:** MAY ONLY change files under Allowed paths.
- **Determinism:** URL parsing and config derivation MUST be deterministic.
- **Evidence:** All URL patterns tested must be documented.

## Preconditions / dependencies
- TC-510: MCP server exists with tool registration infrastructure
- TC-540: Content path resolver provides URL-to-path mapping logic

## Inputs
- Product page URL (e.g., `https://products.aspose.org/3d/python/`)
- URL patterns from specs/32_platform_aware_content_layout.md

## Outputs
- `src/launch/mcp/tools/start_run_from_product_url.py` — MCP tool implementation
- `tests/unit/mcp/test_tc_511_start_run_from_product_url.py` — Unit tests

## Allowed paths
- src/launch/mcp/tools/start_run_from_product_url.py
- tests/unit/mcp/test_tc_511_start_run_from_product_url.py
- reports/agents/**/TC-511/**

## Implementation steps
1) Create `src/launch/mcp/tools/start_run_from_product_url.py`:
   - Parse URL to extract: site (products/docs/kb/blog/reference), product, platform, locale
   - Map to run_config fields using content path resolver logic
   - Validate URL matches known site patterns
   - Build minimal run_config
   - Delegate to `launch_start_run`

2) Handle URL patterns:
   - `https://products.aspose.org/{product}/{locale}/{platform}/` (V2)
   - `https://docs.aspose.org/{product}/{locale}/{platform}/{page}/`
   - `https://kb.aspose.org/{product}/{locale}/{platform}/{article}/`
   - `https://blog.aspose.org/{locale?}/{product}/{platform}/{post}/`
   - `https://reference.aspose.org/{product}/{locale}/{platform}/`

3) Write unit tests:
   - Valid URL patterns for each site
   - Invalid URL rejection
   - Deterministic config derivation

## Test plan
- Unit tests: `tests/unit/mcp/test_tc_511_start_run_from_product_url.py`
- Integration tests: Covered by TC-523 (MCP E2E)
- Determinism proof: Same URL produces identical run_config across calls

## E2E verification
**Concrete command(s) to run:**
```bash
# Unit tests for URL parsing and config derivation
python -m pytest tests/unit/mcp/test_tc_511_start_run_from_product_url.py -v
# Import test (requires implementation)
python -c "from launch.mcp.tools.start_run_from_product_url import parse_product_url; print(parse_product_url('https://products.aspose.org/3d/en/python/'))"
```

**Expected artifacts:**
- src/launch/mcp/tools/start_run_from_product_url.py exists and imports cleanly
- Unit tests pass with 100% coverage of URL patterns

**Success criteria:**
- [ ] MCP tool parses all documented URL patterns
- [ ] Invalid URLs return appropriate error code
- [ ] Derived run_config matches expected values
- [ ] Unit tests pass

> When TC-523 (MCP E2E) runs, it will also exercise this tool indirectly.

## Integration boundary proven
What upstream/downstream wiring was validated:
- Upstream: TC-540 (content path resolver provides URL parsing patterns)
- Downstream: TC-510 (MCP server registers and exposes the tool)
- Contracts: specs/24_mcp_tool_schemas.md response shape

## Failure modes
1. **Failure**: Schema validation fails for output artifacts
   - **Detection**: `validate_swarm_ready.py` or pytest fails with JSON schema errors
   - **Fix**: Review artifact structure against schema files in `specs/schemas/`; ensure all required fields are present and types match
   - **Spec/Gate**: specs/11_state_and_events.md, specs/09_validation_gates.md (Gate C)

2. **Failure**: Nondeterministic output detected
   - **Detection**: Running task twice produces different artifact bytes or ordering
   - **Fix**: Review specs/10_determinism_and_caching.md; ensure stable JSON serialization, stable sorting of lists, no timestamps/UUIDs in outputs
   - **Spec/Gate**: specs/10_determinism_and_caching.md, tools/validate_swarm_ready.py (Gate H)

3. **Failure**: Write fence violation (modified files outside allowed_paths)
   - **Detection**: `git status` shows changes outside allowed_paths, or Gate E fails
   - **Fix**: Revert unauthorized changes; if shared library modification needed, escalate to owning taskcard
   - **Spec/Gate**: plans/taskcards/00_TASKCARD_CONTRACT.md (Write fence rule), tools/validate_taskcards.py

## Task-specific review checklist
Beyond the standard acceptance checks, verify:
- [ ] All outputs are written atomically per specs/10_determinism_and_caching.md
- [ ] No manual content edits made (compliance with no_manual_content_edits policy)
- [ ] Determinism verified by running task twice and comparing artifacts byte-for-byte
- [ ] All spec references listed in taskcard were consulted during implementation
- [ ] Evidence files (report.md, self_review.md) include all required sections and command outputs
- [ ] No placeholder values (PIN_ME, TODO, FIXME, etc.) remain in production code paths

## Deliverables
- Code: `src/launch/mcp/tools/start_run_from_product_url.py`
- Tests: `tests/unit/mcp/test_tc_511_start_run_from_product_url.py`
- Docs/specs/plans: None (specs updated as part of Phase 9)
- Reports (required):
  - reports/agents/__AGENT__/TC-511/report.md
  - reports/agents/__AGENT__/TC-511/self_review.md

## Acceptance checks
- [ ] MCP tool implementation exists
- [ ] All URL patterns handled correctly
- [ ] Error handling for invalid URLs
- [ ] Unit tests pass
- [ ] Reports written

## Self-review
Use `reports/templates/self_review_12d.md`.
