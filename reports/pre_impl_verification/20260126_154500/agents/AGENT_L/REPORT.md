# AGENT_L: Links/Consistency/Repo Professionalism Audit Report

**Agent**: AGENT_L (Links/Consistency/Repo Professionalism Auditor)
**Date**: 2026-01-27
**Repository**: foss-launcher
**Commit**: (current HEAD at time of audit)

## Executive Summary

- **Total markdown files checked**: 335 files
- **Total internal links checked**: 892 links
- **Broken internal links**: 184 (❌ **BLOCKER**)
- **Duplicate/conflicting sources**: 1 conflict found (exit codes)
- **TODOs without ownership**: 0 critical unowned TODOs (all are template examples or quoted references)
- **Index accuracy issues**: 0 major issues (indexes are accurate and complete)
- **Naming consistency issues**: 0 issues (all follow conventions)
- **"Where to add what" documentation**: Partially missing (gaps identified)
- **Total gaps identified**: 8 gaps (1 BLOCKER, 4 MAJOR, 3 MINOR)
- **Overall professionalism score**: C (due to BLOCKER broken links)

### Critical Finding (BLOCKER)

**184 broken internal links found** across markdown files. This is a **STOP-THE-LINE** issue per mission rules. Broken links fall into 5 categories:

1. **Absolute path links** (129 links): Links using absolute paths like `/specs/file.md` instead of relative paths
2. **Directory links** (40 links): Links pointing to directories instead of files
3. **Broken anchors** (8 links): Links to non-existent heading anchors
4. **Line number anchors** (4 links): GitHub-style `#L123` anchors that don't work in standard markdown
5. **Missing relative files** (3 links): Legitimate broken links to files that don't exist

---

## Broken Internal Links Check

### ❌ BLOCKER: 184 Broken Links Found

Comprehensive link checking performed using automated Python script (`temp_link_checker.py`) that:
- Scanned all 335 markdown files (excluding `.venv`, `.git`, `node_modules`, `.pytest_cache`)
- Extracted 892 internal markdown links
- Validated file existence and anchor existence
- Found 184 broken links across 5 categories

#### Category 1: Absolute Path Links (129 links)

**Issue**: Many report files use absolute paths (starting with `/`) instead of relative paths. Absolute paths don't work in markdown file viewers or local file systems.

**Evidence (sample)**:
- `reports/pre_impl_review/20260126_152133_completion/FINDINGS.md:69` → `/specs/schemas/ruleset.schema.json`
- `reports/pre_impl_review/20260126_152133_completion/FINDINGS.md:70` → `/specs/rulesets/ruleset.v1.yaml`
- `reports/pre_impl_review/20260126_152133_completion/FINDINGS.md:71` → `/specs/20_rulesets_and_templates_registry.md`
- `reports/agents/PRE_IMPL_HEALING_AGENT/PRE_IMPL_HEALING/report.md:60` → `/specs/schemas/run_config.schema.json`
- `reports/agents/PRE_IMPL_HEALING_AGENT/PRE_IMPL_HEALING/report.md:80` → `/specs/schemas/validation_report.schema.json`

**Affected files**: Primarily recent pre-implementation review reports in `reports/pre_impl_review/20260126_152133_completion/` and `reports/agents/PRE_IMPL_HEALING_AGENT/`

**Impact**: Links appear broken in markdown viewers, GitHub UI, and local development

#### Category 2: Directory Links (40 links)

**Issue**: Links point to directories instead of specific files. Markdown links require file targets, not directory targets.

**Evidence (sample)**:
- `reports/orchestrator_master_review.md:49` → `agents/hygiene-agent/H1_WINDOWS_RESERVED_NAMES/` (should link to `report.md` or `index.md`)
- `reports/orchestrator_master_review.md:87` → `agents/policy-agent/H2_PINNED_REFS_ALIGNMENT/` (should link to `report.md`)
- `specs/README.md:139` → `pilots/pilot-aspose-3d-foss-python/` (should link to `run_config.pinned.yaml` or README)
- `reports/phase-0_discovery/inventory.md:89` → `../../specs/schemas/` (should link to specific schema or index)
- `reports/phase-0_discovery/inventory.md:182` → `../../reports/` (should link to README or index)

**Pattern**: Many older phase reports link to directories when they should link to specific files within those directories

#### Category 3: Broken Anchors (8 links)

**Issue**: Links reference heading anchors that don't exist in target files, usually due to heading format differences.

**Evidence**:

