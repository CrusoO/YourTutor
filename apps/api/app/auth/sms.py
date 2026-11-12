"""Sending text messages: one small interface, and no real vendor until the owner chooses one.

`SMS_PROVIDER` picks the implementation:
  console  (default) sends nothing; logs only that a message was NOT sent, with the last 2 digits.
  fake     keeps messages in memory (tests and local checks); sends nothing.
  vendor   the place for the real SMS vendor. It is deliberately a stub that refuses to send until
           the owner supplies a vendor and an adapter is written (see docs/OPERATOR.md).

No provider here ever logs a message body: bodies hold sign-in codes and approval links.
"""

from __future__ import annotations

import logging
from typing import Protocol

from app.config import settings

logger = logging.getLogger("yourtutor.sms")


class SmsUnavailable(Exception):  # noqa: N818
    """The message could not be sent (no vendor set, or the vendor failed)."""


class SmsProvider(Protocol):
    def send_sms(self, to: str, body: str) -> None: ...


def _tail(to: str) -> str:
    return "***" + to[-2:] if len(to) >= 2 else "***"


class ConsoleSmsProvider:
    """Sends nothing. A deployment on this provider cannot deliver codes: it says so."""

    def send_sms(self, to: str, body: str) -> None:
        logger.warning(
            "SMS not sent (SMS_PROVIDER=console) to %s, %d characters", _tail(to), len(body)
        )
        raise SmsUnavailable("SMS_PROVIDER is console: no SMS vendor is configured")


class FakeSmsProvider:
    """Records messages in memory; for tests and for looking at the flow without a vendor."""

    def __init__(self) -> None:
        self.outbox: list[tuple[str, str]] = []

    def send_sms(self, to: str, body: str) -> None:
        self.outbox.append((to, body))

    def last_to(self, to: str) -> str | None:
        for destination, body in reversed(self.outbox):
            if destination == to:
                return body
        return None


class VendorSmsProvider:
    """Placeholder for the real vendor. Replace the body with the vendor's client; keep the rule
    that nothing is logged but the destination's last digits and a failure's type."""

    def send_sms(self, to: str, body: str) -> None:
        logger.warning(
            "SMS not sent (SMS_PROVIDER=vendor but no adapter is written) to %s", _tail(to)
        )
        raise SmsUnavailable("SMS vendor adapter not written: owner supplies the vendor")


_fake = FakeSmsProvider()
_override: SmsProvider | None = None


def fake_provider() -> FakeSmsProvider:
    return _fake


def get_sms_provider() -> SmsProvider:
    if _override is not None:
        return _override
    name = settings.sms_provider.strip().lower()
    if name == "fake":
        return _fake
    if name == "vendor":
        return VendorSmsProvider()
    return ConsoleSmsProvider()


def set_sms_provider(provider: SmsProvider | None) -> None:
    """Tests pin a provider; None goes back to the setting."""
    global _override
    _override = provider
