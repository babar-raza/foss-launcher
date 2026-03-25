---
title: "Workbook Operations"
slug: "workbook-operations"
url: "/cells/python/workbook-operations/"
page_role: "developer-guide"
---

## Overview

The `Workbook` class provides methods for creating and managing spreadsheet files.
Use `add_worksheet` to create a new worksheet, and `save` to persist changes.

## Creating a Workbook

Create a new workbook instance and add worksheets as needed.

```python
from cells import Workbook

wb = Workbook()
ws = wb.add_worksheet("Sheet1")
ws.set_cell_value("A1", "Hello")
wb.save("output.xlsx")
```

## Saving Formats

Aspose.Cells supports multiple output formats including XLSX, CSV, and JSON.
Use the appropriate save method for each format.

```python
wb.save("output.csv", save_format="csv")
wb.save("output.json", save_format="json")
```

## See Also

- [Worksheet Operations](/cells/python/worksheet-operations/)
- [Formula Calculation](/cells/python/formula-calculation/)
