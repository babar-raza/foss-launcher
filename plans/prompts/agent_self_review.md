# Agent Self-Review Prompt

> **Use this prompt** when completing the self-review for a taskcard.
> Based on `reports/templates/self_review_12d.md`.

---

## Self-Review Dimensions (12D)

Rate each dimension 1-5. Any score <4 requires a concrete fix plan.

### 1. Spec Adherence (1-5)
```
Score: ___

Evidence:
- Spec X section Y: [how implemented]
- Spec Z binding rule: [how enforced]

If <4, fix plan:
[What needs to change to fully adhere to specs]
```

### 2. Determinism (1-5)
```
Score: ___

Evidence:
- No timestamps: [verified where]
- Stable ordering: [how ensured]
- Reproducible: [proof — e.g., "ran twice, identical output"]

If <4, fix plan:
[What introduces non-determinism and how to fix]
```

### 3. Test Coverage (1-5)
```
Score: ___

Evidence:
- Unit tests: [count and what they cover]
- Integration tests: [if applicable]
- Commands to run: `python -m pytest ...`

If <4, fix plan:
[What tests are missing and how to add them]
```

### 4. Write Fence Compliance (1-5)
```
Score: ___

Evidence:
- Files modified: [list]
- All in allowed_paths: [yes/no]

If <4, fix plan:
[Which files violated and how to remediate]
```

### 5. Error Handling (1-5)
```
Score: ___

Evidence:
- Error cases handled: [list]
- Graceful degradation: [how]

If <4, fix plan:
[What error cases are missing]
```

### 6. Documentation (1-5)
```
Score: ___

Evidence:
- Docstrings: [yes/no, coverage]
- Comments for non-obvious logic: [yes/no]
- Report completeness: [yes/no]

If <4, fix plan:
[What documentation is missing]
```

### 7. Code Quality (1-5)
```
Score: ___

Evidence:
- Follows project patterns: [yes/no]
- No code smells: [yes/no]
- Linting passes: [yes/no]

If <4, fix plan:
[What quality issues to address]
```

### 8. Security (1-5)
```
Score: ___

Evidence:
- No secrets in code: [yes/no]
- Input validation: [where applicable]
- OWASP concerns: [none/addressed]

If <4, fix plan:
[What security issues to address]
```

### 9. Performance (1-5)
```
Score: ___

Evidence:
- No obvious bottlenecks: [yes/no]
- Appropriate algorithms: [yes/no]

If <4, fix plan:
[What performance issues to address]
```

### 10. Integration (1-5)
```
Score: ___

Evidence:
- Upstream contracts honored: [list]
- Downstream contracts provided: [list]
- Integration boundary documented: [yes/no]

If <4, fix plan:
[What integration issues to address]
```

### 11. Evidence Quality (1-5)
```
Score: ___

Evidence:
- Commands documented: [yes/no]
- Outputs captured: [yes/no]
- Decisions traced to specs: [yes/no]

If <4, fix plan:
[What evidence is missing]
```

### 12. Acceptance Criteria (1-5)
```
Score: ___

Evidence:
- [ ] Check 1: [pass/fail]
- [ ] Check 2: [pass/fail]
- [ ] Check N: [pass/fail]

If <4, fix plan:
[Which criteria not met and how to fix]
```

---

## Summary Template

```markdown
# Self-Review: {{TC_ID}}

## Scores
| Dimension | Score | Notes |
|-----------|-------|-------|
| Spec Adherence | _/5 | |
| Determinism | _/5 | |
| Test Coverage | _/5 | |
| Write Fence | _/5 | |
| Error Handling | _/5 | |
| Documentation | _/5 | |
| Code Quality | _/5 | |
| Security | _/5 | |
| Performance | _/5 | |
| Integration | _/5 | |
| Evidence Quality | _/5 | |
| Acceptance Criteria | _/5 | |

**Average Score**: _/5

## Fix Plans (for scores <4)
1. [Dimension]: [Fix plan]

## Overall Assessment
[1-2 sentences on task completion quality]
```

---

## Scoring Guide

| Score | Meaning |
|-------|---------|
| 5 | Exemplary — exceeds requirements |
| 4 | Complete — meets all requirements |
| 3 | Partial — meets most requirements, minor gaps |
| 2 | Incomplete — significant gaps |
| 1 | Failed — does not meet requirements |

---

## Quick Checklist

Before submitting self-review:
- [ ] All 12 dimensions scored
- [ ] Evidence provided for each score
- [ ] Fix plan for any score <4
- [ ] Summary completed
- [ ] File saved to `reports/agents/{{AGENT_NAME}}/{{TC_ID}}/self_review.md`
