from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session
from .. import schemas
from ..auth import get_current_user
from ..database import get_db
from ..models import Activity, Recipe, User
from ..utils import recipe_to_list_item

router = APIRouter(prefix="/dashboard", tags=["Panel de Control"])

@router.get("", response_model=schemas.DashboardOut)
def dashboard(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    week_start = datetime.utcnow() - timedelta(days=7)
    total = db.query(Recipe).count()
    # Pendientes visibles para farmacia: recetas ya procesadas por OCR que faltan validar.
    pending = db.query(Recipe).filter(Recipe.status == "procesada").count()
    processed_week = db.query(Recipe).filter(Recipe.created_at >= week_start).count()
    observed = db.query(Recipe).filter(Recipe.status == "observada").count()
    approved = db.query(Recipe).filter(Recipe.status == "aprobada").count()
    avg_confidence = db.query(func.avg(Recipe.ocr_confidence)).filter(Recipe.ocr_confidence > 0).scalar() or 0
    recent = db.query(Recipe).order_by(Recipe.created_at.desc()).limit(6).all()
    validation_actions = [
        "Pendiente de validación",
        "Corrección manual",
        "Aprobación de receta",
        "Receta observada",
        "Cancelación de receta",
        "Eliminación de receta",
    ]
    activities = (
        db.query(Activity)
        .filter(Activity.action.in_(validation_actions))
        .order_by(Activity.created_at.desc())
        .limit(8)
        .all()
    )
    return {
        "pending": pending,
        "processed_week": processed_week,
        "observed": observed,
        "approved": approved,
        "avg_confidence": round(float(avg_confidence), 2),
        "total_recipes": total,
        "recent_recipes": [recipe_to_list_item(r) for r in recent],
        "activities": activities,
    }
