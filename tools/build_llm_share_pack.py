#!/usr/bin/env python3
"""Build a compact, text-first share pack for handing this repo to another LLM."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import tempfile
import textwrap
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List
from zipfile import ZIP_DEFLATED, ZipFile


SIZE_LIMIT_BYTES = 20 * 1024 * 1024
TRIM_THRESHOLD_BYTES = 500 * 1024
TREE_MAX_DEPTH = 4

STAGE_DIR_NAME = "llm_share_pack"
PRIMARY_ZIP_NAME = "llm_share_pack.zip"
SMALL_ZIP_NAME = "llm_share_pack_small.zip"
MANIFEST_NAME = "llm_share_pack_manifest.json"
REPORT_NAME = "llm_share_pack_report.md"

EXCLUDED_DIR_NAMES = {
    ".git",
    ".venv",
    "node_modules",
    "runs",
    "output",
    "outputs",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".cache",
    "dist",
}

EXCLUDED_PATH_PARTS = {
    ".git",
    ".venv",
    "node_modules",
    "runs",
    "output",
    "outputs",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".cache",
}

TEXT_BINARY_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".svgz",
    ".ico",
    ".pdf",
    ".zip",
    ".gz",
    ".tar",
    ".7z",
    ".exe",
    ".dll",
    ".so",
    ".dylib",
    ".db",
    ".sqlite",
    ".sqlite3",
    ".bin",
    ".woff",
    ".woff2",
    ".ttf",
    ".otf",
}

SECRET_PATTERNS = [
    re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC |DSA |PGP )?PRIVATE KEY-----"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(
        r"(?i)\b(api[_-]?key|secret|token|password)\b\s*[:=]\s*['\"][A-Za-z0-9/_+=.-]{12,}['\"]"
    ),
]


@dataclass(frozen=True)
class PackGroup:
    name: str
    optional: bool
    summary: str
    files: tuple[str, ...]


@dataclass
class CopyRecord:
    source: str
    dest: str
    bytes: int
    mode: str
    group: str
    notes: str = ""


@dataclass
class OmissionRecord:
    path: str
    reason: str
    group: str


GROUPS: tuple[PackGroup, ...] = (
    PackGroup(
        name="root_docs",
        optional=False,
        summary="Top-level repo and packaging docs.",
        files=(
            "README.md",
            "agents.md",
            "pyproject.toml",
        ),
    ),
    PackGroup(
        name="docs_reference",
        optional=True,
        summary="Human-oriented reference docs that explain CLI and runtime contracts.",
        files=(
            "docs/README.md",
            "docs/reference/architecture.md",
            "docs/reference/cli.md",
            "docs/reference/cli_usage.md",
            "docs/reference/config.md",
            "docs/reference/file-contracts.md",
            "docs/reference/heal.md",
            "docs/OPERATOR_TRIAGE.md",
        ),
    ),
    PackGroup(
        name="specs_core",
        optional=False,
        summary="Binding specs for architecture, state, resume, healing, storage, and gates.",
        files=(
            "specs/README.md",
            "specs/00_overview.md",
            "specs/01_system_contract.md",
            "specs/09_validation_gates.md",
            "specs/11_state_and_events.md",
            "specs/21_worker_contracts.md",
            "specs/28_coordination_and_handoffs.md",
            "specs/29_project_repo_structure.md",
            "specs/40_storage_model.md",
            "specs/43_resumable_pipeline.md",
            "specs/48_autopilot_phase_selection.md",
            "specs/50_healing_cost_reduction.md",
            "specs/state-management.md",
            "specs/state-graph.md",
        ),
    ),
    PackGroup(
        name="schemas_core",
        optional=False,
        summary="Schemas for event, snapshot, heal, validation, and phase artifacts.",
        files=(
            "specs/schemas/README.md",
            "specs/schemas/event.schema.json",
            "specs/schemas/snapshot.schema.json",
            "specs/schemas/heal_plan.schema.json",
            "specs/schemas/validation_report.schema.json",
            "specs/schemas/phase_report.schema.json",
            "specs/schemas/run_summary.schema.json",
            "specs/schemas/run_config.schema.json",
        ),
    ),
    PackGroup(
        name="config_core",
        optional=False,
        summary="Pinned toolchain and representative run configuration files.",
        files=(
            "config/toolchain.lock.yaml",
            "config/network_allowlist.yaml",
            "config/markdownlint-cli2.yaml",
            "config/lychee_allowlist.txt",
            "configs/README.md",
            "configs/intake_config.yaml",
            "configs/products/_template.run_config.yaml",
            "configs/pilots/_template.pinned.run_config.yaml",
            "configs/pilots/pilot-aspose-cells-foss-python.yaml",
            "configs/pilots/pilot-aspose-cells-foss-python.resolved.yaml",
            "configs/pilots/pilot-aspose-note-foss-python.resolved.yaml",
            "configs/pilots/README.md",
            "configs/pilots/pilot-aspose-note-foss-python/run_config.pinned.yaml",
        ),
    ),
    PackGroup(
        name="src_core",
        optional=False,
        summary="Runtime source files that define CLI, orchestration, state, heal, and validation.",
        files=(
            "src/launcher/cli/main.py",
            "src/launcher/cli/heal.py",
            "src/launcher/cli/triage.py",
            "src/launcher/autopilot/phase_selector.py",
            "src/launcher/orchestrator/graph.py",
            "src/launcher/orchestrator/phase_executor.py",
            "src/launcher/orchestrator/phase_verifier.py",
            "src/launcher/orchestrator/run_loop.py",
            "src/launcher/validation_engine/adapters.py",
            "src/launcher/validation_engine/context.py",
            "src/launcher/validation_engine/gate_types.py",
            "src/launcher/validation_engine/gates_registry.yaml",
            "src/launcher/validation_engine/registry_loader.py",
            "src/launcher/validation_engine/runner.py",
            "src/launcher/validators/cli.py",
            "src/launcher/workers/w9_validator/worker.py",
            "src/launcher/models/event.py",
            "src/launcher/models/state.py",
            "src/launcher/io/run_layout.py",
            "src/launcher/io/run_lock.py",
            "src/launcher/monitoring/event_tailer.py",
            "src/launcher/observability/run_summary.py",
            "src/launcher/state/__init__.py",
            "src/launcher/state/event_log.py",
            "src/launcher/state/snapshot_manager.py",
            "src/launcher/state_store/store.py",
            "src/launcher/util/path_validation.py",
        ),
    ),
    PackGroup(
        name="worker_runtime",
        optional=False,
        summary="Concrete worker implementations and W9 gate modules where content and fix defects are usually introduced.",
        files=(
            "src/launcher/workers/_shared/**",
            "src/launcher/workers/_git/**",
            "src/launcher/workers/w1_repo_scout/**",
            "src/launcher/workers/w2_facts_builder/**",
            "src/launcher/workers/w3_snippet_curator/**",
            "src/launcher/workers/w4_ia_planner/**",
            "src/launcher/workers/w5_section_writer/**",
            "src/launcher/workers/w6_seo_optimizer/**",
            "src/launcher/workers/w7_content_reviewer/**",
            "src/launcher/workers/w8_linker_and_patcher/**",
            "src/launcher/workers/w9_validator/gates/**",
            "src/launcher/workers/w10_fixer/**",
            "src/launcher/workers/w11_pr_manager/**",
        ),
    ),
    PackGroup(
        name="tools_core",
        optional=False,
        summary="Repo-level governance and validation entrypoints.",
        files=(
            "tools/validate_swarm_ready.py",
            "tools/validate_taskcards.py",
            "tools/validate_mcp_contract.py",
            "tools/validate_untrusted_code_policy.py",
            "tools/extract_validation_gates.py",
            "scripts/run_pilot.py",
            "scripts/validate_plans.py",
            "scripts/validate_spec_pack.py",
        ),
    ),
    PackGroup(
        name="tests_core",
        optional=True,
        summary="Focused tests that show heal, resume, phase, and validation behavior.",
        files=(
            "tests/unit/autopilot/test_phase_selector.py",
            "tests/unit/cli/test_heal.py",
            "tests/unit/cli/test_heal_convergence_e2e.py",
            "tests/unit/cli/test_heal_regression_guard.py",
            "tests/unit/orchestrator/test_resume_from_node.py",
            "tests/unit/test_phase_executor.py",
            "tests/unit/test_phase_report.py",
            "tests/unit/test_phase_verifier.py",
            "tests/unit/test_validation_engine.py",
            "tests/unit/test_validation_engine_golden.py",
            "tests/unit/test_validation_engine_pilot_equivalence.py",
            "tests/unit/workers/w9/test_partial_report.py",
        ),
    ),
    PackGroup(
        name="quality_reviews_baseline",
        optional=False,
        summary="Manual quality reviews of baseline pilot content — the original audit that triggered all quality hardening work.",
        files=(
            "reviews/pilot_content_review_summary.md",
            "reviews/cells_pilot_review.md",
            "reviews/note_pilot_review.md",
        ),
    ),
    PackGroup(
        name="quality_root_cause",
        optional=False,
        summary="Root cause analysis documents tracing defects to specific workers and design gaps.",
        files=(
            "reviews/content_quality_v1.md",
            "reviews/content_quality_v2.md",
            "reviews/content_quality_v3.md",
        ),
    ),
    PackGroup(
        name="quality_reports",
        optional=False,
        summary="Quality metric summaries comparing baseline, phase 1, and phase 2 results.",
        files=(
            "reports/quality/baseline_summary.md",
            "reports/quality/postfix_summary.md",
            "reports/quality/phase2_summary.md",
            "reports/quality/STRUCTURED_LIMITATIONS.md",
            "reports/quality/future_self_focus.md",
        ),
    ),
    PackGroup(
        name="quality_handoffs",
        optional=False,
        summary="Per-workstream handoff docs (WS-B through WS-H) documenting each fix shipped.",
        files=(
            "reports/quality/ws_B_handoff.md",
            "reports/quality/ws_C_handoff.md",
            "reports/quality/ws_D_handoff.md",
            "reports/quality/ws_E_handoff.md",
            "reports/quality/ws_F_handoff.md",
            "reports/quality/ws_G_handoff.md",
            "reports/quality/ws_H_handoff.md",
        ),
    ),
    PackGroup(
        name="quality_metrics",
        optional=False,
        summary="Raw JSON quality metrics from baseline, postfix (phase 1), and phase 2 pilot runs.",
        files=(
            "reports/quality/baseline/cells/quality_metrics.json",
            "reports/quality/baseline/cells/quality_metrics.md",
            "reports/quality/baseline/note/quality_metrics.json",
            "reports/quality/baseline/note/quality_metrics.md",
            "reports/quality/postfix/cells/quality_metrics.json",
            "reports/quality/postfix/cells/quality_metrics.md",
            "reports/quality/postfix/note/quality_metrics.json",
            "reports/quality/postfix/note/quality_metrics.md",
            "reports/quality/phase2/cells/quality_metrics.json",
            "reports/quality/phase2/cells/quality_metrics.md",
            "reports/quality/phase2/note/quality_metrics.json",
            "reports/quality/phase2/note/quality_metrics.md",
        ),
    ),
    PackGroup(
        name="quality_content_samples",
        optional=True,
        summary="Representative baseline content samples showing what defective output looks like.",
        files=(
            "reports/quality/baseline/cells/samples/docs.aspose.org/cells/en/python/installation.md",
            "reports/quality/baseline/cells/samples/docs.aspose.org/cells/en/python/formula-calculation.md",
            "reports/quality/baseline/cells/samples/kb.aspose.org/cells/en/python/faq.md",
            "reports/quality/baseline/cells/samples/reference.aspose.org/cells/en/python/workbook.md",
            "reports/quality/baseline/cells/samples/products.aspose.org/cells/en/python/_index.md",
            "reports/quality/baseline/note/samples/docs.aspose.org/note/en/python/installation.md",
            "reports/quality/baseline/note/samples/docs.aspose.org/note/en/python/feature.md",
            "reports/quality/baseline/note/samples/reference.aspose.org/note/en/python/document.md",
            "reports/quality/baseline/note/samples/products.aspose.org/note/en/python/_index.md",
            "reports/quality/baseline/note/samples/kb.aspose.org/note/en/python/troubleshooting.md",
        ),
    ),
    PackGroup(
        name="quality_specs",
        optional=False,
        summary="Specs that define content quality contracts — evidence model, section templates, sanitization, SEO.",
        files=(
            "specs/03_product_facts_and_evidence.md",
            "specs/07_section_templates.md",
            "specs/08_content_reviewer.md",
            "specs/45_seo_slug_strategy.md",
            "specs/46_content_sanitization_pipeline.md",
        ),
    ),
)

OPTIONAL_REMOVAL_ORDER = ("quality_content_samples", "tests_core", "docs_reference")


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def is_excluded_path(path: Path) -> bool:
    return any(part in EXCLUDED_PATH_PARTS for part in path.parts)


def is_probably_text(path: Path) -> bool:
    if path.suffix.lower() in TEXT_BINARY_SUFFIXES:
        return False
    try:
        with path.open("rb") as handle:
            chunk = handle.read(8192)
    except OSError:
        return False
    return b"\x00" not in chunk


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def trim_text_for_excerpt(text: str) -> str:
    lines = text.splitlines()
    head = lines[:80]
    tail = lines[-80:] if len(lines) > 80 else []
    omitted = max(len(lines) - len(head) - len(tail), 0)
    body = [
        "# EXCERPT",
        "",
        "This file exceeded the 500 KB cap, so only the top and bottom are included.",
        "",
    ]
    body.extend(head)
    if omitted:
        body.extend(["", f"... {omitted} middle line(s) omitted ...", ""])
        body.extend(tail)
    return "\n".join(body).rstrip() + "\n"


def redact_secrets(text: str) -> tuple[str, List[str]]:
    redaction_notes: List[str] = []
    redacted = text
    for pattern in SECRET_PATTERNS:
        if not pattern.search(redacted):
            continue
        if "PRIVATE KEY" in pattern.pattern:
            redacted = pattern.sub("[REDACTED_PRIVATE_KEY]", redacted)
            redaction_notes.append("private_key_block")
            continue

        def _mask(match: re.Match[str]) -> str:
            value = match.group(0)
            redaction_notes.append(pattern.pattern)
            if ":" in value:
                key, _, _ = value.partition(":")
                return f"{key}: [REDACTED]"
            if "=" in value:
                key, _, _ = value.partition("=")
                return f"{key}=[REDACTED]"
            return "[REDACTED_SECRET]"

        redacted = pattern.sub(_mask, redacted)
    return redacted, redaction_notes


def ensure_clean_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def build_tree(root: Path, max_depth: int = TREE_MAX_DEPTH) -> str:
    lines = [
        "Read these areas first:",
        "- START_HERE.md",
        "- QUALITY_JOURNEY.md (for content quality improvement planning)",
        "- ARCHITECTURE.md",
        "- STATE_MACHINE.md",
        "- HEALING_LOOP.md",
        "- GATES_AND_VALIDATION.md",
        "- CONFIG_MAP.md",
        "- reviews/ (baseline quality audits)",
        "- reports/quality/ (metrics and handoffs across phases)",
        "- src/launcher/cli/",
        "- src/launcher/orchestrator/",
        "- src/launcher/workers/",
        "- src/launcher/validation_engine/",
        "- specs/",
        "",
        "Repository tree (depth <= 4, heavy dirs excluded):",
        ".",
    ]

    def _walk(base: Path, prefix: str, depth: int) -> None:
        if depth >= max_depth:
            return
        children = []
        for child in sorted(base.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower())):
            if child.name in EXCLUDED_DIR_NAMES:
                continue
            if child.name.startswith(".") and child.name not in {".foss_state"}:
                continue
            children.append(child)
        for index, child in enumerate(children):
            connector = "`-- " if index == len(children) - 1 else "|-- "
            display = child.name + ("/" if child.is_dir() else "")
            lines.append(f"{prefix}{connector}{display}")
            if child.is_dir():
                extension = "    " if index == len(children) - 1 else "|   "
                _walk(child, prefix + extension, depth + 1)

    _walk(root, "", 0)
    return "\n".join(lines) + "\n"


def relative_stage_entry(path: Path, stage_dir: Path) -> str:
    return path.relative_to(stage_dir).as_posix()


def count_validation_gates(repo: Path) -> int:
    registry = repo / "src" / "launch" / "validation_engine" / "gates_registry.yaml"
    return len(re.findall(r"^\s*-\s+gate_id:", read_text(registry), flags=re.MULTILINE))


def is_glob_pattern(entry: str) -> bool:
    return any(char in entry for char in "*?[]")


def stage_generated_docs(stage_dir: Path, repo: Path) -> List[CopyRecord]:
    gate_count = count_validation_gates(repo)
    generated: List[tuple[str, str]] = []

    generated.append(
        (
            "START_HERE.md",
            textwrap.dedent(
                """\
                # START HERE

                This pack is a compact map of `foss-launcher`: a CLI-driven documentation
                pipeline that runs a fixed worker graph, persists state in `runs/<run_id>/`,
                can resume from any worker, validates output through a canonical gate engine,
                and uses a deterministic heal loop to converge failing runs.

                Recommended reading order:
                1. `QUALITY_JOURNEY.md` — **Start here if planning content quality improvements**
                2. `ARCHITECTURE.md`
                3. `STATE_MACHINE.md`
                4. `HEALING_LOOP.md`
                5. `GATES_AND_VALIDATION.md`
                6. `CONFIG_MAP.md`
                7. `TREE.txt`
                8. `src/launcher/cli/main.py`
                9. `src/launcher/orchestrator/run_loop.py`
                10. `src/launcher/validation_engine/runner.py`

                Mental model:
                - `launch` is the operator-facing front door.
                - `src/launcher/orchestrator/graph.py` is the runtime state machine.
                - `runs/<run_id>/` is the per-run source of truth.
                - `launch resume` and phase execution reuse prior artifacts instead of restarting.
                - `launch_validate` and W9 both call the same gate engine (`run_gates()`).
                - `launch heal` is a bounded controller around triage -> resume -> validate.
                - `.foss_state/` is cross-run cache/state-store data for autopilot reuse.
                - `src/launcher/workers/` contains the actual producer/fixer implementations where many defects originate.

                This bundle intentionally keeps only the files needed to understand those flows.
                Non-core artifacts, caches, run outputs, and bulky logs are omitted.
                """
            ),
        )
    )

    generated.append(
        (
            "ARCHITECTURE.md",
            textwrap.dedent(
                """\
                # ARCHITECTURE

                Purpose:
                `foss-launcher` generates and validates documentation sites from a product/run
                configuration. The codebase is centered on an 11-worker pipeline executed by a
                LangGraph orchestrator, with optional autopilot phase selection and deterministic
                healing for failed validation runs.

                Entrypoints:
                - `launch` -> `src/launcher/cli/main.py`
                - `launch_validate` -> `src/launcher/validators/cli.py`
                - `scripts/run_pilot.py` -> repeatable end-to-end pilot runner

                Main user-facing workflows:
                - `launch run --config ...`: create a fresh `runs/<run_id>/` skeleton and execute W1-W11.
                - `launch resume --run-dir ... --from-worker Wn`: re-enter at a chosen worker using existing artifacts.
                - `launch phase --phase-start Px --phase-end Py`: resume at phase boundaries.
                - `launch drive --config ...`: auto-select earliest safe resume point.
                - `launch validate <run_id>` / `launch_validate runs/<run_id>`: run the canonical validation engine.
                - `launch heal <run_id>`: triage, resume, revalidate, and rollback/checkpoint if needed.

                Worker pipeline:
                - W1 `clone_inputs`
                - W2 `ingest`
                - W3 `build_facts`
                - W4 `plan_pages`
                - W5 `draft_sections`
                - W6 `optimize_seo`
                - W7 `review_content`
                - W8 `link_and_patch`
                - W9 `validate`
                - W10 `fix`
                - W11 `open_pr`

                Phase groups:
                - P1 = W1-W2
                - P2 = W3-W4
                - P3 = W5-W6
                - P4 = W7-W8
                - P5 = W9-W10
                - P6 = W11

                Where configuration lives:
                - Packaging and CLI entrypoints: `pyproject.toml`
                - Tooling pins and allowlists: `config/`
                - Run config templates and resolved configs: `configs/`
                - Binding specs and schemas: `specs/`
                - Validation registry: `src/launcher/validation_engine/gates_registry.yaml`
                - Concrete worker implementations: `src/launcher/workers/`
                """
            ),
        )
    )

    generated.append(
        (
            "STATE_MACHINE.md",
            textwrap.dedent(
                """\
                # STATE MACHINE

                The runtime state machine is implemented in:
                - `src/launcher/orchestrator/graph.py`
                - `src/launcher/orchestrator/run_loop.py`
                - `src/launcher/models/state.py`

                Core run states:
                `CREATED -> CLONED_INPUTS -> INGESTED -> FACTS_READY -> PLAN_READY -> DRAFTING -> DRAFT_READY -> LINKING -> VALIDATING -> FIXING -> READY_FOR_PR -> PR_OPENED -> DONE`

                ASCII view:

                ```text
                CREATED -> CLONED_INPUTS -> INGESTED -> FACTS_READY -> PLAN_READY
                                                       |
                                                       v
                                                  DRAFTING -> DRAFT_READY
                                                                  |
                                                                  v
                                                             LINKING -> VALIDATING
                                                                          |
                                                               +----------+---------+
                                                               |                    |
                                                               v                    v
                                                            FIXING             READY_FOR_PR
                                                               |                    |
                                                               +----------+---------+
                                                                          |
                                                                          v
                                                                       PR_OPENED
                                                                          |
                                                                          v
                                                                         DONE

                Any node may transition to FAILED. Operator cancel forces CANCELLED.
                ```

                Disk-truth state files:
                - `runs/<run_id>/run_config.yaml`
                - `runs/<run_id>/events.ndjson`
                - `runs/<run_id>/snapshot.json`
                - `runs/<run_id>/telemetry_outbox.jsonl`
                - `runs/<run_id>/artifacts/run_summary.json`
                - `runs/<run_id>/artifacts/validation_report.json`
                - `runs/<run_id>/artifacts/heal_plan.json`

                Resume semantics:
                - `launch resume` keeps the same `run_id` and appends `RUN_RESUMED`.
                - `execute_run_from_node()` validates required upstream artifacts first.
                - Earlier-worker artifacts are preserved; the selected worker and downstream outputs can be overwritten.
                - `snapshot.json` is rewritten as resumed state transitions are replayed.
                - `.foss_state/` is separate, cross-run cache/state, not per-run truth.
                """
            ),
        )
    )

    generated.append(
        (
            "HEALING_LOOP.md",
            textwrap.dedent(
                """\
                # HEALING LOOP

                The heal loop is implemented primarily in:
                - `src/launcher/cli/heal.py`
                - `src/launcher/cli/triage.py`
                - `src/launcher/orchestrator/run_loop.py`
                - `src/launcher/validation_engine/runner.py`
                - Downstream repair targets in `src/launcher/workers/` (especially W5-W10)

                Control loop:
                1. Read `artifacts/validation_report.json` from disk.
                2. Rank open issues and pick a recommended repair entry point.
                3. Choose a worker with regression and stuck guards.
                4. Create a checkpoint before mutating downstream content.
                5. Resume from the chosen worker.
                6. Re-run validation through the canonical engine.
                7. Compare before/after metrics.
                8. If the run regressed, restore from checkpoint.
                9. Persist `artifacts/heal_plan.json` and append heal events.

                Important functions and classes:
                - `HealStep`, `HealResult`
                - `compute_report_metrics()`
                - `choose_worker()`
                - `_create_checkpoint()`
                - `_restore_checkpoint()`
                - `write_heal_plan()`
                - `run_heal_loop()`
                - `recommend_action()` in `src/launcher/cli/triage.py`
                """
            ),
        )
    )

    generated.append(
        (
            "GATES_AND_VALIDATION.md",
            textwrap.dedent(
                f"""\
                # GATES AND VALIDATION

                Validation exists at two levels:

                1. Repo preflight / swarm-readiness
                   - Entry: `tools/validate_swarm_ready.py`
                   - Scope: taskcards, specs, links, secrets, pinning, allowlists, policy gates

                2. Per-run content validation
                   - Entries: `launch validate <run_id>` and `launch_validate runs/<run_id>`
                   - Runtime: `src/launcher/validators/cli.py` -> `src/launcher/validation_engine/runner.py`
                   - Registry: `src/launcher/validation_engine/gates_registry.yaml`
                   - Registry gate count: {gate_count}
                   - Output: `runs/<run_id>/artifacts/validation_report.json`
                   - Concrete gate implementations are copied under `src/launcher/workers/w9_validator/gates/`

                Key mechanics:
                - W9 and `launch_validate` share the same `run_gates()` implementation.
                - Gate order, adapters, skip behavior, and profile requirements are registry-driven.
                - `validation_report.json` contains `ok`, `profile`, `gates`, `issues`, `generation_id`, and `content_hash`.
                - W9 also emits `work/quality_feedback.json`.

                Where failures feed into healing:
                - `launch heal` loads `validation_report.json`.
                - `src/launcher/cli/triage.py` ranks issues and suggests a resume worker.
                - `src/launcher/cli/heal.py` executes the repair and compares the next report to the previous one.
                - Regressions trigger checkpoint restore.

                The YAML registry is the operational source of truth even if a prose spec lags.
                """
            ),
        )
    )

    generated.append(
        (
            "CONFIG_MAP.md",
            textwrap.dedent(
                """\
                # CONFIG MAP

                Core config surfaces:
                - `pyproject.toml`: packaging and console scripts
                - `config/toolchain.lock.yaml`: pinned toolchain versions
                - `config/network_allowlist.yaml`: allowed outbound domains
                - `config/markdownlint-cli2.yaml`: markdown lint config
                - `config/lychee_allowlist.txt`: link-check exceptions
                - `configs/intake_config.yaml`: intake workflow config
                - `configs/products/_template.run_config.yaml`: run config template
                - `configs/pilots/_template.pinned.run_config.yaml`: pilot template
                - `configs/pilots/*.yaml`: local pilot configs
                - `configs/pilots/*/run_config.pinned.yaml`: binding pilot configs
                - `specs/schemas/*.json`: runtime artifact contracts
                - `src/launcher/validation_engine/gates_registry.yaml`: declarative validation behavior
                - `.foss_state/`: cross-run cache keyed by family/platform and repo SHA/signature
                """
            ),
        )
    )

    generated.append(
        (
            "QUALITY_JOURNEY.md",
            textwrap.dedent(
                """\
                # QUALITY JOURNEY — Content Hardening Progress

                ## READ THIS FIRST if you are planning further quality improvements.

                This document summarizes the quality hardening work done across 2 phases and
                8 workstreams (WS-A through WS-H). It tells you what was broken, what was
                fixed, and what still needs fixing.

                ## Timeline

                - **2026-03-01 (Baseline):** Manual review of 60 generated .md files across
                  Cells and Note pilots. Result: 0% publication-ready, 70% D/F grade,
                  390 total defects across 7 systemic defect families (G1-G7).
                  See: `reviews/pilot_content_review_summary.md`

                - **2026-03-01 (Phase 1):** Shipped WS-A through WS-D — 8 new gates (42→50),
                  3 auto-fixers, quality metrics tool.
                  Result: 390→183 issues (-53%), but G2/G3/G7 barely improved.
                  See: `reports/quality/postfix_summary.md`

                - **2026-03-03 (Phase 2):** Shipped WS-E through WS-H — evidence binding
                  overhaul, skeleton-first content, canonical import injection, content cache.
                  Result: 390→60 issues (-85%), A/B rate from 7% to 45%.
                  See: `reports/quality/phase2_summary.md`

                ## The 7 Defect Families (G1-G7)

                | Code | Defect | Baseline | Phase 2 | Reduction |
                |------|--------|----------|---------|-----------|
                | G1 | LLM generation artifacts | 110 | 2 | -98% |
                | G2 | Cross-page content repetition | 27 | 0 | -100% |
                | G3 | Hallucinated/inconsistent APIs | 14 | 4 | -71% |
                | G4 | Structural chaos (heading/section) | 147 | 32 | -78% |
                | G5 | Product name errors | 11 | 4 | -64% |
                | G6 | Permalink/URL collisions | 2 | 9 | +350%* |
                | G7 | Spec-level content leakage | 79 | 9 | -89% |

                *G6 increase is because a new gate now detects issues the baseline had no gate for.

                ## What Was Fixed (and How)

                | Workstream | What It Did | Key Files |
                |------------|-------------|-----------|
                | WS-A (G1) | `remove_llm_artifact_preambles()` auto-fixer | `workers/_shared/content_sanitizer.py` |
                | WS-B (G5) | `canonicalize_product_names()` auto-fixer + gate | `workers/w9_validator/gates/gate_product_name_integrity.py` |
                | WS-C (G4) | `strip_heading_trailing_punct()` + `gate_section_structure` | `workers/w9_validator/gates/gate_section_structure.py` |
                | WS-D | Quality metrics tool (`tools/quality_metrics.py`) | Measures G1-G7 per run |
                | WS-E (G2,G7) | Claim visibility tagging + page-role affinity scoping | `workers/w2_facts_builder/extract_claims.py`, `workers/w4_ia_planner/worker.py` |
                | WS-F (G3,G4) | Skeleton-first content + canonical import injection | `workers/w5_section_writer/page_skeletons.py`, `workers/w5_section_writer/rich_context.py` |
                | WS-G | Reference completeness + topic alignment gates | `workers/w9_validator/gates/gate_reference_completeness.py`, `gate_topic_content_alignment.py` |
                | WS-H | Content cache for section-level LLM output stability | `workers/w5_section_writer/content_cache.py` |

                ## What Still Needs Fixing (Ranked by Severity)

                ### 1. G7 Spec Leakage — Note Pilot (HIGH)
                11 of 28 Note files still contain binary format terms (CompactID, STP, CB,
                stpNext, fcrNil, rgIndices, 0x008, .onetoc2, CRC32, MS-ONESTORE).
                **Root cause:** Claim visibility filter blocks claims tagged "internal" but
                some spec terms are embedded in claims tagged "public." Need a post-classification
                term-level filter.

                ### 2. Title-Content Mismatch — Cells Pilot (HIGH)
                5+ Cells how-to files have titles about one topic but content about another
                (e.g., "Convert Formats" page about Agile encryption).
                **Root cause:** W4 assigns claims by TF-IDF similarity, but when one topic
                dominates, it crowds out the assigned page topic.

                ### 3. G4 Trailing Periods on Headings (MEDIUM)
                ~15 files have `## See Also.`, `## Comparison.` with trailing periods.
                **Root cause:** `strip_heading_trailing_punct()` fixer may not match all
                patterns or W10 routing isn't dispatching G4 issues to the fixer.

                ### 4. G3 Import Inconsistency — Note KB Files (MEDIUM)
                4 Note KB how-to files use `from onenote import` instead of
                `from aspose.note import`.
                **Root cause:** Canonical import derivation chain may not resolve for all
                page types, or W5 system prompt constraint is overridden by the LLM.

                ### 5. Duplicate See Also Sections (LOW)
                ~4 files have two `## See Also` sections with different link sets.
                **Root cause:** W5 skeleton emits See Also, then W6/W10 appends another one.

                ## Key Files for Planning Next Steps

                **Reviews (read these to understand the defects):**
                - `reviews/pilot_content_review_summary.md` — aggregate baseline audit
                - `reviews/cells_pilot_review.md` — per-file grades and defects (Cells)
                - `reviews/note_pilot_review.md` — per-file grades and defects (Note)
                - `reviews/content_quality_v3.md` — deepest root cause analysis

                **Metrics (quantified improvement across phases):**
                - `reports/quality/phase2_summary.md` — 3-way comparison table
                - `reports/quality/phase2/*/quality_metrics.json` — raw per-gate counts

                **Handoffs (what each workstream shipped):**
                - `reports/quality/ws_{B..H}_handoff.md` — one per workstream

                **Source code (where defects originate and are fixed):**
                - `src/launcher/workers/w2_facts_builder/extract_claims.py` — claim visibility
                - `src/launcher/workers/w4_ia_planner/worker.py` — claim scoping + affinity
                - `src/launcher/workers/w5_section_writer/` — content generation (skeletons, imports, cache)
                - `src/launcher/workers/w7_content_reviewer/` — semantic accuracy checks
                - `src/launcher/workers/w9_validator/gates/` — all 50 validation gates
                - `src/launcher/workers/w10_fixer/worker.py` — auto-fix dispatch
                - `src/launcher/workers/_shared/content_sanitizer.py` — shared content cleaning

                **Specs (contracts that define correct behavior):**
                - `specs/03_product_facts_and_evidence.md` — evidence model
                - `specs/07_section_templates.md` — page role templates
                - `specs/08_content_reviewer.md` — W7 review contract
                - `specs/09_validation_gates.md` — gate definitions
                - `specs/46_content_sanitization_pipeline.md` — sanitizer pipeline

                **Content samples (what defective output looks like):**
                - `reports/quality/baseline/*/samples/` — actual baseline .md files with defects
                """
            ),
        )
    )

    generated.append(("TREE.txt", build_tree(repo)))

    records: List[CopyRecord] = []
    for name, content in generated:
        target = stage_dir / name
        target.write_text(content, encoding="utf-8")
        records.append(
            CopyRecord(
                source="[generated]",
                dest=name,
                bytes=target.stat().st_size,
                mode="generated",
                group="generated_docs",
            )
        )
    return records


def copy_selected_files(
    repo: Path,
    stage_dir: Path,
    selected_group_names: set[str],
) -> tuple[List[CopyRecord], List[OmissionRecord], List[dict[str, str]]]:
    records: List[CopyRecord] = []
    omissions: List[OmissionRecord] = []
    redactions: List[dict[str, str]] = []
    seen_sources: set[str] = set()

    for group in GROUPS:
        if group.name not in selected_group_names:
            continue
        group_name = group.name
        for rel in group.files:
            if is_glob_pattern(rel):
                matches = sorted(
                    path
                    for path in repo.glob(rel)
                    if path.is_file() and not is_excluded_path(path.relative_to(repo))
                )
                if not matches:
                    omissions.append(OmissionRecord(path=rel, reason="glob_no_matches", group=group_name))
                    continue
            else:
                source = repo / rel
                if not source.exists():
                    omissions.append(OmissionRecord(path=rel, reason="missing", group=group_name))
                    continue
                if source.is_dir():
                    omissions.append(
                        OmissionRecord(path=rel, reason="directory_not_supported", group=group_name)
                    )
                    continue
                matches = [source]

            for source in matches:
                rel_source = source.relative_to(repo).as_posix()
                if rel_source in seen_sources:
                    continue
                seen_sources.add(rel_source)

                if is_excluded_path(source.relative_to(repo)):
                    omissions.append(OmissionRecord(path=rel_source, reason="excluded_path", group=group_name))
                    continue
                if not is_probably_text(source):
                    omissions.append(OmissionRecord(path=rel_source, reason="non_text", group=group_name))
                    continue

                text = read_text(source)
                mode = "full"
                notes = ""
                if source.stat().st_size > TRIM_THRESHOLD_BYTES:
                    text = trim_text_for_excerpt(text)
                    mode = "excerpt"
                    notes = "trimmed_for_size"

                text, redaction_notes = redact_secrets(text)
                if redaction_notes:
                    mode = "redacted" if mode == "full" else f"{mode}+redacted"
                    notes = ",".join(sorted(set(redaction_notes)))
                    redactions.append(
                        {
                            "path": rel_source,
                            "patterns": ",".join(sorted(set(redaction_notes))),
                        }
                    )

                target = stage_dir / rel_source
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(text, encoding="utf-8")
                records.append(
                    CopyRecord(
                        source=rel_source,
                        dest=rel_source,
                        bytes=target.stat().st_size,
                        mode=mode,
                        group=group_name,
                        notes=notes,
                    )
                )

    return records, omissions, redactions


def stage_size_bytes(stage_dir: Path) -> int:
    return sum(path.stat().st_size for path in stage_dir.rglob("*") if path.is_file())


def zip_stage(stage_dir: Path, zip_path: Path) -> int:
    if zip_path.exists():
        zip_path.unlink()
    with ZipFile(zip_path, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for file_path in sorted(path for path in stage_dir.rglob("*") if path.is_file()):
            arcname = f"{stage_dir.name}/{relative_stage_entry(file_path, stage_dir)}"
            archive.write(file_path, arcname=arcname)
    return zip_path.stat().st_size


def build_variant(
    repo: Path,
    stage_dir: Path,
    selected_group_names: set[str],
) -> tuple[List[CopyRecord], List[OmissionRecord], List[dict[str, str]], int]:
    ensure_clean_dir(stage_dir)
    records = stage_generated_docs(stage_dir, repo)
    copied, omissions, redactions = copy_selected_files(repo, stage_dir, selected_group_names)
    records.extend(copied)
    return records, omissions, redactions, stage_size_bytes(stage_dir)


def ordered_group_names(selected_group_names: set[str]) -> List[str]:
    return [group.name for group in GROUPS if group.name in selected_group_names]


def build_small_variant(
    repo: Path,
    selected_group_names: set[str],
    dist_dir: Path,
) -> tuple[dict | None, List[str]]:
    working = set(selected_group_names)
    removed: List[str] = []
    small_zip_path = dist_dir / SMALL_ZIP_NAME
    if small_zip_path.exists():
        small_zip_path.unlink()

    for group_name in OPTIONAL_REMOVAL_ORDER:
        if group_name not in working:
            continue
        working.remove(group_name)
        removed.append(group_name)
        with tempfile.TemporaryDirectory(prefix="llm-share-pack-") as tmp:
            tmp_stage = Path(tmp) / STAGE_DIR_NAME
            records, omissions, redactions, stage_bytes = build_variant(repo, tmp_stage, working)
            zip_bytes = zip_stage(tmp_stage, small_zip_path)
            if zip_bytes <= SIZE_LIMIT_BYTES:
                return (
                    {
                        "path": small_zip_path.as_posix(),
                        "bytes": zip_bytes,
                        "stage_bytes": stage_bytes,
                        "removed_groups": removed,
                        "included_groups": ordered_group_names(working),
                        "included_files": len(records),
                        "omitted_files": len(omissions),
                        "redaction_count": len(redactions),
                    },
                    removed,
                )

    if small_zip_path.exists():
        small_zip_path.unlink()
    return None, removed


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_report(path: Path, manifest: dict) -> None:
    primary = manifest["primary_zip"]
    small = manifest.get("small_zip")
    redactions = manifest.get("redactions", [])
    omitted = manifest.get("omitted_files", [])
    lines = [
        "# LLM Share Pack Report",
        "",
        "## What This Pack Contains",
        "",
        "This pack is a small, text-first orientation bundle for understanding the runtime",
        "architecture, state machine, resume behavior, validation engine, and heal loop.",
        "It excludes caches, run outputs, binaries, and unrelated bulk files so it stays",
        "easy to upload to another LLM.",
        "",
        "Included groups:",
    ]
    for group in manifest["included_groups"]:
        lines.append(f"- {group['name']}: {group['summary']}")

    lines.extend(
        [
            "",
            "## Size",
            "",
            f"- Stage directory: `{manifest['stage_dir']}` ({manifest['stage_bytes']} bytes)",
            f"- Primary zip: `{primary['path']}` ({primary['bytes']} bytes)",
        ]
    )
    if small:
        lines.append(f"- Smaller fallback zip: `{small['path']}` ({small['bytes']} bytes)")
        if small.get("removed_groups"):
            lines.append(f"- Small variant removed: {', '.join(small['removed_groups'])}")

    lines.extend(
        [
            "",
            "## How To Read It",
            "",
            "1. Open `START_HERE.md`.",
            "2. Read `ARCHITECTURE.md`, `STATE_MACHINE.md`, and `HEALING_LOOP.md`.",
            "3. Use `GATES_AND_VALIDATION.md` and `CONFIG_MAP.md` as indexes.",
            "4. Use `TREE.txt` to branch into the copied specs, code, tools, and tests.",
            "",
            "## Exclusions",
            "",
            "- Heavy directories are excluded by default: `.git/`, `.venv/`, `node_modules/`, `runs/`, `output/`, caches, and unrelated `dist/` contents.",
            "- Only curated text-first files are copied. Non-text files are omitted.",
            "- Files above 500 KB are trimmed to excerpts instead of copied whole.",
        ]
    )

    if redactions:
        lines.extend(["", "## Redactions", ""])
        for redaction in redactions:
            lines.append(
                f"- `{redaction['path']}` redacted for pattern(s): `{redaction['patterns']}`"
            )
    else:
        lines.extend(["", "## Redactions", "", "- No likely secrets were found in copied files."])

    lines.extend(["", "## Notable Omissions", ""])
    if omitted:
        preview = omitted[:15]
        for entry in preview:
            lines.append(f"- `{entry['path']}` omitted ({entry['reason']})")
        if len(omitted) > len(preview):
            lines.append(
                f"- ... plus {len(omitted) - len(preview)} more omitted item(s) listed in the manifest."
            )
    else:
        lines.append("- No requested files were omitted.")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_manifest(
    repo: Path,
    stage_dir: Path,
    records: List[CopyRecord],
    omissions: List[OmissionRecord],
    redactions: List[dict[str, str]],
    primary_zip_bytes: int,
    small_zip: dict | None,
    selected_group_names: set[str],
) -> dict:
    return {
        "schema_version": "1.0",
        "generated_at_utc": utc_now(),
        "repo_root": str(repo),
        "stage_dir": stage_dir.as_posix(),
        "stage_bytes": stage_size_bytes(stage_dir),
        "excluded_patterns": [
            ".git/",
            ".venv/",
            "node_modules/",
            "runs/",
            "output/",
            "outputs/",
            "__pycache__/",
            ".pytest_cache/",
            ".mypy_cache/",
            ".ruff_cache/",
            ".cache/",
            "dist/ (except this share-pack output)",
            "binary files",
        ],
        "included_groups": [
            {
                "name": group.name,
                "optional": group.optional,
                "summary": group.summary,
            }
            for group in GROUPS
            if group.name in selected_group_names
        ],
        "included_files": [
            {
                "source": record.source,
                "dest": record.dest,
                "bytes": record.bytes,
                "mode": record.mode,
                "group": record.group,
                "notes": record.notes,
            }
            for record in sorted(records, key=lambda item: item.dest)
        ],
        "omitted_files": [
            {
                "path": item.path,
                "reason": item.reason,
                "group": item.group,
            }
            for item in omissions
        ],
        "redactions": redactions,
        "primary_zip": {
            "path": (stage_dir.parent / PRIMARY_ZIP_NAME).as_posix(),
            "bytes": primary_zip_bytes,
        },
        "small_zip": small_zip,
    }


def main() -> int:
    repo = repo_root()
    dist_dir = repo / "dist"
    stage_dir = dist_dir / STAGE_DIR_NAME
    manifest_path = dist_dir / MANIFEST_NAME
    report_path = dist_dir / REPORT_NAME
    primary_zip_path = dist_dir / PRIMARY_ZIP_NAME

    dist_dir.mkdir(parents=True, exist_ok=True)

    selected_group_names = {group.name for group in GROUPS}
    records, omissions, redactions, _ = build_variant(repo, stage_dir, selected_group_names)
    primary_zip_bytes = zip_stage(stage_dir, primary_zip_path)

    small_zip, removed_groups = (None, [])
    if primary_zip_bytes > SIZE_LIMIT_BYTES:
        small_zip, removed_groups = build_small_variant(repo, selected_group_names, dist_dir)

    manifest = build_manifest(
        repo=repo,
        stage_dir=stage_dir,
        records=records,
        omissions=omissions,
        redactions=redactions,
        primary_zip_bytes=primary_zip_bytes,
        small_zip=small_zip,
        selected_group_names=selected_group_names,
    )
    if removed_groups and small_zip is not None:
        manifest["size_control"] = {
            "primary_exceeded_limit": True,
            "limit_bytes": SIZE_LIMIT_BYTES,
            "small_variant_removed_groups": removed_groups,
        }
    else:
        manifest["size_control"] = {
            "primary_exceeded_limit": False,
            "limit_bytes": SIZE_LIMIT_BYTES,
        }

    write_json(manifest_path, manifest)
    write_report(report_path, manifest)

    print(f"Stage directory: {stage_dir}")
    print(f"Primary zip: {primary_zip_path} ({primary_zip_bytes} bytes)")
    if small_zip:
        print(f"Small zip: {small_zip['path']} ({small_zip['bytes']} bytes)")
    print(f"Manifest: {manifest_path}")
    print(f"Report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
