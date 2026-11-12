"""Tell someone something at a contact (an email or a phone): used for the guardian approval link.

Sign-in codes keep their own senders (sender.py). Nothing here logs a message body, an address or
a number: a body holds a link that lets someone act for a child.
"""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from typing import Protocol

from app.auth.sms import SmsUnavailable, get_sms_provider
from app.config import settings

logger = logging.getLogger("yourtutor.notify")


class NotifyUnavailable(Exception):  # noqa: N818
    """The message could not be sent (no mail server or SMS vendor, or it failed)."""


class Notifier(Protocol):
    def send(self, kind: str, contact: str, subject: str, text: str) -> None: ...


class DefaultNotifier:
    def send(self, kind: str, contact: str, subject: str, text: str) -> None:
        if kind == "phone":
            try:
                get_sms_provider().send_sms(contact, text)
            except SmsUnavailable:
                raise NotifyUnavailable("sms") from None
            return
        if not settings.smtp_host:
            logger.warning("Notice email not sent: SMTP_HOST is empty")
            raise NotifyUnavailable("smtp")
        message = EmailMessage()
        message["From"] = settings.otp_from_email
        message["To"] = contact
        message["Subject"] = subject
        message.set_content(text)
        try:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
                if settings.smtp_user:
                    smtp.starttls()
                    smtp.login(settings.smtp_user, settings.smtp_password)
                smtp.send_message(message)
        except (OSError, smtplib.SMTPException) as error:
            logger.warning("Notice email not sent: %s", type(error).__name__)
            raise NotifyUnavailable("smtp") from None


class MemoryNotifier:
    """Test double: the messages sent, per contact."""

    def __init__(self) -> None:
        self.sent: dict[str, list[str]] = {}

    def send(self, kind: str, contact: str, subject: str, text: str) -> None:
        self.sent.setdefault(contact, []).append(text)

    def last(self, contact: str) -> str:
        return self.sent[contact][-1]


_notifier: Notifier = DefaultNotifier()


def get_notifier() -> Notifier:
    return _notifier


def set_notifier(notifier: Notifier) -> None:
    global _notifier
    _notifier = notifier
