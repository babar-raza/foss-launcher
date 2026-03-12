---
page_role: howto_article
title: Working with Cells
slug: spreadsheet-operations
description: >-
  Read and write cell values, create formula cells, and use the Cell constructor
  in Python using Aspose.Cells FOSS â€” with int, float, string, and formula support.
type: docs
weight: 20
---

## Overview

Every worksheet exposes a `cells` collection that maps Excel-style address strings
(such as `"A1"`, `"B3"`) to `Cell` objects. You access a cell directly by subscript:

```python
from aspose_cells import Workbook, Cell

workbook = Workbook()
ws = workbook.worksheets[0]

##Access a cell by address
cell = ws.cells["A1"]
```

Values, formulas, and style information all live on the `Cell` object. You can
either mutate a cell in place by writing to its `.value` or `.formula` property,
or replace the cell entirely by assigning a new `Cell` instance to the address.

---

## Reading and Writing Values

Assign to `cell.value` to write a string, integer, or float. Read the same
property back to retrieve whatever was stored.

```python
from aspose_cells import Workbook

workbook = Workbook()
ws = workbook.worksheets[0]

##Write a string
ws.cells["A1"].value = "Hello, world"

##Write an integer
ws.cells["A2"].value = 42

##Write a float
ws.cells["A3"].value = 3.14159

##Read values back
print(ws.cells["A1"].value)   # Hello, world
print(ws.cells["A2"].value)   # 42
print(ws.cells["A3"].value)   # 3.14159

workbook.save("values_demo.xlsx")
```

The `.value` property accepts any Python scalar. The library stores the
Python type as-is; no implicit conversion occurs at write time.

---

## Using the Cell Constructor

The `Cell` constructor lets you create a cell with a value (and optionally a
formula) in a single expression. Assign the resulting `Cell` object to the
address subscript to place it in the sheet.

```python
from aspose_cells import Workbook, Cell

workbook = Workbook()
ws = workbook.worksheets[0]

##Integer cell
ws.cells["A1"] = Cell(42)

##String cell
ws.cells["A2"] = Cell("Revenue")

##Float cell
ws.cells["A3"] = Cell(3.14)

##Explicitly empty cell (no value, no formula)
ws.cells["A4"] = Cell(None)

workbook.save("cell_constructor_demo.xlsx")
```

The first positional argument to `Cell` is the value. When you pass `None` the
cell is stored with no value, which is useful when you intend to set a formula
separately or want an explicitly blank cell rather than an absent one.

---

## Formula Cells

A formula cell stores an Excel-compatible expression string alongside (or instead
of) a static value. There are two ways to create one.

**Via the Cell constructor** â€” pass `None` as the value and the formula string
as the second argument:

```python
from aspose_cells import Workbook, Cell

workbook = Workbook()
ws = workbook.worksheets[0]

ws.cells["A1"] = Cell(10)
ws.cells["A2"] = Cell(20)
ws.cells["A3"] = Cell(30)

##Formula via constructor: value=None, formula="=SUM(A1:A3)"
ws.cells["A4"] = Cell(None, "=SUM(A1:A3)")

workbook.save("formula_constructor.xlsx")
```

**Via the `.formula` property** â€” set the property on an existing cell:

```python
from aspose_cells import Workbook, Cell

workbook = Workbook()
ws = workbook.worksheets[0]

for i, v in enumerate([5, 10, 15, 20, 25], start=1):
    ws.cells[f"A{i}"].value = v

ws.cells["B1"].formula = "=AVERAGE(A1:A5)"

workbook.save("formula_property.xlsx")
```

### Common Formulas Quick Reference

| Purpose | Formula string |
|---|---|
| Sum a range | `=SUM(A1:A10)` |
| Average of a range | `=AVERAGE(A1:A10)` |
| Maximum value | `=MAX(A1:A10)` |
| Minimum value | `=MIN(A1:A10)` |
| Count non-empty | `=COUNT(A1:A10)` |
| Conditional value | `=IF(A1>0,"Positive","Non-positive")` |
| Lookup a value | `=VLOOKUP(D1,A1:B10,2,FALSE)` |
| Concatenate strings | `=CONCATENATE(A1," ",B1)` |

