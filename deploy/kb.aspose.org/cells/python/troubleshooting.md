---
canonical: https://kb.aspose.org/cells/python/troubleshooting/
canonical_import: aspose_cells_foss
date: '2026-03-11T11:59:24Z'
dateModified: '2026-03-11T11:59:24Z'
datePublished: '2026-03-11T11:59:24Z'
description: This occurs when the CSV file uses a non-UTF-8 encoding (e.g., cp1252
  or Shift-JIS) but `CSVHandler.load_csv()` defaults to UTF-8. To fix, specify the...
display_name: Aspose.Cells FOSS
family: cells
keywords:
- python
- python openpyxl
- openpyxl pandas
- openpyxl in python
- openpyxl documentation
- install openpyxl
- openpyxl cell
- openpyxl pip
lastmod: '2026-03-11T11:59:24Z'
page_role: troubleshooting
platform: python
reading_time: 1
robots: index, follow
seoTitle: Aspose.Cells FOSS Troubleshooting
slug: troubleshooting
title: Troubleshooting
type: troubleshooting
url: /kb.aspose.org/cells/python/troubleshooting/
weight: 9
---

## Common Issues

This section covers frequent issues encountered when using Aspose.Cells FOSS in Python, specifically with classes from the API surface such as `Cell`, `AutoFilter`, `CSVHandler`, and `CFBReader`.

### CSV Import Fails with Encoding Errors

Symptoms include garbled text or UnicodeDecodeError when loading CSV files. This occurs when the CSV file uses a non-UTF-8 encoding (e.g., cp1252 or Shift-JIS) but `CSVHandler.load_csv()` defaults to UTF-8. To fix, specify the correct encoding via `CSVLoadOptions` if supported, or preprocess the file to UTF-8. Note: Aspose.Cells FOSS currently does not expose encoding options in `CSVLoadOptions`, so ensure input files are UTF-8 encoded before calling `CSVHandler.load_csv()`.

### `AutoFilter` Not Applied After Loading XLSX

Symptoms include missing `filter` controls or unfiltered data after loading an `.xlsx` file. This happens when `AutoFilterXMLLoader.load_auto_filter()` fails silently due to malformed XML in the source file. Verify the XLSX’s `xl/autofilters/autofilter*.xml` is well-formed. If the file was `created` externally, ensure it conforms to ECMA-376. Use `AutoFilter.range`, `filter_columns`, and sort_state to inspect loaded state after loading.

### Encrypted XLSX Files Cannot Be Read

Symptoms include `NotImplementedError: Standard encryption is not yet supported` when attempting to open an encrypted `.xlsx` file. Aspose.Cells FOSS only supports Agile encryption (ECMA-376 Part 2, Section 4) via `AgileEncryptionParameters`. Files encrypted with legacy XOR or standard ECMA-376 encryption are unsupported. Use `CFBReader.read_encryption_info()` only if the file uses Agile encryption; otherwise, decrypt externally before loading.

### `Cell` Values Not Parsing Correctly from XML

Symptoms include incorrect date values, numeric strings misinterpreted as numbers, or `error` values (e.g., #N/A) not recognized. This occurs when `CellValueHandler.parse_value_from_xml()` is used with incorrect cell_type or missing shared_strings context. Ensure cell_type matches the ECMA-376 t attribute (e.g., 's' for shared string, 'n' for number), and provide a populated shared_strings list for string types. Use `CellValueHandler.get_cell_type()` to validate inferred types before parsing.

## Error Messages

Aspose.Cells FOSS raises specific `errors` during file I/O, encryption, and parsing operations. This section documents common `error` messages from classes like `CFBReader`, `CFBWriter`, and `AutoFilterXMLLoader`, along with their causes and fixes.

| Error | Cause | Fix |
|-------|-------|-----|
| `NotImplementedError: Standard encryption is not yet supported` | Attempting to read or write encrypted XLSX using non-Agile encryption (e.g., XOR, RC4). | Use `AgileEncryptionParameters` and ensure the file uses Agile encryption (ECMA-376 Part 2, Section 4). |
| `NotImplementedError: Only Agile encryption is currently supported` | Using `CFBWriter` or `CFBReader` with encryption parameters other than Agile. | Configure encryption via `AgileEncryptionParameters` before calling write() or read_encrypted_package(). |
| `NotImplementedError: Unsupported chart type for creation` | Creating a chart of type not in `ChartType.LINE`, BAR, PIE, AREA, or STOCK. | Limit chart creation to supported types: LINE, BAR, PIE, AREA, STOCK. |
| `NotImplementedError: Only line, bar, pie, area and stock charts are currently supported` | Saving unsupported chart types (e.g., WATERFALL, BOX_WHISKER) to XML. | Use only supported `ChartType` values when saving `charts` via xml_chart_saver. |
| `ValueError: Invalid CSV content` | Malformed CSV data passed to `CSVHandler.load_csv_from_string()` or load_csv(). | Validate CSV syntax and ensure encoding matches `CSVLoadOptions` settings before loading. |
| `ValueError: Cell value type mismatch` | Passing an incompatible type to `CellValueHandler.format_value_for_xml()` or parse_value_from_xml(). | Use `CellValueHandler.get_cell_type()` to determine the correct `cell` type before formatting or parsing. |

## Getting Help

For Aspose.Cells FOSS, report issues or request features via GitHub Issues. Review the documentation for classes like `AutoFilter`, `Cell`, `CSVHandler`, and `AgileEncryptionParameters`. Engage the community on GitHub Discussions for general questions about using the library in Python workflows.

- GitHub Issues: https://github.com/aspose-cells/Aspose.Cells-for-Python-via-.NET/issues
- GitHub Discussions: https://github.com/aspose-cells/Aspose.Cells-for-Python-via-.NET/discussions
- API Reference: 

## See Also

For related guidance on handling common issues in Aspose.Cells FOSS, review the documentation for `core` classes such as `Cell`, `AutoFilter`, `CSVHandler`, and `AgileEncryptionParameters`.

- [API reference for error codes](/reference.aspose.org/cells/python/api-overview/)
- [Fix conditional formatting issues](/blog.aspose.org/cells/python/introducing-cells-foss-python/)
- [Debug conditional formatting rules](/blog.aspose.org/cells/python/testcreateallcharts-spreadsheets/)
- [Formula troubleshooting guide](/docs.aspose.org/cells/python/developer-guide/formula-calculation/)
- [Common spreadsheet operation errors](/docs.aspose.org/cells/python/developer-guide/spreadsheet-operations/)
