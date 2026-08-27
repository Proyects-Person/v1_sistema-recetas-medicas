from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import schemas
from ..auth import create_access_token, get_current_user, get_password_hash, verify_password
from ..database import get_db
from ..models import User
from ..utils import add_activity

router = APIRouter(prefix="/auth", tags=["Autenticación"])

@router.post("/login", response_model=schemas.Token)
def login(payload: schemas.LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Credenciales incorrectas.")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="La cuenta está inactiva. Solicita reactivación al administrador.")
    token = create_access_token(user.email)
    add_activity(db, user.id, "Inicio de sesión", f"{user.full_name} accedió al sistema.")
    return {"access_token": token, "token_type": "bearer", "user": user}

@router.get("/me", response_model=schemas.UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user

@router.post("/logout")
def logout(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    add_activity(db, current_user.id, "Cierre de sesión", f"{current_user.full_name} cerró sesión correctamente.")
    return {"message": "Sesión finalizada correctamente."}

@router.post("/change-password")
def change_password(
    payload: schemas.PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="La contraseña actual no es correcta.")
    current_user.password_hash = get_password_hash(payload.new_password)
    db.commit()
    add_activity(db, current_user.id, "Cambio de contraseña", "La contraseña fue actualizada correctamente.")
    return {"message": "Contraseña actualizada correctamente."}
