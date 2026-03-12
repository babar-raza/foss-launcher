# AH-05 — Correctness Fixes and Intake Sub-commands

**Context**: Three precision gaps in `agents.md` that cause agents to act
on wrong information:

1. **G-09 (`max_re_runs` inaccurate)**: Section 7 says `max_re_runs=2` is
   "configurable" — it is hardcoded in `run_loop.py`'s `PipelineGraphState`
   initialization. There is no run-config key for it. An agent searching for
   a `max_re_runs` config parameter will waste time.

2. **G-10 (`--run-id` constraint undocumented)**: The CLI accepts `--run-id`
   only when `--resume-from` is also set. Without this constraint documented,
   agents will hit `ValueError("run_id requires resume_from")` with no
   contextual explanation.

3. **G-11 (`launch intake` sub-commands)**: The sub-commands table in Section 2
   lists `launch intake scan` and `launch intake classify` with one-line
   descriptions but no flags, arguments, or usage examples. Agents can't
   use the intake CLI without reading source.

---

## Taskcard AH-05

**Status**: Done
**Gap linkage**: G-09 (max_re_runs inaccurate), G-10 (run_id constraint undocumented), G-11 (intake sub-commands not detailed)
**Role**: Senior engineer. Drop-in, production-ready corrections to `agents.md`.

---

### Scope

**Fix**:
1. In Section 7 (Quality Gate and Re-run Logic), replace "configurable"
   with accurate language: `max_re_runs=2` is hardcoded in `run_loop.py`.
2. In Section 2 (CLI), add a "Constraint" callout block after the
   `--run-id` example documenting the mutual requirement with `--resume-from`.
3. In Section 2, expand the Sub-commands table's intake rows and add a
   "### Intake Sub-commands" section with full flag documentation.

**Allowed paths**:
- `agents.md`
- `plans/healing/AH-05-correctness-and-intake.md`

**Forbidden**: any file under `src/launcher/**`, `configs/**`, `specs/**`,
`tests/**`.

---

### Acceptance checks

**CLI**:
```bash
# 1. Verify max_re_runs is hardcoded (not a RunConfig field)
grep -n "max_re_runs" src/launcher/models/run_config.py
# Expected: no match (it is not a config field)
grep -n "max_re_runs" src/launcher/orchestrator/run_loop.py
# Expected: appears in PipelineGraphState initialization dict with value 2

# 2. Verify run_id requires resume_from constraint in CLI
grep -n "run_id.*resume_from\|resume_from.*run_id" src/launcher/cli/main.py

# 3. Verify intake CLI commands and their flags
python -c "from launcher.cli.intake import intake_app; print('ok')"
.venv/Scripts/python.exe -m launcher.cli.main intake --help
.venv/Scripts/python.exe -m launcher.cli.main intake scan --help
.venv/Scripts/python.exe -m launcher.cli.main intake classify --help
```

**UI/Web/API**: N/A.

**Tests**:
- Manual: the `--run-id` constraint callout matches the error message in
  `src/launcher/cli/main.py` (line: `"run_id requires resume_from"`).
- Manual: `launch intake scan --help` output matches the flags documented
  in the new subsection.
- `python scripts/check_doc_freshness.py --since HEAD~1` exits 0.

**Config respected end-to-end**: Confirm `max_re_runs` is absent from
`RunConfig`, `RunOutput`, and pilot YAML configs (it would be misleading
if an agent tried to set it there).

**No mock data**: All intake CLI flag documentation must match the actual
typer app in `src/launcher/cli/intake.py`.

---

### Deliverables

**1. Targeted edit in Section 7 — fix "configurable" claim**

Replace this sentence in Section 7:
```
`run_loop` allows up to `max_re_runs=2` re-run cycles (configurable).
```
With:
```
`run_loop` allows up to 2 re-run cycles. `max_re_runs=2` is
**hardcoded** in `run_loop.py`'s `PipelineGraphState` initialization —
it is not a run-config parameter. After 2 failed evaluate cycles, the
pipeline returns NO-GO without further attempts.
```

**2. Constraint callout in Section 2 — `--run-id` requirement**

After the `--run-id` example in the "### Invoking via CLI" section, add:

```markdown
> **Constraint**: `--run-id` REQUIRES `--resume-from`. Using `--run-id`
> alone raises `ValueError: "run_id requires resume_from (to avoid
> corrupting an existing run)"`. This is a safety guard — providing an
> explicit run ID without a resume point would silently overwrite the
> existing run's artifacts.
>
> Also: `--resume-from` must come **before** `--stop-after` in pipeline
> order. The CLI validates this and exits with an error if violated.
```

**3. Expanded intake sub-commands section**

Replace the two intake rows in the Sub-commands table with a reference,
then add a full "### Intake Sub-commands" section after the table:

```markdown
### Intake Sub-commands

