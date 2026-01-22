# Phase 0: Standardization Proposal

**Date**: 2026-01-22
**Phase**: Discovery & Gap Report
**Purpose**: Propose naming templates and standardization patterns for specs/plans/taskcards

---

## Current State Analysis

### Existing Naming Conventions

#### Specs
- **Pattern**: `{number}_{topic}.md` (mostly)
- **Examples**:
  - `00_overview.md` ✓
  - `01_system_contract.md` ✓
  - `02_repo_ingestion.md` ✓
- **Exceptions**:
  - `blueprint.md` (no number)
  - `pilot-blueprint.md` (no number)
  - `state-management.md` (no number)
  - `state-graph.md` (no number)
  - `README.md` (entry point)
- **Assessment**: Generally consistent, exceptions are reasonable for meta-docs

#### Taskcards
- **Pattern**: `TC-{number}_{topic}_{worker_id}.md` for worker-specific
- **Pattern**: `TC-{number}_{topic}.md` for cross-cutting
- **Examples**:
  - `TC-400_repo_scout_w1.md` ✓
  - `TC-401_clone_and_resolve_shas.md` ✓
  - `TC-500_clients_services.md` ✓
- **Special**:
  - `00_TASKCARD_CONTRACT.md` (contract doc)
  - `INDEX.md` (index)
- **Assessment**: Highly consistent, clear numbering scheme

#### Plans
- **Pattern**: Mixed - descriptive names without numbers
- **Examples**:
  - `00_README.md` (numbered entry point)
  - `00_orchestrator_master_prompt.md` (numbered entry point)
  - `traceability_matrix.md` (no number)
  - `acceptance_test_matrix.md` (no number)
- **Assessment**: Less consistent than specs/taskcards, but small set makes this acceptable

---

## Proposed Standardization Rules

### Rule Set 1: File Naming

#### RULE-FN-001: Spec File Naming
**Pattern**: `{number}_{snake_case_topic}.md`
**Numbering**:
- `00-39`: Core system specs (as currently organized)
- `40-59`: Reserved for future extensions
- `60-79`: Reserved for platform-specific addenda
- `80-99`: Reserved for experimental/draft specs

**Exceptions Allowed**:
- `README.md` - Entry point (MUST exist)
- `blueprint.md`, `pilot-blueprint.md` - Meta-level blueprints (unnumbered acceptable)
- `state-*.md` - State-related supplementary docs (unnumbered acceptable)

**Enforcement**: SHOULD follow pattern for all new specs

#### RULE-FN-002: Taskcard File Naming
**Pattern**: `TC-{number}_{snake_case_topic}[_{worker_id}].md`
**Numbering**:
- `TC-001 to TC-099`: System bootstrap and infrastructure
- `TC-100 to TC-199`: Bootstrap layer
- `TC-200 to TC-299`: Core systems (schemas, IO, orchestrator)
- `TC-300 to TC-399`: Orchestrator and state machine
- `TC-400 to TC-499`: Worker implementations (W1-W9)
  - `TC-400-TC-409`: W1 RepoScout
  - `TC-410-TC-419`: W2 FactsBuilder
  - `TC-420-TC-429`: W3 SnippetCurator
  - `TC-430-TC-439`: W4 IA Planner
  - `TC-440-TC-449`: W5 SectionWriter
  - `TC-450-TC-459`: W6 Linker/Patcher
  - `TC-460-TC-469`: W7 Validator
  - `TC-470-TC-479`: W8 Fixer
  - `TC-480-TC-489`: W9 PR Manager
- `TC-500 to TC-599`: Cross-cutting concerns and hardening
- `TC-600 to TC-699`: Additional extensions
- `TC-700+`: Reserved for product-specific extensions

**Worker ID Suffix**:
- Format: `_w{1-9}`
- Use: Epic wrapper taskcards for workers
- Example: `TC-400_repo_scout_w1.md`

**Exceptions Allowed**:
- `00_TASKCARD_CONTRACT.md` - Contract definition
- `INDEX.md` - Taskcard index

