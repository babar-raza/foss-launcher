# Deploy Remediation Plan — 2026-03-11

**Source**: Chat-derived from full deploy/ audit session (2026-03-10/11)
**Materialized**: 2026-03-11T00:04:28Z
**Status**: IN PROGRESS

---

## Context

Full manual audit of all 143 files in `deploy/` against cached repo clones (`runs/.clone_cache/`).
Five product families covered: Cells/Python, Note/Python, Slides/Python, 3D/Python, 3D/TypeScript.

### Audit Findings Summary

| Family | Files | PASS | FAIL | CRIT | Root Cause |
|--------|------:|-----:|-----:|-----:|-----------|
| Cells/Python | ~38 | ~60% | ~40% | 5 | Wrong imports (`aspose.cells`/`aspose_cells_foss`), `add_column()` DNE → `add_bar()`, false PDF export claims |
| Note/Python | ~30 | 45% | 55% | 6 | LLM-batch (2026-03-09) hallucinated .NET API; correct batch (2026-03-10) passes |
| Slides/Python | ~20 | 0% | 100% | 4 | Wrong import (`aspose_slides_foss` vs `aspose.slides_foss`); NotImplementedError features claimed |
| 3D/Python+TS | ~32 | 79% | 21% | 3 | Placeholder in license.md; code bug `_iter_nodes`; fake testimonial |
| Products pages | 4 | 0% | 100% | 2 | 0-word body content; fabricated testimonials |

### All 142 manifest SHA256 hashes stale (0% match rate).
### 1 orphan file not tracked in manifest.

---

## Goals

1. **Phase A — Delete**: Remove all irredeemable files (wrong API, garbled titles, 381KB dumps, 0% pass rate families)
2. **Phase B — Fix Content**: Targeted fixes for surviving files (Cells `add_column`→`add_bar`, 3D 3 blockers + 8 warnings)
3. **Phase C — Fix Structure**: Strip Hugo `{{ }}` artifacts, fix product pages (0-word body), fix broken relative links, fix garbled Slides titles
4. **Phase D — Manifest Rebuild**: Regenerate `deploy/manifest.json` from scratch after all file changes
5. **TC-HYBRID Phase 1**: Implement TC-HYBRID-02 (typed sigs) + TC-HYBRID-03 (format matrix) to enable proper Slides regeneration later

---

## Assumptions

- `deploy/` is NOT a protected path — no taskcard required for file edits
- Slides regeneration is DEFERRED until TC-HYBRID pipeline improvements (Phase 1+) complete
- Note LLM-batch files (17 files, 2026-03-09 date with `canonical_import: aspose_note_foss`) are all irredeemable — delete all
- Note hand-written batch (2026-03-10 date, no `canonical_import` field) are correct — keep all
- 3D/TypeScript files are mostly correct — keep all, fix 3 blockers

---

## Step-by-Step Execution

### Phase A — Deletions

**Delete these Cells files** (wrong API / garbled / dump):
1. `deploy/blog.aspose.org/cells/python/introducing-cells-foss-python.md` (381KB commercial API dump, duplicate)
2. `deploy/blog.aspose.org/cells/python/microsoft-windows-windows-desktop-spreadsheets.md` (garbled keyword-stuffed title, wrong import)
3. `deploy/kb.aspose.org/cells/python/developer-guide/print-microsoft-excel-files-to-spreadsheets.md` (all placeholder text)
4. `deploy/kb.aspose.org/cells/python/developer-guide/use-cases.md` (414KB dump)
5. `deploy/kb.aspose.org/cells/python/developer-guide/high-quality-file-format-spreadsheets.md` (wrong API claims)
6. `deploy/kb.aspose.org/cells/python/developer-guide/spreadsheet-generation-spreadsheets.md` (wrong API claims)
7. `deploy/reference.aspose.org/cells/python/per_module-spreadsheets-1.md` (fabricated classes)
8. `deploy/reference.aspose.org/cells/python/per_module-spreadsheets-2.md` (fabricated classes)
9. `deploy/reference.aspose.org/cells/python/per_module-spreadsheets-3.md` (fabricated classes)

