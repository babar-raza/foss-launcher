<!-- GOLDEN REFERENCE | Source: cells/en/Aspose.Cells.LowCode.SplitPartInfo.md | Original-Grade: B -->
---
linkTitle: "Class SplitPartInfo"
title: "Class SplitPartInfo"
description: "Represents the information of one input/output for multiple inputs/outputs, such as current page to be rendered when converting spreadsheet to image."
summary: "Represents the information of one input/output for multiple inputs/outputs, such as current page to be rendered when converting spreadsheet to image."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Cells.LowCode](/cells/aspose.cells.lowcode)
Assembly: Aspose.Cells.dll (26.2.0)

Represents the information of one input/output for multiple inputs/outputs,
such as current page to be rendered when converting spreadsheet to image.

```csharp
public class SplitPartInfo
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ←
[SplitPartInfo](/cells/aspose.cells.lowcode.splitpartinfo)

## Properties

### <a id="Aspose_Cells_LowCode_SplitPartInfo_PartIndex"></a> PartIndex

Index of current part in sequence(0 based).
-1 means there are no multiple parts so the result is single.

```csharp
public int PartIndex { get; }
```

#### Property Value

 [int](https://learn.microsoft.com/dotnet/api/system.int32)

#### Remarks

If multiple sheets need to be processed and every sheet is processed(split)
separately, the part index always starts from 0 for every sheet.
For example, when converting workbook to images,
it represents the output page index of currently processed sheet.
And -1 denotes there is only one page for current sheet.

### <a id="Aspose_Cells_LowCode_SplitPartInfo_SheetIndex"></a> SheetIndex

Index of the sheet where current part is in. -1 denotes there is only one sheet.

```csharp
public int SheetIndex { get; }
```

#### Property Value

 [int](https://learn.microsoft.com/dotnet/api/system.int32)

### <a id="Aspose_Cells_LowCode_SplitPartInfo_SheetName"></a> SheetName

Name of the sheet where current part is in.

```csharp
public string SheetName { get; }
```

#### Property Value

 [string](https://learn.microsoft.com/dotnet/api/system.string)

#### Remarks

May be null for some situations, such as when rendering the whole workbook to tiff image.
