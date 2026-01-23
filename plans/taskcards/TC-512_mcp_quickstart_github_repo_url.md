---
id: TC-512
title: "MCP quickstart from GitHub repo URL (launch_start_run_from_github_repo_url)"
status: Ready
owner: "unassigned"
updated: "2026-01-23"
depends_on:
  - TC-510
  - TC-540
  - TC-401
allowed_paths:
  - src/launch/mcp/tools/start_run_from_github_repo_url.py
  - src/launch/inference/repo_analyzer.py
  - tests/unit/mcp/test_tc_512_start_run_from_github_repo_url.py
  - tests/unit/inference/test_repo_analyzer.py
  - reports/agents/**/TC-512/**
evidence_required:
  - reports/agents/<agent>/TC-512/report.md
  - reports/agents/<agent>/TC-512/self_review.md
  - "Test output: MCP tool responds with run_id for valid GitHub repo URL"
  - "Test output: MCP tool returns INVALID_INPUT with missing_fields for ambiguous repo"
---

# Taskcard TC-512 — MCP quickstart from GitHub repo URL (launch_start_run_from_github_repo_url)

## Objective
Implement the `launch_start_run_from_github_repo_url` MCP tool that accepts only a public GitHub repository URL, attempts to infer product family and target platform, and derives a minimal run_config automatically.

## Required spec references
- specs/14_mcp_endpoints.md
- specs/24_mcp_tool_schemas.md
- specs/02_repo_ingestion.md

## Scope
### In scope
- MCP tool `launch_start_run_from_github_repo_url`
- Repository metadata fetching (GitHub API or clone)
- Deterministic inference algorithm for:
  - `family` (product family: 3d, cells, words, etc.)
  - `target_platform` (python, java, net, cpp, etc.)
- Confidence scoring and threshold enforcement
- Ambiguity handling with structured error responses
- Delegation to existing `launch_start_run`
- Error handling for invalid/inaccessible repos

### Out of scope
- Aspose product page URL quickstart (see TC-511)
- CLI quickstart (this is MCP only)
- Full repo analysis (only inference for required fields)
- Modifying existing `launch_start_run` tool

## Non-negotiables (binding for this task)
- **No improvisation:** if anything is unclear, write a blocker issue and stop.
- **Write fence:** MAY ONLY change files under Allowed paths.
- **Determinism:** Inference algorithm MUST be deterministic (same repo state = same inference result).
- **No guessing:** If inference is ambiguous (confidence < 80%), MUST return error with `missing_fields`.
- **Evidence:** Inference algorithm and confidence thresholds must be documented.

## Preconditions / dependencies
- TC-510: MCP server exists with tool registration infrastructure
- TC-540: Content path resolver provides platform mapping logic
- TC-401: Clone and resolve SHAs logic exists

## Inputs
- GitHub repository URL (e.g., `https://github.com/aspose-3d/Aspose.3D-for-Python-via-.NET`)
- Optional: GitHub API token for rate limiting

## Outputs
- `src/launch/mcp/tools/start_run_from_github_repo_url.py` — MCP tool implementation
- `src/launch/inference/repo_analyzer.py` — Inference algorithm implementation
- `tests/unit/mcp/test_tc_512_start_run_from_github_repo_url.py` — MCP tool unit tests
- `tests/unit/inference/test_repo_analyzer.py` — Inference algorithm unit tests

## Allowed paths
- src/launch/mcp/tools/start_run_from_github_repo_url.py
- src/launch/inference/repo_analyzer.py
- tests/unit/mcp/test_tc_512_start_run_from_github_repo_url.py
- tests/unit/inference/test_repo_analyzer.py
- reports/agents/**/TC-512/**

## Implementation steps
1) Create `src/launch/inference/repo_analyzer.py`:
   - Implement inference algorithm per specs/24_mcp_tool_schemas.md:
     - Repository name parsing: extract family and platform from naming conventions
       - Pattern: `Aspose.{Family}-for-{Platform}` or similar
     - README scanning: look for product family identifiers and platform mentions
     - Package file analysis: check setup.py, pom.xml, build.gradle, .csproj, etc.
   - Compute confidence score (0.0-1.0) for each inferred field
   - Return inference result with confidence scores

2) Create `src/launch/mcp/tools/start_run_from_github_repo_url.py`:
   - Validate GitHub URL format
   - Fetch repository metadata (use GitHub API or shallow clone)
   - Call repo_analyzer to infer family and target_platform
   - If confidence >= 80% for both:
     - Derive minimal run_config with defaults:
       - `locales: ["en"]`
       - `layout_mode: "auto"`
       - `allow_inference: false`
     - Pin `github_ref` to resolved HEAD SHA
     - Delegate to `launch_start_run`
   - If confidence < 80% for any field:
     - Return `ok: false` with `error.code = INVALID_INPUT`
     - Include `missing_fields` array
     - Include `suggested_values` object with candidates

3) Write unit tests:
   - Test inference on known Aspose repo patterns
   - Test ambiguous repo handling
   - Test invalid URL rejection
   - Test determinism (same input = same output)

## Test plan
- Unit tests: `tests/unit/mcp/test_tc_512_start_run_from_github_repo_url.py`
- Unit tests: `tests/unit/inference/test_repo_analyzer.py`
- Integration tests: Covered by TC-523 (MCP E2E)
- Determinism proof: Same repo URL produces identical inference across calls

## E2E verification
**Concrete command(s) to run:**
```bash
# Unit tests for inference algorithm
python -m pytest tests/unit/inference/test_repo_analyzer.py -v
# Unit tests for MCP tool
python -m pytest tests/unit/mcp/test_tc_512_start_run_from_github_repo_url.py -v
# Manual test (requires network)
python -c "from src.launch.inference.repo_analyzer import analyze_repo; print(analyze_repo('https://github.com/aspose-3d/Aspose.3D-for-Python-via-.NET'))"
```

**Expected artifacts:**
- src/launch/mcp/tools/start_run_from_github_repo_url.py exists and imports cleanly
- src/launch/inference/repo_analyzer.py exists and imports cleanly
- Unit tests pass

**Success criteria:**
- [ ] MCP tool validates GitHub URL format
- [ ] Inference correctly identifies known Aspose repo patterns
- [ ] Ambiguous repos return INVALID_INPUT with missing_fields
- [ ] Confidence threshold (80%) is enforced
- [ ] Unit tests pass
- [ ] Inference is deterministic

> When TC-523 (MCP E2E) runs, it will also exercise this tool indirectly.

## Integration boundary proven
What upstream/downstream wiring was validated:
- Upstream: TC-401 (clone/resolve SHA logic), TC-540 (platform mapping)
- Downstream: TC-510 (MCP server registers and exposes the tool)
- Contracts: specs/24_mcp_tool_schemas.md response shape

## Deliverables
- Code:
  - `src/launch/mcp/tools/start_run_from_github_repo_url.py`
  - `src/launch/inference/repo_analyzer.py`
- Tests:
  - `tests/unit/mcp/test_tc_512_start_run_from_github_repo_url.py`
  - `tests/unit/inference/test_repo_analyzer.py`
- Docs/specs/plans: None (specs updated as part of Phase 9)
- Reports (required):
  - reports/agents/__AGENT__/TC-512/report.md
  - reports/agents/__AGENT__/TC-512/self_review.md

## Acceptance checks
- [ ] MCP tool implementation exists
- [ ] Inference algorithm documented and tested
- [ ] Known Aspose repo patterns correctly identified
- [ ] Ambiguous repos handled per spec (INVALID_INPUT + missing_fields)
- [ ] Error handling for invalid/inaccessible repos
- [ ] Confidence threshold enforced
- [ ] Unit tests pass
- [ ] Reports written

## Self-review
Use `reports/templates/self_review_12d.md`.
