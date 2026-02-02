# Docs Root Orphans

Per root-orphan contract, any file directly under `docs/` (maxdepth=1) except `docs/README.md` is an orphan and must be triaged.

| orphan_path | brief content summary | likely target area (overview/guides/reference/ops/dev/arch) | action (move/merge/archive/delete) | canonical merge target (if merge) | risks/notes |
| --- | --- | --- | --- | --- | --- |
| `docs/architecture.md` | Non-binding architecture overview and control flow summary. | arch | move | N/A | ROOT ORPHAN. Suggest move to `docs/reference/architecture.md` or `docs/_archive/architecture.md`. Also contains claims that code is “scaffold only” which conflicts with implemented workers; update after move. |
| `docs/cli_usage.md` | CLI entrypoints and runbooks for launch_run/launch_validate/launch_mcp. | guides | move | N/A | ROOT ORPHAN. Suggest move to `docs/reference/cli_usage.md` (or `docs/guides/cli_usage.md` if a guides folder is created). Contains flag mismatches vs code. |
