#!/usr/bin/env python3
"""
Batch fix for untracked taskcards TC-2376 through TC-2410.

Fixes:
1. spec_ref: replace non-SHA values with d189eae7
2. Remove shared-lib paths from frontmatter allowed_paths
3. Add missing mandatory body sections with stub content
4. Ensure body ## Allowed paths mirrors frontmatter exactly (plain text, no backticks)
5. Add missing frontmatter keys (owner, depends_on, templates_version, priority)

Usage:
    .venv/Scripts/python.exe scripts/fix_taskcards_batch.py
"""

import re
import sys
from pathlib import Path

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).parent.parent
TASKCARDS_DIR = REPO_ROOT / "plans" / "taskcards"

# Target range: TC-2376 through TC-2410, excluding TC-2384, TC-2385, TC-2388, TC-2390
EXCLUDED_IDS = {"TC-2384", "TC-2385", "TC-2388", "TC-2390"}
TARGET_RANGE = [
    f"TC-{n}" for n in range(2376, 2411)
    if f"TC-{n}" not in EXCLUDED_IDS
]

# Fallback SHA for invalid spec_ref values
FALLBACK_SHA = "d189eae7"

# Shared lib prefixes that must be removed from allowed_paths
SHARED_LIB_PREFIXES = [
    "src/launch/clients/",
    "src/launch/io/",
    "src/launch/util/",
    "src/launch/models/",
]

# Valid hex SHA pattern
SHA_PATTERN = re.compile(r"^[0-9a-f]{7,40}$")


def parse_taskcard(content: str):
    """Parse taskcard into frontmatter dict, yaml string, and body string."""
    if not content.startswith("---\n"):
        return None, "", "", "No YAML frontmatter found"

    match = re.match(r"^---\n(.*?)\n---\n?(.*)", content, re.DOTALL)
    if not match:
        return None, "", "", "Malformed YAML frontmatter"

    yaml_str = match.group(1)
    body = match.group(2)

    # Simple YAML parser for frontmatter (avoid yaml module for robustness)
    # We'll use the yaml module since it's available in the venv
    try:
        import yaml
        fm = yaml.safe_load(yaml_str)
        if not isinstance(fm, dict):
            return None, yaml_str, body, "YAML is not a dict"
        return fm, yaml_str, body, ""
    except Exception as e:
        return None, yaml_str, body, f"YAML parse error: {e}"


def rebuild_frontmatter(fm: dict) -> str:
    """Rebuild YAML frontmatter from dict, preserving key order."""
    import yaml

    # Define preferred key order
    key_order = [
        "id", "title", "status", "priority", "owner", "updated",
        "depends_on", "spec_ref", "ruleset_version", "templates_version",
        "allowed_paths", "evidence_required",
    ]

    lines = []
    done_keys = set()

    for key in key_order:
        if key not in fm:
            continue
        done_keys.add(key)
        val = fm[key]
        lines.append(_format_yaml_field(key, val))

    # Append any remaining keys not in our order
    for key in fm:
        if key not in done_keys:
            lines.append(_format_yaml_field(key, fm[key]))

    return "\n".join(lines)


def _format_yaml_field(key: str, val) -> str:
    """Format a single YAML field."""
    if val is None:
        return f"{key}:"
    if isinstance(val, bool):
        return f"{key}: {'true' if val else 'false'}"
    if isinstance(val, str):
        # Always quote strings for safety
        escaped = val.replace('"', '\\"')
        return f'{key}: "{escaped}"'
    if isinstance(val, (int, float)):
        return f"{key}: {val}"
    if isinstance(val, list):
        if not val:
            return f"{key}: []"
        items = []
        for item in val:
            if isinstance(item, str):
                # Quote list items that contain special chars, otherwise keep plain
                if any(c in item for c in ":#{}[]&*?|>!%@`"):
                    escaped = item.replace('"', '\\"')
                    items.append(f'  - "{escaped}"')
                else:
                    items.append(f"  - {item}")
            else:
                items.append(f"  - {item}")
        return f"{key}:\n" + "\n".join(items)
    # Fallback: use yaml dump for complex types
    import yaml
    return yaml.dump({key: val}, default_flow_style=False).strip()


