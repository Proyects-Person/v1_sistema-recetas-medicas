import os

from fastapi import FastAPI

from fastapi.middleware.cors import (
    CORSMiddleware,
)

from fastapi.responses import (
    FileResponse,
)

from sqlalchemy import (
    inspect,
    text,
)

from .auth import (
    get_password_hash,
)

from .database import (
    Base,
    UPLOAD_DIR,
    engine,
    SessionLocal,
)

from .models import (
    User,
)

from .routers import (
    auth,
    config,
    dashboard,
    recipes,
    users,
)


# ============================================================
# CORS
# ============================================================

def _cors_origins(
) -> list[str]:

    raw = os.getenv(
        "BACKEND_CORS_ORIGINS",
        os.getenv(
            "CORS_ORIGINS",
            (
                "http://localhost:5173,"
                "http://127.0.0.1:5173,"
                "http://localhost:8080,"
                "http://127.0.0.1:8080"
            ),
        ),
    )

    return [
        origin.strip()
        for origin in raw.split(",")
        if origin.strip()
    ]


# ============================================================
# APP
# ============================================================

app = FastAPI(
    title=(
        "Sistema de Recetas Médicas "
        "- OCR Cloud"
    ),
    version="2.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# STARTUP
# ============================================================

@app.on_event(
    "startup"
)
def startup():

    Base.metadata.create_all(
        bind=engine
    )

    ensure_recipe_dictionary_columns()

    ensure_user_contact_columns()

    seed_admin_user()


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():

    return {
        "app":
            "Sistema de Recetas Médicas",

        "status":
            "operativo",

        "ocr_engine":
            os.getenv(
                "OCR_ENGINE",
                "google_vision",
            ),

        "docs":
            "/docs",
    }


# ============================================================
# HEALTH
# ============================================================

@app.get(
    "/api/health"
)
def health():

    return {
        "status":
            "ok",

        "ocr_engine":
            os.getenv(
                "OCR_ENGINE",
                "google_vision",
            ),
    }


# ============================================================
# ARCHIVOS DE PERFIL
# ============================================================

@app.get(
    "/api/files/profiles/{filename}"
)
def profile_file(
    filename: str,
):

    path = (
        UPLOAD_DIR
        / "profiles"
        / filename
    )

    if (
        path.exists()
        and path.is_file()
    ):

        return FileResponse(
            path
        )

    return {
        "detail":
            "Archivo no encontrado"
    }


# ============================================================
# ROUTERS
# ============================================================

app.include_router(
    auth.router,
    prefix="/api",
)

app.include_router(
    users.router,
    prefix="/api",
)

app.include_router(
    recipes.router,
    prefix="/api",
)

app.include_router(
    dashboard.router,
    prefix="/api",
)

app.include_router(
    config.router,
    prefix="/api",
)


# ============================================================
# ADMIN POR DEFECTO
# ============================================================

def seed_admin_user():

    db = SessionLocal()

    try:

        admin_email = os.getenv(
            "ADMIN_EMAIL",
            "admin@recetas.pe",
        )

        admin_password = os.getenv(
            "ADMIN_PASSWORD",
            "admin123",
        )

        admin_name = os.getenv(
            "ADMIN_NAME",
            "Administrador del Sistema",
        )

        admin = (
            db.query(User)
            .filter(
                User.email
                == admin_email
            )
            .first()
        )

        if not admin:

            admin = User(

                email=
                    admin_email,

                full_name=
                    admin_name,

                role=
                    "admin",

                dni=
                    os.getenv(
                        "ADMIN_DNI",
                        "00000000",
                    ),

                phone=
                    os.getenv(
                        "ADMIN_PHONE",
                        "999999999",
                    ),

                password_hash=
                    get_password_hash(
                        admin_password
                    ),

                is_active=
                    True,
            )

            db.add(admin)

            db.commit()

        elif admin.role != "admin":

            admin.role = "admin"

            admin.is_active = True

            db.commit()

    finally:

        db.close()


# ============================================================
# MIGRACIÓN SIMPLE DE RECETAS
# ============================================================

def ensure_recipe_dictionary_columns():

    """
    create_all() crea tablas nuevas,
    pero NO modifica columnas de tablas existentes.

    Por eso agregamos manualmente las columnas nuevas
    cuando trabajamos con una base SQLite que ya existía.
    """

    inspector = inspect(
        engine
    )

    try:

        existing = {
            column["name"]
            for column
            in inspector.get_columns(
                "recipes"
            )
        }

    except Exception:

        return

    columns = {

        "normalized_text":
            "TEXT",

        "dictionary_suggestions":
            "TEXT",

        "recognized_terms":
            "TEXT",

        # NUEVA COLUMNA
        "structured_data":
            "TEXT",

        "patient_age":
            "INTEGER",

        "patient_phone":
            "VARCHAR(9)",

        "service_reason":
            "VARCHAR(80)",
    }

    with engine.begin() as connection:

        for (
            name,
            sql_type,
        ) in columns.items():

            if name not in existing:

                connection.execute(
                    text(
                        f"ALTER TABLE recipes "
                        f"ADD COLUMN {name} {sql_type}"
                    )
                )


# ============================================================
# MIGRACIÓN SIMPLE DE USUARIOS
# ============================================================

def ensure_user_contact_columns():

    inspector = inspect(
        engine
    )

    try:

        existing = {
            column["name"]
            for column
            in inspector.get_columns(
                "users"
            )
        }

    except Exception:

        return

    columns = {

        "dni":
            "VARCHAR(20)",

        "phone":
            "VARCHAR(30)",
    }

    with engine.begin() as connection:

        for (
            name,
            sql_type,
        ) in columns.items():

            if name not in existing:

                connection.execute(
                    text(
                        f"ALTER TABLE users "
                        f"ADD COLUMN {name} {sql_type}"
                    )
                )