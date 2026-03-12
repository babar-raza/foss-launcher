---
id: TC-3859
title: "evaluate/safety: scope content scanning to prose only"
status: Done
priority: High
owner: agent
updated: "2026-03-08"
tags: [evaluate, checks, safety]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-3859_safety_code_block_scoping.md
  - src/launcher/workers/evaluate/checks/safety.py
  - src/launcher/workers/evaluate/worker.py
evidence_required:
  - reports/TC-3859/evidence.md
---

# Taskcard TC-3859 — evaluate/safety: scope content scanning to prose only

## Objective

`check_safety()` has two false positive vectors: (1) the commercial domain regex scans
ALL content including code blocks, so a release URL in a code comment fires a `high`
finding; (2) the base64 regex in `body_no_code` doesn't strip inline code, so long
inline identifiers can match. This taskcard scopes both scans to prose-only content.

## Required spec references

- `specs/evaluation.md` (Section: safety check definition)

## Scope

### In scope
- `check_safety()`: strip code blocks before commercial domain scan
- `check_safety()`: strip inline code from `body_no_code` before sensitive data scan
- Add `page_role: str = ""` parameter to signature (consistency)
- `worker.py` call site: pass `page_role`

### Out of scope
- Changing `_COMMERCIAL_DOMAIN_RE` pattern — it's correct
- Changing `_SENSITIVE_PATTERNS` — they're correct
- XSS scan — already uses `prose` variable (code blocks stripped)

## Inputs

- `src/launcher/workers/evaluate/checks/safety.py`
- `src/launcher/workers/evaluate/worker.py`

## Outputs

- Modified `safety.py` with tighter content scoping
- Modified `worker.py` call site

## Allowed paths

- plans/taskcards/TC-3859_safety_code_block_scoping.md
- src/launcher/workers/evaluate/checks/safety.py
- src/launcher/workers/evaluate/worker.py

### Allowed paths rationale
Only the safety check and its call site are modified.

## Implementation steps

### Step 1: Strip code blocks before commercial domain scan

Replace:
```python
commercial_links = _COMMERCIAL_DOMAIN_RE.findall(content)
```
With:
```python
content_no_code = re.sub(r"```.*?```", "", content, flags=re.DOTALL)
commercial_links = _COMMERCIAL_DOMAIN_RE.findall(content_no_code)
```

### Step 2: Strip inline code from body_no_code before base64/sensitive scan

After the existing `body_no_code = re.sub(r"```.*?```", "", content, flags=re.DOTALL)[:50_000]`
line, add:
```python
body_no_code = re.sub(r"`[^`\n]+`", "", body_no_code)
```

### Step 3: Add page_role parameter

```python
def check_safety(content: str, slug: str, *, page_role: str = "") -> list[Finding]:
```

### Step 4: Update call site in worker.py

```python
findings.extend(check_safety(content, slug, page_role=page_role))
```

## Failure modes

### Failure mode 1: Commercial links in prose still missed

**Detection**: A page with `https://www.aspose.com` in prose text doesn't fire.
**Resolution**: Verify `content_no_code` strips code blocks correctly but leaves prose.
The regex `re.sub(r"```.*?```", "", content, flags=re.DOTALL)` is non-greedy; verify
it doesn't over-strip. Test: prose link → fires; code link → doesn't fire.
**Gate**: Unit test for commercial link in prose vs code block.

### Failure mode 2: Base64 pattern now misses long inline identifiers

**Detection**: A legitimate base64 key in inline code is not caught.
**Resolution**: This is the DESIRED behavior — inline code identifiers should not be
flagged as sensitive data. Actual base64 secrets should appear in prose as strings,
not as inline code tokens.
**Gate**: Test: ``api_key = `sk-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa=` `` → no finding.

### Failure mode 3: Inline code stripping breaks page_size calculation

**Detection**: Page size byte count changes after inline stripping.
**Resolution**: Page size is calculated from the raw `content`, before any stripping,
in a separate block (line 34-43). Confirm the strip only applies to `body_no_code`.
**Gate**: Verify page_size check uses `len(content.encode("utf-8"))` unchanged.

## Task-specific review checklist

1. [ ] Commercial domain scan uses `content_no_code` (code blocks stripped)
2. [ ] Page size check still uses raw `content` (unchanged)
3. [ ] XSS check still uses `prose` variable (already code-block-stripped)
4. [ ] Inline code stripped from `body_no_code` AFTER triple-backtick stripping
5. [ ] `page_role` parameter is keyword-only
6. [ ] Test: release URL in ` ```bash ` block → 0 high findings
7. [ ] Test: release URL in prose → 1 high finding
8. [ ] Docstrings updated for check_safety()
9. [ ] Schema `"description"` fields present for all new/changed properties

## Deliverables

1. `src/launcher/workers/evaluate/checks/safety.py` — modified
2. `src/launcher/workers/evaluate/worker.py` — call site updated

## Acceptance checks

1. [x] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x` — all pass
2. [x] Release URL inside code block → 0 high findings from safety check
3. [x] Release URL in prose → 1 high finding from safety check

## Self-review

### Verification results
- [x] Tests: 2863/2863 PASS
- [x] Evidence captured: reports/TC-3859/evidence.md

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -v
```

## Integration boundary proven

**Upstream**: `_run_deterministic_checks()` calls `check_safety`
**Downstream**: `grade_page()` receives findings
**Contract**: Code block content (URLs, identifiers) does not contribute to safety findings
