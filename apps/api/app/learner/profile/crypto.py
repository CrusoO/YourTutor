"""AES-256-GCM per-row seal with associated data, and a rotatable key ring.

`PROFILE_ENC_KEYS` is a comma list of `id:base64key` (32 bytes each), newest first. The first key
encrypts; every key decrypts. Rotation: add a new key in front, re-encrypt, then remove the old.
The associated data (student id, skill id, schema) binds a row to its owner: a copied row fails
to open anywhere else. Keys are never logged, printed or put in an error message.
"""

from __future__ import annotations

import base64
import binascii
import os
import uuid
from dataclasses import dataclass, field

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

NONCE_BYTES = 12
KEY_BYTES = 32
MAX_KEY_ID = 32767  # fits the SMALLINT key_id column


class ProfileCryptoError(Exception):
    """A row could not be sealed or opened. The message never carries key or plaintext bytes."""


@dataclass(frozen=True)
class KeyRing:
    keys: tuple[tuple[int, bytes], ...] = field(default=(), repr=False)

    def __repr__(self) -> str:
        return f"KeyRing(ids={[k for k, _ in self.keys]})"

    @property
    def empty(self) -> bool:
        return not self.keys


def parse_key_ring(text: str) -> KeyRing:
    """Parse `id:base64key,id:base64key`. Raises ValueError without echoing any key text."""
    entries: list[tuple[int, bytes]] = []
    for part in (p.strip() for p in text.split(",")):
        if not part:
            continue
        ident, sep, encoded = part.partition(":")
        if not sep or not ident.strip().isdigit():
            raise ValueError("PROFILE_ENC_KEYS entries must look like id:base64key")
        key_id = int(ident)
        if not 0 <= key_id <= MAX_KEY_ID or any(key_id == k for k, _ in entries):
            raise ValueError("PROFILE_ENC_KEYS has a bad or repeated key id")
        try:
            raw = base64.b64decode(encoded.strip(), validate=True)
        except (binascii.Error, ValueError):
            raise ValueError("PROFILE_ENC_KEYS has a key that is not valid base64") from None
        if len(raw) != KEY_BYTES:
            raise ValueError(f"PROFILE_ENC_KEYS keys must be {KEY_BYTES} bytes")
        entries.append((key_id, raw))
    return KeyRing(tuple(entries))


def build_aad(student_id: uuid.UUID, skill_id: str, schema: int) -> bytes:
    return f"{student_id}|{skill_id}|{schema}".encode()


def seal(ring: KeyRing, plaintext: bytes, aad: bytes) -> tuple[int, bytes]:
    """Encrypt with the newest key. Returns (key_id, nonce || ciphertext || tag)."""
    if ring.empty:
        raise ProfileCryptoError("no encryption key is configured")
    key_id, key = ring.keys[0]
    nonce = os.urandom(NONCE_BYTES)
    return key_id, nonce + AESGCM(key).encrypt(nonce, plaintext, aad)


def unseal(ring: KeyRing, key_id: int, blob: bytes, aad: bytes) -> bytes:
    """Decrypt a sealed row; wrong key id, wrong AAD or any tampering raises ProfileCryptoError."""
    key = dict(ring.keys).get(key_id)
    if key is None or len(blob) <= NONCE_BYTES:
        raise ProfileCryptoError("the row cannot be opened with the configured keys")
    try:
        return AESGCM(key).decrypt(blob[:NONCE_BYTES], blob[NONCE_BYTES:], aad)
    except InvalidTag:
        raise ProfileCryptoError("the row failed its integrity check") from None
