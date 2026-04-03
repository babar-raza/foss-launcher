"""TC-5303: Tests for _normalize_internal_links() post-processor in worker.py.

Verifies that subdomain-prefixed internal Aspose markdown link paths are
converted to site-relative paths, while external https:// links are preserved.
"""
from __future__ import annotations

from launcher.models.page_ir import BlockIR, BlockType
from launcher.workers.generate.worker import _normalize_internal_links


def _para(content: str) -> BlockIR:
    return BlockIR(type=BlockType.paragraph, content=content)


def _list_block(items: list[str]) -> BlockIR:
    return BlockIR(type=BlockType.list, items=items)


def _code_block(content: str) -> BlockIR:
    return BlockIR(type=BlockType.code, content=content, language="csharp")


# ---------------------------------------------------------------------------
# TC-5303-T1: Strip /docs.aspose.org prefix from markdown link URL
# ---------------------------------------------------------------------------


def test_normalize_strips_docs_prefix():
    """TC-5303-T1: /docs.aspose.org prefix stripped from markdown link."""
    blocks = [_para("See [Model Loading](/docs.aspose.org/3d/dotnet/developer-guide/model-loading.md).")]
    result = _normalize_internal_links(blocks)
    assert len(result) == 1
    assert "/docs.aspose.org" not in result[0].content
    assert "](/3d/dotnet/developer-guide/model-loading.md)" in result[0].content


# ---------------------------------------------------------------------------
# TC-5303-T2: Strip /kb.aspose.org prefix
# ---------------------------------------------------------------------------


def test_normalize_strips_kb_prefix():
    """TC-5303-T2: /kb.aspose.org prefix stripped from markdown link."""
    blocks = [_para("See the [FAQ](/kb.aspose.org/3d/dotnet/faq.md) page.")]
    result = _normalize_internal_links(blocks)
    assert "/kb.aspose.org" not in result[0].content
    assert "](/3d/dotnet/faq.md)" in result[0].content


# ---------------------------------------------------------------------------
# TC-5303-T3: Preserve https:// external links unchanged
# ---------------------------------------------------------------------------


def test_normalize_preserves_https_external_links():
    """TC-5303-T3: External https:// links are not modified."""
    content = "See [GitHub](https://github.com/aspose-3d/Aspose.3D-for-.NET) for source."
    blocks = [_para(content)]
    result = _normalize_internal_links(blocks)
    assert result[0].content == content


# ---------------------------------------------------------------------------
# TC-5303-T4: Preserve already-site-relative links unchanged
# ---------------------------------------------------------------------------


def test_normalize_preserves_already_relative_links():
    """TC-5303-T4: Already-correct site-relative /path links are unchanged."""
    content = "See [Model Loading](/3d/dotnet/developer-guide/model-loading.md)."
    blocks = [_para(content)]
    result = _normalize_internal_links(blocks)
    assert result[0].content == content


# ---------------------------------------------------------------------------
# TC-5303-T5: Normalize links in list block items
# ---------------------------------------------------------------------------


def test_normalize_strips_prefix_in_list_items():
    """TC-5303-T5: List block items with subdomain prefix links are also fixed."""
    items = [
        "[Model Loading](/docs.aspose.org/3d/dotnet/developer-guide/model-loading.md)",
        "[FAQ](/kb.aspose.org/3d/dotnet/faq.md)",
        "Plain item with no link",
    ]
    blocks = [_list_block(items)]
    result = _normalize_internal_links(blocks)
    assert "/docs.aspose.org" not in result[0].items[0]
    assert "/kb.aspose.org" not in result[0].items[1]
    assert result[0].items[2] == "Plain item with no link"


# ---------------------------------------------------------------------------
# TC-5303-T6: Code blocks are not modified
# ---------------------------------------------------------------------------


def test_normalize_does_not_modify_code_blocks():
    """TC-5303-T6: Links inside code blocks are not touched (they're not prose links)."""
    code = 'var url = "/docs.aspose.org/3d/dotnet/";\n// This is code, not a link'
    blocks = [_code_block(code)]
    result = _normalize_internal_links(blocks)
    # Code block content should be unchanged (the regex looks for ]( pattern — not in code)
    assert result[0].content == code


# ---------------------------------------------------------------------------
# TC-5303-T7: Multiple subdomain variants stripped
# ---------------------------------------------------------------------------


def test_normalize_strips_all_subdomain_variants():
    """TC-5303-T7: All supported subdomain variants are stripped."""
    content = (
        "[Docs](/docs.aspose.org/3d/dotnet/x) "
        "[KB](/kb.aspose.org/3d/dotnet/y) "
        "[Blog](/blog.aspose.org/3d/dotnet/z)"
    )
    blocks = [_para(content)]
    result = _normalize_internal_links(blocks)
    out = result[0].content
    assert "/docs.aspose.org" not in out
    assert "/kb.aspose.org" not in out
    assert "/blog.aspose.org" not in out
    assert "](/3d/dotnet/x)" in out
    assert "](/3d/dotnet/y)" in out
    assert "](/3d/dotnet/z)" in out
