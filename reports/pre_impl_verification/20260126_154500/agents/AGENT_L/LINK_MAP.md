# AGENT_L: Internal Link Map

**Purpose**: Document which files reference which other files, showing the repository's internal link structure and most interconnected documents.

**Note**: This map shows VALID internal links only. See GAPS.md L-GAP-001 for 184 broken links.

---

## Most Referenced Files (Top Targets)

Files that are linked to most frequently from other documents:

### 1. specs/README.md
**Referenced by**: 9 files
- README.md (root entry point)
- docs/cli_usage.md (binding spec reference)
- docs/reference/local-telemetry.md (system architecture link)
- Multiple pre-implementation review reports
- Phase reports

**Why**: Primary entry point to binding specifications

### 2. plans/taskcards/INDEX.md
**Referenced by**: 6 files
- README.md (taskcard organization)
- plans/taskcards/STATUS_BOARD.md
- TRACEABILITY_MATRIX.md
- Multiple orchestrator and phase reports

**Why**: Primary taskcard navigation and organization

### 3. plans/taskcards/00_TASKCARD_CONTRACT.md
**Referenced by**: 5 files
- README.md (binding taskcard rules)
- plans/taskcards/INDEX.md (contract reference)
- Multiple agent reports (compliance verification)

**Why**: Binding rules for all taskcard implementation

### 4. specs/01_system_contract.md
**Referenced by**: 8 files
- docs/cli_usage.md (exit codes, error handling)
- specs/09_validation_gates.md (error handling dependency)
- Multiple taskcards (system contract compliance)
- TRACEABILITY_MATRIX.md

**Why**: Core system contracts, exit codes, error codes

### 5. specs/00_environment_policy.md
**Referenced by**: 7 files
- README.md (venv policy reference)
- DEVELOPMENT.md (policy enforcement)
- docs/cli_usage.md (prerequisites)
- plans/00_orchestrator_master_prompt.md

**Why**: Mandatory virtual environment policy (`.venv` enforcement)

---

## Most Linking Files (Top Sources)

Files that contain the most internal links to other documents:

### 1. specs/README.md
**Links to**: 41 spec files
- All specs in structured navigation tables
- Pilot configurations
- Schema references

**Why**: Comprehensive index of all specifications

### 2. TRACEABILITY_MATRIX.md
**Links to**: 30+ files
- Links specs to taskcards
- Links requirements to implementations
- Cross-references plans and specs

**Why**: Central traceability hub

### 3. README.md (root)
**Links to**: 20+ files
- Entry points (specs/, plans/, docs/)
- Key documentation (GLOSSARY, CONTRIBUTING, etc.)
- Quick navigation to major sections

**Why**: Repository entry point and primary navigation

### 4. plans/taskcards/STATUS_BOARD.md
**Links to**: Potentially 41 taskcard files (via auto-generation)
- Note: STATUS_BOARD is auto-generated, doesn't contain many direct links in current version
- Links exist in frontmatter references

**Why**: Single source of truth for taskcard status

### 5. docs/cli_usage.md
**Links to**: 10+ files
- Specs for binding contracts (exit codes, validation gates)
- README for installation
- Taskcards for implementation reference

**Why**: Comprehensive CLI usage guide with spec references

---

## Link Clusters (Highly Interconnected Areas)

### Cluster 1: Spec Ecosystem
**Core files**:
- specs/README.md (hub)
- specs/01_system_contract.md (foundational)
- specs/00_environment_policy.md (mandatory policy)
- specs/09_validation_gates.md (quality gates)
- specs/29_project_repo_structure.md (project layout)

**Pattern**: Specs heavily cross-reference each other for dependencies and context. Most binding specs link to 3-5 other specs.

### Cluster 2: Taskcard Ecosystem
**Core files**:
- plans/taskcards/INDEX.md (hub)
- plans/taskcards/00_TASKCARD_CONTRACT.md (rules)
- plans/taskcards/STATUS_BOARD.md (status)
- Individual TC-XXX files (41 taskcards)

**Pattern**: Taskcards reference their dependencies (other taskcards) and required specs. Less cross-linking than specs.

### Cluster 3: Root Documentation
**Core files**:
- README.md (entry point)
- CONTRIBUTING.md (contribution rules)
- GLOSSARY.md (terminology)
- TRACEABILITY_MATRIX.md (requirement mapping)
- DEVELOPMENT.md (dev guide)

**Pattern**: Root docs create navigation web, linking to major sections and entry points.

### Cluster 4: Reports (Weak Cluster)
**Core files**:
- reports/templates/ (templates)
- reports/agents/**/report.md (agent deliverables)
- reports/phase-* (phase reviews)

**Pattern**: Reports REFERENCE specs/taskcards but don't heavily interlink with each other. Mostly outward links to specs/plans.

---

## Link Health by Directory

