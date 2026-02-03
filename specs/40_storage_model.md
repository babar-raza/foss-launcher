# Storage Model

## Goal

Define the complete storage architecture for the foss-launcher system, including:
- What data is stored where (files vs. database)
- How to reproduce runs deterministically
- Retention policies and evidence packaging
- Debugging procedures and traceability

This spec provides a unified view of storage across all components.

## Architecture Overview

The foss-launcher uses a **hybrid storage model**:

1. **File-based storage (primary):** All operational data stored as JSON files and NDJSON logs
2. **SQLite database (optional):** Used ONLY for Local Telemetry API (run metadata queries)

**Design Principle:** File-based storage ensures portability, determinism, and auditability without external dependencies.

---

## File-Based Storage (Primary)

### Run Directory Structure

Every run is isolated in a self-contained directory:

```
runs/<run_id>/
├─ run_config.yaml                 # Input configuration (validated)
├─ events.ndjson                   # Append-only event log (source of truth)
├─ snapshot.json                   # Materialized state snapshot
├─ telemetry_outbox.jsonl          # Buffered telemetry (when API unavailable)
├─ validation_report.json          # Validation gate results
├─ work/
│  ├─ repo/                        # Cloned product repo (read-only after ingestion)
│  ├─ site/                        # Cloned site repo (writeable, path-restricted)
│  └─ workflows/                   # Cloned workflows repo (read-only)
├─ artifacts/                      # Schema-validated JSON artifacts
│  ├─ repo_inventory.json          # W1: Repo fingerprint and file inventory
│  ├─ discovered_docs.json         # W1: Documentation discovery
│  ├─ discovered_examples.json     # W1: Example discovery
│  ├─ frontmatter_contract.json    # W1: Site metadata contract
│  ├─ site_context.json            # W1: Hugo config and build matrix
│  ├─ product_facts.json           # W2: Extracted claims and facts
│  ├─ evidence_map.json            # W2: Claim → evidence mappings
│  ├─ snippet_catalog.json         # W3: Curated code snippets
│  ├─ page_plan.json               # W4: Page generation plan
│  ├─ patch_bundle.json            # W6: Content patches
│  ├─ validation_report.json       # W7: Validation gate results
│  └─ pr.json                      # W9: Pull request metadata (optional)
├─ drafts/                         # Generated markdown pages
│  ├─ products/                    # Product pages
│  ├─ docs/                        # Documentation pages
│  ├─ reference/                   # API reference pages
│  ├─ kb/                          # Knowledge base articles
│  └─ blog/                        # Blog posts
├─ reports/                        # Human-readable reports (diffs, summaries)
└─ logs/                           # Raw tool outputs (gate logs, command logs)
```

**Binding Contract:** This structure is defined in `specs/29_project_repo_structure.md` and implemented by `src/launch/io/run_layout.py`.

---

## Core State Files

### events.ndjson (Source of Truth)

**Purpose:** Append-only event log enabling replay and resume.

**Format:** Newline-delimited JSON (one event per line)
**Schema:** `specs/schemas/event.schema.json`
**Implementation:** `src/launch/state/event_log.py`

**Contents:**
```json
{"event_id":"evt-20260203120000-abc123","run_id":"r_xyz","ts":"2026-02-03T12:00:00Z","type":"RUN_CREATED","payload":{...},"trace_id":"abc...","span_id":"def..."}
{"event_id":"evt-20260203120001-def456","run_id":"r_xyz","ts":"2026-02-03T12:00:01Z","type":"ARTIFACT_WRITTEN","payload":{"name":"repo_inventory.json","sha256":"..."},"trace_id":"abc...","span_id":"ghi..."}
```

**Key Operations:**
- `append_event(events_file, event)` - Atomic append
- `read_events(events_file)` - Load all events for replay
- `validate_event_chain(events)` - Verify integrity (optional)

**Required Event Types:**
- RUN_CREATED, RUN_STATE_CHANGED, RUN_COMPLETED, RUN_FAILED
- ARTIFACT_WRITTEN, WORK_ITEM_QUEUED, WORK_ITEM_STARTED, WORK_ITEM_FINISHED
- GATE_RUN_STARTED, GATE_RUN_FINISHED
- ISSUE_OPENED, ISSUE_RESOLVED
- LLM_CALL_STARTED, LLM_CALL_FINISHED, LLM_CALL_FAILED

