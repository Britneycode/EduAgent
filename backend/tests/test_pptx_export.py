from __future__ import annotations

from io import BytesIO
from zipfile import ZipFile

from app.core.pptx_export import build_pptx, parse_ppt_outline


def test_parse_ppt_outline_from_page_headings() -> None:
    slides = parse_ppt_outline(
        "## 第1页：封面\n- 课程主题\n\n## 第2页：核心概念\n- 状态空间\n- 搜索树",
        fallback_title="搜索算法",
    )

    assert [slide.title for slide in slides] == ["封面", "核心概念"]
    assert slides[0].bullets == ["课程主题"]
    assert slides[1].bullets == ["状态空间", "搜索树"]


def test_build_pptx_creates_valid_package() -> None:
    payload = build_pptx(
        "搜索算法教学演示",
        "## 第1页：封面\n- 搜索算法\n\n## 第2页：A* 搜索\n- f(n)=g(n)+h(n)",
    )

    with ZipFile(BytesIO(payload)) as package:
        names = set(package.namelist())
        assert "[Content_Types].xml" in names
        assert "ppt/presentation.xml" in names
        assert "ppt/slides/slide1.xml" in names
        assert "ppt/slides/slide2.xml" in names
        slide_two = package.read("ppt/slides/slide2.xml").decode("utf-8")

    assert "A* 搜索" in slide_two
    assert "f(n)=g(n)+h(n)" in slide_two
