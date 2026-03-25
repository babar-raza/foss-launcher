# Evidence: TC-2442 run_cache.schema.json

## Files Created
- `specs/schemas/run_cache.schema.json` — JSON Schema draft-07

## Schema Coverage
- schema_version: "1.0" (enum)
- enabled: boolean
- workers: object of {input_hash, output_hash} pairs
- pages: object of {draft_path} pairs
- Required fields: schema_version, enabled
