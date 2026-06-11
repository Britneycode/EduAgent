from __future__ import annotations

import html
import json
import re
from dataclasses import asdict, dataclass
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile


@dataclass(slots=True)
class AnimationScene:
    index: int
    title: str
    narration: str
    visuals: str
    formula: str
    purpose: str
    duration: str
    notes: str
    duration_sec: int


CHINESE_NUMERAL = "零一二三四五六七八九十"
EXPLICIT_SCENE_MARKER = re.compile(
    rf"^(?:#{{1,6}}\s*)?(?:[-*+]\s*)?(?:\*\*)?\s*"
    rf"(?:第\s*[\d{CHINESE_NUMERAL}]+\s*(?:个)?\s*)?"
    rf"(?:镜头|分镜|场景|片段|Scene)\s*[\d{CHINESE_NUMERAL}]*"
    rf"\s*(?:\*\*)?\s*[：:.\-\s]*(.*)$",
    re.IGNORECASE,
)
NUMBERED_SCENE_MARKER = re.compile(
    rf"^(?:#{{1,6}}\s*)?(?:[-*+]\s*)?(?:\*\*)?\s*"
    rf"[\d{CHINESE_NUMERAL}]+\s*[.、]\s*(?:镜头|分镜|场景|片段)"
    rf"\s*[：:.\-\s]*(.*)$",
    re.IGNORECASE,
)


def build_animation_export_package(
    *,
    title: str,
    content: str,
    audio: bytes | None = None,
) -> bytes:
    """Build a portable animation package with HTML player and subtitles."""
    scenes = parse_animation_script(content)
    if not scenes:
        scenes = [
            AnimationScene(
                index=0,
                title=title or "动画讲解",
                narration=content.strip() or "暂无旁白。",
                visuals=content.strip() or "暂无画面说明。",
                formula="",
                purpose="",
                duration="",
                notes="",
                duration_sec=6,
            )
        ]

    manifest = {
        "title": title,
        "scene_count": len(scenes),
        "duration_sec": sum(scene.duration_sec for scene in scenes),
        "has_audio": audio is not None,
        "files": [
            "index.html",
            "subtitles.vtt",
            "subtitles.srt",
            "script.md",
            "manifest.json",
        ],
    }
    if audio is not None:
        manifest["files"].append("narration.mp3")

    buffer = BytesIO()
    with ZipFile(buffer, mode="w", compression=ZIP_DEFLATED) as package:
        package.writestr("index.html", build_animation_html(title, scenes, audio is not None))
        package.writestr("subtitles.vtt", build_webvtt(scenes))
        package.writestr("subtitles.srt", build_srt(scenes))
        package.writestr("script.md", content)
        package.writestr(
            "manifest.json",
            json.dumps(manifest, ensure_ascii=False, indent=2),
        )
        if audio is not None:
            package.writestr("narration.mp3", audio)
    return buffer.getvalue()


def parse_animation_script(content: str) -> list[AnimationScene]:
    normalized = content.replace("\r\n", "\n").strip()
    if not normalized:
        return []

    drafts: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    current_field: str | None = None

    for line in normalized.split("\n"):
        scene_title = _extract_scene_title(line)
        if scene_title is not None:
            current = _empty_scene(scene_title)
            drafts.append(current)
            current_field = None
            continue

        if current is None:
            continue

        field = _classify_field(line)
        if field is not None:
            current_field, value = field
            _append(current, current_field, value)
            continue

        cleaned = _clean_line(line)
        if not cleaned:
            current_field = None
            continue
        _append(current, current_field or "notes", cleaned)

    if not drafts:
        drafts = _fallback_scene_drafts(normalized)

    scenes: list[AnimationScene] = []
    for index, draft in enumerate(drafts):
        duration = _normalize(draft.get("duration", ""))
        scenes.append(
            AnimationScene(
                index=index,
                title=_normalize(draft.get("title", "")) or f"镜头 {index + 1}",
                narration=_normalize(draft.get("narration", "")),
                visuals=_normalize(draft.get("visuals", "")),
                formula=_normalize(draft.get("formula", "")),
                purpose=_normalize(draft.get("purpose", "")),
                duration=duration,
                notes=_normalize(draft.get("notes", "")),
                duration_sec=_parse_duration_sec(duration),
            )
        )
    return scenes


