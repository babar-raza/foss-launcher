"""Tests for TC-4249: code-block retry fires unconditionally for code-required roles.

Verifies that the `sec_snippets` guard was removed from the code-block retry
condition in `_generate_section`, so reference page sections with no snippet
overlap still trigger the retry when a code block is absent.

Uses two verification layers:
1. Source/string guards (like test_tc4237_retry_type_reminder.py) for the
   private closure that cannot be invoked directly.
2. AST-structural guard: parse the worker.py AST and verify that the `If` node
   containing `_needs_code_retry = True` does NOT reference `sec_snippets` in
   its test expression. This is stronger than regex — it is unambiguous about
   the parsed code structure.
"""
from __future__ import annotations

import ast
import inspect
import re


class TestCodeBlockRetryUnconditional:
    """TC-4249: `sec_snippets` must not gate the code-block retry check."""

    def test_sec_snippets_not_in_code_retry_condition(self) -> None:
        """Source guard: the code-block retry condition must not reference sec_snippets.

        Before TC-4249:
            if page_plan.page_role in _CODE_REQUIRED_ROLES and sec_snippets:
        After TC-4249:
            if page_plan.page_role in _CODE_REQUIRED_ROLES:
        """
        import launcher.workers.generate.worker as w

        src = inspect.getsource(w)

        # Find the block containing _CODE_REQUIRED_ROLES check near _needs_code_retry
        # We look for the pattern:
        #   _CODE_REQUIRED_ROLES ... sec_snippets
        # on the SAME condition line — this should NOT exist after TC-4249.
        bad_pattern = re.compile(
            r"_CODE_REQUIRED_ROLES\b.*\bsec_snippets\b"
        )
        matches = bad_pattern.findall(src)
        assert not matches, (
            "TC-4249 REGRESSION: `sec_snippets` guard found alongside `_CODE_REQUIRED_ROLES` "
            "in code-block retry condition. Remove `and sec_snippets` so the retry fires "
            "even for sections with no snippet overlap.\n"
            f"Found: {matches}"
        )

    def test_code_required_roles_still_gates_retry(self) -> None:
        """Source guard: _CODE_REQUIRED_ROLES must still be the condition for the retry."""
        import launcher.workers.generate.worker as w

        src = inspect.getsource(w)

        # The _needs_code_retry assignment and the _CODE_REQUIRED_ROLES check must both exist
        assert "_needs_code_retry = False" in src, (
            "_needs_code_retry flag not found in worker.py — retry logic may have been removed"
        )
        assert "_needs_code_retry = True" in src, (
            "_needs_code_retry=True assignment not found — retry never fires"
        )
        assert "_CODE_REQUIRED_ROLES" in src, (
            "_CODE_REQUIRED_ROLES not found in worker.py — retry condition missing"
        )

    def test_tc4249_comment_present(self) -> None:
        """Source guard: TC-4249 comment must be present to document the intentional change."""
        import launcher.workers.generate.worker as w

        src = inspect.getsource(w)
        assert "TC-4249" in src, (
            "TC-4249 comment not found in worker.py — add a comment referencing this taskcard "
            "near the code-block retry condition."
        )

    def test_code_retry_instruction_in_retry_additions(self) -> None:
        """Source guard: the retry additions block must include a code block instruction."""
        import launcher.workers.generate.worker as w

        src = inspect.getsource(w)

        # The retry instruction for code blocks must be present (from TC-4229)
        assert "REQUIRES at least one code block" in src or "CRITICAL: This section REQUIRES" in src, (
            "Code block requirement instruction not found in _retry_additions block. "
            "The retry must instruct the LLM to produce a code block."
        )

    def test_code_required_roles_includes_reference_object_page(self) -> None:
        """_CODE_REQUIRED_ROLES must include reference_object_page (the primary failing role)."""
        from launcher.workers.generate.worker import _CODE_REQUIRED_ROLES

        assert "reference_object_page" in _CODE_REQUIRED_ROLES, (
            "reference_object_page not in _CODE_REQUIRED_ROLES — "
            "Properties/Methods sections will never trigger code-block retry."
        )

    def test_code_required_roles_includes_api_reference(self) -> None:
        """_CODE_REQUIRED_ROLES must include api_reference."""
        from launcher.workers.generate.worker import _CODE_REQUIRED_ROLES

        assert "api_reference" in _CODE_REQUIRED_ROLES, (
            "api_reference not in _CODE_REQUIRED_ROLES — "
            "api_reference pages will not trigger code-block retry."
        )


