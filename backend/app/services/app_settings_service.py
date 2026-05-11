from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models import AppSettingRecord


class AppSettingsService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def get_settings(self) -> AppSettingRecord:
        async with self._session_factory() as session:
            return await self._get_or_create(session)

    async def update_settings(
        self,
        studio_background: str,
        studio_text: str,
        studio_font_size: int,
        speech_recognizer: str,
    ) -> AppSettingRecord:
        async with self._session_factory() as session:
            settings = await self._get_or_create(session)
            settings.studio_background = studio_background
            settings.studio_text = studio_text
            settings.studio_font_size = studio_font_size
            settings.speech_recognizer = speech_recognizer
            await session.commit()
            return settings

    async def _get_or_create(self, session: AsyncSession) -> AppSettingRecord:
        settings = await session.get(AppSettingRecord, "default")
        if settings is None:
            settings = AppSettingRecord(id="default")
            session.add(settings)
            await session.flush()
        return settings
