from datetime import datetime
from typing import Literal

from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    field_validator,
)


Role = Literal[
    "admin",
    "quimico_farmaceutico",
]


# ============================================================
# VALIDADORES
# ============================================================

def validate_phone_number(
    value: str | None,
    field_name: str = "El teléfono",
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
        raise ValueError(
            f"{field_name} debe tener 9 dígitos y comenzar con 9."
        )

    return clean_value


# ============================================================
# AUTENTICACIÓN
# ============================================================

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"


class LoginIn(BaseModel):
    email: EmailStr

    password: str = Field(
        min_length=6
    )


class PasswordChange(BaseModel):
    current_password: str

    new_password: str = Field(
        min_length=6,
        max_length=128,
    )


class ForgotPasswordIn(BaseModel):
    email: EmailStr


class ResetPasswordIn(BaseModel):
    token: str = Field(
        min_length=20
    )

    new_password: str = Field(
        min_length=6,
        max_length=128,
    )


# ============================================================
# CREAR USUARIO
# ============================================================

class UserCreate(BaseModel):
    email: EmailStr

    full_name: str = Field(
        min_length=3
    )

    dni: str = Field(
        pattern=r"^\d{8}$"
    )

    phone: str

    password: str = Field(
        min_length=6
    )

    role: Role = "quimico_farmaceutico"

    @field_validator("dni")
    @classmethod
    def clean_dni(
        cls,
        value: str,
    ) -> str:

        return value.strip()

    @field_validator("phone")
    @classmethod
    def validate_phone(
        cls,
        value: str,
    ) -> str:

        result = validate_phone_number(
            value,
            "El teléfono",
        )

        if result is None:
            raise ValueError(
                "El teléfono es obligatorio."
            )

        return result


# ============================================================
# EDITAR USUARIO
# ============================================================

class UserUpdate(BaseModel):
    full_name: str | None = None

    email: EmailStr | None = None

    dni: str | None = Field(
        default=None,
        pattern=r"^\d{8}$"
    )

    phone: str | None = None

    @field_validator("phone")
    @classmethod
    def validate_phone(
        cls,
        value: str | None,
    ) -> str | None:

        return validate_phone_number(
            value,
            "El teléfono",
        )


# ============================================================
# EDICIÓN DE USUARIO POR ADMINISTRADOR
# ============================================================

class UserAdminUpdate(BaseModel):
    full_name: str | None = None

    email: EmailStr | None = None

    dni: str | None = Field(
        default=None,
        pattern=r"^\d{8}$"
    )

    phone: str | None = None

    role: Role | None = None

    is_active: bool | None = None

    password: str | None = Field(
        default=None,
        min_length=6,
        max_length=128,
    )

    @field_validator("phone")
    @classmethod
    def validate_phone(
        cls,
        value: str | None,
    ) -> str | None:

        return validate_phone_number(
            value,
            "El teléfono",
        )


# ============================================================
# SALIDA DE USUARIO
#
# IMPORTANTE:
# Aquí NO validamos nuevamente el teléfono.
# De esta forma usuarios antiguos no rompen una consulta.
# ============================================================

class UserOut(BaseModel):
    id: int

    email: EmailStr

    full_name: str

    role: str

    dni: str | None = None

    phone: str | None = None

    photo_url: str | None = None

    is_active: bool

    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================
# ACTIVIDAD
# ============================================================

class ActivityOut(BaseModel):
    id: int

    action: str

    description: str

    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================
# DICCIONARIO
# ============================================================

class DictionarySuggestion(BaseModel):
    original: str

    suggestion: str

    category: str | None = None

    confidence: float | None = None

    reason: str | None = None

    mode: str | None = None


class RecognizedTerm(BaseModel):
    term: str

    category: str | None = None

    match: str | None = None

    confidence: float | None = None

    mode: str | None = None


# ============================================================
# RECETA ESTRUCTURADA
# ============================================================

class IngredientExtraction(BaseModel):
    ingredient: str

    concentration: str | None = None

    confidence: float | None = None

    sources: list[str] = Field(
        default_factory=list
    )

    source_line: str | None = None

    line_number: int | None = None


class NerEntity(BaseModel):
    text: str

    label: str

    start: int

    end: int

    canonical: str | None = None

    source: str | None = None


# ============================================================
# DATOS BASE DE RECETA
#
# IMPORTANTE:
#
# NO colocamos aquí el validator del teléfono.
#
# RecipeOut hereda esta clase.
# Si validáramos aquí, FastAPI volvería a rechazar
# recetas antiguas como 123456787 al CONSULTARLAS.
# ============================================================

class RecipeBase(BaseModel):
    patient_name: str | None = None

    patient_age: int | None = Field(
        default=None,
        ge=0,
        le=130,
    )

    patient_phone: str | None = None

    service_reason: str | None = None

    doctor_name: str | None = None

    diagnosis: str | None = None

    composition: str | None = None

    administration_route: str | None = None

    dosage: str | None = None

    observations: str | None = None


# ============================================================
# EDITAR RECETA
#
# AQUÍ SÍ VALIDAMOS EL TELÉFONO.
#
# Es decir:
#
# - Consultar receta antigua: permitido.
# - Intentar guardar 123456789: rechazado.
# - Intentar guardar 987654321: permitido.
# ============================================================

class RecipeUpdate(RecipeBase):

    structured_ingredients: list[
        IngredientExtraction
    ] | None = None

    @field_validator("patient_phone")
    @classmethod
    def validate_patient_phone(
        cls,
        value: str | None,
    ) -> str | None:

        return validate_phone_number(
            value,
            "El teléfono del paciente",
        )


# ============================================================
# SALIDA COMPLETA DE RECETA
#
# NO lleva validator del teléfono.
# ============================================================

class RecipeOut(RecipeBase):
    id: int

    code: str

    file_name: str

    status: str

    ocr_confidence: float

    ocr_engine: str | None = None

    low_confidence_fields: list[str] = Field(
        default_factory=list
    )

    dictionary_suggestions: list[
        DictionarySuggestion
    ] = Field(
        default_factory=list
    )

    recognized_terms: list[
        RecognizedTerm
    ] = Field(
        default_factory=list
    )

    structured_ingredients: list[
        IngredientExtraction
    ] = Field(
        default_factory=list
    )

    ner_entities: list[
        NerEntity
    ] = Field(
        default_factory=list
    )

    created_at: datetime

    updated_at: datetime

    validated_at: datetime | None = None

    validator_name: str | None = None

    created_by_name: str | None = None


# ============================================================
# LISTADO DE RECETAS
#
# UTILIZADO POR:
#
# - Historial
# - Dashboard / Inicio
#
# MUY IMPORTANTE:
# NO debe tener validator de patient_phone.
# ============================================================

class RecipeListItem(BaseModel):
    id: int

    code: str

    file_name: str | None = None

    patient_name: str | None = None

    patient_age: int | None = Field(
        default=None,
        ge=0,
        le=130,
    )

    patient_phone: str | None = None

    service_reason: str | None = None

    doctor_name: str | None = None

    composition: str | None = None

    status: str

    ocr_confidence: float

    ocr_engine: str | None = None

    created_at: datetime

    validator_name: str | None = None


# ============================================================
# VALIDACIÓN FARMACÉUTICA
# ============================================================

class ValidationIn(BaseModel):
    observations: str | None = None


# ============================================================
# CONFIGURACIÓN
# ============================================================

class ConfigIn(BaseModel):
    notifications: bool = True

    theme: str = "claro"

    language: str = "es"


class ConfigOut(ConfigIn):
    updated_at: datetime


# ============================================================
# DASHBOARD
# ============================================================

class DashboardOut(BaseModel):
    pending: int

    processed_week: int

    observed: int

    approved: int

    avg_confidence: float

    total_recipes: int

    recent_recipes: list[
        RecipeListItem
    ]

    activities: list[
        ActivityOut
    ]


Token.model_rebuild()