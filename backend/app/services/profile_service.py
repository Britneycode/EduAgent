from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.profile import ProfileSnapshot, StudentProfile
from app.schemas.profile import ProfileHistoryItem, ProfileResponse

_JSON_LIST_FIELDS = {"weak_points", "interest_areas"}
_JSON_DICT_FIELDS = {"knowledge_base"}
_INT_FIELDS = {"weekly_hours"}
_TEXT_FIELDS = {
    "major",
    "grade",
    "cognitive_style",
    "learning_goal",
    "learning_pace",
    "coding_level",
}
_PROFILE_FIELDS = {
    "major",
    "grade",
    "knowledge_base",
    "cognitive_style",
    "learning_goal",
    "weak_points",
    "learning_pace",
    "interest_areas",
    "coding_level",
    "weekly_hours",
}


class ProfileService:
    """学生画像服务。

    画像绑定 user_id（MVP 默认为 1），跨 session 累积更新。
    """

    def __init__(self, session: AsyncSession | None) -> None:
        self.session = session

    async def get_or_create_profile(
        self,
        session_id: int | None = None,
        user_id: int = 1,
    ) -> ProfileResponse:
        if self.session is None:
            return ProfileResponse(user_id=user_id, session_id=session_id)

        profile = await self._get_profile_by_user(user_id)
        if profile is None:
            profile = StudentProfile(user_id=user_id, session_id=session_id)
            self._normalize_profile_model(profile)
            self._require_session().add(profile)
            await self._require_session().commit()
            await self._require_session().refresh(profile)
        else:
            changed = self._normalize_profile_model(profile)
            if changed:
                self._require_session().add(profile)
                await self._require_session().commit()
                await self._require_session().refresh(profile)

        return self._to_response(profile, session_id)

    def merge_profile(
        self,
        existing: dict[str, Any],
        update: dict[str, Any],
    ) -> dict[str, Any]:
        merged = dict(existing)
        for field, value in update.items():
            if field not in _PROFILE_FIELDS:
                continue
            if field == "knowledge_base":
                existing_kb = self._normalize_field_value(field, merged.get(field))
                update_kb = self._normalize_field_value(field, value)
                merged[field] = {**existing_kb, **update_kb}
            elif field in _JSON_LIST_FIELDS:
                existing_items = self._normalize_field_value(field, merged.get(field))
                update_items = self._normalize_field_value(field, value)
                merged[field] = self._merge_unique_list(existing_items, update_items)
            else:
                merged[field] = self._normalize_field_value(field, value)

        for field in _JSON_DICT_FIELDS:
            merged[field] = self._normalize_field_value(field, merged.get(field))
        for field in _JSON_LIST_FIELDS:
            merged[field] = self._normalize_field_value(field, merged.get(field))

        return merged

    async def save_profile_update(
        self,
        session_id: int | None,
        update: dict[str, Any],
        user_id: int = 1,
        *,
        source: str = "agent",
    ) -> ProfileResponse:
        update = self.sanitize_profile_update(update)
        if self.session is None:
            payload = self.merge_profile(
                ProfileResponse(user_id=user_id, session_id=session_id).model_dump(),
                update,
            )
            payload["user_id"] = user_id
            payload["session_id"] = session_id
            return ProfileResponse(**payload)

        profile = await self._get_profile_by_user(user_id)
        if profile is None:
            profile = StudentProfile(user_id=user_id, session_id=session_id)
            self._normalize_profile_model(profile)
            self._require_session().add(profile)
            await self._require_session().flush()

        current = self._model_to_dict(profile)
        merged = self.merge_profile(current, update)
        changed_fields = self._changed_fields(current, merged)
        self._apply_to_model(profile, merged)
        profile.session_id = session_id
        self._normalize_profile_model(profile)

        self._require_session().add(profile)
        await self._record_snapshot(
            profile=profile,
            session_id=session_id,
            source=source,
            changed_fields=changed_fields,
        )
        await self._require_session().commit()
        await self._require_session().refresh(profile)
        return self._to_response(profile, session_id)

    async def preview_profile_update(
        self,
        *,
        user_id: int,
        session_id: int | None,
        update: dict[str, Any],
    ) -> tuple[ProfileResponse, dict[str, Any], list[str]]:
        sanitized = self.sanitize_profile_update(update)
        if self.session is None:
            current_response = ProfileResponse(user_id=user_id, session_id=session_id)
        else:
            profile = await self._get_profile_by_user(user_id)
            current_response = (
                self._to_response(profile, session_id)
                if profile is not None
                else ProfileResponse(user_id=user_id, session_id=session_id)
            )
        current = current_response.model_dump()
        merged = self.merge_profile(current, sanitized)
        changed_fields = self._changed_fields(current, merged)
        proposed_update = {
            field: merged[field]
            for field in changed_fields
            if field in merged
        }
        return current_response, proposed_update, changed_fields

    async def update_profile_direct(
        self,
        *,
        user_id: int,
        session_id: int | None,
        update: dict[str, Any],
    ) -> ProfileResponse:
        """用户主动编辑画像：只更新显式提交的字段，允许清空列表/字典/文本。"""
        if self.session is None:
            payload = ProfileResponse(user_id=user_id, session_id=session_id).model_dump()
            payload.update(self._normalize_direct_update(update))
            return ProfileResponse(**payload)

        profile = await self._get_profile_by_user(user_id)
        if profile is None:
            profile = StudentProfile(user_id=user_id, session_id=session_id)
            self._normalize_profile_model(profile)
            self._require_session().add(profile)
            await self._require_session().flush()

        normalized = self._normalize_direct_update(update)
        current = self._model_to_dict(profile)
        self._apply_to_model(profile, normalized)
        profile.session_id = session_id
        self._normalize_profile_model(profile)
        changed_fields = self._changed_fields(current, self._model_to_dict(profile))

        self._require_session().add(profile)
        await self._record_snapshot(
            profile=profile,
            session_id=session_id,
            source="manual",
            changed_fields=changed_fields,
        )
        await self._require_session().commit()
        await self._require_session().refresh(profile)
        return self._to_response(profile, session_id)

    async def list_profile_history(
        self,
        *,
        user_id: int,
        limit: int = 20,
    ) -> list[ProfileHistoryItem]:
        if self.session is None:
            return []

        result = await self._require_session().execute(
            select(ProfileSnapshot)
            .where(ProfileSnapshot.user_id == user_id)
            .order_by(ProfileSnapshot.created_at.desc(), ProfileSnapshot.id.desc())
            .limit(max(1, min(limit, 100)))
        )
        snapshots = list(result.scalars().all())
        return [
            ProfileHistoryItem(
                id=snapshot.id,
                user_id=snapshot.user_id,
                session_id=snapshot.session_id,
                source=snapshot.source,
                changed_fields=snapshot.changed_fields or [],
                profile_data=snapshot.profile_data or {},
                created_at=snapshot.created_at.isoformat(),
            )
            for snapshot in snapshots
        ]

    def sanitize_profile_update(self, update: dict[str, Any]) -> dict[str, Any]:
        sanitized: dict[str, Any] = {}
        for field, value in update.items():
            if field not in _PROFILE_FIELDS:
                continue

            normalized = self._normalize_agent_field_value(field, value)
            if normalized is None:
                continue

            sanitized[field] = normalized

        return sanitized

    def _normalize_direct_update(self, update: dict[str, Any]) -> dict[str, Any]:
        normalized: dict[str, Any] = {}
        for field, value in update.items():
            if field not in _PROFILE_FIELDS:
                continue
            normalized[field] = self._normalize_direct_field_value(field, value)
        return normalized

    async def _get_profile_by_user(self, user_id: int) -> StudentProfile | None:
        result = await self._require_session().execute(
            select(StudentProfile).where(StudentProfile.user_id == user_id)
        )
        return result.scalars().first()

    def _to_response(
        self,
        profile: StudentProfile,
        session_id: int | None = None,
    ) -> ProfileResponse:
        resp = ProfileResponse.model_validate(profile)
        resp.session_id = session_id
        return resp

    def _model_to_dict(self, profile: StudentProfile) -> dict[str, Any]:
        return {
            "major": profile.major,
            "grade": profile.grade,
            "knowledge_base": profile.knowledge_base,
            "cognitive_style": profile.cognitive_style,
            "learning_goal": profile.learning_goal,
            "weak_points": profile.weak_points,
            "learning_pace": profile.learning_pace,
            "interest_areas": profile.interest_areas,
            "coding_level": profile.coding_level,
            "weekly_hours": profile.weekly_hours,
        }

    def _apply_to_model(self, profile: StudentProfile, data: dict[str, Any]) -> None:
        for field in _PROFILE_FIELDS:
            if field in data:
                setattr(profile, field, data[field])

    def _changed_fields(
        self,
        before: dict[str, Any],
        after: dict[str, Any],
    ) -> list[str]:
        return [
            field
            for field in sorted(_PROFILE_FIELDS)
            if self._normalize_field_value(field, before.get(field))
            != self._normalize_field_value(field, after.get(field))
        ]

    async def _record_snapshot(
        self,
        *,
        profile: StudentProfile,
        session_id: int | None,
        source: str,
        changed_fields: list[str],
    ) -> None:
        if not changed_fields:
            return
        snapshot = ProfileSnapshot(
            user_id=profile.user_id,
            session_id=session_id,
            source=source,
            changed_fields=changed_fields,
            profile_data=self._to_response(profile, session_id).model_dump(),
        )
        self._require_session().add(snapshot)

    def _normalize_profile_model(self, profile: StudentProfile) -> bool:
        changed = False
        for field in _JSON_DICT_FIELDS:
            normalized = self._normalize_field_value(
                field, getattr(profile, field, None)
            )
            if getattr(profile, field, None) != normalized:
                setattr(profile, field, normalized)
                changed = True
        for field in _JSON_LIST_FIELDS:
            normalized = self._normalize_field_value(
                field, getattr(profile, field, None)
            )
            if getattr(profile, field, None) != normalized:
                setattr(profile, field, normalized)
                changed = True
        return changed

    def _normalize_agent_field_value(self, field: str, value: Any) -> Any:
        if field in _TEXT_FIELDS:
            if isinstance(value, str):
                normalized_text = value.strip()
                return normalized_text or None
            return None

        if field in _INT_FIELDS:
            if isinstance(value, bool):
                return None
            if isinstance(value, int):
                return value if value > 0 else None
            return None

        if field in _JSON_DICT_FIELDS:
            return value if isinstance(value, dict) and value else None

        if field in _JSON_LIST_FIELDS:
            return value if isinstance(value, list) and value else None

        return value

    def _normalize_direct_field_value(self, field: str, value: Any) -> Any:
        if value is None:
            if field in _JSON_DICT_FIELDS:
                return {}
            if field in _JSON_LIST_FIELDS:
                return []
            return None

        if field in _TEXT_FIELDS:
            if not isinstance(value, str):
                return None
            text = value.strip()
            return text or None

        if field in _INT_FIELDS:
            if isinstance(value, bool):
                return None
            if isinstance(value, int):
                return max(0, value)
            return None

        if field in _JSON_DICT_FIELDS:
            return self._normalize_field_value(field, value)

        if field in _JSON_LIST_FIELDS:
            if not isinstance(value, list):
                return []
            return self._merge_unique_list([], value)

        return value

    def _normalize_field_value(self, field: str, value: Any) -> Any:
        if field in _JSON_DICT_FIELDS:
            if field == "knowledge_base":
                return self._normalize_knowledge_base(value)
            return value if isinstance(value, dict) else {}
        if field in _JSON_LIST_FIELDS:
            return value if isinstance(value, list) else []
        return value

    def _normalize_knowledge_base(self, value: Any) -> dict[str, Any]:
        if not isinstance(value, dict):
            return {}

        subject = value.get("subject")
        level = value.get("level")
        if isinstance(subject, str) and subject.strip():
            normalized_level = level if isinstance(level, str) and level.strip() else "未知"
            return {subject.strip(): normalized_level}

        normalized: dict[str, Any] = {}
        for concept, raw_level in value.items():
            if concept in {"subject", "level"} or not isinstance(concept, str):
                continue
            concept_name = concept.strip()
            if not concept_name:
                continue

            if isinstance(raw_level, dict):
                level_value = raw_level.get("level")
                if level_value is None:
                    level_value = raw_level.get("status")
            else:
                level_value = raw_level

            if isinstance(level_value, str):
                level_text = level_value.strip()
                if level_text:
                    normalized[concept_name] = level_text
            elif isinstance(level_value, (int, float)) and not isinstance(
                level_value, bool
            ):
                normalized[concept_name] = level_value

        return normalized

    def _merge_unique_list(self, existing: list[Any], update: list[Any]) -> list[Any]:
        merged: list[Any] = []
        seen: set[str] = set()
        for item in [*existing, *update]:
            if not isinstance(item, str):
                continue
            normalized = item.strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            merged.append(normalized)
        return merged

    def _require_session(self) -> AsyncSession:
        if self.session is None:
            raise ValueError("ProfileService 需要有效的数据库会话")
        return self.session
