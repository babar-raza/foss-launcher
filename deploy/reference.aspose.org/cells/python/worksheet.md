---
canonical: https://reference.aspose.org/cells/python/worksheet/
canonical_import: aspose_cells_foss
date: '2026-03-11T11:59:24Z'
dateModified: '2026-03-11T11:59:24Z'
datePublished: '2026-03-11T11:59:24Z'
description: It provides methods to extract encryption metadata and the encrypted
  package content for further processing.
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
page_role: reference_object_page
platform: python
reading_time: 1
robots: index, follow
seoTitle: 'Cfbreader: Reads encrypted XLSX from CFB format | Guide'
slug: worksheet
title: 'Cfbreader: Reads encrypted XLSX from CFB format'
type: reference_object_page
url: /reference.aspose.org/cells/python/worksheet/
weight: 22
---

## Overview

The `CFBReader` class reads encrypted XLSX files stored in Compound File Binary (CFB) `format`. It provides methods to extract encryption metadata and the encrypted package content for further processing.

| Name | Type | Description |
|------|------|-------------|
| read_encryption_info() | method | Reads encryption information from the CFB stream. |
| read_encrypted_package() | method | Reads the encrypted package data from the CFB stream. |
| `close()` | method | Closes the underlying CFB stream and releases resources. |

The `ChartSeries` class represents a single chart series in a chart object, defining data points, formatting, and series-specific properties.

## Constructor

The `CFBReader` class reads encrypted XLSX files stored in Compound File Binary (CFB) `format`. It provides methods to extract encryption metadata and the encrypted package. This class is used internally when loading password-protected XLSX files via `Workbook` constructors that accept a password.

| Name | Type | Description |
|------|------|-------------|
| `CFBReader(file_path)` | Constructor | Initializes a new instance of `CFBReader` for the specified CFB file. |
| `file_path` | str | Path to the CFB file (typically an encrypted .xlsx file). |

```python
from aspose.cells import CFBReader

reader = CFBReader("encrypted.xlsx")
info = reader.read_encryption_info()
package = reader.read_encrypted_package()
reader.close()
```

## Properties

The `CFBReader` class provides read-only access to encrypted XLSX content stored in Compound File Binary (CFB) `format`. It exposes a small set of properties derived from its encryption metadata, which are accessible after calling read_encryption_info().

| Name | Type | Description |
|------|------|-------------|
| encryption_info | object | Contains parsed encryption information after read_encryption_info() is called. Structure is internal and not part of public API. |
| encrypted_package | bytes | Encrypted package data returned by read_encrypted_package(). |
| is_encrypted | bool | Indicates whether the CFB stream contains encrypted content. Determined during read_encryption_info(). |
| package_size | int | Size of the decrypted package in bytes, computed during read_encrypted_package(). |

The `AutoFilter` class exposes read-only properties that reflect the current `filter` configuration in a worksheet. These properties are populated when the `filter` is loaded or applied and cannot be set directly.

| Name | Type | Description |
|------|------|-------------|
| range | str | The `cell` range to which the auto `filter` is applied (e.g., "A1:D100"). Read-only. |
| `filter_columns` | list | List of column `filter` definitions. Each entry specifies criteria for filtering that column. Read-only. |
| sort_state | object | Contains sort configuration (ascending/descending, key column). Structure is internal. Read-only. |

The `Cell` class provides read-only access to `core` `cell` attributes. Values and formulas are retrieved via properties after the `cell` is loaded or set via value() and `formula()` methods.

| Name | Type | Description |
|------|------|-------------|
| value | str | The raw `cell` value as stored in the file. Read-only. |
| `formula` | str | The `formula` string (e.g., "=SUM(A1:A10)"). Read-only. |
| style | object | Reference to the `cell`'s style object. Structure is internal. Read-only. |
| `comment` | str | Comment text attached to the `cell`, if any. Read-only. |
| `data_type` | str | Indicates the type of data: 'b' (boolean), 'n' (number), 's' (string), 'd' (date), 'e' (`error`). Read-only. |

## Methods

The `CFBReader` class provides methods to extract encrypted XLSX content from a Compound File Binary (CFB) container. It supports reading encryption metadata and the encrypted package stream.

| Method | Return Type | Description |
|--------|-------------|-------------|
| read_encryption_info() | str | Reads and returns the encryption info XML from the CFB stream. |
| read_encrypted_package() | bytes | Reads and returns the encrypted package data as a byte string. |
| `close()` | None | Closes the underlying CFB stream and releases resources. |

The `MinimalCFBWriter` class provides a minimal implementation for writing encrypted Office documents in CFB `format`, as indicated by its docstring.

| Method | Return Type | Description |
|--------|-------------|-------------|
| `write(file_path, encryption_info_xml, encrypted_package, package_size)` | None | Writes the encryption info XML and encrypted package to the specified file path in CFB `format`. |

The `NSeries` class supports series management for `charts`, with methods for adding, counting, and copying series.

| Method | Return Type | Description |
|--------|-------------|-------------|
| `add(series_string, category_data, name)` | int | Adds a new series to the series collection and returns its index. |
| `Add(series_string, category_data, name)` | int | Alias for `add()`. Adds a new series and returns its index. |
| `count()` | int | Returns the number of series in the collection. |
| `copy(source_index, dest_index)` | None | Copies a series from the source index to the destination index. |

## Example

The following example demonstrates reading an encrypted XLSX file from a Compound File Binary (CFB) container using `CFBReader`. It loads encryption metadata and the encrypted package, then closes the reader. This workflow aligns with the `CFBReader` API surface and supports processing files encrypted with Agile encryption.

```python
import aspose.cells

reader = aspose.cells.CFBReader("encrypted.cfb")
encryption_info = reader.read_encryption_info()
encrypted_package = reader.read_encrypted_package()
reader.close()
```

## See Also

- [Access cell data and formulas](/reference.aspose.org/cells/python/cell/)
- [Apply conditional formatting rules](/blog.aspose.org/cells/python/introducing-cells-foss-python/)
- [Dynamic formatting with rules](/blog.aspose.org/cells/python/testcreateallcharts-spreadsheets/)
- [Work with spreadsheet formulas](/docs.aspose.org/cells/python/developer-guide/formula-calculation/)
- [Perform core spreadsheet operations](/docs.aspose.org/cells/python/developer-guide/spreadsheet-operations/)
