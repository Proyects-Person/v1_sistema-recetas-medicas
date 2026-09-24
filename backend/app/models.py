from datetime import datetime

from fastapi import HTTPException

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)

from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
    validates,
)

from .database import Base


# ============================================================
# VALIDACIÓN CENTRAL DE TELÉFONOS
# ============================================================

def validate_peruvian_phone(
    value: str | None,
    field_name: str,
) -> str | None:

    if value is None:
        return None

    clean_value = value.strip()

    if clean_value == "":
        return None

    if (
        not clean_value.isdigit()
        or len(clean_value) != 9
        or not clean_value.startswith("9")
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                f"{field_name} debe tener "
                "9 dígitos y comenzar con 9."
            ),
        )

    return clean_value


# ============================================================
# USUARIO
# ============================================================

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    email: Mapped[str] = mapped_column(
        String(180),
        unique=True,
        index=True,
        nullable=False,
    )

    full_name: Mapped[str] = mapped_column(
        String(180),
        nullable=False,
    )

    role: Mapped[str] = mapped_column(
        String(60),
        default="quimico_farmaceutico",
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    dni: Mapped[str | None] = mapped_column(
        String(20),
        unique=True,
        index=True,
        nullable=True,
    )

    phone: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    photo_url: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )

    recipes_uploaded = relationship(
        "Recipe",
        foreign_keys="Recipe.created_by_id",
        back_populates="created_by",
    )

    recipes_validated = relationship(
        "Recipe",
        foreign_keys="Recipe.validated_by_id",
        back_populates="validated_by",
    )

    password_reset_tokens = relationship(
        "PasswordResetToken",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    @validates("phone")
    def validate_phone(
        self,
        key: str,
        value: str | None,
    ) -> str | None:

        return validate_peruvian_phone(
            value,
            "El teléfono",
        )


# ============================================================
# TOKEN PARA RECUPERAR CONTRASEÑA
# ============================================================

class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    token_hash: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        index=True,
    )

    used_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )

    user = relationship(
        "User",
        back_populates="password_reset_tokens",
    )


# ============================================================
# ACTIVIDAD
# ============================================================

class Activity(Base):
    __tablename__ = "activities"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
    )

    action: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        index=True,
    )


# ============================================================
# RECETA
# ============================================================

class Recipe(Base):
    __tablename__ = "recipes"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    code: Mapped[str] = mapped_column(
        String(40),
        unique=True,
        index=True,
        nullable=False,
    )

    file_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    file_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    file_mime_type: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(40),
        default="pendiente",
        index=True,
    )

    raw_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    normalized_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    dictionary_suggestions: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    recognized_terms: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    structured_ingredients: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    ner_entities: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    ocr_confidence: Mapped[float] = mapped_column(
        Float,
        default=0.0,
    )

    ocr_engine: Mapped[str | None] = mapped_column(
        String(60),
        nullable=True,
    )

    low_confidence_fields: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    patient_name: Mapped[str | None] = mapped_column(
        String(180),
        nullable=True,
    )

    patient_age: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    patient_phone: Mapped[str | None] = mapped_column(
        String(9),
        nullable=True,
    )

    service_reason: Mapped[str | None] = mapped_column(
        String(80),
        nullable=True,
    )

    doctor_name: Mapped[str | None] = mapped_column(
        String(180),
        nullable=True,
    )

    diagnosis: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    composition: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    administration_route: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
    )

    dosage: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    observations: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
    )

    validated_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
    )

    validated_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        index=True,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    created_by = relationship(
        "User",
        foreign_keys=[created_by_id],
        back_populates="recipes_uploaded",
    )

    validated_by = relationship(
        "User",
        foreign_keys=[validated_by_id],
        back_populates="recipes_validated",
    )

    @validates("patient_phone")
    def validate_patient_phone(
        self,
        key: str,
        value: str | None,
    ) -> str | None:

        return validate_peruvian_phone(
            value,
            "El teléfono del paciente",
        )


# ============================================================
# CONFIGURACIÓN DEL USUARIO
# ============================================================

class UserConfig(Base):
    __tablename__ = "user_configs"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        unique=True,
        nullable=False,
    )

    notifications: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )

    theme: Mapped[str] = mapped_column(
        String(30),
        default="claro",
    )

    language: Mapped[str] = mapped_column(
        String(20),
        default="es",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )