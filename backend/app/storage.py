import os
from pathlib import Path
from uuid import uuid4

import requests
from fastapi import HTTPException
from fastapi.responses import Response, FileResponse

from .database import UPLOAD_DIR


def storage_backend() -> str:
    return os.getenv("STORAGE_BACKEND", "local").strip().lower()


def _supabase_settings() -> tuple[str, str, str]:
    url = os.getenv("SUPABASE_URL", "").rstrip("/")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    bucket = os.getenv("SUPABASE_STORAGE_BUCKET", "recetas")
    if not url or not key:
        raise RuntimeError("Faltan SUPABASE_URL o SUPABASE_SERVICE_ROLE_KEY para usar Supabase Storage.")
    return url, key, bucket


def _headers(content_type: str | None = None) -> dict[str, str]:
    _, key, _ = _supabase_settings()
    headers = {"Authorization": f"Bearer {key}", "apikey": key}
    if content_type:
        headers["Content-Type"] = content_type
    return headers


def save_uploaded_file(original_filename: str, content: bytes, content_type: str | None = None, folder: str = "recipes") -> str:
    ext = Path(original_filename or "receta.jpg").suffix.lower() or ".jpg"
    safe_name = f"{folder}/{uuid4().hex}{ext}"

    if storage_backend() == "supabase":
        url, _, bucket = _supabase_settings()
        endpoint = f"{url}/storage/v1/object/{bucket}/{safe_name}"
        response = requests.post(
            endpoint,
            headers={**_headers(content_type or "application/octet-stream"), "x-upsert": "true"},
            data=content,
            timeout=60,
        )
        if response.status_code >= 400:
            raise RuntimeError(f"No se pudo subir el archivo a Supabase Storage: {response.text}")
        return f"supabase:{safe_name}"

    local_path = UPLOAD_DIR / safe_name
    local_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_bytes(content)
    return f"local:{local_path}"


def read_file_bytes(file_ref: str) -> bytes:
    if file_ref.startswith("supabase:"):
        path = file_ref.split(":", 1)[1]
        url, _, bucket = _supabase_settings()
        endpoint = f"{url}/storage/v1/object/{bucket}/{path}"
        response = requests.get(endpoint, headers=_headers(), timeout=60)
        if response.status_code >= 400:
            raise FileNotFoundError("Archivo no encontrado en Supabase Storage.")
        return response.content

    path_text = file_ref.split(":", 1)[1] if file_ref.startswith("local:") else file_ref
    path = Path(path_text)
    if not path.exists() or not path.is_file():
        raise FileNotFoundError("Archivo local no encontrado.")
    return path.read_bytes()


def delete_file(file_ref: str) -> None:
    if file_ref.startswith("supabase:"):
        path = file_ref.split(":", 1)[1]
        url, _, bucket = _supabase_settings()
        endpoint = f"{url}/storage/v1/object/{bucket}/{path}"
        requests.delete(endpoint, headers=_headers(), timeout=60)
        return

    path_text = file_ref.split(":", 1)[1] if file_ref.startswith("local:") else file_ref
    try:
        Path(path_text).unlink(missing_ok=True)
    except Exception:
        pass


def file_response(file_ref: str, filename: str, media_type: str | None = None):
    if file_ref.startswith("supabase:"):
        try:
            content = read_file_bytes(file_ref)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Archivo no encontrado.") from exc
        return Response(
            content=content,
            media_type=media_type or "application/octet-stream",
            headers={"Content-Disposition": f'inline; filename="{filename}"'},
        )

    path_text = file_ref.split(":", 1)[1] if file_ref.startswith("local:") else file_ref
    path = Path(path_text)
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="Archivo no encontrado.")
    return FileResponse(path, filename=filename, media_type=media_type)