**Delete these Note files** (LLM-batch, hallucinated .NET API):
- All 17 files with `canonical_import: aspose_note_foss` frontmatter (2026-03-09 date)
  - `deploy/blog.aspose.org/note/python/introducing-note-foss-python.md`
  - `deploy/blog.aspose.org/note/python/exportpdf-notebooks.md`
  - `deploy/docs.aspose.org/note/python/developer-guide/this-repository-provides-a-python-notebooks.md`
  - All others in docs/note/python/developer-guide/ with LLM-batch markers

**Delete ALL Slides files** (0% pass rate, wrong import throughout, deferred for regeneration post-TC-HYBRID):
- All ~20 files under `deploy/*/slides/python/`

### Phase B — Content Fixes

**Cells fixes** (surviving files):
- Find all 9 occurrences of `add_column()` → replace with `add_bar()` across surviving Cells files
- Fix all import lines: `import aspose.cells` → `from aspose_cells import Workbook` (or per context)
- Fix all import lines: `from aspose_cells_foss import` → `from aspose_cells import`

**3D fixes** (3 blockers):
1. `deploy/docs.aspose.org/3d/python/getting-started/license.md` — replace `Copyright (c) [repo-url] Contributors` with correct license text
2. `deploy/kb.aspose.org/3d/python/how-to-convert-3d-models-in-python.md` — fix `_iter_nodes` used before defined (move def above first use or inline)
3. `deploy/products.aspose.org/3d/python/_index.md` — remove fabricated testimonial; add real content to 0-word body

**3D warnings** (8 warnings to address):
- Minor factual corrections in 3D files flagged during audit

### Phase C — Structural Fixes

1. **Strip Hugo `{{ }}` artifacts** in ~17 files — remove `{{ .Title }}`, `{{ partial ... }}`, etc.
2. **Fix product pages** — `deploy/products.aspose.org/cells/python/_index.md` and Note equivalent have 0-word body: add real content
3. **Fix 17 broken relative links** — relative links using `../` that resolve incorrectly in Hugo
4. **Fix 2 garbled Slides titles** (if any Slides files survive Phase A)
5. **Remove orphan file** from `deploy/blog.aspose.org/cells/python/introducing-cells-foss-python/index.md` directory (flat duplicate)

### Phase D — Manifest Rebuild

Run the manifest regeneration script to rebuild `deploy/manifest.json` with correct SHA256 hashes for all surviving files.

---

## Acceptance Criteria

- [ ] All files with `canonical_import: aspose_note_foss` DELETED
- [ ] All Slides files DELETED (deferred)
- [ ] 381KB Cells dump files DELETED
- [ ] Fabricated class reference files DELETED
- [ ] No `add_column()` calls remain in surviving Cells files
- [ ] No `import aspose.cells` (commercial) remains in any file
- [ ] No unresolved `[repo-url]` or `[topic]` placeholders remain
- [ ] No Hugo `{{ }}` artifacts remain
- [ ] Products pages have non-zero body content
- [ ] `_iter_nodes` code bug fixed
- [ ] `deploy/manifest.json` SHA256 hashes all match actual file contents
- [ ] No files in `deploy/` that are NOT tracked in `manifest.json`

---

## Risks

| Risk | Mitigation |
|------|-----------|
| Deleting Note hand-written files by mistake | Gate on date field AND absence of `canonical_import: aspose_note_foss` |
| Cells surviving files also have wrong imports | Run grep after fix pass to confirm 0 matches |
| Manifest rebuild misses orphan files | Run `find deploy/ -name "*.md"` count vs manifest count |
| TC-HYBRID Phase 1 breaks existing 3325 tests | Run full test suite after each TC implementation |

---

## Evidence Commands

```bash
# Verify deletions
find deploy/ -name "*.md" | wc -l

# Verify no commercial import remains
grep -r "import aspose.cells" deploy/ --include="*.md"

# Verify no LLM-batch Note files remain
grep -r "aspose_note_foss" deploy/ --include="*.md"

# Verify no Slides files remain
find deploy/ -path "*/slides/*" -name "*.md"

# Verify no Hugo artifacts remain
grep -r "{{" deploy/ --include="*.md"

# Verify no add_column remains
grep -r "add_column" deploy/ --include="*.md"

# Verify manifest count matches file count
python -c "import json; m=json.load(open('deploy/manifest.json')); print(len(m['files']))"
```
