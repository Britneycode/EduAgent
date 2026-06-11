from __future__ import annotations

import pytest

from app.wiki.embeddings import DevEmbedding
from app.wiki.graph import KnowledgeGraph
from app.wiki.rag_engine import RAGEngine
from app.wiki.vector_store import VectorStore
from app.wiki.wiki_service import WikiService


@pytest.fixture
def wiki_service():
    embedding = DevEmbedding()
    vs = VectorStore(embedding_client=embedding, persist_directory=None)
    vs.add(
        chunk_ids=["c1"],
        documents=["神经网络是一种模拟人脑的计算模型"],
        metadatas=[{"title": "神经网络", "chapter": "ch3", "section": "s1"}],
    )
    rag = RAGEngine(vector_store=vs)
    graph = KnowledgeGraph()
    return WikiService(rag_engine=rag, knowledge_graph=graph, vector_store=vs)


@pytest.mark.asyncio
async def test_rag_search_is_async(wiki_service: WikiService):
    results = await wiki_service.search("神经网络")
    assert len(results) > 0
    assert results[0].title == "神经网络"


@pytest.mark.asyncio
async def test_build_context_is_async(wiki_service: WikiService):
    context = await wiki_service.build_context("神经网络")
    assert "神经网络" in context


@pytest.mark.asyncio
async def test_write_back_without_db(wiki_service: WikiService):
    chunk_id = await wiki_service.write_back(
        title="测试回写",
        content="测试内容",
        source_agent="TestAgent",
    )
    assert chunk_id is not None