**Enforcement**: MUST follow pattern for all taskcards

#### RULE-FN-003: Plan File Naming
**Pattern**: `{number}_{snake_case_topic}.md` for core plans, descriptive names for supporting docs
**Core Plans** (numbered):
- `00_README.md`
- `00_orchestrator_master_prompt.md`
- Additional core plans: `01_`, `02_`, etc. as needed

**Supporting Docs** (descriptive):
- `traceability_matrix.md`
- `acceptance_test_matrix.md`
- Any other planning artifacts

**Enforcement**: SHOULD follow pattern, but flexibility allowed for small plan set

#### RULE-FN-004: Report File Naming
**Pattern**: `{snake_case_topic}.md` for phase reports
**Phase Reports**:
- `inventory.md`
- `gap_analysis.md`
- `standardization_proposal.md`
- `phase-{N}_self_review.md`
- `change_log.md`
- `diff_manifest.md`
- etc.

**Agent Reports** (different pattern):
- `reports/agents/{agent_name}/{task_id}/report.md`
- `reports/agents/{agent_name}/{task_id}/self_review.md`

**Enforcement**: MUST follow pattern for phase reports

---

### Rule Set 2: Internal Structure

#### RULE-IS-001: Required Spec Sections
Every numbered spec MUST contain (at minimum):
1. **Purpose** or **Goal** - What this spec defines
2. **Scope** - What's in scope and out of scope (or Non-goals)
3. **Required Inputs** or **Inputs** (if applicable)
4. **Outputs** or **Artifacts** (if applicable)
5. **Acceptance** or **Acceptance Criteria** - How to verify compliance

**Recommended** sections:
- **Failure Modes** - What can go wrong
- **Determinism Requirements** - Stability guarantees
- **Error Handling** - How errors are managed
- **Dependencies** - What other specs/systems this relies on

**Enforcement**: Phase 1 will add missing sections

#### RULE-IS-002: Required Taskcard Sections
Every taskcard MUST contain (per existing contract):
1. `## Objective`
2. `## Required spec references`
3. `## Scope` (with `### In scope` and `### Out of scope`)
4. `## Inputs`
5. `## Outputs`
6. `## Allowed paths`
7. `## Implementation steps`
8. `## Deliverables`
9. `## Acceptance checks`
10. `## Self-review`

**Strongly Recommended**:
11. `## Preconditions / dependencies`
12. `## Test plan`
13. `## Failure modes`

**New Additions for Standardization**:
14. `## Status` - One of: `Draft | Ready | In-Progress | Complete`
15. `## Dependencies` - Links to prerequisite taskcards

**Enforcement**: Phase 2 will verify/add missing sections

#### RULE-IS-003: Required Plan Sections
Master plans MUST contain:
1. **Objective** - What the plan achieves
2. **Workflow** or **Phases** - Step-by-step execution
3. **Non-negotiable rules** - Constraints and requirements
4. **Output requirements** - What must be delivered
5. **Acceptance** or **Success criteria**

**Enforcement**: Phase 2 will verify

---

### Rule Set 3: Metadata Standards

#### RULE-MS-001: Taskcard Status Metadata
Every taskcard MUST include status metadata at the top (after title):

```markdown
# Taskcard TC-XXX — Title

**Status**: Draft | Ready | In-Progress | Complete
**Dependencies**: TC-XXX, TC-YYY (links)
**Estimated Complexity**: Low | Medium | High
**Last Updated**: YYYY-MM-DD
```

**Status Definitions**:
- **Draft**: Taskcard content incomplete or under review
- **Ready**: Implementation-ready, all sections complete
- **In-Progress**: Currently being implemented
- **Complete**: Implementation done, self-review submitted

**Enforcement**: Phase 2 will add metadata to all taskcards

#### RULE-MS-002: Spec Version Metadata
Every spec SHOULD include (recommended, not mandatory):

```markdown
# Title

**Spec Version**: v1.0 | v1.1 | etc.
**Last Updated**: YYYY-MM-DD
**Status**: Stable | Draft | Deprecated
```

