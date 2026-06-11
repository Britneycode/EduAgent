from __future__ import annotations

from io import BytesIO
from zipfile import ZipFile

from app.core.video_export import (
    build_animation_export_package,
    build_srt,
    build_webvtt,
    parse_animation_script,
)


ANIMATION_SCRIPT = """\
## 镜头 1：问题引入
时长：5秒
旁白：我们先观察搜索算法如何展开状态空间。
画面：节点从起点向外扩展。
学习目的：理解状态空间展开。

## 镜头 2：启发式估计
时长：00:07
旁白：启发式函数帮助算法优先探索更有希望的节点。
画面：较短路径被高亮。
公式：f(n)=g(n)+h(n)
"""


def test_parse_animation_script_extracts_scenes_and_durations() -> None:
    scenes = parse_animation_script(ANIMATION_SCRIPT)

    assert len(scenes) == 2
    assert scenes[0].title == "问题引入"
    assert scenes[0].duration_sec == 5
    assert scenes[1].duration_sec == 7
    assert "启发式函数" in scenes[1].narration


def test_animation_subtitles_use_scene_timeline() -> None:
    scenes = parse_animation_script(ANIMATION_SCRIPT)

    webvtt = build_webvtt(scenes)
    srt = build_srt(scenes)

    assert "WEBVTT" in webvtt
    assert "00:00:00.000 --> 00:00:05.000" in webvtt
    assert "00:00:05,000 --> 00:00:12,000" in srt


def test_build_animation_export_package_contains_player_subtitles_and_audio() -> None:
    payload = build_animation_export_package(
        title="搜索算法动画",
        content=ANIMATION_SCRIPT,
        audio=b"fake-mp3",
    )

    with ZipFile(BytesIO(payload)) as package:
        names = set(package.namelist())
        manifest = package.read("manifest.json").decode("utf-8")
        index_html = package.read("index.html").decode("utf-8")

    assert {
        "index.html",
        "subtitles.vtt",
        "subtitles.srt",
        "script.md",
        "manifest.json",
        "narration.mp3",
    }.issubset(names)
    assert '"has_audio": true' in manifest
    assert "搜索算法动画" in index_html