class TestCodeBlockRetryASTStructure:
    """TC-4249 AST-structural guard: parse worker.py AST and verify the `If` node
    that sets `_needs_code_retry = True` does not include `sec_snippets` in its
    test expression. This is unambiguous — regex could match comments or strings,
    but AST traversal only matches executable code structure.
    """

    @staticmethod
    def _find_needs_code_retry_if_tests() -> list[ast.expr]:
        """Return all `If.test` expressions that guard `_needs_code_retry = True`."""
        import launcher.workers.generate.worker as w

        src = inspect.getsource(w)
        tree = ast.parse(src)

        result: list[ast.expr] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.If):
                continue
            # Check if ANY statement in the `if` body is `_needs_code_retry = True`
            for stmt in ast.walk(ast.Module(body=node.body, type_ignores=[])):
                if (
                    isinstance(stmt, ast.Assign)
                    and len(stmt.targets) == 1
                    and isinstance(stmt.targets[0], ast.Name)
                    and stmt.targets[0].id == "_needs_code_retry"
                    and isinstance(stmt.value, ast.Constant)
                    and stmt.value.value is True
                ):
                    result.append(node.test)
                    break
        return result

    def test_ast_needs_code_retry_if_found(self) -> None:
        """At least one `If` node guards `_needs_code_retry = True` — sanity check."""
        tests = self._find_needs_code_retry_if_tests()
        assert tests, (
            "No `If` node found that sets `_needs_code_retry = True`. "
            "The retry logic may have been removed or restructured."
        )

    def test_ast_sec_snippets_not_in_condition(self) -> None:
        """AST guard: `sec_snippets` must NOT appear in any `If.test` that guards
        `_needs_code_retry = True`. This verifies the TC-4249 fix at the parsed
        code structure level — not regex on source text."""
        tests = self._find_needs_code_retry_if_tests()
        assert tests, "No if-node found for _needs_code_retry=True — cannot verify"

        for test_expr in tests:
            # Walk all Name nodes in the condition expression
            names_in_cond = {
                node.id for node in ast.walk(test_expr) if isinstance(node, ast.Name)
            }
            assert "sec_snippets" not in names_in_cond, (
                "TC-4249 REGRESSION (AST): `sec_snippets` is referenced in the `If` condition "
                "that guards `_needs_code_retry = True`. This means the retry is still gated "
                "on snippets being present — breaking the fix.\n"
                f"Names in condition: {sorted(names_in_cond)}"
            )

    def test_ast_code_required_roles_in_condition(self) -> None:
        """AST guard: `_CODE_REQUIRED_ROLES` must appear in the condition that guards
        `_needs_code_retry = True`, confirming the role-check is still the gate."""
        tests = self._find_needs_code_retry_if_tests()
        assert tests, "No if-node found for _needs_code_retry=True — cannot verify"

        # At least one condition must reference _CODE_REQUIRED_ROLES
        found = False
        for test_expr in tests:
            names_in_cond = {
                node.id for node in ast.walk(test_expr) if isinstance(node, ast.Name)
            }
            if "_CODE_REQUIRED_ROLES" in names_in_cond:
                found = True
                break

        assert found, (
            "No `If` condition gating `_needs_code_retry = True` references "
            "`_CODE_REQUIRED_ROLES`. The role guard may have been removed."
        )
