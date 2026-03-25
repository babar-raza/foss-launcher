---
canonical: https://kb.aspose.org/email/_index/
canonical_import: aspose.email
code_import: aspose.email
date: '2026-03-24T16:46:41Z'
dateModified: '2026-03-24T16:46:41Z'
datePublished: '2026-03-24T16:46:41Z'
description: It supports both direct access to internal structures like storages and
  streams, and high-level message handling via `MapiMessage`.
display_name: Aspose.Email FOSS
family: email
keywords:
- email python
- email python library
- email python package
- email python module
- email python install
- email python code
- email python documentation
- email python regex
lastmod: '2026-03-24T16:46:41Z'
page_role: toc
platform: python
reading_time: 1
robots: noindex, follow
seoTitle: Aspose.Email FOSS Kb _Index
slug: _index
title: Kb _Index
type: toc
url: /kb.aspose.org/email/_index/
weight: 7
---

## Capabilities

Aspose.Email FOSS provides low- and high-level APIs for reading, inspecting, and manipulating Outlook MSG files and Compound File Binary (CFB) containers in Python. It supports both direct access to internal structures like storages and streams, and high-level message handling via `MapiMessage`.

- Read and parse MSG files and CFB containers using `CFBReader`, `MsgReader`, and `MapiMessage.from_file()`
- Inspect and modify message properties, recipients, and attachments via `MapiMessage`, `MapiAttachment`, and `MapiProperty`
- Convert between `MapiMessage` and standard Python `email.message.EmailMessage` objects
- Serialize CFB documents and MSG files using `CFBWriter` and `MsgWriter`

## Quick Install

This section covers installation and initial setup for Aspose.Email FOSS, the Python email processing library. Install the package using pip, then verify the installation by importing the core module.

```bash
pip install aspose.email
```

After installation, verify the setup by running `import aspose.email` in a Python interpreter or script. No additional configuration is required.

## Getting Started

This section covers the Python API for reading, writing, and manipulating Outlook MSG files and Compound File Binary (CFB) containers using Aspose.Email FOSS. The library exposes core classes like `MapiMessage`, `CFBReader`, `CFBWriter`, and supporting types for low-level file inspection and message processing.

```python
import aspose.email

msg = aspose.email.MapiMessage.from_file("sample.msg")
print(msg.subject)
```

## Developer Guide

This section covers the Python API for reading, inspecting, and manipulating Outlook MSG files and Compound File Binary (CFB) containers using Aspose.Email FOSS. The core classes include `MapiMessage` for high-level message handling, `CFBReader`/`CFBWriter` for low-level CFB parsing and serialization, and supporting types like `MapiAttachment`, `MapiProperty`, and `CommonMessagePropertyId` for structured access to MAPI semantics.

Developers can load MSG files via `MapiMessage.from_file()` or convert from [identifier omitted] using `MapiMessage.from_email_message()`. For deeper inspection, `CFBReader` exposes raw storage and stream data through methods like `get_stream_data()` and `iter_storages()`. Attachments and embedded messages are handled via `MapiAttachment.from_bytes()` and `MapiAttachment.from_embedded_message()`, while named properties are defined using `MapiNamedProperty.string()` or `MapiNamedProperty.numeric()`.

- Load and inspect MSG files with `MapiMessage`
- Parse CFB containers using `CFBReader` and `CFBDocument`
- Create and modify attachments with `MapiAttachment`
- Access MAPI properties via `CommonMessagePropertyId` and `MapiProperty`
- Convert between MSG and `email.message.EmailMessage`

## See Also

This section covers the Python API for reading, writing, and manipulating Outlook MSG files and Compound File Binary (CFB) containers using Aspose.Email FOSS.

- Read MSG files — load and inspect `MapiMessage` objects from `.msg` files using `from_file()` and access headers, recipients, and attachments.
- Convert email formats — transform between `MapiMessage`, `MsgDocument`, and Python's `email.message.EmailMessage` using dedicated factory methods.
- Work with CFB containers — parse and serialize low-level structures like `CFBReader`, `CFBWriter`, and `CFBDocument` for advanced file analysis.
- Manage MAPI properties — access and modify named and numeric properties via `MapiProperty`, `MapiNamedProperty`, and `CommonMessagePropertyId` constants.
- Handle attachments and embedded messages — create `MapiAttachment` instances from bytes or embedded `MapiMessage` objects with full storage isolation.
