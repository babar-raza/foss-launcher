#!/usr/bin/env python3
"""
Taskcard Creation Script
TC-PREVENT-INCOMPLETE: Helper script to create valid taskcards from template

Usage:
    python scripts/create_taskcard.py
    python scripts/create_taskcard.py --tc-number 999 --title "My Task"
"""

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def get_git_sha() -> str:
    """Get current git commit SHA."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()[:40]
    except subprocess.CalledProcessError:
        print("Warning: Could not get git SHA, using placeholder")
        return "[git rev-parse HEAD]"


def slugify(text: str) -> str:
    """Convert title to filename-safe slug."""
    # Convert to lowercase, replace spaces with underscores
    slug = text.lower().replace(" ", "_")
    # Remove non-alphanumeric characters except hyphens and underscores
    slug = "".join(c for c in slug if c.isalnum() or c in "-_")
    return slug


def create_taskcard(tc_number: int, title: str, owner: str, tags: list = None):
    """Create a new taskcard from template."""
    repo_root = Path(__file__).parent.parent
    template_path = repo_root / "plans" / "taskcards" / "00_TEMPLATE.md"

    if not template_path.exists():
        print(f"ERROR: Template not found at {template_path}")
        return False

    # Read template
    template_content = template_path.read_text(encoding="utf-8")

    # Generate slug
    slug = slugify(title)

    # Get current date and git SHA
    today = datetime.now().strftime("%Y-%m-%d")
    spec_ref = get_git_sha()

    # Prepare substitutions
    substitutions = {
        "TC-XXX": f"TC-{tc_number}",
        "XXX": str(tc_number),
        "[Brief title describing the taskcard]": title,
        "[Title]": title,
        "[agent or team name]": owner,
        "YYYY-MM-DD": today,
        "[slug]": slug,
        "[git rev-parse HEAD]": spec_ref,
    }

    # Apply substitutions
    content = template_content
    for old, new in substitutions.items():
        content = content.replace(old, new)

    # Add tags if provided
    if tags:
        tags_str = ", ".join(f'"{tag}"' for tag in tags)
        content = content.replace('["tag1", "tag2"]', f'[{tags_str}]')

    # Generate filename
    filename = f"TC-{tc_number}_{slug}.md"
    output_path = repo_root / "plans" / "taskcards" / filename

    # Check if file already exists
    if output_path.exists():
        print(f"ERROR: Taskcard {filename} already exists")
        return False

    # Write file
    output_path.write_text(content, encoding="utf-8")
    print(f"[OK] Created taskcard: {output_path}")

    # Validate taskcard
    print("\nValidating taskcard...")
    try:
        result = subprocess.run(
            [sys.executable, "tools/validate_taskcards.py"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=30
        )

        if filename in result.stdout and "[OK]" in result.stdout:
            print("[OK] Taskcard passes validation")
        else:
            print("[WARN] Taskcard validation output:")
            # Show relevant output
            for line in result.stdout.split("\n"):
                if filename in line or "[FAIL]" in line or "Missing" in line:
                    print(f"  {line}")
    except subprocess.TimeoutExpired:
        print("[WARN] Validation timed out (may be due to large repository)")
    except Exception as e:
        print(f"[WARN] Could not run validation: {e}")

    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="Create a new taskcard from template"
    )
    parser.add_argument(
        "--tc-number", type=int,
        help="Taskcard number (e.g., 999 for TC-999)"
    )
    parser.add_argument(
        "--title",
        help="Taskcard title"
    )
    parser.add_argument(
        "--owner",
        help="Taskcard owner (agent or team name)"
    )
    parser.add_argument(
        "--tags", nargs="+",
        help="Tags for taskcard (space-separated)"
    )
    parser.add_argument(
        "--open", action="store_true",
        help="Open taskcard in default editor after creation"
    )

    args = parser.parse_args()

    # Interactive mode if arguments not provided
    if not args.tc_number:
        try:
            tc_number = int(input("Enter taskcard number (e.g., 999 for TC-999): "))
        except ValueError:
            print("ERROR: Invalid taskcard number")
            return 1
    else:
        tc_number = args.tc_number

    if not args.title:
        title = input("Enter taskcard title: ").strip()
        if not title:
            print("ERROR: Title cannot be empty")
            return 1
    else:
        title = args.title

    if not args.owner:
        owner = input("Enter owner (agent/team name): ").strip()
        if not owner:
            print("ERROR: Owner cannot be empty")
            return 1
    else:
        owner = args.owner

    if not args.tags:
        tags_input = input("Enter tags (comma-separated, optional): ").strip()
        tags = [t.strip() for t in tags_input.split(",")] if tags_input else None
    else:
        tags = args.tags

    # Create taskcard
    output_path = create_taskcard(tc_number, title, owner, tags)

    if not output_path:
        return 1

    # Offer to open in editor
    should_open = args.open
    if not should_open:
        open_input = input("\nOpen in editor? (y/n): ").lower()
        should_open = open_input in ['y', 'yes']

    if should_open:
        import os
        import platform

        try:
            if platform.system() == "Windows":
                os.startfile(output_path)
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", output_path])
            else:  # Linux
                subprocess.run(["xdg-open", output_path])

            print(f"Opened {output_path.name} in default editor")
        except Exception as e:
            print(f"Could not open editor: {e}")
            print(f"You can manually open: {output_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
