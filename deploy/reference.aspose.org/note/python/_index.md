---
page_role: howto_article
linkTitle: "aspose.note"
title: "Aspose.Note FOSS for Python — API Reference"
description: "Complete API reference for the aspose.note Python package (v26.2). Lists all public classes, methods, properties, enumerations, and exceptions."
summary: "Public API reference for aspose-note v26.2"
categories:
  - Reference
layout: "reference-home"
---

This reference covers the complete public API surface of `aspose-note` version 26.2. Only symbols exported from the `aspose.note` package are documented here. Anything under `aspose.note._internal` is an implementation detail and may change without notice.

**Install**: `pip install aspose-note` (core) or `pip install "aspose-note[pdf]"` (with PDF export)

**Import**: `from aspose.note import Document, RichText, ...`

---

## Classes

### Document and Traversal

| Class | Description |
|---|---|
| [`Document`](#document) | Root document object. Load a `.one` file, iterate pages, and save to PDF. |
| [`DocumentVisitor`](#documentvisitor) | Abstract base for visitor-pattern traversal of the document tree. |
| [`Node`](#node) | Base class for all document nodes. |
| [`CompositeNode`](#compositenode) | Base class for nodes that can contain child nodes. |

### Document Structure

| Class | Description |
|---|---|
| [`Page`](#page) | Represents a OneNote page. |
| [`Title`](#title) | Page title block containing TitleText, TitleDate, TitleTime. |
| [`Outline`](#outline) | Positional container for OutlineElement nodes. |
| [`OutlineElement`](#outlineelement) | Leaf container; holds RichText, Image, Table, AttachedFile. |

### Content

| Class | Description |
|---|---|
| [`RichText`](#richtext) | Text block with formatting runs, tags, and hyperlinks. |
| [`TextRun`](#textrun) | Single formatted text segment within a RichText. |
| [`TextStyle`](#textstyle) | Formatting properties for a TextRun. |
| [`Image`](#image) | Embedded image with raw bytes and metadata. |
| [`AttachedFile`](#attachedfile) | Embedded file attachment with raw bytes. |
| [`Table`](#table) | Table with rows, cells, and column widths. |
| [`TableRow`](#tablerow) | A row within a Table. |
| [`TableCell`](#tablecell) | A cell within a TableRow; contains content nodes. |
| [`NoteTag`](#notetag) | OneNote tag (star, checkbox, etc.) attached to a content node. |
| [`NumberList`](#numberlist) | Numbered list metadata on an OutlineElement. |

### Options

| Class | Description |
|---|---|
| [`LoadOptions`](#loadoptions) | Options for loading a `.one` file. |
| [`SaveOptions`](#saveoptions) | Base class for save options. |
| [`PdfSaveOptions`](#pdfsaveoptions) | PDF-specific save options (tag icons). |
| [`OneSaveOptions`](#onehtmlimagesaveoptions) | Declared for API compatibility; not implemented. |
| [`HtmlSaveOptions`](#onehtmlimagesaveoptions) | Declared for API compatibility; not implemented. |
| [`ImageSaveOptions`](#onehtmlimagesaveoptions) | Declared for API compatibility; not implemented. |

### Compatibility Stubs

| Class | Description |
|---|---|
| [`License`](#license-and-metered) | Compatibility stub — `SetLicense()` is a no-op in this FOSS implementation. |
| [`Metered`](#license-and-metered) | Compatibility stub — `SetMeteredKey()` is a no-op in this FOSS implementation. |

---

## Class Details

### Document

The root document class. Load a `.one` file from a file path, a `pathlib.Path`, or a binary stream.

```python
from aspose.note import Document, LoadOptions

doc = Document(source=None, load_options=None)
```

**Constructor parameters**:

| Parameter | Type | Description |
|---|---|---|
| `source` | `str \| Path \| BinaryIO \| None` | File path string, `pathlib.Path`, binary stream, or `None` for an empty document |
| `load_options` | `LoadOptions \| None` | Optional load-time configuration |

**Properties**:

| Property | Type | Description |
|---|---|---|
| `DisplayName` | `str \| None` | Section display name from the file metadata |
| `CreationTime` | `datetime \| None` | Field exists; not populated from the parser in v26.2 (always `None`) |
| `FileFormat` | `FileFormat` | **Always returns `FileFormat.OneNote2010`** — hardcoded constant in v26.2, not a detected value |

**Methods**:

| Method | Signature | Description |
|---|---|---|
| `Count()` | `() -> int` | Number of direct child pages |
| `GetPageHistory(page)` | `(Page) -> list[Page]` | Returns `[page]` (stub; full history not yet implemented) |
| `DetectLayoutChanges()` | `() -> None` | Compatibility stub; no operation |
| `Save(target, format_or_options)` | `(str \| Path \| BinaryIO, SaveFormat \| SaveOptions \| None) -> None` | Save to file or stream. Only `SaveFormat.Pdf` is implemented |
| `Accept(visitor)` | `(DocumentVisitor) -> None` | Invoke visitor traversal |
| `for page in doc` | — | Iterate direct child `Page` nodes |

> **`Document.FileFormat` note**: The property always returns `FileFormat.OneNote2010` regardless of the actual file. The `FileFormat` enum has three values (`OneNote2010`, `OneNoteOnline`, `OneNote2007`) but format detection is not yet implemented.

> **`Document.Save()` stream support**: `target` can be a binary stream (`io.BytesIO`, file handle opened in binary write mode, etc.). This is confirmed by the test suite: `doc.Save(io.BytesIO(), PdfSaveOptions(SaveFormat.Pdf))`.

---

### DocumentVisitor

Abstract base class for visitor-pattern traversal. Override the visit methods you need:

| Method | Called when |
|---|---|
| `VisitDocumentStart(doc)` | Entering a Document node |
| `VisitDocumentEnd(doc)` | Leaving a Document node |
| `VisitPageStart(page)` | Entering a Page node |
| `VisitPageEnd(page)` | Leaving a Page node |
| `VisitTitleStart(title)` | Entering a Title node |
| `VisitTitleEnd(title)` | Leaving a Title node |
| `VisitOutlineStart(outline)` | Entering an Outline node |
| `VisitOutlineEnd(outline)` | Leaving an Outline node |
| `VisitOutlineElementStart(oe)` | Entering an OutlineElement node |
| `VisitOutlineElementEnd(oe)` | Leaving an OutlineElement node |
| `VisitRichTextStart(rt)` | Entering a RichText node |
| `VisitRichTextEnd(rt)` | Leaving a RichText node |
| `VisitImageStart(img)` | Entering an Image node |
| `VisitImageEnd(img)` | Leaving an Image node |

---

### Node

Base class for all document tree nodes.

| Property / Method | Type | Description |
|---|---|---|
| `ParentNode` | `Node \| None` | Parent in the document tree (`None` for the root Document) |
| `Document` | `Document \| None` | Walk up to the root Document; returns `None` if this node is not attached to a Document |
| `Accept(visitor)` | `(DocumentVisitor) -> None` | Dispatch visitor for this node |

---

### CompositeNode

Extends `Node`. Adds child management:

| Property / Method | Description |
|---|---|
| `FirstChild` | First child node, or `None` |
| `LastChild` | Last child node, or `None` |
| `AppendChildLast(node)` | Add a child node at the end; sets `node.ParentNode = self` |
| `AppendChildFirst(node)` | Add a child node at the start |
| `InsertChild(index, node)` | Insert a child at the given position |
| `RemoveChild(node)` | Remove a child node; sets `node.ParentNode = None` |
| `GetEnumerator()` | Returns an iterator over direct children |
| `for child in node` | Iterate direct children |
| `GetChildNodes(Type)` | `(Type) -> list[Type]` — recursive, depth-first search of the entire subtree including `self` |

---

### Page

Extends `CompositeNode`. Represents a OneNote page.

| Property | Type | Description |
|---|---|---|
| `Title` | `Title \| None` | Page title block |
| `Author` | `str \| None` | Author string |
| `CreationTime` | `datetime \| None` | Page creation timestamp |
| `LastModifiedTime` | `datetime \| None` | Last modification timestamp |
| `Level` | `int \| None` | Sub-page indent level (0 = top-level) |

**Methods**:

| Method | Description |
|---|---|
| `Clone(deep=False)` | Return a shallow or deep clone of the page |

---

### Title

Extends `CompositeNode`. Holds the title block of a `Page`.

| Property | Type | Description |
|---|---|---|
| `TitleText` | `RichText \| None` | Main title text |
| `TitleDate` | `RichText \| None` | Date portion of the title |
| `TitleTime` | `RichText \| None` | Time portion of the title |

---

### Outline

Extends `CompositeNode`. A positional container for `OutlineElement` nodes.

| Property | Type | Description |
|---|---|---|
| `X` | `float \| None` | Horizontal position on the page |
| `Y` | `float \| None` | Vertical position on the page |
| `Width` | `float \| None` | Width in points |

---

### OutlineElement

Extends `CompositeNode`. A leaf container that holds content nodes.

| Property | Type | Description |
|---|---|---|
| `IndentLevel` | `int` | Nesting depth (0 = outermost) |
| `NumberList` | `NumberList \| None` | Numbered list metadata, or `None` |
| `Tags` | `list[NoteTag]` | OneNote tags attached to this element |

---

### RichText

Extends `CompositeNode`. A block of styled text.

| Property | Type | Description |
|---|---|---|
| `Text` | `str` | Full plain-text string (all runs concatenated) |
| `Runs` | `list[TextRun]` | Ordered list of formatted segments |
| `FontSize` | `float \| None` | Paragraph-level font size in points |
| `Tags` | `list[NoteTag]` | OneNote tags attached to this block |

**Methods**:

| Method | Signature | Description |
|---|---|---|
| `Append(text, style=None)` | `(str, TextStyle \| None) -> RichText` | Append text in-memory; if `style` is given, also appends a `TextRun` to `Runs` |
| `Replace(old_value, new_value)` | `(str, str) -> None` | In-memory string substitution on `Text`; does not update `Runs` |

---

### TextRun

Extends `Node`. A single formatted text segment.

| Property | Type | Description |
|---|---|---|
| `Text` | `str` | The segment's text content (default `""`) |
| `Style` | `TextStyle` | Formatting properties |
| `Start` | `int \| None` | Character offset of the segment start within `RichText.Text` |
| `End` | `int \| None` | Character offset of the segment end |

---

### TextStyle

Extends `Node`. Per-character formatting properties for a `TextRun`.

| Property | Type | Default | Description |
|---|---|---|---|
| `Bold` | `bool` | `False` | Bold |
| `Italic` | `bool` | `False` | Italic |
| `Underline` | `bool` | `False` | Underline |
| `Strikethrough` | `bool` | `False` | Strikethrough |
| `Superscript` | `bool` | `False` | Superscript |
| `Subscript` | `bool` | `False` | Subscript |
| `FontName` | `str \| None` | `None` | Font family name |
| `FontSize` | `float \| None` | `None` | Font size in points |
| `FontColor` | `int \| None` | `None` | Font color as ARGB integer |
| `HighlightColor` | `int \| None` | `None` | Background highlight color as ARGB integer |
| `LanguageId` | `int \| None` | `None` | Language identifier (LCID) |
| `IsHyperlink` | `bool` | `False` | Whether this run is a hyperlink |
| `HyperlinkAddress` | `str \| None` | `None` | Hyperlink URL (when `IsHyperlink` is True) |

---

### Image

Extends `CompositeNode`. An embedded image.

| Property | Type | Description |
|---|---|---|
| `FileName` | `str \| None` | Original filename of the image |
| `Bytes` | `bytes` | Raw image data (default `b""`) |
| `Width` | `float \| None` | Image width in points |
| `Height` | `float \| None` | Image height in points |
| `AlternativeTextTitle` | `str \| None` | Alt text title field (always `None` for files parsed in v26.2 — the parser does not populate it) |
| `AlternativeTextDescription` | `str \| None` | Alt text description (populated from the parser's `alt_text` field) |
| `HyperlinkUrl` | `str \| None` | URL if the image is a hyperlink |
| `Tags` | `list[NoteTag]` | OneNote tags attached to this image |

**Methods**:

| Method | Description |
|---|---|
| `Replace(image)` | Copy `Bytes` and `FileName` from another `Image` node into this one |

---

### AttachedFile

Extends `CompositeNode`. An embedded file attachment.

| Property | Type | Description |
|---|---|---|
| `FileName` | `str \| None` | Original filename |
| `Bytes` | `bytes` | Raw file data (default `b""`) |
| `Tags` | `list[NoteTag]` | OneNote tags attached to this attachment |

---

### Table

Extends `CompositeNode`. A table within an OutlineElement.

| Property | Type | Default | Description |
|---|---|---|---|
| `ColumnWidths` | `list[float]` | `[]` | Width of each column in points |
| `BordersVisible` | `bool` | `True` | Whether table borders are visible |
| `Tags` | `list[NoteTag]` | `[]` | OneNote tags attached to this table |

---

### TableRow

Extends `CompositeNode`. A row within a `Table`. Iterate `GetChildNodes(TableCell)` to access cells.

---

### TableCell

Extends `CompositeNode`. A cell within a `TableRow`. Contains `RichText`, `Image`, and other content nodes.

---

### NoteTag

Extends `Node`. A OneNote tag attached to a content node.

| Field | Type | Default | Description |
|---|---|---|---|
| `shape` | `int \| None` | `None` | Numeric shape identifier for the tag icon |
| `label` | `str \| None` | `None` | Display label string (e.g. `"Yellow Star"`, `"Important"`) |
| `text_color` | `int \| None` | `None` | Text color as raw integer |
| `highlight_color` | `int \| None` | `None` | Highlight color as raw integer |
| `created` | `int \| None` | `None` | Raw MS timestamp integer when the tag was created |
| `completed` | `int \| None` | `None` | Raw MS timestamp integer when the tag was completed (`None` = not completed) |

> **Timestamp note**: `created` and `completed` are raw integer timestamps as parsed from the MS-ONE binary format, not `datetime` objects.

**Factory methods**:

| Method | Description |
|---|---|
| `NoteTag.CreateYellowStar()` | Creates a `NoteTag(shape=None, label="Yellow Star")` |

---

### NumberList

Extends `Node`. Numbered or bulleted list metadata on an `OutlineElement`.

| Property | Type | Default | Description |
|---|---|---|---|
| `Format` | `str \| None` | `None` | Number format string from MS-ONE |
| `Restart` | `int \| None` | `None` | Explicit restart number |
| `IsNumbered` | `bool` | `False` | True for ordered (numbered) lists |

---

### LoadOptions

| Property | Type | Default | Description |
|---|---|---|---|
| `DocumentPassword` | `str \| None` | `None` | Setting this causes an `IncorrectPasswordException` at load time; encrypted documents are not supported |
| `LoadHistory` | `bool` | `False` | API compatibility field; not functionally used in v26.2 |

---

### SaveOptions

Base class for all save options. Required positional argument.

| Property | Type | Description |
|---|---|---|
| `SaveFormat` | `SaveFormat` | Target save format |

---

### PdfSaveOptions

Extends `SaveOptions`. PDF-specific export configuration. Construct with `PdfSaveOptions(SaveFormat.Pdf)`.

| Property | Type | Default | Description |
|---|---|---|---|
| `PageIndex` | `int` | `0` | Field exists; **not forwarded to PDF exporter in v26.2** — has no effect on output |
| `PageCount` | `int \| None` | `None` | Field exists; **not forwarded to PDF exporter in v26.2** — has no effect on output |
| `TagIconDir` | `str \| None` | `None` | Directory containing custom tag icon PNG files — **forwarded and applied** |
| `TagIconSize` | `float \| None` | `None` | Tag icon size in points — **forwarded and applied** |
| `TagIconGap` | `float \| None` | `None` | Horizontal gap around tag icons in points — **forwarded and applied** |

> **`PageIndex` / `PageCount` caveat**: These fields are declared on `PdfSaveOptions` for API compatibility, but the `Document.Save()` implementation in v26.2 does not read or forward them to the PDF exporter. All pages are always exported.

### OneSaveOptions, HtmlSaveOptions, ImageSaveOptions {#onehtmlimagesaveoptions}

Declared for API compatibility with Aspose.Note for .NET. Attempting to use them with `Document.Save()` raises `UnsupportedSaveFormatException`.

| Class | Extra fields |
|---|---|
| `OneSaveOptions` | `DocumentPassword: str \| None` |
| `HtmlSaveOptions` | `PageIndex: int`, `PageCount: int \| None` |
| `ImageSaveOptions` | `PageIndex: int`, `PageCount: int \| None`, `Quality: int \| None`, `Resolution: int \| None` |

---

### License and Metered

Compatibility stubs exported for API shape compatibility with Aspose.Note for .NET. All methods are no-ops in this FOSS implementation.

```python
from aspose.note import License, Metered

lic = License()
lic.SetLicense("path/to/license.lic")  # no-op

m = Metered()
m.SetMeteredKey("public_key", "private_key")  # no-op
```

No license key is required to use any feature of Aspose.Note FOSS for Python.

---

## Enumerations

### SaveFormat

| Value | Description |
|---|---|
| `SaveFormat.Pdf` | PDF export — implemented; requires `pip install "aspose-note[pdf]"` |
| `SaveFormat.One` | OneNote format — declared only; raises `UnsupportedSaveFormatException` |
| `SaveFormat.Html` | HTML — declared only; raises `UnsupportedSaveFormatException` |
| `SaveFormat.Jpeg` | JPEG image — declared only; raises `UnsupportedSaveFormatException` |
| `SaveFormat.Png` | PNG image — declared only; raises `UnsupportedSaveFormatException` |
| `SaveFormat.Gif` | GIF image — declared only; raises `UnsupportedSaveFormatException` |
| `SaveFormat.Bmp` | BMP image — declared only; raises `UnsupportedSaveFormatException` |
| `SaveFormat.Tiff` | TIFF image — declared only; raises `UnsupportedSaveFormatException` |

### FileFormat

Enum values used for API compatibility. `Document.FileFormat` always returns `FileFormat.OneNote2010` in v26.2.

| Value | String value |
|---|---|
| `FileFormat.OneNote2010` | `"onenote2010"` |
| `FileFormat.OneNoteOnline` | `"onenoteonline"` |
| `FileFormat.OneNote2007` | `"onenote2007"` |

### HorizontalAlignment

| Value | String value |
|---|---|
| `HorizontalAlignment.Left` | `"left"` |
| `HorizontalAlignment.Center` | `"center"` |
| `HorizontalAlignment.Right` | `"right"` |

### NodeType

| Value | String value |
|---|---|
| `NodeType.Document` | `"document"` |
| `NodeType.Page` | `"page"` |
| `NodeType.Outline` | `"outline"` |
| `NodeType.OutlineElement` | `"outline_element"` |
| `NodeType.RichText` | `"rich_text"` |
| `NodeType.Image` | `"image"` |
| `NodeType.Table` | `"table"` |
| `NodeType.AttachedFile` | `"attached_file"` |

---

## Exceptions

| Exception | Description |
|---|---|
| `AsposeNoteError` | Base class for all Aspose.Note FOSS exceptions |
| `FileCorruptedException` | The `.one` file cannot be parsed (corrupted or malformed binary) |
| `IncorrectDocumentStructureException` | The file structure is invalid or unsupported |
| `IncorrectPasswordException` | Raised when `LoadOptions.DocumentPassword` is set; encrypted documents are not supported |
| `UnsupportedFileFormatException` | The file format is not recognized; exposes a `FileFormat` field (string) |
| `UnsupportedSaveFormatException` | The requested `SaveFormat` is not implemented in this version |

---

## See Also

- [Getting Started Guide](https://docs.aspose.org/note/python/getting-started/)
- [Developer Guide](https://docs.aspose.org/note/python/developer-guide/)
- [Knowledge Base — How-to Articles](https://kb.aspose.org/note/python/)
- [Blog — Aspose.Note for Python](https://blog.aspose.org/note/python/)
