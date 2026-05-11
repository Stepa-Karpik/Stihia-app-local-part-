import hashlib

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models import ProfileRecord


class ProfileService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def change_password(self, old_password: str | None, new_password: str) -> None:
        async with self._session_factory() as session:
            profile = await self._get_or_create_profile(session)
            if profile.password_hash is not None and profile.password_hash != self._hash(old_password or ""):
                raise PermissionError("Old password is invalid")
            profile.password_hash = self._hash(new_password)
            await session.commit()

    async def verify_password(self, password: str) -> bool:
        async with self._session_factory() as session:
            profile = await self._get_or_create_profile(session)
            return profile.password_hash is not None and profile.password_hash == self._hash(password)

    async def _get_or_create_profile(self, session: AsyncSession) -> ProfileRecord:
        profile = await session.get(ProfileRecord, "default")
        if profile is None:
            profile = ProfileRecord(id="default")
            session.add(profile)
            await session.flush()
        return profile

    def _hash(self, value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()
