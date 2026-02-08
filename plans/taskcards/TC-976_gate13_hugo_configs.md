---
id: TC-976
title: "Fix Gate 13 (Hugo Build) - Copy Hugo Configuration Files"
status: Draft
priority: High
owner: "Agent-B (Implementation)"
updated: "2026-02-05"
tags: ["gate-13", "hugo", "config", "validation"]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-976_gate13_hugo_configs.md
  - src/launch/workers/w1_repo_scout/clone.py
  - specs/reference/hugo-configs/configs/**
evidence_required:
  - runs/vfv_tc971-975_iter10/vfv_3d_report.json
  - reports/agents/agent-b/TC-976/evidence.md
spec_ref: "3e91498d6b9dbda85744df6bf8d5f3774ca39c60"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# Taskcard TC-976 — Fix Gate 13 (Hugo Build) - Copy Hugo Configuration Files

## Objective
Fix Gate 13 (Hugo Build) failure by copying Hugo configuration files from aspose.net to pilot site directories, enabling successful Hugo builds and passing validation.

## Problem Statement
Gate 13 fails with error "Unable to locate config file or config directory" because FOSS pilots don't clone a separate site repository containing Hugo configs. Hugo requires configuration files in `RUN_DIR/work/site/` but they are never placed during pilot setup.

## Required spec references
- specs/31_hugo_config_awareness.md (Hugo configuration requirements)
- specs/09_validation_gates.md (Gate 13: Hugo Build validation)
- C:\Users\prora\.claude\plans\magical-prancing-fountain.md (Investigation results and fix strategy)

## Scope

### In scope
- Check if D:\onedrive\Documents\GitHub\aspose.net\configs exists and is accessible
- If not accessible, use reference fixtures at specs/reference/hugo-configs/configs
- Copy Hugo configs to RUN_DIR/work/site/configs/ during pilot setup
- Verify directory structure matches: configs/common.toml, configs/docs.aspose.org/, etc.
- Ensure Gate 13 passes after Hugo configs are in place

### Out of scope
- Modifying Hugo config file contents
- Changing Hugo build command or parameters
- Modifying other validation gates
- Creating custom Hugo themes or layouts

## Inputs
- Source configs: D:\onedrive\Documents\GitHub\aspose.net\configs OR specs/reference/hugo-configs/configs
- Target location: RUN_DIR/work/site/configs/
- Gate 13 implementation: src/launch/workers/w7_validator/gates/gate_13_hugo_build.py

## Outputs
- Hugo config files copied to RUN_DIR/work/site/configs/
- Gate 13 validation passes (ok: true)
- Hugo build completes successfully without errors
- Validation report showing gate_13_hugo_build: ok=true

## Allowed paths
- plans/taskcards/TC-976_gate13_hugo_configs.md
- src/launch/workers/w1_repo_scout/clone.py
- specs/reference/hugo-configs/configs/**

### Allowed paths rationale
TC-976 may modify W1 RepoScout clone.py to copy Hugo configs post-clone, and accesses reference config fixtures for copying.

## Implementation steps

### Step 1: Verify config source availability
Check if source configs exist:
```bash
ls -la "D:\onedrive\Documents\GitHub\aspose.net\configs"
```
If not accessible, verify reference fixtures:
```bash
ls -la specs/reference/hugo-configs/configs/
```

### Step 2: Create config copy script
Option A (Preferred): Create standalone script to copy configs:
```bash
# Create scripts/copy_hugo_configs.py
# This script copies Hugo configs from reference to site directory
```

Option B: Modify W1 RepoScout to copy configs post-clone:
```python
# In src/launch/workers/w1_repo_scout/clone.py
# Add post-clone step to copy configs from reference fixtures
```

### Step 3: Test config copy
Run pilot iteration to verify configs are copied:
```bash
.venv/Scripts/python.exe scripts/run_pilot_vfv.py \
  --pilot pilot-aspose-3d-foss-python \
  --output runs/vfv_iter10/vfv_3d_report.json \
  --allow_placeholders --approve-branch
```

### Step 4: Verify Hugo can find configs
After pilot run, check:
```bash
ls -la runs/r_*/work/site/configs/
hugo --source runs/r_*/work/site/ --help
```

### Step 5: Confirm Gate 13 passes
Check validation report:
```bash
cat runs/r_*/artifacts/validation_report.json | grep -A 5 "gate_13_hugo_build"
```

## Failure modes

### Failure 1: Source configs not accessible
**Symptom**: D:\onedrive\Documents\GitHub\aspose.net\configs not found
**Mitigation**: Use reference fixtures at specs/reference/hugo-configs/configs
**Rollback**: None needed (read-only operation)

### Failure 2: Permission denied copying configs
**Symptom**: Access denied error during copy
**Mitigation**: Check file permissions, use robocopy /COPYALL on Windows
**Rollback**: Remove partially copied configs

### Failure 3: Hugo still can't find configs
**Symptom**: Gate 13 still fails after copy
**Mitigation**: Verify directory structure matches Hugo expectations (config.toml in root or config/_default/)
**Rollback**: None needed (configs don't affect other gates)

## Task-specific review checklist

- [ ] Source config files verified (D:\... OR specs/reference/...)
- [ ] Config copy logic implemented (script OR W1 modification)
- [ ] Directory structure matches Hugo requirements
- [ ] Configs copied successfully during pilot run
- [ ] Hugo build command can find config files
- [ ] Gate 13 passes (validation_report.json shows ok: true)
- [ ] No interference with other gates
- [ ] Evidence collected (commands.sh, validation report)

## Deliverables

1. Hugo config copy mechanism (script or W1 modification)
2. Evidence of successful copy (ls output, file tree)
3. Gate 13 passing validation report
4. Hugo build output showing successful build
5. Self-review.md with scores >= 4/5 on all dimensions

## Acceptance checks

**MUST ALL PASS**:
- [ ] Hugo configs exist in RUN_DIR/work/site/configs/ after pilot run
- [ ] Gate 13 validation passes (ok: true in validation_report.json)
- [ ] Hugo build completes without "config file not found" errors
- [ ] All other gates remain passing (no regressions)
- [ ] Evidence files created in reports/agents/agent-b/TC-976/

## Self-review

**Dimensions**: Coverage, Correctness, Evidence, Test Quality, Maintainability, Safety, Security, Reliability, Observability, Performance, Compatibility, Docs/Specs Fidelity

**Scores** (filled after execution):
- Coverage: ___/5
- Correctness: ___/5
- Evidence: ___/5
- Test Quality: ___/5
- Maintainability: ___/5
- Safety: ___/5
- Security: ___/5
- Reliability: ___/5
- Observability: ___/5
- Performance: ___/5
- Compatibility: ___/5
- Docs/Specs Fidelity: ___/5

**Evidence links**: (Fill after execution)

**Known gaps**: (Must be empty to pass)

## E2E verification

```bash
# Run full pilot with Hugo configs in place
.venv/Scripts/python.exe scripts/run_pilot_vfv.py \
  --pilot pilot-aspose-3d-foss-python \
  --output runs/vfv_iter10/vfv_3d_report.json \
  --allow_placeholders --approve-branch

# Verify Gate 13 passes
cat runs/r_*/artifacts/validation_report.json | jq '.gates[] | select(.name == "gate_13_hugo_build")'

# Check Hugo build output
ls -la runs/r_*/work/site/configs/
```

## Integration boundary proven

**Upstream dependencies**: W1 RepoScout (clone phase)
**Downstream consumers**: W7 Validator (Gate 13)

**Integration tests**:
1. Config copy occurs after W1 clone completes
2. Configs are in place before W7 Gate 13 runs
3. Hugo can locate and parse config files
4. Gate 13 validation succeeds

**Evidence of integration**: Validation report showing gate_13_hugo_build: ok=true
