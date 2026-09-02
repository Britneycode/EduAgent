from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import ChatSession
from app.models.material import SessionMaterial
from app.wiki.ingestion import (
    UnsupportedDocumentTypeError,
    extract_upload_text,
)

if TYPE_CHECKING:
    from app.core.storage import LocalAssetStorage, StoredAsset
    from app.wiki.wiki_service import WikiService

logger = logging.getLogger(__name__)


class SessionMaterialError(ValueError):
    """会话材料操作失败。"""


class SessionMaterialService:
    """会话学习材料服务：上传/列出/删除按会话隔离的学习材料。

    材料原始文件落盘到资产存储（namespace=materials/{session_id}），文本内容
    摄取进向量库（scope=session，course_id=session:{session_id}），供 Agent 在
    课程知识库未命中时作为兜底检索源。
    """

    def __init__(
        self,
        session: AsyncSession,
        wiki_service: "WikiService",
        asset_storage: "LocalAssetStorage | None" = None,
    ) -> None:
        self._session = session
        self._wiki_service = wiki_service
        if asset_storage is None:
            from app.core.storage import get_asset_storage

            asset_storage = get_asset_storage()
        self._asset_storage = asset_storage

    async def attach_material(
        self,
        *,
        session_id: int,
        user_id: int | None,
        filename: str,
        content: bytes,
        mime_type: str = "",
    ) -> SessionMaterial:
        """把一份学习材料挂到某会话。

        校验会话归属 → 校验并解析文本 → 原始文件落盘 → 摄取进向量库（会话隔离）
        → 记录 SessionMaterial 行。
        """
        session_ok = await self._session_owned_by(session_id, user_id)
        if not session_ok:
            raise SessionMaterialError("会话不存在或无权访问")

        safe_filename = filename or "uploaded-material"
        # 提前解析校验格式与文本可读性（非法格式直接抛错，不落盘）。
        try:
            text = extract_upload_text(filename=safe_filename, content=content)
        except UnsupportedDocumentTypeError as exc:
            supported = "、".join(sorted((".md", ".markdown", ".txt", ".pdf", ".pptx")))
            raise SessionMaterialError(
                f"材料 {safe_filename} 格式不支持（{exc}）。"
                f"请将内容转换为以下格式之一后重试：{supported}"
            ) from exc
        if not text.strip():
            raise SessionMaterialError(
                f"材料 {safe_filename} 未解析出可入库文本（可能是空白文件或仅含无法提取的图片）。"
                f"请确保文档包含文字内容，或改用 Markdown/纯文本后重试。"
            )

        stored: StoredAsset | None = None
        try:
            stored = self._asset_storage.save_bytes(
                data=content,
                filename=safe_filename,
                media_type=mime_type or "application/octet-stream",
                namespace=f"materials/{session_id}",
            )
        except Exception:
            logger.warning("材料原始文件落盘失败，仅保留检索块", exc_info=True)

        result = await self._wiki_service.ingest_uploaded_document(
            filename=safe_filename,
            content=content,
            mime_type=mime_type,
            session_id=session_id,
        )

        material = SessionMaterial(
            session_id=session_id,
            filename=result.filename,
            stored_key=stored.key if stored else None,
            mime_type=mime_type or "",
            content_type=result.content_type,
            char_count=result.char_count,
            chunk_count=result.chunk_count,
            chunk_ids=result.chunk_ids,
            chapter=result.chapter,
            section=result.section,
        )
        self._session.add(material)
        try:
            await self._session.commit()
        except Exception:
            # DB 落库失败时补偿删除已写入的向量块，避免孤儿块污染该会话检索。
            await self._session.rollback()
            if result.chunk_ids:
                try:
                    await self._wiki_service.delete_chunks(result.chunk_ids)
                except Exception:
                    logger.warning("材料落库失败后的向量块补偿删除失败", exc_info=True)
            raise
        await self._session.refresh(material)
        logger.info(
            "会话 %s 新增学习材料: %s（%d 块）",
            session_id,
            material.filename,
            material.chunk_count,
        )
        return material

    async def list_materials(
        self,
        session_id: int,
        user_id: int | None,
    ) -> list[SessionMaterial]:
        """列出某会话的全部学习材料。"""
        if not await self._session_owned_by(session_id, user_id):
            raise SessionMaterialError("会话不存在或无权访问")
        result = await self._session.execute(
            select(SessionMaterial)
            .where(SessionMaterial.session_id == session_id)
            .order_by(SessionMaterial.id.asc())
        )
        return list(result.scalars().all())

    async def delete_material(
        self,
        *,
        session_id: int,
        material_id: int,
        user_id: int | None,
    ) -> bool:
        """删除某会话的一份材料（向量块 + DB 条目 + 原始文件）。"""
        if not await self._session_owned_by(session_id, user_id):
            raise SessionMaterialError("会话不存在或无权访问")

        material = await self._session.scalar(
            select(SessionMaterial).where(
                SessionMaterial.id == material_id,
                SessionMaterial.session_id == session_id,
            )
        )
        if material is None:
            return False

        if material.chunk_ids:
            await self._wiki_service.delete_chunks(material.chunk_ids)
        if material.stored_key:
            path = self._asset_storage.resolve(material.stored_key)
            if path is not None:
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    logger.debug("删除材料原始文件失败: %s", material.stored_key)

        await self._session.delete(material)
        await self._session.commit()
        logger.info("会话 %s 删除学习材料: %s", session_id, material.filename)
        return True

    async def _session_owned_by(self, session_id: int, user_id: int | None) -> bool:
        """校验会话真实存在；提供 user_id 时进一步校验归属。

        MCP 等免登录宿主传 user_id=None，仅要求会话存在（防孤儿数据）；
        Web 形态传具体 user_id，执行存在 + 归属双重校验。
        """
        stmt = select(ChatSession.id).where(ChatSession.id == session_id)
        if user_id is not None:
            stmt = stmt.where(ChatSession.user_id == user_id)
        result = await self._session.execute(stmt)
        return result.scalars().first() is not None