**Binding Rule:** The event log is the authoritative source for run history. All state can be reconstructed by replaying events.

---

### snapshot.json (Materialized State)

**Purpose:** Materialized view of current run state for fast access.

**Schema:** `specs/schemas/snapshot.schema.json`
**Implementation:** `src/launch/state/snapshot_manager.py`

**Contents:**
```json
{
  "schema_version": "1.0.0",
  "run_id": "r_xyz",
  "run_state": "DRAFT_READY",
  "artifacts_index": {
    "repo_inventory.json": {
      "path": "artifacts/repo_inventory.json",
      "sha256": "abc123...",
      "schema_id": "repo_inventory.schema.json",
      "writer_worker": "w1_repo_scout",
      "ts": "2026-02-03T12:00:01Z",
      "event_id": "evt-..."
    }
  },
  "work_items": [
    {
      "work_item_id": "wi-001",
      "worker": "w1_repo_scout",
      "status": "finished",
      "started_at": "2026-02-03T12:00:00Z",
      "finished_at": "2026-02-03T12:00:10Z"
    }
  ],
  "issues": [],
  "section_states": {}
}
```

**Key Operations:**
- `write_snapshot(snapshot_file, snapshot)` - Atomic write
- `read_snapshot(snapshot_file)` - Load current state
- `replay_events(events_file, run_id)` - Reconstruct from events.ndjson

**Binding Rule:** The snapshot can be regenerated from events.ndjson at any time. If snapshot.json is lost or corrupted, replay the event log.

---

### run_config.yaml

**Purpose:** Input configuration for the run (immutable after start).

**Schema:** `specs/schemas/run_config.schema.json`
**Format:** YAML (human-readable)

**Contents:**
- Product metadata (product_slug, product_family, subdomain)
- Repository URLs and pinned SHAs
- Platform and locale settings
- Allowed paths policy
- Ruleset references
- Template configuration

**Binding Rule:** Configuration is copied from `configs/` to `runs/<run_id>/run_config.yaml` at run start. Modifications after start are ignored.

---

## Artifacts Directory

All worker outputs are stored as **schema-validated JSON files** in `artifacts/`.

### Artifact Lifecycle

1. **Generate:** Worker produces artifact data in memory
2. **Validate:** Data validates against JSON schema
3. **Write:** Atomic write to temp file
4. **Hash:** Compute SHA256 hash
5. **Rename:** Atomic rename to final location
6. **Event:** Emit ARTIFACT_WRITTEN event
7. **Index:** Add to snapshot.artifacts_index

**Implementation:** `src/launch/io/atomic.py::atomic_write_json()`

### Artifact Registry

| Artifact | Schema | Producer | Purpose |
|----------|--------|----------|---------|
| repo_inventory.json | repo_inventory.schema.json | W1 RepoScout | Repo fingerprint, file inventory, tech stack |
| discovered_docs.json | - | W1 RepoScout | Documentation file discovery results |
| discovered_examples.json | - | W1 RepoScout | Example file discovery results |
| frontmatter_contract.json | frontmatter_contract.schema.json | W1 RepoScout | Site metadata contract (required fields) |
| site_context.json | site_context.schema.json | W1 RepoScout | Hugo config, build matrix, platform detection |
| product_facts.json | product_facts.schema.json | W2 FactsBuilder | Extracted claims and facts from documentation |
| evidence_map.json | evidence_map.schema.json | W2 FactsBuilder | Claim → evidence mappings (source traceability) |
| snippet_catalog.json | snippet_catalog.schema.json | W3 SnippetCurator | Curated code snippets with metadata |
| page_plan.json | page_plan.schema.json | W4 IAPlanner | Page generation plan (templates, contexts) |
| patch_bundle.json | patch_bundle.schema.json | W6 LinkerAndPatcher | Content patches to apply to site repo |
| validation_report.json | validation_report.schema.json | W7 Validator | Validation gate results (pass/fail) |
| pr.json | pr.schema.json | W9 PRManager | Pull request metadata (optional) |

**Binding Rule:** All artifacts MUST validate against their schema before being written. Invalid artifacts MUST cause the worker to fail.

---

## Draft Files

Generated markdown pages stored in `drafts/` subdirectories:

- `drafts/products/` - Product overview pages
- `drafts/docs/` - Documentation pages
- `drafts/reference/` - API reference pages
- `drafts/kb/` - Knowledge base articles
- `drafts/blog/` - Blog posts

