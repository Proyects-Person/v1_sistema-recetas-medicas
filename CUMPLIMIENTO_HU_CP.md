# Cumplimiento funcional

## Autenticación y roles

- Login funcional con token.
- Usuario administrador inicial configurable por variables de entorno.
- Rol `admin`: creación, edición de rol y activación/desactivación de usuarios.
- Rol `quimico_farmaceutico`: operación de recetas, procesamiento OCR y validación farmacéutica.
- Usuarios inactivos no pueden iniciar sesión.

## Recetas

- Carga de imágenes PNG, JPG, JPEG y WEBP.
- Validación de tipo y tamaño máximo.
- Almacenamiento local en desarrollo o Supabase Storage en producción.
- Procesamiento OCR real mediante Google Cloud Vision o EasyOCR opcional.
- Campo único: **Texto detectado por OCR**.
- No se autocompletan paciente, médico, diagnóstico, medicamento, dosis ni posología.
- Corrección manual del texto OCR.
- Estados: pendiente, procesando, procesada, aprobada, observada y cancelada.
- Trazabilidad de usuario cargador, validador y fechas.

## Historial y dashboard

- Historial con búsqueda por código, nombre de archivo y texto OCR.
- Filtro por fecha y estado.
- Descarga de resumen TXT.
- Dashboard con contadores reales desde base de datos.
- Actividad reciente del sistema.

## Despliegue

- SQLite para desarrollo local.
- PostgreSQL/Supabase para producción mediante `DATABASE_URL`.
- Supabase Storage para imágenes mediante `STORAGE_BACKEND=supabase`.
- Render Web Service para backend.
- Render Static Site para frontend.

## Ajustes adicionales solicitados

- El módulo de Historial mantiene separación alineada entre filas mediante tabla con layout fijo.
- Las acciones del Historial permiten visualizar, editar, descargar reporte PDF y eliminar recetas.
- El reporte PDF incluye imagen original, texto OCR, sugerencia por diccionario, estado, datos del paciente y validador.
- El módulo Subir Receta registra datos administrativos del paciente y motivo de evaluación.
- La pantalla Procesamiento fue ajustada visualmente para evitar que el texto quede junto al botón.
- El Dashboard muestra como pendientes las recetas procesadas por OCR pero aún no validadas.
- La actividad del día se limita a eventos relevantes del flujo farmacéutico.
- Se retiró la campana de la barra superior.
- El formulario de login queda vacío por defecto.
- El panel visual del login fue reemplazado por una vista estilo laboratorio/farmacia magistral.
