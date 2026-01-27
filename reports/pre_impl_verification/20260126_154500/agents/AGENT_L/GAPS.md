# AGENT_L: Gaps Register

**Agent**: AGENT_L (Links/Consistency/Repo Professionalism Auditor)
**Date**: 2026-01-27
**Total Gaps**: 8 (1 BLOCKER, 4 MAJOR, 3 MINOR)

---

## L-GAP-001 | BLOCKER | Broken internal links (184 total)

**Description**: 184 broken internal markdown links found across 81 source files (24% of markdown files). Broken links hurt navigation, professionalism, and maintainability. Per Agent L mission rules, broken internal links are ALWAYS BLOCKER severity.

**Evidence**:
- Link checker results: `temp_link_check_results.json`
- Categorized analysis: `temp_broken_links_categorized.json`
- Total internal links checked: 892
- Broken links: 184 (20.6% failure rate)

**Breakdown by category**:
1. **Absolute path links** (129 / 70%): Links using `/specs/file.md` instead of relative paths
   - Example: `reports/pre_impl_review/20260126_152133_completion/FINDINGS.md:69` → `/specs/schemas/ruleset.schema.json`
   - Affected: Primarily `reports/pre_impl_review/20260126_152133_completion/` and `reports/agents/PRE_IMPL_HEALING_AGENT/`

2. **Directory links** (40 / 22%): Links to directories instead of files
   - Example: `specs/README.md:139` → `pilots/pilot-aspose-3d-foss-python/` (should link to file)
   - Affected: `reports/orchestrator_master_review.md`, `specs/README.md`, phase reports

3. **Broken anchors** (8 / 4%): Links to non-existent heading anchors
   - Example: `reports/agents/hardening-agent/.../compliance_matrix.md:28` → `specs/34_strict_compliance_guarantees.md#a-input-immutability---pinned-commit-shas`
   - Actual heading: `### A) Input Immutability - Pinned Commit SHAs` (anchor format mismatch)

