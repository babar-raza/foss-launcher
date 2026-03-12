# docs/ — Operational Guides

This directory has two layers:
- **`docs/usage/`** — how to **use** the system today (operators)
- **`docs/guides/`** — how to **build and extend** the system (agents/developers)

Neither layer is a protected path. No taskcard is required to update these files.
Updating them promptly is required — see ownership map below.

---

## Usage Guides (`docs/usage/`)

For operators running the pipeline.

| Guide | When to reach for it |
|-------|----------------------|
| [quickstart.md](usage/quickstart.md) | First time setup; install, configure, first run |
| [cli.md](usage/cli.md) | Full CLI reference — every command and flag |
| [configuration.md](usage/configuration.md) | Pilot YAML fields, LLM defaults, intake config, families |
| [workflows.md](usage/workflows.md) | Step-by-step recipes: new repo, batch, heal, deploy |
| [skills.md](usage/skills.md) | When and how to invoke operator skills (SKL-2xx); reading quality signals; new-family sequence |

---

## Developer Guides (`docs/guides/`)

For agents implementing features or extending the system.

| Guide | When to reach for it |
|-------|----------------------|
| [ops-debug.md](guides/ops-debug.md) | Pipeline run failed; reading evaluation_report.json; debugging gates; running heal |
| [testing.md](guides/testing.md) | Writing a new test; using MockLLMProvider; test fixture inventory |
| [schema-authorship.md](guides/schema-authorship.md) | Adding or extending a JSON schema; updating CODE_TO_SPEC |
| [intake-setup.md](guides/intake-setup.md) | Onboarding a new GitHub org; authoring intake_config.yaml; first pilot run |
| [new-worker.md](guides/new-worker.md) | Implementing a new pipeline worker; WorkerContract; event emission |

---

## Ownership Map

Each guide is owned by the agent completing the task that triggers its update.
Ownership is by trigger event, not by team.

| Guide | Update when... |
|-------|----------------|
| `guides/ops-debug.md` | New gate added to `validation_engine/gates_registry.yaml`; new field in `specs/schemas/evaluation_report.schema.json`; `heal` CLI flags change; new event schema in `specs/schemas/event_schemas/` |
| `guides/testing.md` | New fixture added to `tests/conftest.py`; `MockLLMProvider` API changes (`src/launcher/clients/llm_mock_provider.py`); new test directory created |
| `guides/schema-authorship.md` | New schema file in `specs/schemas/`; new entry in `CODE_TO_SPEC` in `scripts/check_doc_freshness.py`; schema structural conventions change |
| `guides/intake-setup.md` | New `launch intake` CLI flag; new field in `specs/schemas/intake_config.schema.json`; classifier eligibility rules change in `src/launcher/intake/` |
| `guides/new-worker.md` | `WorkerContract` abstract method changes (`src/launcher/orchestrator/worker_contract.py`); new `WorkerContext` property; orchestrator-emitted event changes; `configs/pipeline.yaml` schema changes |
| `usage/quickstart.md` | Install process changes; `launch --help` output changes; required env vars change |
| `usage/cli.md` | Any `src/launcher/cli/*.py` flag added/removed/renamed; new top-level command added |
| `usage/configuration.md` | `src/launcher/models/run_config.py` field added/changed; `configs/llm_defaults.yaml` schema changes; `configs/intake_config.yaml` fields change |
| `usage/workflows.md` | End-to-end workflow changes; heal or deploy workflow changes; new scenario becomes common |
| `usage/skills.md` | New skill added to `skills_catalog.md`; skill trigger conditions change; new quality signal identified |
| `docs/README.md` | New guide added to `docs/guides/` or `docs/usage/` |

### Root .md files

These files live at the repository root and are not in `docs/`. They are equally
important and must be kept current.

| File | Purpose | Update when... |
|------|---------|----------------|
| `CLAUDE.md` | Agent governance (AG-001..AG-020, protected paths, self-review rule) | A new governance rule is added; AG-002 protected paths change; self-review dimensions change |
| `agents.md` | Operational guide: commands, entry points, test conventions, LLM config | New pipeline command; entry point changes; new test convention; LLM model or endpoint changes; new common mistake identified |
| `skills.md` | Runtime quality standards injected into LLM prompts | New prose/code quality rule; new anti-pattern; new per-platform convention; evaluation criteria change; human review criteria change. Also update `skills/context.md` and `.kilocode/rules/content-quality.md` when GENERATION STANDARDS, EVALUATION CRITERIA, or ANTI-PATTERNS change; update `.kilocode/rules/human-review.md` when HUMAN REVIEW STANDARDS change |
| `skills_catalog.md` | Skill system: 8 knowledge groups, 17 skill definitions | New skill added; skill inputs/outputs change; new knowledge group; escalation rules revised |
| `TASK_BACKLOG.md` | Active sprint and task tracking | Agent-managed; updated at the start of each work session |
| `README.md` | Project overview and ground rules | Project name changes; architecture overview changes; ground rules change |

### Spec files (`specs/*.md`)

