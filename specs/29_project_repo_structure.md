# Project Repository Structure (launcher repo)

## Purpose
This document removes ambiguity for implementation by defining:
- the required **source code** layout of the launcher project
- the required **run directory** layout produced at runtime
- how other specs reference paths (using `RUN_DIR`)

This is binding. If a path or folder name appears here, implementers MUST follow it.

---

## Terminology (binding)
- **Launcher repo**: the repository implementing this system (this project).
- **Site repo**: the aspose.org Hugo content repository that will be patched.
- **GitHub product repo**: the public repo being launched.
- **RUN_DIR**: an absolute path to a single run folder on disk, for example `runs/<run_id>/`.

**Binding rule:** Any spec that refers to `artifacts/`, `drafts/`, `reports/`, or `logs/` is referring to a path under `RUN_DIR`
unless it explicitly says otherwise.

---

## Launcher repo: required top-level layout (binding)

```
.
├─ src/                       # Python package source (importable)
│  └─ launch/                 # top-level package namespace (recommended)
│     ├─ orchestrator/        # LangGraph graph + state + routing
│     ├─ workers/             # W1..W9 implementations
│     ├─ validators/          # gate implementations + helpers
│     ├─ mcp/                 # FastAPI MCP server + tool routing
│     ├─ clients/             # httpx clients: telemetry, commit service, llm
│     ├─ models/              # pydantic models mirroring schemas (optional)
│     ├─ io/                  # file IO, hashing, stable JSON, path utilities
│     └─ util/                # logging, retry policies, deterministic helpers
├─ specs/                     # this specification (checked in)
│  ├─ schemas/                # JSON schemas used by validators
│  ├─ rulesets/               # versioned rulesets
│  └─ templates/              # templates tree (see below)
├─ docs/                      # non-binding reference docs (API refs, notes)
├─ config/                    # pinned tool configs (markdownlint, lychee, toolchain.lock)
├─ configs/                   # run_config files (product launch configs)
│  ├─ pilots/                 # pinned pilot configs (one per pilot)
│  └─ products/               # real product configs (one per product_slug)
├─ scripts/                   # dev scripts (optional)
├─ tests/                     # unit/integration tests
├─ runs/                      # runtime output (gitignored)
├─ pyproject.toml             # required
├─ uv.lock or poetry.lock     # required for production runs (recommended for all dev)
└─ README.md
```

### Binding rules
1) `runs/` MUST be in `.gitignore`. Runs are artifacts, not source.
2) **Lockfile strategy (production requirement):**
   - Production/CI runs MUST use exactly one lock strategy: `uv` (`uv.lock`) **or** Poetry (`poetry.lock`).
   - This repo may start without a lockfile during the **spec-pack + scaffold** phase, but the first implementation PR MUST add one.
3) The MCP server and the CLI (if present) MUST call the same internal services. No parallel implementations.

---

## Templates tree (binding)
Templates MUST be present in the launcher repo at runtime under:

- `specs/templates/<subdomain>/<family>/<locale>/...`

Implementations MAY bring templates in via:
- git submodule
- a second repo clone during bootstrap
- a CI artifact download

But the resolved runtime path MUST match the folder layout above.

See:
- `specs/20_rulesets_and_templates_registry.md`

---

## RUN_DIR layout (binding)

Every run writes to one isolated run folder:

- `RUN_DIR = runs/<run_id>/`

Required structure:

```
RUN_DIR/
├─ run_config.yaml                 # the validated run config used for the run
├─ events.ndjson                   # append-only local event log (source of truth)
├─ snapshot.json                   # materialized state snapshot (atomic writes)
├─ telemetry_outbox.jsonl          # buffered telemetry payloads (when API unavailable)
├─ work/
│  ├─ repo/                        # cloned GitHub product repo at pinned SHA (read-only after ingestion)
│  ├─ site/                        # cloned site repo worktree (writeable, allowed_paths enforced)
│  └─ workflows/                   # cloned workflows repo at pinned SHA (read-only)
├─ artifacts/                      # schema-validated JSON artifacts (authoritative)
│  ├─ repo_inventory.json
│  ├─ product_facts.json
│  ├─ evidence_map.json
│  ├─ snippet_catalog.json
│  ├─ frontmatter_contract.json
│  ├─ site_context.json
│  ├─ page_plan.json
│  ├─ patch_bundle.json
│  ├─ validation_report.json
│  └─ pr.json                      # optional
├─ drafts/
│  ├─ products/                    # section drafts
│  ├─ docs/
│  ├─ reference/
│  ├─ kb/
│  └─ blog/
├─ reports/                        # human-readable reports (diffs, fix notes, summaries)
└─ logs/                           # raw tool logs (gate outputs, command logs)
```

### Binding rules
1) **Isolation**: workers MUST NOT read or write outside `RUN_DIR` (except for reading installed tools and env vars).
2) **Atomic writes**:
   - JSON artifacts are written to a temp file and atomically renamed into `RUN_DIR/artifacts/`.
   - `snapshot.json` is written atomically.
3) **Worktree safety**:
   - Only the LinkerAndPatcher (W6) and Fixer (W8) may write to `RUN_DIR/work/site/`.
   - All writes MUST be refused if outside `run_config.allowed_paths`.

---

## Draft file naming (binding)
`page_plan.pages[].output_path` is the canonical target path inside the site repo (relative to the site repo root).

Drafts MUST mirror the target path to avoid collisions:

- draft_path = `RUN_DIR/drafts/<section>/<output_path>`

Example:
- output_path: `content/docs.aspose.org/note/en/getting-started.md`
- draft_path: `runs/<run_id>/drafts/docs/content/docs.aspose.org/note/en/getting-started.md`

---

## Acceptance
- An engineer (or LLM agent) can implement without guessing where to put code, configs, templates, or run outputs.
- All path references across specs are unambiguous via `RUN_DIR`.
