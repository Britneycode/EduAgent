from __future__ import annotations

import json
import logging
import math
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import numpy as np

from app.wiki.embeddings import BaseEmbedding

logger = logging.getLogger(__name__)

_TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9_]+|[\u4e00-\u9fff]+")
_CHINESE_PATTERN = re.compile(r"^[\u4e00-\u9fff]+$")


def tokenize_for_lexical(text: str) -> list[str]:
    """面向中英文混合内容的轻量分词。

    中文不引入额外分词依赖，使用整段短词 + 2/3-gram 提供 BM25 召回能力。
    """
    tokens: list[str] = []
    for raw_token in _TOKEN_PATTERN.findall(text.lower()):
        if _CHINESE_PATTERN.match(raw_token):
            if len(raw_token) <= 8:
                tokens.append(raw_token)
            for size in (2, 3):
                if len(raw_token) >= size:
                    tokens.extend(
                        raw_token[i : i + size]
                        for i in range(0, len(raw_token) - size + 1)
                    )
            continue

        tokens.append(raw_token)

    return tokens


@dataclass(slots=True)
class VectorSearchResult:
    """向量检索结果。"""

    chunk_id: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    distance: float = 0.0


VectorStoreBackendName = Literal["numpy", "chroma-http"]


def _metadata_matches(metadata: dict[str, Any], where: dict[str, Any]) -> bool:
    return all(metadata.get(k) == v for k, v in where.items())


def _sanitize_chroma_metadata(metadata: dict[str, Any]) -> dict[str, str | int | float | bool]:
    """Chroma metadata 只接受标量类型，复杂值转为 JSON 字符串。"""
    sanitized: dict[str, str | int | float | bool] = {}
    for key, value in metadata.items():
        if value is None:
            sanitized[key] = ""
        elif isinstance(value, str | int | float | bool):
            sanitized[key] = value
        else:
            sanitized[key] = json.dumps(value, ensure_ascii=False)
    return sanitized


def _rank_lexical_documents(
    *,
    query: str,
    top_k: int,
    ids: list[str],
    documents: list[str],
    metadatas: list[dict[str, Any]],
    candidate_indices: list[int],
) -> list[VectorSearchResult]:
    query_tokens = tokenize_for_lexical(query)
    if not query_tokens or not candidate_indices:
        return []

    corpus_tokens: list[list[str]] = []
    for idx in candidate_indices:
        metadata = metadatas[idx]
        title = metadata.get("title", "")
        corpus_tokens.append(tokenize_for_lexical(f"{title}\n{documents[idx]}"))

    doc_freq: Counter[str] = Counter()
    for tokens in corpus_tokens:
        doc_freq.update(set(tokens))

    doc_count = len(corpus_tokens)
    avg_doc_len = sum(len(tokens) for tokens in corpus_tokens) / max(doc_count, 1)
    avg_doc_len = max(avg_doc_len, 1.0)
    query_freq = Counter(query_tokens)
    k1 = 1.5
    b = 0.75

    scored: list[tuple[int, float]] = []
    for local_idx, tokens in enumerate(corpus_tokens):
        if not tokens:
            continue

        token_freq = Counter(tokens)
        doc_len = len(tokens)
        score = 0.0
        for token, query_weight in query_freq.items():
            term_freq = token_freq.get(token, 0)
            if term_freq == 0:
                continue

            idf = math.log(
                1.0 + (doc_count - doc_freq[token] + 0.5) / (doc_freq[token] + 0.5)
            )
            denominator = term_freq + k1 * (1.0 - b + b * doc_len / avg_doc_len)
            score += idf * (term_freq * (k1 + 1.0) / denominator) * query_weight

        if score > 0:
            scored.append((candidate_indices[local_idx], score))

    if not scored:
        return []

    scored.sort(key=lambda item: item[1], reverse=True)
    max_score = scored[0][1]
    results: list[VectorSearchResult] = []
    for idx, raw_score in scored[:top_k]:
        normalized_score = raw_score / max_score if max_score > 0 else 0.0
        metadata = dict(metadatas[idx])
        metadata["lexical_raw_score"] = raw_score
        metadata["lexical_score"] = normalized_score
        results.append(
            VectorSearchResult(
                chunk_id=ids[idx],
                content=documents[idx],
                metadata=metadata,
                distance=max(0.0, 1.0 - normalized_score),
            )
        )

    return results


