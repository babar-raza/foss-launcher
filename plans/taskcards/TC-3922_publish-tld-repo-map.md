---
id: TC-3922
title: "Simplify content_repo_map to TLD-level keys (aspose.org / aspose.net)"
status: Done
priority: High
owner: "agent"
updated: "2026-03-10"
tags: [publish, deploy, git, multi-domain]
depends_on: [TC-3921]
allowed_paths:
  - plans/taskcards/TC-3922_publish-tld-repo-map.md
  - src/launcher/models/run_config.py
  - src/launcher/workers/publish/worker.py
  - tests/unit/workers/test_publish.py
evidence_required:
  - reports/agents/B-Impl/TC-3922/evidence.md
---

# Taskcard TC-3922 — Simplify content_repo_map to TLD-level keys

## Objective

TC-3921 implemented `content_repo_map` keyed by full subdomain (`"docs.aspose.org"`).
Users only want to set two env vars — one root path for all aspose.org repos, one for all aspose.net.
This TC changes routing to extract the TLD (`aspose.org` / `aspose.net`) from the page's subdomain
so only two map entries are needed, regardless of how many subdomains exist.

## Required spec references

- `specs/worker_publish.md` (publish worker output configuration)

## Scope

### In scope
- Update `_push_to_content_repo()` in `worker.py`: group by TLD (last two domain components) instead of full subdomain
- Update `content_repo_map` docstring in `run_config.py` to show 2-key example
- Update all `TestDeployIntegration` tests to use `"aspose.org"` as map key instead of `"docs.aspose.org"`

### Out of scope
- Changes to `_git_publisher.py` (domain-agnostic)
- Changes to `PublishBundle` model or schema
- Changes to promote_run or deploy/promoter

## Inputs

- `src/launcher/workers/publish/worker.py` — `_push_to_content_repo()` with subdomain-level grouping
- `tests/unit/workers/test_publish.py` — tests using `"docs.aspose.org"` map keys

## Outputs

- Updated `worker.py` using TLD extraction
- Updated tests using `"aspose.org"` keys
- Updated docstring in `run_config.py`

## Allowed paths

- plans/taskcards/TC-3922_publish-tld-repo-map.md
- src/launcher/models/run_config.py
- src/launcher/workers/publish/worker.py
- tests/unit/workers/test_publish.py

### Allowed paths rationale

- `run_config.py`: docstring update for `content_repo_map`
- `worker.py`: TLD extraction logic in `_push_to_content_repo`
- `test_publish.py`: map keys updated to TLD level

## Implementation steps

### Step 1: Update `_push_to_content_repo` in worker.py

Replace subdomain grouping with TLD grouping:
```python
# OLD
domain = cp.split("/")[0]
by_domain.setdefault(domain, []).append(cp)

# NEW
subdomain = cp.split("/")[0]      # e.g. "docs.aspose.org"
parts = subdomain.split(".")
tld_key = ".".join(parts[-2:]) if len(parts) >= 2 else subdomain  # "aspose.org"
by_tld.setdefault(tld_key, []).append(cp)
```

Also rename `by_domain` → `by_tld` and update the warning message.

### Step 2: Update docstring in run_config.py

Change the example in `content_repo_map` docstring from per-subdomain to 2-key:
```yaml
content_repo_map:
  "aspose.org":  "${ASPOSE_ORG_CONTENT_REPO}"
  "aspose.net":  "${ASPOSE_NET_CONTENT_REPO}"
```

### Step 3: Update tests

In `TestDeployIntegration`, change all occurrences of `"docs.aspose.org"` map keys to `"aspose.org"`.

## Failure modes

### Failure mode 1: Single-component domain (no dots)

**Detection**: `content_path = "local/foo/bar"` — `split("/")[0]` = `"local"`, no dots
**Resolution**: Guard `if len(parts) >= 2` falls back to the full token; map lookup will miss → warning log, skip
**Gate**: Test `test_content_repo_missing_skips_mr` covers missing map key

### Failure mode 2: Three-level TLD (e.g. aspose.co.uk)

**Detection**: `"docs.aspose.co.uk"` → `parts[-2:]` = `"co.uk"` (wrong)
**Resolution**: Not in scope — aspose domains are all `.org` or `.net`. Document limitation in docstring.
**Gate**: Docstring note

### Failure mode 3: Tests use old subdomain keys after change

**Detection**: Tests fail with KeyError or empty result because map key `"docs.aspose.org"` not found
**Resolution**: Update all test `content_repo_map` dicts to use `"aspose.org"` key
**Gate**: `pytest tests/unit/workers/test_publish.py` must pass

## Task-specific review checklist

1. [ ] `_push_to_content_repo()` extracts `".".join(parts[-2:])` from subdomain
2. [ ] `by_domain` renamed to `by_tld` throughout the function
3. [ ] Warning log says "No repo configured for TLD: %s" (not "domain")
4. [ ] `content_repo_map` docstring shows 2-key example (`aspose.org`, `aspose.net`)
5. [ ] All test map keys use `"aspose.org"` instead of `"docs.aspose.org"`
6. [ ] All 27 tests pass: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_publish.py -v`
7. [ ] Docstrings updated for changed function
8. [ ] No spec drift (worker behaviour unchanged except routing key resolution)
9. [ ] Schema description fields unchanged (no schema changes in this TC)
10. [ ] `docs/README.md` ownership map checked — no publish guide trigger
11. [ ] Full suite: no regressions

## Deliverables

1. Updated `src/launcher/workers/publish/worker.py`
2. Updated `src/launcher/models/run_config.py` (docstring only)
3. Updated `tests/unit/workers/test_publish.py`
4. Evidence at `reports/agents/B-Impl/TC-3922/evidence.md`

## Acceptance checks

1. [ ] `_push_to_content_repo()` groups by TLD not full subdomain
2. [ ] `content_repo_map` docstring shows `"aspose.org"` / `"aspose.net"` example
3. [ ] All 27 publish tests pass

## Self-review

### Verification results
- [ ] Tests: 27/27 PASS
- [ ] Evidence captured: reports/agents/B-Impl/TC-3922/evidence.md
- [ ] Doc freshness: checked

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_publish.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q 2>&1 | tail -10
```

**Expected results**:
- All 27 publish tests pass
- No regressions in full suite

## Integration boundary proven

**Upstream**: `promote_run()` produces `PromotionReport.details[].content_path` values like `"docs.aspose.org/3d/python/features"`
**Downstream**: `_git_publisher.copy_to_content_repo()` receives the content repo root; path is domain-agnostic
**Contract**: `content_repo_map` keys must match the TLD extracted from `content_path` first component
