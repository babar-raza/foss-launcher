# Schema Authorship Guide

Reach for this guide when adding a new JSON schema, extending an existing one,
or updating `CODE_TO_SPEC` in `scripts/check_doc_freshness.py`.

For the schema registry and validation enforcement rules, see
`specs/system_contract.md` (Schema Registry section) and `specs/governance.md` (AG-004).

---

## 1. When a New Schema Is Required

| Situation | Schemas required |
|-----------|-----------------|
| New pipeline worker | `<worker>_input.schema.json` + `<worker>_output.schema.json` |
| New event type | `specs/schemas/event_schemas/<event_type>.schema.json` |
| New top-level artifact (new run-dir file) | `<artifact_name>.schema.json` |
| New property on an existing schema | No new file; update existing schema + bump version |

Do **not** create a schema for internal data structures that never cross a
worker boundary. Internal models use Pydantic; schemas are for boundaries.

---

## 2. File Naming and Location

| Type | Location | Convention |
|------|----------|-----------|
| Worker I/O, artifact schemas | `specs/schemas/` | `<name>.schema.json` |
| Event schemas | `specs/schemas/event_schemas/` | `<event_type>.schema.json` |

Event type names use snake_case and match the `type` field in the event
(e.g., `worker_started`, `gate_executed`).

---

## 3. Mandatory Schema Structure

Every schema must include all of the following:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://launcher.internal/schemas/<name>.schema.json",
  "title": "Human-readable title",
  "version": "1.0.0",
  "description": "One sentence: what this schema validates and who produces/consumes it.",
  "type": "object",
  "required": ["field1", "field2"],
  "additionalProperties": false,
  "properties": {
    "field1": {
      "type": "string",
      "description": "What this field contains and when it is populated."
    }
  }
}
```

### Rules for every property

- **`"description"` is mandatory** on every property, including nested objects.
  No property may have `"type"` without `"description"`.
- Use `"$comment"` for implementation notes that should not be in the schema
  description (e.g., `"$comment": "See worker_generate.md §3.2 for full semantics"`).
- Mark all truly required fields in the top-level `"required"` array.
  If a field is conditionally required, add a note in `"description"`.
- `"additionalProperties": false` at the top level prevents schema drift.
  Use `true` only when the object is explicitly open-ended (document why).

### version field

The `version` field follows semver:
- Patch bump (1.0.0 → 1.0.1): documentation-only changes, no structural change
- Minor bump (1.0.0 → 1.1.0): additive changes (new optional property)
- Major bump (1.0.0 → 2.0.0): breaking changes (removal, rename, type change)

---

## 4. Registering a New Schema in pipeline.yaml

`configs/pipeline.yaml` is a protected path. Modifying it requires an In-Progress
taskcard (AG-002). Include the schema registration in the same taskcard as the
worker implementation.

In `pipeline.yaml`, each worker entry has `input_schema` and `output_schema`:

```yaml
workers:
  understand:
    input_schema:  specs/schemas/intake_bundle.schema.json
    output_schema: specs/schemas/understanding_bundle.schema.json
```

The runtime validates worker I/O against these schemas on every execution.
A `SCHEMA_MISMATCH` error means the worker returned a structure that does not
match `output_schema`.

---

## 5. Additive vs. Breaking Changes

### Additive (safe to deploy without migration)

- Adding a new **optional** property with a `"description"` and sane default
- Adding a new enum value to an existing enum property
- Loosening a type constraint (e.g., `string` → `["string", "null"]`)

Additive changes require a **minor version bump**.

### Breaking (requires migration note)

- Removing a property that existing checkpoints may contain
- Renaming a property
- Changing a property's type
- Adding a new **required** property (breaks old checkpoint payloads)
- Tightening a constraint (e.g., adding `"minLength": 1` to a previously unconstrained string)

Breaking changes require a **major version bump** and an entry in
`reports/CHANGELOG.md`:

```markdown
## Schema: understanding_bundle v2.0.0 (2024-03-15)

**Breaking**: `claims` array items now require `evidence_urls` field.
Old checkpoints from runs before this date must be re-generated.
```

When resuming a run that has an old-version checkpoint, the run_loop logs
`SCHEMA_VERSION_MISMATCH`. See `docs/guides/ops-debug.md §5` for the fix.

---

## 6. Event Schemas

Event schemas are simpler than artifact schemas. Every event schema must include:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "...",
  "title": "WorkerStarted Event",
  "description": "Emitted when a worker begins execution.",
  "type": "object",
  "required": ["type", "run_id", "worker", "timestamp"],
  "additionalProperties": false,
  "properties": {
    "type":      { "type": "string", "const": "worker_started", "description": "Event type identifier." },
    "run_id":    { "type": "string", "description": "The run this event belongs to." },
    "worker":    { "type": "string", "description": "Worker name (matches pipeline.yaml key)." },
    "timestamp": { "type": "string", "format": "date-time", "description": "ISO 8601 UTC timestamp." }
  }
}
```

Use `"const"` on the `type` field to lock the event type value.

Event schemas do **not** go in `pipeline.yaml`. They are validated at runtime
by the event log writer in `src/launcher/state/event_log.py`.

---

## 7. Updating CODE_TO_SPEC in check_doc_freshness.py

When you add a new schema file or a new source module, update
`scripts/check_doc_freshness.py` to keep the doc-freshness check accurate.

`CODE_TO_SPEC` maps source file globs to governing docs (specs or guides).

### Rules for adding entries

1. More-specific entries (exact file paths) must precede less-specific ones
   (directory `**` patterns) for the same subtree — first match wins.
2. Every new source module that has a governing spec must have an entry.
3. New `docs/guides/` targets follow the same format as spec targets:
   `("src/launcher/new_module/**", "docs/guides/new-worker.md")`.

### Example: adding a new worker

```python
# In CODE_TO_SPEC, add before the broad "src/launcher/workers/**" fallback:
("src/launcher/workers/deploy/**", "specs/worker_deploy.md"),
```

### Example: adding a new schema

The schema itself lives in `specs/schemas/`, which is already covered by
the broad `("specs/schemas/**", "docs/guides/schema-authorship.md")` entry
added by this plan. No additional CODE_TO_SPEC entry is needed for the schema
file itself. You only need a new entry if you're adding a new **source module**
that is governed by the new schema.

---

## 8. Pre-Done Checklist for Schema Taskcards

Before marking a schema-related taskcard Done:

```
[ ] $schema, $id, title, version, description all present
[ ] Every property has a "description"
[ ] "required" array is complete and accurate
[ ] "additionalProperties": false set at top level (or rationale documented)
[ ] Version bumped correctly (patch/minor/major per change type)
[ ] For breaking changes: entry in reports/CHANGELOG.md
[ ] Schema registered in pipeline.yaml (if worker I/O schema)
[ ] CODE_TO_SPEC updated if a new source module was added
[ ] docs/guides/schema-authorship.md updated if schema conventions changed
[ ] python scripts/check_doc_freshness.py --since HEAD~N exits 0
[ ] jsonschema validation test added (validate a fixture against the new schema)
```
