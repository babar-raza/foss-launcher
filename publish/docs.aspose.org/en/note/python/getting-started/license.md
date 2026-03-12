---
page_role: howto_article
title: License
description: >-
  Licensing information for Aspose.Note FOSS for Python. The library is distributed
  under the MIT license (Aspose-Split). Third-party notices cover ReportLab used for PDF export.
weight: 20
type: docs
---

## License Overview

Aspose.Note FOSS for Python is distributed under the **MIT License (Aspose-Split)**. It is 100% free to use, modify, and distribute. There is no usage fee, no API key, and no registration required.

The license identifier in `pyproject.toml` is `LicenseRef-Aspose-Split`. The full license text is included in the repository as `LICENSE`.

**Source**: https://github.com/aspose-note-foss/Aspose.Note-FOSS-for-Python/blob/main/LICENSE

---

## Third-Party Notices

PDF export functionality uses [ReportLab](https://www.reportlab.com/), which is installed as an optional dependency via `pip install "aspose-note[pdf]"`. ReportLab's license terms are documented in `THIRD_PARTY_NOTICES.md` in the repository root.

**Source**: https://github.com/aspose-note-foss/Aspose.Note-FOSS-for-Python/blob/main/THIRD_PARTY_NOTICES.md

---

## What the License Allows

Under the MIT License you may:

- Use the library in commercial applications
- Use the library in open-source projects
- Modify the source code
- Redistribute the library or modified versions
- Include the library in SaaS products and server-side pipelines

The only requirement is that the original copyright notice and license text must be retained in any distribution.

---

## No Runtime License Key Required

Unlike commercial Aspose products, Aspose.Note FOSS for Python does **not** require a license file or license key at runtime. Import the package and use it directly:

```python
from aspose.note import Document, SaveFormat

doc = Document("MyNotes.one")
doc.Save("output.pdf", SaveFormat.Pdf)
```

There is no `License` class, no `SetLicense()` call, and no metered key setup.

---

## Relationship to Commercial Aspose.Note

Aspose.Note FOSS for Python is an independent open-source library with an API surface modeled after Aspose.Note for .NET. It is not a wrapper around the commercial product. The commercial products are separate:

| Product | License | Write .one | Encryption | Image/HTML export |
|---|---|---|---|---|
| Aspose.Note FOSS for Python | MIT (free) | No | No | No |
| Aspose.Note for .NET | Commercial | Yes | Yes | Yes |
| Aspose.Note for Java | Commercial | Yes | Yes | Yes |

If your workflow requires writing `.one` files, decrypting protected notebooks, or exporting to HTML or image formats, see the [official Aspose.Note products](https://products.aspose.com/note/).

---

## See Also

- [Installation](installation/)
- [Getting Started](/docs.aspose.org/note/python/getting-started/)
- [API Reference](https://reference.aspose.org/note/python/)
- [Source Repository](https://github.com/aspose-note-foss/Aspose.Note-FOSS-for-Python)
