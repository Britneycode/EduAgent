from __future__ import annotations

from datetime import timezone, datetime

from sqlalchemy import case, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import ChatMessage, ChatSession
from app.models.resource import GeneratedResource


class ChatService:
    """聊天会话与资源持久化服务。"""

    def __init__(self, session: AsyncSession | None) -> None:
        self.session = session
        self._resource_id_seq = 1

    async def create_session(
        self,
        title: str = "新学习会话",
        user_id: int | None = None,
        course_id: str | None = None,
    ) -> int:
        chat_session = ChatSession(title=title, user_id=user_id, course_id=course_id)
        self._require_session().add(chat_session)
        await self._require_session().commit()
        await self._require_session().refresh(chat_session)
        return chat_session.id

    async def session_exists(self, session_id: int, user_id: int | None = None) -> bool:
        if self.session is None:
            return True
        stmt = select(ChatSession).where(ChatSession.id == session_id)
        if user_id is not None:
            stmt = stmt.where(ChatSession.user_id == user_id)
        result = await self._require_session().execute(stmt)
        return result.scalars().first() is not None

    async def delete_session(self, session_id: int, user_id: int | None = None) -> bool:
        session = await self.get_session(session_id, user_id=user_id)
        if session is None:
            return False

        await self._require_session().delete(session)
        await self._require_session().commit()
        return True

    async def save_message(
        self,
        session_id: int,
        role: str,
        content: str,
        message_type: str = "text",
        turn_id: str | None = None,
    ) -> ChatMessage:
        message = ChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            message_type=message_type,
            turn_id=turn_id,
        )
        self._require_session().add(message)
        await self._require_session().commit()
        await self._require_session().refresh(message)
        return message

    async def list_sessions(self, user_id: int | None = None) -> list[ChatSession]:
        stmt = select(ChatSession)

        if user_id is not None:
            stmt = stmt.where(ChatSession.user_id == user_id)

        stmt = stmt.order_by(
            ChatSession.is_pinned.desc(),
            case((ChatSession.pinned_at.is_(None), 1), else_=0).asc(),
            ChatSession.pinned_at.desc(),
            ChatSession.updated_at.desc(),
        )

        result = await self._require_session().execute(stmt)
        return list(result.scalars().all())

    async def get_session(
        self, session_id: int, user_id: int | None = None
    ) -> ChatSession | None:
        stmt = select(ChatSession).where(ChatSession.id == session_id)
        if user_id is not None:
            stmt = stmt.where(ChatSession.user_id == user_id)
        result = await self._require_session().execute(stmt)
        return result.scalars().first()

    async def update_session_title(
        self,
        session_id: int,
        title: str,
        user_id: int | None = None,
    ) -> ChatSession | None:
        session = await self.get_session(session_id, user_id=user_id)
        if session is None:
            return None

        session.title = title
        await self._require_session().commit()
        await self._require_session().refresh(session)
        return session

    async def update_session_course(
        self,
        session_id: int,
        course_id: str | None,
        user_id: int | None = None,
    ) -> ChatSession | None:
        session = await self.get_session(session_id, user_id=user_id)
        if session is None:
            return None

        session.course_id = course_id
        await self._require_session().commit()
        await self._require_session().refresh(session)
        return session

    async def set_session_pinned(
        self,
        session_id: int,
        is_pinned: bool,
        user_id: int | None = None,
    ) -> ChatSession | None:
        session = await self.get_session(session_id, user_id=user_id)
        if session is None:
            return None

        if is_pinned:
            session.is_pinned = True
            session.pinned_at = datetime.now(timezone.utc)
        else:
            session.is_pinned = False
            session.pinned_at = None

        await self._require_session().commit()
        await self._require_session().refresh(session)
        return session

    async def list_messages(self, session_id: int) -> list[ChatMessage]:
        result = await self._require_session().execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.id.asc())
        )
        return list(result.scalars().all())

    async def list_recent_messages(
        self, session_id: int, limit: int = 10
    ) -> list[dict[str, str]]:
        result = await self._require_session().execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.id.desc())
            .limit(limit)
        )
        rows = list(result.scalars().all())
        rows.reverse()
        return [{"role": m.role, "content": m.content} for m in rows]

    async def list_resources(self, session_id: int) -> list[GeneratedResource]:
        result = await self._require_session().execute(
            select(GeneratedResource)
            .where(GeneratedResource.session_id == session_id)
            .order_by(GeneratedResource.id.asc())
        )
        return list(result.scalars().all())

    async def list_all_resources(
        self, user_id: int, resource_type: str | None = None
    ) -> list[GeneratedResource]:
        stmt = (
            select(GeneratedResource)
            .join(ChatSession, GeneratedResource.session_id == ChatSession.id)
            .where(ChatSession.user_id == user_id)
            .order_by(GeneratedResource.is_favorite.desc(), GeneratedResource.id.desc())
        )
        if resource_type:
            stmt = stmt.where(GeneratedResource.resource_type == resource_type)
        result = await self._require_session().execute(stmt)
        return list(result.scalars().all())

    async def get_resource(
        self, resource_id: int, user_id: int | None = None
    ) -> GeneratedResource | None:
        stmt = select(GeneratedResource).where(GeneratedResource.id == resource_id)
        if user_id is not None:
            stmt = stmt.join(
                ChatSession, GeneratedResource.session_id == ChatSession.id
            ).where(ChatSession.user_id == user_id)
        result = await self._require_session().execute(stmt)
        return result.scalars().first()

    async def set_resource_favorite(
        self,
        resource_id: int,
        user_id: int,
        is_favorite: bool,
    ) -> GeneratedResource | None:
        resource = await self.get_resource(resource_id, user_id=user_id)
        if resource is None:
            return None

        resource.is_favorite = is_favorite
        await self._require_session().commit()
        await self._require_session().refresh(resource)
        return resource

    async def update_resource(
        self,
        *,
        resource_id: int,
        user_id: int,
        title: str,
        content: str,
        knowledge_point: str | None = None,
        agent_name: str | None = None,
    ) -> GeneratedResource | None:
        resource = await self.get_resource(resource_id, user_id=user_id)
        if resource is None:
            return None

        resource.title = title
        resource.content = content
        resource.knowledge_point = knowledge_point
        resource.agent_name = agent_name
        await self._require_session().commit()
        await self._require_session().refresh(resource)
        return resource

    async def save_resource(
        self,
        session_id: int,
        resource_type: str,
        title: str,
        content: str,
        knowledge_point: str | None = None,
        agent_name: str | None = None,
        turn_id: str | None = None,
    ) -> GeneratedResource:
        if self.session is None:
            resource = GeneratedResource(
                id=self._resource_id_seq,
                session_id=session_id,
                resource_type=resource_type,
                title=title,
                content=content,
                knowledge_point=knowledge_point,
                agent_name=agent_name,
                turn_id=turn_id,
            )
            self._resource_id_seq += 1
            return resource

        resource = GeneratedResource(
            session_id=session_id,
            resource_type=resource_type,
            title=title,
            content=content,
            knowledge_point=knowledge_point,
            agent_name=agent_name,
            turn_id=turn_id,
        )
        self._require_session().add(resource)
        await self._require_session().commit()
        await self._require_session().refresh(resource)
        return resource

    def _require_session(self) -> AsyncSession:
        if self.session is None:
            raise ValueError("ChatService 需要有效的数据库会话")
        return self.session
