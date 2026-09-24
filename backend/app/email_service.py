import html
import os
import smtplib

from email.message import EmailMessage
from urllib.parse import quote

from dotenv import load_dotenv


load_dotenv()


def send_password_reset_email(
    to_email: str,
    full_name: str,
    token: str
) -> None:

    smtp_host = os.getenv(
        "SMTP_HOST",
        ""
    ).strip()

    smtp_port = int(
        os.getenv(
            "SMTP_PORT",
            "587"
        )
    )

    smtp_user = os.getenv(
        "SMTP_USER",
        ""
    ).strip()

    smtp_password = os.getenv(
        "SMTP_PASSWORD",
        ""
    )

    smtp_from_email = os.getenv(
        "SMTP_FROM_EMAIL",
        smtp_user
    ).strip()

    smtp_from_name = os.getenv(
        "SMTP_FROM_NAME",
        "Sistema de Recetas Médicas"
    ).strip()

    smtp_use_tls = os.getenv(
        "SMTP_USE_TLS",
        "true"
    ).lower() == "true"

    frontend_url = os.getenv(
        "FRONTEND_URL",
        "http://localhost:5173"
    ).rstrip("/")

    if (
        not smtp_host
        or not smtp_user
        or not smtp_password
        or not smtp_from_email
    ):
        raise RuntimeError(
            "Falta configurar SMTP_HOST, SMTP_USER, "
            "SMTP_PASSWORD o SMTP_FROM_EMAIL."
        )

    reset_url = (
        f"{frontend_url}/reset-password"
        f"?token={quote(token)}"
    )

    safe_name = html.escape(full_name)

    message = EmailMessage()

    message["Subject"] = "Recuperación de contraseña"

    message["From"] = (
        f"{smtp_from_name} <{smtp_from_email}>"
    )

    message["To"] = to_email

    message.set_content(
        f"Hola {full_name},\n\n"
        "Recibimos una solicitud para restablecer tu contraseña.\n\n"
        "Abre este enlace para crear una nueva contraseña:\n"
        f"{reset_url}\n\n"
        "El enlace vence en 30 minutos y solo puede utilizarse una vez.\n\n"
        "Si no solicitaste este cambio, puedes ignorar este correo."
    )

    message.add_alternative(
        f"""
        <html>
            <body style="
                font-family: Arial, sans-serif;
                color: #172033;
                line-height: 1.6;
            ">
                <div style="
                    max-width: 600px;
                    margin: auto;
                    padding: 24px;
                ">

                    <h2 style="color: #0a74ff;">
                        Recuperación de contraseña
                    </h2>

                    <p>
                        Hola <strong>{safe_name}</strong>,
                    </p>

                    <p>
                        Recibimos una solicitud para
                        restablecer tu contraseña.
                    </p>

                    <p style="margin: 28px 0;">
                        <a
                            href="{reset_url}"
                            style="
                                background: #0a74ff;
                                color: white;
                                text-decoration: none;
                                padding: 12px 20px;
                                border-radius: 8px;
                                font-weight: bold;
                            "
                        >
                            Restablecer contraseña
                        </a>
                    </p>

                    <p>
                        El enlace vence en 30 minutos
                        y solo puede utilizarse una vez.
                    </p>

                    <p>
                        Si no solicitaste este cambio,
                        puedes ignorar este correo.
                    </p>

                </div>
            </body>
        </html>
        """,
        subtype="html"
    )

    if smtp_port == 465:

        with smtplib.SMTP_SSL(
            smtp_host,
            smtp_port,
            timeout=20
        ) as server:

            server.login(
                smtp_user,
                smtp_password
            )

            server.send_message(
                message
            )

        return

    with smtplib.SMTP(
        smtp_host,
        smtp_port,
        timeout=20
    ) as server:

        server.ehlo()

        if smtp_use_tls:

            server.starttls()

            server.ehlo()

        server.login(
            smtp_user,
            smtp_password
        )

        server.send_message(
            message
        )