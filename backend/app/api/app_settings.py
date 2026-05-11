from fastapi import APIRouter, Request

from app.schemas import AppSettingsRequest, AppSettingsResponse

router = APIRouter(prefix="/api/app-settings", tags=["app-settings"])


def serialize_settings(record: object) -> AppSettingsResponse:
    return AppSettingsResponse(
        studio_background=record.studio_background,
        studio_text=record.studio_text,
        studio_font_size=record.studio_font_size,
        speech_recognizer=record.speech_recognizer,
    )


@router.get("", response_model=AppSettingsResponse)
async def get_app_settings(request: Request) -> AppSettingsResponse:
    return serialize_settings(await request.app.state.app_settings_service.get_settings())


@router.put("", response_model=AppSettingsResponse)
async def update_app_settings(payload: AppSettingsRequest, request: Request) -> AppSettingsResponse:
    record = await request.app.state.app_settings_service.update_settings(
        studio_background=payload.studio_background,
        studio_text=payload.studio_text,
        studio_font_size=payload.studio_font_size,
        speech_recognizer=payload.speech_recognizer,
    )
    return serialize_settings(record)
