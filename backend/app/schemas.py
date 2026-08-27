from datetime import datetime
from typing import Literal
from pydantic import BaseModel, EmailStr, Field, field_validator

Role = Literal["admin", "quimico_farmaceutico"]

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"

class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=4)

class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=3)
    dni: str = Field(pattern=r"^\d{8}$")
    phone: str = Field(pattern=r"^\d{9}$")
    password: str = Field(min_length=6)
    role: Role = "quimico_farmaceutico"

    @field_validator("dni", "phone")
    @classmethod
    def only_digits(cls, value: str) -> str:
        return value.strip()

class UserUpdate(BaseModel):
    full_name: str | None = None
    email: EmailStr | None = None
    dni: str | None = Field(default=None, pattern=r"^\d{8}$")
    phone: str | None = Field(default=None, pattern=r"^\d{9}$")

class UserAdminUpdate(BaseModel):
    full_name: str | None = None
    email: EmailStr | None = None
    dni: str | None = Field(default=None, pattern=r"^\d{8}$")
    phone: str | None = Field(default=None, pattern=r"^\d{9}$")
    role: Role | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=6)

class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=6)

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

class ActivityOut(BaseModel):
    id: int
    action: str
    description: str
    created_at: datetime

    class Config:
        from_attributes = True

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

class RecipeBase(BaseModel):
    raw_text: str | None = None
    normalized_text: str | None = None
    patient_name: str | None = None
    patient_age: int | None = Field(default=None, ge=0, le=130)
    patient_phone: str | None = Field(default=None, pattern=r"^\d{9}$")
    service_reason: str | None = None
    doctor_name: str | None = None
    diagnosis: str | None = None
    composition: str | None = None
    administration_route: str | None = None
    dosage: str | None = None
    observations: str | None = None

class RecipeUpdate(RecipeBase):
    pass

class RecipeOut(RecipeBase):
    id: int
    code: str
    file_name: str
    status: str
    ocr_confidence: float
    ocr_engine: str | None = None
    low_confidence_fields: list[str] = Field(default_factory=list)
    dictionary_suggestions: list[DictionarySuggestion] = Field(default_factory=list)
    recognized_terms: list[RecognizedTerm] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    validated_at: datetime | None = None
    validator_name: str | None = None
    created_by_name: str | None = None

class RecipeListItem(BaseModel):
    id: int
    code: str
    file_name: str | None = None
    raw_text: str | None = None
    normalized_text: str | None = None
    patient_name: str | None = None
    patient_age: int | None = Field(default=None, ge=0, le=130)
    patient_phone: str | None = Field(default=None, pattern=r"^\d{9}$")
    service_reason: str | None = None
    doctor_name: str | None = None
    composition: str | None = None
    status: str
    ocr_confidence: float
    ocr_engine: str | None = None
    created_at: datetime
    validator_name: str | None = None

class ValidationIn(BaseModel):
    observations: str | None = None

class ConfigIn(BaseModel):
    notifications: bool = True
    theme: str = "claro"
    language: str = "es"

class ConfigOut(ConfigIn):
    updated_at: datetime

class DashboardOut(BaseModel):
    pending: int
    processed_week: int
    observed: int
    approved: int
    avg_confidence: float
    total_recipes: int
    recent_recipes: list[RecipeListItem]
    activities: list[ActivityOut]

Token.model_rebuild()
