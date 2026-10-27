"""E-mails. User-facing texts live in templates (French at launch), never in business code."""

import logging
import smtplib
from email.message import EmailMessage

from app.config import get_settings

logger = logging.getLogger("orienta.mail")

TEMPLATES_FR = {
    "verification_code": (
        "Votre code de vérification Orienta",
        "Bonjour {name},\n\nVotre code de vérification est : {code}\n\n"
        "Il est valable {minutes} minutes. Si vous n'êtes pas à l'origine de cette demande, ignorez ce message.\n\n"
        "L'équipe Orienta",
    ),
    "invitation": (
        "Votre invitation sur Orienta",
        "Bonjour {name},\n\nUn administrateur vous a créé un compte {role_label} sur Orienta.\n"
        "Votre code d'activation est : {code}\n\n"
        "Activez votre compte ici : {link}\nLe code est valable {minutes} minutes.\n\nL'équipe Orienta",
    ),
    "already_registered": (
        "Vous avez déjà un compte Orienta",
        "Bonjour,\n\nQuelqu'un a essayé de créer un compte Orienta avec cette adresse, qui possède déjà un compte.\n"
        "Si c'était vous, connectez-vous simplement : {link}\n\nL'équipe Orienta",
    ),
}

ROLE_LABELS_FR = {"HEALTH_AGENT": "d'agent de santé", "ADMIN": "d'administrateur"}


def send_template(to: str, template: str, **params: object) -> None:
    """Send an e-mail. Called as a FastAPI background task, in the api process (never through a queue)."""
    settings = get_settings()
    subject, body = TEMPLATES_FR[template]
    message = EmailMessage()
    message["From"] = settings.mail_from
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body.format(**params))
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
            if settings.smtp_user:
                smtp.starttls()
                smtp.login(settings.smtp_user, settings.smtp_password or "")
            smtp.send_message(message)
    except OSError:
        # The address and the code are never logged.
        logger.exception("mail_send_failed template=%s", template)
