# Runtime Validation Tools

This directory contains validation gates that run **inside a RUN_DIR workspace** to validate:
- Generated content
- Site structure and Hugo configs
- Cross-references and links
- Policy compliance (no manual edits)

## Distinction from Repo Root `tools/`

**Repo root `tools/` directory** (`<repo>/tools/`):
- Validates the **foss-launcher repository itself**
- Runs during development and CI
- Examples: spec validation, taskcard validation, markdown link checks

**This directory** (`src/launch/tools/`):
- Validates **generated site content** inside a RUN_DIR
- Runs during the launch pipeline (after content generation)
- Examples: Hugo build validation, content policy gates, determinism checks

## Architecture Decision

See **DEC-006** in `DECISIONS.md` for the architectural decision that created this structure.

## Related Taskcards

- **TC-560**: Determinism harness (validation gate framework)
- **TC-570**: Validation gates extension (specific gate implementations)
- **TC-571**: Policy gate for no manual edits