The `launch intake` sub-group handles repository discovery and
classification outside of a full pipeline run.

#### `launch intake scan`

Scans a GitHub org (or local config) to discover repositories matching
the product family/platform filter.

```bash
.venv/Scripts/python.exe -m launcher.cli.main intake scan \
    --config configs/families.yaml \
    --org <github-org> \
    --family cells \
    --platform python \
    --output intake/discovered_repos.yaml
```

| Flag | Required | Purpose |
|------|----------|---------|
| `--config` | Yes | Path to `families.yaml` (defines family/platform mappings) |
| `--org` | Yes | GitHub org name to scan |
| `--family` | No | Filter by product family (e.g., `cells`) |
| `--platform` | No | Filter by platform (e.g., `python`) |
| `--output` | No | Write discovered repos to YAML (default: stdout) |

#### `launch intake classify`

Classifies a single repository into a product family + platform + tier.

```bash
.venv/Scripts/python.exe -m launcher.cli.main intake classify \
    --repo-url https://github.com/aspose-free/aspose-cells-python \
    --config configs/families.yaml
```

| Flag | Required | Purpose |
|------|----------|---------|
| `--repo-url` | Yes | GitHub URL of the repository to classify |
| `--config` | Yes | Path to `families.yaml` |
| `--output` | No | Write classification result to JSON (default: stdout) |

Output fields: `family`, `platform`, `launch_tier` (A/B/C), `display_name`,
`canonical_import`, `confidence_score`.
```

---

### Hard rules

- Keep public signatures — this is docs; verifying that CLI flags match
  source is the equivalent constraint.
- No new deps — N/A.
- Deterministic — N/A for docs.
- Keep code/docs/tests in sync — all flags documented must match
  `src/launcher/cli/intake.py` exactly.

---

### Review dimensions (5/5 criteria)

| Dimension | 5/5 means for AH-05 |
|-----------|---------------------|
| Thoroughness | All 3 gaps fully closed; intake flags documented with full flag tables |
| Consistency | max_re_runs correction propagates to Section 7 and is consistent with AH-01's PipelineGraphState table (where max_re_runs is listed as hardcoded int) |
| Production grading | An agent can use `launch intake scan` and `launch intake classify` from docs alone; won't hit the run_id ValueError anymore |
| Systematic approach | Three independent fixes applied in the order they appear in agents.md (Section 2, then Section 7) |
| Correctness & spec alignment | max_re_runs hardcoded claim verified against run_loop.py; run_id constraint text copied from actual error message; intake flags verified via --help |
| Scope & constraints adherence | Only agents.md modified; three surgical edits |
| Maintainability & readability | Constraint uses a blockquote callout (visually distinct); intake section uses consistent flag tables |
| Testability & coverage | All acceptance checks are runnable commands with expected output specified |
| Robustness & failure modes | Constraint callout explicitly names the error message so agents can map it back to this doc |
| Performance & efficiency | N/A — docs only |
| Integration & architectural fit | Intake section placed with the other CLI sub-command content in Section 2 |
| Observability & telemetry | N/A |
| Minimality & diff quality | Three targeted edits; no unrelated content touched |

---

### Now (runbook)

```bash
# 1. Verify max_re_runs is NOT in RunConfig
grep -rn "max_re_runs" src/launcher/models/ --include="*.py"
grep -rn "max_re_runs" configs/ --include="*.yaml"
# Expected: no matches in models/ or configs/

# 2. Verify hardcoded value in run_loop.py
grep -n "max_re_runs" src/launcher/orchestrator/run_loop.py
# Expected: two occurrences — _build_resume_state and execute_run initial state dict

# 3. Get the actual run_id error message text
grep -n "run_id requires" src/launcher/orchestrator/run_loop.py src/launcher/cli/main.py

# 4. Get intake CLI flag names (verify against source before documenting)
grep -n "typer.Argument\|typer.Option" src/launcher/cli/intake.py

# 5. Apply the three edits to agents.md

# 6. Run freshness check
python scripts/check_doc_freshness.py --since HEAD~1

# 7. Verify the intake --help output matches what we documented
.venv/Scripts/python.exe -m launcher.cli.main intake scan --help
.venv/Scripts/python.exe -m launcher.cli.main intake classify --help

# 8. Commit
git add agents.md
git commit -m "docs(AH-05): fix max_re_runs accuracy, document run_id constraint, expand intake CLI"
```
