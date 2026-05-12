import hashlib

import pytest

from app.db.models import ProfileRecord
from app.db.session import create_session_factory, init_models
from app.services.profile_service import ProfileService


@pytest.mark.asyncio
async def test_profile_password_uses_salted_pbkdf2_hash(tmp_path):
    session_factory = create_session_factory(f"sqlite+aiosqlite:///{tmp_path / 'profile.db'}")
    await init_models(session_factory)
    service = ProfileService(session_factory)

    await service.change_password(None, "secret-1")

    async with session_factory() as session:
        profile = await session.get(ProfileRecord, "default")
        assert profile is not None
        assert profile.password_hash is not None
        assert profile.password_hash.startswith("pbkdf2_sha256$")
        assert "secret-1" not in profile.password_hash
    assert await service.verify_password("secret-1") is True
    assert await service.verify_password("bad") is False


@pytest.mark.asyncio
async def test_profile_accepts_legacy_sha256_once_and_rehashes_on_change(tmp_path):
    session_factory = create_session_factory(f"sqlite+aiosqlite:///{tmp_path / 'profile.db'}")
    await init_models(session_factory)
    legacy_hash = hashlib.sha256("old-secret".encode("utf-8")).hexdigest()
    async with session_factory() as session:
        session.add(ProfileRecord(id="default", password_hash=legacy_hash))
        await session.commit()

    service = ProfileService(session_factory)
    await service.change_password("old-secret", "new-secret")

    assert await service.verify_password("new-secret") is True
    async with session_factory() as session:
        profile = await session.get(ProfileRecord, "default")
        assert profile is not None
        assert profile.password_hash is not None
        assert profile.password_hash.startswith("pbkdf2_sha256$")
