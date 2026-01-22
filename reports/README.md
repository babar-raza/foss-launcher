# reports/ (implementation-time evidence)

During implementation, every agent writes evidence here.

## Required layout

```
reports/
  agents/
    <agent_name>/
      <task_id>/
        report.md
        self_review.md
        artifacts/... (optional)
  templates/
    agent_report.md
    self_review_12d.md
    orchestrator_master_review.md
```

## Rules
- Every taskcard produces `report.md` + `self_review.md`.
- Self-review uses 12-D template.
- Orchestrator writes `reports/orchestrator_master_review.md`.
