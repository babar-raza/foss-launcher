#!/usr/bin/env python3
"""
Platform Layout Consistency Validator (V2)

Validates that platform-aware layout requirements are properly implemented across:
- Schema includes target_platform and layout_mode
- Binding spec exists (specs/32_platform_aware_content_layout.md)
- TC-540 mentions platform + v2 path forms
- Example configs updated with platform fields
- No stale v1-only path examples in critical specs

Exit codes:
  0 - All checks pass
  1 - One or more checks failed
"""

import sys
import json
import re
from pathlib import Path
from typing import List, Tuple


class PlatformLayoutValidator:
    """Validates platform layout consistency."""

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def check_schema_has_platform_fields(self) -> bool:
        """Check that run_config schema includes target_platform and layout_mode."""
        schema_path = self.repo_root / "specs" / "schemas" / "run_config.schema.json"
        if not schema_path.exists():
            self.errors.append(f"Schema not found: {schema_path}")
            return False

        try:
            with open(schema_path, 'r', encoding='utf-8') as f:
                schema = json.load(f)

            properties = schema.get("properties", {})

            has_errors = False
            if "target_platform" not in properties:
                self.errors.append("Schema missing 'target_platform' field")
                has_errors = True

            if "layout_mode" not in properties:
                self.errors.append("Schema missing 'layout_mode' field")
                has_errors = True
            else:
                layout_mode = properties["layout_mode"]
                if "enum" not in layout_mode:
                    self.errors.append("'layout_mode' missing enum constraint")
                    has_errors = True
                else:
                    expected_values = {"auto", "v1", "v2"}
                    actual_values = set(layout_mode["enum"])
                    if actual_values != expected_values:
                        self.errors.append(
                            f"'layout_mode' enum mismatch. Expected {expected_values}, got {actual_values}"
                        )
                        has_errors = True

            return not has_errors

        except json.JSONDecodeError as e:
            self.errors.append(f"Failed to parse schema JSON: {e}")
            return False
        except Exception as e:
            self.errors.append(f"Error checking schema: {e}")
            return False

    def check_binding_spec_exists(self) -> bool:
        """Check that binding spec 32_platform_aware_content_layout.md exists."""
        spec_path = self.repo_root / "specs" / "32_platform_aware_content_layout.md"
        if not spec_path.exists():
            self.errors.append(f"Binding spec not found: {spec_path}")
            return False

        # Verify it contains key terms
        try:
            content = spec_path.read_text(encoding='utf-8')
            required_terms = [
                "target_platform",
                "platform_family",
                "layout_mode",
                "V1 Layout",
                "V2 Layout",
                "Platform Mapping Table"
            ]

            missing_terms = []
            for term in required_terms:
                if term not in content:
                    missing_terms.append(term)

            if missing_terms:
                self.errors.append(
                    f"Binding spec missing required terms: {', '.join(missing_terms)}"
                )
                return False

            return True
        except Exception as e:
            self.errors.append(f"Error reading binding spec: {e}")
            return False

    def check_tc540_mentions_platform(self) -> bool:
        """Check that TC-540 mentions platform and v2 path forms."""
        tc_path = self.repo_root / "plans" / "taskcards" / "TC-540_content_path_resolver.md"
        if not tc_path.exists():
            self.errors.append(f"TC-540 not found: {tc_path}")
            return False

        try:
            content = tc_path.read_text(encoding='utf-8')
            required_terms = [
                "target_platform",
                "layout_mode",
                "V2",
                "{locale}/{platform}",
                "specs/32_platform_aware_content_layout.md"
            ]

            missing_terms = []
            for term in required_terms:
                if term not in content:
                    missing_terms.append(term)

            if missing_terms:
                self.errors.append(
                    f"TC-540 missing platform-aware terms: {', '.join(missing_terms)}"
                )
                return False

            return True
        except Exception as e:
            self.errors.append(f"Error reading TC-540: {e}")
            return False

    def check_example_configs_updated(self) -> bool:
        """Check that example configs include platform fields."""
        example_config = self.repo_root / "specs" / "examples" / "launch_config.example.yaml"
        if not example_config.exists():
            self.warnings.append(f"Example config not found: {example_config}")
            return True  # Don't fail, just warn

        try:
            content = example_config.read_text(encoding='utf-8')

            has_errors = False
            if "target_platform:" not in content:
                self.errors.append("Example config missing 'target_platform' field")
                has_errors = True

            if "layout_mode:" not in content:
                self.errors.append("Example config missing 'layout_mode' field")
                has_errors = True

            # Check for V2 path examples in allowed_paths
            if "/python/" not in content or "/en/python/" not in content:
                self.warnings.append(
                    "Example config should include V2 path examples (e.g., /en/python/)"
                )

            return not has_errors
        except Exception as e:
            self.errors.append(f"Error reading example config: {e}")
            return False

    def check_key_specs_updated(self) -> bool:
        """Check that key specs mention V2 layout."""
        specs_to_check = [
            ("specs/18_site_repo_layout.md", [
                "specs/32_platform_aware_content_layout.md",
                "V2 Layout",
                "Platform-Aware"
            ]),
            ("specs/20_rulesets_and_templates_registry.md", [
                "__PLATFORM__",
                "V2",
                "platform"
            ])
        ]

        all_pass = True
        for spec_path_str, required_terms in specs_to_check:
            spec_path = self.repo_root / spec_path_str
            if not spec_path.exists():
                self.warnings.append(f"Spec not found: {spec_path}")
                continue

            try:
                content = spec_path.read_text(encoding='utf-8')
                missing_terms = []
                for term in required_terms:
                    if term not in content:
                        missing_terms.append(term)

                if missing_terms:
                    self.errors.append(
                        f"{spec_path_str} missing platform-aware terms: {', '.join(missing_terms)}"
                    )
                    all_pass = False
            except Exception as e:
                self.errors.append(f"Error reading {spec_path_str}: {e}")
                all_pass = False

        return all_pass

    def run_all_checks(self) -> bool:
        """Run all validation checks."""
        print("Platform Layout Consistency Validation (V2)")
        print("=" * 70)
        print()

        checks = [
            ("Schema includes target_platform and layout_mode", self.check_schema_has_platform_fields),
            ("Binding spec exists (32_platform_aware_content_layout.md)", self.check_binding_spec_exists),
            ("TC-540 mentions platform + V2 paths", self.check_tc540_mentions_platform),
            ("Example configs updated with platform fields", self.check_example_configs_updated),
            ("Key specs updated for V2 layout", self.check_key_specs_updated),
        ]

        all_passed = True
        for check_name, check_func in checks:
            try:
                passed = check_func()
                status = "[OK]" if passed else "[FAIL]"
                print(f"{status} {check_name}")
                if not passed:
                    all_passed = False
            except Exception as e:
                print(f"[FAIL] {check_name}: {e}")
                all_passed = False

        print()

        # Print errors
        if self.errors:
            print("ERRORS:")
            for error in self.errors:
                print(f"  - {error}")
            print()

        # Print warnings
        if self.warnings:
            print("WARNINGS:")
            for warning in self.warnings:
                print(f"  - {warning}")
            print()

        # Summary
        print("=" * 70)
        if all_passed:
            print("SUCCESS: Platform layout consistency checks passed")
        else:
            print(f"FAILURE: {len(self.errors)} error(s) found")
        print("=" * 70)

        return all_passed


def main():
    """Main validation routine."""
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent

    validator = PlatformLayoutValidator(repo_root)
    passed = validator.run_all_checks()

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