def build_webvtt(scenes: list[AnimationScene]) -> str:
    lines = ["WEBVTT", ""]
    cursor = 0
    for scene in scenes:
        start = cursor
        end = cursor + scene.duration_sec
        lines.append(f"{_format_vtt_timestamp(start)} --> {_format_vtt_timestamp(end)}")
        lines.append(scene.narration or scene.title)
        lines.append("")
        cursor = end
    return "\n".join(lines)


def build_srt(scenes: list[AnimationScene]) -> str:
    lines: list[str] = []
    cursor = 0
    for index, scene in enumerate(scenes, start=1):
        start = cursor
        end = cursor + scene.duration_sec
        lines.append(str(index))
        lines.append(f"{_format_srt_timestamp(start)} --> {_format_srt_timestamp(end)}")
        lines.append(scene.narration or scene.title)
        lines.append("")
        cursor = end
    return "\n".join(lines)


def build_animation_html(
    title: str,
    scenes: list[AnimationScene],
    has_audio: bool,
) -> str:
    scene_json = json.dumps([asdict(scene) for scene in scenes], ensure_ascii=False)
    audio_markup = (
        '<audio controls src="narration.mp3" class="audio"></audio>'
        if has_audio
        else '<p class="audio-note">未包含旁白音频：请启用讯飞 TTS 后重新导出。</p>'
    )
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{html.escape(title)} 动画导出</title>
  <style>
    :root {{
      color-scheme: dark;
      font-family: Inter, "Microsoft YaHei", system-ui, sans-serif;
      background: #24221b;
      color: #fff8f0;
    }}
    body {{
      margin: 0;
      min-height: 100vh;
      display: grid;
      place-items: center;
      background:
        radial-gradient(circle at 15% 10%, rgba(201,100,66,.3), transparent 28%),
        radial-gradient(circle at 85% 80%, rgba(107,142,107,.26), transparent 30%),
        #24221b;
    }}
    main {{
      width: min(1080px, calc(100vw - 32px));
    }}
    .stage {{
      aspect-ratio: 16 / 9;
      border: 1px solid rgba(255,255,255,.12);
      border-radius: 18px;
      padding: 28px;
      overflow: hidden;
      background:
        linear-gradient(rgba(255,255,255,.08) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,.08) 1px, transparent 1px),
        rgba(20,19,16,.7);
      background-size: 36px 36px;
      box-shadow: 0 24px 80px rgba(0,0,0,.35);
    }}
    .meta {{
      display: flex;
      justify-content: space-between;
      gap: 16px;
      color: #c8c4b8;
      font-size: 12px;
      letter-spacing: .16em;
      text-transform: uppercase;
    }}
    h1 {{
      margin: 18px 0 28px;
      font-size: clamp(26px, 4vw, 52px);
      line-height: 1.08;
      max-width: 780px;
    }}
    .scene-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 28px;
      align-items: center;
    }}
    .orb {{
      width: min(300px, 42vw);
      aspect-ratio: 1;
      border-radius: 999px;
      border: 1px dashed rgba(240,195,109,.5);
      display: grid;
      place-items: center;
      margin: 0 auto;
      position: relative;
    }}
    .orb::before {{
      content: "";
      width: 52%;
      aspect-ratio: 1;
      border-radius: 26px;
      background: #c96442;
      box-shadow: 0 0 48px rgba(201,100,66,.45);
      animation: pulse 2.6s ease-in-out infinite;
    }}
    .caption {{
      font-size: clamp(16px, 2vw, 24px);
      line-height: 1.7;
      color: #e8e0d4;
    }}
    .chips {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 16px;
    }}
    .chip {{
      border: 1px solid rgba(255,255,255,.13);
      border-radius: 999px;
      padding: 6px 10px;
      color: #f5f4ed;
      background: rgba(255,255,255,.08);
      font-size: 12px;
    }}
    .controls {{
      margin-top: 18px;
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      align-items: center;
    }}
    button {{
      border: 1px solid rgba(255,255,255,.18);
      border-radius: 10px;
      background: rgba(255,255,255,.1);
      color: #fff8f0;
      padding: 9px 14px;
      cursor: pointer;
    }}
    .progress {{
      flex: 1;
      min-width: 180px;
      height: 8px;
      border-radius: 999px;
      overflow: hidden;
      background: rgba(255,255,255,.14);
    }}
    .bar {{
      height: 100%;
      width: 0;
      background: #c96442;
      transition: width .2s linear;
    }}
    .audio, .audio-note {{
      width: 100%;
      margin-top: 12px;
      color: #c8c4b8;
    }}
    @keyframes pulse {{
      0%, 100% {{ transform: scale(1) rotate(0deg); }}
      50% {{ transform: scale(1.12) rotate(8deg); }}
    }}
    @media (max-width: 720px) {{
      .stage {{ padding: 18px; }}
      .scene-grid {{ grid-template-columns: 1fr; }}
      .orb {{ width: min(240px, 70vw); }}
    }}
  </style>
