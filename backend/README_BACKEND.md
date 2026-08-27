# Backend FastAPI

## Local

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env -Force
python -m uvicorn app.main:app --reload --port 8000
```

## OCR

`OCR_ENGINE=google_vision` usa Google Cloud Vision. Requiere una de estas variables:

```env
GOOGLE_APPLICATION_CREDENTIALS=D:/ruta/key.json
```

ó

```env
GOOGLE_APPLICATION_CREDENTIALS_JSON={"type":"service_account",...}
```

No existe fallback demo. Si faltan credenciales o falla Google Vision, el backend devuelve un error claro.

## Roles

- `admin`: administra usuarios.
- `quimico_farmaceutico`: opera recetas y validación farmacéutica.
