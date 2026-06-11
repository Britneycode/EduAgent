from __future__ import annotations

from io import BytesIO
from zipfile import ZipFile

import pytest
from httpx import ASGITransport, AsyncClient

from app.agents.resource_types import AgentResource
from app.core.database import AsyncSessionLocal
from app.core.storage import LocalAssetStorage
from app.main import app
from app.services.chat_service import ChatService


async def _register_and_get_auth(
    client: AsyncClient,
    username: str,
) -> tuple[int, dict[str, str]]:
    response = await client.post(
        "/api/auth/register",
        json={"username": username, "password": "password123"},
    )
    assert response.status_code == 200
    data = response.json()
    return data["user_id"], {"Authorization": f"Bearer {data['access_token']}"}


class StubTTSClient:
    def __init__(self) -> None:
        self.text = ""

    async def synthesize(self, text: str) -> bytes:
        self.text = text
        return b"fake-mp3"


@pytest.mark.asyncio
async def test_resource_speech_returns_mp3_for_owner(monkeypatch) -> None:
    from app.api import resources as resources_api

    stub_tts = StubTTSClient()
    monkeypatch.setattr(resources_api, "get_xunfei_tts_client", lambda: stub_tts)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        user_id, headers = await _register_and_get_auth(client, "speech_owner")
        async with AsyncSessionLocal() as db:
            service = ChatService(session=db)
            session_id = await service.create_session(user_id=user_id)
            resource = await service.save_resource(
                session_id=session_id,
                resource_type="document",
                title="反向传播讲义",
                content="# 反向传播\n\n这是一份讲义。",
                knowledge_point="反向传播",
            )

        response = await client.post(
            f"/api/resources/{resource.id}/speech",
            headers=headers,
        )

    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/mpeg"
    assert response.content == b"fake-mp3"
    assert "学习文档：反向传播讲义" in stub_tts.text


@pytest.mark.asyncio
async def test_resource_speech_returns_503_when_tts_disabled(monkeypatch) -> None:
    from app.api import resources as resources_api

    monkeypatch.setattr(resources_api, "get_xunfei_tts_client", lambda: None)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        user_id, headers = await _register_and_get_auth(client, "speech_disabled")
        async with AsyncSessionLocal() as db:
            service = ChatService(session=db)
            session_id = await service.create_session(user_id=user_id)
            resource = await service.save_resource(
                session_id=session_id,
                resource_type="document",
                title="测试文档",
                content="内容",
            )

        response = await client.post(
            f"/api/resources/{resource.id}/speech",
            headers=headers,
        )

    assert response.status_code == 503
    assert response.json()["detail"] == "讯飞 TTS 未启用"


