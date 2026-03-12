# Healing Plan — TreeSitter Integration Gaps

## Origin

Self-review of TC-3790 + TC-3791 (TreeSitterAnalyzer foundation + integration).
These taskcards address every meaningful gap identified during honest self-review.

## Gap Inventory

| HC | Gap | Severity | File(s) |
|----|-----|----------|---------|
| HC-01 | `_build_import_allowlist()` uses regex, not TreeSitterAnalyzer | High | extract.py |
| HC-02 | Thread safety: `_parser_cache` has no lock | High | ts_analyzer.py |
| HC-03 | `section_validator.py` import normalization Python-only | Medium | section_validator.py |
| HC-04 | `discover_source_files` missing 7+ extensions | Medium | code_analyzer.py |
| HC-05 | `discover_manifests` missing pom.xml, build.gradle | Medium | code_analyzer.py |
| HC-06 | `extract_code_limitations` only walks `*.py` | Medium | code_analyzer.py |
| HC-07 | DRY violation: `_EXT_TO_LANG` duplicates `LANG_BY_EXT` | Low | code_analyzer.py |
| HC-08 | Dead regex fallback after TreeSitterAnalyzer in code_analyzer | Low | code_analyzer.py |
| HC-09 | `_is_public()` and `normalize_imports` regex fragility | Low | ts_analyzer.py |
| HC-10 | Uses stdlib `logging` instead of project `structlog` | Low | ts_analyzer.py |

## Execution Order

1. **HC-02** (thread safety) — foundational correctness
2. **HC-01** (import allowlist) — highest functional gap
3. **HC-03** (section_validator) — integration completeness
4. **HC-04 + HC-05 + HC-06** (code_analyzer multi-platform) — bundled, same file
5. **HC-07 + HC-08** (DRY + dead code cleanup) — bundled, same file
6. **HC-09** (regex hardening) — low risk
7. **HC-10** (logging) — cosmetic

## Taskcard Files

- `plans/healing/HC-01_import_allowlist_treesitter.md`
- `plans/healing/HC-02_parser_cache_thread_safety.md`
- `plans/healing/HC-03_section_validator_multi_lang.md`
- `plans/healing/HC-04_code_analyzer_multi_platform.md`
- `plans/healing/HC-05_regex_hardening.md`
- `plans/healing/HC-06_logging_structlog.md`