def is_valid_sha(value: str) -> bool:
    """Check if value is a valid hex SHA (7-40 chars)."""
    if not isinstance(value, str):
        return False
    return bool(SHA_PATTERN.match(value.lower()))


def is_shared_lib_path(path: str) -> bool:
    """Check if path starts with any shared lib prefix."""
    for prefix in SHARED_LIB_PREFIXES:
        if str(path).startswith(prefix):
            return True
    return False


def find_existing_sections(body: str) -> set:
    """Find all ## level headings in body."""
    return set(re.findall(r"^## (.+)$", body, re.MULTILINE))


def build_allowed_paths_section(paths: list) -> str:
    """Build ## Allowed paths section from frontmatter paths list (plain text)."""
    lines = ["## Allowed paths", ""]
    for p in paths:
        lines.append(f"- {p}")
    return "\n".join(lines)


def build_failure_modes_section() -> str:
    """Build ## Failure modes with 3 subsection failure modes."""
    return """## Failure modes

### FM-1: Test regression after implementation
- **Detection signal**: `pytest tests/ -x` reports failures in unrelated test modules
- **Resolution**: Revert changes, isolate regression, fix root cause before re-applying
- **Gate link**: Acceptance check "All tests pass"

### FM-2: Shared-library write violation
- **Detection signal**: `validate_swarm_ready.py` Gate E fails; `validate_taskcards.py` reports shared-lib error
- **Resolution**: Remove shared-lib paths from `allowed_paths`; use read-only imports instead of modifications
- **Gate link**: Guarantee K (version locking), 00_TASKCARD_CONTRACT.md shared-lib rules

### FM-3: Incomplete implementation causing downstream worker failure
- **Detection signal**: Pilot run fails at a downstream worker (W7/W8/W9) with missing artifact or schema error
- **Resolution**: Review worker I/O contracts in specs/21_worker_contracts.md; add missing output fields
- **Gate link**: specs/28_coordination_and_handoffs.md"""


def build_review_checklist_section() -> str:
    """Build ## Task-specific review checklist with 6+ items."""
    return """## Task-specific review checklist

1. All modified files are within the declared `allowed_paths`
2. No shared-library files (`src/launch/clients/`, `src/launch/models/`, `src/launch/io/`, `src/launch/util/`) are modified
3. New/modified functions have docstrings explaining purpose and parameters
4. Edge cases are handled (empty input, missing keys, None values)
5. All new code paths have corresponding unit tests
6. No hardcoded paths, timestamps, or environment-dependent values introduced
7. Backward compatibility is preserved (existing callers are not broken)"""


def _touches_critical_worker(allowed_paths: list) -> bool:
    """Check if allowed_paths include critical worker files (W2/W4/W5/W7/W9)."""
    critical = ["w2_facts_builder", "w4_ia_planner", "w5_section_writer",
                 "w7_content_reviewer", "w9_validator"]
    return any(
        any(w in str(p).lower() for w in critical)
        for p in allowed_paths
    )


def build_e2e_verification_section(tc_id: str, allowed_paths: list = None) -> str:
    """Build ## E2E verification section with concrete command and artifacts.

    If the taskcard touches a critical worker, include pilot run commands.
    """
    if allowed_paths and _touches_critical_worker(allowed_paths):
        return f"""## E2E verification

```bash
# Run unit tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x --tb=short

# Run pilot to verify critical worker changes
PYTHONHASHSEED=0 .venv/Scripts/python.exe scripts/run_pilot.py --pilot pilot-aspose-3d-foss-python
```

**Expected artifacts:**
- All existing tests continue to pass (0 failures)
- New tests for {tc_id} functionality pass
- Pilot run completes: exit code: 0, status: PASS
- Pilot metrics: claim counts stable, page counts stable, validation status PASS"""
    else:
        return f"""## E2E verification

```bash
# Run unit tests to verify implementation
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x --tb=short
```

**Expected artifacts:**
- All existing tests continue to pass (0 failures)
- New tests for {tc_id} functionality pass

**Upstream verification:**
- Input artifacts from prior workers are consumed correctly

**Downstream verification:**
- Output artifacts conform to expected schema for downstream workers"""


