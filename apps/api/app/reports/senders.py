"""Where a report goes. Email is the only channel built; the profile lists what is allowed."""

from __future__ import annotations

import logging
import smtplib
from dataclasses import dataclass, field
from email.message import EmailMessage
from typing import Protocol

from app.config import settings

logger = logging.getLogger("yourtutor.reports")


class ReportSender(Protocol):
    channel: str

    def send(self, destination: str, subject: str, body: str) -> None: ...


class EmailReportSender:
    channel = "email"

    def send(self, destination: str, subject: str, body: str) -> None:
        if not settings.smtp_host:
            logger.info("Report to %s: %s", destination, subject)
            return
        message = EmailMessage()
        message["From"] = settings.otp_from_email
        message["To"] = destination
        message["Subject"] = subject
        message.set_content(body)
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
            if settings.smtp_user:
                smtp.starttls()
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(message)


@dataclass
class MemoryReportSender:
    """Test double: keeps what would have been sent."""

    channel: str = "email"
    sent: list[tuple[str, str, str]] = field(default_factory=list)

    def send(self, destination: str, subject: str, body: str) -> None:
        self.sent.append((destination, subject, body))