Spec files are the source of truth for worker contracts and system behavior.
They are owned by the agent completing the taskcard that changes the relevant
code. `specs/governance.md` is the single authoritative source for all AG-xxx
rules — `CLAUDE.md` and `.claude_code_rules` enforce or reference it, they do
not duplicate it.

| Spec | Update when... |
|------|----------------|
| `specs/governance.md` | New AG-xxx rule added or changed; `.claude_code_rules` enforcement logic changes |
| `specs/system_overview.md` | New worker added; `configs/pipeline.yaml` topology changes; architecture fundamentally changes |
| `specs/system_contract.md` | Any worker I/O boundary contract changes; new schema boundary added |
| `specs/worker_understand.md` | `src/launcher/workers/understand/` behavior changes; `understanding_bundle.schema.json` fields change |
| `specs/worker_generate.md` | `src/launcher/workers/generate/` behavior changes; `content_manifest.schema.json` fields change |
| `specs/worker_evaluate.md` | `src/launcher/workers/evaluate/` gates change; `evaluation_report.schema.json` fields change |
| `specs/worker_publish.md` | `src/launcher/workers/publish/` behavior changes; `publish_bundle.schema.json` fields change |
| `specs/claims_evidence.md` | Claim schema changes in `understanding_bundle.schema.json`; new claim kind added |
| `specs/content_model_pageir.md` | `page_ir.schema.json` changes; new BlockIR type added |
| `specs/product_model.md` | `configs/families.yaml` schema changes; new family, platform, or tier added |
| `specs/site_model_hugo.md` | Template structure changes in `specs/templates/`; new Hugo shortcode or layout type |
| `specs/templates_rulesets.md` | `specs/rulesets/ruleset.yaml` changes; template variant selection logic changes |
| `specs/run_configuration.md` | `run_config.schema.json` changes; new RunConfig field; new required env var |
| `specs/llm_provider.md` | LLM endpoint changes; new model added to `configs/llm_defaults.yaml`; fallback behavior changes |
| `specs/github_intake.md` | `src/launcher/intake/` logic changes; new org config field; clone naming convention changes |
| `specs/pilot_program.md` | New pilot added to `configs/pilots/`; pilot config schema changes |
| `specs/state_events_checkpoints.md` | New event schema in `specs/schemas/event_schemas/`; checkpoint format changes |
| `specs/determinism_caching.md` | Cache invalidation logic changes; `PYTHONHASHSEED` requirement changes |
| `specs/toolchain_ci_telemetry.md` | CI config changes; new telemetry event emitted; `src/launcher/telemetry_api/` changes |

### Runbooks (`.claude/runbooks/`)

| Runbook | Update when... |
|---------|----------------|
| `.claude/runbooks/taskcards.md` | Taskcard template (`plans/taskcards/TC-000_TEMPLATE.md`) changes; AG-002 workflow changes |
| `.claude/runbooks/self-review.md` | Self-review dimensions change; AG-020 protocol changes; healing plan requirements change |

### How the map is enforced

1. **`scripts/check_doc_freshness.py`** — maps code file globs to guide paths.
   When a code file changes without its guide being touched, the script exits 1.
   Run before marking any taskcard Done: `python scripts/check_doc_freshness.py --since HEAD~N`

2. **Taskcard template** — items 10 and 11 in `## Task-specific review checklist`
   force every agent to check this map before marking a taskcard Done.

3. **Self-review runbook** — Dimension 14 ("Documentation completeness") scores
   whether the relevant guide was updated per this map.

---

## What belongs where

| Content | Location |
|---------|----------|
| Worker I/O contracts, schemas, event definitions | `specs/` |
| Gate behavior, evaluation criteria | `specs/worker_evaluate.md` |
| Agent governance rules (AG-001..AG-020) — **authoritative** | `specs/governance.md` |
| Agent governance enforcement (protected paths, rule references) | `CLAUDE.md`, `.claude_code_rules` |
| Operational guide: pipeline commands, test conventions, LLM config | `agents.md` |
| Taskcard creation and management runbook | `.claude/runbooks/taskcards.md` |
| Self-review protocol runbook | `.claude/runbooks/self-review.md` |
| LLM content quality standards (injected into prompts) | `skills.md` → GENERATION STANDARDS + EVALUATION CRITERIA |
| Human reviewer quality and SEO standards | `skills.md` → HUMAN REVIEW STANDARDS |
| Skill definitions (system + operator) | `skills_catalog.md` |
| Day-to-day skill usage | `docs/usage/skills.md` |
| Install and first run | `docs/usage/quickstart.md` |
| CLI flags and command reference | `docs/usage/cli.md` |
| Config file field reference | `docs/usage/configuration.md` |
| Common operator scenarios | `docs/usage/workflows.md` |
| How to debug a failed run | `docs/guides/ops-debug.md` |
| How to write a test | `docs/guides/testing.md` |
| How to add a schema | `docs/guides/schema-authorship.md` |
| How to onboard a new org | `docs/guides/intake-setup.md` |
| How to implement a new worker | `docs/guides/new-worker.md` |
