import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.assets import router as assets_router
from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.learning import router as learning_router
from app.api.profile import router as profile_router
from app.api.resources import router as resources_router
from app.api.wiki import router as wiki_router
from app.core.cache import close_cache_backend, get_cache_status
from app.core.config import get_settings
from app.core.database import AsyncSessionLocal, init_db
from app.core.llm import get_llm_configuration_warning
from app.core.xunfei_safety import get_xunfei_safety_configuration_warning
from app.core.xunfei_tts import get_xunfei_tts_configuration_warning
from app.wiki import get_vector_store_status

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    from app.wiki import init_wiki

    await init_db()

    # 初始化 Wiki 知识中枢（自动导入知识库到向量存储）
    async with AsyncSessionLocal() as session:
        await init_wiki(session=session)

    try:
        yield
    finally:
        await close_cache_backend()


settings = get_settings()
app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.backend_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(assets_router)
app.include_router(chat_router)
app.include_router(learning_router)
app.include_router(profile_router)
app.include_router(resources_router)
app.include_router(wiki_router)


@app.exception_handler(Exception)
async def global_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    logger.error("未处理的异常: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "服务器内部错误，请稍后重试"},
    )


@app.get("/health")
async def health() -> dict[str, object | None]:
    cache_status = get_cache_status()
    return {
        "status": "ok",
        "llm_warning": get_llm_configuration_warning(),
        "safety_warning": get_xunfei_safety_configuration_warning(),
        "tts_warning": get_xunfei_tts_configuration_warning(),
        "cache": {
            "enabled": cache_status.enabled,
            "backend": cache_status.backend,
            "redis_configured": cache_status.redis_configured,
        },
        "vector_store": get_vector_store_status(),
    }
