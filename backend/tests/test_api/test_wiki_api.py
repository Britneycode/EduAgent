from __future__ import annotations

from fastapi.testclient import TestClient


def _register(client: TestClient, username: str) -> str:
    response = client.post(
        "/api/auth/register",
        json={"username": username, "password": "password123"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_wiki_upload_markdown_then_search(client: TestClient) -> None:
    token = _register(client, "wiki_upload_user")
    headers = {"Authorization": f"Bearer {token}"}

    upload = client.post(
        "/api/wiki/upload",
        headers=headers,
        files={
            "file": (
                "graph-search-notes.md",
                (
                    "# 图搜索课堂资料\n\n"
                    "## A* 搜索\n\n"
                    "A* 搜索结合路径代价和启发式估计，适合最短路径规划。"
                    "开放列表用于保存候选节点，关闭列表用于避免重复展开。"
                ).encode("utf-8"),
                "text/markdown",
            )
        },
    )
    assert upload.status_code == 200
    upload_data = upload.json()
    assert upload_data["success"] is True
    assert upload_data["chunk_count"] >= 1

    search = client.post(
        "/api/wiki/search",
        headers=headers,
        json={"query": "A* 搜索 开放列表", "top_k": 5},
    )
    assert search.status_code == 200
    results = search.json()["results"]
    assert any("开放列表" in item["content"] for item in results)


def test_wiki_courses_can_filter_chapters_and_search(client: TestClient) -> None:
    token = _register(client, "wiki_course_user")
    headers = {"Authorization": f"Bearer {token}"}

    courses = client.get("/api/wiki/courses", headers=headers)
    assert courses.status_code == 200
    course_ids = {course["id"] for course in courses.json()}
    assert {"ai_intro", "computer_networks"}.issubset(course_ids)

    chapters = client.get(
        "/api/wiki/chapters?course_id=computer_networks",
        headers=headers,
    )
    assert chapters.status_code == 200
    assert [chapter["id"] for chapter in chapters.json()][:2] == ["cn01", "cn02"]

    search = client.post(
        "/api/wiki/search",
        headers=headers,
        json={
            "query": "HTTP HTTPS 请求流程",
            "top_k": 5,
            "course_id": "computer_networks",
        },
    )
    assert search.status_code == 200
    results = search.json()["results"]
    assert results
    assert {item["course_id"] for item in results} == {"computer_networks"}
    assert any("HTTP" in item["content"] or "HTTPS" in item["content"] for item in results)
