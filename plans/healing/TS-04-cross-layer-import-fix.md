# TS-04 — Eliminate Cross-Layer Import + Curate Discovery Extensions

## Context

HC-04 introduced `from launcher.workers.understand.file_classifier import LANG_BY_EXT`
inside `shared/code_analyzer.py`. This creates a dependency from a shared utility
to a worker-specific module, violating the project's layer architecture:

```
shared/ (utilities)  →  workers/ (business logic)   BAD
workers/  →  shared/                                 OK
```

If `file_classifier.py` ever imports from `shared/`, this becomes a circular
import. Additionally, `discover_source_files` now iterates ALL `LANG_BY_EXT`
keys including `.sh`, `.sql`, `.ps1`, `.zsh`, `.bash` — non-compilable files
that don't belong in source discovery for a code analysis context.

## Status: Done

## Gap linkage

| Gap ID | Description |
|--------|-------------|
| G-06 | Cross-layer import: `shared/code_analyzer.py` → `workers/understand/file_classifier.py` |
| G-07 | `discover_source_files` includes `.sh`, `.sql`, `.ps1` (over-broad) |

## Role

Senior engineer. Drop-in, production-ready.

## Scope

### Fix

**Option A (preferred)**: Move the `LANG_BY_EXT` dict from
`workers/understand/file_classifier.py` to a new or existing shared module
(e.g., `shared/lang_constants.py` or inline in `shared/code_analyzer.py`),
then import from there in both `file_classifier.py` and `code_analyzer.py`.

**Option B**: Define a curated `_SOURCE_EXTS` set directly in
`code_analyzer.py` for the specific functions that need it (`discover_source_files`,
`analyze_file_safe`, `extract_code_limitations`). Keep the `LANG_BY_EXT`
import in `extract.py` (which is in `workers/` — legal to import from workers).

The recommended approach is **Option B** because:
1. It avoids creating a new module for a single dict
2. `discover_source_files` SHOULD have a curated list (not auto-expanded)
3. `analyze_file_safe` already has the language mapping inline in the
   TreeSitter dispatch
4. `extract_code_limitations` needs a different set than full discovery

Concrete changes:

```python
# code_analyzer.py — replace all LANG_BY_EXT imports with:

_SOURCE_EXTS: set[str] = {
    ".py", ".pyi", ".java", ".cs", ".js", ".mjs", ".cjs", ".jsx",
    ".ts", ".tsx", ".go", ".rs", ".rb", ".php", ".kt", ".kts",
    ".dart", ".scala", ".swift", ".c", ".cpp", ".cc", ".h", ".hpp",
}

# For analyze_file_safe, inline the ext→lang mapping:
_EXT_TO_LANG: dict[str, str] = {
    ".java": "java", ".cs": "csharp", ".js": "javascript",
    ".mjs": "javascript", ".cjs": "javascript", ".jsx": "javascript",
    ".ts": "typescript", ".tsx": "typescript", ".go": "go",
    ".php": "php", ".rs": "rust", ".rb": "ruby",
    ".kt": "kotlin", ".kts": "kotlin", ".dart": "dart",
    ".scala": "scala", ".swift": "swift", ".m": "objc",
    ".cpp": "cpp", ".cc": "cpp", ".hpp": "cpp",
    ".c": "c", ".h": "c",
}
```

Note: This re-introduces `_EXT_TO_LANG` which was deleted by HC-04. That
deletion was wrong — the DRY concern was valid but the fix (importing from
workers) introduced a worse problem. The correct DRY solution is Option A
(shared module), but Option B is simpler and sufficient for now.

### Allowed paths

- `src/launcher/shared/code_analyzer.py`

### Forbidden

Any other file or path.

## Acceptance checks

- **CLI**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest -x` — full suite 0 failures
- **Tests**: `grep -r "from launcher.workers" src/launcher/shared/` returns 0 matches
- **Config respected**: `discover_source_files` does NOT glob for `.sh`, `.sql`, `.ps1`
- **Config respected**: `analyze_file_safe` still routes to TreeSitterAnalyzer for non-Python
- No mock data in production paths

## Deliverables

- Updated `code_analyzer.py` with self-contained extension sets
- No `from launcher.workers` imports in `src/launcher/shared/`
- No TODOs, no stubs

## Hard rules

- Keep public signatures unchanged (`discover_source_files`, `discover_manifests`, `analyze_file_safe`, `extract_code_limitations`)
- No network in offline tests
- Deterministic runs (PYTHONHASHSEED=0)
- No new deps
- Keep code/docs/tests in sync
- The curated `_SOURCE_EXTS` must NOT include `.sh`, `.sql`, `.ps1`, `.zsh`, `.bash`, `.psm1`

## Review dimensions — what 5/5 means for this taskcard

| Dimension | 5/5 means |
|-----------|-----------|
| Thoroughness | ALL `from launcher.workers` imports removed from `shared/` |
| Consistency | `_SOURCE_EXTS` used consistently across discover/analyze/limitations |
| Production grading | No circular import risk; no over-broad globbing |
| Correctness | `analyze_file_safe` still routes all known languages correctly |
| Integration | shared/ layer has zero dependencies on workers/ |
| Performance | `discover_source_files` does ~20 rglob calls instead of 26+ |
| Minimality | Only `code_analyzer.py` changed |
| Robustness | `_EXT_TO_LANG.get(ext)` returns None for unknown → returns `{}` (safe) |

## Now (runbook)

```bash
# 1. Edit code_analyzer.py:
#    a) Add _SOURCE_EXTS set and _EXT_TO_LANG dict at module level
#    b) Replace LANG_BY_EXT imports in discover_source_files, analyze_file_safe, extract_code_limitations
#    c) Remove all `from launcher.workers.understand.file_classifier import LANG_BY_EXT`

# 2. Verify no cross-layer imports
grep -rn "from launcher.workers" src/launcher/shared/
# Expected: 0 matches

# 3. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest -x

# 4. Verify discover_source_files does not include shell/sql
python -c "
exts = {'.py','.pyi','.java','.cs','.js','.mjs','.cjs','.jsx','.ts','.tsx','.go','.rs','.rb','.php','.kt','.kts','.dart','.scala','.swift','.c','.cpp','.cc','.h','.hpp'}
assert '.sh' not in exts
assert '.sql' not in exts
assert '.ps1' not in exts
print('OK')
"
```
