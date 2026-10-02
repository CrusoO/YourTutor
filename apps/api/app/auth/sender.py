from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from typing import Protocol

from app.config import settings

logger = logging.getLogger("yourtutor.otp")


class OtpSender(Protocol):
    def send(self, destination: str, code: str) -> None: ...


class EmailOtpSender:
    """Email OTP. Logs the code to the console when SMTP is unset."""

    def send(self, destination: str, code: str) -> None:
        if not settings.smtp_host:
            logger.info("OTP for %s: %s", destination, code)
            return
        message = EmailMessage()
        message["From"] = settings.otp_from_email
        message["To"] = destination
        message["Subject"] = "YourTutor sign-in code"
        message.set_content(f"Your sign-in code is {code}. It expires in 10 minutes.")
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
            if settings.smtp_user:
                smtp.starttls()
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(message)


class MemoryOtpSender:
    """Test double that records the last code per destination."""

    def __init__(self) -> None:
        self.inbox: dict[str, str] = {}

    def send(self, destination: str, code: str) -> None:
        self.inbox[destination] = code
        logger.info("OTP for %s: %s", destination, code)


_sender: OtpSender = EmailOtpSender()


def get_otp_sender() -> OtpSender:
    return _sender


def set_otp_sender(sender: OtpSender) -> None:
    global _sender
    _sender = sender
