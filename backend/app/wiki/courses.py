from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class CourseTemplate:
    """Course-level metadata discovered from a knowledge directory."""

    id: str
    title: str
    description: str
    path: Path
    metadata_course_id: str = ""
    chapter_count: int = 0
    estimated_hours: int = 0
    is_default: bool = False


def discover_course_templates(primary_knowledge_dir: str | Path) -> list[CourseTemplate]:
    """Discover course templates from the configured knowledge directory.

    The configured directory remains the default course. Any sibling directory
    with a metadata.json file is exposed as another course template.
    """
    primary_path = Path(primary_knowledge_dir)
    candidate_dirs: list[Path] = []
    if (primary_path / "metadata.json").exists():
        candidate_dirs.append(primary_path)
        if primary_path.parent.exists():
            candidate_dirs.extend(
                sorted(
                    path
                    for path in primary_path.parent.iterdir()
                    if path.is_dir()
                    and path != primary_path
                    and (path / "metadata.json").exists()
                )
            )
    elif primary_path.exists():
        candidate_dirs.extend(
            sorted(
                path
                for path in primary_path.iterdir()
                if path.is_dir() and (path / "metadata.json").exists()
            )
        )

    courses: list[CourseTemplate] = []
    seen: set[str] = set()
    for index, course_dir in enumerate(candidate_dirs):
        try:
            metadata = _load_metadata(course_dir / "metadata.json")
        except (OSError, json.JSONDecodeError):
            continue

        course_id = _resolve_template_id(course_dir, metadata)
        if not course_id or course_id in seen:
            continue
        seen.add(course_id)

        chapters = metadata.get("chapters")
        objectives = metadata.get("course_objectives")
        description = str(metadata.get("description") or "").strip()
        if not description and isinstance(objectives, list) and objectives:
            description = str(objectives[0])

        courses.append(
            CourseTemplate(
                id=course_id,
                title=str(
                    metadata.get("course_name")
                    or metadata.get("title")
                    or metadata.get("course_name_en")
                    or course_dir.name
                ),
                description=description,
                path=course_dir,
                metadata_course_id=str(metadata.get("course_id") or ""),
                chapter_count=len(chapters) if isinstance(chapters, list) else 0,
                estimated_hours=int(metadata.get("total_estimated_hours") or 0),
                is_default=index == 0,
            )
        )

    return courses


def load_course_metadata(course: CourseTemplate) -> dict[str, Any]:
    return _load_metadata(course.path / "metadata.json")


def normalize_course_id(value: object) -> str:
    """Normalize user/API supplied course ids to URL-safe metadata ids."""
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9_-]+", "_", text)
    return text.strip("_")


def _resolve_template_id(course_dir: Path, metadata: dict[str, Any]) -> str:
    """Resolve a stable API course id.

    Directory names are usually enough, but non-ASCII course folders normalize
    to an empty slug. In that case a metadata-provided slug keeps the template
    addressable from the API.
    """
    candidates = (
        metadata.get("course_slug"),
        metadata.get("template_id"),
        course_dir.name,
        metadata.get("course_id"),
        metadata.get("course_name_en"),
        metadata.get("course_name"),
        metadata.get("title"),
    )
    for candidate in candidates:
        normalized = normalize_course_id(candidate)
        if normalized:
            return normalized
    return ""


def _load_metadata(path: Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        payload = json.load(f)
    return payload if isinstance(payload, dict) else {}
