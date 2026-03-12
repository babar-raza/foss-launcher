---
id: TC-3903
title: "Fix wrong repo_url in aspose-note-foss-python.yaml"
status: In-Progress
priority: Critical
owner: agent
updated: "2026-03-09"
tags: [configs, pilot, blocker]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-3903_note_python_repo_url_fix.md
  - configs/pilots/aspose-note-foss-python.yaml
evidence_required: []
---

# Taskcard TC-3903 — Fix wrong repo_url in aspose-note-foss-python.yaml

## Objective

`aspose-note-foss-python.yaml` has `repo_url: https://github.com/aspose-note/Aspose.Note-for-Python-via-.NET`
which returns "Repository not found" from GitHub. The correct FOSS URL (confirmed
from a successful prior run `260309_082341_note_python_35f6`) is
`https://github.com/aspose-note-foss/Aspose.Note-FOSS-for-Python`.

## Required spec references

- `configs/families.yaml`

## Scope

### In scope
- Fix `repo_url` in `aspose-note-foss-python.yaml`

### Out of scope
- Any other config field

## Inputs

- `configs/pilots/aspose-note-foss-python.yaml` — wrong repo_url
- Evidence: `runs/260309_082341_note_python_35f6/intake_checkpoint.json` shows correct URL

## Outputs

- Corrected YAML config

## Allowed paths

- plans/taskcards/TC-3903_note_python_repo_url_fix.md
- configs/pilots/aspose-note-foss-python.yaml

## Implementation steps

### Step 1: Fix repo_url
Change `repo_url: "https://github.com/aspose-note/Aspose.Note-for-Python-via-.NET"`
→ `repo_url: "https://github.com/aspose-note-foss/Aspose.Note-FOSS-for-Python"`

## Failure modes

### Failure mode 1: URL unreachable after fix
**Detection**: `git ls-remote https://github.com/aspose-note-foss/Aspose.Note-FOSS-for-Python HEAD` fails
**Resolution**: Confirm repo exists; check spelling
**Gate**: intake worker clone

### Failure mode 2: YAML parse error
**Detection**: python -c "import yaml; yaml.safe_load(open(...))" raises exception
**Resolution**: Fix quoting
**Gate**: config loading

### Failure mode 3: Wrong product
**Detection**: Intake worker resolves wrong product_name/family
**Resolution**: Verify family=note in the resolved intake checkpoint
**Gate**: intake self-review

## Task-specific review checklist

1. [x] URL points to aspose-note-foss org (not aspose-note)
2. [x] URL confirmed reachable with git ls-remote
3. [x] No other fields changed
4. [x] YAML valid after edit
5. [x] Matches evidence from successful prior run
6. [x] Only allowed_paths file modified

## Deliverables

1. Corrected `configs/pilots/aspose-note-foss-python.yaml`

## Acceptance checks

1. [ ] `git ls-remote $(grep repo_url configs/pilots/aspose-note-foss-python.yaml | awk '{print $2}' | tr -d '"') HEAD` succeeds
2. [ ] note-python pilot run completes past intake

## Self-review

### Verification results
- [ ] URL reachable: PASS (verified above)
- [ ] YAML valid: PASS

## E2E verification

```bash
python -c "import yaml; c=yaml.safe_load(open('configs/pilots/aspose-note-foss-python.yaml')); print(c['repo_url'])"
# Expected: https://github.com/aspose-note-foss/Aspose.Note-FOSS-for-Python
```

## Integration boundary proven

**Upstream**: Intake config reader loads repo_url
**Downstream**: Clone worker uses repo_url for git clone
**Contract**: repo_url must be a valid, accessible GitHub HTTPS URL
