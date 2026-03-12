---
id: GR-02
title: "Retroactive: add pyproject.toml to TC-3876b allowed_paths"
status: Open
priority: Low
owner: agent
updated: "2026-03-09"
tags: [governance, taskcard, allowed-paths]
depends_on: []
allowed_paths:
  - plans/healing/GR-02-tc3876b-allowed-paths-governance.md
  - plans/taskcards/TC-3876b_check_regression_suite.md
evidence_required:
  - reports/GR-02/evidence.md
---

# GR-02 — Retroactive allowed_paths fix for TC-3876b

## Objective

TC-3876b touched `pyproject.toml` to register the `golden` pytest marker but
`pyproject.toml` was not listed in the taskcard's `allowed_paths`. Fix the
taskcard retroactively to document the actual scope, maintaining governance
accuracy.

## Gap source

TC-3876b self-review: `pyproject.toml` was modified (pytest marker added)
without being declared in the taskcard frontmatter. AG-002 requires allowed_paths
to match all files touched.

## Required spec references

- `CLAUDE.md` (AG-002 — Taskcard-first workflow, allowed_paths governance)
- `.claude/runbooks/taskcards.md`

## Scope

### In scope
- Add `pyproject.toml` to `allowed_paths` in `TC-3876b_check_regression_suite.md`
  frontmatter AND allowed paths section
- Add rationale comment explaining the pytest marker addition

### Out of scope
- Any code changes
- Reverting the `pyproject.toml` change (the change is correct)

## Inputs

- `plans/taskcards/TC-3876b_check_regression_suite.md`

## Outputs

- `plans/taskcards/TC-3876b_check_regression_suite.md` (updated)
- `reports/GR-02/evidence.md`

## Allowed paths

- plans/healing/GR-02-tc3876b-allowed-paths-governance.md
- plans/taskcards/TC-3876b_check_regression_suite.md

### Allowed paths rationale

Retroactive governance fix — only the taskcard needs updating.

## Implementation steps

### Step 1: Update TC-3876b frontmatter allowed_paths

In `plans/taskcards/TC-3876b_check_regression_suite.md`, add to the frontmatter:
```yaml
allowed_paths:
  - plans/taskcards/TC-3876b_check_regression_suite.md
  - tests/golden/__init__.py
  - tests/golden/test_checks_regression.py
  - pyproject.toml  # pytest marker registration (golden marker)
```

### Step 2: Update allowed paths section in body

In the `## Allowed paths` section, add:
```
- pyproject.toml
```

And in `### Allowed paths rationale`:
```
`pyproject.toml` modified to register `@pytest.mark.golden` custom pytest marker
under `[tool.pytest.ini_options] markers`. Without this, pytest warns on
unrecognized marker usage.
```

### Step 3: Create evidence report

Create `reports/GR-02/evidence.md` documenting the retroactive fix.

## Failure modes

### Failure mode 1: Taskcard status already Done — should not be reopened

**Detection**: TC-3876b has status: Done
**Resolution**: Apply the allowed_paths fix WITHOUT changing the status or any
acceptance checks — this is a retroactive documentation correction only
**Gate**: Status remains `Done` after edit

### Failure mode 2: Other pyproject.toml changes not captured

**Detection**: `git diff HEAD pyproject.toml` shows more changes than just the marker
**Resolution**: Document all pyproject.toml sections touched in allowed_paths rationale
**Gate**: Diff review before committing

### Failure mode 3: Frontmatter YAML syntax error after edit

**Detection**: YAML parsing fails on taskcard load
**Resolution**: Validate YAML indentation — `allowed_paths` is a list with `  - ` items
**Gate**: `python -c "import yaml; yaml.safe_load(open('plans/taskcards/TC-3876b_check_regression_suite.md').read().split('---')[1])"`

## Task-specific review checklist

1. [ ] `pyproject.toml` appears in both frontmatter `allowed_paths` and body section
2. [ ] Rationale explains WHY pyproject.toml was needed (pytest marker registration)
3. [ ] TC-3876b status remains `Done` (not changed)
4. [ ] No acceptance checks modified (retroactive only)
5. [ ] YAML frontmatter parses without error
6. [ ] Date updated to 2026-03-09 to reflect the retroactive correction
7. [ ] Spec file: not applicable (taskcard only)
8. [ ] Schema: not applicable
9. [ ] Checked `docs/README.md` — no trigger events apply
10. [ ] No new `docs/guides/` file added

## Deliverables

1. `plans/taskcards/TC-3876b_check_regression_suite.md` (pyproject.toml added to allowed_paths)
2. `reports/GR-02/evidence.md`

## Acceptance checks

1. [ ] `pyproject.toml` appears in TC-3876b frontmatter `allowed_paths`
2. [ ] TC-3876b body `## Allowed paths` section includes `pyproject.toml` with rationale
3. [ ] TC-3876b status remains `Done`
4. [ ] YAML frontmatter is syntactically valid

## Self-review

### Verification results
- [ ] YAML valid: confirmed by python yaml.safe_load
- [ ] Evidence captured: reports/GR-02/evidence.md
- [ ] Doc freshness: not applicable

## E2E verification

```bash
python -c "
import yaml, pathlib
raw = pathlib.Path('plans/taskcards/TC-3876b_check_regression_suite.md').read_text()
fm = raw.split('---')[1]
data = yaml.safe_load(fm)
paths = data.get('allowed_paths', [])
assert 'pyproject.toml' in paths, f'pyproject.toml not in allowed_paths: {paths}'
print('OK: pyproject.toml found in allowed_paths')
"
```

**Expected results**:
- `OK: pyproject.toml found in allowed_paths`

## Integration boundary proven

**Upstream**: TC-3876b implementation (Done, pyproject.toml was modified)
**Downstream**: AG-002 governance audit — taskcard allowed_paths must cover all touched files
**Contract**: `allowed_paths` list ⊇ set of files actually modified in the TC