1. `reports/agents/hardening-agent/COMPLIANCE_HARDENING/run_20260123_strict_compliance/compliance_matrix.md:28`
   - Link: `specs/34_strict_compliance_guarantees.md#a-input-immutability---pinned-commit-shas`
   - Actual heading: `### A) Input Immutability - Pinned Commit SHAs`
   - Issue: Anchor uses `---` (3 hyphens) but heading converts to `---` with parenthesis removed. Anchor format mismatch.

2. `reports/pre_impl_review/20260124-102204/go_no_go.md:64`
   - Link: `gaps_and_blockers.md#BLOCKER-A-spec-classification`
   - Issue: Anchor not found (heading may have been renamed or removed)

3. Similar anchor mismatches for guarantees E, F, G, H, L in `compliance_matrix.md`

#### Category 4: Line Number Anchors (4 links)

**Issue**: Links use GitHub-style line number anchors (`#L123` or `#L7-L8`) which don't work in standard markdown.

**Evidence**:
- `reports/phase-0_discovery/gap_analysis.md:51` → `../../specs/01_system_contract.md#L86`
- `reports/pre_impl_review/20260124-192034/go_no_go.md:133` → `../../../.github/workflows/ci.yml#L7-L8`
- `reports/pre_impl_review/20260124-192034/go_no_go.md:136` → `../../../pyproject.toml#L51-L60`
- `reports/pre_impl_review/20260124-192034/go_no_go.md:137` → `../../../DEVELOPMENT.md#L107-L121`

**Impact**: These links only work on GitHub web UI, not in local markdown viewers or editors

#### Category 5: Missing Relative Files (3 links)

**Issue**: Links to files that legitimately don't exist (not absolute path or directory issues).

**Evidence**:
- `reports/pre_impl_verification/20260126_154500/agents/AGENT_G/GAPS.md:178` → `path` (appears to be placeholder text, not a real link)
- `reports/pre_impl_review/20260124-102204/IMPLEMENTATION_KICKOFF_PROMPT.md:5` → `../20260124-102204/` (self-referential directory link)

**Note**: Two of these appear to be template placeholders in AGENT_G's GAPS.md file (uses literal word "path" as link target).

### Link Checking Methodology

**Tool Used**: Custom Python script (`temp_link_checker.py`) implementing:
1. Recursive markdown file discovery (excluding dependencies)
2. Regex-based link extraction: `\[([^\]]+)\]\(([^)]+)\)`
3. Internal link filtering (excludes `http://`, `https://`, `mailto:`)
4. Relative path resolution from source file location
5. File existence validation
6. Anchor extraction via heading parsing
7. Anchor existence validation with GitHub-style slug conversion

**Full results**: `temp_link_check_results.json` (892 links analyzed)
**Categorized results**: `temp_broken_links_categorized.json`

---

## Duplicate/Conflicting Sources Check

### ✅ Most Concepts Are Consistent

Checked for duplicate definitions of key concepts across specs and docs. Most definitions are consistent and cross-referenced correctly.

### ❌ MAJOR: Exit Code Conflict (Conflicting Definitions)

**Concept**: CLI Exit Codes
**Conflict Found**: YES

**Source 1**: `specs/01_system_contract.md:141-146`
```markdown
### Exit codes (recommended)
- `0` success
- `2` validation/spec/schema failure
- `3` policy violation (allowed_paths, governance)
- `4` external dependency failure (commit service, telemetry API)
- `5` unexpected internal error
```

**Source 2**: `docs/cli_usage.md:69-72`
```markdown
- **Exit Codes**:
  - `0` - Success
  - `1` - Validation failure
  - `2` - Critical error
```

**Source 3**: `docs/cli_usage.md:129-131` (validate command)
```markdown
- **Exit Codes**:
  - `0` - All gates pass
  - `1` - One or more gates fail
```

**Conflict**:
- Spec says validation failure = exit `2`
- Docs say validation failure = exit `1`
- This is a **source of truth conflict** where binding spec and reference docs contradict each other

**Impact**: Implementers may follow docs instead of specs, creating non-compliant implementation

**Resolution Required**: Harmonize definitions. Since `specs/` are BINDING and `docs/` are REFERENCE, `docs/cli_usage.md` must be updated to match `specs/01_system_contract.md`.

### ✅ Other Key Concepts Checked (Consistent)

Checked the following concepts for consistency across specs/docs:

