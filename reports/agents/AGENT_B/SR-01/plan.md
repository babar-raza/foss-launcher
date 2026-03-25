# SR-01 Plan

Fix the `robots` regression introduced by TC-3400 Change B, where `index.md` files
use `md_file.parent.name` as slug, making the old `slug in ("_index", "index")` check
unreachable. Add `is_section_index: bool = False` kwarg to `optimize_seo_metadata()`,
pass `is_section_index=(md_file.name == "_index.md")` from worker.py, and strengthen
two existing test assertions (weak substring checks) plus add two new targeted tests.

Addresses: GAP-01 (HIGH), GAP-03, GAP-04.
