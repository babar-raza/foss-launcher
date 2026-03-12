---
id: TC-3898
title: "generate_config(): populate missing extended fields (github_ref, product_slug, budgets, telemetry)"
status: Done
priority: Normal
allowed_paths:
  - src/launcher/intake/config_generator.py
---

## Objective
Fix pre-existing test failure: `test_extended_fields_present_but_ignored`.
`generate_config()` must populate four extended metadata fields that downstream systems consume.

## Required spec references
- `specs/github_intake.md` Section 6 (pilot config generation)

## Scope

**In:**
- `src/launcher/intake/config_generator.py` — `_DEFAULT_TEMPLATE` + `generate_config()`

**Out:**
- RunConfig model (no change — `extra="ignore"` already handles these)
- Pilot YAML files in `configs/pilots/` (hand-crafted, not auto-generated)
- Any test files (existing tests just need the implementation to exist)

## Inputs
- Repo metadata dict (from GitHub API / org_scanner)

## Outputs
- `generate_config()` returns dict containing `github_ref`, `product_slug`, `budgets`, `telemetry`

## Implementation steps
1. Add `budgets` and `telemetry` to `_DEFAULT_TEMPLATE` (static defaults)
2. Compute `github_ref` = `"{full_name}@{default_branch}"` in `generate_config()`
3. Compute `product_slug` = `"{family}-{platform}"` in `generate_config()`

## Acceptance checks
- [x] `test_extended_fields_present_but_ignored` passes
- [x] All 5 existing roundtrip tests still pass
- [x] Full suite: 0 new failures
- [x] `config["github_ref"]` == `"aspose-cells-foss/Aspose.Cells-for-Python-via-.NET@main"` for mock repo
- [x] `config["product_slug"]` == `"cells-python"` for cells/python
- [x] `config["budgets"]["max_tokens"]` == 200_000
- [x] `config["telemetry"]["enabled"]` == False
