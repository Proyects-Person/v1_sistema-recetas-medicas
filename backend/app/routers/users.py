import os
from pathlib import Path
from uuid import uuid4
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session
from .. import schemas
from ..auth import get_current_user, get_password_hash, require_admin
from ..database import UPLOAD_DIR, get_db
from ..models import User
from ..ocr_pln import validate_image_file
from ..utils import add_activity

router = APIRouter(prefix="/users", tags=["Usuarios"])
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_MB", "10")) * 1024 * 1024
VALID_ROLES = {"admin", "quimico_farmaceutico"}


def _validate_dni_phone(dni: str, phone: str) -> tuple[str, str]:
    dni_clean = (dni or "").strip()
    phone_clean = (phone or "").strip()
    if not dni_clean.isdigit() or len(dni_clean) != 8:
        raise HTTPException(status_code=400, detail="El DNI debe contener exactamente 8 dígitos.")
    if not phone_clean.isdigit() or len(phone_clean) != 9:
        raise HTTPException(status_code=400, detail="El teléfono debe contener exactamente 9 dígitos.")
    return dni_clean, phone_clean

@router.get("", response_model=list[schemas.UserOut])
def list_users(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    return db.query(User).order_by(User.created_at.desc()).all()

@router.post("", response_model=schemas.UserOut, status_code=201)
def create_user(payload: schemas.UserCreate, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    if payload.role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail="Rol no válido. Usa admin o quimico_farmaceutico.")
    exists = db.query(User).filter(User.email == payload.email).first()
    if exists:
        raise HTTPException(status_code=409, detail="Ya existe una cuenta con este correo.")
    dni_clean, phone_clean = _validate_dni_phone(payload.dni, payload.phone)
    if db.query(User).filter(User.dni == dni_clean).first():
        raise HTTPException(status_code=409, detail="Ya existe una cuenta con este DNI.")
    user = User(
        email=str(payload.email),
        full_name=payload.full_name,
        dni=dni_clean,
        phone=phone_clean,
        role=payload.role,
        password_hash=get_password_hash(payload.password),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    add_activity(db, current_user.id, "Creación de usuario", f"Se creó la cuenta de {payload.full_name} con rol {payload.role}.")
    return user

@router.put("/me", response_model=schemas.UserOut)
def update_me(payload: schemas.UserUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if payload.email and payload.email != current_user.email:
        exists = db.query(User).filter(User.email == payload.email).first()
        if exists:
            raise HTTPException(status_code=409, detail="El correo ya está registrado.")
        current_user.email = str(payload.email)
    if payload.full_name:
        current_user.full_name = payload.full_name
    if payload.dni is not None:
        dni_clean = payload.dni.strip()
        if not dni_clean.isdigit() or len(dni_clean) != 8:
            raise HTTPException(status_code=400, detail="El DNI debe contener exactamente 8 dígitos.")
        exists = db.query(User).filter(User.dni == dni_clean, User.id != current_user.id).first()
        if exists:
            raise HTTPException(status_code=409, detail="El DNI ya está registrado.")
        current_user.dni = dni_clean
    if payload.phone is not None:
        phone_clean = payload.phone.strip()
        if not phone_clean.isdigit() or len(phone_clean) != 9:
            raise HTTPException(status_code=400, detail="El teléfono debe contener exactamente 9 dígitos.")
        current_user.phone = phone_clean
    db.commit()
    db.refresh(current_user)
    add_activity(db, current_user.id, "Actualización de perfil", "Los datos personales fueron actualizados.")
    return current_user

@router.post("/me/photo", response_model=schemas.UserOut)
def upload_photo(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        validate_image_file(file.filename or "foto.png", file.content_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    content = file.file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"El archivo supera el límite permitido de {MAX_UPLOAD_BYTES // (1024 * 1024)}MB.")

    ext = Path(file.filename or "foto.png").suffix.lower()
    profile_dir = UPLOAD_DIR / "profiles"
    profile_dir.mkdir(exist_ok=True)
    safe_name = f"profile_{current_user.id}_{uuid4().hex}{ext}"
    path = profile_dir / safe_name
    with path.open("wb") as buffer:
        buffer.write(content)
    current_user.photo_url = f"/api/files/profiles/{safe_name}"
    db.commit()
    db.refresh(current_user)
    add_activity(db, current_user.id, "Carga de imagen", "La foto de perfil fue actualizada.")
    return current_user

@router.put("/{user_id}", response_model=schemas.UserOut)
def update_user(user_id: int, payload: schemas.UserAdminUpdate, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    if payload.email and str(payload.email) != user.email:
        exists = db.query(User).filter(User.email == payload.email).first()
        if exists:
            raise HTTPException(status_code=409, detail="El correo ya está registrado.")
        user.email = str(payload.email)
    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.dni is not None:
        dni_clean = payload.dni.strip()
        if not dni_clean.isdigit() or len(dni_clean) != 8:
            raise HTTPException(status_code=400, detail="El DNI debe contener exactamente 8 dígitos.")
        exists = db.query(User).filter(User.dni == dni_clean, User.id != user.id).first()
        if exists:
            raise HTTPException(status_code=409, detail="El DNI ya está registrado.")
        user.dni = dni_clean
    if payload.phone is not None:
        phone_clean = payload.phone.strip()
        if not phone_clean.isdigit() or len(phone_clean) != 9:
            raise HTTPException(status_code=400, detail="El teléfono debe contener exactamente 9 dígitos.")
        user.phone = phone_clean
    if payload.role is not None:
        if payload.role not in VALID_ROLES:
            raise HTTPException(status_code=400, detail="Rol no válido.")
        user.role = payload.role
    if payload.is_active is not None:
        if user.id == current_user.id and payload.is_active is False:
            raise HTTPException(status_code=400, detail="No puedes desactivar tu propia cuenta administradora.")
        user.is_active = payload.is_active
    if payload.password:
        user.password_hash = get_password_hash(payload.password)
    db.commit()
    db.refresh(user)
    add_activity(db, current_user.id, "Actualización de usuario", f"Se actualizó la cuenta de {user.full_name}.")
    return user
