---
id: TC-3920
title: "Fix Aspose.Cells FOSS Python pilot config to correct repo URL and rewrite deploy content"
status: In-Progress
priority: High
owner: agent
updated: "2026-03-10"
tags: [cells, python, config, content]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-3920_fix-cells-foss-python-repo-url.md
  - configs/pilots/aspose-cells-foss-python.yaml
  - deploy/products.aspose.org/cells/python/_index.md
  - deploy/docs.aspose.org/cells/python/developer-guide/_index.md
  - deploy/docs.aspose.org/cells/python/developer-guide/features.md
  - deploy/docs.aspose.org/cells/python/developer-guide/working-with-cells.md
  - deploy/docs.aspose.org/cells/python/developer-guide/working-with-charts.md
  - deploy/docs.aspose.org/cells/python/developer-guide/working-with-formulas.md
  - deploy/docs.aspose.org/cells/python/getting-started/_index.md
  - deploy/docs.aspose.org/cells/python/getting-started/installation.md
  - deploy/kb.aspose.org/cells/python/_index.md
  - deploy/kb.aspose.org/cells/python/how-to-convert-excel-to-pdf-python.md
  - deploy/kb.aspose.org/cells/python/how-to-create-charts-python.md
  - deploy/kb.aspose.org/cells/python/how-to-load-spreadsheets-python.md
  - deploy/kb.aspose.org/cells/python/how-to-style-cells-python.md
  - deploy/reference.aspose.org/cells/python/_index.md
  - deploy/blog.aspose.org/cells/python/introducing-cells-foss-python/index.md
  - deploy/blog.aspose.org/cells/python/python-excel-chart-tutorial/index.md
evidence_required:
  - reports/TC-3920/evidence.md
---

# Taskcard TC-3920 — Fix Aspose.Cells FOSS Python pilot config and rewrite deploy content

## Objective

The pilot config `configs/pilots/aspose-cells-foss-python.yaml` points to the wrong upstream repository (`aspose-cells/Aspose.Cells-for-Python-via-.NET`). The correct FOSS repo is `https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-Python`. Fix the config, clone the correct repo, and rewrite all 10 deploy pages for Python to be accurate against the actual FOSS library.

## Required spec references

- `configs/pilots/aspose-cells-foss-python.yaml` (repo_url field)
- `deploy/` output structure conventions

## Scope

### In scope
- Fix `repo_url` and `product_name` in pilot config
- Clone correct FOSS repo
- Rewrite all 10 `deploy/*/cells/python/` pages from correct repo evidence

### Out of scope
- TypeScript platform (no repo exists)
- Other pilot configs
- Pipeline code changes

## Inputs

- `https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-Python` (cloned)
- Golden corpus templates

## Outputs

- Updated `configs/pilots/aspose-cells-foss-python.yaml`
- 10 rewritten deploy pages for cells/python

## Allowed paths

- `configs/pilots/aspose-cells-foss-python.yaml`
- `deploy/products.aspose.org/cells/python/_index.md`
- `deploy/docs.aspose.org/cells/python/developer-guide/_index.md`
- `deploy/docs.aspose.org/cells/python/developer-guide/features.md`
- `deploy/docs.aspose.org/cells/python/getting-started/_index.md`
- `deploy/docs.aspose.org/cells/python/getting-started/installation.md`
- `deploy/kb.aspose.org/cells/python/_index.md`
- `deploy/kb.aspose.org/cells/python/how-to-convert-excel-to-pdf-python.md`
- `deploy/kb.aspose.org/cells/python/how-to-create-charts-python.md`
- `deploy/reference.aspose.org/cells/python/_index.md`
- `deploy/blog.aspose.org/cells/python/introducing-cells-foss-python/index.md`

### Allowed paths rationale
Config fix + content rewrite scope exactly.

## Implementation steps

### Step 1: Clone correct repo
`git clone https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-Python`

### Step 2: Read and analyze repo
Read README, pyproject.toml, src/, examples/, tests/, LICENSE.

### Step 3: Fix pilot config
Update `repo_url` and `product_name`.

### Step 4: Rewrite 10 deploy pages
Rewrite each page based only on evidence from the correct FOSS repo.

## Failure modes

### Failure mode 1: Repo not publicly accessible
**Detection**: `git clone` returns 404 or permission error
**Resolution**: Check org name spelling; verify repo is public
**Gate**: Content accuracy

### Failure mode 2: FOSS repo has different API from commercial repo
**Detection**: import names, class names, or method signatures differ
**Resolution**: Use only what is confirmed in the FOSS repo; mark unknowns clearly
**Gate**: No hallucinated APIs

### Failure mode 3: FOSS repo has minimal content
**Detection**: README is sparse; no examples
**Resolution**: Use only verified claims; note evidence gaps explicitly
**Gate**: All content evidence-bound

## Task-specific review checklist

1. [ ] `repo_url` in config matches `aspose-cells-foss/Aspose.Cells-FOSS-for-Python`
2. [ ] `product_name` updated if different from commercial version
3. [ ] pip install command verified from FOSS repo
4. [ ] Import statement verified from FOSS repo
5. [ ] All code examples copied or adapted from actual FOSS repo examples
6. [ ] No APIs mentioned that are not in FOSS repo
7. [ ] All 10 deploy pages written from FOSS evidence
8. [ ] Spec file updated if worker behavior changed (or confirmed no spec drift)
9. [ ] Schema `"description"` fields present for all new/changed properties
10. [ ] Checked `docs/README.md` ownership map
11. [ ] If a new `docs/guides/` file was added: `docs/README.md` index updated

## Deliverables

1. Updated `configs/pilots/aspose-cells-foss-python.yaml`
2. 10 rewritten deploy pages at correct paths

## Acceptance checks

1. [ ] `repo_url` field in config is `https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-Python`
2. [ ] All 10 deploy files exist and are non-empty
3. [ ] No code examples reference APIs not found in the FOSS repo

## Self-review

### Verification results
- [ ] Tests: N/A (content task)
- [ ] Validation: Manual page review
- [ ] Evidence captured: FOSS repo clone

## E2E verification

```bash
ls deploy/products.aspose.org/cells/python/
ls deploy/docs.aspose.org/cells/python/
ls deploy/kb.aspose.org/cells/python/
ls deploy/reference.aspose.org/cells/python/
ls deploy/blog.aspose.org/cells/python/introducing-cells-foss-python/
```

**Expected results**:
- All 10 required files present
- Config URL updated

## Integration boundary proven

**Upstream**: `aspose-cells-foss/Aspose.Cells-FOSS-for-Python` GitHub repo
**Downstream**: `deploy/` content served by site
**Contract**: Pages must accurately reflect the public FOSS library API
