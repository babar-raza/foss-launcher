# Spec 42: Quality Feedback Loop (W9 → W2/W4)

**Status**: Binding
**Version**: v1.0
**Author**: Agent
**Date**: 2026-02-20

## Overview

After each validation run, W9 (Validator) writes a `quality_feedback.json` file recording
per-page quality issues and suggested remediation actions. On the next run, W4 (IAPlanner)
and W2 (FactsBuilder) read this feedback to tune their parameters.

## quality_feedback.json Schema

```json
{
  "run_id": "r_20260220T...",
  "generated_at": "2026-02-20T...",
  "pages": [
    {
      "output_path": "docs/3d/python/getting-started/index.md",
      "error_count": 2,
      "warn_count": 5,
      "gate_issues": [
        {"error_code": "G16-001", "severity": "error", "message": "..."}
      ],
      "suggested_actions": ["increase_claim_count", "lower_snippet_threshold"]
    }
  ]
}
```

## Suggested Actions

| Code | Trigger | W4 Action | W2 Action |
|------|---------|-----------|-----------|
| `increase_claim_count` | Page has ≥2 G7/G15 errors (content_density, api_hallucination) | top_k += 3 (max 20) | — |
| `lower_snippet_threshold` | Page has ≥2 G15 errors (api_hallucination) | — | similarity_threshold -= 0.05 (min 0.2) |

## Feature Flag

`use_feedback: false` in run_config (default). When false, W9 still writes feedback but W2/W4 don't read it.

## Immutability

Feedback from run N is read-only in run N+1. It is never modified after being written.