**Enforcement**: Optional, nice-to-have during Phase 1

#### RULE-MS-003: Schema Version Requirements
All JSON schemas MUST include:
- `schema_version` field in schema definition
- `$id` field with stable URI
- `description` field explaining purpose

**Enforcement**: Verify during Phase 1 spec review

---

### Rule Set 4: Cross-Referencing

#### RULE-XR-001: Link Format
**Internal Links**: Use relative markdown links with readable link text
```markdown
See [02_repo_ingestion.md](../../specs/02_repo_ingestion.md) for details.
See [repo ingestion spec](../../specs/02_repo_ingestion.md) for details.
```

**Schema Links**: Link to schema file when first mentioned
```markdown
Must validate against [`repo_inventory.schema.json`](../../specs/schemas/repo_inventory.schema.json)
```

**Taskcard Links**: Link to taskcards when referencing
```markdown
Implemented in [TC-401](../../plans/taskcards/TC-401_clone_and_resolve_shas.md)
```

**Enforcement**: Phase 1-2 will add missing links

#### RULE-XR-002: Required Cross-References
**Specs MUST link to**:
- Related specs (in Dependencies or See Also section)
- Schemas they define or use
- Taskcards that implement them (via traceability matrix)

**Taskcards MUST link to**:
- Required spec references (already required)
- Dependency taskcards
- Related schemas

**Plans MUST link to**:
- Taskcards they orchestrate
- Specs they implement

**Enforcement**: Phase 1-2 improvements

---

### Rule Set 5: Terminology Consistency

#### RULE-TC-001: Use GLOSSARY Terms
All specs/plans/taskcards MUST use terms as defined in [GLOSSARY.md](../../GLOSSARY.md)

**Key Terms** (from GLOSSARY):
- **Artifact** (not "output file" or "result")
- **RUN_DIR** (not "run folder" or "execution directory")
- **Worker** (not "agent" when referring to W1-W9)
- **Orchestrator** (not "controller" or "coordinator")
- **Claim** (not "statement" or "assertion" in evidence context)
- **PatchBundle** (not "patch set" or "changes")

**Enforcement**: Phase 1 will audit and standardize terminology

#### RULE-TC-002: RFC 2119 Keywords
Use RFC 2119 keywords consistently:
- **MUST** / **REQUIRED** / **SHALL**: Absolute requirement
- **MUST NOT** / **SHALL NOT**: Absolute prohibition
- **SHOULD** / **RECOMMENDED**: Strong recommendation, but deviations allowed with justification
- **SHOULD NOT** / **NOT RECOMMENDED**: Strong advice against, but allowed with justification
- **MAY** / **OPTIONAL**: Truly optional

**Avoid**:
- "You should" → Use "You SHOULD" or "SHOULD"
- "Required" without MUST → Use "MUST" or "is required"
- "Binding" alone → Use "MUST (binding)"

**Enforcement**: Phase 1 will standardize keyword usage

---

### Rule Set 6: Acceptance Criteria Format

#### RULE-AC-001: Taskcard Acceptance Checks
Format as checkboxes with measurable criteria:

```markdown
## Acceptance checks
- [ ] {Specific outcome} {verification method}
- [ ] Tests pass: `pytest tests/test_*.py`
- [ ] Artifact validates: `jsonschema -i artifact.json schema.json`
- [ ] Agent reports written to `reports/agents/{agent}/{task_id}/`
```

**Good Examples**:
- `[ ] RepoInventory.json validates against schema`
- `[ ] Default branch resolves to concrete SHA and is recorded`
- `[ ] Tests passing: pytest exits with code 0`

**Bad Examples** (too vague):
- `[ ] Code works` ❌
- `[ ] Implementation complete` ❌
- `[ ] No bugs` ❌

**Enforcement**: Phase 2 will standardize all taskcard acceptance checks

#### RULE-AC-002: Spec Acceptance Criteria
Format as numbered list with clear validation approach:

```markdown
## Acceptance criteria
1. {Criterion} verified by {method}
2. {Criterion} validated via {test/check}
```

