# Orchestrator Handoff Prompt

> **Use this prompt** when assigning a taskcard to an agent.
> Copy and paste, filling in the `{{placeholders}}`.

---

## Handoff Prompt

```
You are being assigned taskcard {{TC_ID}}.

## Your Task
Read and implement taskcard: `plans/taskcards/{{TC_FILENAME}}`

## Binding Rules
1. **Read the taskcard FIRST** — understand scope, allowed paths, and acceptance criteria
2. **Read required specs** — listed in "Required spec references" section
3. **Write fence** — you may ONLY modify files listed in `allowed_paths` frontmatter
4. **Determinism** — no timestamps, no random values, stable ordering
5. **Evidence** — document all decisions in your agent report

## Before You Start
- [ ] Read the taskcard completely
- [ ] Read all required spec references
- [ ] Understand preconditions/dependencies
- [ ] Know your allowed paths

## When Done
- [ ] All acceptance checks pass
- [ ] Tests added and passing (document commands in report)
- [ ] Write `reports/agents/{{AGENT_NAME}}/{{TC_ID}}/report.md`
- [ ] Write `reports/agents/{{AGENT_NAME}}/{{TC_ID}}/self_review.md` using template

## If Blocked
- Create blocker issue at `reports/agents/{{AGENT_NAME}}/{{TC_ID}}/blockers/`
- Issue must validate against `specs/schemas/issue.schema.json`
- Stop work on that path until blocker is resolved

## Non-Negotiables
- NO improvisation outside spec
- NO files outside allowed_paths
- NO guessing — if unclear, create blocker issue
- YES determinism — always
- YES evidence — document everything
```

---

## Example Filled Prompt

```
You are being assigned taskcard TC-411.

## Your Task
Read and implement taskcard: `plans/taskcards/TC-411_facts_extract_catalog.md`

## Binding Rules
1. **Read the taskcard FIRST** — understand scope, allowed paths, and acceptance criteria
2. **Read required specs** — listed in "Required spec references" section
3. **Write fence** — you may ONLY modify files listed in `allowed_paths` frontmatter
4. **Determinism** — no timestamps, no random values, stable ordering
5. **Evidence** — document all decisions in your agent report

## Before You Start
- [ ] Read the taskcard completely
- [ ] Read all required spec references
- [ ] Understand preconditions/dependencies
- [ ] Know your allowed paths

## When Done
- [ ] All acceptance checks pass
- [ ] Tests added and passing (document commands in report)
- [ ] Write `reports/agents/claude-opus/TC-411/report.md`
- [ ] Write `reports/agents/claude-opus/TC-411/self_review.md` using template

## If Blocked
- Create blocker issue at `reports/agents/claude-opus/TC-411/blockers/`
- Issue must validate against `specs/schemas/issue.schema.json`
- Stop work on that path until blocker is resolved

## Non-Negotiables
- NO improvisation outside spec
- NO files outside allowed_paths
- NO guessing — if unclear, create blocker issue
- YES determinism — always
- YES evidence — document everything
```
