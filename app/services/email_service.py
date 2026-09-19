import smtplib
from email.message import EmailMessage

from app.core.config import settings


class EmailService:
    @staticmethod
    def send_password_reset_email(
        recipient: str,
        token: str,
    ) -> None:
        if not settings.SMTP_HOST or not settings.SMTP_FROM_EMAIL:
            raise RuntimeError(
                "Email delivery is not configured."
            )

        reset_url = (
            f"{settings.FRONTEND_URL}/reset-password"
            f"?token={token}"
        )
        message = EmailMessage()
        message["Subject"] = "Reset your Ultimate Kits password"
        message["From"] = settings.SMTP_FROM_EMAIL
        message["To"] = recipient
        message.set_content(
            "Use the following link to reset your password. "
            f"The link expires in "
            f"{settings.PASSWORD_RESET_EXPIRE_MINUTES} minutes.\n\n"
            f"{reset_url}"
        )

        with smtplib.SMTP(
            settings.SMTP_HOST,
            settings.SMTP_PORT,
            timeout=30,
        ) as smtp:
            if settings.SMTP_USE_TLS:
                smtp.starttls()

            if settings.SMTP_USERNAME:
                if settings.SMTP_PASSWORD is None:
                    raise RuntimeError(
                        "SMTP_PASSWORD is required when "
                        "SMTP_USERNAME is configured."
                    )

                smtp.login(
                    settings.SMTP_USERNAME,
                    settings.SMTP_PASSWORD,
                )

            smtp.send_message(message)
