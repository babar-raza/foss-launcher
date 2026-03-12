---
id: TC-HYBRID-03
title: "Format Matrix Extraction — FormatRecord with can_import/can_export/test_count"
status: Done
priority: High
owner: "Agent-B"
updated: "2026-03-10"
tags: [evidence-model, format-matrix, extraction]
depends_on: [TC-HYBRID-01]
allowed_paths:
  - plans/taskcards/TC-HYBRID-03_format-matrix.md
  - src/launcher/models/product.py
  - src/launcher/models/understanding.py
  - src/launcher/workers/understand/extract/_deterministic.py
  - src/launcher/workers/understand/extract/_entry.py
  - tests/unit/workers/test_understand.py
  - reports/TC-HYBRID-03/evidence.md
  - reports/agents/B/TC-HYBRID-03/self_review.md
  - reports/agents/B/TC-HYBRID-03/plan.md
evidence_required:
  - reports/TC-HYBRID-03/evidence.md
---

# Taskcard TC-HYBRID-03 — Format Matrix Extraction (FormatRecord)

## Objective

Add `FormatRecord` (format name, extension, `can_import`, `can_export`, `caveats`,
`test_count`) to the extracted evidence model, populated deterministically from
test files and README format tables. This gives the contradiction gate (TC-HYBRID-06)
a ground-truth matrix to compare against generated format claims, eliminating the
class of hallucination where the LLM claims a format "can be exported" when the
source code shows otherwise.

## Required spec references

- `specs/product_model.md` (Section: ProductEvidence, supported_formats)
- `specs/worker_understand.md` (Section: Phase B — deterministic extraction)
- `specs/worker_evaluate.md` (Section: format claims validation)

## Scope

### In scope
- Add `FormatRecord` model to `src/launcher/models/product.py`
- Add `format_matrix: list[FormatRecord]` to `ApiSurface` in `product.py`
- Add `extract_format_matrix()` function to `_deterministic.py`
- Wire `extract_format_matrix()` into `_entry.py` Phase B (deterministic) pass
- Unit tests: format matrix populated from fixture test files, `can_export=False` detected for excluded formats, `test_count` accurate

### Out of scope
- Contradiction detection gate (TC-HYBRID-06) — this TC only provides the data model
- Changing `ProductEvidence.supported_formats` (existing string list preserved; FormatRecord is additive)
- TypeScript/Java/.NET format extraction (Python-first; extension can be added later)

## Inputs

- `src/launcher/models/product.py` — `ApiSurface` model (will be extended)
- `src/launcher/models/understanding.py` — `ProductEvidence` model (may be extended with `format_matrix`)
- `src/launcher/workers/understand/extract/_deterministic.py` — claim extraction patterns (import from here)
- `src/launcher/workers/understand/extract/_entry.py` — orchestrates Phase B calls
- Test files from product repos (contain `FileFormat.OBJ`, `SaveOptions.*` patterns)
- README format tables (markdown table rows with format names and capabilities)

## Outputs

- `FormatRecord` model in `product.py` with: `name`, `extension`, `can_import`, `can_export`, `caveats`, `test_count`
- `ApiSurface.format_matrix: list[FormatRecord]` — populated by `extract_format_matrix()`
- `extract_format_matrix(repo_dir, product)` function in `_deterministic.py`
- Evidence: at least 1 FormatRecord with `can_export=False` in fixture test

## Allowed paths

- plans/taskcards/TC-HYBRID-03_format-matrix.md
- src/launcher/models/product.py
- src/launcher/models/understanding.py
- src/launcher/workers/understand/extract/_deterministic.py
- src/launcher/workers/understand/extract/_entry.py
- tests/unit/workers/test_understand.py
- reports/TC-HYBRID-03/evidence.md
- reports/agents/B/TC-HYBRID-03/self_review.md
- reports/agents/B/TC-HYBRID-03/plan.md

### Allowed paths rationale
- `product.py`: `FormatRecord` lives alongside `ApiSurface`
- `understanding.py`: `ProductEvidence` may need `format_matrix` field
- `_deterministic.py`: `extract_format_matrix()` is a deterministic extractor
- `_entry.py`: wires extractor call into the Phase B pipeline
- `test_understand.py`: unit tests for new extraction
- `reports/`: evidence and self-review

