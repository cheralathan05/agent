"""Settings API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.database.models.setting import Setting
from backend.app.database.session import get_db

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])


class SettingUpdate(BaseModel):
    value: str


@router.get("")
async def list_settings(db: Session = Depends(get_db)):
    """List all settings."""
    settings = db.query(Setting).all()
    return {
        "settings": {s.key: s.value for s in settings}
    }


@router.put("/{key}")
async def update_setting(
    key: str,
    request: SettingUpdate,
    db: Session = Depends(get_db),
):
    """Update or create a setting."""
    setting = db.query(Setting).filter(Setting.key == key).first()
    if setting:
        setting.value = request.value
    else:
        setting = Setting(key=key, value=request.value)
        db.add(setting)
    db.commit()
    return {"key": key, "value": request.value}
