# TC-4306 Changes

## Files Modified

### 1. src/launcher/workers/scout/scout.py

**Lines changed:** ~1082-1148 (inserted `_select_main_csproj` function + updated `_parse_csproj_first`), ~999-1007 (dotnet build_system detection)

- Added `_select_main_csproj(csproj_files, canonical_import)` function that:
  - Excludes test projects (path contains "test" relative to repo root)
  - Excludes exe projects (XML `<OutputType>Exe</OutputType>`)
  - Prefers canonical_import match via `<AssemblyName>` or `<PackageId>` XML tags
  - Falls back to shortest relative path (closest to repo root)
  - Uses common ancestor for relative path computation to avoid matching temp dir names
- Updated `_parse_csproj_first(repo_dir, canonical_import="")` to use `_select_main_csproj()` with sorted + deterministic order
- Added TC-4306 dotnet build_system detection: any `.csproj` file in `file_tree` → adds `"dotnet"` to `build_systems`

### 2. src/launcher/workers/understand/adapters/_dotnet.py

**Lines changed:** Full file rewrite of `detect_package_root` and `build_import_allowlist`

- `detect_package_root`: Replaced `csproj_files[0]` (alphabetical first) with full ranking logic:
  - Uses `csproj.relative_to(repo_dir)` for test detection (fixes temp-dir false-positive bug)
  - Excludes test/exe projects progressively
  - Prefers canonical_import XML match
  - Falls back to shortest relative path
- `build_import_allowlist`: Removed premature `break` after first namespace:
  - Now collects ALL distinct namespaces with canonical prefix (up to 20)
  - Enables import filtering across all sub-namespaces (Aspose.ThreeD.Animation, etc.)

### 3. src/launcher/workers/understand/extract/_api_surface.py

**Lines changed:** ~361-369 (the main file iteration loop)

- Added adapter dispatch for `.cs` files when adapter is available:
  - When `adapter` is not None and file extension matches `adapter.file_extensions`
  - Calls `adapter.extract_class_details()` for typed tree-sitter extraction
  - Falls back to `analyze_file_safe()` for other file types

### 4. src/launcher/workers/understand/worker.py

**Lines changed:** ~510-542 (after `run_extract()` returns)

- Added `api_extraction_status` classification after extraction:
  - `"failed"` if 0 public classes
  - `"partial"` if < 5 public classes
  - `"ok"` if >= 5 public classes
- Logs warning + emits `"api_extraction_status"` event when status is not `"ok"`

### 5. tests/unit/workers/test_scout_facts.py

**Lines added:** ~253-296 (2 new tests)

- `test_dotnet_build_system_detected`: verifies .csproj → "dotnet" in build_systems
- `test_multi_csproj_selects_library_project`: verifies multi-project ranking (lib vs Converter/Tests)

### 6. tests/unit/workers/understand/test_dotnet_adapter.py

**Lines added:** ~212-310 (new `TestDotNetAdapterPackageRoot` class with 5 tests)

- `test_detect_package_root_multi_project`: multi-project → main lib dir selected
- `test_detect_package_root_single_csproj`: single .csproj → correct dir
- `test_detect_package_root_no_csproj_fallback`: no .csproj → "src" fallback
- `test_build_import_allowlist_all_namespaces`: all 6 Aspose.ThreeD.* namespaces collected
- `test_build_import_allowlist_excludes_foreign_namespaces`: System.Collections excluded
