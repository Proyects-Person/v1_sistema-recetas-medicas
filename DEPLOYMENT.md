# Despliegue gratis con Render, Supabase y Google Cloud Vision

## 1. Crear proyecto en Supabase

1. Entra a Supabase.
2. Crea un proyecto nuevo.
3. Guarda la contraseña de la base de datos.
4. Ve a **Project Settings > Database**.
5. Copia la cadena de conexión tipo URI del pooler.
6. Usa este formato en Render:

```env
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:6543/postgres?sslmode=require
```

## 2. Crear bucket en Supabase Storage

1. Entra a **Storage**.
2. Crea un bucket llamado:

```txt
recetas
```

3. Puede ser privado.
4. Ve a **Project Settings > API**.
5. Copia:

```txt
Project URL
service_role key
```

Usarás ambos en Render:

```env
STORAGE_BACKEND=supabase
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=tu_service_role_key
SUPABASE_STORAGE_BUCKET=recetas
```

## 3. Configurar Google Cloud Vision

1. Crea un proyecto en Google Cloud.
2. Activa **Cloud Vision API**.
3. Ve a **IAM & Admin > Service Accounts**.
4. Crea una cuenta de servicio.
5. Dale permisos para usar Vision API.
6. Crea una key JSON.
7. Copia el JSON completo.
8. En Render pega ese JSON como variable:

```env
GOOGLE_APPLICATION_CREDENTIALS_JSON={"type":"service_account",...}
```

No subas el archivo JSON al repositorio.

## 4. Backend en Render

Crea un **Web Service** conectado a GitHub.

Configuración:

```txt
Root Directory: backend
Build Command: pip install -r requirements.txt
Start Command: python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Variables de entorno:

```env
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:6543/postgres?sslmode=require
SECRET_KEY=clave_larga_segura
ACCESS_TOKEN_EXPIRE_MINUTES=1440
BACKEND_CORS_ORIGINS=https://TU-FRONTEND.onrender.com
MAX_UPLOAD_MB=10
ADMIN_EMAIL=admin@recetas.pe
ADMIN_PASSWORD=contraseña_segura
ADMIN_NAME=Administrador del Sistema
OCR_ENGINE=google_vision
GOOGLE_APPLICATION_CREDENTIALS_JSON={"type":"service_account",...}
STORAGE_BACKEND=supabase
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=tu_service_role_key
SUPABASE_STORAGE_BUCKET=recetas
```

## 5. Frontend en Render

Crea un **Static Site** conectado al mismo repositorio.

Configuración:

```txt
Root Directory: frontend
Build Command: npm install && npm run build
Publish Directory: dist
```

Variable de entorno:

```env
VITE_API_BASE_URL=https://TU-BACKEND.onrender.com/api
```

## 6. Verificación final

1. Abre el frontend.
2. Inicia sesión con el admin.
3. Crea un usuario químico farmacéutico.
4. Cierra sesión e ingresa con ese usuario.
5. Sube una receta.
6. Procesa OCR.
7. Verifica que aparece únicamente el campo **Texto detectado por OCR**.
8. Corrige manualmente si es necesario.
9. Aprueba, observa o rechaza.
10. Revisa el historial y el dashboard.

## Nota importante

Render Free puede dormir el backend tras inactividad. Si la primera carga demora, espera a que el servicio despierte.

## Nota sobre el diccionario farmacéutico

El diccionario se despliega junto con el backend y no requiere servicios adicionales. En producción se seguirá usando `OCR_ENGINE=google_vision`; el diccionario solo actúa como capa de postprocesamiento para sugerencias.

Si ya tienes una base de datos creada, el backend ejecuta una migración ligera al iniciar para agregar estas columnas si no existen:

- `normalized_text`
- `dictionary_suggestions`
- `recognized_terms`

