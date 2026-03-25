# AGENT_A Evidence: ORCH-SU-01

## Verified Inputs

- Fresh Cells run: `runs/260313_051354_cells_python_a359`
- Fresh Note run: `runs/260313_051458_note_python_0fc6`
- Active taskcards:
  - `plans/taskcards/TC-4257_scout_evidence_pipeline_hardening.md`
  - `plans/taskcards/TC-4258_understand_evidence_pipeline_hardening.md`

## Verified Findings

- Scout boundary schema is missing: `specs/schemas/scout_bundle.schema.json`
- Scout to Understand in-memory handoff is not real because `WorkerContext` is recreated per node in `src/launcher/orchestrator/graph_builder.py`
- Understand fails a real pilot self-review on Note evidence
- `tests/unit/workers/test_understand.py` currently fails on multiple extraction cases

## Commands

```powershell
$env:PYTHONHASHSEED='0'; .venv\Scripts\python.exe -m launcher.cli.main run configs\pilots\aspose-cells-foss-python.yaml --stop-after understand
$env:PYTHONHASHSEED='0'; .venv\Scripts\python.exe -m launcher.cli.main run configs\pilots\aspose-note-foss-python.yaml --stop-after understand
$env:PYTHONHASHSEED='0'; .venv\Scripts\python.exe -m pytest tests\unit\workers\test_scout.py tests\unit\workers\test_understand.py -q
```
