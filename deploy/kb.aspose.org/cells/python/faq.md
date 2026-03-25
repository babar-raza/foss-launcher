---
canonical: https://kb.aspose.org/cells/python/faq/
canonical_import: aspose.cells
date: '2026-03-23T13:16:22Z'
dateModified: '2026-03-23T13:16:22Z'
datePublished: '2026-03-23T13:16:22Z'
description: Attempting to create or `save` other chart types such as scatter, combo,
  waterfall, or treemap will raise a NotImplementedError with the message 'Only line,...
display_name: Aspose.Cells FOSS
family: cells
keywords:
- cells python
- python cells in excel
- python cells vscode
- cell python docx
- cell python spyder
- aspose cells python
- code cells python
- voronoi cells python
lastmod: '2026-03-23T13:16:22Z'
page_role: faq
platform: python
reading_time: 1
robots: index, follow
seoTitle: Aspose.Cells FOSS FAQ | Guide
slug: faq
title: Aspose.Cells FOSS FAQ
type: faq
url: /kb.aspose.org/cells/python/faq/
weight: 8
---

## Frequently Asked Questions

### What chart types can I create and `save` with Aspose.Cells FOSS?

Aspose.Cells FOSS currently supports only line, bar, pie, area, and stock chart types for creation and saving. Attempting to create or `save` other chart types such as scatter, combo, waterfall, or treemap will raise a NotImplementedError with the message 'Only line, bar, pie, area and stock `charts` are currently supported'. This limitation applies to both new chart creation and saving existing workbooks containing unsupported chart types. Developers should verify their chart requirements align with these supported types before integrating the library into production workflows.

### Which encryption methods does Aspose.Cells FOSS support?

Aspose.Cells FOSS only supports Agile encryption (ECMA-376 Part 2, Section 4) for protecting Excel workbooks. Standard encryption methods are not implemented and will raise a NotImplementedError if attempted. When saving a protected workbook, you must use the `AgileEncryptionParameters` class to configure encryption settings. This restriction ensures compatibility with modern Excel versions while limiting the library's scope to a single, well-defined encryption standard.

### What is the license for Aspose.Cells FOSS?

Aspose.Cells FOSS is distributed under the MIT License, a permissive open-source license that allows free use, modification, and distribution of the software for both personal and commercial purposes. The license requires only that the original copyright notice and permission notice be included in all copies or substantial portions of the software. This licensing model supports integration into proprietary applications without requiring source code disclosure.

### How do I create a supported chart in a workbook?

```python
import aspose.cells

# Create a new workbook and access the first worksheet
workbook = aspose.cells.Workbook()
worksheet = workbook.worksheets[0]

# Add sample data for the chart
cells = worksheet.cells
cells["A1"].value = "Category"
cells["B1"].value = "Value"
cells["A2"].value = "A"
cells["B2"].value = 10
cells["A3"].value = "B"
cells["B3"].value = 20
cells["A4"].value = "C"
cells["B4"].value = 30

# Add a line chart to the worksheet
chart_collection = worksheet.charts
chart_index = chart_collection.add_line(5, 0, 20, 8)
chart = chart_collection[chart_index]

# Save the workbook
workbook.save("output.xlsx")
```

## See Also

Aspose.Cells FOSS supports Agile encryption for Excel files, but standard encryption is not yet implemented. When saving encrypted workbooks, use `AgileEncryptionParameters` to configure encryption settings. This limitation is enforced by the `xlsx_encryptor.py` module, which raises NotImplementedError for non-Agile encryption attempts.

- [Troubleshooting common issues](/kb.aspose.org/cells/python/troubleshooting/)
- [Convert file formats step-by-step](/kb.aspose.org/cells/python/how-to-convert-csv-to-json-python/)
- [Fix common errors effectively](/kb.aspose.org/cells/python/how-to-fix-spreadsheets-errors-python/)
- [Load files correctly and efficiently](/kb.aspose.org/cells/python/how-to-load-spreadsheets-python/)
- [Optimize performance tips](/kb.aspose.org/cells/python/how-to-optimize-spreadsheets-python/)
