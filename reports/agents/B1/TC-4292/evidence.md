# TC-4292 Evidence — Generate: Property vs method distinction in LLM prompt

## Date: 2026-03-14

## Changes Made

### `src/launcher/workers/generate/section_prompt.py`
- In `_format_api_surface()`, added PROPERTY ACCESS RULE after properties listing
- Rule only emitted when `any(b.typed_properties for b in class_briefs if b)` is True
- Rule text: "Properties listed under 'Properties' MUST be accessed WITHOUT parentheses... Methods listed under 'Methods' MUST be called WITH parentheses"

## Root Cause Addressed

LLM generated `scene.rootNode()` (method call) instead of `scene.rootNode` (property access) because the prompt didn't distinguish access patterns. This caused 12+ api_identifier_unknown_method findings in 3d_typescript.

## Test Results

```
4436 passed, 65 skipped, 3 xfailed, 2 xpassed in 102.93s
```

## Expected E2E Impact

- Eliminates 12+ property/method confusion findings in 3d_typescript
- 5 D-grade typescript reference pages should improve to C/B
