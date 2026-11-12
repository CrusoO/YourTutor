from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from typing import Protocol

from app.config import settings

logger = logging.getLogger("yourtutor.otp")


class EmailUnavailable(Exception):  # noqa: N818
    """The code could not be sent (no SMTP configured, or the mail server failed)."""


class OtpSender(Protocol):
    def send(self, destination: str, code: str) -> None: ...


class EmailOtpSender:
    """Email OTP. Never logs the code; with no SMTP host it raises EmailUnavailable."""

    def send(self, destination: str, code: str) -> None:
        if not settings.smtp_host:
            logger.warning("OTP email not sent: SMTP_HOST is empty")
            raise EmailUnavailable("SMTP_HOST is empty")
        message = EmailMessage()
        message["From"] = settings.otp_from_email
        message["To"] = destination
        message["Subject"] = "YourTutor sign-in code"
        message.set_content(f"Your sign-in code is {code}. It expires in 10 minutes.")
        try:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
                if settings.smtp_user:
                    smtp.starttls()
                    smtp.login(settings.smtp_user, settings.smtp_password)
                smtp.send_message(message)
        except (OSError, smtplib.SMTPException) as error:
            logger.warning("OTP email not sent: %s", type(error).__name__)
            raise EmailUnavailable(type(error).__name__) from None


class SmsOtpSender:
    """Phone OTP through the configured SMS provider (app/auth/sms.py). `destination` is E.164."""

    def send(self, destination: str, code: str) -> None:
        from app.auth.sms import get_sms_provider

        get_sms_provider().send_sms(
            destination, f"Your YourTutor sign-in code is {code}. It expires in 10 minutes."
        )


class MemoryOtpSender:
    """Test double that records the last code per destination."""

    def __init__(self) -> None:
        self.inbox: dict[str, str] = {}

    def send(self, destination: str, code: str) -> None:
        self.inbox[destination] = code


_sender: OtpSender = EmailOtpSender()


def get_otp_sender() -> OtpSender:
    return _sender


def get_sms_otp_sender() -> OtpSender:
    return SmsOtpSender()


def set_otp_sender(sender: OtpSender) -> None:
    global _sender
    _sender = sender
