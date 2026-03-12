---
canonical: https://kb.aspose.org/cells/python/faq/
canonical_import: aspose_cells_foss
date: '2026-03-11T21:00:43Z'
dateModified: '2026-03-11T21:00:43Z'
datePublished: '2026-03-11T21:00:43Z'
description: This license also permits integration into proprietary applications,
  provided the original copyright notice and permission notice are included in all
  copies...
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
lastmod: '2026-03-11T21:00:43Z'
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

### [identifier omitted] is the license for Aspose.Cells FOSS?

Aspose.Cells FOSS is distributed under the MIT [identifier omitted], a permissive open-source license that allows you to use, modify, and distribute the software for both commercial and non-commercial purposes without restriction. This license also permits integration into proprietary applications, provided the original copyright notice and permission notice are included in all copies or substantial portions of the software. You can verify the license by checking the [identifier omitted].md file in the repository, which includes a badge linking to the official MIT [identifier omitted] text.

### [identifier omitted] encryption methods does Aspose.Cells FOSS support?

Aspose.Cells FOSS currently supports only Agile encryption for XLSX files; standard encryption is not yet implemented. This means when encrypting or decrypting files, the library expects and produces files using the Agile encryption schema defined in [identifier omitted]-376. [identifier omitted] to use other encryption types will raise a NotImplementedError with the message '[identifier omitted] Agile encryption is currently supported'. If your workflow requires compatibility with legacy or non-Agile encryption, you must handle conversion externally before using this library.

### How do I encrypt an XLSX file using Aspose.Cells FOSS?

To encrypt an XLSX file, you must configure `AgileEncryptionParameters`, apply them to the workbook, and then save the file. The library uses the CFB format internally for encrypted packages, and only supports Agile encryption as per the [identifier omitted]-376 standard. [identifier omitted] is a minimal working example that demonstrates how to set up encryption and write the protected file.

```python
import aspose.cells
from aspose.cells import AgileEncryptionParameters

# Create a new workbook
workbook = aspose.cells.Workbook()
worksheet = workbook.worksheets[0]
worksheet.cells.get("A1").value = "Encrypted content"

# Configure Agile encryption
params = AgileEncryptionParameters()
params.password = "secret123"
params.algorithm = "AES"
params.key_size = 128

# Apply encryption and save
workbook.save("encrypted.xlsx", params)
```

### [identifier omitted] chart types can be saved to XML format?

Aspose.Cells FOSS supports saving only line, bar, pie, area, and stock charts to XML format. [identifier omitted] chart types such as waterfall, scatter, or combo charts will raise a NotImplementedError during save operations if they are not in the supported list. This limitation applies specifically to XML-based chart serialization, not to in-memory chart creation or rendering. If your use case involves exporting charts for external consumption, ensure you restrict your chart types to the supported set.

### Is Aspose.Cells FOSS compatible with openpyxl or pandas?

Aspose.Cells FOSS is a standalone library and does not depend on openpyxl or pandas, nor does it directly interoperate with them. While both openpyxl and Aspose.Cells FOSS can read and write XLSX files, they use different internal models and [identifier omitted]. You cannot pass an openpyxl workbook into Aspose.Cells FOSS or vice versa. If you need to migrate from openpyxl to Aspose.Cells FOSS, you must rewrite your file-handling logic using the Aspose.Cells FOSS API surface. [identifier omitted], pandas integration requires exporting to CSV or XLSX first, then loading with Aspose.Cells FOSS.

## See Also

Aspose.Cells FOSS supports a subset of Excel features with clear limitations. Standard encryption is not yet supported in the library, and only Agile encryption is currently supported. For charting, only line, bar, pie, area and stock charts are currently supported for saving in XML format; other chart types raise NotImplementedError during XML export.

- [Common troubleshooting tips](/kb.aspose.org/cells/python/troubleshooting/)
- [Convert file formats step by step](/kb.aspose.org/cells/python/how-to-convert-csv-to-json-python/)
- [Fix common errors quickly](/kb.aspose.org/cells/python/how-to-fix-spreadsheets-errors-python/)
- [Load files efficiently](/kb.aspose.org/cells/python/how-to-load-spreadsheets-python/)
- [Optimize performance best practices](/kb.aspose.org/cells/python/how-to-optimize-spreadsheets-python/)
