# Diff Manifest — Sub-Phase 1: Platform Completeness Hardening

## Files Modified

| File | Change Type | Description |
|------|-------------|-------------|
| `tools/validate_platform_layout.py` | Enhanced | Added `check_products_v2_path_format()` and `check_templates_products_v2_structure()` checks |

## Files Added

| File | Purpose |
|------|---------|
| `reports/phase-6_2_platform-completeness/change_log.md` | This sub-phase change log |
| `reports/phase-6_2_platform-completeness/diff_manifest.md` | This file |
| `reports/phase-6_2_platform-completeness/self_review_12d.md` | Self-review |
| `reports/phase-6_2_platform-completeness/gate_outputs/validate_platform_layout.txt` | Gate output |
| `reports/phase-6_2_platform-completeness/gate_outputs/markdown_links.txt` | Gate output |

## Detailed Diff

### tools/validate_platform_layout.py

```diff
+ def check_products_v2_path_format(self) -> bool:
+     """Check that products V2 paths use /{locale}/{platform}/ not /{platform}/ alone.
+     ...
+
+ def check_templates_products_v2_structure(self) -> bool:
+     """Check that products templates V2 hierarchy uses __LOCALE__/__PLATFORM__ order."""
+     ...
+
  checks = [
      ...
+     ("Products V2 path uses /{locale}/{platform}/ format", self.check_products_v2_path_format),
+     ("Products templates V2 use __LOCALE__/__PLATFORM__ order", self.check_templates_products_v2_structure),
  ]
```