@pytest.mark.asyncio
async def test_execute_code_resource_returns_stdout_for_owner() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        user_id, headers = await _register_and_get_auth(client, "code_runner_owner")
        async with AsyncSessionLocal() as db:
            service = ChatService(session=db)
            session_id = await service.create_session(user_id=user_id)
            resource = await service.save_resource(
                session_id=session_id,
                resource_type="code",
                title="Python 示例",
                content="```python\nprint(1 + 2)\n```",
                knowledge_point="Python",
            )

        response = await client.post(
            f"/api/resources/{resource.id}/execute",
            json={"code_index": 0},
            headers=headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["stdout"].strip() == "3"
    assert data["stderr"] == ""


@pytest.mark.asyncio
async def test_execute_code_resource_blocks_unsafe_code() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        user_id, headers = await _register_and_get_auth(client, "code_runner_block")
        async with AsyncSessionLocal() as db:
            service = ChatService(session=db)
            session_id = await service.create_session(user_id=user_id)
            resource = await service.save_resource(
                session_id=session_id,
                resource_type="code",
                title="危险示例",
                content="```python\nimport os\nprint(os.getcwd())\n```",
            )

        response = await client.post(
            f"/api/resources/{resource.id}/execute",
            headers=headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "blocked"
    assert "不允许导入模块" in data["stderr"]


@pytest.mark.asyncio
async def test_execute_non_code_resource_returns_400() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        user_id, headers = await _register_and_get_auth(client, "code_runner_non_code")
        async with AsyncSessionLocal() as db:
            service = ChatService(session=db)
            session_id = await service.create_session(user_id=user_id)
            resource = await service.save_resource(
                session_id=session_id,
                resource_type="document",
                title="讲义",
                content="不是代码",
            )

        response = await client.post(
            f"/api/resources/{resource.id}/execute",
            headers=headers,
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "只有代码实践资源可以执行"


@pytest.mark.asyncio
async def test_set_resource_favorite_and_list_prioritizes_favorites() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        user_id, headers = await _register_and_get_auth(client, "resource_favorite")
        async with AsyncSessionLocal() as db:
            service = ChatService(session=db)
            session_id = await service.create_session(user_id=user_id)
            regular = await service.save_resource(
                session_id=session_id,
                resource_type="document",
                title="普通资源",
                content="内容 A",
            )
            favorite = await service.save_resource(
                session_id=session_id,
                resource_type="document",
                title="收藏资源",
                content="内容 B",
            )

        response = await client.patch(
            f"/api/resources/{favorite.id}/favorite",
            json={"is_favorite": True},
            headers=headers,
        )
        list_response = await client.get("/api/resources", headers=headers)

    assert response.status_code == 200
    assert response.json()["is_favorite"] is True
    items = list_response.json()
    assert items[0]["id"] == favorite.id
    assert items[0]["is_favorite"] is True
    assert any(item["id"] == regular.id for item in items)


@pytest.mark.asyncio
async def test_regenerate_resource_updates_only_target_resource(monkeypatch) -> None:
    from app.api import resources as resources_api

    called: dict[str, int] = {}

    async def fake_generate_replacement_resource(**kwargs) -> AgentResource:
        called["resource_id"] = kwargs["resource"].id
        return AgentResource(
            title="新版反向传播讲义",
            resource_type="document",
            content="新版讲义正文，包含更多步骤。",
            knowledge_point="反向传播",
            agent_name="DocAgent",
        )

    monkeypatch.setattr(
        resources_api,
        "_generate_replacement_resource",
        fake_generate_replacement_resource,
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        user_id, headers = await _register_and_get_auth(client, "resource_regenerate")
        async with AsyncSessionLocal() as db:
            service = ChatService(session=db)
            session_id = await service.create_session(user_id=user_id)
            target = await service.save_resource(
                session_id=session_id,
                resource_type="document",
                title="旧讲义",
                content="旧内容",
                knowledge_point="反向传播",
            )
            other = await service.save_resource(
                session_id=session_id,
                resource_type="quiz",
                title="练习题",
                content='{"questions":[]}',
            )

        response = await client.post(
            f"/api/resources/{target.id}/regenerate",
            headers=headers,
        )
        other_response = await client.get(
            f"/api/resources/{other.id}",
            headers=headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert called["resource_id"] == target.id
    assert data["id"] == target.id
    assert data["title"] == "新版反向传播讲义"
    assert "新版讲义正文" in data["content"]
    assert other_response.json()["title"] == "练习题"


@pytest.mark.asyncio
async def test_export_resource_markdown_for_owner() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        user_id, headers = await _register_and_get_auth(client, "resource_export")
        async with AsyncSessionLocal() as db:
            service = ChatService(session=db)
            session_id = await service.create_session(user_id=user_id)
            resource = await service.save_resource(
                session_id=session_id,
                resource_type="reading",
                title="拓展阅读",
                content="阅读内容",
                knowledge_point="搜索",
                agent_name="ReadingAgent",
            )

        response = await client.get(
            f"/api/resources/{resource.id}/export",
            headers=headers,
        )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
    assert 'filename="resource-' in response.headers["content-disposition"]
    assert "# 拓展阅读" in response.text
    assert "阅读内容" in response.text


@pytest.mark.asyncio
async def test_create_export_asset_returns_persistent_url(monkeypatch, tmp_path) -> None:
    from app.api import resources as resources_api

    storage = LocalAssetStorage(tmp_path, public_url_prefix="/api/assets")
    monkeypatch.setattr(resources_api, "get_asset_storage", lambda: storage)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        user_id, headers = await _register_and_get_auth(client, "resource_asset")
        async with AsyncSessionLocal() as db:
            service = ChatService(session=db)
            session_id = await service.create_session(user_id=user_id)
            resource = await service.save_resource(
                session_id=session_id,
                resource_type="reading",
                title="拓展阅读",
                content="阅读内容",
                knowledge_point="搜索",
                agent_name="ReadingAgent",
            )

        response = await client.post(
            f"/api/resources/{resource.id}/assets/export?format=markdown",
            headers=headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["url"].startswith("/api/assets/resource-")
    saved_path = storage.resolve(data["url"].replace("/api/assets/", ""))
    assert saved_path is not None
    assert "阅读内容" in saved_path.read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_create_animation_export_asset_includes_audio_and_subtitles(
    monkeypatch,
    tmp_path,
) -> None:
    from app.api import resources as resources_api

    storage = LocalAssetStorage(tmp_path, public_url_prefix="/api/assets")
    stub_tts = StubTTSClient()
    monkeypatch.setattr(resources_api, "get_asset_storage", lambda: storage)
    monkeypatch.setattr(resources_api, "get_xunfei_tts_client", lambda: stub_tts)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        user_id, headers = await _register_and_get_auth(client, "animation_asset")
        async with AsyncSessionLocal() as db:
            service = ChatService(session=db)
            session_id = await service.create_session(user_id=user_id)
            resource = await service.save_resource(
                session_id=session_id,
                resource_type="animation",
                title="搜索算法动画",
                content=(
                    "## 镜头 1：问题引入\n"
                    "时长：5秒\n"
                    "旁白：观察搜索算法如何展开状态空间。\n"
                    "画面：节点从起点向外扩展。"
                ),
                knowledge_point="搜索算法",
                agent_name="MediaAgent",
            )

        response = await client.post(
            f"/api/resources/{resource.id}/assets/animation",
            headers=headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["media_type"] == "application/zip"
    assert "算法动画：搜索算法动画" in stub_tts.text

    saved_path = storage.resolve(data["url"].replace("/api/assets/", ""))
    assert saved_path is not None
    with ZipFile(saved_path) as package:
        names = set(package.namelist())
        manifest = package.read("manifest.json").decode("utf-8")

    assert "index.html" in names
    assert "subtitles.vtt" in names
    assert "narration.mp3" in names
    assert '"has_audio": true' in manifest


@pytest.mark.asyncio
async def test_create_animation_export_asset_rejects_non_animation() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        user_id, headers = await _register_and_get_auth(client, "animation_asset_400")
        async with AsyncSessionLocal() as db:
            service = ChatService(session=db)
            session_id = await service.create_session(user_id=user_id)
            resource = await service.save_resource(
                session_id=session_id,
                resource_type="document",
                title="讲义",
                content="文档内容",
            )

        response = await client.post(
            f"/api/resources/{resource.id}/assets/animation",
            headers=headers,
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "只有算法动画资源可以导出动画包"


@pytest.mark.asyncio
async def test_export_ppt_resource_as_pptx_for_owner() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        user_id, headers = await _register_and_get_auth(client, "resource_pptx")
        async with AsyncSessionLocal() as db:
            service = ChatService(session=db)
            session_id = await service.create_session(user_id=user_id)
            resource = await service.save_resource(
                session_id=session_id,
                resource_type="ppt",
                title="搜索算法教学演示",
                content=(
                    "## 第1页：搜索算法概览\n"
                    "- 状态空间\n"
                    "- 搜索策略\n\n"
                    "## 第2页：A* 搜索\n"
                    "- 评价函数 f(n)=g(n)+h(n)\n"
                    "- 启发式函数"
                ),
                knowledge_point="搜索算法",
                agent_name="MediaAgent",
            )

        response = await client.get(
            f"/api/resources/{resource.id}/export?format=pptx",
            headers=headers,
        )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    )
    assert 'filename="resource-' in response.headers["content-disposition"]

    with ZipFile(BytesIO(response.content)) as package:
        names = set(package.namelist())
        assert "[Content_Types].xml" in names
        assert "ppt/presentation.xml" in names
        assert "ppt/slides/slide1.xml" in names
        assert "ppt/slides/slide2.xml" in names
        slide_one = package.read("ppt/slides/slide1.xml").decode("utf-8")
        slide_two = package.read("ppt/slides/slide2.xml").decode("utf-8")

    assert "搜索算法概览" in slide_one
    assert "状态空间" in slide_one
    assert "A* 搜索" in slide_two


@pytest.mark.asyncio
async def test_export_non_ppt_resource_as_pptx_returns_400() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        user_id, headers = await _register_and_get_auth(client, "resource_pptx_400")
        async with AsyncSessionLocal() as db:
            service = ChatService(session=db)
            session_id = await service.create_session(user_id=user_id)
            resource = await service.save_resource(
                session_id=session_id,
                resource_type="document",
                title="讲义",
                content="文档内容",
            )

        response = await client.get(
            f"/api/resources/{resource.id}/export?format=pptx",
            headers=headers,
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "只有教学演示资源可以导出 PPTX"
