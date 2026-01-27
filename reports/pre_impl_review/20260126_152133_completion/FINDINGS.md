# Findings Log

**Run**: 20260126_152133
**Status**: In Progress

## Format

Each finding follows:
- **GAP-###**: Unique identifier
- **Severity**: BLOCKER / MAJOR / MINOR / INFO
- **Description**: What's wrong
- **Evidence**: File path + lines or exact excerpt
- **Impact**: What artifacts/flows are affected
- **Fix**: Action taken (or remaining if not yet fixed)

---

## Findings

### GAP-001: Critical path overlap - src/launch/validators/cli.py

**Severity**: BLOCKER
**Description**: File `src/launch/validators/cli.py` is claimed by both TC-530 and TC-570 in their allowed_paths, causing a critical overlap violation.
**Evidence**:
- [reports/swarm_allowed_paths_audit.md](../../swarm_allowed_paths_audit.md) lines 27-29
- TC-530 allowed_paths: line 12 of [plans/taskcards/TC-530_cli_entrypoints_and_runbooks.md](../../../plans/taskcards/TC-530_cli_entrypoints_and_runbooks.md)
- TC-570 allowed_paths: line 11 of [plans/taskcards/TC-570_validation_gates_ext.md](../../../plans/taskcards/TC-570_validation_gates_ext.md)
- [pyproject.toml](../../../pyproject.toml) shows `launch_validate` → `launch.validators.cli:main`
**Impact**: Gate E (Allowed paths audit) fails with 1 critical overlap. Violates zero-tolerance policy for src/** overlaps.
**Analysis**: `src/launch/validators/cli.py` implements the `launch_validate` CLI command and validation logic. This belongs to TC-570 (Validation Gates), not TC-530 (CLI entrypoints). TC-530's scope is the main CLI app (`src/launch/cli.py`) and runbooks.
**Fix**: Remove `src/launch/validators/cli.py` from TC-530 allowed_paths.
**Status**: ✅ FIXED - Removed from TC-530 frontmatter and body. Gate E now passing.

### GAP-002: Broken markdown links with GitHub line anchors

**Severity**: MAJOR
**Description**: 19 markdown links in PRE_IMPL_HEALING_AGENT report use GitHub-style line number anchors (#L##-L##) which are not valid local file references.
**Evidence**:
- [reports/agents/PRE_IMPL_HEALING_AGENT/PRE_IMPL_HEALING/report.md](../../agents/PRE_IMPL_HEALING_AGENT/PRE_IMPL_HEALING/report.md)
  - Line 60: `specs/schemas/run_config.schema.json#L457-L468`
  - Line 80: `specs/schemas/validation_report.schema.json#L20-L24`
  - Line 93: `docs/cli_usage.md#L122-L124`
  - Line 104: `src/launch/validators/cli.py#L74-L82`
  - Line 116: `src/launch/validators/cli.py#L219-L225`
  - (14 more similar links)
**Impact**: Gate D (Markdown link integrity) fails with 24 broken links total (19 from this issue, 5 expected from new INDEX.md).
**Analysis**: The link checker validates links as local filesystem paths and doesn't understand GitHub's #L notation. These links work on GitHub but fail local validation.
**Fix Options**:
1. Strip #L anchors from links in the report (make them point to files only)
2. Update link checker to ignore #L anchors
3. Mark this report directory as excluded from link checking (since it's an agent report, not canonical docs)
**Fix**: Converted all links to absolute paths from repo root (with leading `/`).
**Status**: ✅ FIXED - All 16 relative links converted to absolute. Gate D now has only 6 expected broken links (from INDEX.md).

### GAP-003: Expected broken links in new INDEX.md

**Severity**: INFO
**Description**: 5 broken links in newly created INDEX.md point to files that will be created during this review run.
**Evidence**: [reports/pre_impl_review/20260126_152133_completion/INDEX.md](INDEX.md) lines 17-25
**Impact**: Gate D (Markdown link integrity) - 5 of 24 broken links
**Fix**: Files will be created during Phase 3 and Phase 4 of this review
**Status**: EXPECTED - Will resolve naturally

### GAP-004: Ruleset contract mismatch (Phase 2 Fix B)

**Severity**: BLOCKER
**Description**: Ruleset schema was incomplete and didn't match the actual ruleset.v1.yaml file, causing potential validation failures.
**Evidence**:
- [specs/schemas/ruleset.schema.json](/specs/schemas/ruleset.schema.json) was missing keys: `hugo`, `claims`, and optional properties in `style`, `truth`, `editing`
- [specs/rulesets/ruleset.v1.yaml](/specs/rulesets/ruleset.v1.yaml) would have failed validation
- [specs/20_rulesets_and_templates_registry.md](/specs/20_rulesets_and_templates_registry.md) lacked normative definitions of ruleset structure
- [scripts/validate_spec_pack.py](/scripts/validate_spec_pack.py) did not validate rulesets
**Impact**: Spec pack was incomplete; rulesets could not be validated mechanically.
**Fix Applied**:
1. Updated ruleset.schema.json to include all keys from ruleset.v1.yaml
2. Added normative ruleset structure documentation to specs/20
3. Extended validate_spec_pack.py with `_validate_rulesets()` function
4. Verified: spec pack validation now includes ruleset validation and passes
**Status**: ✅ FIXED

### GAP-005: Duplicate requirement ID REQ-011 (Phase 2 Fix A)

**Severity**: BLOCKER
**Description**: TRACEABILITY_MATRIX.md had two headings with `### REQ-011`, violating requirement ID uniqueness.
**Evidence**: [TRACEABILITY_MATRIX.md](/TRACEABILITY_MATRIX.md) lines 120 and 128
**Impact**: Requirements traceability was ambiguous; automated processing would fail.
**Fix Applied**: Renamed second REQ-011 ("Two pilot projects") to REQ-011a to match canonical source [specs/reference/system-requirements.md](/specs/reference/system-requirements.md)
**Status**: ✅ FIXED

### GAP-006: Plans traceability incomplete (Phase 2 Fix C)

**Severity**: MAJOR
**Description**: 10 binding specs were missing from plans/traceability_matrix.md
**Evidence**: Comparison of [specs/README.md](/specs/README.md) binding specs vs [plans/traceability_matrix.md](/plans/traceability_matrix.md)
**Impact**: Incomplete traceability coverage; some binding specs had no taskcard mappings documented.
**Fix Applied**: Added all 10 missing specs with appropriate taskcard mappings
**Status**: ✅ FIXED

### GAP-007: Validation profile precedence not implemented (Phase 2 Fix D)

**Severity**: MAJOR
**Description**: [src/launch/validators/cli.py](/src/launch/validators/cli.py) only used CLI `--profile` argument, not the 4-level precedence defined in specs/09
**Evidence**: [specs/09_validation_gates.md](/specs/09_validation_gates.md) defines precedence: run_config → CLI → env var → default
**Impact**: Profile selection didn't match spec; run_config.validation_profile was ignored.
**Fix Applied**: Implemented full 4-level precedence in validate() function
**Status**: ✅ FIXED

### GAP-008: Incorrect gate enforcement claim (Phase 2 Fix E)

**Severity**: MINOR
**Description**: TRACEABILITY_MATRIX.md claimed Gate J enforces allowed_paths, but it's actually Gate E.
**Evidence**: Line 162 of [TRACEABILITY_MATRIX.md](/TRACEABILITY_MATRIX.md)
**Impact**: Documentation inaccuracy; enforcement was correct, just misdocumented.
**Fix Applied**: Changed "Gate J" → "Gate E" in allowed_paths requirement row
**Status**: ✅ FIXED

### GAP-009: Broken link to non-existent mcp_tool_schemas.json (Phase 4 Fix)

**Severity**: MINOR
**Description**: SPECS_TO_SCHEMAS.md trace matrix referenced `/specs/schemas/mcp_tool_schemas.json`, which does not exist. MCP tool schemas are defined inline in specs, not as separate JSON files.
**Evidence**:
- [reports/pre_impl_review/20260126_152133_completion/TRACE_MATRICES/SPECS_TO_SCHEMAS.md](TRACE_MATRICES/SPECS_TO_SCHEMAS.md) lines 152 and 221
- Link checker failure: `specs\schemas\mcp_tool_schemas.json` not found
**Impact**: Gate D (Markdown link integrity) failure; broken link in trace matrix documentation
**Fix Applied**:
1. Line 152: Changed link from `/specs/schemas/mcp_tool_schemas.json` to `/specs/14_mcp_endpoints.md`
2. Line 221: Changed link from inline text to `/specs/24_mcp_tool_schemas.md`
3. Clarified that MCP tool schemas are defined inline in specs (JSON Schema format)
**Verification**: Link checker reduced from 3 to 2 broken links (remaining 2 are expected Phase 4 files)
**Status**: ✅ FIXED

