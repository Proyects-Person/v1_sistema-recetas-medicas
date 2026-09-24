import hashlib
import secrets

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException

from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import schemas

from ..auth import (
    create_access_token,
    get_current_user,
    get_password_hash,
    verify_password,
)

from ..database import get_db

from ..email_service import send_password_reset_email

from ..models import PasswordResetToken, User

from ..utils import add_activity


router = APIRouter(
    prefix="/auth",
    tags=["Autenticación"],
)


RESET_TOKEN_EXPIRE_MINUTES = 30


GENERIC_RESET_MESSAGE = (
    "Si el correo está registrado y la cuenta está activa, "
    "recibirás un enlace para restablecer tu contraseña."
)


def hash_reset_token(token: str) -> str:
    """
    Convierte el token real en un hash SHA-256.

    El token real se envía al correo del usuario.
    En la base de datos solamente se almacena el hash.
    """

    return hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()


# ============================================================
# LOGIN
# ============================================================

@router.post(
    "/login",
    response_model=schemas.Token,
)
def login(
    payload: schemas.LoginIn,
    db: Session = Depends(get_db),
):
    user = (
        db.query(User)
        .filter(
            User.email == payload.email
        )
        .first()
    )

    if (
        not user
        or not verify_password(
            payload.password,
            user.password_hash,
        )
    ):
        raise HTTPException(
            status_code=401,
            detail="Credenciales incorrectas.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail=(
                "La cuenta está inactiva. "
                "Solicita reactivación al administrador."
            ),
        )

    token = create_access_token(
        user.email
    )

    add_activity(
        db,
        user.id,
        "Inicio de sesión",
        f"{user.full_name} accedió al sistema.",
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user,
    }


# ============================================================
# OLVIDÉ MI CONTRASEÑA
# ============================================================

@router.post("/forgot-password")
def forgot_password(
    payload: schemas.ForgotPasswordIn,
    db: Session = Depends(get_db),
):
    email = (
        payload.email
        .strip()
        .lower()
    )

    user = (
        db.query(User)
        .filter(
            func.lower(User.email) == email
        )
        .first()
    )

    # No indicamos si el correo existe o no.
    # Esto evita revelar qué usuarios están registrados.
    if not user or not user.is_active:
        return {
            "message": GENERIC_RESET_MESSAGE
        }

    now = datetime.utcnow()

    # ========================================================
    # INVALIDAR TOKENS ANTERIORES
    # ========================================================

    (
        db.query(PasswordResetToken)
        .filter(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None),
        )
        .update(
            {
                "used_at": now
            },
            synchronize_session=False,
        )
    )

    # ========================================================
    # GENERAR TOKEN
    # ========================================================

    raw_token = secrets.token_urlsafe(48)

    token_hash = hash_reset_token(
        raw_token
    )

    expires_at = (
        now
        + timedelta(
            minutes=RESET_TOKEN_EXPIRE_MINUTES
        )
    )

    reset_token = PasswordResetToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at,
    )

    db.add(
        reset_token
    )

    db.commit()

    db.refresh(
        reset_token
    )

    # ========================================================
    # ENVIAR CORREO
    # ========================================================

    try:
        send_password_reset_email(
            to_email=user.email,
            full_name=user.full_name,
            token=raw_token,
        )

    except Exception as exc:
        # Si el correo no pudo enviarse,
        # invalidamos el token generado.

        reset_token.used_at = (
            datetime.utcnow()
        )

        db.commit()

        print(
            "[ERROR SMTP] "
            "No se pudo enviar el correo "
            f"de recuperación: {exc}"
        )

        raise HTTPException(
            status_code=503,
            detail=(
                "No se pudo enviar el correo "
                "de recuperación. "
                "Inténtalo nuevamente."
            ),
        )

    return {
        "message": GENERIC_RESET_MESSAGE
    }


# ============================================================
# RESTABLECER CONTRASEÑA
# ============================================================

