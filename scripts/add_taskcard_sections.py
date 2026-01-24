#!/usr/bin/env python3
"""
Add Failure modes and Task-specific review checklist sections to taskcards.
"""
import re
from pathlib import Path


def get_taskcard_context(content: str) -> dict:
    """Extract key context from a taskcard to inform section content."""
    context = {
        "id": "",
        "title": "",
        "objective": "",
        "specs": [],
        "has_failure_modes": False,
        "has_review_checklist": False,
    }

    # Extract ID and title from frontmatter
    id_match = re.search(r'^id:\s*(\S+)', content, re.MULTILINE)
    if id_match:
        context["id"] = id_match.group(1)

    title_match = re.search(r'^title:\s*"([^"]+)"', content, re.MULTILINE)
    if title_match:
        context["title"] = title_match.group(1)

    # Extract objective
    obj_match = re.search(r'## Objective\n(.+?)(?=\n##|\Z)', content, re.DOTALL)
    if obj_match:
        context["objective"] = obj_match.group(1).strip()[:200]  # First 200 chars

    # Extract spec references
    spec_match = re.search(r'## Required spec references\n(.+?)(?=\n##|\Z)', content, re.DOTALL)
    if spec_match:
        specs_text = spec_match.group(1)
        context["specs"] = re.findall(r'- (specs/\S+)', specs_text)

    # Check if sections already exist
    context["has_failure_modes"] = bool(re.search(r'## Failure modes', content))
    context["has_review_checklist"] = bool(re.search(r'## Task-specific review checklist', content))

    return context


def generate_failure_modes(context: dict) -> str:
    """Generate failure modes section based on taskcard context."""
    tc_id = context["id"]
    title = context["title"]

    # Common failure mode templates that can be customized per taskcard
    modes = []

    # Mode 1: Schema validation failure
    modes.append(f"""1. **Failure**: Schema validation fails for output artifacts
   - **Detection**: `validate_swarm_ready.py` or pytest fails with JSON schema errors
   - **Fix**: Review artifact structure against schema files in `specs/schemas/`; ensure all required fields are present and types match
   - **Spec/Gate**: specs/11_state_and_events.md, specs/09_validation_gates.md (Gate C)""")

    # Mode 2: Determinism failure
    modes.append(f"""2. **Failure**: Nondeterministic output detected
   - **Detection**: Running task twice produces different artifact bytes or ordering
   - **Fix**: Review specs/10_determinism_and_caching.md; ensure stable JSON serialization, stable sorting of lists, no timestamps/UUIDs in outputs
   - **Spec/Gate**: specs/10_determinism_and_caching.md, tools/validate_swarm_ready.py (Gate H)""")

    # Mode 3: Write fence violation
    modes.append(f"""3. **Failure**: Write fence violation (modified files outside allowed_paths)
   - **Detection**: `git status` shows changes outside allowed_paths, or Gate E fails
   - **Fix**: Revert unauthorized changes; if shared library modification needed, escalate to owning taskcard
   - **Spec/Gate**: plans/taskcards/00_TASKCARD_CONTRACT.md (Write fence rule), tools/validate_taskcards.py""")

    return "## Failure modes\n" + "\n\n".join(modes) + "\n"


def generate_review_checklist(context: dict) -> str:
    """Generate task-specific review checklist based on context."""
    tc_id = context["id"]
    title = context["title"]
    objective = context["objective"][:80] if context["objective"] else title

    items = []

    # Add context-specific items based on taskcard ID patterns
    if "W1" in title or "W2" in title or "W3" in title or "W4" in title or "W5" in title or "W6" in title or "W7" in title or "W8" in title or "W9" in title or "worker" in title.lower():
        items.append(f"- [ ] Worker emits required events per specs/21_worker_contracts.md")
        items.append(f"- [ ] Worker outputs validate against declared schemas")
        items.append(f"- [ ] Worker handles missing/malformed inputs gracefully with blocker artifacts")

    if "schema" in title.lower() or tc_id == "TC-200":
        items.append(f"- [ ] All schema files validate as proper JSON Schema Draft 7")
        items.append(f"- [ ] Schema validation helpers cover all required artifact types")

    if "test" in objective.lower() or "pilot" in title.lower():
        items.append(f"- [ ] Tests include positive and negative cases")
        items.append(f"- [ ] E2E verification command documented and tested")

    # Always add these generic but important items
    items.append(f"- [ ] All outputs are written atomically per specs/10_determinism_and_caching.md")
    items.append(f"- [ ] No manual content edits made (compliance with no_manual_content_edits policy)")
    items.append(f"- [ ] Determinism verified by running task twice and comparing artifacts byte-for-byte")
    items.append(f"- [ ] All spec references listed in taskcard were consulted during implementation")
    items.append(f"- [ ] Evidence files (report.md, self_review.md) include all required sections and command outputs")
    items.append(f"- [ ] No placeholder values (PIN_ME, TODO, FIXME, etc.) remain in production code paths")

    # Ensure we have at least 6 items
    while len(items) < 6:
        items.append(f"- [ ] Task deliverables match expected outputs exactly")

    return "## Task-specific review checklist\nBeyond the standard acceptance checks, verify:\n" + "\n".join(items[:10]) + "\n"  # Cap at 10 items


def find_insertion_point(content: str) -> tuple[int, str]:
    """Find where to insert the new sections (before ## Deliverables)."""
    # Look for ## Deliverables section
    match = re.search(r'\n(## Deliverables)\n', content)
    if match:
        return match.start(), "before_deliverables"

    # Fallback: before ## Acceptance checks
    match = re.search(r'\n(## Acceptance checks)\n', content)
    if match:
        return match.start(), "before_acceptance"

    # Last resort: before ## Self-review
    match = re.search(r'\n(## Self-review)\n', content)
    if match:
        return match.start(), "before_self_review"

    return -1, "not_found"


def update_taskcard(file_path: Path) -> bool:
    """Update a single taskcard file. Returns True if modified."""
    content = file_path.read_text(encoding="utf-8")
    context = get_taskcard_context(content)

    # Skip if already has both sections
    if context["has_failure_modes"] and context["has_review_checklist"]:
        print(f"[SKIP] {file_path.name} - already has both sections")
        return False

    # Find insertion point
    insert_pos, location = find_insertion_point(content)
    if insert_pos == -1:
        print(f"[ERROR] {file_path.name} - could not find insertion point")
        return False

    # Generate sections
    sections_to_add = []

    if not context["has_failure_modes"]:
        sections_to_add.append(generate_failure_modes(context))

    if not context["has_review_checklist"]:
        sections_to_add.append(generate_review_checklist(context))

    # Insert sections
    new_content = (
        content[:insert_pos] +
        "\n" + "\n".join(sections_to_add) +
        content[insert_pos:]
    )

    file_path.write_text(new_content, encoding="utf-8")
    print(f"[OK] {file_path.name} - added sections")
    return True


def main():
    taskcards_dir = Path(__file__).parent.parent / "plans" / "taskcards"

    # Get all TC-*.md files
    taskcard_files = sorted(taskcards_dir.glob("TC-*.md"))

    print(f"Found {len(taskcard_files)} taskcard(s)\n")

    modified_count = 0
    for tc_file in taskcard_files:
        if update_taskcard(tc_file):
            modified_count += 1

    print(f"\n{modified_count} taskcard(s) updated")


if __name__ == "__main__":
    main()
