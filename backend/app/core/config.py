import logging
import secrets
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """应用基础配置。"""

    app_name: str = "EduAgent API"
    app_version: str = "0.1.0"
    database_url: str = "sqlite+aiosqlite:///./eduagent.db"
    backend_cors_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    # 开发模式：LLM 返回模拟内容，不调用真实模型。
    llm_dev_mode: bool = False
    # 资源 Agent 并发上限，免费 API 建议保持较低数值。
    resource_concurrency: int = 2
    deepseek_enabled: bool = False
    deepseek_api_key: str = ""
    deepseek_api_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-v4-flash"
    openai_compatible_enabled: bool = False
    openai_compatible_provider: str = "OpenAI 兼容模型"
    openai_compatible_api_key: str = ""
    openai_compatible_api_base_url: str = (
        "https://dashscope.aliyuncs.com/compatible-mode/v1"
    )
    openai_compatible_model: str = "qwen3.6-plus"
    openai_compatible_enable_thinking: bool | None = None
    dashscope_api_key: str = ""

    # 相关视频联网搜索：默认使用 Tavily，并限制到 B站域名。
    video_search_enabled: bool = True
    video_search_provider: str = "tavily"
    tavily_api_key: str = ""
    tavily_api_base_url: str = "https://api.tavily.com"
    video_search_domains: list[str] = ["bilibili.com"]
    video_search_max_results: int = 5

    # 缓存配置（REDIS_URL 为空时使用进程内 TTL 缓存）
    cache_enabled: bool = True
    cache_ttl_seconds: int = 1800
    cache_memory_max_items: int = 512
    redis_url: str = ""

    # JWT 认证
    app_env: str = "development"
    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440

    # Wiki 知识中枢配置
    wiki_vector_backend: str = "auto"
    wiki_chroma_dir: str = "./chroma_data"
    wiki_chroma_host: str = ""
    wiki_chroma_port: int = 8001
    wiki_chroma_ssl: bool = False
    wiki_chroma_collection: str = "eduagent_wiki"
    wiki_knowledge_dir: str = "./knowledge/计算机网络知识库"
    wiki_embedding_dev_mode: bool = False
    wiki_auto_ingest: bool = True

    # 资产存储：默认落到本地目录，后续可替换为 MinIO/S3 适配器。
    asset_storage_dir: str = "./storage/assets"
    asset_public_url_prefix: str = "/api/assets"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if not settings.jwt_secret_key:
        if settings.app_env.lower() in {"prod", "production"}:
            raise RuntimeError("生产环境必须配置 JWT_SECRET_KEY")
        settings.jwt_secret_key = secrets.token_urlsafe(32)
        logger.warning(
            "JWT_SECRET_KEY 未配置，已自动生成随机密钥。"
            "生产环境请在 .env 中设置 JWT_SECRET_KEY"
        )
    return settings
