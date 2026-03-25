# TC-4306 Execution Plan (Completed)

## Problem Chain Fixed
1. `glob("**/*.csproj")[0]` → alphabetically first → picks Converter.csproj
2. Converter.csproj is an Exe project → its parent dir becomes `package_root`
3. Main library .cs files are excluded from extraction
4. Result: public_classes=[], api_identifiers=[] → broken pipeline

## Solution Applied
1. **Change 1**: `_select_main_csproj()` in scout.py — ranking function that excludes test/exe, prefers canonical match, falls back to shortest path. `_parse_csproj_first()` updated to use it.
2. **Change 2**: dotnet build_system detection in `_extract_shared_facts()` — extension-based since .csproj has no fixed filename.
3. **Change 3**: `detect_package_root()` in `_dotnet.py` — same ranking logic (duplicated to avoid circular imports), uses relative paths for test detection.
4. **Change 4**: `build_import_allowlist()` in `_dotnet.py` — removed premature `break`, collects all namespaces with canonical prefix.
5. **Change 5**: Adapter dispatch in `_api_surface.py` — routes .cs files through DotNetExtractor for typed tree-sitter extraction.
6. **Change 6**: `api_extraction_status` event in `worker.py` — observability for extraction failures.

## Bug Found
The `is_test` detection using full absolute paths caused false positives in pytest temp dirs. Fixed by using relative paths from repo_dir (or common ancestor for scout.py where repo_dir isn't passed).

## Status: DONE
All 6 changes implemented. All 12 new tests pass. Full suite: 4740 passed.