@router.post("/reset-password")
def reset_password(
    payload: schemas.ResetPasswordIn,
    db: Session = Depends(get_db),
):
    now = datetime.utcnow()

    token_hash = hash_reset_token(
        payload.token
    )

    reset_token = (
        db.query(PasswordResetToken)
        .filter(
            PasswordResetToken.token_hash
            == token_hash
        )
        .first()
    )

    # ========================================================
    # TOKEN INEXISTENTE
    # ========================================================

    if not reset_token:
        raise HTTPException(
            status_code=400,
            detail=(
                "El enlace de recuperación "
                "no es válido."
            ),
        )

    # ========================================================
    # TOKEN YA UTILIZADO
    # ========================================================

    if reset_token.used_at is not None:
        raise HTTPException(
            status_code=400,
            detail=(
                "Este enlace de recuperación "
                "ya fue utilizado."
            ),
        )

    # ========================================================
    # TOKEN VENCIDO
    # ========================================================

    if reset_token.expires_at < now:
        raise HTTPException(
            status_code=400,
            detail=(
                "El enlace de recuperación "
                "ha vencido. Solicita uno nuevo."
            ),
        )

    # ========================================================
    # BUSCAR USUARIO
    # ========================================================

    user = (
        db.query(User)
        .filter(
            User.id == reset_token.user_id
        )
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=400,
            detail=(
                "El usuario asociado "
                "ya no existe."
            ),
        )

    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail=(
                "La cuenta está inactiva. "
                "Solicita reactivación "
                "al administrador."
            ),
        )

    # ========================================================
    # CAMBIAR CONTRASEÑA
    # ========================================================

    user.password_hash = (
        get_password_hash(
            payload.new_password
        )
    )

    # Marcar token como utilizado
    reset_token.used_at = now

    # ========================================================
    # INVALIDAR OTROS TOKENS
    # ========================================================

    (
        db.query(PasswordResetToken)
        .filter(
            PasswordResetToken.user_id
            == user.id,

            PasswordResetToken.id
            != reset_token.id,

            PasswordResetToken.used_at.is_(None),
        )
        .update(
            {
                "used_at": now
            },
            synchronize_session=False,
        )
    )

    db.commit()

    # ========================================================
    # REGISTRAR ACTIVIDAD
    # ========================================================

    add_activity(
        db,
        user.id,
        "Recuperación de contraseña",
        (
            "La contraseña fue "
            "restablecida correctamente "
            "mediante el correo registrado."
        ),
    )

    return {
        "message": (
            "Contraseña restablecida correctamente. "
            "Ya puedes iniciar sesión."
        )
    }


# ============================================================
# INFORMACIÓN DEL USUARIO ACTUAL
# ============================================================

@router.get(
    "/me",
    response_model=schemas.UserOut,
)
def me(
    current_user: User = Depends(
        get_current_user
    ),
):
    return current_user


# ============================================================
# LOGOUT
# ============================================================

@router.post("/logout")
def logout(
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):
    add_activity(
        db,
        current_user.id,
        "Cierre de sesión",
        (
            f"{current_user.full_name} "
            "cerró sesión correctamente."
        ),
    )

    return {
        "message": (
            "Sesión finalizada correctamente."
        )
    }


# ============================================================
# CAMBIO DE CONTRASEÑA DESDE CONFIGURACIÓN
# ============================================================

@router.post("/change-password")
def change_password(
    payload: schemas.PasswordChange,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):
    if not verify_password(
        payload.current_password,
        current_user.password_hash,
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "La contraseña actual "
                "no es correcta."
            ),
        )

    current_user.password_hash = (
        get_password_hash(
            payload.new_password
        )
    )

    db.commit()

    add_activity(
        db,
        current_user.id,
        "Cambio de contraseña",
        (
            "La contraseña fue "
            "actualizada correctamente."
        ),
    )

    return {
        "message": (
            "Contraseña actualizada correctamente."
        )
    }