# Resume Instructions — <TS>

If you restart after a crash/timeout:

1) Open `reports/swarm_implementation/<TS>/swarm_state.json`.
2) Confirm repo head and branch:
   - `git status`
   - `git rev-parse HEAD`
3) Reconcile progress:
   - Compare `swarm_state.json` task statuses with `plans/taskcards/STATUS_BOARD.md`.
   - Verify evidence exists for any DONE task:
     - `reports/agents/<agent>/<TC-ID>/report.md`
     - `reports/agents/<agent>/<TC-ID>/self_review.md`
4) Continue:
   - Finish earliest IN_PROGRESS task missing acceptance/evidence.
   - Otherwise take next READY task with deps satisfied.
5) Never redo DONE unless:
   - gates now fail, or
   - evidence is missing.
6) After each accepted taskcard:
   - checkpoint status board copy into `reports/swarm_implementation/<TS>/checkpoints/`
   - record head into `reports/swarm_implementation/<TS>/checkpoints/`
