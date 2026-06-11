from __future__ import annotations

import asyncio
import json
import sys
import types
from pathlib import Path

from app.agents.doc_agent import DocAgent
from app.core.cache import MemoryTTLCacheBackend
from app.core.llm import BaseLLMClient
from app.wiki.embeddings import BaseEmbedding
from app.wiki.graph import KnowledgeGraph
from app.wiki.ingestion import KnowledgeIngestion
from app.wiki.rag_engine import RAGEngine
from app.wiki.vector_store import (
    ChromaHttpVectorStore,
    VectorSearchResult,
    VectorStore,
    create_vector_store,
)
from app.wiki.wiki_service import WikiService


class TinyEmbedding(BaseEmbedding):
    KEYWORDS = ["神经", "网络", "反向传播", "逻辑", "搜索", "图谱"]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)

    @property
    def dimension(self) -> int:
        return len(self.KEYWORDS)

    def _embed(self, text: str) -> list[float]:
        return [float(text.count(keyword)) for keyword in self.KEYWORDS]


class RecordingLLMClient(BaseLLMClient):
    def __init__(self) -> None:
        self.prompts: list[str] = []

    async def generate_text(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return "反向传播学习讲义\n\n一、核心概念\n内容基于知识库整理。"


class CountingVectorStore(VectorStore):
    def __init__(self, embedding_client: BaseEmbedding) -> None:
        super().__init__(embedding_client)
        self.vector_search_calls = 0
        self.lexical_search_calls = 0

    def search(
        self,
        query: str,
        top_k: int = 5,
        where: dict[str, object] | None = None,
    ) -> list[VectorSearchResult]:
        self.vector_search_calls += 1
        return super().search(query=query, top_k=top_k, where=where)

    def lexical_search(
        self,
        query: str,
        top_k: int = 5,
        where: dict[str, object] | None = None,
    ) -> list[VectorSearchResult]:
        self.lexical_search_calls += 1
        return super().lexical_search(query=query, top_k=top_k, where=where)


def test_vector_store_supports_search_delete_and_persistence(tmp_path: Path) -> None:
    store_dir = tmp_path / "vector_store"
    store = VectorStore(TinyEmbedding(), persist_directory=store_dir)

    store.add(
        chunk_ids=["c1", "c2"],
        documents=["神经网络与反向传播", "命题逻辑与知识图谱"],
        metadatas=[
            {"chapter": "ch5", "title": "反向传播"},
            {"chapter": "ch2", "title": "命题逻辑"},
        ],
    )

    assert store.count() == 2

    results = store.search("反向传播 神经网络", top_k=2)

    assert len(results) == 2
    assert results[0].chunk_id == "c1"
    assert results[0].metadata["chapter"] == "ch5"

    filtered_results = store.search("逻辑", top_k=5, where={"chapter": "ch2"})
    assert [r.chunk_id for r in filtered_results] == ["c2"]

    lexical_results = store.lexical_search("真假命题", top_k=1)
    assert lexical_results[0].chunk_id == "c2"
    assert lexical_results[0].metadata["lexical_score"] > 0

    reloaded = VectorStore(TinyEmbedding(), persist_directory=store_dir)
    reloaded_results = reloaded.search("反向传播", top_k=1)
    assert reloaded.count() == 2
    assert reloaded_results[0].chunk_id == "c1"

    reloaded.delete(["c1"])
    assert reloaded.count() == 1
    assert reloaded.search("反向传播", top_k=5, where={"chapter": "ch5"}) == []


def test_vector_store_factory_auto_falls_back_to_numpy_without_chroma_host(
    tmp_path: Path,
) -> None:
    store, backend = create_vector_store(
        embedding_client=TinyEmbedding(),
        backend="auto",
        persist_directory=tmp_path / "vector_store",
        chroma_host="",
        chroma_port=8001,
        chroma_ssl=False,
        chroma_collection="eduagent_wiki",
    )

    assert backend == "numpy"
    store.add(["c1"], ["反向传播通过链式法则计算梯度"], [{"title": "反向传播"}])
    assert store.search("反向传播", top_k=1)[0].chunk_id == "c1"


def test_chroma_http_vector_store_adapter_uses_chroma_client(monkeypatch) -> None:
    class FakeCollection:
        def __init__(self) -> None:
            self.ids: list[str] = []
            self.documents: list[str] = []
            self.metadatas: list[dict[str, object]] = []

        def upsert(self, **kwargs: object) -> None:
            self.ids = list(kwargs["ids"])  # type: ignore[arg-type]
            self.documents = list(kwargs["documents"])  # type: ignore[arg-type]
            self.metadatas = list(kwargs["metadatas"])  # type: ignore[arg-type]

        def query(self, **kwargs: object) -> dict[str, list[list[object]]]:
            n_results = int(kwargs["n_results"])
            return {
                "ids": [self.ids[:n_results]],
                "documents": [self.documents[:n_results]],
                "metadatas": [self.metadatas[:n_results]],
                "distances": [[0.1 for _ in self.ids[:n_results]]],
            }

        def get(self, **_kwargs: object) -> dict[str, list[object]]:
            return {
                "ids": self.ids,
                "documents": self.documents,
                "metadatas": self.metadatas,
            }

        def delete(self, ids: list[str]) -> None:
            keep = [idx for idx, chunk_id in enumerate(self.ids) if chunk_id not in ids]
            self.ids = [self.ids[idx] for idx in keep]
            self.documents = [self.documents[idx] for idx in keep]
            self.metadatas = [self.metadatas[idx] for idx in keep]

        def count(self) -> int:
            return len(self.ids)

    fake_collection = FakeCollection()

    class FakeClient:
        def get_or_create_collection(self, **_kwargs: object) -> FakeCollection:
            return fake_collection

    fake_chromadb = types.SimpleNamespace(
        HttpClient=lambda **_kwargs: FakeClient()
    )
    monkeypatch.setitem(sys.modules, "chromadb", fake_chromadb)

    store = ChromaHttpVectorStore(
        TinyEmbedding(),
        host="localhost",
        port=8001,
        collection_name="eduagent_wiki",
    )
    store.add(
        ["c1", "c2"],
        ["神经网络与反向传播", "命题逻辑与知识图谱"],
        [{"title": "反向传播"}, {"title": "命题逻辑", "tags": ["logic"]}],
    )

    assert store.count() == 2
    assert store.search("反向传播", top_k=1)[0].chunk_id == "c1"
    assert store.lexical_search("真假命题", top_k=1)[0].chunk_id == "c2"
    assert fake_collection.metadatas[1]["tags"] == "[\"logic\"]"

    store.delete(["c1"])
    assert store.count() == 1


def test_knowledge_graph_returns_prerequisites_dependents_and_related() -> None:
    graph = KnowledgeGraph()
    graph.load_from_dict(
        {
            "concepts": {
                "梯度下降": {
                    "chapter": "ch4",
                    "section": "ch4_s4",
                    "prerequisites": [],
                    "description": "参数优化方法",
                },
                "多层感知机": {
                    "chapter": "ch5",
                    "section": "ch5_s1",
                    "prerequisites": ["梯度下降"],
                    "description": "多层神经网络",
                },
                "反向传播": {
                    "chapter": "ch5",
                    "section": "ch5_s1",
                    "prerequisites": ["多层感知机", "梯度下降"],
                    "description": "梯度计算算法",
                },
                "Transformer": {
                    "chapter": "ch5",
                    "section": "ch5_s3",
                    "prerequisites": ["梯度下降"],
                    "description": "注意力架构",
                },
            }
        }
    )

    assert graph.get_prerequisites("反向传播") == ["多层感知机", "梯度下降"]
    assert graph.get_all_prerequisites("反向传播") == ["梯度下降", "多层感知机"]
    assert set(graph.get_dependents("梯度下降")) == {
        "多层感知机",
        "反向传播",
        "Transformer",
    }
    assert set(graph.get_related("反向传播")) == {"多层感知机", "Transformer"}
    assert [node.name for node in graph.get_chapter_concepts("ch5")] == [
        "多层感知机",
        "反向传播",
        "Transformer",
    ]


def test_knowledge_graph_loads_nodes_edges_format() -> None:
    graph = KnowledgeGraph()
    graph.load_from_dict(
        {
            "chapters": [
                {"chapter_id": "ch01", "title": "人工智能概述"},
                {"chapter_id": "ch02", "title": "智能体与问题求解"},
            ],
            "nodes": [
                {
                    "id": "kp01",
                    "name": "人工智能的定义与本质",
                    "chapter_id": "ch01",
                    "type": "concept",
                    "difficulty": 1,
                    "tags": ["AI基础"],
                },
                {
                    "id": "kp02",
                    "name": "智能体的定义与基本架构",
                    "chapter_id": "ch02",
                    "type": "concept",
                    "difficulty": 1,
                    "tags": ["智能体"],
                },
            ],
            "edges": [
                {
                    "source": "kp01",
                    "target": "kp02",
                    "relation": "prerequisite",
                }
            ],
        }
    )

    assert graph.list_chapters() == [
        {"id": "ch01", "title": "人工智能概述"},
        {"id": "ch02", "title": "智能体与问题求解"},
    ]
    assert graph.get_prerequisites("智能体的定义与基本架构") == [
        "人工智能的定义与本质"
    ]
    assert graph.get_dependents("人工智能的定义与本质") == [
        "智能体的定义与基本架构"
    ]
    assert graph.get_chapter_concepts("ch02")[0].description == (
        "类型：concept；难度：1；标签：智能体"
    )


def test_knowledge_graph_isolates_courses_with_same_chapter_ids() -> None:
    graph = KnowledgeGraph()
    graph.load_from_dict(
        {
            "course_name": "人工智能导论",
            "chapters": [{"chapter_id": "ch01", "title": "AI 概述"}],
            "concepts": {
                "搜索": {
                    "chapter": "ch01",
                    "section": "ai_s1",
                    "prerequisites": [],
                    "description": "AI 搜索问题",
                }
            },
        },
        course_id="ai_intro",
    )
    graph.load_from_dict(
        {
            "course_name": "Python 基础",
            "chapters": [{"chapter_id": "ch01", "title": "Python 环境"}],
            "concepts": {
                "脚本运行": {
                    "chapter": "ch01",
                    "section": "py_s1",
                    "prerequisites": [],
                    "description": "运行 Python 脚本",
                }
            },
        },
        course_id="python_basics",
        clear=False,
    )

    assert graph.list_chapters("ai_intro") == [
        {"id": "ch01", "title": "AI 概述", "course_id": "ai_intro"}
    ]
    assert graph.list_chapters("python_basics") == [
        {"id": "ch01", "title": "Python 环境", "course_id": "python_basics"}
    ]
    assert [node.name for node in graph.get_chapter_concepts("ch01", "ai_intro")] == [
        "搜索"
    ]
    assert [
        node.name for node in graph.get_chapter_concepts("ch01", "python_basics")
    ] == ["脚本运行"]


def test_knowledge_ingestion_parses_markdown_and_stores_chunks(tmp_path: Path) -> None:
    asyncio.run(_test_ingestion(tmp_path))


async def _test_ingestion(tmp_path: Path) -> None:
    knowledge_dir = tmp_path / "knowledge"
    knowledge_dir.mkdir()

    metadata = {
        "chapters": [
            {
                "id": "ch5",
                "title": "深度学习",
                "file": "chapter5.md",
                "sections": [
                    {
                        "id": "ch5_s1",
                        "title": "神经网络基础",
                        "concepts": ["多层感知机", "反向传播"],
                    }
                ],
            }
        ]
    }
    (knowledge_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (knowledge_dir / "chapter5.md").write_text(
        "# 第五章 深度学习\n\n"
        "## 5.1 神经网络基础\n\n"
        "### 多层感知机\n\n"
        "多层感知机可以表达非线性映射。\n\n"
        "### 反向传播\n\n"
        "反向传播通过链式法则高效计算梯度。\n",
        encoding="utf-8",
    )

    vector_store = VectorStore(TinyEmbedding())
    ingestion = KnowledgeIngestion(vector_store=vector_store)

    count = await ingestion.ingest_course(knowledge_dir)

    assert count == 2
    assert vector_store.count() == 2

    results = vector_store.search("反向传播", top_k=1)
    assert results[0].chunk_id == "ch5_反向传播"
    assert results[0].metadata["section"] == "ch5_s1"
    assert "链式法则" in results[0].content


def test_knowledge_ingestion_marks_course_metadata(tmp_path: Path) -> None:
    asyncio.run(_test_ingestion_with_course(tmp_path))


async def _test_ingestion_with_course(tmp_path: Path) -> None:
    knowledge_dir = tmp_path / "knowledge"
    knowledge_dir.mkdir()
    (knowledge_dir / "metadata.json").write_text(
        json.dumps(
            {
                "chapters": [
                    {
                        "chapter_id": "py01",
                        "title": "Python 环境",
                        "file": "chapter_01.md",
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (knowledge_dir / "chapter_01.md").write_text(
        "# Python 环境\n\n## 基础\n\n### Python 解释器\n\n解释器负责执行脚本。",
        encoding="utf-8",
    )
    vector_store = VectorStore(TinyEmbedding())
    ingestion = KnowledgeIngestion(vector_store=vector_store)

    count = await ingestion.ingest_course(knowledge_dir, course_id="python_basics")

    assert count == 1
    result = vector_store.search(
        "解释器",
        top_k=1,
        where={"course_id": "python_basics"},
    )[0]
    assert result.chunk_id == "python_basics:py01_Python 解释器"
    assert result.metadata["course_id"] == "python_basics"


def test_knowledge_ingestion_supports_multiple_files_per_chapter(
    tmp_path: Path,
) -> None:
    asyncio.run(_test_ingestion_with_multiple_files(tmp_path))


async def _test_ingestion_with_multiple_files(tmp_path: Path) -> None:
    knowledge_dir = tmp_path / "knowledge"
    knowledge_dir.mkdir()
    (knowledge_dir / "metadata.json").write_text(
        json.dumps(
            {
                "chapters": [
                    {
                        "chapter_id": "net01",
                        "title": "网络基础",
                        "files": ["overview.md", "layering.md"],
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (knowledge_dir / "overview.md").write_text(
        "# 网络概述\n\n## 核心概念\n\n计算机网络连接主机并共享资源。",
        encoding="utf-8",
    )
    (knowledge_dir / "layering.md").write_text(
        "# 分层体系结构\n\n## 核心概念\n\n分层模型通过接口隔离复杂度。",
        encoding="utf-8",
    )
    vector_store = VectorStore(TinyEmbedding())
    ingestion = KnowledgeIngestion(vector_store=vector_store)

    count = await ingestion.ingest_course(knowledge_dir, course_id="computer_networks")

    assert count == 2
    results = vector_store.lexical_search("核心概念", top_k=5)
    chunk_ids = {result.chunk_id for result in results}
    assert len(chunk_ids) == 2
    assert all(chunk_id.startswith("computer_networks:net01_") for chunk_id in chunk_ids)


def test_knowledge_ingestion_ingests_uploaded_markdown() -> None:
    asyncio.run(_test_uploaded_markdown_ingestion())


async def _test_uploaded_markdown_ingestion() -> None:
    vector_store = VectorStore(TinyEmbedding())
    ingestion = KnowledgeIngestion(vector_store=vector_store)

    result = await ingestion.ingest_uploaded_document(
        filename="bayes-notes.md",
        content=(
            "# 贝叶斯网络课堂笔记\n\n"
            "## 条件独立性\n\n"
            "贝叶斯网络用有向无环图表示随机变量之间的条件依赖关系，"
            "可用于诊断、预测和因果分析。"
        ).encode("utf-8"),
        mime_type="text/markdown",
        chapter="uploaded",
        tags=["概率图模型"],
    )

    assert result.chunk_count == 1
    assert result.content_type == "markdown"
    assert vector_store.count() == 1

    results = vector_store.lexical_search("贝叶斯网络 条件依赖", top_k=1)
    assert results[0].metadata["content_type"] == "uploaded_document"
    assert results[0].metadata["source_name"] == "bayes-notes.md"
    assert "有向无环图" in results[0].content


def test_rag_engine_builds_context_and_supports_chapter_filter() -> None:
    asyncio.run(_test_rag_engine())


async def _test_rag_engine() -> None:
    vector_store = VectorStore(TinyEmbedding())
    vector_store.add(
        chunk_ids=["ch5_反向传播", "ch2_命题逻辑"],
        documents=["反向传播用于训练神经网络", "命题逻辑研究真假命题"],
        metadatas=[
            {"chapter": "ch5", "section": "ch5_s1", "title": "反向传播"},
            {"chapter": "ch2", "section": "ch2_s1", "title": "命题逻辑"},
        ],
    )
    rag_engine = RAGEngine(vector_store)

    results = await rag_engine.search(
        "反向传播 神经网络", top_k=2, chapter="ch5", min_score=0.1
    )
    context = await rag_engine.build_context(
        "反向传播 神经网络", top_k=1, chapter="ch5"
    )
    ctx_with_sources = await rag_engine.build_context_with_sources(
        "反向传播 神经网络", top_k=1, chapter="ch5"
    )

    assert len(results) == 1
    assert results[0].chunk_id == "ch5_反向传播"
    assert results[0].score > 0.1
    assert "以下是与问题相关的参考知识" in context
    assert "【参考 1】反向传播" in context
    assert "命题逻辑" not in context
    assert ctx_with_sources.sources[0].chunk_id == "ch5_反向传播"
    assert "反向传播用于训练神经网络" in ctx_with_sources.sources[0].snippet
    assert ctx_with_sources.confidence > 0


def test_rag_engine_supports_course_filter() -> None:
    asyncio.run(_test_rag_engine_course_filter())


async def _test_rag_engine_course_filter() -> None:
    vector_store = VectorStore(TinyEmbedding())
    vector_store.add(
        chunk_ids=["ai_intro:ch1_search", "python_basics:py1_runtime"],
        documents=["搜索算法用于状态空间探索", "Python 解释器负责运行脚本"],
        metadatas=[
            {"course_id": "ai_intro", "chapter": "ch1", "title": "搜索算法"},
            {
                "course_id": "python_basics",
                "chapter": "py1",
                "title": "Python 解释器",
            },
        ],
    )
    rag_engine = RAGEngine(vector_store)

    results = await rag_engine.search(
        "解释器 脚本",
        top_k=3,
        course_id="python_basics",
        min_score=0.1,
    )

    assert [result.course_id for result in results] == ["python_basics"]
    assert results[0].title == "Python 解释器"


def test_rag_engine_uses_lexical_search_when_embedding_misses() -> None:
    asyncio.run(_test_rag_engine_uses_lexical_search_when_embedding_misses())


async def _test_rag_engine_uses_lexical_search_when_embedding_misses() -> None:
    vector_store = VectorStore(TinyEmbedding())
    vector_store.add(
        chunk_ids=["ch5_反向传播", "ch2_命题逻辑"],
        documents=["反向传播通过链式法则高效计算梯度", "命题逻辑研究真假命题"],
        metadatas=[
            {"chapter": "ch5", "section": "ch5_s1", "title": "反向传播"},
            {"chapter": "ch2", "section": "ch2_s1", "title": "命题逻辑"},
        ],
    )
    rag_engine = RAGEngine(vector_store)

    results = await rag_engine.search("链式法则", top_k=1, min_score=0.1)

    assert results[0].chunk_id == "ch5_反向传播"
    assert results[0].metadata["retrieval"]["lexical_score"] > 0
    assert results[0].score > 0.1


def test_rag_engine_caches_search_results() -> None:
    asyncio.run(_test_rag_engine_caches_search_results())


async def _test_rag_engine_caches_search_results() -> None:
    vector_store = CountingVectorStore(TinyEmbedding())
    vector_store.add(
        chunk_ids=["ch5_反向传播"],
        documents=["反向传播通过链式法则高效计算梯度"],
        metadatas=[{"chapter": "ch5", "section": "ch5_s1", "title": "反向传播"}],
    )
    rag_engine = RAGEngine(
        vector_store,
        cache_backend=MemoryTTLCacheBackend(),
        cache_ttl_seconds=60,
    )

    first = await rag_engine.search("链式法则", top_k=1)
    second = await rag_engine.search("链式法则", top_k=1)

    assert first[0].chunk_id == second[0].chunk_id
    assert vector_store.vector_search_calls == 1
    assert vector_store.lexical_search_calls == 1

    await rag_engine.clear_cache()
    await rag_engine.search("链式法则", top_k=1)

    assert vector_store.vector_search_calls == 2
    assert vector_store.lexical_search_calls == 2


def test_wiki_service_write_back_and_doc_agent_injects_wiki_context() -> None:
    asyncio.run(_test_wiki_service())


async def _test_wiki_service() -> None:
    vector_store = VectorStore(TinyEmbedding())
    vector_store.add(
        chunk_ids=["ch5_反向传播"],
        documents=["反向传播\n\n反向传播通过链式法则计算梯度。"],
        metadatas=[{"chapter": "ch5", "section": "ch5_s1", "title": "反向传播"}],
    )

    graph = KnowledgeGraph()
    graph.load_from_dict(
        {
            "concepts": {
                "梯度下降": {
                    "chapter": "ch4",
                    "section": "ch4_s4",
                    "prerequisites": [],
                    "description": "参数优化方法",
                },
                "多层感知机": {
                    "chapter": "ch5",
                    "section": "ch5_s1",
                    "prerequisites": ["梯度下降"],
                    "description": "多层神经网络",
                },
                "反向传播": {
                    "chapter": "ch5",
                    "section": "ch5_s1",
                    "prerequisites": ["多层感知机", "梯度下降"],
                    "description": "梯度计算算法",
                },
            }
        }
    )
    wiki_service = WikiService(
        rag_engine=RAGEngine(vector_store),
        knowledge_graph=graph,
        vector_store=vector_store,
    )

    chunk_id = await wiki_service.write_back(
        title="学习总结",
        content="反向传播的核心是链式法则。",
        source_agent="DocAgent",
        chapter="ch5",
        section="ch5_s1",
    )

    assert chunk_id == "agent_DocAgent_学习总结"
    assert vector_store.count() == 2
    assert wiki_service.get_prerequisites("反向传播") == ["梯度下降", "多层感知机"]

    llm_client = RecordingLLMClient()
    agent = DocAgent(llm_client=llm_client, wiki_service=wiki_service)

    document = await agent.generate_document(
        "反向传播",
        {"cognitive_style": "图文结合", "learning_goal": "复习"},
    )

    prompt = llm_client.prompts[0]
    assert document.title == "反向传播个性化学习讲义"
    assert "以下是与问题相关的参考知识" in prompt
    assert "【参考 1】反向传播" in prompt
    assert "请基于以上参考知识生成讲义" in prompt
    assert "认知风格：图文结合" in prompt