Analysis of internal link health by directory:

### specs/ - HEALTHY (mostly)
- **Total links**: ~150 internal links
- **Broken**: 8 links (5%)
- **Issues**: Mostly broken anchors to other specs (heading format mismatches)
- **Grade**: A- (excellent)

### plans/ - HEALTHY
- **Total links**: ~80 internal links
- **Broken**: 2 links (2%)
- **Issues**: Directory links instead of files
- **Grade**: A (excellent)

### docs/ - HEALTHY
- **Total links**: ~15 internal links
- **Broken**: 0 links (0%)
- **Grade**: A+ (perfect)

### reports/ - UNHEALTHY ⚠️
- **Total links**: ~550 internal links (reports are link-heavy)
- **Broken**: ~174 links (32%)
- **Issues**:
  - Absolute path links (majority)
  - Directory links
  - Broken anchors in older reports
- **Grade**: D (needs significant remediation)

**Key Finding**: Reports directory accounts for 94% of all broken links (174/184). Recent reports (pre_impl_review, PRE_IMPL_HEALING_AGENT) use absolute paths extensively.

---

## Cross-Directory Linking Patterns

### Root → specs/
- **Pattern**: Root docs (README, TRACEABILITY_MATRIX) heavily link to specs
- **Health**: Excellent (0 broken links)

### Root → plans/
- **Pattern**: Root docs link to master prompts, taskcard indexes
- **Health**: Excellent (0 broken links)

### specs/ → specs/
- **Pattern**: Heavy cross-referencing (dependencies, related specs)
- **Health**: Good (few broken anchors)

### docs/ → specs/
- **Pattern**: Reference docs cite binding specs
- **Health**: Excellent (0 broken links)

### reports/ → specs/
- **Pattern**: Agent reports cite specs for evidence
- **Health**: POOR (absolute path links broken)

### reports/ → plans/
- **Pattern**: Agent reports reference taskcards and orchestrator prompts
- **Health**: POOR (absolute path links broken)

### taskcards → specs/
- **Pattern**: Taskcards reference required specs
- **Health**: Excellent (0 broken links)

---

## Orphan Files (Not Linked From Anywhere)

Files that exist but are not linked to by any other markdown file:

**Note**: This analysis is limited. Many files may be linked from external sources (GitHub README, CI configs, etc.) or are standalone reports.

### Likely Orphans (candidates for indexing):
- Various older phase reports (phase-0, phase-1, phase-2) may not be linked from current docs
- Some forensic reports in `reports/forensics/` (if they exist)
- Individual agent reports (may not be cross-linked, only referenced by orchestrator)

**Action**: Not a gap—most reports are deliberately standalone evidence, not meant to be navigated to from other docs.

---

## Dead-End Files (Link To Others, Not Linked From Others)

Files that link out but are not entry points:

- Most individual agent reports (`reports/agents/*/*/report.md`)
- Many phase self-reviews
- Change logs and gap analyses

**Pattern**: Reports are leaf nodes—they cite evidence but aren't meant to be navigated hubs.

---

## Recommended Navigation Improvements

### 1. Create reports/INDEX.md
Link to major phase reports and agent findings for discoverability.

### 2. Create docs/README.md
Internal index for docs/ directory (see GAPS.md L-GAP-006)

### 3. Fix Absolute Path Links in Reports
Convert 129 absolute path links to relative paths (see GAPS.md L-GAP-001)

### 4. Add File Targets to Directory Links
40 directory links should point to specific files (see GAPS.md L-GAP-001)

---

## Link Statistics Summary

- **Total markdown files**: 335
- **Total internal links analyzed**: 892
- **Broken links**: 184 (20.6%)
- **Valid links**: 708 (79.4%)
- **Most linked file**: specs/README.md (9 inbound links)
- **Most linking file**: specs/README.md (41+ outbound links)
- **Healthiest directory**: docs/ (0% broken links)
- **Unhealthiest directory**: reports/ (32% broken links)

---

## Methodology

**Link Extraction**:
- Regex: `\[([^\]]+)\]\(([^)]+)\)`
- Filtered for internal links (exclude http://, https://, mailto:)

**Link Validation**:
- File existence check
- Anchor existence check (heading parsing)
- Relative path resolution

**Tools**:
- `temp_link_checker.py` (comprehensive link checker)
- `temp_analyze_broken_links.py` (categorization and analysis)

**Results Saved**:
- `temp_link_check_results.json` (full results)
- `temp_broken_links_categorized.json` (categorized analysis)

---

## Conclusion

The repository has a **strong core link structure** (root docs ↔ specs ↔ plans) with excellent health in primary navigation areas. However, the **reports directory has severe link health issues** (32% broken links), primarily due to recent reports using absolute paths instead of relative paths.

**Priority**: Fix reports/ directory links (L-GAP-001) to restore overall repository link health to professional standards.