class VectorStore:
    """纯 Python 向量存储（numpy + JSON 持久化）。

    无需 C++ 编译依赖，Windows 开箱即用。
    persist_directory 不为 None 时自动持久化到磁盘，为 None 时使用内存模式（测试用）。
    """

    _STORE_FILE = "vector_store.json"
    _EMBEDDINGS_FILE = "embeddings.npy"

    def __init__(
        self,
        embedding_client: BaseEmbedding,
        persist_directory: str | Path | None = None,
    ) -> None:
        self._embedding = embedding_client
        self._persist_dir = Path(persist_directory) if persist_directory else None

        # 内存数据结构
        self._ids: list[str] = []
        self._documents: list[str] = []
        self._metadatas: list[dict[str, Any]] = []
        self._vectors: np.ndarray | None = None  # shape: (n, dim)

        # 从磁盘恢复
        if self._persist_dir is not None:
            self._load()

    def add(
        self,
        chunk_ids: list[str],
        documents: list[str],
        metadatas: list[dict[str, Any]] | None = None,
    ) -> None:
        """批量添加文档到向量存储。"""
        if not chunk_ids:
            return

        embeddings = self._embedding.embed_documents(documents)
        new_vectors = np.array(embeddings, dtype=np.float32)

        if metadatas is None:
            metadatas = [{} for _ in chunk_ids]

        # 去重：如果 chunk_id 已存在则覆盖
        for i, cid in enumerate(chunk_ids):
            if cid in self._ids:
                idx = self._ids.index(cid)
                self._documents[idx] = documents[i]
                self._metadatas[idx] = metadatas[i]
                if self._vectors is not None:
                    self._vectors[idx] = new_vectors[i]
            else:
                self._ids.append(cid)
                self._documents.append(documents[i])
                self._metadatas.append(metadatas[i])
                if self._vectors is None:
                    self._vectors = new_vectors[i : i + 1].copy()
                else:
                    self._vectors = np.vstack([self._vectors, new_vectors[i : i + 1]])

        self._save()

    def search(
        self,
        query: str,
        top_k: int = 5,
        where: dict[str, Any] | None = None,
    ) -> list[VectorSearchResult]:
        """语义检索（余弦距离）。"""
        if self._vectors is None or len(self._ids) == 0:
            return []

        query_embedding = np.array(self._embedding.embed_query(query), dtype=np.float32)

        # 确定候选索引（按 metadata 过滤）
        if where:
            candidates = [
                i
                for i, meta in enumerate(self._metadatas)
                if all(meta.get(k) == v for k, v in where.items())
            ]
            if not candidates:
                return []
            candidate_vectors = self._vectors[candidates]
        else:
            candidates = list(range(len(self._ids)))
            candidate_vectors = self._vectors

        # 余弦距离 = 1 - 余弦相似度
        query_norm = np.linalg.norm(query_embedding)
        if query_norm == 0:
            distances = np.ones(len(candidates), dtype=np.float32)
        else:
            doc_norms = np.linalg.norm(candidate_vectors, axis=1)
            # 避免除零
            doc_norms = np.maximum(doc_norms, 1e-10)
            similarities = (
                candidate_vectors @ query_embedding / (doc_norms * query_norm)
            )
            distances = 1.0 - similarities

        # 取 Top-K
        k = min(top_k, len(candidates))
        top_indices = np.argsort(distances)[:k]

        results: list[VectorSearchResult] = []
        for idx in top_indices:
            orig_idx = candidates[idx]
            results.append(
                VectorSearchResult(
                    chunk_id=self._ids[orig_idx],
                    content=self._documents[orig_idx],
                    metadata=self._metadatas[orig_idx],
                    distance=float(distances[idx]),
                )
            )

        return results

    def lexical_search(
        self,
        query: str,
        top_k: int = 5,
        where: dict[str, Any] | None = None,
    ) -> list[VectorSearchResult]:
        """BM25 词法检索，用于和向量检索混合召回。"""
        if len(self._ids) == 0:
            return []

        if where:
            candidates = [
                i
                for i, meta in enumerate(self._metadatas)
                if _metadata_matches(meta, where)
            ]
        else:
            candidates = list(range(len(self._ids)))

        return _rank_lexical_documents(
            query=query,
            top_k=top_k,
            ids=self._ids,
            documents=self._documents,
            metadatas=self._metadatas,
            candidate_indices=candidates,
        )

    def delete(self, chunk_ids: list[str]) -> None:
        """按 ID 删除文档。"""
        if not chunk_ids:
            return

        indices_to_remove = [
            i for i, cid in enumerate(self._ids) if cid in set(chunk_ids)
        ]
        if not indices_to_remove:
            return

        keep = [i for i in range(len(self._ids)) if i not in set(indices_to_remove)]
        self._ids = [self._ids[i] for i in keep]
        self._documents = [self._documents[i] for i in keep]
        self._metadatas = [self._metadatas[i] for i in keep]
        if self._vectors is not None:
            if keep:
                self._vectors = self._vectors[keep]
            else:
                self._vectors = None

        self._save()

    def count(self) -> int:
        """返回存储的文档总数。"""
        return len(self._ids)

    def _save(self) -> None:
        """持久化到磁盘。"""
        if self._persist_dir is None:
            return

        self._persist_dir.mkdir(parents=True, exist_ok=True)

        store_data = {
            "ids": self._ids,
            "documents": self._documents,
            "metadatas": self._metadatas,
        }
        store_path = self._persist_dir / self._STORE_FILE
        with open(store_path, "w", encoding="utf-8") as f:
            json.dump(store_data, f, ensure_ascii=False, indent=2)

        if self._vectors is not None:
            embeddings_path = self._persist_dir / self._EMBEDDINGS_FILE
            np.save(str(embeddings_path), self._vectors)

    def _load(self) -> None:
        """从磁盘恢复。"""
        if self._persist_dir is None:
            return

        store_path = self._persist_dir / self._STORE_FILE
        embeddings_path = self._persist_dir / self._EMBEDDINGS_FILE

        if not store_path.exists():
            return

        try:
            with open(store_path, encoding="utf-8") as f:
                store_data = json.load(f)

            self._ids = store_data.get("ids", [])
            self._documents = store_data.get("documents", [])
            self._metadatas = store_data.get("metadatas", [])

            if embeddings_path.exists() and self._ids:
                self._vectors = np.load(str(embeddings_path))
            else:
                self._vectors = None

            logger.info("从磁盘恢复向量存储，共 %d 条记录", len(self._ids))
        except Exception:
            logger.warning("恢复向量存储失败，将使用空存储", exc_info=True)
            self._ids = []
            self._documents = []
            self._metadatas = []
            self._vectors = None