**Naming Convention:** Draft files mirror the target site path structure:
- Target: `content/docs.aspose.org/note/en/getting-started.md`
- Draft: `drafts/docs/content/docs.aspose.org/note/en/getting-started.md`

**Binding Rule:** Draft paths MUST match `page_plan.json` entries. W5 SectionWriter writes drafts; W6 LinkerAndPatcher merges them into `work/site/`.

---

## Reports and Logs

### Reports Directory

**Location:** `reports/`
**Format:** Human-readable (markdown, text, JSON)
**Purpose:** Debugging and audit trail

**Examples:**
- `run_summary.md` - High-level run summary
- `validation_summary.md` - Validation gate summary
- `fix_notes.md` - W8 Fixer actions

**Retention:** Optional; useful for debugging but regenerable.

### Logs Directory

**Location:** `logs/`
**Format:** Raw tool outputs (text, JSON)
**Purpose:** Detailed debugging

**Examples:**
- `w1_repo_scout.log` - W1 worker output
- `gate_9_navigation.log` - Gate 9 execution log
- `hugo_build.log` - Hugo build output

**Retention:** Optional; useful for 7 days, then deletable.

---

## SQLite Database (Telemetry API Only)

### Purpose

**CRITICAL:** The SQLite database is used ONLY for the Local Telemetry API. It is NOT used for operational state management.

**Use Cases:**
- Run history queries (UI/API)
- Performance metrics aggregation
- Parent/child run hierarchies
- Telemetry event streaming

**Non-Use Cases:**
- Run state persistence (use events.ndjson + snapshot.json)
- Artifact storage (use artifacts/)
- Worker coordination (use orchestrator graph)
- Deterministic replay (use events.ndjson)

### Database Location

**File:** Configurable (typically `telemetry.db` in launcher root)
**Implementation:** `src/launch/telemetry_api/routes/database.py`

### Schema

#### Table: runs

Stores run metadata:

```sql
CREATE TABLE runs (
    event_id TEXT PRIMARY KEY,          -- Idempotent run creation key
    run_id TEXT NOT NULL,               -- Run identifier
    agent_name TEXT NOT NULL,           -- Worker/agent name
    job_type TEXT NOT NULL,             -- run, worker, gate, llm_call
    start_time TEXT NOT NULL,           -- ISO8601 timestamp
    status TEXT NOT NULL DEFAULT 'running',  -- running, completed, failed
    parent_run_id TEXT,                 -- Parent run (for hierarchies)
    product TEXT,                       -- Product slug
    product_family TEXT,                -- Product family
    platform TEXT,                      -- Platform (.NET, Java, etc.)
    subdomain TEXT,                     -- docs, reference, kb, blog
    website_section TEXT,               -- Website section
    item_name TEXT,                     -- Item name
    git_repo TEXT,                      -- Git repository URL
    git_branch TEXT,                    -- Git branch
    end_time TEXT,                      -- ISO8601 timestamp
    duration_ms INTEGER,                -- Duration in milliseconds
    items_discovered INTEGER,           -- Count of discovered items
    items_succeeded INTEGER,            -- Count of successful items
    items_failed INTEGER,               -- Count of failed items
    items_skipped INTEGER,              -- Count of skipped items
    output_summary TEXT,                -- Summary of outputs
    error_summary TEXT,                 -- Summary of errors
    metrics_json TEXT,                  -- JSON metrics blob
    context_json TEXT,                  -- JSON context (trace_id, span_id)
    commit_hash TEXT,                   -- Git commit SHA
    commit_source TEXT,                 -- manual, llm, ci
    commit_author TEXT,                 -- Commit author
    commit_timestamp TEXT,              -- Commit timestamp
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_runs_run_id ON runs(run_id);
CREATE INDEX idx_runs_parent_run_id ON runs(parent_run_id);
CREATE INDEX idx_runs_status ON runs(status);
CREATE INDEX idx_runs_job_type ON runs(job_type);
CREATE INDEX idx_runs_start_time ON runs(start_time);
```

#### Table: events

Stores event stream for telemetry:

```sql
CREATE TABLE events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL,             -- Event identifier
    run_id TEXT NOT NULL,               -- Associated run
    ts TEXT NOT NULL,                   -- ISO8601 timestamp
    type TEXT NOT NULL,                 -- Event type
    payload TEXT NOT NULL,              -- JSON payload
    trace_id TEXT,                      -- Telemetry trace ID
    span_id TEXT,                       -- Telemetry span ID
    parent_span_id TEXT,                -- Parent span ID
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_events_run_id ON events(run_id);
CREATE INDEX idx_events_ts ON events(ts);
```

