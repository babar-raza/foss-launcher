# Phase Hardening: Intake + Understand — TC-4060 + TC-4061
**Generated**: 2026-03-11
**Source**: Repo Analyst deep inspection + Orchestrator Protocol execution
**Taskcards**: TC-4060 (Phase 1 Intake), TC-4061 (Phase 2 Understand)

## Context
Deep code inspection of the first two pipeline phases revealed 13 confirmed root-cause defects.
The system has correct separation of concerns (batch onboarding vs runtime intake) but the
runtime path has platform bias, weak acquisition signals, and the understand phase has
Python-only self-review that silently passes semantically broken non-Python runs.

## Goals
1. TC-4060: Platform-correct acquisition — remove Python/Aspose bias from defaults, strengthen artifact, fix config_generator
2. TC-4061: Platform-correct understanding — fix synthetic snippets, code fences, api_surface warnings, evidence provenance
3. Both phases must be manually verified on Python + TypeScript + empty fixtures
4. All existing tests must continue to pass

## Assumptions
- VERIFIED: `_resolve_identity` code-level default at worker.py:204 is Aspose-shaped
- VERIFIED: `_generate_synthetic_snippets` has no platform gate (generates Python syntax always)
- VERIFIED: `_build_snippet_context` hardcodes `` ```python `` fence for all languages
- VERIFIED: `api_surface_empty` self-review check gated on `_python_like` — non-Python silently passes
- VERIFIED: `config_generator._derive_canonical_import` hardcodes `{brand}_{family}_foss` for all platforms
- VERIFIED: `ProductEvidence` has no `format_evidence_source` field
- VERIFIED: SharedFacts already has `install_command` (platform-aware, from _INSTALL_CMD_MAP)
- VERIFIED: TC-4030 changes already in place (shared_facts has description/python_requires/dependencies/entrypoints)

## Steps (TC-4060)
1. Fix code-level display_name default — remove "Aspose" brand
2. Extend Python-shaped canonical_import warning to `families_yaml_fallback` provenance
3. Add `acquisition_confidence` field to intake_bundle.json artifact
4. Add `repo_signals` to artifact (readme_present, is_empty_clone, files_estimated)
5. Write `.clone_timestamp` alongside `.clone_sha` in clone.py
6. Log cache age on cache-hit path
7. Add `force_refresh` param to `clone_repo_cached`
8. Fix `config_generator._derive_canonical_import` — platform-aware, not Python-defaulted

## Steps (TC-4061)
1. Remove `_python_like` gate from api_surface self-review checks; use severity tiers
2. Add `platform` and `tree_sitter_available` to `extraction_audit.json`
3. Gate `_generate_synthetic_snippets` on platform == "python"
4. Fix `_build_evidence_context` to use `shared_facts.install_command` not always pip_command
5. Fix `_build_snippet_context` to use `snippet.language` for code fence labels
6. Add WARNING log when `_detect_package_root` returns ""
7. Emit MissingInfoEntry when TreeSitter unavailable for non-Python api_surface
8. Add `format_evidence_source` field to ProductEvidence model
9. Populate `format_evidence_source` in _entry.py
10. Update `understanding_bundle.schema.json` with new field

## Acceptance criteria
- `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_intake.py -v` — all pass
- `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/ -v` — all pass
- `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_understand.py -v` — all pass
- `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q` — no regressions
- intake_bundle.json contains: acquisition_confidence, repo_signals, field_provenance
- extraction_audit.json contains: platform, tree_sitter_available
- Non-Python synthetic snippet count == 0 for TypeScript fixture

## Evidence commands
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_intake.py -v --tb=short
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/ -v --tb=short
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_understand.py -v --tb=short
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q --tb=short
```

## Risks + rollback
- Schema change (understanding_bundle.schema.json): bump $comment version, all existing bundles still valid (field is additive)
- `config_generator._derive_canonical_import` change: affects pilot config generation only, not runtime path
- `_python_like` removal: medium severity warnings fire for non-Python — correct behavior, not regression
- Rollback any file: `git checkout <file>` on branch v2

## Open questions
(none — all verified against live codebase)
