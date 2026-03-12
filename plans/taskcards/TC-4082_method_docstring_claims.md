---
id: TC-4082
title: "Add structured method-level docstring claims for Python"
status: Done
priority: Normal
owner: agent
updated: "2026-03-11"
tags: [phase3, understand, python, claims]
depends_on: [TC-4079]
allowed_paths:
  - plans/taskcards/TC-4082_method_docstring_claims.md
  - src/launcher/workers/understand/extract/_deterministic.py
  - tests/unit/workers/understand/test_python_hardening.py
evidence_required:
  - reports/TC-4082/evidence.md
---

# Taskcard TC-4082 — Add structured method-level docstring claims for Python

## Objective

A Python repo with 1 public class can only produce 2 deterministic claims (class docstring +
method list). Adding per-method docstring claims in `ClassName.method_name: first_sentence`
format ensures thin repos still produce N claims where N = number of documented public methods.

## Allowed paths

- plans/taskcards/TC-4082_method_docstring_claims.md
- src/launcher/workers/understand/extract/_deterministic.py
- tests/unit/workers/understand/test_python_hardening.py

## Implementation steps

### Step 1: Add `_extract_method_docstring_claims` function

Add new function to `_deterministic.py`:

```python
def _extract_method_docstring_claims(
    content: str,
    source_file: str,
    family_slug: str,
    seq: int,
    claims: list[dict[str, Any]],
) -> int:
    """Extract claims from public method docstrings in the format 'ClassName.method: first_sentence'.

    Criteria:
    - Public method (not starting with _)
    - Docstring length > 50 chars
    - Not a placeholder docstring
    - Associates method with its parent class
    """
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return seq

    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        cls_name = node.name
        if cls_name.startswith("_"):
            continue
        for child in ast.walk(node):
            if not isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            method_name = child.name
            if method_name.startswith("_"):
                continue
            docstring = ast.get_docstring(child)
            if not docstring or len(docstring) < 50:
                continue
            first_line = docstring.split("\n")[0].strip()
            if len(first_line) < 20:
                first_line = docstring.replace("\n", " ")[:200].strip()
            claim_text = f"{cls_name}.{method_name}: {first_line}"
            if _is_junk_claim(claim_text):
                continue
            seq += 1
            claims.append({
                "claim_id": f"CLM-{family_slug}-{seq:03d}",
                "text": claim_text,
                "kind": "api",
                "evidence": [{
                    "source_file": source_file,
                    "line_start": getattr(child, "lineno", 0),
                    "line_end": getattr(child, "end_lineno", 0),
                    "snippet": first_line[:100],
                }],
                "visibility": "public",
                "tier_relevance": "all",
                "claim_source": "deterministic",
            })
    return seq
```

### Step 2: Call from `_extract_claims_from_python`

After the existing `ast.walk` loop, call:
```python
seq = _extract_method_docstring_claims(content, source_file, family_slug, seq, claims)
```

## Failure modes

### Failure mode 1: Private methods included
**Detection**: Claims with `_method_name` in text
**Resolution**: Guard with `if method_name.startswith("_"): continue`
**Gate**: Claim quality

### Failure mode 2: Duplicate claims from class + method docstring both extracted
**Detection**: Identical first_line text from class docstring and method docstring
**Resolution**: Dedup at validation stage (`_validate_and_normalize_claims`)
**Gate**: Claim dedup

### Failure mode 3: Placeholder docstrings extracted
**Detection**: Claims like "Workbook.__init__: Initialize the workbook"
**Resolution**: `_is_junk_claim` filter catches generic placeholders
**Gate**: Claim quality

## Task-specific review checklist

1. [ ] Only public methods (not starting with `_`) produce claims
2. [ ] Docstring length threshold 50 chars enforced
3. [ ] Format is `ClassName.method_name: first_sentence`
4. [ ] Dedup handled by existing validation pipeline
5. [ ] `claim_source` set to "deterministic"
6. [ ] `_extract_claims_from_python` calls new function
7. [ ] Docstrings updated
8. [ ] Spec confirmed — no drift

## Acceptance checks

1. [ ] `test_method_docstrings_produce_claims` passes
2. [ ] A class with 3 documented public methods produces ≥ 3 claims from method docstrings
3. [ ] Private methods do NOT produce claims

## E2E verification

```bash
.venv/Scripts/python.exe -m pytest tests/unit/workers/understand/test_python_hardening.py::TestMethodDocstringClaims -v
```