## Implementation steps

### Step 1: Add FormatRecord model to product.py

Add to `src/launcher/models/product.py` (before `ApiSurface`):

```python
class FormatRecord(LauncherBaseModel):
    """A single file format with import/export capability from source evidence.

    Populated deterministically from test files and README format tables.
    Used by the contradiction gate to verify generated format claims.
    """
    name: str              # display name, e.g. "OBJ", "FBX", "GLTF"
    extension: str = ""    # file extension, e.g. ".obj", ".fbx"
    can_import: bool = False
    can_export: bool = False
    caveats: list[str] = Field(default_factory=list)   # known limitations
    test_count: int = 0    # number of test files referencing this format
    source_evidence: str = ""  # file:line where this was extracted from
```

Then add to `ApiSurface`:
```python
class ApiSurface(LauncherBaseModel):
    """Extracted API surface of a product repository."""
    public_classes: list[str]
    import_allowlist: list[str]
    confidence: Literal["high", "medium", "low"]
    api_identifiers: list[str] = Field(default_factory=list)
    class_briefs: list[ClassBrief] = Field(default_factory=list)
    enums: list[EnumRecord] = Field(default_factory=list)      # from TC-HYBRID-02
    format_matrix: list[FormatRecord] = Field(default_factory=list)  # NEW
```

Note: TC-HYBRID-02 and TC-HYBRID-03 both touch `product.py`. Coordinate to avoid
conflicts: TC-HYBRID-02 adds `enums` to `ApiSurface`; TC-HYBRID-03 adds `format_matrix`.
Both are additive optional fields.

### Step 2: Implement extract_format_matrix() in _deterministic.py

Add the following function to `src/launcher/workers/understand/extract/_deterministic.py`:

