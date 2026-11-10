import json
import logging
from datetime import datetime

from fastapi import APIRouter, Depends
from fastapi.encoders import jsonable_encoder
from fastapi.responses import StreamingResponse

from ..auth import get_current_user
from ..database import SessionLocal
from ..models import Activity, Recipe, User
from ..nlp.prescription_parser import parse_prescription
from ..ocr_dictionary import analyze_ocr_text
from ..ocr_pln import extract_text_from_bytes
from ..storage import read_file_bytes
from ..utils import recipe_to_out


router = APIRouter(
    prefix="/processing",
    tags=["Procesamiento"]
)

logger = logging.getLogger(__name__)


def event_line(stage, progress, message, **extra):
    payload = {
        "stage": stage,
        "progress": progress,
        "message": message,
        **extra,
    }

    return (
        json.dumps(
            jsonable_encoder(payload),
            ensure_ascii=False,
        )
        + "\n"
    )


def process_events(recipe_id: int, user_id: int):
    db = SessionLocal()
    original_status = None
    acquired = False
    completed = False

    try:
        recipe = db.get(Recipe, recipe_id)

        if recipe is None:
            yield event_line(
                "error",
                0,
                "Receta no encontrada.",
            )
            return

        original_status = recipe.status

        # Evitar dos procesamientos simultáneos de la misma receta.
        changed = (
            db.query(Recipe)
            .filter(
                Recipe.id == recipe_id,
                Recipe.status != "procesando",
            )
            .update(
                {"status": "procesando"},
                synchronize_session=False,
            )
        )

        db.commit()

        if changed != 1:
            yield event_line(
                "error",
                0,
                "La receta ya se encuentra en procesamiento.",
            )
            return

        acquired = True
        db.refresh(recipe)

        # ETAPA 1: IMAGEN
        yield event_line(
            "imagen",
            10,
            "Preparando imagen de la receta...",
        )

        image_bytes = read_file_bytes(recipe.file_path)

        # ETAPA 2: OCR
        yield event_line(
            "ocr",
            30,
            "Extrayendo texto mediante OCR...",
        )

        raw_text, confidence, engine_name = extract_text_from_bytes(
            image_bytes,
            recipe.file_name,
        )

        # ETAPA 3: PLN
        yield event_line(
            "pln",
            65,
            "Estructurando insumos y concentraciones mediante PLN...",
        )

        dictionary_result = analyze_ocr_text(
            raw_text,
            confidence,
        )

        parser_result = parse_prescription(
            raw_text,
            ocr_confidence=confidence,
        )

        structured_rows = (
            parser_result.get("structured_rows", []) or []
        )
        ner_entities = (
            parser_result.get("ner_entities", []) or []
        )

        dosage_parts = []

        if parser_result.get("frequency"):
            dosage_parts.append(parser_result["frequency"])

        if parser_result.get("duration"):
            dosage_parts.append(parser_result["duration"])

        recipe.raw_text = raw_text
        recipe.normalized_text = dictionary_result["normalized_text"]

        recipe.dictionary_suggestions = json.dumps(
            dictionary_result["dictionary_suggestions"],
            ensure_ascii=False,
        )

        recipe.recognized_terms = json.dumps(
            dictionary_result["recognized_terms"],
            ensure_ascii=False,
        )

        recipe.structured_ingredients = json.dumps(
            structured_rows,
            ensure_ascii=False,
        )

        recipe.ner_entities = json.dumps(
            ner_entities,
            ensure_ascii=False,
        )

        composition_lines = []

        for item in structured_rows:
            ingredient = str(
                item.get("ingredient") or ""
            ).strip()

            concentration = str(
                item.get("concentration") or ""
            ).strip()

            if not ingredient:
                continue

            line = ingredient

            if concentration:
                line += f" {concentration}"

            composition_lines.append(line.strip())

        recipe.composition = (
            "\n".join(composition_lines)
            if composition_lines
            else None
        )

        recipe.ocr_confidence = (
            round(confidence * 100, 2)
            if confidence <= 1
            else round(confidence, 2)
        )

        recipe.ocr_engine = engine_name

        recipe.low_confidence_fields = json.dumps(
            ["raw_text"] if confidence < 0.70 else [],
            ensure_ascii=False,
        )

        recipe.administration_route = parser_result.get(
            "administration_route"
        )

        recipe.dosage = (
            " | ".join(dosage_parts)
            if dosage_parts
            else None
        )

        yield event_line(
            "pln",
            90,
            "Guardando los resultados de la estructuración mediante PLN...",
        )

        recipe.status = "procesada"
        recipe.updated_at = datetime.utcnow()

        db.add(
            Activity(
                user_id=user_id,
                action="Pendiente de validación",
                description=(
                    f"La receta {recipe.code} quedó procesada "
                    "y pendiente de validación farmacéutica."
                ),
            )
        )

        db.commit()
        completed = True
        db.refresh(recipe)

        yield event_line(
            "finalizado",
            100,
            "Procesamiento finalizado. Redirigiendo a validación...",
            recipe=recipe_to_out(recipe),
        )

    except FileNotFoundError:
        yield event_line(
            "error",
            0,
            "No existe un archivo válido para procesar.",
        )

    except RuntimeError as exc:
        yield event_line(
            "error",
            0,
            str(exc),
        )

    except Exception:
        logger.exception(
            "Error al procesar la receta %s",
            recipe_id,
        )

        yield event_line(
            "error",
            0,
            "No se pudo completar el procesamiento de la receta.",
        )

    finally:
        try:
            db.rollback()

            # Recuperar el estado anterior si el proceso no terminó.
            if acquired and not completed:
                (
                    db.query(Recipe)
                    .filter(
                        Recipe.id == recipe_id,
                        Recipe.status == "procesando",
                    )
                    .update(
                        {
                            "status": original_status,
                            "updated_at": datetime.utcnow(),
                        },
                        synchronize_session=False,
                    )
                )

                db.commit()
        finally:
            db.close()


@router.post("/{recipe_id}/stream")
def stream_processing(
    recipe_id: int,
    current_user: User = Depends(get_current_user),
):
    return StreamingResponse(
        process_events(recipe_id, current_user.id),
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )