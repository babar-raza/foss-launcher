# Reports — Evidence & Review Artifacts

This directory contains all **review artifacts**, **evidence**, and **self-assessments** produced by agents, orchestrators, and verification workflows.

## Overview

The FOSS Launcher follows a **mandatory evidence protocol**: all agent work must be auditable through structured reports. During implementation, every agent writes evidence here.

## Required Directory Layout

```
reports/
├── README.md (this file)
├── STATUS.md - Current pre-implementation status tracker
├── CHANGELOG.md - Update history for reports directory
├── templates/ - Report templates for agents/orchestrators
│   ├── agent_report.md - Agent implementation report template
│   ├── orchestrator_master_review.md - Orchestrator review template
│   └── self_review_12d.md - 12-dimension self-review template
├── agents/ - Agent execution artifacts
│   └── <agent_name>/
│       └── <task_id>/
│           ├── run_<timestamp>/
│           │   ├── plan.md
│           │   ├── changes.md
│           │   ├── evidence.md
│           │   ├── self_review.md
│           │   ├── commands.sh
│           │   └── artifacts/
│           ├── report.md (legacy, use run_*/evidence.md)
│           └── self_review.md (legacy, use run_*/self_review.md)
├── pre_impl_verification/ - Pre-implementation readiness audits
│   └── <timestamp>/
│       ├── INDEX.md - Main verification report
│       ├── GAPS.md - Consolidated gap list
│       ├── HEALING_PROMPT.md - Gap remediation instructions
│       └── agents/ - Individual agent reports
├── bootstrap/ - Initial repository setup
├── forensics/ - Repository integrity catalogs
└── phase-*/ - Historical phase completion reports
```

## Mandatory Evidence Files

Every agent run MUST produce these artifacts in `agents/<AGENT_NAME>/<TASK_ID>/run_<timestamp>/`:

### 1. plan.md (Pre-Execution Plan)
Document assumptions, steps, risks, rollback strategy before starting work.

**Required Sections**: Mission summary, task breakdown, execution order, risk assessment, rollback strategy, validation plan, deliverables checklist, success criteria, assumptions, dependencies, timeline estimate.

### 2. changes.md (File Modification Log)
List all files created, modified, or deleted with before/after excerpts.

**Required Content**: Complete list of affected files (absolute paths), operation type (CREATE/UPDATE/DELETE), before/after excerpts, rationale for each change.

### 3. evidence.md (Command & Output Log)
Capture all commands executed and their outputs (stdout/stderr).

**Required Content**: All commands run (copy-pasteable), full stdout/stderr for each command, validation results, screenshots if applicable.

### 4. self_review.md (12-Dimension Assessment)
Agent self-assessment using 12-dimension rubric from `reports/templates/self_review_12d.md`.

**Required Dimensions** (all must be ≥ 4/5 for PASS):
1. Coverage, 2. Correctness, 3. Evidence, 4. Test Quality, 5. Maintainability, 6. Safety, 7. Security, 8. Reliability, 9. Observability, 10. Performance, 11. Compatibility, 12. Docs/Specs Fidelity

### 5. commands.sh (Executable Command Log)
Append-only log of all bash commands executed.

### 6. artifacts/ (Logs & Outputs)
Store command outputs, logs, screenshots, intermediate files.

## Naming Conventions

### Agent Directories
- Format: `AGENT_<LETTER>` (e.g., `AGENT_D` = Docs & Specs, `AGENT_R` = Requirements)
- See [plans/swarm_coordination_playbook.md](../plans/swarm_coordination_playbook.md) for agent roles

### Task Directories
- Format: `<WAVE_OR_TASK_ID>` (e.g., `WAVE1_QUICK_WINS`, `TC-480`)
- Use descriptive names for multi-task efforts, taskcard IDs for single-taskcard execution

### Run Directories
- Format: `run_<YYYYMMDD_HHMMSS>` (e.g., `run_20260127_131045`)
- Timestamp in PKT timezone (UTC+5)
- One run directory per execution attempt

## Report Templates

All templates are in `reports/templates/`:

| Template | Purpose | Used By |
|----------|---------|---------|
| `agent_report.md` | Agent implementation report | All agents |
| `orchestrator_master_review.md` | Orchestrator review of agent work | Orchestrator |
| `self_review_12d.md` | 12-dimension self-assessment | All agents |

**Usage**:
```bash
# Copy template to agent run directory
cp reports/templates/self_review_12d.md \
   reports/agents/AGENT_D/<TASK_ID>/run_<timestamp>/self_review.md
```

## Rules

### Evidence Requirements
- **Every taskcard** produces `plan.md`, `changes.md`, `evidence.md`, `self_review.md`, `commands.sh`, `artifacts/`
- **Self-review** uses 12-dimension template from `reports/templates/self_review_12d.md`
- **Orchestrator** writes `reports/orchestrator_master_review.md` after reviewing agent work
- **NO work is complete** without all 6 required files and 12-dimension scores

### Pass Criteria
- **PASS**: ALL 12 dimensions ≥ 4/5 in self_review.md
- **FAIL**: Any dimension < 4 triggers HARDENING_TICKET.md and return to agent
- **Escalation**: If stuck twice, escalate to different agent

### Git Integration
Reports are **tracked in Git** for audit trail:
```bash
git add reports/agents/AGENT_D/<TASK_ID>/run_<timestamp>/
git commit -m "docs: AGENT_D completes <TASK_ID> (12d score: 4.8/5)"
```

**DO NOT** commit sensitive data (credentials, tokens) in reports.

## Status Tracking

- **Current Status**: `reports/STATUS.md` - Pre-implementation progress, active tasks, blockers
- **Change Log**: `reports/CHANGELOG.md` - Update history, completed runs, milestones

## Verification Reports

Pre-implementation verification reports are in `pre_impl_verification/<timestamp>/`:
- **INDEX.md** - Main report with executive summary
- **GAPS.md** - Consolidated gap list (BLOCKER, MAJOR, MINOR severity)
- **HEALING_PROMPT.md** - Step-by-step remediation instructions
- **agents/** - Individual agent reports (AGENT_R, AGENT_S, AGENT_C, etc.)

## Forensics & Integrity

The `reports/forensics/` directory contains repository integrity catalogs:
```bash
# Generate forensics catalog
python scripts/forensics_catalog.py
# Output: reports/forensics/<timestamp>/tree.txt, catalog.csv
```

**Use Cases**: Verify repository integrity before/after agent runs, detect unexpected modifications, audit swarm execution safety.

## References

- **Taskcard Contract**: [plans/taskcards/00_TASKCARD_CONTRACT.md](../plans/taskcards/00_TASKCARD_CONTRACT.md)
- **Swarm Playbook**: [plans/swarm_coordination_playbook.md](../plans/swarm_coordination_playbook.md)
- **Orchestrator Prompt**: [plans/00_orchestrator_master_prompt.md](../plans/00_orchestrator_master_prompt.md)
- **Self-Review Guide**: [plans/prompts/agent_self_review.md](../plans/prompts/agent_self_review.md)
