import json
import os
import tempfile
from pathlib import Path
from typing import Any

ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


def validate_image_file(filename: str, content_type: str | None = None) -> None:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError("Formato no válido. Solo se permiten imágenes PNG, JPG, JPEG o WEBP.")
    if content_type and not content_type.startswith("image/"):
        raise ValueError("El archivo cargado no corresponde a una imagen.")


def _bbox_xy(result_item: Any) -> tuple[float, float]:
    try:
        bbox = result_item[0]
        xs = [float(point[0]) for point in bbox]
        ys = [float(point[1]) for point in bbox]
        return min(ys), min(xs)
    except Exception:
        return 0.0, 0.0


def _google_credentials_from_env():
    """Crea credenciales de Google Cloud Vision desde variable JSON o ruta estándar."""
    try:
        from google.oauth2 import service_account  # type: ignore
    except Exception as exc:
        raise RuntimeError(
            "Falta instalar Google Cloud Vision. Ejecuta: pip install -r requirements.txt"
        ) from exc

    raw_json = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON", "").strip()
    if raw_json:
        try:
            info = json.loads(raw_json)
        except json.JSONDecodeError:
            try:
                info = json.loads(raw_json.replace("\\n", "\n"))
            except json.JSONDecodeError as exc:
                raise RuntimeError(
                    "GOOGLE_APPLICATION_CREDENTIALS_JSON no contiene un JSON válido. Copia el JSON completo de la cuenta de servicio."
                ) from exc
        return service_account.Credentials.from_service_account_info(info)

    # Permite usar GOOGLE_APPLICATION_CREDENTIALS con una ruta local al JSON durante desarrollo.
    return None


def _average_google_confidence(annotation: Any) -> float:
    confidences: list[float] = []
    try:
        for page in annotation.pages:
            for block in page.blocks:
                for paragraph in block.paragraphs:
                    for word in paragraph.words:
                        value = float(getattr(word, "confidence", 0.0) or 0.0)
                        if value > 0:
                            confidences.append(value)
    except Exception:
        return 0.0
    return sum(confidences) / len(confidences) if confidences else 0.0


def _ocr_with_google_vision(image_bytes: bytes) -> tuple[str, float]:
    try:
        from google.cloud import vision  # type: ignore
    except Exception as exc:
        raise RuntimeError(
            "Falta instalar Google Cloud Vision. Ejecuta: pip install -r requirements.txt"
        ) from exc

    credentials = _google_credentials_from_env()
    try:
        client = vision.ImageAnnotatorClient(credentials=credentials) if credentials else vision.ImageAnnotatorClient()
    except Exception as exc:
        raise RuntimeError(
            "No se pudo crear el cliente de Google Vision. Verifica GOOGLE_APPLICATION_CREDENTIALS_JSON o GOOGLE_APPLICATION_CREDENTIALS."
        ) from exc

    image = vision.Image(content=image_bytes)
    context = vision.ImageContext(language_hints=["es"])
    response = client.document_text_detection(image=image, image_context=context)

    if response.error and response.error.message:
        raise RuntimeError(f"Google Vision rechazó la imagen: {response.error.message}")

    annotation = response.full_text_annotation
    raw_text = (annotation.text or "").strip() if annotation else ""
    confidence = _average_google_confidence(annotation) if annotation else 0.0
    return raw_text, confidence


def _ocr_with_easyocr_from_bytes(image_bytes: bytes, suffix: str = ".jpg") -> tuple[str, float]:
    """OCR local opcional. No se usa como fallback automático para no ocultar errores de configuración."""
    try:
        import easyocr  # type: ignore
    except Exception as exc:
        raise RuntimeError(
            "EasyOCR no está instalado. Instala el OCR local con: pip install -r requirements-ocr.txt"
        ) from exc

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(image_bytes)
        tmp_path = tmp.name

    try:
        reader = easyocr.Reader(["es", "en"], gpu=False)
        result = reader.readtext(tmp_path, detail=1, paragraph=False)
        if not result:
            return "", 0.0

        ordered = sorted(result, key=_bbox_xy)
        lines: list[str] = []
        confidences: list[float] = []
        for item in ordered:
            if len(item) < 2:
                continue
            text = str(item[1]).strip()
            if not text:
                continue
            lines.append(text)
            if len(item) >= 3:
                try:
                    confidences.append(float(item[2]))
                except Exception:
                    pass
        raw_text = "\n".join(lines).strip()
        confidence = sum(confidences) / len(confidences) if confidences else 0.0
        return raw_text, confidence
    finally:
        try:
            Path(tmp_path).unlink(missing_ok=True)
        except Exception:
            pass


def extract_text_from_bytes(image_bytes: bytes, filename: str = "receta.jpg") -> tuple[str, float, str]:
    """
    Transcribe únicamente lo detectado visualmente por OCR.

    Motores disponibles:
    - google_vision: recomendado para recetas manuscritas y despliegue.
    - easyocr: opción local, solo si se instala requirements-ocr.txt.

    No existe fallback demo ni texto inventado.
    """
    engine = os.getenv("OCR_ENGINE", "google_vision").strip().lower()
    suffix = Path(filename).suffix.lower() or ".jpg"

    if engine == "google_vision":
        raw_text, confidence = _ocr_with_google_vision(image_bytes)
        used_engine = "google_vision"
    elif engine == "easyocr":
        raw_text, confidence = _ocr_with_easyocr_from_bytes(image_bytes, suffix=suffix)
        used_engine = "easyocr"
    else:
        raise RuntimeError("OCR_ENGINE no válido. Usa 'google_vision' o 'easyocr'.")

    if not raw_text.strip():
        raise RuntimeError("No se detectó texto en la imagen. Sube una receta más nítida, iluminada y enfocada.")
    return raw_text.strip(), confidence, used_engine


def extract_text(path: str) -> tuple[str, float]:
    image_bytes = Path(path).read_bytes()
    raw_text, confidence, _ = extract_text_from_bytes(image_bytes, Path(path).name)
    return raw_text, confidence


def structure_prescription(raw_text: str, confidence: float) -> dict[str, Any]:
    return {
        "patient_name": None,
        "doctor_name": None,
        "diagnosis": None,
        "composition": None,
        "administration_route": None,
        "dosage": None,
        "observations": None,
        "raw_text": raw_text.strip(),
        "ocr_confidence": round(confidence * 100, 2),
        "low_confidence_fields": ["raw_text"] if confidence < 0.70 else [],
    }
