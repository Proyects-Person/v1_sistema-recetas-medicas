import json
import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from io import BytesIO
from xml.sax.saxutils import escape
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import Image as PdfImage, Paragraph, Preformatted, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib.utils import ImageReader
from .. import schemas
from ..auth import get_current_user
from ..database import get_db
from ..models import Recipe, User
from ..ocr_pln import extract_text_from_bytes, validate_image_file
from ..ocr_dictionary import analyze_ocr_text
from ..utils import add_activity, generate_recipe_code, recipe_to_list_item, recipe_to_out
from ..storage import delete_file as storage_delete_file, file_response, read_file_bytes, save_uploaded_file

router = APIRouter(prefix="/recipes", tags=["Recetas"])
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_MB", "10")) * 1024 * 1024

@router.post("/upload", response_model=schemas.RecipeOut, status_code=201)
def upload_recipe(
    file: UploadFile = File(...),
    patient_name: str = Form(...),
    patient_age: int = Form(...),
    patient_phone: str = Form(...),
    service_reason: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not patient_name.strip():
        raise HTTPException(status_code=400, detail="El nombre del paciente es obligatorio.")
    if patient_age < 0 or patient_age > 130:
        raise HTTPException(status_code=400, detail="La edad del paciente no es válida.")
    patient_phone_clean = patient_phone.strip()
    if not patient_phone_clean.isdigit() or len(patient_phone_clean) != 9:
        raise HTTPException(status_code=400, detail="El teléfono del paciente debe contener exactamente 9 dígitos.")
    if service_reason not in {"analisis_receta", "preparacion_magistral", "consulta_validacion", "otro"}:
        raise HTTPException(status_code=400, detail="El motivo de evaluación no es válido.")

    try:
        validate_image_file(file.filename or "receta.png", file.content_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    content = file.file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"El archivo supera el límite permitido de {MAX_UPLOAD_BYTES // (1024 * 1024)}MB.")

    try:
        file_ref = save_uploaded_file(file.filename or "receta.png", content, file.content_type, folder="recipes")
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    recipe = Recipe(
        code=generate_recipe_code(db),
        file_name=file.filename or "receta.png",
        file_path=file_ref,
        file_mime_type=file.content_type or "image/jpeg",
        status="pendiente",
        patient_name=patient_name.strip(),
        patient_age=patient_age,
        patient_phone=patient_phone_clean,
        service_reason=service_reason.strip(),
        created_by_id=current_user.id,
    )
    db.add(recipe)
    db.commit()
    db.refresh(recipe)
    add_activity(db, current_user.id, "Carga de receta", f"Se cargó la receta {recipe.code}.")
    return recipe_to_out(recipe)

@router.get("", response_model=list[schemas.RecipeListItem])
def list_recipes(
    status: str | None = Query(default=None),
    search: str | None = Query(default=None),
    date: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Recipe)
    if status:
        query = query.filter(Recipe.status == status)
    if search:
        term = f"%{search.strip()}%"
        query = query.filter(or_(Recipe.code.ilike(term), Recipe.raw_text.ilike(term), Recipe.normalized_text.ilike(term), Recipe.file_name.ilike(term), Recipe.patient_name.ilike(term), Recipe.service_reason.ilike(term)))
    if date:
        try:
            parsed = datetime.fromisoformat(date).date()
            query = query.filter(Recipe.created_at >= datetime.combine(parsed, datetime.min.time()))
            query = query.filter(Recipe.created_at <= datetime.combine(parsed, datetime.max.time()))
        except ValueError:
            raise HTTPException(status_code=400, detail="La fecha no tiene formato válido.")
    recipes = query.order_by(Recipe.created_at.desc()).all()
    return [recipe_to_list_item(r) for r in recipes]

@router.get("/{recipe_id}", response_model=schemas.RecipeOut)
def get_recipe(recipe_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    recipe = db.get(Recipe, recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Receta no encontrada.")
    return recipe_to_out(recipe)

@router.get("/{recipe_id}/file")
def get_recipe_file(recipe_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    recipe = db.get(Recipe, recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Receta no encontrada.")
    return file_response(recipe.file_path, recipe.file_name, recipe.file_mime_type)

@router.delete("/{recipe_id}")
def delete_recipe(recipe_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    recipe = db.get(Recipe, recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Receta no encontrada.")
    storage_delete_file(recipe.file_path)
    db.delete(recipe)
    db.commit()
    add_activity(db, current_user.id, "Eliminación de receta", f"Se eliminó la receta {recipe.code}.")
    return {"message": "Receta eliminada correctamente."}




"""
AQUI
"""
from ..nlp.regex_extractor import extract_regex_entities
from ..nlp.prescription_parser import parse_prescription

@router.post("/{recipe_id}/process", response_model=schemas.RecipeOut)
def process_recipe(recipe_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    recipe = db.get(Recipe, recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Receta no encontrada.")
    try:
        image_bytes = read_file_bytes(recipe.file_path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail="No existe un archivo válido para procesar.") from exc
    recipe.status = "procesando"
    db.commit()
    try:
        raw_text, confidence, engine_name = extract_text_from_bytes(image_bytes, recipe.file_name)
    except RuntimeError as exc:
        recipe.status = "pendiente"
        recipe.updated_at = datetime.utcnow()
        db.commit()
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    dictionary_result = analyze_ocr_text(raw_text, confidence)

    regex_result = extract_regex_entities(
    dictionary_result["normalized_text"]
    )

    parser_result = parse_prescription(
    raw_text,
    ocr_confidence=confidence,
    )
    components = parser_result.get("components", [])

    composition_lines = []

    for component in components:
        name = component.get("name")
        concentration = component.get("concentration")
        quantity = component.get("quantity")

        parts = []

        if name:
            parts.append(name)

        if concentration:
            parts.append(concentration)

        if quantity:
            normalized_quantity = quantity.get("normalized")
            if normalized_quantity:
                parts.append(normalized_quantity)

        if parts:
            composition_lines.append(" ".join(parts))

    dosage_parts = []

    if parser_result.get("frequency"):
        dosage_parts.append(
            parser_result["frequency"]
        )

    if parser_result.get("duration"):
        dosage_parts.append(
            parser_result["duration"]
        )

    dosage_text = " | ".join(dosage_parts) if dosage_parts else None
        
    recipe.raw_text = raw_text
    recipe.normalized_text = dictionary_result["normalized_text"]
    recipe.dictionary_suggestions = json.dumps(dictionary_result["dictionary_suggestions"], ensure_ascii=False)
    recipe.recognized_terms = json.dumps(dictionary_result["recognized_terms"], ensure_ascii=False)
    recipe.ocr_confidence = round(confidence * 100, 2) if confidence <= 1 else round(confidence, 2)
    recipe.ocr_engine = engine_name
    recipe.low_confidence_fields = json.dumps(["raw_text"] if confidence < 0.70 else [], ensure_ascii=False)

    # El sistema queda en modo transcripción OCR: no se rellenan datos estructurados
    # para evitar información inventada o ajena a la receta cargada.
    # Se conservan datos administrativos ingresados en la carga.

## recipe.doctor_name = None
## recipe.diagnosis = None
##  recipe.composition = None
##    recipe.administration_route = None
##    recipe.dosage = None

    recipe.composition = (
    "\n".join(composition_lines)
    if composition_lines
    else None
    )

    recipe.administration_route = parser_result.get(
        "administration_route"
    )

    recipe.dosage = dosage_text

    recipe.status = "procesada"
    recipe.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(recipe)
    add_activity(db, current_user.id, "Pendiente de validación", f"La receta {recipe.code} quedó procesada y pendiente de validación farmacéutica.")
    return recipe_to_out(recipe)

@router.put("/{recipe_id}/data", response_model=schemas.RecipeOut)
def update_recipe_data(
    recipe_id: int,
    payload: schemas.RecipeUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    recipe = db.get(Recipe, recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Receta no encontrada.")
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(recipe, field, value)
    if "raw_text" in data and data.get("raw_text") is not None:
        confidence_decimal = float(recipe.ocr_confidence or 0) / 100 if float(recipe.ocr_confidence or 0) > 1 else float(recipe.ocr_confidence or 0)
        dictionary_result = analyze_ocr_text(str(data.get("raw_text") or ""), confidence_decimal)
        recipe.normalized_text = dictionary_result["normalized_text"]
        recipe.dictionary_suggestions = json.dumps(dictionary_result["dictionary_suggestions"], ensure_ascii=False)
        recipe.recognized_terms = json.dumps(dictionary_result["recognized_terms"], ensure_ascii=False)
    recipe.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(recipe)
    add_activity(db, current_user.id, "Corrección manual", f"Se actualizaron los datos de la receta {recipe.code}.")
    return recipe_to_out(recipe)

@router.post("/{recipe_id}/approve", response_model=schemas.RecipeOut)
def approve_recipe(recipe_id: int, payload: schemas.ValidationIn | None = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _change_status(recipe_id, "aprobada", "Aprobación de receta", payload, current_user, db)

@router.post("/{recipe_id}/observe", response_model=schemas.RecipeOut)
def observe_recipe(recipe_id: int, payload: schemas.ValidationIn | None = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _change_status(recipe_id, "observada", "Receta observada", payload, current_user, db)

@router.post("/{recipe_id}/cancel", response_model=schemas.RecipeOut)
def cancel_recipe(recipe_id: int, payload: schemas.ValidationIn | None = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _change_status(recipe_id, "cancelada", "Cancelación de receta", payload, current_user, db)

@router.get("/{recipe_id}/download")
def download_recipe_summary(recipe_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    recipe = db.get(Recipe, recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Receta no encontrada.")
    pdf = _build_recipe_pdf(recipe)
    filename = f"{recipe.code}.pdf"
    return StreamingResponse(
        pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


def _service_reason_label(value: str | None) -> str:
    labels = {
        "analisis_receta": "Análisis de receta",
        "preparacion_magistral": "Preparar producto magistral",
        "consulta_validacion": "Consulta/validación farmacéutica",
        "otro": "Otro",
    }
    return labels.get(value or "", value or "No registrado")


LIMA_TZ = ZoneInfo("America/Lima")

def _lima_datetime(value: datetime | None) -> str:
    if not value:
        return "Pendiente"
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(LIMA_TZ).strftime("%d/%m/%Y %I:%M %p")

def _build_recipe_pdf(recipe: Recipe) -> BytesIO:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=1.5 * cm, leftMargin=1.5 * cm, topMargin=1.4 * cm, bottomMargin=1.4 * cm)
    styles = getSampleStyleSheet()
    title = ParagraphStyle("TitleCustom", parent=styles["Heading1"], fontSize=18, leading=22, textColor=colors.HexColor("#0F172A"), spaceAfter=10)
    subtitle = ParagraphStyle("SubtitleCustom", parent=styles["Normal"], fontSize=9, leading=12, textColor=colors.HexColor("#475467"))
    section = ParagraphStyle("SectionCustom", parent=styles["Heading2"], fontSize=12, leading=15, textColor=colors.HexColor("#0F172A"), spaceBefore=12, spaceAfter=6)
    body = ParagraphStyle("BodyCustom", parent=styles["Normal"], fontSize=9, leading=13, textColor=colors.HexColor("#1F2937"))
    mono = ParagraphStyle("MonoCustom", parent=styles["Code"], fontName="Courier", fontSize=8.5, leading=11, textColor=colors.HexColor("#111827"))

    story = []
    story.append(Paragraph("Sistema de Recetas Médicas", title))
    story.append(Paragraph("Reporte de transcripción OCR y validación farmacéutica", subtitle))
    story.append(Spacer(1, 0.25 * cm))

    def cell(value: str) -> Paragraph:
        return Paragraph(escape(str(value or "")), body)

    details = [
        [cell("Código"), cell(recipe.code), cell("Estado"), cell(recipe.status.capitalize())],
        [cell("Fecha de carga"), cell(_lima_datetime(recipe.created_at)), cell("Confianza OCR"), cell(f"{float(recipe.ocr_confidence or 0):.2f}%")],
        [cell("Paciente"), cell(recipe.patient_name or "No registrado"), cell("Edad"), cell(str(recipe.patient_age) if recipe.patient_age is not None else "No registrada")],
        [cell("Teléfono"), cell(getattr(recipe, "patient_phone", None) or "No registrado"), cell("Validador"), cell(recipe.validated_by.full_name if recipe.validated_by else "Pendiente")],
        [cell("Motivo"), cell(_service_reason_label(recipe.service_reason)), cell("Motor OCR"), cell(recipe.ocr_engine or "No definido")],
        [cell("Archivo"), cell(recipe.file_name), cell("Reporte"), cell(f"{recipe.code}.pdf")],
    ]
    table = Table(details, colWidths=[3.0 * cm, 6.0 * cm, 3.0 * cm, 6.0 * cm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#111827")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CBD5E1")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(table)

    try:
        image_bytes = read_file_bytes(recipe.file_path)
        image_buffer = BytesIO(image_bytes)
        iw, ih = ImageReader(BytesIO(image_bytes)).getSize()
        max_w = 17.5 * cm
        max_h = 8.5 * cm
        scale = min(max_w / iw, max_h / ih, 1.0)
        story.append(Paragraph("Imagen de la receta", section))
        story.append(PdfImage(image_buffer, width=iw * scale, height=ih * scale))
    except Exception:
        story.append(Paragraph("Imagen de la receta", section))
        story.append(Paragraph("No fue posible incorporar la imagen original en el reporte.", body))

    story.append(Paragraph("Texto detectado por OCR", section))
    story.append(Preformatted(escape(recipe.raw_text or "No se registró texto OCR."), mono))

    if recipe.normalized_text and recipe.normalized_text.strip() != (recipe.raw_text or "").strip():
        story.append(Paragraph("Sugerencia por diccionario farmacéutico", section))
        story.append(Preformatted(escape(recipe.normalized_text), mono))

    story.append(Paragraph("Observaciones de validación", section))
    story.append(Paragraph(escape(recipe.observations or "Sin observaciones registradas."), body))

    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph("Este reporte conserva el texto OCR original y las sugerencias como apoyo. La decisión final corresponde al químico farmacéutico validador.", subtitle))
    doc.build(story)
    buffer.seek(0)
    return buffer

def _change_status(recipe_id: int, status: str, action: str, payload: schemas.ValidationIn | None, current_user: User, db: Session):
    recipe = db.get(Recipe, recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Receta no encontrada.")
    recipe.status = status
    if payload and payload.observations is not None:
        recipe.observations = payload.observations
    recipe.validated_by_id = current_user.id
    recipe.validated_at = datetime.utcnow()
    recipe.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(recipe)
    add_activity(db, current_user.id, action, f"La receta {recipe.code} cambió a estado {status}.")
    return recipe_to_out(recipe)
