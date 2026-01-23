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

    def check_templates_have_platform_folder(self) -> bool:
        """Check that specs/templates/** contains at least one __PLATFORM__ folder."""
        templates_dir = self.repo_root / "specs" / "templates"
        if not templates_dir.exists():
            self.errors.append(f"Templates directory not found: {templates_dir}")
            return False

        # Look for __PLATFORM__ directories
        platform_dirs = list(templates_dir.rglob("__PLATFORM__"))
        if not platform_dirs:
            self.errors.append(
                "specs/templates/** contains no __PLATFORM__ folder. "
                "V2 template hierarchy not materialized."
            )
            return False

        return True

    def check_templates_readme_v2(self) -> bool:
        """Check that specs/templates/README.md documents both V1 and V2 layouts."""
        readme_path = self.repo_root / "specs" / "templates" / "README.md"
        if not readme_path.exists():
            self.errors.append(f"Templates README not found: {readme_path}")
            return False

        try:
            content = readme_path.read_text(encoding='utf-8')
            required_terms = [
                "V1 Layout",
                "V2 Layout",
                "specs/32_platform_aware_content_layout.md"
            ]

            missing_terms = []
            for term in required_terms:
                if term not in content:
                    missing_terms.append(term)

            if missing_terms:
                self.errors.append(
                    f"specs/templates/README.md still claims V1-only layout. "
                    f"Missing terms: {', '.join(missing_terms)}"
                )
                return False

            return True
        except Exception as e:
            self.errors.append(f"Error reading templates README: {e}")
            return False

    def check_config_templates_have_platform_fields(self) -> bool:
        """Check that config templates include target_platform and layout_mode."""
        config_templates = [
            "configs/products/_template.run_config.yaml",
            "configs/pilots/_template.pinned.run_config.yaml"
        ]

        all_pass = True
        for config_path_str in config_templates:
            config_path = self.repo_root / config_path_str
            if not config_path.exists():
                self.warnings.append(f"Config template not found: {config_path}")
                continue

            try:
                content = config_path.read_text(encoding='utf-8')

                has_errors = False
                if "target_platform:" not in content:
                    self.errors.append(
                        f"{config_path_str} missing 'target_platform' field"
                    )
                    has_errors = True

                if "layout_mode:" not in content:
                    self.errors.append(
                        f"{config_path_str} missing 'layout_mode' field"
                    )
                    has_errors = True

                if has_errors:
                    all_pass = False
            except Exception as e:
                self.errors.append(f"Error reading {config_path_str}: {e}")
                all_pass = False

        return all_pass

    def check_products_v2_path_format(self) -> bool:
        """Check that products V2 paths use /{locale}/{platform}/ not /{platform}/ alone.

        Products MUST remain language-folder based per spec 32.
        Invalid: /words/python/, /cells/typescript/
        Valid: /words/en/python/, /cells/es/typescript/
        """
        # Check binding spec for correct examples
        spec_path = self.repo_root / "specs" / "32_platform_aware_content_layout.md"
        if not spec_path.exists():
            return True  # Already checked in check_binding_spec_exists

        try:
            content = spec_path.read_text(encoding='utf-8')

            # Pattern that would indicate invalid products path (without locale)
            # We look for products.aspose.org/{family}/{platform}/ without locale
            invalid_patterns = [
                r'products\.aspose\.org/\w+/(?:python|typescript|javascript|go|java|dotnet|cpp|ruby|php)/',
            ]

            for pattern in invalid_patterns:
                matches = re.findall(pattern, content)
                # Filter out matches that are within valid V1 examples context or negation
                for match in matches:
                    # Check if this is in a "NOT" context or V1 context
                    idx = content.find(match)
                    context_start = max(0, idx - 100)
                    context = content[context_start:idx + len(match) + 50]
                    if "NOT" not in context and "Invalid" not in context and "V1" not in context:
                        self.errors.append(
                            f"Binding spec contains invalid products V2 path example: {match} "
                            f"(products V2 MUST use /{'{locale}'}/{'{platform}'}/ format)"
                        )
                        return False

            # Verify correct examples exist
            if "products.aspose.org/words/en/typescript/" not in content:
                self.warnings.append(
                    "Binding spec should include explicit valid products V2 example: "
                    "products.aspose.org/{family}/{locale}/{platform}/"
                )

            return True
        except Exception as e:
            self.errors.append(f"Error checking products V2 path format: {e}")
            return False

    def check_templates_products_v2_structure(self) -> bool:
        """Check that products templates V2 hierarchy uses __LOCALE__/__PLATFORM__ order."""
        templates_dir = self.repo_root / "specs" / "templates"
        products_dir = templates_dir / "products.aspose.org"

        if not products_dir.exists():
            self.warnings.append("products.aspose.org templates directory not found")
            return True  # Not an error, just not present

        # Find V2 products templates with __PLATFORM__
        platform_dirs = list(products_dir.rglob("__PLATFORM__"))

        for platform_dir in platform_dirs:
            # Check that __PLATFORM__ is nested under __LOCALE__
            path_parts = platform_dir.relative_to(products_dir).parts

            # Expect: {family}/__LOCALE__/__PLATFORM__/...
            if len(path_parts) >= 2:
                locale_idx = None
                platform_idx = None
                for i, part in enumerate(path_parts):
                    if part == "__LOCALE__":
                        locale_idx = i
                    if part == "__PLATFORM__":
                        platform_idx = i

                if locale_idx is not None and platform_idx is not None:
                    if platform_idx < locale_idx:
                        self.errors.append(
                            f"Products V2 template has invalid structure: {platform_dir.relative_to(templates_dir)} "
                            f"(__PLATFORM__ must be nested under __LOCALE__)"
                        )
                        return False

        return True

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
            ("Templates hierarchy has __PLATFORM__ folders", self.check_templates_have_platform_folder),
            ("Templates README documents V1 and V2", self.check_templates_readme_v2),
            ("Config templates have platform fields", self.check_config_templates_have_platform_fields),
            ("Products V2 path uses /{locale}/{platform}/ format", self.check_products_v2_path_format),
            ("Products templates V2 use __LOCALE__/__PLATFORM__ order", self.check_templates_products_v2_structure),
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
