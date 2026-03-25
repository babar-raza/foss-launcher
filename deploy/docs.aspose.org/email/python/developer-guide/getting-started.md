---
canonical: https://docs.aspose.org/email/python/developer-guide/getting-started/
canonical_import: aspose.email_foss
date: '2026-03-19T06:25:09Z'
dateModified: '2026-03-19T06:37:47Z'
datePublished: '2026-03-19T06:25:09Z'
description: The library supports writing Outlook MSG files (.msg) through the MapiMessage
  class. The library supports reading Compound File Binary (CFB) containers...
display_name: Aspose.Email FOSS
family: email
keywords:
- library
- supports
- files
lastmod: '2026-03-19T06:37:47Z'
page_role: workflow_page
platform: python
reading_time: 1
robots: index, follow
seoTitle: Aspose.Email FOSS Getting Started
slug: getting-started
title: Getting Started
type: workflow_page
url: /docs.aspose.org/email/python/developer-guide/getting-started/
weight: 10
---

## Prerequisites

- Python 3.8 or later installed on your system
- The aspose.email-foss package installed via pip: `pip install aspose.email-foss`
- No additional system dependencies required—this is a pure Python implementation

## Next Steps

- Explore [Working with Attachments](https://docs.example.com/email/python/attachments) to learn how to add, extract, and manage embedded messages and file attachments.
- Review [Low-Level CFB Access](https://docs.example.com/email/python/cfb-structure) for advanced scenarios involving direct manipulation of Compound File Binary containers.
- Consult the [API Reference](https://docs.example.com/email/python/api) for full method signatures and property details.
- See [Conversion Scenarios](https://docs.example.com/email/python/conversions) for more format transformations, including MSG ↔ EML ↔ MHT.

```python
# source: snippet_0
from aspose.email_foss.msg import MapiMessage
from aspose.email_foss.cfb import CFBReader
```

## See Also

- [Install Aspose.Email FOSS](/docs.aspose.org/email/python/developer-guide/installation/)
- [Load email files](/kb.aspose.org/email/python/how-to-load-files-python/)
- [API reference documentation](/reference.aspose.org/email/python/api-overview/)
- [Convert file formats](/kb.aspose.org/email/python/how-to-convert-cfb-to-eml-python/)
- [How to Save Files with Aspose.Email FOSS](/kb.aspose.org/email/python/how-to-save-files-python/)

## Overview

The library supports reading Outlook MSG files (.msg) through the MapiMessage class.

The library supports writing Outlook MSG files (.msg) through the MapiMessage class.

The library supports reading Compound File Binary (CFB) containers through the CFBReader class.

The library supports writing Compound File Binary (CFB) containers through the CFBWriter class.

The library supports converting MSG files to EML format using the MapiMessage.to_email_message() method.

The library supports converting EML files to MSG format using the MapiMessage.from_email_message() method.

The library supports importing EML (.eml) files.

The library supports importing and exporting MAPI (.msg) files.

The library supports importing and exporting CFB (.cfb) files.

The library supports importing and exporting MSG (.msg) files.

The library supports conversion between MSG and EML formats, including bidirectional round-trip operations.

CFBDocument: Mutable Compound File Binary (CFB) document description.