| Concept | Primary Source | Secondary References | Status |
|---------|---------------|----------------------|--------|
| RUN_DIR structure | specs/29_project_repo_structure.md | docs/architecture.md, README.md | ✅ Consistent |
| Virtual environment policy | specs/00_environment_policy.md | README.md, DEVELOPMENT.md | ✅ Consistent |
| Taskcard structure | plans/taskcards/00_TASKCARD_CONTRACT.md | Multiple taskcards | ✅ Consistent |
| Schema locations | specs/README.md | Multiple spec files | ✅ Consistent |
| Worker pipeline (W1-W9) | specs/21_worker_contracts.md | plans/taskcards/INDEX.md | ✅ Consistent |

---

## Naming/Template Consistency Check

### ✅ Consistent Naming: Taskcards

**Convention**: `TC-XXX_descriptive_name.md`

**Evidence**:
```bash
$ ls plans/taskcards/TC-*.md | wc -l
41
```

All 41 taskcards follow the `TC-XXX` prefix convention. No anomalies found.

**Special files** (correctly named, not taskcards):
- `00_TASKCARD_CONTRACT.md` (template/contract)
- `INDEX.md` (index file)
- `STATUS_BOARD.md` (auto-generated status board)

### ✅ Consistent Naming: Specs

**Convention**: `NN_descriptive_name.md` (two-digit prefix)

**Evidence**:
```bash
$ ls specs/*.md
specs/00_environment_policy.md
specs/00_overview.md
specs/01_system_contract.md
specs/02_repo_ingestion.md
...
specs/34_strict_compliance_guarantees.md
```

All 41 spec files follow the `NN_` two-digit prefix convention. No anomalies found.

### ✅ Consistent Naming: Schemas

**Convention**: `name.schema.json`

**Evidence**: All 22 schema files in `specs/schemas/` follow the `.schema.json` suffix convention:
- `run_config.schema.json`
- `validation_report.schema.json`
- `product_facts.schema.json`
- etc.

### ✅ Template Consistency: Taskcards

**Contract**: `plans/taskcards/00_TASKCARD_CONTRACT.md`

**Checked**: Sample taskcards (`TC-100`, `TC-200`, `TC-401`) for compliance with contract

**Required sections** (from contract):
- YAML frontmatter with required fields
- Objective
- Required spec references
- Scope (In scope / Out of scope)
- Inputs / Outputs
- Allowed paths
- Implementation steps
- Failure modes
- Task-specific review checklist
- Deliverables
- Acceptance checks
- Self-review

**Result**: ✅ All sampled taskcards follow the contract template consistently

### ✅ No Naming Issues Found

No gaps identified in naming or template consistency.

---

## "Where to Add What" Check

### ✅ Documented: Where to Add Specs

**Location**: `specs/README.md`
**Evidence**: README provides clear classification and organization:
- Lists all 49 specs (BINDING and REFERENCE)
- Categorizes by domain (Core System, Ingestion & Evidence, Planning & Writing, etc.)
- Clear navigation table with document numbers and descriptions

### ✅ Documented: Where to Add Taskcards

**Location**: `plans/taskcards/INDEX.md`
**Evidence**: INDEX.md provides:
- Clear pipeline mapping (W1-W9)
- Bootstrap, cross-cutting, and critical hardening sections
- Suggested landing order
- Reference to `00_TASKCARD_CONTRACT.md` for taskcard rules

### ⚠️ MAJOR: Where to Add Schemas - Partially Documented

**Location**: `specs/README.md:142-153` mentions schemas
**Issue**: No dedicated `specs/schemas/README.md` explaining:
- How to add a new schema
- Schema naming conventions (beyond `.schema.json` suffix)
- Schema validation requirements
- Relationship between schemas and specs

**Impact**: Contributors may not know how to properly add or version schemas

### ⚠️ MAJOR: Where to Report Findings - Partially Documented

**Current**: Multiple places mention reports directory:
- `README.md:15` mentions `reports/` contains agent review artifacts
- `CONTRIBUTING.md:10` says "write reports to `reports/`"
- `reports/templates/` contains templates

**Issue**: No `reports/README.md` explaining:
- Report directory structure
- Which report templates to use when
- Where to place different types of reports (agent reports, phase reports, forensics)
- Report naming conventions

**Impact**: Agent reports are somewhat inconsistent in structure/location

### ⚠️ MAJOR: Where to Add Documentation - Not Documented

