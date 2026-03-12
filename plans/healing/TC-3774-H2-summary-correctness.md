# TC-3774-H2: Fix Worker Summary Field Names and None-Safety

## Context

`_print_worker_summary` in `main.py` was written with guessed field names for `generate` and `publish` workers. Model verification reveals:
- `generate` summary misses `generation_stats` (llm_calls, fallback_count, duration_seconds)
- `publish` summary uses `output.get('files', [])` but `PublishBundle` has `patches` (list[Patch]) and `pr` (PullRequest)
- Multiple `.get()` calls will crash on `None` values when used with slicing or arithmetic

## Gap Table

| Gap ID | Description | Taskcard |
|--------|-------------|----------|
| G-02 | `publish` summary uses wrong field name `files` (actual: `patches`, `pr`) | TC-3774-H2 |
| G-03 | `generate` summary only shows page count, misses `generation_stats` | TC-3774-H2 |
| G-04 | None-safety: `repo_sha[:12]` and `content_budget_used / 1024` crash on None | TC-3774-H2 |

## Taskcard: TC-3774-H2

- **Status:** Done
- **Gap linkage:** G-02, G-03, G-04
- **Role:** Senior engineer. Drop-in, production-ready.

### Scope

- **Fix:** Correct field names in `_print_worker_summary` for generate/publish workers; add None-safe access patterns throughout.
- **Allowed paths:**
  - `src/launcher/cli/main.py`
- **Forbidden:** any other file/path

### Acceptance Checks

- **CLI:**
  - `python -m launcher.cli.main run <config> --stop-after generate` prints `Pages generated`, `LLM calls`, `Fallbacks`, `Duration`
  - `python -m launcher.cli.main run <config>` (full run) prints publish summary with `Patches` count and `PR` URL
- **Tests:**
  - Covered by TC-3774-H1 test additions (TestWorkerSummary)
- **Config respected end-to-end:** Field names match models exactly:
  - `ContentManifest.pages` (list[GeneratedPage]), `.generation_stats.llm_calls`, `.generation_stats.fallback_count`, `.generation_stats.duration_seconds`
  - `PublishBundle.patches` (list[Patch]), `.pr.url`, `.pr.state`
  - `IntakeBundle.repo_sha` (str, default "")
  - `RepoInfo.content_budget_used` (int, default 0)
- **No mock data in production paths:** N/A (display-only code)

### Deliverables

Exact replacements for `_print_worker_summary` sections:

**Line 26 (intake SHA):** Replace `output.get('repo_sha', '?')[:12]` with `(output.get('repo_sha') or '?')[:12]`

**Line 42 (understand files):** Replace `repo.get('content_budget_used', 0) / 1024` with `(repo.get('content_budget_used') or 0) / 1024`

**Lines 44-46 (generate):** Replace entire block:
```python
elif worker_name == "generate":
    pages = output.get("pages", [])
    stats = output.get("generation_stats", {})
    typer.echo(f"  Pages:     {len(pages)}")
    typer.echo(f"  LLM calls: {stats.get('llm_calls', 0)}")
    typer.echo(f"  Fallbacks: {stats.get('fallback_count', 0)}")
    typer.echo(f"  Duration:  {stats.get('duration_seconds', 0):.1f}s")
```

**Lines 57-58 (publish):** Replace entire block:
```python
elif worker_name == "publish":
    patches = output.get("patches", [])
    pr = output.get("pr", {})
    typer.echo(f"  Patches:   {len(patches)}")
    typer.echo(f"  PR:        {pr.get('url', 'none')} ({pr.get('state', '?')})")
```

### Hard Rules

- Keep public signatures unchanged (`_print_worker_summary(worker_name, output)`)
- No new deps
- Keep code/docs/tests in sync (H1 tests must match updated field names)

### Review Dimensions (5/5 targets)

| Dimension | What 5/5 means |
|-----------|----------------|
| Correctness | Every field name verified against Pydantic model source |
| Robustness | All `.get()` chains handle None/missing safely |
| Minimality | Surgical changes, no unrelated edits |
| Maintainability | Field names documented in comments referencing model class |
| Consistency | All 5 worker summaries follow the same `key: value` alignment pattern |

### Runbook

```
1. Read src/launcher/cli/main.py (current)
2. Apply the 4 fixes listed in Deliverables
3. Run: PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
4. Verify 665+ passed, 0 failed
5. Smoke test: python -m launcher.cli.main run configs/pilots/aspose-cells-foss-python.yaml --dry-run
   (validates import chain, no runtime crash)
```
