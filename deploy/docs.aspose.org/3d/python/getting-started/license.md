---
page_role: howto_article
title: License
description: >-
  Aspose.3D FOSS for Python is released under the MIT License — free for
  commercial, open-source, and internal use with no API key, no usage limits,
  and no registration required.
weight: 15
type: docs
---

Aspose.3D FOSS for Python (`aspose-3d-foss`) is open-source software released under the **MIT License**. You can use it in commercial products, open-source projects, internal tools, and research without restriction. No license key, API key, metered token, or registration is required.

## Key Points of the MIT License

- **Free for any use**: commercial, open-source, internal, academic, and personal.
- **No usage limits**: there are no call quotas, file-size caps, or watermark restrictions.
- **No API key required**: install the package and start using it immediately.
- **No registration**: no account, no sign-in, no online activation.
- **Attribution**: retain the copyright notice and the MIT License text in your distribution (see below).

## MIT License Text

The full license text shipped with the package reads:

```
MIT License

Copyright (c) Aspose Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Viewing the License in Your Installed Package

The `LICENSE` file is included inside the installed package directory. You can locate it with Python's `importlib.metadata` module:

```python
import importlib.metadata

dist = importlib.metadata.packages_distributions()
meta = importlib.metadata.metadata("aspose-3d-foss")

print(meta["License"])          # Should print: MIT
print(meta["Name"])             # aspose-3d-foss
print(meta["Version"])          # e.g. 26.1.0
```

Or inspect it directly with pip:

```bash
pip show aspose-3d-foss
```

This prints the package name, version, summary, homepage, and license field (`MIT`).

## No Commercial License Required

Unlike some Aspose products that offer metered or enterprise licensing, `aspose-3d-foss` is not a commercial product. There is no paid tier, no evaluation watermark, and no restricted feature set. All API functionality described in this documentation is available under the MIT License from the first install.

## Redistribution and Bundling

If you redistribute the package as part of your own application or library:

1. Include the original MIT License notice (the `LICENSE` file from the installed package is sufficient).
2. You do not need to make your application open-source — the MIT License is permissive, not copyleft.
3. You may modify the source code and distribute modified versions under the same MIT License.

## Additional Resources

- [Installation Guide](../installation/) — Install `aspose-3d-foss` via pip
- [Developer Guide](../../developer-guide/_index.md) — API reference with Python code examples
- [PyPI Page](https://pypi.org/project/aspose-3d-foss/) — Package page with full metadata and download statistics