### Key Operations

**Run Management:**
- `create_run(run_data)` - Create run record (idempotent via event_id)
- `update_run(event_id, update_data)` - Update run status/metadata
- `get_run_by_id(run_id)` - Retrieve run by run_id
- `list_runs(filters)` - Query runs with pagination

**Event Management:**
- `add_event(event_data)` - Record event for streaming
- `get_events_for_run(run_id)` - Retrieve event stream

**Telemetry:**
- `get_metadata()` - Get distinct agent names, job types
- `get_metrics()` - Get system-level metrics

### Database Availability

**Optional Operation:** If the telemetry API is unavailable:
- System buffers telemetry to `telemetry_outbox.jsonl`
- All core operations continue using file-based storage
- Buffered telemetry is POSTed when API becomes available

**Binding Rule:** Workers MUST NOT depend on database availability for correctness. Database is for observability only.

---

## Deterministic Reproduction

### Required Files

To reproduce a run deterministically, retain:

**Minimal Set (MUST retain):**
1. `run_config.yaml` - Input configuration with pinned SHAs
2. `events.ndjson` - Complete event history
3. `artifacts/*.json` - All generated artifacts
4. `work/repo/` - Cloned product repo at pinned SHA

**Optional for Debugging (SHOULD retain 30 days):**
5. `snapshot.json` - Can be regenerated from events.ndjson
6. `validation_report.json` - Also in artifacts/, useful for quick access
7. `reports/` - Human-readable summaries
8. `logs/` - Detailed tool outputs

**Regenerable (MAY delete immediately):**
9. `drafts/` - Can regenerate from artifacts + templates
10. `work/site/` - Cloned site repo (not part of run output)
11. `work/workflows/` - Cloned workflows repo
12. `telemetry_outbox.jsonl` - After successful POST to API

### Replay Algorithm

The replay algorithm reconstructs the final snapshot from the event log without re-executing workers.

**Specification:** `specs/11_state_and_events.md:117-167`
**Implementation:** `src/launch/state/snapshot_manager.py::replay_events()`

**Algorithm:**

```python
def replay_events(events_file: Path, run_id: str) -> Snapshot:
    # Step 1: Load Events
    events = read_events(events_file)

    # Step 2: Validate Chain (optional but recommended)
    validate_event_chain(events)

    # Step 3: Apply Event Reducers
    snapshot = Snapshot(
        schema_version="1.0.0",
        run_id=run_id,
        run_state="CREATED",
        artifacts_index={},
        work_items=[],
        issues=[],
        section_states={},
    )

    for event in events:
        snapshot = apply_event_reducer(snapshot, event)

    return snapshot

def apply_event_reducer(snapshot: Snapshot, event: Event) -> Snapshot:
    if event.type == "RUN_CREATED":
        # Initialize snapshot with run metadata
        pass
    elif event.type == "RUN_STATE_CHANGED":
        snapshot.run_state = event.payload["new_state"]
    elif event.type == "ARTIFACT_WRITTEN":
        artifact_name = event.payload["name"]
        snapshot.artifacts_index[artifact_name] = ArtifactIndexEntry(
            path=event.payload["path"],
            sha256=event.payload["sha256"],
            schema_id=event.payload.get("schema_id", ""),
            writer_worker=event.payload.get("writer_worker", ""),
            ts=event.ts,
            event_id=event.event_id,
        )
    elif event.type == "WORK_ITEM_QUEUED":
        snapshot.work_items.append(WorkItem(
            work_item_id=event.payload["work_item_id"],
            worker=event.payload["worker"],
            status="queued",
            ...
        ))
    elif event.type == "WORK_ITEM_FINISHED":
        # Update work item status
        ...

    return snapshot
```

**Binding Rule:** If `snapshot.json` is lost or corrupted, replay `events.ndjson` to reconstruct it. The event log is the source of truth.

---

## Traceability

### Forward Trace (Source → Output)

**Goal:** Trace from source repository files to generated pages.

