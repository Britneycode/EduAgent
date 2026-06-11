from __future__ import annotations

import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class BaseEmbedding(ABC):
    """统一的文本向量化接口。"""

    @abstractmethod
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """批量文本向量化。"""

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        """查询文本向量化（可添加检索前缀以提升效果）。"""

    @property
    @abstractmethod
    def dimension(self) -> int:
        """向量维度。"""


class BGEEmbedding(BaseEmbedding):
    """基于 BAAI/bge-small-zh-v1.5 的中文 Embedding。

    首次实例化时从 HuggingFace 下载模型（约 90MB），后续使用本地缓存。
    """

    MODEL_NAME = "BAAI/bge-small-zh-v1.5"
    QUERY_PREFIX = "为这个句子生成表示以用于检索相关段落："

    def __init__(self) -> None:
        from sentence_transformers import SentenceTransformer

        logger.info("正在加载 Embedding 模型: %s", self.MODEL_NAME)
        self._model = SentenceTransformer(self.MODEL_NAME)
        self._dimension = self._model.get_sentence_embedding_dimension()
        logger.info("Embedding 模型加载完成，维度: %d", self._dimension)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        embeddings = self._model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()

    def embed_query(self, text: str) -> list[float]:
        query = f"{self.QUERY_PREFIX}{text}"
        embedding = self._model.encode(query, normalize_embeddings=True)
        return embedding.tolist()

    @property
    def dimension(self) -> int:
        return self._dimension


class DevEmbedding(BaseEmbedding):
    """开发模式 Embedding，返回固定维度零向量。

    用于测试和不需要真实向量化的场景。
    """

    DEV_DIMENSION = 64

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] * self.DEV_DIMENSION for _ in texts]

    def embed_query(self, text: str) -> list[float]:
        return [0.0] * self.DEV_DIMENSION

    @property
    def dimension(self) -> int:
        return self.DEV_DIMENSION


_embedding_instance: BaseEmbedding | None = None


def get_embedding_client(dev_mode: bool = False) -> BaseEmbedding:
    """获取 Embedding 客户端单例。"""
    global _embedding_instance
    if _embedding_instance is not None:
        return _embedding_instance

    if dev_mode:
        logger.warning("⚠️ 当前为开发模式，Embedding 使用零向量")
        _embedding_instance = DevEmbedding()
    else:
        _embedding_instance = BGEEmbedding()

    return _embedding_instance