4. **Line number anchors** (4 / 2%): GitHub-style `#L123` anchors (don't work in markdown)
   - Example: `reports/phase-0_discovery/gap_analysis.md:51` → `../../specs/01_system_contract.md#L86`
   - Don't work in local markdown viewers/editors

5. **Missing relative files** (3 / 2%): Legitimate missing file links
   - Example: `reports/pre_impl_verification/20260126_154500/agents/AGENT_G/GAPS.md:178` → `path` (placeholder text)

**Proposed Fix**:

**Step 1: Absolute path links (129 links)**
- Automated conversion: Replace `/specs/` with `../../../specs/` (adjust depth per source file location)
- Focus files:
  - `reports/pre_impl_review/20260126_152133_completion/FINDINGS.md` (11 links)
  - `reports/agents/PRE_IMPL_HEALING_AGENT/PRE_IMPL_HEALING/report.md` (18 links)
  - Other files in `reports/pre_impl_review/20260126_152133_completion/`
- Can be scripted with relative path calculation based on source file depth

**Step 2: Directory links (40 links)**
- Manual review required for each link to determine correct target file
- Common patterns:
  - Agent report directories → link to `report.md` or `README.md`
  - Pilot directories → link to `run_config.pinned.yaml` or `README.md`
  - Schema/template directories → link to specific schema or `README.md`
- Update format: `[link] (dir/)` → `[link] (dir/report.md)`

**Step 3: Broken anchors (8 links)**
- Verify actual heading format in target file
- Update anchor to match GitHub slug generation:
  - Lowercase all letters
  - Replace spaces with hyphens
  - Remove punctuation (parentheses, colons, etc.)
  - Example: `### A) Input Immutability - Pinned Commit SHAs` → `#a-input-immutability---pinned-commit-shas`
- Specific fixes:
  - `compliance_matrix.md`: Update 6 links to `specs/34_strict_compliance_guarantees.md` anchors
  - `go_no_go.md` (20260124-102204): Fix 2 links to `gaps_and_blockers.md` anchors (verify heading names)

**Step 4: Line number anchors (4 links)**
- Convert to section anchors where possible: `file.md#L86` → `file.md#error-codes` (find nearest heading)
- Or remove anchors if not critical: `file.md#L86` → `file.md`
- Files affected:
  - `reports/phase-0_discovery/gap_analysis.md:51`
  - `reports/pre_impl_review/20260124-192034/go_no_go.md` (3 links)

**Step 5: Missing files (3 links)**
- `AGENT_G/GAPS.md:178`: Remove placeholder links (uses literal word "path" as target)
- `IMPLEMENTATION_KICKOFF_PROMPT.md:5`: Fix self-referential directory link

**Validation**:
Re-run link checker: `python temp_link_checker.py` and verify 0 broken links remain.

**Gap Closed When**: Link checker reports 0 broken links (100% link health)

---

## L-GAP-002 | MAJOR | Conflicting exit code definitions

**Description**: Exit code definitions conflict between binding spec (`specs/01_system_contract.md`) and reference docs (`docs/cli_usage.md`). Binding spec defines validation failure as exit code `2`, while reference docs define it as exit code `1`. This creates ambiguity for implementers.

**Evidence**:

**Source 1 (BINDING)**: `specs/01_system_contract.md:141-146`
```markdown
### Exit codes (recommended)
- `0` success
- `2` validation/spec/schema failure
- `3` policy violation (allowed_paths, governance)
- `4` external dependency failure (commit service, telemetry API)
- `5` unexpected internal error
```

**Source 2 (REFERENCE)**: `docs/cli_usage.md:69-72`
```markdown
- **Exit Codes**:
  - `0` - Success
  - `1` - Validation failure
  - `2` - Critical error
```

**Source 3 (REFERENCE)**: `docs/cli_usage.md:129-131`
```markdown
- **Exit Codes**:
  - `0` - All gates pass
  - `1` - One or more gates fail
```

**Conflict**:
- Spec (BINDING): validation failure = exit `2`
- Docs (REFERENCE): validation failure = exit `1`
- Spec defines 5 exit codes; docs define 3

**Impact**:
- Implementers may follow docs instead of specs, creating non-compliant CLI
- Testing scripts may expect wrong exit codes
- User documentation would be incorrect

**Proposed Fix**:

Update `docs/cli_usage.md` to match `specs/01_system_contract.md` (specs are authority):

**Line 69-72** (launch_run exit codes):
```markdown
- **Exit Codes**:
  - `0` - Success
  - `2` - Validation/spec/schema failure
  - `3` - Policy violation
  - `4` - External dependency failure (commit service, telemetry API)
  - `5` - Unexpected internal error
```

**Line 129-131** (launch_validate exit codes):
```markdown
- **Exit Codes**:
  - `0` - All gates pass
  - `2` - One or more gates fail (validation/schema issues)
  - `3` - Policy violation detected
  - `5` - Unexpected internal error
```

**Line 220-228** (Exit Code Reference section):
Ensure this section references `specs/01_system_contract.md` and uses its definitions verbatim.

**Gap Closed When**: `docs/cli_usage.md` exit codes match `specs/01_system_contract.md` exactly

---

## L-GAP-003 | MAJOR | Missing schemas/README.md (schema contribution guidance)

**Description**: No `specs/schemas/README.md` exists to explain how to add, version, or validate schemas. While schemas are listed in `specs/README.md`, there's no guidance for contributors who need to add or modify schemas.

**Evidence**:
- `specs/schemas/` directory exists with 22 schema files
- `specs/README.md:142-153` lists schemas but doesn't explain contribution process
- No README in schemas directory: `ls specs/schemas/README.md` → file not found

**Impact**:
- Contributors don't know how to properly add new schemas
- No documented schema naming conventions (beyond `.schema.json` suffix)
- No validation requirements documented
- Unclear relationship between schemas and specs

**Proposed Fix**:

Create `specs/schemas/README.md` with:

```markdown
# JSON Schemas

This directory contains JSON Schema definitions for all launcher artifacts and API contracts.

## Schema Naming Convention
- Format: `{artifact_name}.schema.json`
- Use snake_case for artifact names
- Example: `run_config.schema.json`, `validation_report.schema.json`

## Adding a New Schema
1. Create schema file: `specs/schemas/{artifact_name}.schema.json`
2. Include required metadata:
   - `$schema`: "https://json-schema.org/draft/2020-12/schema"
   - `$id`: Unique identifier
   - `title`: Human-readable title
   - `description`: What the schema validates
3. Reference from binding spec (if applicable)
4. Add validation to `tools/validate_spec_pack.py` (if required)
5. Update `specs/README.md` schema list

## Schema Validation
All schemas must:
- Be valid JSON Schema Draft 2020-12
- Include `$schema`, `$id`, `title`, `description`
- Use `additionalProperties: false` for strict validation (recommended)
- Include examples in spec files (not in schema itself)

## Versioning
- Schemas follow semver semantics but versioning is implicit
- Breaking changes require spec version bump
- See `specs/20_rulesets_and_templates_registry.md` for registry versioning

## Schema List
See [specs/README.md] (../../../../../specs/README.md) for complete schema inventory.

## Related Specs
- [specs/01_system_contract.md] (../../../../../specs/01_system_contract.md) - Schema validation requirements
- [specs/20_rulesets_and_templates_registry.md] (../../../../../specs/20_rulesets_and_templates_registry.md) - Versioning
- [specs/29_project_repo_structure.md] (../../../../../specs/29_project_repo_structure.md) - Where schemas live
```

**Gap Closed When**: `specs/schemas/README.md` exists and explains schema contribution process

---

## L-GAP-004 | MAJOR | Missing reports/README.md (report structure guidance)

**Description**: No `reports/README.md` exists to explain report directory structure, naming conventions, or which templates to use. While `reports/templates/` exists and README mentions reports, there's no comprehensive guide.

**Evidence**:
- `reports/` directory has complex structure:
  - `agents/` (agent reports)
  - `phase-*` (phase reports)
  - `pre_impl_verification/` (verification reports)
  - `pre_impl_review/` (review reports)
  - `templates/` (report templates)
- No README: `ls reports/README.md` → file not found
- `README.md:15` mentions reports briefly
- `CONTRIBUTING.md:10` says "write reports to `reports/`" but no details

**Impact**:
- Inconsistent report placement (some agents use different structures)
- Unclear which template to use for which report type
- No naming convention documentation
- Hard to navigate report history

**Proposed Fix**:

Create `reports/README.md` with:

```markdown
# Reports Directory

This directory contains all agent and phase review artifacts required by the swarm coordination playbook.

## Directory Structure

- `agents/{agent-name}/{task-id}/` - Per-agent, per-task reports
  - `report.md` - Task completion report (required)
  - `self_review.md` - 12-dimension self-review (required)
  - `GAPS.md` - Gaps identified (if applicable)
  - Additional task-specific artifacts
- `phase-{N}_{phase-name}/` - Phase completion reports
  - `change_log.md` - What changed in this phase
  - `self_review_12d.md` - Phase self-review
  - `gate_outputs/` - Validation gate outputs
- `pre_impl_verification/{timestamp}/` - Pre-implementation verification reports
- `pre_impl_review/{timestamp}/` - Pre-implementation review reports
- `templates/` - Report templates (DO NOT MODIFY - copy for use)
- `orchestrator_master_review.md` - Orchestrator handoff report

## Naming Conventions

### Agent Reports
- Directory: `agents/{agent-name}/{task-id}/`
- Agent name: kebab-case (e.g., `hygiene-agent`, `pre-flight-agent`)
- Task ID: uppercase (e.g., `TC-100`, `PRE_FLIGHT`, `H1_WINDOWS_RESERVED_NAMES`)

### Phase Reports
- Directory: `phase-{N}_{phase-name}/`
- Number: Sequential integer (0, 1, 2, ...)
- Name: kebab-case (e.g., `discovery`, `spec-hardening`)

### Timestamps
- Format: ISO 8601 compact (YYYYMMDD_HHMMSS) or (YYYYMMDD-HHMMSS)
- Timezone: UTC recommended
- Example: `20260126_154500`

## Required Templates

### For Taskcards
Use `templates/self_review_12d.md` for task self-reviews.

Required deliverables per `plans/taskcards/00_TASKCARD_CONTRACT.md`:
- `reports/agents/<agent>/<task_id>/report.md`
- `reports/agents/<agent>/<task_id>/self_review.md`

### For Pre-Implementation Verification
Each agent produces:
- `REPORT.md` - Main findings report
- `GAPS.md` - Gaps register with severity
- `SELF_REVIEW.md` - Self-assessment

## Immutability

**Important**: Reports are **append-only evidence**. Do not modify or delete published reports. If corrections are needed, add an errata file or new timestamped report.

## Related Documentation
- [plans/swarm_coordination_playbook.md] (../../../../../plans/swarm_coordination_playbook.md) - Report requirements
- [plans/taskcards/00_TASKCARD_CONTRACT.md] (../../../../../plans/taskcards/00_TASKCARD_CONTRACT.md) - Per-task evidence
- [reports/templates/] (../../../../templates/) - Report templates
```

**Gap Closed When**: `reports/README.md` exists and explains report structure and conventions

---

## L-GAP-005 | MAJOR | Missing general contribution guidelines (CONTRIBUTING.md is minimal)

**Description**: `CONTRIBUTING.md` is minimal (20 lines) and lacks detailed guidance for contributors on repo conventions, processes, and requirements.

**Evidence**: `CONTRIBUTING.md` (entire file):
```markdown
# Contributing

This repository is a **spec pack + scaffold**.

## Ground rules

- Do not change binding specs casually. Changes to `specs/` must be deliberate and reviewed.
- Keep implementation aligned to specs. If implementation diverges, update specs or fix code.
- No manual content edits in target site repos during launches (see `plans/policies/no_manual_content_edits.md`).
- All agent work must be auditable: write reports to `reports/` and runs to `runs/`.

## Development quickstart

```bash
make install
make lint
make validate
make test
```
```

**Missing guidance**:
- How to add specs (naming, what requires taskcards, BINDING vs REFERENCE)
- How to add taskcards (frontmatter, STATUS_BOARD regeneration, dependency tracking)
- How to add schemas (validation, versioning, spec references)
- How to structure reports (directory placement, naming, templates)
- PR submission guidelines
- Review process
- When to update indexes (specs/README.md, plans/taskcards/INDEX.md)

**Impact**:
- External contributors may not understand repo conventions
- Risk of incorrectly structured PRs
- Inconsistent additions to specs/taskcards/schemas

**Proposed Fix**:

Expand `CONTRIBUTING.md` with sections:

1. **Repository Structure** (overview of directories and their purposes)
2. **Adding Specs**
   - Naming convention: `NN_descriptive_name.md`
   - BINDING vs REFERENCE classification
   - When taskcards are required
   - Update `specs/README.md` index
3. **Adding Taskcards**
   - Naming convention: `TC-XXX_descriptive_name.md`
   - Required YAML frontmatter fields
   - Regenerate STATUS_BOARD: `python tools/generate_status_board.py`
   - Update `plans/taskcards/INDEX.md` if needed
4. **Adding Schemas**
   - Naming convention: `{artifact}.schema.json`
   - Validation requirements
   - Reference from specs
5. **Writing Reports**
   - Directory structure: `reports/agents/{agent}/{task}/`
   - Required files: `report.md`, `self_review.md`
   - Use templates from `reports/templates/`
6. **Pull Request Process**
   - Run validation: `make validate`
   - Run tests: `make test`
   - Update documentation if needed
   - Reference related specs/taskcards
7. **Virtual Environment Policy** (`.venv` requirement)
8. **Review Checklist** (what reviewers look for)

**Gap Closed When**: `CONTRIBUTING.md` contains comprehensive contribution guidelines (minimum 100 lines with all sections)

---

## L-GAP-006 | MAJOR | Missing docs/README.md (docs directory index)

**Description**: `docs/` directory contains reference documentation but has no `README.md` or `INDEX.md` to guide navigation.

**Evidence**:
- `docs/` contains:
  - `architecture.md`
  - `cli_usage.md`
  - `reference/local-telemetry.md`
  - `reference/local-telemetry-api.md`
- No index: `ls docs/README.md` → file not found
- Root `README.md` references some docs files but `docs/` itself has no internal navigation

**Impact**:
- Minor impact (docs are referenced from root README)
- Harder to discover all available docs when browsing `docs/` directly
- No explanation of REFERENCE vs BINDING distinction for docs

**Proposed Fix**:

Create `docs/README.md` with:

```markdown
# Documentation (Reference)

This directory contains **reference documentation** that is **non-binding**. For binding specifications, see `specs/` (../../specs/).

## Difference: docs/ vs specs/

- **specs/**: Binding specifications that implementations MUST follow. These define contracts, requirements, and system behavior.
- **docs/**: Reference documentation that provides guidance, examples, and explanations. These are informational and may lag behind specs.

**Authority**: If docs/ conflicts with specs/, specs/ wins. Report conflicts as gaps.

## Available Documentation

### Architecture & Design
- `architecture.md` (architecture.md) - System architecture overview and design principles

### CLI Usage
- `cli_usage.md` (cli_usage.md) - Command-line interface usage guide (reference implementation)

### API Reference
- `reference/local-telemetry-api.md` (reference/local-telemetry-api.md) - Local telemetry API contract
- `reference/local-telemetry.md` (reference/local-telemetry.md) - Local telemetry implementation guide

## Contributing to docs/

Reference documentation should:
- Align with binding specs (cite spec sources)
- Provide practical examples and usage guidance
- Include diagrams and illustrations where helpful
- Be updated when specs change

**Note**: If specs/ change, docs/ should be updated to match. Outdated docs are considered gaps.

## Related
- `specs/README.md` (../specs/README.md) - Binding specifications index
- `README.md` (../README.md) - Repository overview
```

**Gap Closed When**: `docs/README.md` exists and explains docs/ purpose and navigation

---

## L-GAP-007 | MINOR | AGENT_G placeholder links in GAPS.md

**Description**: `reports/pre_impl_verification/20260126_154500/agents/AGENT_G/GAPS.md` contains placeholder links using literal word "path" as link target.

**Evidence**:
- `AGENT_G/GAPS.md:178` contains two links: `[text] (path)` and `[text] (path#anchor)`
- These are obviously placeholder/template text, not real links
- Breaks link checker (counted as 2-3 broken links)

**Context**:
These appear to be example/template text in gap descriptions showing the format for evidence links.

**Impact**:
- Minimal (template/example text)
- Contributes to broken link count
- Could confuse automated link checkers

**Proposed Fix**:

Option 1: Use code formatting for examples (not links):
```markdown
Evidence format: `path:lineStart-lineEnd` or `file.md#anchor`
```

Option 2: Use actual example paths:
```markdown
Evidence: [specs/01_system_contract.md:141-146] (../../../../../specs/01_system_contract.md)
```

Option 3: Remove placeholder links, use plain text:
```markdown
Evidence: See specs/01_system_contract.md lines 141-146
```

**Recommended**: Option 1 (code formatting) - clearest for templates

**Gap Closed When**: AGENT_G/GAPS.md contains no placeholder link targets

---

## L-GAP-008 | MINOR | Self-referential directory link in IMPLEMENTATION_KICKOFF_PROMPT.md

**Description**: `reports/pre_impl_review/20260124-102204/IMPLEMENTATION_KICKOFF_PROMPT.md:5` contains link to its own parent directory.

**Evidence**:
- Line 5: `[report directory] (../20260124-102204/)`
- Links to: `reports/pre_impl_review/20260124-102204/`
- This is the same directory the file is in (self-referential)

**Impact**:
- Minimal (one broken link)
- Likely intended to reference the directory but links are file-based in markdown

**Proposed Fix**:

Option 1: Link to a specific file in the directory:
```markdown
See `go/no-go decision` (GO_NO_GO.md) in this review.
```

Option 2: Remove link, use plain text:
```markdown
Review artifacts are in this directory (20260124-102204).
```

Option 3: Link to parent index if it exists:
```markdown
See [pre-implementation review index] (../../INDEX.md)
```

**Recommended**: Option 1 (link to GO_NO_GO.md or other key file)

**Gap Closed When**: Link points to specific file, not directory

---

## Summary by Severity

### BLOCKER (1)
- L-GAP-001: 184 broken internal links

### MAJOR (4)
- L-GAP-002: Exit code conflict (specs vs docs)
- L-GAP-003: Missing schemas/README.md
- L-GAP-004: Missing reports/README.md
- L-GAP-005: CONTRIBUTING.md is minimal
- L-GAP-006: Missing docs/README.md

### MINOR (3)
- L-GAP-007: AGENT_G placeholder links
- L-GAP-008: Self-referential link in IMPLEMENTATION_KICKOFF_PROMPT.md

---

## Remediation Priority

**Phase 1 (BLOCKER - must fix before go-live)**:
1. L-GAP-001: Fix all 184 broken links (estimated: 4-8 hours)

**Phase 2 (MAJOR - should fix before implementation)**:
2. L-GAP-002: Harmonize exit codes (estimated: 30 minutes)
3. L-GAP-003: Create schemas/README.md (estimated: 1 hour)
4. L-GAP-004: Create reports/README.md (estimated: 1 hour)
5. L-GAP-005: Expand CONTRIBUTING.md (estimated: 2 hours)
6. L-GAP-006: Create docs/README.md (estimated: 30 minutes)

**Phase 3 (MINOR - nice to have)**:
7. L-GAP-007: Fix AGENT_G placeholders (estimated: 5 minutes)
8. L-GAP-008: Fix self-referential link (estimated: 2 minutes)

**Total estimated effort**: 9-15 hours

**Critical path**: L-GAP-001 must be resolved before repository is considered professional and ready for external visibility or implementation go-live.
