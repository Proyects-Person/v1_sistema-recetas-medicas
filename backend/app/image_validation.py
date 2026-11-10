import os
import warnings
from io import BytesIO
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
)
from PIL import Image

from .auth import get_current_user
from .models import User


router = APIRouter(
    prefix="/images",
    tags=["Validación de imágenes"],
)

INVALID_IMAGE_MESSAGE = (
    "No se puede adjuntar el archivo porque está dañado "
    "o no corresponde a una imagen válida. "
    "Selecciona otra imagen."
)

INVALID_FORMAT_MESSAGE = (
    "Archivo no válido. Solo se permiten imágenes "
    "PNG, JPG, JPEG o WEBP."
)

ALLOWED_FORMATS = {
    ".png": "PNG",
    ".jpg": "JPEG",
    ".jpeg": "JPEG",
    ".webp": "WEBP",
}

MAX_UPLOAD_BYTES = (
    int(os.getenv("MAX_UPLOAD_MB", "10"))
    * 1024
    * 1024
)


def validate_image_content(
    filename: str,
    content: bytes,
) -> dict:
    extension = Path(filename or "").suffix.lower()
    expected_format = ALLOWED_FORMATS.get(extension)

    if expected_format is None:
        raise HTTPException(
            status_code=400,
            detail=INVALID_FORMAT_MESSAGE,
        )

    if not content:
        raise HTTPException(
            status_code=400,
            detail=INVALID_IMAGE_MESSAGE,
        )

    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=(
                "El archivo supera el límite permitido de "
                f"{MAX_UPLOAD_BYTES // (1024 * 1024)}MB."
            ),
        )

    try:
        with warnings.catch_warnings():
            warnings.simplefilter(
                "error",
                Image.DecompressionBombWarning,
            )

            # Comprobar formato real e integridad del archivo.
            with Image.open(BytesIO(content)) as image:
                if image.format != expected_format:
                    raise ValueError(
                        "El contenido no coincide con la extensión."
                    )

                image.verify()

            # Abrir nuevamente y decodificar los píxeles.
            # verify() por sí solo no detecta todos los truncamientos.
            with Image.open(BytesIO(content)) as image:
                width, height = image.size

                if width <= 0 or height <= 0:
                    raise ValueError(
                        "Las dimensiones de la imagen no son válidas."
                    )

                frame_count = getattr(image, "n_frames", 1)

                for frame_index in range(frame_count):
                    image.seek(frame_index)
                    image.load()

    except (
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ) as exc:
        raise HTTPException(
            status_code=400,
            detail=(
                "No se puede adjuntar el archivo porque "
                "las dimensiones de la imagen son demasiado grandes. "
                "Selecciona una imagen de menor resolución."
            ),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=INVALID_IMAGE_MESSAGE,
        ) from exc

    return {
        "valid": True,
        "format": expected_format,
        "width": width,
        "height": height,
    }


@router.post("/validate")
def validate_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    try:
        # Leer como máximo el límite permitido más un byte.
        content = file.file.read(MAX_UPLOAD_BYTES + 1)

        return validate_image_content(
            file.filename or "",
            content,
        )
    finally:
        file.file.close()