```python
_FORMAT_EXTENSIONS: dict[str, str] = {
    # 3D formats
    "OBJ": ".obj", "FBX": ".fbx", "GLTF": ".gltf", "GLB": ".glb",
    "STL": ".stl", "DAE": ".dae", "COLLADA": ".dae", "3DS": ".3ds",
    "USD": ".usd", "USDA": ".usda", "USDC": ".usdc", "USDZ": ".usdz",
    "DXF": ".dxf", "DWG": ".dwg", "IFC": ".ifc", "STEP": ".step",
    "IGES": ".iges", "PLY": ".ply", "X3D": ".x3d",
    # Document formats
    "PDF": ".pdf", "DOCX": ".docx", "DOC": ".doc", "XLSX": ".xlsx",
    "XLS": ".xls", "PPTX": ".pptx", "PPT": ".ppt",
    "HTML": ".html", "MHTML": ".mhtml", "RTF": ".rtf", "TXT": ".txt",
    "CSV": ".csv", "TSV": ".tsv", "ODS": ".ods", "ODT": ".odt",
    # Image formats
    "PNG": ".png", "JPEG": ".jpg", "JPG": ".jpg", "BMP": ".bmp",
    "TIFF": ".tiff", "GIF": ".gif", "SVG": ".svg", "WEBP": ".webp",
    # Note formats
    "ONE": ".one", "ONETOC2": ".onetoc2",
}

# Pattern to match FileFormat.OBJ, FileFormat.FBX, etc.
_FORMAT_PATTERN = re.compile(
    r'\b(?:FileFormat|SaveFormat|LoadFormat|ExportFormat|ImportFormat)'
    r'\s*\.\s*([A-Z][A-Z0-9_]{1,15})\b'
)

# SaveOptions / LoadOptions patterns
_SAVE_LOAD_PATTERN = re.compile(
    r'\b([A-Z][a-zA-Z0-9]+(?:Save|Load|Export|Import)Options)\b'
)

# README table patterns: | OBJ | ✓ | ✗ | or | OBJ | Yes | No |
_README_TABLE_IMPORT_RE = re.compile(r'[✓✔✅]|yes|supported|true', re.I)
_README_TABLE_EXPORT_RE = re.compile(r'[✓✔✅]|yes|supported|true', re.I)
_README_TABLE_NEGATIVE_RE = re.compile(r'[✗✘❌]|no|unsupported|false|-', re.I)


def extract_format_matrix(
    repo_dir: Path,
    product: ProductIdentity,
) -> list["FormatRecord"]:
    """Scan test files and README tables to build a format capability matrix.

    Strategy:
    1. Scan test files for `FileFormat.XXX` usage → can_import / can_export heuristic
    2. Scan README format tables (markdown tables with format names) → can_import / can_export
    3. Merge results: source beats README when both present

    Returns a list of FormatRecord with test_count and capability flags.
    On any failure: return empty list (never raise).
    """
    from launcher.models.product import FormatRecord

    format_counts: dict[str, int] = {}
    format_context: dict[str, set[str]] = {}  # format_name → set of context strings

    # --- Strategy 1: scan test files ---
    try:
        test_dirs = [repo_dir / "tests", repo_dir / "test", repo_dir / "examples"]
        test_files: list[Path] = []
        for td in test_dirs:
            if td.is_dir():
                for ext in (".py", ".ts", ".cs", ".java"):
                    test_files.extend(sorted(td.rglob(f"*{ext}"))[:50])

        for tf in test_files[:100]:
            try:
                content = tf.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            for m in _FORMAT_PATTERN.finditer(content):
                fmt = m.group(1).upper()
                format_counts[fmt] = format_counts.get(fmt, 0) + 1
                # Collect surrounding context (line) to guess import/export
                start = max(0, m.start() - 200)
                end = min(len(content), m.end() + 200)
                ctx = content[start:end].lower()
                if fmt not in format_context:
                    format_context[fmt] = set()
                format_context[fmt].add(ctx)
    except Exception:
        logger.warning("extract_format_matrix: test file scan failed", exc_info=True)

    # --- Strategy 2: README format tables ---
    readme_formats: dict[str, dict[str, bool]] = {}
    try:
        for readme_name in ("README.md", "README.rst", "docs/formats.md"):
            readme_path = repo_dir / readme_name
            if not readme_path.exists():
                continue
            content = readme_path.read_text(encoding="utf-8", errors="replace")
            for line in content.split("\n"):
                stripped = line.strip()
                if not stripped.startswith("|"):
                    continue
                cells = [c.strip() for c in stripped.split("|") if c.strip()]
                if len(cells) < 2:
                    continue
                fmt_name = cells[0].upper().replace(".", "").strip()
                if fmt_name not in _FORMAT_EXTENSIONS and len(fmt_name) > 6:
                    continue
                if len(fmt_name) < 2 or re.match(r"^[-:]+$", fmt_name):
                    continue
                # Heuristic: cells[1] = import capability, cells[2] = export capability
                can_import = bool(_README_TABLE_IMPORT_RE.search(cells[1])) if len(cells) > 1 else False
                can_export = bool(_README_TABLE_EXPORT_RE.search(cells[2])) if len(cells) > 2 else False
                # Only record if at least one capability signal found
                if can_import or can_export or _README_TABLE_NEGATIVE_RE.search(cells[1] if cells else ""):
                    readme_formats[fmt_name] = {"can_import": can_import, "can_export": can_export}
    except Exception:
        logger.warning("extract_format_matrix: README table scan failed", exc_info=True)

    # --- Build FormatRecord list ---
    all_formats = set(format_counts.keys()) | set(readme_formats.keys())
    records: list[FormatRecord] = []
    for fmt in sorted(all_formats):
        test_count = format_counts.get(fmt, 0)
        ctx_strings = format_context.get(fmt, set())

        # Heuristic: if "save" or "export" or "write" in context → can_export
        can_export_src = any(
            kw in ctx for ctx in ctx_strings for kw in ("save", "export", "write", "tosave", "tofile")
        )
        # Heuristic: if "load" or "import" or "read" or "open" in context → can_import
        can_import_src = any(
            kw in ctx for ctx in ctx_strings for kw in ("load", "import", "read", "open", "fromfile")
        )

        # Source beats README
        if fmt in readme_formats:
            can_export = readme_formats[fmt]["can_export"] or (can_export_src and test_count > 0)
            can_import = readme_formats[fmt]["can_import"] or (can_import_src and test_count > 0)
        else:
            can_export = can_export_src and test_count > 0
            can_import = can_import_src and test_count > 0

        if test_count == 0 and fmt not in readme_formats:
            continue  # no evidence at all → skip

        records.append(FormatRecord(
            name=fmt,
            extension=_FORMAT_EXTENSIONS.get(fmt, ""),
            can_import=can_import,
            can_export=can_export,
            test_count=test_count,
            source_evidence=str(repo_dir),
        ))

    logger.info("extract_format_matrix: %d format records extracted", len(records))
    return records
```

