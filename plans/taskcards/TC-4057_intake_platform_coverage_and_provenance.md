---
id: TC-4057
title: "Phase 1 — Intake platform coverage + acquisition artifact provenance"
status: Done
priority: High
owner: "agent"
updated: "2026-03-11"
tags: [intake, identity, platform, artifact]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-4057_intake_platform_coverage_and_provenance.md
  - configs/families.yaml
  - src/launcher/workers/intake/worker.py
  - tests/unit/workers/test_intake.py
evidence_required:
  - reports/TC-4057/evidence.md
---

# Taskcard TC-4057 — Phase 1: Intake platform coverage + acquisition artifact provenance

## Objective

Fix three structural weaknesses in the Intake worker that allow wrong identity to flow silently
into downstream workers: (1) families.yaml only has 4 platforms, leaving go/rust/php/ruby/kotlin/
swift/typescript/javascript with Python-shaped import defaults; (2) the acquisition artifact
(`intake_bundle.json`) does not distinguish verified vs. inferred vs. config-override fields,
making human review impossible; (3) there is no explicit warning when a platform is not found
in families.yaml.

## Required spec references

- `specs/system_contract.md` (Error codes, severity levels)
- `specs/github_intake.md` (Platform resolution)
- `specs/worker_understand.md` (Identity requirements for downstream)

## Scope

### In scope
- Add go, rust, php, ruby, kotlin, swift to `configs/families.yaml` platforms section
- Add provenance tracking in `_resolve_identity()`: return which source each field came from
- Write provenance into `intake_bundle.json` artifact
- Emit WARNING log when platform is not in families.yaml
- Update tests to verify provenance fields and unknown-platform warning

### Out of scope
- Changing the IntakeBundle model schema (no downstream contract changes)
- Adding platform support in extract adapters (separate taskcard)
- Fixing launch_tier auto-detection (separate concern)

## Inputs

- `configs/families.yaml` — current platform coverage (4 platforms)
- `src/launcher/workers/intake/worker.py` — identity resolution + artifact writing
- `tests/unit/workers/test_intake.py` — existing 29 tests

## Outputs

- Updated `configs/families.yaml` with 10 platform entries (was 4)
- Updated `src/launcher/workers/intake/worker.py` with provenance tracking
- Updated `tests/unit/workers/test_intake.py` with provenance and coverage tests
- `reports/TC-4057/evidence.md` (test output + artifact samples)

## Allowed paths

- plans/taskcards/TC-4057_intake_platform_coverage_and_provenance.md
- configs/families.yaml
- src/launcher/workers/intake/worker.py
- tests/unit/workers/test_intake.py

### Allowed paths rationale
- families.yaml: primary fix location for platform coverage gap
- worker.py: contains _resolve_identity and artifact writing
- test_intake.py: must verify the changes with tests

## Implementation steps

### Step 1: Add missing platform entries to families.yaml

Add go, rust, php, ruby, kotlin, swift, typescript (TypeScript uses npm pattern similar to node)
to the platforms section. Each entry must have:
- `import_tpl`: language-specific import convention (NOT Python-shaped)
- `install_cmd`: correct package manager command
- `lang_tag`: language identifier
- `file_ext`: primary file extension
- `doc_comment`: documentation comment style

### Step 2: Add provenance tracking to _resolve_identity()

Change the function signature to return a 4-tuple:
`(display_name, canonical_import, runtime_import, provenance_dict)`

The provenance_dict must record for each field: source = "families_yaml" | "families_yaml_fallback"
| "config_override" | "inferred_default"

### Step 3: Write provenance into acquisition artifact

In `IntakeWorker.run()`, update the `_artifact` dict written to `intake_bundle.json` to include
a `"field_provenance"` key with the provenance_dict.

### Step 4: Emit WARNING when platform not in families.yaml

If the platform lookup returns an empty dict from families.yaml (i.e., the platform is not
listed), emit a WARNING log message noting which platform was not found and which defaults
were used.

