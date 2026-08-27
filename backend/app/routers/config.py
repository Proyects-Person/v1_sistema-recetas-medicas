from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from .. import schemas
from ..auth import get_current_user
from ..database import get_db
from ..models import User, UserConfig
from ..utils import add_activity

router = APIRouter(prefix="/config", tags=["Configuración"])

@router.get("", response_model=schemas.ConfigOut)
def get_config(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    config = db.query(UserConfig).filter(UserConfig.user_id == current_user.id).first()
    if not config:
        config = UserConfig(user_id=current_user.id)
        db.add(config)
        db.commit()
        db.refresh(config)
    return config

@router.put("", response_model=schemas.ConfigOut)
def save_config(payload: schemas.ConfigIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    config = db.query(UserConfig).filter(UserConfig.user_id == current_user.id).first()
    if not config:
        config = UserConfig(user_id=current_user.id)
        db.add(config)
    config.notifications = payload.notifications
    config.theme = payload.theme
    config.language = payload.language
    db.commit()
    db.refresh(config)
    add_activity(db, current_user.id, "Guardado de configuración", "La configuración del usuario fue guardada.")
    return config
