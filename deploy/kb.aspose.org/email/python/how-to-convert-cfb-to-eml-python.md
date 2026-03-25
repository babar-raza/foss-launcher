---
canonical: https://kb.aspose.org/email/python/convert-cfb-eml-python/
canonical_import: aspose.email_foss
date: '2026-03-19T15:03:00Z'
dateModified: '2026-03-19T15:03:00Z'
datePublished: '2026-03-19T15:03:00Z'
description: The MapiMessage class enables programmatic creation, reading, editing,
  and saving of Outlook MSG files. The MsgWriter class provides methods to serialize...
display_name: Aspose.Email FOSS
family: email
keywords:
- file
- compound
- binary
lastmod: '2026-03-19T15:03:00Z'
page_role: howto_article
platform: python
reading_time: 1
robots: index, follow
seoTitle: How to Convert File Formats with Aspose.Email FOSS | Guide
slug: convert-cfb-eml-python
title: How to Convert File Formats with Aspose.Email FOSS
type: howto_article
url: /kb.aspose.org/email/python/convert-cfb-eml-python/
weight: 17
---

## Prerequisites

- Python 3.8 or later
- Install the package using: `pip install aspose-email-foss`
- Input files must be valid MSG (.msg) or EML (.eml) files

```python
# source: snippet_0
from aspose.email_foss.msg import MapiMessage
from aspose.email_foss.cfb import CFBReader
```

```python
# Prerequisites
from aspose.email_foss.msg import MapiMessage
from aspose.email_foss.cfb import CFBReader
```

## See Also

- [Explore the API reference](/reference.aspose.org/email/python/api-overview/)
- [Frequently asked questions](/kb.aspose.org/email/python/frequently-asked-questions/)
- [Low-level CFB parsing details](/reference.aspose.org/email/python/cfb-reader/)
- [High-level MAPI message APIs](/reference.aspose.org/email/python/mapi-message/)
- [Troubleshooting common issues](/kb.aspose.org/email/python/problem-solving/)

## Problem

The library supports writing Outlook MSG (.msg) files through the MapiMessage class.

The MapiMessage class enables programmatic creation, reading, editing, and saving of Outlook MSG files.

The MsgWriter class provides methods to serialize MAPI message documents to .msg files using to_bytes() and write_file().

CFBDocument: Mutable Compound File Binary (CFB) document description.

CFBError: Raised for malformed or unsupported Compound File Binary (CFB) content.

CFBReader: Reusable reader for Compound File Binary (CFB) containers.

CFBReader.iter_tree(): Yield a depth-first tree traversal as `(depth, entry)` tuples.

CFBStorage: Mutable storage node used by the CFB writer.

CFBStream: Mutable stream node used by the CFB writer.

CFBWriter: Deterministic serializer for Compound File Binary (CFB) containers.

DirectoryEntry: Fixed-size directory record for one storage/stream object and its tree links.

Header: Header record at file offset 0 defining Compound File Binary (CFB) geometry and allocation chain entry points.
