# FOSS Launcher — Spec Pack + Implementation Scaffold

This repository contains **binding specifications** and a **minimal scaffold implementation** for an agent-executed system that launches a GitHub product repository onto the Hugo-based **aspose.org** website.

> Note on naming: in this repo, **“FOSS”** refers to the *product distribution* naming used by some pilot repos (e.g., “Aspose.Note FOSS for Python”), not the license of this launcher repo.

## Contents

- `specs/` — binding specs for the end-to-end launcher system ([entry point](specs/README.md))
- `plans/` — LLM-ready orchestration + taskcards ([master prompt](plans/00_orchestrator_master_prompt.md), [taskcard index](plans/taskcards/INDEX.md))
- `docs/` — reference docs (non-binding), including [architecture.md](docs/architecture.md)
- `config/` — deterministic gate toolchain pins and lint/link configs
- `configs/` — run configs (pilots + real products)
- `src/launch/**` — implementation scaffold (CLI surfaces + schema validation)
- `reports/` — required agent review artifacts (templates included)

### Documentation Navigation

**New to this repository?** Start here:
1. Read [specs/README.md](specs/README.md) for spec overview
2. Read [GLOSSARY.md](GLOSSARY.md) for terminology
3. Read [plans/00_orchestrator_master_prompt.md](plans/00_orchestrator_master_prompt.md) for implementation workflow
4. Check [plans/taskcards/INDEX.md](plans/taskcards/INDEX.md) for taskcard organization

**For implementation agents**:
- [plans/taskcards/00_TASKCARD_CONTRACT.md](plans/taskcards/00_TASKCARD_CONTRACT.md) - Binding taskcard rules
- [plans/traceability_matrix.md](plans/traceability_matrix.md) - Spec to taskcard mapping
- [TRACEABILITY_MATRIX.md](TRACEABILITY_MATRIX.md) - High-level requirement tracing

**For questions and decisions**:
- [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md) - Unresolved questions
- [ASSUMPTIONS.md](ASSUMPTIONS.md) - Documented assumptions
- [DECISIONS.md](DECISIONS.md) - Design decisions made

## What is implemented (scaffold)

The Python code in `src/launch/**` is **not** the full launcher. It intentionally implements only:

- YAML `run_config` loading + JSON-Schema validation
- RUN_DIR scaffolding per `specs/29_project_repo_structure.md`
- A scaffold `launch_validate` that runs schema/toolchain checks and records all other gates as **NOT_IMPLEMENTED** (no false passes)

Everything else (orchestrator, workers, patching, PR creation, MCP server) is implemented by the agent workforce defined in `plans/`.

## Quick start (local dev)

```bash
# Install dev tooling
make install

# Validate the spec pack itself (schemas, pinned pilot configs, toolchain lock)
make validate

# Create a scaffold RUN_DIR from a pinned pilot config
launch_run --config specs/pilots/pilot-aspose-note-foss-python/run_config.pinned.yaml

# Validate the run directory (expected to fail until full gates are implemented)
launch_validate --run_dir runs/<run_id> --profile ci
```

## Swarm Coordination (Agent Execution)

This repository is **swarm-ready** with coordination protocols for parallel agent execution.

### Before Starting
1. Read [plans/swarm_coordination_playbook.md](plans/swarm_coordination_playbook.md) - Binding rules
2. Review [plans/taskcards/STATUS_BOARD.md](plans/taskcards/STATUS_BOARD.md) - Taskcard status
3. Read [plans/taskcards/00_TASKCARD_CONTRACT.md](plans/taskcards/00_TASKCARD_CONTRACT.md) - Taskcard rules

### Validation Tools

```bash
# Validate all taskcard YAML frontmatter
python tools/validate_taskcards.py

# Generate/regenerate STATUS_BOARD
python tools/generate_status_board.py

# Check markdown link integrity
python tools/check_markdown_links.py

# Audit allowed_paths for overlaps
python tools/audit_allowed_paths.py
```

**Run after**: Any taskcard frontmatter changes or documentation updates

### Selecting a Taskcard

1. Find taskcards with `status: Ready` in STATUS_BOARD
2. Verify dependencies are `Done` (check `depends_on` field)
3. Ensure no `allowed_paths` conflict with in-progress taskcards
4. Update taskcard frontmatter: set `owner` and `status: In-Progress`
5. Regenerate STATUS_BOARD: `python tools/generate_status_board.py`

### Implementation Workflow

1. Create branch: `feat/<taskcard-id>-<slug>`
2. Follow taskcard implementation steps
3. Write evidence artifacts per `evidence_required`
4. Run acceptance checks
5. Write agent report and self-review
6. Open PR with taskcard evidence

## Implementation guidance

Start with:
- `plans/00_orchestrator_master_prompt.md`
- `plans/taskcards/INDEX.md`
- `plans/swarm_coordination_playbook.md` (for swarm execution)

All agents must write artifacts under `reports/` and include a 12-dimension self-review.

## Forensics utilities

- `scripts/forensics_catalog.py` writes an auditable tree + file catalog with hashes to `reports/forensics/`.
- `scripts/validate_spec_pack.py` runs a lightweight integrity check suitable for CI.