### Step 3: Wire into _entry.py

In `src/launcher/workers/understand/extract/_entry.py`, find where `_extract_api_surface()` is called and add a format matrix extraction call:

After `api_surface = _extract_api_surface(repo_dir, product)`, add:
```python
# Phase B.2: format matrix extraction
try:
    from launcher.workers.understand.extract._deterministic import extract_format_matrix
    format_matrix = extract_format_matrix(repo_dir, product)
    if format_matrix:
        api_surface = api_surface.model_copy(update={"format_matrix": format_matrix})
        logger.info("format_matrix: %d formats extracted", len(format_matrix))
except Exception:
    logger.warning("extract_format_matrix failed", exc_info=True)
```

The `model_copy(update=...)` pattern is the Pydantic v2 way to create an updated copy.

### Step 4: Unit tests

In `tests/unit/workers/test_understand.py`, add tests:

```python
class TestFormatMatrix:
    def test_extract_format_matrix_from_test_files(self, tmp_path):
        """FormatRecord populated from test files with FileFormat.OBJ patterns."""
        test_dir = tmp_path / "tests"
        test_dir.mkdir()
        (test_dir / "test_export.py").write_text(
            "scene.save('out.obj', FileFormat.OBJ)  # save to OBJ"
        )
        (test_dir / "test_import.py").write_text(
            "scene = Scene.from_file('input.fbx', FileFormat.FBX)  # load FBX"
        )
        product = ProductIdentity(
            family="3d", platform="python",
            display_name="Aspose.3D", canonical_import="aspose_3d_foss",
            repo_url="file://" + str(tmp_path),
        )
        result = extract_format_matrix(tmp_path, product)
        names = {r.name for r in result}
        assert "OBJ" in names
        assert "FBX" in names

    def test_format_record_can_export_false_when_no_save_context(self, tmp_path):
        """FormatRecord.can_export=False when format only appears in read/load context."""
        test_dir = tmp_path / "tests"
        test_dir.mkdir()
        (test_dir / "test_import_only.py").write_text(
            "scene = Scene.from_file('input.obj', FileFormat.OBJ)  # load only"
        )
        product = ProductIdentity(
            family="3d", platform="python",
            display_name="Aspose.3D", canonical_import="aspose_3d_foss",
            repo_url="file://" + str(tmp_path),
        )
        result = extract_format_matrix(tmp_path, product)
        obj = next((r for r in result if r.name == "OBJ"), None)
        assert obj is not None
        assert obj.can_import is True
        assert obj.can_export is False

    def test_format_matrix_empty_on_no_test_files(self, tmp_path):
        """Returns empty list when no test files exist."""
        product = ProductIdentity(
            family="3d", platform="python",
            display_name="Aspose.3D", canonical_import="aspose_3d_foss",
            repo_url="file://" + str(tmp_path),
        )
        result = extract_format_matrix(tmp_path, product)
        assert result == []

    def test_api_surface_format_matrix_wired(self, tmp_path, monkeypatch):
        """ApiSurface.format_matrix populated after _entry.py wiring."""
        # patch extract_format_matrix to return a known record
        from launcher.models.product import FormatRecord
        monkeypatch.setattr(
            "launcher.workers.understand.extract._deterministic.extract_format_matrix",
            lambda repo_dir, product: [FormatRecord(name="FBX", can_import=True, can_export=True)]
        )
        # ... call _extract_api_surface or _entry run_extract() and assert format_matrix populated
```

