# SR-02 Plan

Three cleanup tasks in W6 SEO Optimizer:

1. Delete the dead variable `page_plan_path = artifacts_dir / "page_plan.json"` (line 96 of
   worker.py) — it was assigned but never read.

2. Replace all 6 occurrences of `[W10]` logger prefix with `[W6]` in worker.py. Also fix
   the class docstring on `SEOOptimizerError` which said "W10".

3. Stub the dead `inject_keywords_naturally` function body in keyword_optimizer.py —
   `modified` was never set True so the function always returned unchanged content. The stub
   documents this with a DEPRECATED notice and maintains the same signature for backward compat.
   `calculate_keyword_density` is left intact (has callers in test_w6_seo_optimizer.py).

Addresses: GAP-02, GAP-07, GAP-09.