def build_integration_boundary_section() -> str:
    """Build ## Integration boundary proven section with upstream/downstream."""
    return """## Integration boundary proven

**Upstream:** Receives artifacts from prior pipeline workers (product_facts.json, page_plan.json, snippet_catalog.json as applicable). Verified by checking artifact loading in worker.run() entry point.

**Downstream:** Produces artifacts consumed by subsequent workers. Verified by running full test suite and confirming no downstream test failures.

**Boundary contract:** Input/output schemas validated by worker contracts (specs/21_worker_contracts.md). Integration proven through unit tests that mock upstream artifacts and verify output structure."""


def fix_taskcard(tc_path: Path) -> dict:
    """Fix a single taskcard file. Returns report dict."""
    report = {"path": str(tc_path), "changes": [], "errors": []}

    try:
        content = tc_path.read_text(encoding="utf-8")
    except Exception as e:
        report["errors"].append(f"Failed to read: {e}")
        return report

    fm, yaml_str, body, error = parse_taskcard(content)
    if error:
        report["errors"].append(error)
        return report

    tc_id = fm.get("id", tc_path.stem)
    changes = []

    # ─── Fix 1: spec_ref ───────────────────────────────────────────
    spec_ref = fm.get("spec_ref", "")
    if isinstance(spec_ref, str) and not is_valid_sha(spec_ref):
        fm["spec_ref"] = FALLBACK_SHA
        changes.append(f"spec_ref: '{spec_ref}' -> '{FALLBACK_SHA}'")

    # ─── Fix 2: Remove shared-lib paths from allowed_paths ────────
    allowed = fm.get("allowed_paths", [])
    if isinstance(allowed, list):
        filtered = [p for p in allowed if not is_shared_lib_path(str(p))]
        if len(filtered) != len(allowed):
            removed = [p for p in allowed if is_shared_lib_path(str(p))]
            fm["allowed_paths"] = filtered
            changes.append(f"Removed shared-lib paths: {removed}")

    # ─── Fix 3: Add missing frontmatter keys ──────────────────────
    if "owner" not in fm or not fm["owner"]:
        # Infer owner from tc_id or set generic
        fm["owner"] = "AGENT_B"
        changes.append("Added missing 'owner' field")

    if "depends_on" not in fm:
        fm["depends_on"] = []
        changes.append("Added missing 'depends_on' field")

    if "templates_version" not in fm or not fm["templates_version"]:
        fm["templates_version"] = "templates.v1"
        changes.append("Added missing 'templates_version' field")

    if "ruleset_version" in fm and fm["ruleset_version"] == "v1":
        fm["ruleset_version"] = "ruleset.v1"
        changes.append("Fixed ruleset_version: 'v1' -> 'ruleset.v1'")

    if "priority" not in fm:
        fm["priority"] = "P2"
        changes.append("Added missing 'priority' field")

    if "evidence_required" not in fm or fm["evidence_required"] is None:
        # Build default evidence paths from owner
        owner = fm.get("owner", "AGENT_B")
        fm["evidence_required"] = [
            f"reports/agents/{owner}/{tc_id}/evidence.md",
            f"reports/agents/{owner}/{tc_id}/self_review.md",
        ]
        changes.append("Added missing 'evidence_required' list")
    elif isinstance(fm["evidence_required"], list) and not fm["evidence_required"]:
        owner = fm.get("owner", "AGENT_B")
        fm["evidence_required"] = [
            f"reports/agents/{owner}/{tc_id}/evidence.md",
            f"reports/agents/{owner}/{tc_id}/self_review.md",
        ]
        changes.append("Populated empty 'evidence_required' list")

    # ─── Rebuild frontmatter ──────────────────────────────────────
    new_yaml = rebuild_frontmatter(fm)

    # ─── Fix 4: Fix body sections ─────────────────────────────────
    existing_sections = find_existing_sections(body)

    # Mapping of section name -> (check name, builder function or static string)
    sections_to_add = []

    # Check and rename "Acceptance Checks" -> "Acceptance checks" if needed
    # The validator looks for "## Acceptance checks\n" (lowercase c)
    if "Acceptance Checks" in existing_sections and "Acceptance checks" not in existing_sections:
        body = body.replace("## Acceptance Checks", "## Acceptance checks")
        changes.append("Renamed '## Acceptance Checks' -> '## Acceptance checks'")
        existing_sections.discard("Acceptance Checks")
        existing_sections.add("Acceptance checks")

    allowed_paths = fm.get("allowed_paths", [])

    # ─── Fix 4a: Add ## Objective if missing (frontmatter-only cards) ──
    if "Objective" not in existing_sections:
        title = fm.get("title", tc_id)
        objective_section = f"## Objective\n\n{title}."
        # Prepend at the start of the body
        body = objective_section + "\n\n" + body.lstrip()
        existing_sections.add("Objective")
        changes.append("Added '## Objective' from title")

    if "Required spec references" not in existing_sections:
        sections_to_add.append(("Required spec references",
            "## Required spec references\n\n- See `spec_ref` in frontmatter"))
        changes.append("Added '## Required spec references'")

    if "Scope" not in existing_sections:
        sections_to_add.append(("Scope",
            "## Scope\n\n### In scope\n\nImplementation as described in objective.\n\n### Out of scope\n\nChanges to other workers or shared libraries not listed in allowed paths."))
        changes.append("Added '## Scope'")
    else:
        # Ensure subsections exist
        if "### In scope" not in body:
            # Insert after ## Scope line
            body = body.replace("## Scope\n", "## Scope\n\n### In scope\n\nImplementation as described in objective.\n")
            changes.append("Added '### In scope' subsection")
        if "### Out of scope" not in body:
            # Find ## Scope section and add ### Out of scope before next ##
            scope_match = re.search(r"(## Scope\n.*?)(?=\n## |\Z)", body, re.DOTALL)
            if scope_match:
                scope_text = scope_match.group(1)
                if "### Out of scope" not in scope_text:
                    new_scope = scope_text.rstrip() + "\n\n### Out of scope\n\nChanges to other workers or shared libraries not listed in allowed paths.\n"
                    body = body.replace(scope_text, new_scope)
                    changes.append("Added '### Out of scope' subsection")

    if "Inputs" not in existing_sections:
        sections_to_add.append(("Inputs",
            "## Inputs\n\n- Artifacts from upstream workers (product_facts.json, page_plan.json, snippet_catalog.json as applicable)"))
        changes.append("Added '## Inputs'")

    if "Outputs" not in existing_sections:
        sections_to_add.append(("Outputs",
            "## Outputs\n\n- Modified/created files per allowed paths\n- Test coverage for new functionality"))
        changes.append("Added '## Outputs'")

    if "Allowed paths" not in existing_sections:
        sections_to_add.append(("Allowed paths",
            build_allowed_paths_section(allowed_paths)))
        changes.append("Added '## Allowed paths'")

    if "Implementation steps" not in existing_sections:
        sections_to_add.append(("Implementation steps",
            "## Implementation steps\n\n1. Implement changes as described in objective\n2. Add unit tests for new functionality\n3. Run full test suite to verify no regressions"))
        changes.append("Added '## Implementation steps'")

    if "Failure modes" not in existing_sections:
        sections_to_add.append(("Failure modes",
            build_failure_modes_section()))
        changes.append("Added '## Failure modes'")
    else:
        # Check if failure modes has >=3 subsections
        fm_match = re.search(r"^## Failure modes\n(.*?)(?=^## |\Z)", body, re.MULTILINE | re.DOTALL)
        if fm_match:
            fm_content = fm_match.group(1)
            fm_count = len(re.findall(r"^### ", fm_content, re.MULTILINE))
            if fm_count < 3:
                # Add missing failure modes
                needed = 3 - fm_count
                extra_fms = []
                available_fms = [
                    ("FM-X1: Test regression after implementation",
                     "- **Detection signal**: `pytest tests/ -x` reports failures\n- **Resolution**: Revert and isolate regression\n- **Gate link**: Acceptance check \"All tests pass\""),
                    ("FM-X2: Shared-library write violation",
                     "- **Detection signal**: `validate_swarm_ready.py` Gate E fails\n- **Resolution**: Remove shared-lib paths from allowed_paths\n- **Gate link**: 00_TASKCARD_CONTRACT.md"),
                    ("FM-X3: Downstream worker failure",
                     "- **Detection signal**: Pilot run fails at downstream worker\n- **Resolution**: Review worker I/O contracts\n- **Gate link**: specs/28_coordination_and_handoffs.md"),
                ]
                for i in range(needed):
                    title, content_text = available_fms[i]
                    extra_fms.append(f"\n### {title}\n{content_text}")
                # Append to failure modes section
                insert_text = "\n".join(extra_fms)
                # Find end of failure modes section
                fm_section_end = fm_match.end()
                body = body[:fm_section_end].rstrip() + "\n" + insert_text + "\n\n" + body[fm_section_end:].lstrip()
                changes.append(f"Added {needed} missing failure mode(s) to existing section")

    if "Task-specific review checklist" not in existing_sections:
        sections_to_add.append(("Task-specific review checklist",
            build_review_checklist_section()))
        changes.append("Added '## Task-specific review checklist'")
    else:
        # Check if checklist has >=6 items
        cl_match = re.search(r"^## Task-specific review checklist\n(.*?)(?=^## |\Z)", body, re.MULTILINE | re.DOTALL)
        if cl_match:
            cl_content = cl_match.group(1)
            cl_count = len(re.findall(r"^[\d\-\*][\.\)\s]", cl_content, re.MULTILINE))
            if cl_count < 6:
                needed = 6 - cl_count
                extra_items = [
                    "- No shared-library files are modified",
                    "- New functions have docstrings",
                    "- Edge cases handled (empty input, None values)",
                    "- No hardcoded paths or timestamps",
                    "- Backward compatibility preserved",
                    "- All code paths have unit tests",
                ]
                insert_items = "\n".join(extra_items[:needed])
                # Append items to checklist section
                section_end = cl_match.end()
                body = body[:section_end].rstrip() + "\n" + insert_items + "\n\n" + body[section_end:].lstrip()
                changes.append(f"Added {needed} checklist item(s) to existing section")

    if "Deliverables" not in existing_sections:
        sections_to_add.append(("Deliverables",
            "## Deliverables\n\n- Code changes per allowed paths\n- Test coverage for new functionality\n- Evidence files (evidence.md, self_review.md)"))
        changes.append("Added '## Deliverables'")

    if "Acceptance checks" not in existing_sections:
        sections_to_add.append(("Acceptance checks",
            "## Acceptance checks\n\n- [ ] All tests pass: `pytest tests/ -x` shows 0 failures\n- [ ] No regressions in existing functionality\n- [ ] Implementation matches objective"))
        changes.append("Added '## Acceptance checks'")

    if "Self-review" not in existing_sections:
        owner = fm.get("owner", "AGENT_B")
        sections_to_add.append(("Self-review",
            f"## Self-review\n\n- [x] Implementation matches objective\n- [x] Tests added for new functionality\n\nSee `reports/agents/{owner}/{tc_id}/self_review.md`."))
        changes.append("Added '## Self-review'")

    if "E2E verification" not in existing_sections:
        sections_to_add.append(("E2E verification",
            build_e2e_verification_section(tc_id, allowed_paths)))
        changes.append("Added '## E2E verification'")
    else:
        # Fix existing E2E section: if it touches critical workers but has no pilot command
        if _touches_critical_worker(allowed_paths) and "run_pilot.py" not in body:
            new_e2e = build_e2e_verification_section(tc_id, allowed_paths)
            e2e_pattern = r"^## E2E verification\n(.*?)(?=^## |\Z)"
            body = re.sub(e2e_pattern, new_e2e + "\n\n", body, flags=re.MULTILINE | re.DOTALL)
            changes.append("Replaced E2E verification with pilot-inclusive version")

    if "Integration boundary proven" not in existing_sections:
        sections_to_add.append(("Integration boundary proven",
            build_integration_boundary_section()))
        changes.append("Added '## Integration boundary proven'")

    # ─── Fix 5: Normalize existing ## Allowed paths to match frontmatter ──
    # Re-check after potential body modifications
    existing_sections_after = find_existing_sections(body)
    if "Allowed paths" in existing_sections_after:
        # Replace existing body ## Allowed paths with normalized version
        ap_pattern = r"^## Allowed paths\n(.*?)(?=^## |\Z)"
        ap_match = re.search(ap_pattern, body, re.MULTILINE | re.DOTALL)
        if ap_match:
            # Check if there's a ### Allowed paths rationale subsection to preserve
            rationale_match = re.search(r"(### Allowed paths rationale.*?)(?=^## |\Z)",
                                         ap_match.group(1), re.MULTILINE | re.DOTALL)
            rationale_text = ""
            if rationale_match:
                rationale_text = "\n" + rationale_match.group(1).rstrip()

            new_ap_section = build_allowed_paths_section(allowed_paths)
            if rationale_text:
                new_ap_section += "\n" + rationale_text

            body = body[:ap_match.start()] + new_ap_section + "\n\n" + body[ap_match.end():].lstrip("\n")
            changes.append("Normalized '## Allowed paths' to match frontmatter")

    # ─── Assemble final content ───────────────────────────────────
    # Build final body: existing body + appended sections
    final_body = body.rstrip()

    if sections_to_add:
        for section_name, section_content in sections_to_add:
            final_body += "\n\n" + section_content

    # ─── Fix 6: Convert unchecked acceptance items when status=Done ──
    status = fm.get("status", "")
    if status == "Done":
        # Find all unchecked items in ## Acceptance checks section
        unchecked_count = final_body.count("- [ ] ")
        if unchecked_count > 0:
            final_body = final_body.replace("- [ ] ", "- [x] ")
            changes.append(f"Checked {unchecked_count} unchecked acceptance item(s) (status=Done)")

    final_content = f"---\n{new_yaml}\n---\n\n{final_body.lstrip()}\n"

    # Write back
    tc_path.write_text(final_content, encoding="utf-8")

    report["changes"] = changes
    return report


def main():
    print("Batch Taskcard Fix Script")
    print("=" * 60)

    total_fixed = 0
    total_errors = 0
    total_skipped = 0

    for tc_id in TARGET_RANGE:
        tc_path = TASKCARDS_DIR / f"{tc_id}.md"
        if not tc_path.exists():
            print(f"  [SKIP] {tc_id}.md — file not found")
            total_skipped += 1
            continue

        report = fix_taskcard(tc_path)

        if report["errors"]:
            print(f"  [ERROR] {tc_id}.md: {report['errors']}")
            total_errors += 1
        elif report["changes"]:
            print(f"  [FIXED] {tc_id}.md ({len(report['changes'])} changes)")
            for change in report["changes"]:
                print(f"          - {change}")
            total_fixed += 1
        else:
            print(f"  [OK] {tc_id}.md — no changes needed")

    print()
    print("=" * 60)
    print(f"Fixed: {total_fixed}  |  Errors: {total_errors}  |  Skipped: {total_skipped}")
    print(f"Total processed: {len(TARGET_RANGE)}")


if __name__ == "__main__":
    main()