### Step 5: Run tests

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_understand.py -v --tb=short
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=no
```

### Step 6: Write evidence and self-review

Create `reports/TC-HYBRID-03/evidence.md` and `reports/agents/B/TC-HYBRID-03/self_review.md`.

## Failure modes

### Failure mode 1: No test files found in repo (sparse checkout)

**Detection**: `test_dirs` all empty; `format_counts == {}`
**Resolution**: Fall back to README table scan. If README also empty, return `[]`. `ApiSurface.format_matrix` stays `[]`; downstream consumers must handle empty list.
**Gate**: `test_format_matrix_empty_on_no_test_files` verifies empty return doesn't crash

### Failure mode 2: model_copy() not available (Pydantic v1 path)

**Detection**: `AttributeError: 'ApiSurface' has no attribute 'model_copy'`
**Resolution**: Use `api_surface.copy(update={"format_matrix": format_matrix})` as Pydantic v1 fallback. Check project's Pydantic version first — v2 uses `model_copy`, v1 uses `copy`.
**Gate**: `python -c "import pydantic; print(pydantic.VERSION)"` → verify version

### Failure mode 3: TC-HYBRID-02 and TC-HYBRID-03 both modify ApiSurface in product.py simultaneously

**Detection**: Merge conflict in `product.py` — both add fields to `ApiSurface`
**Resolution**: TC-HYBRID-02 adds `enums: list[EnumRecord]`; TC-HYBRID-03 adds `format_matrix: list[FormatRecord]`. These are independent fields. The agent completing second must merge the first agent's change before writing.
**Gate**: After both TCs complete, `ApiSurface` must have both `enums` and `format_matrix`

### Failure mode 4: README table parsing false positives (header row detected as format)

**Detection**: `fmt_name = "FORMAT"` or `"NAME"` — table header rows
**Resolution**: Skip names that match common header words: `{"FORMAT", "NAME", "TYPE", "EXT", "EXTENSION", "DESCRIPTION"}`. Also skip names that are all dashes `---`.
**Gate**: Unit test with a README table fixture verifies header rows are skipped

## Task-specific review checklist

1. [ ] `FormatRecord` model added to `product.py` with all required fields
2. [ ] `ApiSurface.format_matrix: list[FormatRecord]` added (default empty list)
3. [ ] `extract_format_matrix()` function implemented in `_deterministic.py`
4. [ ] `_entry.py` wires `extract_format_matrix()` call after `_extract_api_surface()`
5. [ ] `can_export=False` correctly detected when format only in load/read context
6. [ ] `test_count` reflects actual count of test files referencing the format
7. [ ] Returns empty list (no raise) when no test files or README
8. [ ] Docstrings complete on `FormatRecord` and `extract_format_matrix()`
9. [ ] Spec file `specs/product_model.md` updated with `FormatRecord` and `ApiSurface.format_matrix`
10. [ ] Schema `"description"` fields present for new model properties
11. [ ] Checked `docs/README.md` ownership map for trigger events

## Deliverables

1. `src/launcher/models/product.py` — `FormatRecord` model, `ApiSurface.format_matrix` field
2. `src/launcher/workers/understand/extract/_deterministic.py` — `extract_format_matrix()` function
3. `src/launcher/workers/understand/extract/_entry.py` — wiring call
4. `tests/unit/workers/test_understand.py` — 4 new `TestFormatMatrix` tests
5. `reports/TC-HYBRID-03/evidence.md` — test output, format records for fixture repos
6. `reports/agents/B/TC-HYBRID-03/self_review.md` — 12-dimension self-review

## Acceptance checks

1. [ ] `FormatRecord` importable from `launcher.models.product`
2. [ ] `ApiSurface.format_matrix` field exists and defaults to `[]`
3. [ ] `extract_format_matrix()` returns at least 1 record with correct `can_export=False` for load-only fixture
4. [ ] `_entry.py` populates `api_surface.format_matrix` after Phase B run
5. [ ] All new TestFormatMatrix tests pass
6. [ ] Full test suite passes: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=no`

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: `api_surface.format_matrix` non-empty for fixture repo with FileFormat patterns
- [ ] Evidence captured: reports/TC-HYBRID-03/evidence.md
- [ ] Doc freshness: `python scripts/check_doc_freshness.py --since HEAD~N` clean / acknowledged

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_understand.py -v -k "format"
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=no
```

**Expected results**:
- All `TestFormatMatrix` tests pass
- Full suite passes (3325+ total)

## Integration boundary proven

**Upstream**: Product repo test files (`tests/`) and README.md → `extract_format_matrix()` reads them
**Downstream**: `ApiSurface.format_matrix` consumed by TC-HYBRID-06 (contradiction gate) and TC-HYBRID-07 (holistic context injection)
**Contract**: `ApiSurface.format_matrix: list[FormatRecord]` — default empty list; never None; safe for iteration; `FormatRecord.can_export` is boolean (not nullable)
