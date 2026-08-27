# Sistema de Recetas Médicas - OCR Cloud

Sistema web funcional para cargar recetas médicas manuscritas, transcribir el contenido visible mediante OCR real y permitir validación farmacéutica. La versión actual está preparada para trabajar localmente con SQLite y desplegarse con Render + Supabase + Google Cloud Vision.

## Roles

- **Administrador**: inicia sesión, crea usuarios, cambia roles y activa/desactiva cuentas.
- **Químico farmacéutico**: sube recetas, procesa OCR, revisa la transcripción, corrige el texto, aprueba, observa o rechaza recetas.

El usuario administrador inicial se crea automáticamente al iniciar el backend:

```txt
admin@recetas.pe
admin123
```

Cambia esa contraseña en producción usando `ADMIN_PASSWORD`.

## Qué hace el OCR

El sistema muestra un único campo principal: **Texto detectado por OCR**.

No inventa paciente, médico, diagnóstico, medicamento, dosis ni posología. El texto mostrado proviene directamente del motor configurado en `OCR_ENGINE`.

Motores disponibles:

- `google_vision`: recomendado para recetas manuscritas y despliegue.
- `easyocr`: opcional para pruebas locales, requiere `requirements-ocr.txt`.

## Ejecución local en Visual Studio Code

### Backend

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env -Force
python -m uvicorn app.main:app --reload --port 8000
```

Backend:

```txt
http://localhost:8000/docs
```

### Frontend

En otra terminal:

```powershell
cd frontend
npm install
npm run dev
```

Frontend:

```txt
http://localhost:5173
```

## Configurar Google Vision localmente

En `backend/.env`, deja:

```env
OCR_ENGINE=google_vision
GOOGLE_APPLICATION_CREDENTIALS=D:/recetas/google-vision-key.json
```

También puedes usar:

```env
GOOGLE_APPLICATION_CREDENTIALS_JSON={"type":"service_account",...}
```

## Despliegue recomendado

- Backend: Render Web Service.
- Frontend: Render Static Site.
- Base de datos: Supabase PostgreSQL.
- Imágenes: Supabase Storage.
- OCR: Google Cloud Vision `DOCUMENT_TEXT_DETECTION`.

Revisa `DEPLOYMENT.md` para los pasos completos.

## Mejora OCR con diccionario farmacéutico

Esta versión agrega un postprocesamiento de apoyo después del OCR cloud. El flujo queda así:

1. Google Vision realiza la transcripción real de la imagen.
2. El sistema conserva el campo `Texto detectado por OCR` sin inventar información.
3. Un diccionario farmacéutico local compara el texto OCR con términos frecuentes de formulación magistral dermatológica.
4. Se genera un `Texto sugerido por diccionario` y una lista de correcciones candidatas.
5. El químico farmacéutico decide si usa o no la sugerencia.

El diccionario está en:

```txt
backend/app/dictionaries/pharmaceutical_terms.json
```

El código de postprocesamiento está en:

```txt
backend/app/ocr_dictionary.py
```

Ejemplo de mejora esperada:

```txt
OCR crudo: Alcohol / Sonicado / 5%
Sugerencia: Alcohol boricado 5%
```

Importante: el diccionario no reemplaza el criterio profesional ni cambia automáticamente una receta aprobada. Solo muestra sugerencias para acelerar la revisión manual.

## Mejoras funcionales incorporadas

- Login sin credenciales precargadas.
- Pantalla de inicio de sesión con imagen estilo laboratorio/farmacia magistral.
- Registro de datos del paciente al subir receta: nombre, edad y motivo de evaluación.
- Cola de recetas pendientes de validación cuando el estado es `procesada`.
- Panel principal con tarjeta clicable de pendientes que deriva a Validación.
- Actividad del día filtrada solo a eventos de validación, corrección, observación, aprobación, rechazo y eliminación.
- Historial con acciones para visualizar, editar, descargar PDF y borrar receta.
- Descarga de reporte PDF con imagen de la receta, texto OCR, sugerencia farmacéutica, observaciones y validador.
- Diccionario farmacéutico ampliado con términos dermatológicos, magistrales, abreviaturas y variantes frecuentes de OCR.
