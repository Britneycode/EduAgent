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
    spark_app_id: str = ""
    spark_api_key: str = ""
    spark_api_secret: str = ""
    spark_api_password: str = ""
    spark_model: str = "lite"
    spark_api_base_url: str = "https://spark-api-open.xf-yun.com/v1"
    spark_dev_mode: bool = False
    deepseek_enabled: bool = False
    deepseek_api_key: str = ""
    deepseek_api_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-v4-flash"
    # 讯飞安全护栏：关闭或凭证缺失时，调用方会回退本地规则。
    xunfei_safety_enabled: bool = False
    xunfei_safety_app_id: str = ""
    xunfei_safety_access_key_id: str = ""
    xunfei_safety_access_key_secret: str = ""
    xunfei_safety_api_base_url: str = "http://audit-api-spark-dx.iflyaisol.com"
    xunfei_safety_template_id: str = ""
    # 讯飞 TTS：关闭时资源朗读接口不可用；凭证默认可复用 SPARK_*。
    xunfei_tts_enabled: bool = False
    xunfei_tts_app_id: str = ""
    xunfei_tts_api_key: str = ""
    xunfei_tts_api_secret: str = ""
    xunfei_tts_url: str = "wss://tts-api.xfyun.cn/v2/tts"
    xunfei_tts_voice: str = "xiaoyan"
    xunfei_tts_speed: int = 50
    xunfei_tts_volume: int = 50
    xunfei_tts_pitch: int = 50

    # 缓存配置（REDIS_URL 为空时使用进程内 TTL 缓存）
    cache_enabled: bool = True
    cache_ttl_seconds: int = 1800
    cache_memory_max_items: int = 512
    redis_url: str = ""

    # JWT 认证
    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440

    # 教师面板访问白名单。逗号分隔，默认空表示不开放多用户聚合视图。
    teacher_dashboard_allowed_usernames: str = ""
    teacher_dashboard_allowed_user_ids: str = ""

    # Wiki 知识中枢配置
    wiki_vector_backend: str = "auto"
    wiki_chroma_dir: str = "./chroma_data"
    wiki_chroma_host: str = ""
    wiki_chroma_port: int = 8001
    wiki_chroma_ssl: bool = False
    wiki_chroma_collection: str = "eduagent_wiki"
    wiki_knowledge_dir: str = "./knowledge/ai_intro"
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
        settings.jwt_secret_key = secrets.token_urlsafe(32)
        logger.warning(
            "JWT_SECRET_KEY 未配置，已自动生成随机密钥。"
            "生产环境请在 .env 中设置 JWT_SECRET_KEY"
        )
    return settings