**Steps:**
1. Start with source file in `work/repo/<path>`
2. Find file in `repo_inventory.json` → file metadata
3. Check if file is referenced in `evidence_map.json`:
   - If docs file: claims extracted by W2 → `product_facts.json`
   - If example file: snippets extracted by W3 → `snippet_catalog.json`
4. Find claims/snippets used in `page_plan.json` → pages[].context
5. Locate generated page in `drafts/<section>/<output_path>`
6. Follow to merged content in `work/site/<output_path>` (after W6)

**Event Trace:**
- Search `events.ndjson` for `ARTIFACT_WRITTEN` with `name=repo_inventory.json`
- Follow `WORK_ITEM_*` events for W2 (facts), W3 (snippets), W4 (plan), W5 (drafts)
- Complete audit trail from file discovery to page generation

### Backward Trace (Output → Source)

**Goal:** Trace from a generated page back to original source files.

**Steps:**
1. Start with generated page in `drafts/` or `work/site/`
2. Find page entry in `page_plan.json` by matching `output_path`
3. Extract `context.claims[]` identifiers from page entry
4. Look up each claim ID in `evidence_map.json`:
   - `claim_id` → `evidence_sources[]`
   - Each source has `file_path`, `line_start`, `line_end`
5. Locate source files in `repo_inventory.json` by `file_path`
6. Access actual content in `work/repo/<file_path>`

**Example:**

```
Generated Page: drafts/docs/content/docs.aspose.org/note/en/getting-started.md
              ↓
       page_plan.json: pages[].output_path = "content/docs.aspose.org/note/en/getting-started.md"
                       pages[].context.claims = ["claim_001", "claim_002"]
              ↓
    evidence_map.json: claims["claim_001"].evidence_sources = [
                         {"file_path": "docs/getting-started.md", "line_start": 10, "line_end": 20}
                       ]
              ↓
  repo_inventory.json: files["docs/getting-started.md"] = {...}
              ↓
      work/repo/docs/getting-started.md (lines 10-20)
```

**Binding Rule:** Every generated page MUST be traceable back to source files via this chain: page_plan.json → evidence_map.json → repo_inventory.json → work/repo/.

---

## Retention Policy

### Production Retention Guidelines

**Minimal Retention (for determinism):**
- Duration: 90 days
- Files:
  - run_config.yaml
  - events.ndjson
  - artifacts/*.json
  - work/repo/ (at pinned SHA)
- Purpose: Enable deterministic reproduction

**Debugging Retention (for operations):**
- Duration: 30 days
- Files:
  - snapshot.json
  - validation_report.json
  - reports/*
  - logs/*
- Purpose: Debugging failed runs

**Short-Term Retention (for active development):**
- Duration: 7 days
- Files:
  - drafts/* (regenerable)
  - work/site/ (cloned repo)
  - work/workflows/ (cloned repo)
  - telemetry_outbox.jsonl (after API POST)
- Purpose: Active debugging and iteration

### Evidence Package

For long-term retention, create ZIP archive:

**Implementation:** `src/launch/observability/evidence_packager.py`

**Package Contents:**
- artifacts/**/*
- reports/**/*
- events.ndjson
- snapshot.json
- run_config.yaml
- validation_report.json

**Package Manifest:**
```json
{
  "package_created_at": "2026-02-03T12:00:00Z",
  "run_id": "r_xyz",
  "total_files": 15,
  "total_size_bytes": 2048576,
  "files": [
    {
      "relative_path": "artifacts/repo_inventory.json",
      "size_bytes": 10240,
      "sha256": "abc123...",
      "modified_at": "2026-02-03T12:00:01Z"
    }
  ]
}
```

**Usage:**
```python
from launch.observability.evidence_packager import create_evidence_package

manifest = create_evidence_package(
    run_dir=Path("runs/r_xyz"),
    output_path=Path("runs/r_xyz/evidence.zip"),
)
```

**Recommended Retention:**
- Evidence ZIP: 90 days (compliance)
- Database records: 365 days (small footprint)
- Full run directories: 7 days (disk space)

---

## Debugging Procedures

### When a Run Fails

**Step 1: Check Snapshot**
```bash
cat runs/<run_id>/snapshot.json | jq '.run_state'
# Output: "FAILED"
```

**Step 2: Find Last Event**
```bash
tail -n 1 runs/<run_id>/events.ndjson | jq .
# Output: {"event_id":"...", "type":"RUN_FAILED", "payload":{"error":"..."}}
```