### Step 5: Add/update tests

Add tests for:
- go, rust, php, ruby platform resolution (each gets correct import_tpl, not Python default)
- provenance dict appears in artifact for families.yaml-derived, override, and inferred cases
- unknown platform emits warning (caplog or mock)

## Failure modes

### Failure mode 1: families.yaml TOML/YAML syntax error introduced

**Detection**: `yaml.safe_load` raises exception at startup; all tests fail with parse error
**Resolution**: Run `python -c "import yaml; yaml.safe_load(open('configs/families.yaml'))"` before committing
**Gate**: test_intake.py loads families.yaml — parse failure kills all 29 tests

### Failure mode 2: import_tpl contains Python-shaped placeholder

**Detection**: A new platform entry uses `aspose_{family}_foss` — same as Python default
**Resolution**: Verify each new platform entry produces a distinct, language-appropriate string
**Gate**: New test `test_go_platform_not_python_shaped` explicitly checks this

### Failure mode 3: Provenance tracking breaks when families.yaml is absent

**Detection**: `_resolve_identity()` crashes when families.yaml file is missing
**Resolution**: The function already has `if families_path.exists()` guard — provenance must still
work when families.yaml is absent (all fields → "inferred_default")
**Gate**: test_intake.py::test_resolve_identity_no_families_yaml

## Task-specific review checklist

1. [ ] Every new platform in families.yaml has a non-Python import_tpl
2. [ ] install_cmd uses the correct package manager (go get, cargo add, gem install, etc.)
3. [ ] Provenance dict is present in intake_bundle.json artifact
4. [ ] Provenance correctly distinguishes families_yaml vs. inferred_default vs. config_override
5. [ ] WARNING is emitted (and testable) for unknown platforms
6. [ ] All 29 existing tests still pass
7. [ ] Docstrings updated for _resolve_identity() to reflect new return signature
8. [ ] Spec file confirmed: no drift (families.yaml is config, not spec)
9. [ ] Schema description fields: intake_bundle.json is not schema-governed (informal artifact)
10. [ ] docs/README.md ownership: no new guides triggered by this change
11. [ ] No downstream contract change (IntakeBundle model unchanged)

## Deliverables

1. `configs/families.yaml` with 10 platform entries
2. `src/launcher/workers/intake/worker.py` with provenance-tracked identity resolution
3. `tests/unit/workers/test_intake.py` with ≥5 new tests
4. `reports/TC-4057/evidence.md` with test output and sample artifact

## Acceptance checks

1. [ ] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_intake.py -v` — all pass
2. [ ] `python -c "import yaml; d = yaml.safe_load(open('configs/families.yaml')); print(list(d['platforms'].keys()))"` — shows ≥10 platforms
3. [ ] intake_bundle.json written in a test run contains `"field_provenance"` key
4. [ ] A go-platform run produces `canonical_import` starting with "go" or containing the family, NOT "aspose_{family}_foss"

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: families.yaml parse — PASS
- [ ] Evidence captured: reports/TC-4057/evidence.md
- [ ] Doc freshness: confirmed no spec drift

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_intake.py -v
python -c "
import yaml
d = yaml.safe_load(open('configs/families.yaml'))
print('Platforms:', list(d['platforms'].keys()))
for p, v in d['platforms'].items():
    print(f'  {p}: import_tpl={v.get(\"import_tpl\", \"MISSING\")}')
"
```

**Expected results**:
- All intake tests pass (≥34 total after new tests)
- Output shows ≥10 platforms, each with distinct import_tpl

## Integration boundary proven

**Upstream**: RunConfig (family + platform from configs/pilots/*.yaml)
**Downstream**: UnderstandWorker consumes IntakeBundle — display_name and canonical_import used in LLM prompts
**Contract**: IntakeBundle model unchanged; acquisition artifact enriched with provenance (additive)
