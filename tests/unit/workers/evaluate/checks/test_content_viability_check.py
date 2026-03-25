"""Tests for check_content_viability — TC-EVAL-502."""
from __future__ import annotations

from launcher.workers.evaluate.checks.content_viability import check_content_viability


class TestContentViabilityCheck:
    def test_substantial_content_no_finding(self) -> None:
        prose = " ".join(["word"] * 100)
        content = f"---\ntitle: test\n---\n\n## Overview\n\n{prose}\n"
        findings = check_content_viability(content, "test/slug")
        assert findings == []

    def test_thin_content_flagged(self) -> None:
        content = "---\ntitle: test\n---\n\n## Overview\n\nShort text here.\n"
        findings = check_content_viability(content, "test/slug")
        assert any("thin content" in f.message.lower() for f in findings)

    def test_skeleton_placeholder_flagged(self) -> None:
        prose = " ".join(["word"] * 100)
        content = f"---\ntitle: test\n---\n\n[Content to be generated]\n\n{prose}\n"
        findings = check_content_viability(content, "test/slug")
        assert any("skeleton" in f.message.lower() or "placeholder" in f.message.lower() for f in findings)

    def test_todo_placeholder_flagged(self) -> None:
        prose = " ".join(["word"] * 100)
        content = f"---\ntitle: test\n---\n\n[TODO: add content]\n\n{prose}\n"
        findings = check_content_viability(content, "test/slug")
        assert any(f.severity == "critical" for f in findings)

    def test_lorem_ipsum_flagged(self) -> None:
        content = "---\ntitle: test\n---\n\nLorem ipsum dolor sit amet " + " ".join(["word"] * 60) + "\n"
        findings = check_content_viability(content, "test/slug")
        assert any("skeleton" in f.message.lower() or "placeholder" in f.message.lower() or "lorem" in f.message.lower() for f in findings)

    def test_code_blocks_not_counted_as_prose(self) -> None:
        code = "```python\n" + "\n".join([f"x = {i}" for i in range(30)]) + "\n```\n"
        content = f"---\ntitle: test\n---\n\n## Code\n\n{code}\nShort intro.\n"
        findings = check_content_viability(content, "test/slug")
        assert any("thin content" in f.message.lower() for f in findings)

    def test_empty_content_flagged(self) -> None:
        content = "---\ntitle: test\n---\n\n## Overview\n"
        findings = check_content_viability(content, "test/slug")
        assert any("thin content" in f.message.lower() for f in findings)