**Issue**: No guidance on where to add different types of documentation:
- When to add to `docs/` vs `specs/` vs root markdown files
- Whether `docs/` should have an index
- How reference docs relate to binding specs

### ⚠️ MINOR: Contributing Guide is Minimal

**Location**: `CONTRIBUTING.md` (20 lines)

**Current content**:
- Basic ground rules (4 points)
- Make commands for development

**Missing**:
- How to add specs (where, naming, what requires taskcards)
- How to add taskcards (frontmatter requirements, STATUS_BOARD regeneration)
- How to add schemas (validation, versioning)
- How to structure reports
- PR submission guidelines
- Review process

**Impact**: External contributors may not understand repo conventions

---

## TODOs Without Ownership Check

### ✅ No Unowned TODOs Found (Critical)

Searched for `TODO`, `FIXME`, and `XXX` in all markdown files:
```bash
$ rg -n "TODO|FIXME|XXX" --type md | wc -l
89
```

**Analysis**: All 89 instances fall into these categories:

1. **Template examples** (not actual TODOs):
   - `TC-XXX` placeholders in prompt templates
   - Example TODO syntax in guidelines
   - Quoted TODO references in documentation

2. **Prohibition statements** (not TODOs to do):
   - "No `TODO` / `PIN_ME` / `NotImplemented` in production" (specs/34, multiple taskcards)
   - Grep commands checking for TODOs
   - Checklist items about eliminating TODOs

3. **Quoted/reference TODOs**:
   - `specs/03_product_facts_and_evidence.md:106`: Mentions `# TODO:` as evidence type in product repos (not our TODO)