</head>
<body>
  <main>
    <div class="stage">
      <div class="meta">
        <span>{html.escape(title)}</span>
        <span id="counter"></span>
      </div>
      <h1 id="scene-title"></h1>
      <div class="scene-grid">
        <div class="orb" aria-hidden="true"></div>
        <div>
          <p class="caption" id="caption"></p>
          <div class="chips" id="chips"></div>
        </div>
      </div>
    </div>
    <div class="controls">
      <button type="button" id="prev">上一镜</button>
      <button type="button" id="play">播放</button>
      <button type="button" id="next">下一镜</button>
      <div class="progress"><div class="bar" id="bar"></div></div>
    </div>
    {audio_markup}
  </main>
  <script>
    const scenes = {scene_json};
    let index = 0;
    let playing = false;
    let startedAt = Date.now();
    let timer = null;
    const titleEl = document.getElementById("scene-title");
    const captionEl = document.getElementById("caption");
    const counterEl = document.getElementById("counter");
    const chipsEl = document.getElementById("chips");
    const barEl = document.getElementById("bar");
    const playEl = document.getElementById("play");
    function cues(scene) {{
      const source = scene.visuals || scene.formula || scene.notes || scene.narration || scene.title;
      return source.replace(/[；;]/g, "\\n").replace(/[，,、]/g, "\\n")
        .split("\\n").map((item) => item.trim()).filter(Boolean).slice(0, 5);
    }}
    function render() {{
      const scene = scenes[index] || scenes[0];
      titleEl.textContent = scene.title;
      captionEl.textContent = scene.narration || scene.purpose || scene.visuals || scene.notes;
      counterEl.textContent = `${{index + 1}} / ${{scenes.length}}`;
      chipsEl.innerHTML = cues(scene).map((cue) => `<span class="chip">${{cue}}</span>`).join("");
      barEl.style.width = `${{(index / scenes.length) * 100}}%`;
    }}
    function move(delta) {{
      index = (index + delta + scenes.length) % scenes.length;
      startedAt = Date.now();
      render();
    }}
    function tick() {{
      const scene = scenes[index] || scenes[0];
      const elapsed = (Date.now() - startedAt) / 1000;
      const local = Math.min(1, elapsed / scene.duration_sec);
      barEl.style.width = `${{((index + local) / scenes.length) * 100}}%`;
      if (local >= 1) move(1);
    }}
    document.getElementById("prev").onclick = () => move(-1);
    document.getElementById("next").onclick = () => move(1);
    playEl.onclick = () => {{
      playing = !playing;
      playEl.textContent = playing ? "暂停" : "播放";
      if (playing) {{
        startedAt = Date.now();
        timer = setInterval(tick, 200);
      }} else if (timer) {{
        clearInterval(timer);
        timer = null;
      }}
    }};
    render();
  </script>
