---
page_role: howto_article
title: "How to Work with Tables in Python"
description: "Learn how to create, populate, and style tables in PowerPoint presentations using Python and Aspose.Slides FOSS."
date: 2026-03-11
weight: 40
draft: false
type: "topic"
keywords: ["python table pptx", "python add table powerpoint", "aspose slides table python", "python create table slide", "pptx table rows columns python"]
step1: "Install aspose-slides-foss from PyPI"
step2: "Create or open a Presentation"
step3: "Define column widths and row heights"
step4: "Add a Table with slide.shapes.add_table()"
step5: "Set cell text via table.rows[row][col].text_frame.text"
step6: "Save the presentation"
---

Aspose.Slides FOSS for Python supports creating tables on slides with configurable column widths and row heights. This guide shows how to add a table, populate it with data, and apply basic text formatting to cells.

## Step-by-Step Guide

{{% steps %}}

### Step 1: Install the Package

```bash
pip install aspose-slides-foss
```

---

### Step 2: Create or Open a Presentation

```python
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    slide = prs.slides[0]
    # ... add table ...
    prs.save("table.pptx", SaveFormat.PPTX)
```

---

### Step 3: Define Column Widths and Row Heights

Tables require explicit column widths and row heights in points (1 point = 1/72 inch). A standard slide is 720 points wide and 540 points tall.

```python
col_widths = [200.0, 150.0, 150.0]   # 3 columns: 200pt + 150pt + 150pt
row_heights = [45.0, 40.0, 40.0]     # 3 rows: 45pt header + 40pt data rows
```

---

### Step 4: Add the Table

`slide.shapes.add_table(x, y, col_widths, row_heights)` creates the table at position `(x, y)`:

```python
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    slide = prs.slides[0]

    col_widths = [200.0, 150.0, 150.0]
    row_heights = [45.0, 40.0, 40.0]
    table = slide.shapes.add_table(50, 100, col_widths, row_heights)

    prs.save("table.pptx", SaveFormat.PPTX)
```

---

### Step 5: Set Cell Text

Access cells via `table.rows[row_index][col_index]` and assign text through `.text_frame.text`:

```python
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    slide = prs.slides[0]

    col_widths = [200.0, 150.0, 150.0]
    row_heights = [45.0, 40.0, 40.0]
    table = slide.shapes.add_table(50, 100, col_widths, row_heights)

    # Header row (row 0)
    headers = ["Product", "Units Sold", "Revenue"]
    for col, header in enumerate(headers):
        table.rows[0][col].text_frame.text = header

    # Data rows
    data = [
        ["Widget A", "1,200", "$24,000"],
        ["Widget B", "850", "$17,000"],
    ]
    for row_idx, row_data in enumerate(data):
        for col, cell_text in enumerate(row_data):
            table.rows[row_idx + 1][col].text_frame.text = cell_text

    prs.save("sales-table.pptx", SaveFormat.PPTX)
```

---

### Step 6: Format Header Cell Text

Apply bold formatting to header cells using `PortionFormat`:

```python
from aspose.slides_foss import NullableBool, FillType
from aspose.slides_foss.drawing import Color

for col in range(len(headers)):
    cell = table.rows[0][col]
    portions = cell.text_frame.paragraphs[0].portions
    if portions:
        fmt = portions[0].portion_format
        fmt.font_bold = NullableBool.TRUE
        fmt.fill_format.fill_type = FillType.SOLID
        fmt.fill_format.solid_fill_color.color = Color.from_argb(255, 255, 255, 255)
```

{{% /steps %}}

---

## Complete Working Example

```python
import aspose.slides_foss as slides
from aspose.slides_foss import NullableBool, FillType
from aspose.slides_foss.drawing import Color
from aspose.slides_foss.export import SaveFormat

data_rows = [
    ["North", "$1.2M", "+8%"],
    ["South", "$0.9M", "+4%"],
    ["East",  "$1.5M", "+12%"],
    ["West",  "$0.7M", "+2%"],
]
headers = ["Region", "Revenue", "Growth"]

with slides.Presentation() as prs:
    slide = prs.slides[0]

    col_widths = [180.0, 140.0, 120.0]
    row_heights = [45.0] + [38.0] * len(data_rows)

    table = slide.shapes.add_table(60, 80, col_widths, row_heights)

    # Header row
    for col, text in enumerate(headers):
        cell = table.rows[0][col]
        cell.text_frame.text = text
        if cell.text_frame.paragraphs and cell.text_frame.paragraphs[0].portions:
            fmt = cell.text_frame.paragraphs[0].portions[0].portion_format
            fmt.font_bold = NullableBool.TRUE

    # Data rows
    for row_idx, row_data in enumerate(data_rows):
        for col, text in enumerate(row_data):
            table.rows[row_idx + 1][col].text_frame.text = text

    prs.save("regional-revenue.pptx", SaveFormat.PPTX)

print("Saved regional-revenue.pptx")
```

---

## Common Issues and Fixes

**`IndexError` when accessing `table.rows[row][col]`**

Row and column indices are zero-based. If you defined `row_heights` with 3 elements, valid row indices are 0, 1, 2.

**Cell text does not appear in the saved file**

Always assign through `.text_frame.text`, not through `.text` directly on the cell object:

```python
# Correct
table.rows[0][0].text_frame.text = "Header"

# Wrong — AttributeError or silent failure
table.rows[0][0].text = "Header"
```

**Table position is off the slide**

Check that `x + sum(col_widths) <= 720` and `y + sum(row_heights) <= 540` for a standard slide.

---

## Frequently Asked Questions

**Can I merge table cells?**

Cell merging is not supported in this edition.

**Can I apply a table-wide background color?**

Apply fill formatting to each individual cell:

```python
for row_idx in range(len(table.rows)):
    for col_idx in range(len(table.rows[row_idx])):
        cell = table.rows[row_idx][col_idx]
        cell.fill_format.fill_type = FillType.SOLID
        cell.fill_format.solid_fill_color.color = Color.from_argb(255, 240, 248, 255)
```

**Can I set cell border styles?**

Cell border properties are accessible through `table.rows[row][col].border_*` properties. Refer to the API reference for the full list of border format attributes.

---

## See Also

- [How to Add Shapes in Python](/kb.aspose.org/slides/python/how-to-add-shapes-python/)
- [How to Create Presentations in Python](/kb.aspose.org/slides/python/how-to-create-presentations-python/)
- [Features Overview](/docs.aspose.org/slides/python/developer-guide/features/)
- [API Reference](/reference.aspose.org/slides/python/)
