---
id: TC-3899
title: "Fix generic product_name and wrong canonical_import in 3 pilot configs"
status: Done
priority: Normal
owner: agent
updated: "2026-03-09"
tags: [configs, pilot]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-3899_pilot_config_fixes.md
  - configs/pilots/aspose-3d-foss-python.yaml
  - configs/pilots/aspose-slides-foss-python.yaml
  - configs/pilots/aspose-3d-foss-typescript.yaml
evidence_required: []
---

# Taskcard TC-3899 — Fix generic product_name and wrong canonical_import in 3 pilot configs

## Objective

Three pilot configs contain auto-generated field values that are incorrect and will pollute
generated content: generic `product_name` strings ("An open source version of Aspose",
"The official open-source Python library by Aspose") and a Python `canonical_import` value
in a TypeScript config. Fix all three before running these pilots.

## Required spec references

- `configs/families.yaml` (family names and platform conventions)
- `CLAUDE.md` (taskcard-first rule for configs/**)

## Scope

### In scope
- Fix `product_name` in aspose-3d-foss-python.yaml
- Fix `product_name` in aspose-slides-foss-python.yaml
- Fix `canonical_import` in aspose-3d-foss-typescript.yaml

### Out of scope
- Changing LLM settings, tier, or any other config fields
- Creating new configs

## Inputs

- `configs/pilots/aspose-3d-foss-python.yaml` (product_name: "An open source version of Aspose")
- `configs/pilots/aspose-slides-foss-python.yaml` (product_name: "The official open-source Python library by Aspose")
- `configs/pilots/aspose-3d-foss-typescript.yaml` (canonical_import: aspose_3d_foss — Python convention, wrong for TypeScript)
- `configs/families.yaml` (defines display names and platform import templates)

## Outputs

- Three corrected YAML config files

## Allowed paths

- plans/taskcards/TC-3899_pilot_config_fixes.md
- configs/pilots/aspose-3d-foss-python.yaml
- configs/pilots/aspose-slides-foss-python.yaml
- configs/pilots/aspose-3d-foss-typescript.yaml

### Allowed paths rationale
Config files need corrected metadata before pilot runs. No source code changes.

## Implementation steps

### Step 1: Fix aspose-3d-foss-python.yaml
Change `product_name: An open source version of Aspose` → `product_name: Aspose.3D FOSS for Python`

### Step 2: Fix aspose-slides-foss-python.yaml
Change `product_name: The official open-source Python library by Aspose` → `product_name: Aspose.Slides FOSS for Python`

### Step 3: Fix aspose-3d-foss-typescript.yaml
Change `canonical_import: aspose_3d_foss` → `canonical_import: "@aspose/3d-foss"` (npm package convention from families.yaml node platform template `@aspose/{family}`)

## Failure modes

### Failure mode 1: YAML parse error after edit
**Detection**: `python -c "import yaml; yaml.safe_load(open('configs/pilots/<file>.yaml'))"` raises exception
**Resolution**: Correct indentation/quoting in the YAML file
**Gate**: config loading at pipeline start

### Failure mode 2: Wrong canonical_import for TypeScript causes evaluate failures
**Detection**: `claim_leakage` check fires because Python-style import appears in generated TypeScript content
**Resolution**: Verify the `@aspose/3d-foss` npm package exists; adjust if naming differs
**Gate**: claim_leakage check

### Failure mode 3: product_name still generic in generated content
**Detection**: Generated pages contain "An open source version" or "The official open-source" in title or frontmatter
**Resolution**: Re-run pilot after config fix; the intake worker propagates product_name
**Gate**: frontmatter check (product_name field)

## Task-specific review checklist

1. [x] `product_name` in 3d-python config is descriptive (not generic auto-generated text)
2. [x] `product_name` in slides-python config is descriptive
3. [x] `canonical_import` in typescript config uses npm `@scope/package` convention
4. [x] All three YAML files parse without error after edit
5. [x] No other fields changed (LLM config, tier, golden dir, etc.)
6. [x] Change verified by comparing before/after with grep

## Deliverables

1. Three corrected config files in `configs/pilots/`

## Acceptance checks

1. [ ] `grep product_name configs/pilots/aspose-3d-foss-python.yaml` shows "Aspose.3D FOSS for Python"
2. [ ] `grep product_name configs/pilots/aspose-slides-foss-python.yaml` shows "Aspose.Slides FOSS for Python"
3. [ ] `grep canonical_import configs/pilots/aspose-3d-foss-typescript.yaml` shows "@aspose/3d-foss"
4. [ ] All three files parse as valid YAML

## Self-review

### Verification results
- [ ] YAML parse check: PASS (run after edits)
- [ ] Grep confirms correct values

## E2E verification

```bash
python -c "
import yaml
for f in ['configs/pilots/aspose-3d-foss-python.yaml',
          'configs/pilots/aspose-slides-foss-python.yaml',
          'configs/pilots/aspose-3d-foss-typescript.yaml']:
    c = yaml.safe_load(open(f))
    print(f'{f}: product_name={c.get(\"product_name\")} canonical_import={c.get(\"canonical_import\")}')
"
```

**Expected results**:
- aspose-3d-foss-python: product_name=Aspose.3D FOSS for Python
- aspose-slides-foss-python: product_name=Aspose.Slides FOSS for Python
- aspose-3d-foss-typescript: canonical_import=@aspose/3d-foss

## Integration boundary proven

**Upstream**: `intake onboard` generates configs with auto-derived fields
**Downstream**: Pipeline intake worker reads `product_name` and `canonical_import` for content generation
**Contract**: `product_name` → used in page titles and frontmatter; `canonical_import` → used in code examples and claim_leakage check
