from fastapi import APIRouter, HTTPException, Request

from app.schemas import PasswordChangeRequest, UnlockSessionRequest

router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.post("/password")
async def change_password(payload: PasswordChangeRequest, request: Request) -> dict[str, bool]:
    try:
        await request.app.state.profile_service.change_password(payload.old_password, payload.new_password)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail="Old password is invalid") from exc
    return {"changed": True}


@router.post("/unlock-session")
async def unlock_session(payload: UnlockSessionRequest, request: Request) -> dict[str, bool]:
    if not await request.app.state.profile_service.verify_password(payload.password):
        raise HTTPException(status_code=403, detail="Invalid password")
    return {"session_unlocked": True}
