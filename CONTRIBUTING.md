# Contributing

This repository is a **spec pack + scaffold**.

## Ground rules

- Do not change binding specs casually. Changes to `specs/` must be deliberate and reviewed.
- Keep implementation aligned to specs. If implementation diverges, update specs or fix code.
- No manual content edits in target site repos during launches (see `plans/policies/no_manual_content_edits.md`).
- All agent work must be auditable: write reports to `reports/` and runs to `runs/`.

## Development quickstart

```bash
make install
make lint
make validate
make test
```