class ChromaHttpVectorStore:
    """远程 Chroma Server 向量存储适配器。

    使用 `chromadb-client` 连接独立 Chroma 服务，避免在 Windows 本地构建
    chroma-hnswlib。BM25 词法检索仍在应用侧完成，用于保持混合召回能力。
    """

    def __init__(
        self,
        embedding_client: BaseEmbedding,
        *,
        host: str = "localhost",
        port: int = 8001,
        ssl: bool = False,
        collection_name: str = "eduagent_wiki",
    ) -> None:
        try:
            import chromadb
        except ImportError as exc:
            raise RuntimeError(
                "Chroma 后端需要安装 chromadb-client 依赖"
            ) from exc

        self._embedding = embedding_client
        self._client = chromadb.HttpClient(host=host, port=port, ssl=ssl)
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def add(
        self,
        chunk_ids: list[str],
        documents: list[str],
        metadatas: list[dict[str, Any]] | None = None,
    ) -> None:
        if not chunk_ids:
            return

        embeddings = self._embedding.embed_documents(documents)
        if metadatas is None:
            metadatas = [{} for _ in chunk_ids]

        self._collection.upsert(
            ids=chunk_ids,
            documents=documents,
            metadatas=[_sanitize_chroma_metadata(item) for item in metadatas],
            embeddings=embeddings,
        )

    def search(
        self,
        query: str,
        top_k: int = 5,
        where: dict[str, Any] | None = None,
    ) -> list[VectorSearchResult]:
        if top_k <= 0 or self.count() == 0:
            return []

        query_kwargs: dict[str, Any] = {
            "query_embeddings": [self._embedding.embed_query(query)],
            "n_results": top_k,
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            query_kwargs["where"] = where
        payload = self._collection.query(**query_kwargs)

        ids = payload.get("ids", [[]])[0] or []
        documents = payload.get("documents", [[]])[0] or []
        metadatas = payload.get("metadatas", [[]])[0] or []
        distances = payload.get("distances", [[]])[0] or []

        results: list[VectorSearchResult] = []
        for idx, chunk_id in enumerate(ids):
            results.append(
                VectorSearchResult(
                    chunk_id=chunk_id,
                    content=documents[idx] if idx < len(documents) else "",
                    metadata=dict(metadatas[idx] or {}) if idx < len(metadatas) else {},
                    distance=float(distances[idx]) if idx < len(distances) else 0.0,
                )
            )
        return results

    def lexical_search(
        self,
        query: str,
        top_k: int = 5,
        where: dict[str, Any] | None = None,
    ) -> list[VectorSearchResult]:
        if self.count() == 0:
            return []

        get_kwargs: dict[str, Any] = {"include": ["documents", "metadatas"]}
        if where:
            get_kwargs["where"] = where
        payload = self._collection.get(**get_kwargs)
        ids = payload.get("ids", []) or []
        documents = payload.get("documents", []) or []
        metadatas = [dict(item or {}) for item in payload.get("metadatas", []) or []]

        return _rank_lexical_documents(
            query=query,
            top_k=top_k,
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            candidate_indices=list(range(len(ids))),
        )

    def delete(self, chunk_ids: list[str]) -> None:
        if chunk_ids:
            self._collection.delete(ids=chunk_ids)

    def count(self) -> int:
        return int(self._collection.count())


def create_vector_store(
    *,
    embedding_client: BaseEmbedding,
    backend: str,
    persist_directory: str | Path | None,
    chroma_host: str,
    chroma_port: int,
    chroma_ssl: bool,
    chroma_collection: str,
) -> tuple[VectorStore | ChromaHttpVectorStore, VectorStoreBackendName]:
    """创建向量存储。

    backend:
    - numpy: 本地 NumPy + JSON 持久化
    - chroma: 连接远程 Chroma Server
    - auto: 配置了 Chroma host 时优先连接，失败后回退到 numpy
    """
    normalized_backend = backend.strip().lower()
    resolved_chroma_host = chroma_host or "localhost"
    if normalized_backend == "numpy":
        return (
            VectorStore(
                embedding_client=embedding_client,
                persist_directory=persist_directory,
            ),
            "numpy",
        )

    if normalized_backend in {"chroma", "chroma-http"}:
        return (
            ChromaHttpVectorStore(
                embedding_client=embedding_client,
                host=resolved_chroma_host,
                port=chroma_port,
                ssl=chroma_ssl,
                collection_name=chroma_collection,
            ),
            "chroma-http",
        )

    if normalized_backend == "auto":
        if chroma_host:
            try:
                return (
                    ChromaHttpVectorStore(
                        embedding_client=embedding_client,
                        host=resolved_chroma_host,
                        port=chroma_port,
                        ssl=chroma_ssl,
                        collection_name=chroma_collection,
                    ),
                    "chroma-http",
                )
            except Exception:
                logger.warning(
                    "连接 Chroma Server 失败，回退到本地 NumPy 向量存储",
                    exc_info=True,
                )

        return (
            VectorStore(
                embedding_client=embedding_client,
                persist_directory=persist_directory,
            ),
            "numpy",
        )

    raise ValueError(f"不支持的向量存储后端: {backend}")
