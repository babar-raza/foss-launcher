# KNOW-001 Evidence

## Skill run output (cells/python)

```
success: True
artifacts: ['model.yaml', 'api_surface.md', 'claims.md', 'snippets/snippets_index.json',
  'snippets/snippet_001.py', 'snippets/snippet_002.py', ..., 'snippets/snippet_031.py',
  'formats.md', 'limitations.md', 'install.md', 'sync_manifest.yaml']
errors: []
warnings: []
```

Total artifacts: 39 (7 primary files + snippets_index.json + 31 snippet files)

## model.yaml content

```yaml
family: cells
platform: python
display_name: Aspose.Cells FOSS
canonical_import: aspose_cells_foss
repo_url: https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-Python
repo_sha: 5b5b28eb372c28f4529928ea81696a0031b68d60
phase_store_source: phase_store/cells/python/understand.json
ingested_at: '2026-03-15T07:58:18.453401+00:00'
richness_tier: A
claim_count: 135
snippet_count: 31
api_confidence: high
last_diff_check: null
stale_since: null
content_paths: []
page_grades: {}
```

## claims.md first H2

```markdown
## CLM-cells-621552
**Text**: Aspose.Cells for Python supports importing and exporting CSV files using the Workbook class.
**Kind**: format
**Confidence**: 0.75
**Source**: llm
**Evidence**:
- `README.md:38` — workbook.save_as_csv("output.csv")
**Snippets**: _none_
```

## api_surface.md first H2

```markdown
## CSVHandler
**Docstring**: Handles CSV import and export operations for workbooks.
**Methods**:
- `save_csv(workbook, file_path: str, options: Optional[CSVSaveOptions]) -> None`
- `save_csv_to_string(workbook, options: Optional[CSVSaveOptions]) -> str`
- `load_csv(workbook, file_path: str, options: Optional[CSVLoadOptions]) -> None`
- `load_csv_from_string(workbook, csv_content: str, options: Optional[CSVLoadOptions]) -> None`
**Properties**: _none_
```

## File size checks

| File | Size (bytes) |
|------|-------------|
| model.yaml | 498 |
| api_surface.md | 20,933 |
| claims.md | 40,152 |
| snippets/snippets_index.json | 54,933 |
| formats.md | 381 |
| limitations.md | 802 |
| install.md | 349 |
| sync_manifest.yaml | 857 |
| snippets/ (31 files) | 106 – 29,099 bytes each |

## Verification checks

```
claims.md H2 sections: 135
api_surface.md H2 sections: 56
snippet .py files: 31
snippets_index.json exists: True
sync_manifest artifacts: ['model.yaml', 'api_surface.md', 'claims.md', 'formats.md', 'limitations.md', 'install.md']
model.yaml required fields missing: none
richness_tier valid: True
api_confidence valid: True
```

## Idempotency check

Second run produced: success=True, errors=[], artifact_count=39 (identical to first run).

## Snippet file sample

`knowledge/cells/python/snippets/snippet_001.py` — 370 bytes, Python code extracted from source.

## snippets_index.json sample entry

```json
{
  "id": "snip_001",
  "lang": "python",
  "source_file": "tests/test_workbook.py",
  "source_type": "extracted",
  "syntax_valid": true,
  "claim_ids": [],
  "content_hash": "sha256:..."
}
```
