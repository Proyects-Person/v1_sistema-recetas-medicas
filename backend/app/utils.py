import json
from datetime import datetime
from zoneinfo import ZoneInfo
from sqlalchemy.orm import Session
from .models import Activity, Recipe


def add_activity(db: Session, user_id: int | None, action: str, description: str) -> None:
    db.add(Activity(user_id=user_id, action=action, description=description))
    db.commit()


def generate_recipe_code(db: Session) -> str:
    year = datetime.now(ZoneInfo("America/Lima")).year
    count = db.query(Recipe).count() + 1
    return f"REC-{year}-{count:04d}"


def recipe_to_out(recipe: Recipe) -> dict:
    low_fields = []
    if recipe.low_confidence_fields:
        try:
            low_fields = json.loads(recipe.low_confidence_fields)
        except Exception:
            low_fields = []
    dictionary_suggestions = []
    if getattr(recipe, "dictionary_suggestions", None):
        try:
            dictionary_suggestions = json.loads(recipe.dictionary_suggestions)
        except Exception:
            dictionary_suggestions = []
    recognized_terms = []
    if getattr(recipe, "recognized_terms", None):
        try:
            recognized_terms = json.loads(recipe.recognized_terms)
        except Exception:
            recognized_terms = []
    return {
        "id": recipe.id,
        "code": recipe.code,
        "file_name": recipe.file_name,
        "status": recipe.status,
        "raw_text": recipe.raw_text,
        "normalized_text": getattr(recipe, "normalized_text", None),
        "dictionary_suggestions": dictionary_suggestions,
        "recognized_terms": recognized_terms,
        "ocr_confidence": round(float(recipe.ocr_confidence or 0), 2),
        "ocr_engine": recipe.ocr_engine,
        "low_confidence_fields": low_fields,
        "patient_name": recipe.patient_name,
        "patient_age": getattr(recipe, "patient_age", None),
        "patient_phone": getattr(recipe, "patient_phone", None),
        "service_reason": getattr(recipe, "service_reason", None),
        "doctor_name": recipe.doctor_name,
        "diagnosis": recipe.diagnosis,
        "composition": recipe.composition,
        "administration_route": recipe.administration_route,
        "dosage": recipe.dosage,
        "observations": recipe.observations,
        "created_at": recipe.created_at,
        "updated_at": recipe.updated_at,
        "validated_at": recipe.validated_at,
        "validator_name": recipe.validated_by.full_name if recipe.validated_by else None,
        "created_by_name": recipe.created_by.full_name if recipe.created_by else None,
    }


def recipe_to_list_item(recipe: Recipe) -> dict:
    return {
        "id": recipe.id,
        "code": recipe.code,
        "file_name": recipe.file_name,
        "raw_text": recipe.raw_text,
        "normalized_text": getattr(recipe, "normalized_text", None),
        "patient_name": recipe.patient_name,
        "patient_age": getattr(recipe, "patient_age", None),
        "patient_phone": getattr(recipe, "patient_phone", None),
        "service_reason": getattr(recipe, "service_reason", None),
        "doctor_name": recipe.doctor_name,
        "composition": recipe.composition,
        "status": recipe.status,
        "ocr_confidence": round(float(recipe.ocr_confidence or 0), 2),
        "ocr_engine": recipe.ocr_engine,
        "created_at": recipe.created_at,
        "validator_name": recipe.validated_by.full_name if recipe.validated_by else None,
    }