**Step 3: Check Validation Report**
```bash
cat runs/<run_id>/validation_report.json | jq '.gates[] | select(.status=="FAIL")'
# Output: Failed gates
```

**Step 4: Review Logs**
```bash
ls runs/<run_id>/logs/
# Output: gate_9_navigation.log, w7_validator.log
cat runs/<run_id>/logs/gate_9_navigation.log
```

**Step 5: Query Telemetry**
```bash
sqlite3 telemetry.db "SELECT * FROM runs WHERE run_id = '<run_id>'"
```

### When an Artifact is Missing

**Step 1: Check Artifact Index**
```bash
cat runs/<run_id>/snapshot.json | jq '.artifacts_index'
# Output: Map of artifacts
```

**Step 2: Search Event Log**
```bash
grep "ARTIFACT_WRITTEN" runs/<run_id>/events.ndjson | grep "product_facts.json"
# Output: Event(s) that wrote the artifact
```

**Step 3: Check Worker Logs**
```bash
cat runs/<run_id>/logs/w2_facts_builder.log
# Output: Worker execution log
```

**Step 4: Verify File Exists**
```bash
ls -lh runs/<run_id>/artifacts/product_facts.json
# Output: File size and timestamp OR error if missing
```

### When Page Generation Fails

**Step 1: Check Page Plan**
```bash
cat runs/<run_id>/artifacts/page_plan.json | jq '.pages[] | select(.output_path | contains("getting-started"))'
# Output: Page plan entry
```

**Step 2: Verify Dependencies**
```bash
ls runs/<run_id>/artifacts/product_facts.json
ls runs/<run_id>/artifacts/evidence_map.json
# Output: Verify artifacts exist
```

**Step 3: Check Draft Output**
```bash
ls runs/<run_id>/drafts/docs/
# Output: Partial draft files (if any)
```

**Step 4: Review Validation**
```bash
cat runs/<run_id>/validation_report.json | jq '.gates[] | select(.gate_id=="gate_8")'
# Output: Gate 8 (claim coverage) results
```

### When Determinism Fails

**Step 1: Compare Event Logs**
```bash
diff runs/run1/events.ndjson runs/run2/events.ndjson
# Output: Differences in event payloads
```

**Step 2: Compare Artifact Hashes**
```bash
sha256sum runs/run1/artifacts/repo_inventory.json
sha256sum runs/run2/artifacts/repo_inventory.json
# Output: SHA256 hashes (should match)
```

**Step 3: Check for Timestamps**
```bash
grep -r "2026-02-03" runs/run1/artifacts/
# Output: Files containing timestamps (investigate)
```

**Step 4: Verify Pinned SHAs**
```bash
cat runs/run1/run_config.yaml | grep "sha:"
cat runs/run2/run_config.yaml | grep "sha:"
# Output: Should be identical
```

**Step 5: Review Validation Report**
```bash
# Should be deterministic (TC-935)
sha256sum runs/run1/validation_report.json
sha256sum runs/run2/validation_report.json
# Output: Hashes should match
```

### When Telemetry is Missing

**Step 1: Check Outbox**
```bash
cat runs/<run_id>/telemetry_outbox.jsonl | jq .
# Output: Buffered telemetry events
```

**Step 2: Verify API Running**
```bash
curl http://localhost:8001/health
# Output: {"status": "ok"}
```

**Step 3: Query Database**
```bash
sqlite3 telemetry.db "SELECT * FROM runs ORDER BY start_time DESC LIMIT 10"
# Output: Recent runs
```

**Step 4: Check Event Emission**
```bash
grep "emit_event" src/launch/workers/w1_repo_scout/worker.py
# Output: Event emission calls in code
```

---

## Acceptance

This spec is complete when:
- All storage locations are documented (files and database)
- Deterministic reproduction procedure is defined
- Retention policy is specified
- Debugging procedures cover common scenarios
- Traceability is fully explained (forward and backward)
- Database usage is explicitly scoped (telemetry only)

## Related Specs

- `specs/11_state_and_events.md` - Event log and snapshot model
- `specs/29_project_repo_structure.md` - Run directory layout (binding)
- `specs/16_local_telemetry_api.md` - Telemetry database usage
- `specs/10_determinism_and_caching.md` - Determinism requirements

## Related Taskcards

- TC-939 - Storage model audit and documentation
- TC-935 - Validation report determinism
- TC-580 - Observability and evidence bundle
- TC-560 - Determinism harness
