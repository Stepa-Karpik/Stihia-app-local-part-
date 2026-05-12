import hashlib
import hmac
import secrets

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models import ProfileRecord


class ProfileService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def change_password(self, old_password: str | None, new_password: str) -> None:
        async with self._session_factory() as session:
            profile = await self._get_or_create_profile(session)
            if profile.password_hash is not None and not self._verify_hash(old_password or "", profile.password_hash):
                raise PermissionError("Old password is invalid")
            profile.password_hash = self._hash(new_password)
            await session.commit()

    async def verify_password(self, password: str) -> bool:
        async with self._session_factory() as session:
            profile = await self._get_or_create_profile(session)
            return profile.password_hash is not None and self._verify_hash(password, profile.password_hash)

    async def _get_or_create_profile(self, session: AsyncSession) -> ProfileRecord:
        profile = await session.get(ProfileRecord, "default")
        if profile is None:
            profile = ProfileRecord(id="default")
            session.add(profile)
            await session.flush()
        return profile

    def _hash(self, value: str) -> str:
        iterations = 390000
        salt = secrets.token_hex(16)
        digest = hashlib.pbkdf2_hmac("sha256", value.encode("utf-8"), salt.encode("utf-8"), iterations).hex()
        return f"pbkdf2_sha256${iterations}${salt}${digest}"

    def _verify_hash(self, value: str, stored_hash: str) -> bool:
        if stored_hash.startswith("pbkdf2_sha256$"):
            _algorithm, iterations, salt, digest = stored_hash.split("$", 3)
            candidate = hashlib.pbkdf2_hmac(
                "sha256",
                value.encode("utf-8"),
                salt.encode("utf-8"),
                int(iterations),
            ).hex()
            return hmac.compare_digest(candidate, digest)
        legacy = hashlib.sha256(value.encode("utf-8")).hexdigest()
        return hmac.compare_digest(legacy, stored_hash)
