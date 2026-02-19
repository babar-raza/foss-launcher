# Docs Root Orphans

Per root-orphan contract, any file directly under `docs/` (maxdepth=1) except
`docs/README.md` and folders (`docs/_audit/`, `docs/_archive/`) is an orphan
and must be triaged.

## Current Status

**4 ROOT ORPHANS FOUND** - All must be triaged with explicit action.

| orphan_path | brief content summary | likely target area | action | canonical merge target | risks/notes |
| --- | --- | --- | --- | --- | --- |
| `docs/AI_GOVERNANCE_QUICK_REFERENCE.md` | AI governance rules, approval workflows, branch creation gates (AG-001-AG-007) | ops/dev | move | docs/guides/ai_governance.md | High - This is a critical governance document that should be discoverable. Currently scattered. |
| `docs/creating_taskcards.md` | Developer quickstart for creating taskcards with 14 mandatory sections, validation guide | dev | move | docs/guides/creating_taskcards.md | Medium - Developer workflow guide, should be in guides. |
| `docs/MODEL_REFERENCE.md` | LLM model reference, provider configuration, model assignments for pilots | reference | keep | docs/reference/llm_models.md | Low - Reference material, appropriate in reference but should be renamed for clarity. |
| `docs/telemetry_integration_completion.md` | Complete telemetry integration report (TC-1050-1055), 38 tests passing | ops/dev | archive | docs/_archive/telemetry_integration_20260208.md | Medium - Historical completion report, should be archived. May contain useful lessons for future integrations. |

## Archived Moves

| previous path | canonical path | status |
| --- | --- | --- |
| `docs/architecture.md` | `docs/reference/architecture.md` | moved |
| `docs/cli_usage.md` | `docs/reference/cli_usage.md` | moved |