**Evidence (sample)**:
```
CLAUDE_CODE_IMPLEMENTATION_PROMPT.md:202: cat plans/taskcards/TC-XXX_*.md
CLAUDE_CODE_STRICT_PROMPT.md:220: - [x] No `PIN_ME`, `TODO`, or `NotImplemented` in production code
plans/00_orchestrator_master_prompt.md:87: - Ensure any TODO/placeholder tokens are eliminated.
specs/03_product_facts_and_evidence.md:106: | 4 | **Implementation docs** | `*_IMPLEMENTATION.md`, `ARCHITECTURE.md`, inline `# TODO:` | ...
```

### ✅ No Gaps: All TODOs Are Contextual or Examples

No unowned, vague, or actionable TODOs found requiring owner assignment.

---

## Indexing Check

### ✅ specs/README.md: Complete and Accurate

**Status**: ✅ Complete

**Evidence**:
- Lists all 49 specs (both BINDING and REFERENCE)
- Clear categorization by domain
- Navigation table with links to all specs
- Spec classification explained (BINDING vs REFERENCE)
- Pilot project references
- Schema listing

**Cross-check**: All spec files in `specs/*.md` are listed in README

### ✅ plans/taskcards/INDEX.md: Complete and Accurate

**Status**: ✅ Complete

**Evidence**:
- Lists all taskcards organized by pipeline stage (W1-W9)
- Bootstrap and cross-cutting sections
- Clear dependency structure
- Suggested landing order
- Reference to taskcard contract

**Cross-check**: All taskcard files in `plans/taskcards/TC-*.md` are listed in INDEX

### ✅ plans/taskcards/STATUS_BOARD.md: Complete and Auto-Generated

**Status**: ✅ Complete (auto-generated)

**Evidence**:
- Auto-generated by `tools/generate_status_board.py`
- Includes warning: "Do not edit manually"
- Lists all 41 taskcards with status, owner, dependencies
- Last generated: 2026-01-27 11:40:49 UTC (recent)
- Summary statistics: 41 total, 2 Done, 39 Ready

**Note**: This file is the single source of truth for taskcard status, generated from YAML frontmatter

### ⚠️ MINOR: docs/ Has No Index

**Issue**: `docs/` directory contains:
- `architecture.md`
- `cli_usage.md`
- `reference/local-telemetry.md`
- `reference/local-telemetry-api.md`

But no `docs/README.md` or `docs/INDEX.md` to guide navigation.

**Impact**: Minor - docs are referenced from main README, but docs directory itself lacks internal navigation

### ✅ No Index Accuracy Issues

All existing indexes (specs/README.md, plans/taskcards/INDEX.md, STATUS_BOARD.md) are complete, accurate, and up-to-date.

---

## Additional Findings

### ✅ Duplicate Filenames Are Intentional

Found 23 duplicate markdown filenames across the repository (e.g., multiple `README.md`, `report.md`, `GAPS.md` files).

**Analysis**: These are intentional and appropriate:
- `README.md` appears in multiple directories (standard practice)
- `report.md` and `GAPS.md` appear in multiple agent report directories (expected pattern)
- `self_review.md` appears per agent (expected pattern)

**No issues**: Context makes each file unique.

### ✅ GLOSSARY.md Exists and Is Used

**Location**: `GLOSSARY.md` (root)
**References**: Mentioned in README as key documentation
**Usage**: Terms like "RUN_DIR", "Worker", "Gate", "TruthLock" are defined and used consistently

### ✅ Contributing Files Exist

**Files found**:
- `CONTRIBUTING.md` (exists, but minimal)
- `CODE_OF_CONDUCT.md` (exists)

---

## Summary Statistics

- **Total markdown files**: 335
- **Files with broken links**: 81 unique source files (24% of total)
- **Total broken links**: 184
- **Broken link types**:
  - Absolute paths: 129 (70%)
  - Directory links: 40 (22%)
  - Broken anchors: 8 (4%)
  - Line number anchors: 4 (2%)
  - Missing relative files: 3 (2%)
- **Duplicate definitions**: 1 conflict (exit codes)
- **Unowned TODOs**: 0 critical
- **Index inaccuracies**: 0 critical
- **Naming inconsistencies**: 0
- **Missing "where to add what" docs**: 3 areas (schemas, reports, general contributing)

### Overall Professionalism Score: C

**Rationale**:
- **Strong**: Naming conventions, template consistency, index accuracy, no unowned TODOs
- **Critical Blocker**: 184 broken internal links (across 81 files)
- **Major Issues**: Exit code conflict, missing contributor guidance
- **Impact**: Repository is well-organized but has significant link hygiene issues that hurt navigation and professionalism

**Grade breakdown**:
- A = Perfect (0 broken links, no conflicts, complete documentation)
- B = Excellent (1-10 broken links, minor conflicts)
- C = Good with issues (11-200 broken links OR major conflicts) ← **Current**
- D = Needs improvement (201+ broken links, multiple major conflicts)
- F = Unprofessional (broken repo structure, incoherent organization)

---

## Recommendations

### Priority 1 (BLOCKER): Fix Broken Links

1. **Absolute path links** (129): Convert to relative paths
   - Script: Could automate with find/replace
   - Focus on: `reports/pre_impl_review/20260126_152133_completion/` and `reports/agents/PRE_IMPL_HEALING_AGENT/`

2. **Directory links** (40): Add specific file targets
   - Change `[link] (dir/)` to `[link] (dir/report.md)` or `[link] (dir/README.md)`
   - Focus on: `reports/orchestrator_master_review.md`, `specs/README.md`, phase reports

3. **Broken anchors** (8): Fix heading anchor references
   - Verify actual heading format in target files
   - Update anchor slugs to match GitHub's slug generation (spaces→hyphens, remove punctuation)

4. **Line number anchors** (4): Remove or replace with section anchors
   - Convert `file.md#L123` to `file.md#section-heading` or remove anchor

5. **Missing files** (3): Fix placeholder links in AGENT_G GAPS.md

### Priority 2 (MAJOR): Resolve Exit Code Conflict

Update `docs/cli_usage.md` to match `specs/01_system_contract.md`:
- Validation failure: exit `2` (not `1`)
- Add policy violation: exit `3`
- Add external dependency failure: exit `4`
- Add internal error: exit `5`

### Priority 3 (MAJOR): Add "Where to Add What" Documentation

1. Create `specs/schemas/README.md` explaining schema addition process
2. Create `reports/README.md` explaining report structure and templates
3. Expand `CONTRIBUTING.md` with detailed contribution guidelines

### Priority 4 (MINOR): Add docs/ Index

Create `docs/README.md` or `docs/INDEX.md` for internal navigation

---

## Conclusion

The repository demonstrates **strong organizational structure** with consistent naming, accurate indexes, and clear templates. However, **184 broken internal links constitute a BLOCKER** for pre-implementation readiness. These broken links hurt navigation, professionalism, and maintainability.

The repository is **NOT READY** for go-live until broken links are addressed. This is a stop-the-line finding per Agent L mission rules.

**Estimated remediation effort**:
- Link fixes: 4-8 hours (mostly automated, some manual verification)
- Exit code harmonization: 30 minutes
- Documentation additions: 2-3 hours

**Post-fix validation**: Re-run `temp_link_checker.py` to verify 0 broken links remain.