</body>
</html>
"""


def _extract_scene_title(line: str) -> str | None:
    cleaned = _clean_line(line.replace("#", ""))
    if not cleaned:
        return None
    explicit = EXPLICIT_SCENE_MARKER.match(cleaned)
    if explicit:
        return explicit.group(1).strip() or cleaned
    numbered = NUMBERED_SCENE_MARKER.match(cleaned)
    if numbered:
        return numbered.group(1).strip() or cleaned
    return None


def _classify_field(line: str) -> tuple[str, str] | None:
    cleaned = _clean_line(line)
    match = re.match(r"^([^：:]{1,12})[：:]\s*(.*)$", cleaned)
    if not match:
        return None
    label, value = match.group(1).strip(), match.group(2).strip()
    if re.match(r"^(旁白|解说|讲解词|台词)$", label):
        return "narration", value
    if re.match(r"^(画面|画面元素|视觉|视觉元素|可视化|动画|动作|镜头说明)$", label):
        return "visuals", value
    if re.match(r"^(关键公式|公式|代码|关键代码|可视化建议|公式或代码)$", label):
        return "formula", value
    if re.match(r"^(学习目的|目的|意图|目标)$", label):
        return "purpose", value
    if re.match(r"^(时长|时间|预计时长)$", label):
        return "duration", value
    return None


def _fallback_scene_drafts(content: str) -> list[dict[str, str]]:
    paragraphs = [
        _normalize(item)
        for item in re.split(r"\n{2,}", re.sub(r"^#{1,2}\s+.*$", "", content, flags=re.MULTILINE))
        if _normalize(item)
    ]
    source = paragraphs or [_normalize(content)]
    count = min(6, max(1, len(source)))
    bucket_size = max(1, (len(source) + count - 1) // count)
    drafts = []
    for index in range(count):
        body = "\n\n".join(source[index * bucket_size : (index + 1) * bucket_size])
        if body:
            drafts.append(
                {
                    **_empty_scene(f"片段 {index + 1}"),
                    "narration": body,
                    "visuals": body,
                }
            )
    return drafts


def _empty_scene(title: str) -> dict[str, str]:
    return {
        "title": title,
        "narration": "",
        "visuals": "",
        "formula": "",
        "purpose": "",
        "duration": "",
        "notes": "",
    }


def _append(scene: dict[str, str], field: str, value: str) -> None:
    if not value:
        return
    scene[field] = f"{scene[field]}\n{value}".strip() if scene.get(field) else value


def _clean_line(line: str) -> str:
    return (
        line.replace("**", "")
        .strip()
        .lstrip("-*+> ")
        .strip()
    )


def _normalize(value: str) -> str:
    return "\n".join(line.strip() for line in value.splitlines() if line.strip()).strip()


def _parse_duration_sec(value: str) -> int:
    if not value:
        return 6
    normalized = value.strip()
    clock = re.match(r"^(\d{1,2}):(\d{2})$", normalized)
    if clock:
        return max(1, int(clock.group(1)) * 60 + int(clock.group(2)))
    numbers = [float(item) for item in re.findall(r"\d+(?:\.\d+)?", normalized)]
    if not numbers:
        return 6
    amount = sum(numbers) / len(numbers)
    if "分钟" in normalized or "min" in normalized.lower():
        amount *= 60
    return max(1, min(180, round(amount)))


def _format_vtt_timestamp(seconds: int) -> str:
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours:02}:{minutes:02}:{secs:02}.000"


def _format_srt_timestamp(seconds: int) -> str:
    return _format_vtt_timestamp(seconds).replace(".", ",")
