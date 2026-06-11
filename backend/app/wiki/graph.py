from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from typing import Any

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ConceptNode:
    """知识图谱中的概念节点。"""

    name: str
    chapter: str
    section: str
    course_id: str = ""
    prerequisites: list[str] = field(default_factory=list)
    description: str = ""


class KnowledgeGraph:
    """知识图谱 DAG — 管理概念间的依赖关系。

    从 knowledge_graph.json 加载数据，提供前置知识查询、
    关联概念推荐等功能。
    """

    def __init__(self) -> None:
        self._concepts: dict[str, ConceptNode] = {}
        self._chapter_titles: dict[tuple[str, str], str] = {}
        self._course_titles: dict[str, str] = {}
        self._course_descriptions: dict[str, str] = {}

    def load_from_file(
        self,
        path: str | Path,
        *,
        course_id: str | None = None,
        course_title: str | None = None,
        clear: bool = True,
    ) -> None:
        """从 JSON 文件加载知识图谱。"""
        file_path = Path(path)
        if not file_path.exists():
            logger.warning("知识图谱文件不存在: %s", file_path)
            return

        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)

        self.load_from_dict(
            data,
            course_id=course_id,
            course_title=course_title,
            clear=clear,
        )

    def load_from_dict(
        self,
        data: dict[str, Any],
        *,
        course_id: str | None = None,
        course_title: str | None = None,
        clear: bool = True,
    ) -> None:
        """从字典加载知识图谱（也用于测试）。"""
        if clear:
            self._concepts.clear()
            self._chapter_titles.clear()
            self._course_titles.clear()
            self._course_descriptions.clear()

        resolved_course_id = _resolve_course_id(course_id, data)
        self._course_titles[resolved_course_id] = (
            course_title
            or str(data.get("course_name") or data.get("title") or resolved_course_id)
        )
        description = data.get("description")
        if isinstance(description, str):
            self._course_descriptions[resolved_course_id] = description

        self.load_chapter_metadata(data, course_id=resolved_course_id)
        concepts = data.get("concepts", {})
        if isinstance(concepts, dict) and concepts:
            self._load_concepts_map(concepts, course_id=resolved_course_id)
        else:
            self._load_nodes_and_edges(data, course_id=resolved_course_id)
        logger.info("知识图谱加载完成，共 %d 个概念", len(self._concepts))

    def _load_concepts_map(
        self,
        concepts: dict[str, Any],
        *,
        course_id: str,
    ) -> None:
        """兼容旧版 concepts 字典格式。"""
        for name, info in concepts.items():
            if not isinstance(info, dict):
                continue
            self._concepts[_concept_key(course_id, name)] = ConceptNode(
                name=name,
                chapter=str(info.get("chapter", "")),
                section=str(info.get("section", "")),
                course_id=course_id,
                prerequisites=list(info.get("prerequisites", [])),
                description=str(info.get("description", "")),
            )

    def _load_nodes_and_edges(
        self,
        data: dict[str, Any],
        *,
        course_id: str,
    ) -> None:
        """兼容新版 nodes/edges 图谱格式。"""
        nodes = data.get("nodes", [])
        edges = data.get("edges", [])
        if not isinstance(nodes, list):
            return

        id_to_name: dict[str, str] = {}
        for raw_node in nodes:
            if not isinstance(raw_node, dict):
                continue

            node_id = str(raw_node.get("id") or raw_node.get("name") or "")
            name = str(raw_node.get("name") or node_id)
            if not name:
                continue

            if node_id:
                id_to_name[node_id] = name

            self._concepts[_concept_key(course_id, name)] = ConceptNode(
                name=name,
                chapter=str(
                    raw_node.get("chapter") or raw_node.get("chapter_id") or ""
                ),
                section=str(
                    raw_node.get("section") or raw_node.get("section_id") or ""
                ),
                course_id=course_id,
                prerequisites=[],
                description=self._format_node_description(raw_node),
            )

        if not isinstance(edges, list):
            return

        for raw_edge in edges:
            if not isinstance(raw_edge, dict):
                continue
            source_name = id_to_name.get(
                str(raw_edge.get("source")),
                str(raw_edge.get("source") or ""),
            )
            target_name = id_to_name.get(
                str(raw_edge.get("target")),
                str(raw_edge.get("target") or ""),
            )
            if not source_name or not target_name or source_name == target_name:
                continue
            target = self._concepts.get(_concept_key(course_id, target_name))
            if target is None or _concept_key(course_id, source_name) not in self._concepts:
                continue
            if source_name not in target.prerequisites:
                target.prerequisites.append(source_name)

    def _format_node_description(self, node: dict[str, Any]) -> str:
        description = node.get("description")
        if isinstance(description, str) and description.strip():
            return description.strip()

        parts: list[str] = []
        node_type = node.get("type")
        if isinstance(node_type, str) and node_type:
            parts.append(f"类型：{node_type}")
        difficulty = node.get("difficulty")
        if difficulty is not None:
            parts.append(f"难度：{difficulty}")
        tags = node.get("tags")
        if isinstance(tags, list) and tags:
            parts.append("标签：" + "、".join(str(tag) for tag in tags))
        return "；".join(parts)

    def load_chapter_metadata(
        self,
        data: dict[str, Any],
        *,
        course_id: str | None = None,
    ) -> None:
        """加载章节标题元数据，用于前端展示。"""
        resolved_course_id = _resolve_course_id(course_id, data)
        chapters = data.get("chapters", [])
        if not isinstance(chapters, list):
            return
        for raw_chapter in chapters:
            if not isinstance(raw_chapter, dict):
                continue
            chapter_id = str(
                raw_chapter.get("chapter_id") or raw_chapter.get("id") or ""
            )
            title = str(raw_chapter.get("title") or chapter_id)
            if chapter_id:
                self._chapter_titles[(resolved_course_id, chapter_id)] = title

    def get_concept(
        self,
        name: str,
        course_id: str | None = None,
    ) -> ConceptNode | None:
        """获取单个概念节点。"""
        if course_id:
            return self._concepts.get(_concept_key(course_id, name))

        matches = [node for node in self._concepts.values() if node.name == name]
        if not matches:
            return None
        return sorted(matches, key=lambda node: node.course_id)[0]

    def get_prerequisites(
        self,
        concept: str,
        course_id: str | None = None,
    ) -> list[str]:
        """获取直接前置知识列表。"""
        node = self.get_concept(concept, course_id=course_id)
        if node is None:
            return []
        return list(node.prerequisites)

    def get_all_prerequisites(
        self,
        concept: str,
        course_id: str | None = None,
    ) -> list[str]:
        """递归获取全部前置知识（拓扑排序），不含自身。"""
        visited: set[tuple[str, str]] = set()
        order: list[str] = []
        self._dfs_prerequisites(concept, course_id, visited, order)
        # 移除自身
        if concept in order:
            order.remove(concept)
        return order

    def _dfs_prerequisites(
        self,
        concept: str,
        course_id: str | None,
        visited: set[tuple[str, str]],
        order: list[str],
    ) -> None:
        node = self.get_concept(concept, course_id=course_id)
        if node is None:
            return

        key = (node.course_id, node.name)
        if key in visited:
            return
        visited.add(key)

        for prereq in node.prerequisites:
            self._dfs_prerequisites(prereq, node.course_id, visited, order)

        order.append(concept)

    def get_dependents(
        self,
        concept: str,
        course_id: str | None = None,
    ) -> list[str]:
        """获取依赖此概念的所有概念（反向边）。"""
        dependents: list[str] = []
        for node in self._concepts.values():
            if course_id and node.course_id != course_id:
                continue
            if concept in node.prerequisites:
                dependents.append(node.name)
        return dependents

    def get_related(
        self,
        concept: str,
        course_id: str | None = None,
    ) -> list[str]:
        """获取关联概念：同章节 + 共享前置知识的概念。"""
        node = self.get_concept(concept, course_id=course_id)
        if node is None:
            return []

        related: set[str] = set()

        # 同章节的概念
        for other in self._concepts.values():
            if other.course_id != node.course_id:
                continue
            if other.name != concept and other.chapter == node.chapter:
                related.add(other.name)

        # 共享前置知识的概念
        prereq_set = set(node.prerequisites)
        for other in self._concepts.values():
            if other.course_id != node.course_id:
                continue
            if other.name != concept and prereq_set & set(other.prerequisites):
                related.add(other.name)

        return sorted(related)

    def get_chapter_concepts(
        self,
        chapter_id: str,
        course_id: str | None = None,
    ) -> list[ConceptNode]:
        """获取某章所有概念节点。"""
        return [
            node
            for node in self._concepts.values()
            if node.chapter == chapter_id
            and (course_id is None or node.course_id == course_id)
        ]

    def list_all_concepts(self, course_id: str | None = None) -> list[str]:
        """返回所有概念名称。"""
        return sorted(
            {
                node.name
                for node in self._concepts.values()
                if course_id is None or node.course_id == course_id
            }
        )

    def list_chapters(self, course_id: str | None = None) -> list[dict[str, str]]:
        """列出所有章节（去重）。"""
        chapters: dict[tuple[str, str], str] = {}
        for node in self._concepts.values():
            if course_id and node.course_id != course_id:
                continue
            chapter_key = (node.course_id, node.chapter)
            if node.chapter and chapter_key not in chapters:
                chapters[chapter_key] = self._chapter_titles.get(
                    chapter_key, node.chapter
                )
        include_course_id = course_id is not None or len(
            {course for course, _ in chapters}
        ) > 1
        items: list[dict[str, str]] = []
        for (course, cid), title in sorted(chapters.items()):
            item = {"id": cid, "title": title}
            if include_course_id:
                item["course_id"] = course
            items.append(item)
        return items

    def list_courses(self) -> list[dict[str, str | int]]:
        """列出当前知识图谱中可用课程。"""
        course_ids = sorted({node.course_id for node in self._concepts.values()})
        return [
            {
                "id": course_id,
                "title": self._course_titles.get(course_id, course_id),
                "description": self._course_descriptions.get(course_id, ""),
                "concept_count": len(self.list_all_concepts(course_id)),
                "chapter_count": len(self.list_chapters(course_id)),
            }
            for course_id in course_ids
        ]


def _resolve_course_id(course_id: str | None, data: dict[str, Any]) -> str:
    value = course_id or data.get("course_slug") or data.get("course_id") or "default"
    return str(value)


def _concept_key(course_id: str, name: object) -> str:
    return f"{course_id}:{name}"
