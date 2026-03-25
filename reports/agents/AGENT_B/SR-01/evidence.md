# SR-01 Evidence

## Test Run (post-SR-01)

```
collected 15 items

tests/unit/workers/test_w6_seo_hardening.py ...............    [100%]

15 passed, 1 warning in 0.87s
```

Test count increased from 13 (baseline) to 15 (+2 new tests).

## Grep confirmations

### `is_section_index` present in seo_metadata.py
```
grep -n "is_section_index" src/launch/workers/w6_seo_optimizer/seo_metadata.py
22:    is_section_index: bool = False,
64:    robots = "noindex, follow" if is_section_index else "index, follow"
```

### `is_section_index` passed from worker.py
```
grep -n "is_section_index" src/launch/workers/w6_seo_optimizer/worker.py
218:                is_section_index=(md_file.name == "_index.md"),
```

### Old slug-based check is gone
```
grep -n "slug in.*_index" src/launch/workers/w6_seo_optimizer/seo_metadata.py
(no output — check confirmed removed)
```
