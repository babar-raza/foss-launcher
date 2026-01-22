# Site and Workflow Repos (hardcoded defaults)

## Purpose
This system is executed by agents. Agents MUST NOT guess:
- which repositories to clone
- where Markdown content must be created/updated
- where workflow scripts live (for validation, build, and checks)

This spec hardcodes the canonical repositories and their required local clone locations under `RUN_DIR`.

> **Binding:** If `run_config` does not override these values, agents MUST use the defaults below.

---

## Canonical repositories (binding defaults)

### 1) Content + themes (site repo)
- **Repo URL (default):** `https://github.com/Aspose/aspose.org`
- **Role:** Hugo site repository containing `content/`, `configs/`, `themes/`, etc.
- **Local clone (required):** `RUN_DIR/work/site/`

### 2) GitHub workflows (workflows repo)
- **Repo URL (default):** `https://github.com/Aspose/aspose.org-workflows`
- **Role:** Shared workflow scripts and gate runners used by CI and by this launcher for deterministic validation.
- **Local clone (required):** `RUN_DIR/work/workflows/`
- **Read-only:** workflows repo MUST be treated as read-only; the launcher may execute scripts from it, but must not modify it during runs.

---

## run_config override fields
If a run needs forks or feature branches, it MAY override:

- `site_repo_url`, `site_ref`
- `workflows_repo_url`, `workflows_ref`

**Binding rule:** All overrides MUST be recorded into `RUN_DIR/artifacts/site_context.json` (resolved SHAs + fingerprints).

---

## Where agents create and update Markdown files (binding)

All content changes MUST happen inside the **site repo clone**:

- `RUN_DIR/work/site/content/...`

The exact content folder layout is defined in:
- `specs/18_site_repo_layout.md`

**Binding rule:** Agents MUST create `.md` files only under the section roots computed by that contract
(e.g., `content/docs.aspose.org/<family>/<locale>/...`), and MUST refuse any patch outside `run_config.allowed_paths`.

---

## Where agents tweak configs (rare, guarded)
Hugo config changes are high-risk and MUST be opt-in.

Default:
- Hugo configs are **read-only inputs** for planning and validation.
- The launcher should not modify them.

If a run explicitly allows config edits, it MUST:
- include `RUN_DIR/work/site/configs/**` inside `run_config.allowed_paths`
- include a justification in `RUN_DIR/reports/diff_report.md`
- record all config file fingerprints before and after in `site_context.json`

---

## Workflow script entrypoints (binding search order)
When running gates, the system MUST prefer workflow-provided scripts when present.

Search order (first match wins):
1) `RUN_DIR/work/workflows/scripts/gates/<gate_name>.*`
2) `RUN_DIR/work/workflows/gates/<gate_name>.*`
3) Launcher-native implementation (fallback)

The chosen entrypoint MUST be recorded in `validation_report.gates[].command`.

---

## Acceptance
- Agents can run end-to-end without guessing repo URLs or where to write content.
- The run folder always contains both clones (`work/site` and `work/workflows`).
- All resolved SHAs and config fingerprints are captured in `site_context.json`.