Formula strings must start with `=`. The library stores them verbatim; Excel
(or a compatible reader) evaluates the expression when the file is opened.

---

## Iterating Over Data

Use a standard Python loop to populate a column or row from a list:

```python
from aspose_cells import Workbook

workbook = Workbook()
ws = workbook.worksheets[0]

monthly_sales = [12_500, 14_200, 9_800, 17_600, 21_100, 18_400]

##Write a header
ws.cells["A1"].value = "Monthly Sales"

##Write data starting at row 2 (index 1 â†’ address A2)
for i, val in enumerate(monthly_sales, start=2):
    ws.cells[f"A{i}"].value = val

##Write a SUM formula below the data
last_row = 1 + len(monthly_sales)  # row index of last data cell
ws.cells[f"A{last_row + 1}"].formula = f"=SUM(A2:A{last_row})"

workbook.save("monthly_sales.xlsx")
```

The `enumerate(iterable, start=N)` pattern maps cleanly onto Excel row numbers
because Excel rows are 1-based. Starting at `start=2` reserves row 1 for a
header.

---

## Mixed Value Types

The following complete example builds a small dataset with a text header row,
three data rows containing integers, floats, and strings, and a formula row
that summarises the numeric columns.

```python
from aspose_cells import Workbook, Cell

workbook = Workbook()
ws = workbook.worksheets[0]

##--- Header row ---
ws.cells["A1"].value = "Product"
ws.cells["B1"].value = "Units Sold"
ws.cells["C1"].value = "Unit Price"
ws.cells["D1"].value = "Revenue"

##--- Data rows ---
##Row 2
ws.cells["A2"] = Cell("Widget A")
ws.cells["B2"] = Cell(120)
ws.cells["C2"] = Cell(9.99)
ws.cells["D2"] = Cell(None, "=B2*C2")

##Row 3
ws.cells["A3"] = Cell("Widget B")
ws.cells["B3"] = Cell(85)
ws.cells["C3"] = Cell(14.50)
ws.cells["D3"] = Cell(None, "=B3*C3")

##Row 4
ws.cells["A4"] = Cell("Widget C")
ws.cells["B4"] = Cell(200)
ws.cells["C4"] = Cell(4.75)
ws.cells["D4"] = Cell(None, "=B4*C4")

##--- Summary row ---
ws.cells["A5"].value = "TOTAL"
ws.cells["B5"] = Cell(None, "=SUM(B2:B4)")
ws.cells["D5"] = Cell(None, "=SUM(D2:D4)")

workbook.save("mixed_types_dataset.xlsx")
print("Saved mixed_types_dataset.xlsx")
```

After opening the file in Excel (or any compatible spreadsheet application),
the `D` column and the `B5` / `D5` cells will display the evaluated results
of the formula expressions.

---

## Tips

**`None` value vs empty string**

`Cell(None)` and `ws.cells["A1"].value = None` create a cell with no stored
value â€” indistinguishable from a cell that was never written in most spreadsheet
readers. `Cell("")` or `ws.cells["A1"].value = ""` create a cell that explicitly
contains an empty string, which some readers and formulas treat differently
(for example, `=COUNT` ignores empty-string cells the same way it ignores blank
cells, but `=COUNTA` counts them).

**Formula string vs static value**

Reading `.value` from a formula cell returns `None` (or the last cached value if
one was set before the formula was assigned). Reading `.formula` returns the
expression string. If you need to distinguish between a formula cell and a
plain-value cell at runtime, check whether `ws.cells["A1"].formula` is non-empty:

```python
cell = ws.cells["A1"]
if cell.formula:
    print(f"Formula: {cell.formula}")
else:
    print(f"Value: {cell.value}")
```
---

## See Also

- [API Reference](https://reference.aspose.org/cells/python/) — Full class and method documentation for `aspose_cells`
- [Knowledge Base](https://kb.aspose.org/cells/python/) — Task-oriented how-to guides
- [Product Overview](https://products.aspose.org/cells/python/) — Features and capabilities summary
- [Getting Started / Installation](https://docs.aspose.org/cells/python/getting-started/installation/) — pip install and setup
- [Blog: Introducing Aspose.Cells FOSS](https://blog.aspose.org/cells/python/introducing-cells-foss-python/) — Library overview and quick start