**Enforcement**: Phase 1 will improve spec acceptance sections

---

## Proposed File Structure Enhancements

### Current Structure
```
.
├── specs/
├── plans/
│   └── taskcards/
├── reports/
├── docs/
```

### Proposed Additions (Phase 0 - DONE)
```
.
├── OPEN_QUESTIONS.md       ✓ CREATED
├── ASSUMPTIONS.md          ✓ CREATED
├── DECISIONS.md            ✓ CREATED
├── GLOSSARY.md             ✓ CREATED
├── TRACEABILITY_MATRIX.md  ✓ CREATED
```

### Proposed Additions (Phase 1-2)
```
specs/
├── README.md (enhance with RFC2119 guidance)
├── schemas/
│   └── error_codes.catalog.yaml (NEW - if needed per gap analysis)

plans/
├── policies/
│   └── (existing policies remain)

reports/
├── phase-0_discovery/      ✓ CREATED
├── phase-1_spec-hardening/ ✓ CREATED
├── phase-2_plan-taskcard-hardening/ ✓ CREATED
├── phase-3_final-readiness/ ✓ CREATED
└── examples/ (NEW - optional, for filled report examples)
```

---

## Implementation Recommendations

### Phase 0 (Current - DONE)
- [x] Create root scaffolding files
- [x] Create reports/phase-* folder structure
- [x] Document current state in inventory.md
- [x] Identify gaps in gap_analysis.md
- [x] Propose standards in standardization_proposal.md

### Phase 1 (Specs Hardening)
1. Add missing sections to specs per RULE-IS-001
2. Standardize terminology per RULE-TC-001, RULE-TC-002
3. Add cross-references per RULE-XR-001, RULE-XR-002
4. Improve acceptance criteria per RULE-AC-002
5. Populate GLOSSARY.md with all terms from specs
6. Verify schema metadata per RULE-MS-003
7. Address P0/P1 gaps from gap_analysis.md

### Phase 2 (Plans + Taskcards Hardening)
1. Add status metadata to taskcards per RULE-MS-001
2. Verify all taskcard sections per RULE-IS-002
3. Standardize acceptance checks per RULE-AC-001
4. Add missing cross-references per RULE-XR-002
5. Verify plan structure per RULE-IS-003
6. Address P1/P2 gaps from gap_analysis.md
7. Update traceability matrix

### Phase 3 (Final Review)
1. Verify all rules applied
2. Check all cross-references resolve
3. Validate traceability completeness
4. GO/NO-GO decision

---

## Standardization Checklist Template

Use this checklist when reviewing any spec/plan/taskcard:

```markdown
### Standardization Review Checklist

#### Naming
- [ ] File name follows pattern (RULE-FN-001/002/003)
- [ ] Snake_case used consistently

#### Structure
- [ ] Required sections present (RULE-IS-001/002/003)
- [ ] Sections in standard order
- [ ] Metadata included (RULE-MS-001/002)

#### Content
- [ ] Terminology consistent with GLOSSARY (RULE-TC-001)
- [ ] RFC 2119 keywords used correctly (RULE-TC-002)
- [ ] Acceptance criteria measurable (RULE-AC-001/002)

#### Cross-References
- [ ] Internal links formatted correctly (RULE-XR-001)
- [ ] Required cross-references present (RULE-XR-002)
- [ ] All links resolve

#### Quality
- [ ] No ambiguous requirements
- [ ] No "agent will guess" scenarios
- [ ] Contradictions resolved
- [ ] Gaps addressed or documented
```

---

## Summary

This standardization proposal provides:
- **6 Rule Sets** with 15 specific rules
- **Clear naming patterns** for all document types
- **Required sections** for specs/plans/taskcards
- **Metadata standards** for tracking status
- **Cross-referencing guidelines** for navigability
- **Terminology consistency** via GLOSSARY
- **Acceptance criteria** format standardization
- **Phased implementation** plan

**Next Steps**: Apply these standards during Phase 1-2 hardening.
