"""AES-GCM seal and open, the key ring, and that nothing leaks a key."""

from __future__ import annotations

import base64
import os
import uuid

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.learner.profile.crypto import (
    KeyRing,
    ProfileCryptoError,
    build_aad,
    parse_key_ring,
    seal,
    unseal,
)


def _key() -> bytes:
    return os.urandom(32)


def _ring(*ids: int) -> KeyRing:
    return KeyRing(tuple((i, _key()) for i in ids))


@settings(deadline=None)
@given(st.binary(max_size=300), st.text(alphabet="ABC_.", min_size=1, max_size=20))
def test_round_trip(plaintext: bytes, skill: str) -> None:  # property (l)
    ring, student = _ring(1), uuid.uuid4()
    aad = build_aad(student, skill, 1)
    key_id, blob = seal(ring, plaintext, aad)
    assert unseal(ring, key_id, blob, aad) == plaintext


def test_a_tampered_aad_or_blob_fails() -> None:
    ring, student = _ring(1), uuid.uuid4()
    key_id, blob = seal(ring, b"counts", build_aad(student, "SK", 1))
    for bad in (
        build_aad(uuid.uuid4(), "SK", 1),  # another student
        build_aad(student, "OTHER", 1),  # another skill
        build_aad(student, "SK", 2),  # another schema
    ):
        with pytest.raises(ProfileCryptoError):
            unseal(ring, key_id, blob, bad)
    flipped = blob[:-1] + bytes([blob[-1] ^ 1])
    with pytest.raises(ProfileCryptoError):
        unseal(ring, key_id, flipped, build_aad(student, "SK", 1))


def test_rotation_new_key_encrypts_old_key_still_opens() -> None:
    old = _ring(1)
    aad = build_aad(uuid.uuid4(), "SK", 1)
    key_id, blob = seal(old, b"x", aad)
    rotated = KeyRing(((2, _key()), *old.keys))
    assert seal(rotated, b"y", aad)[0] == 2
    assert unseal(rotated, key_id, blob, aad) == b"x"
    with pytest.raises(ProfileCryptoError):
        unseal(KeyRing(((2, _key()),)), key_id, blob, aad)


def test_empty_ring_refuses_to_seal() -> None:
    with pytest.raises(ProfileCryptoError):
        seal(KeyRing(), b"x", b"a")


def test_parse_and_no_key_text_in_errors_or_repr() -> None:
    raw = _key()
    encoded = base64.b64encode(raw).decode()
    ring = parse_key_ring(f"3:{encoded}")
    assert ring.keys == ((3, raw),)
    assert encoded not in repr(ring)
    short = base64.b64encode(b"short").decode()
    with pytest.raises(ValueError) as info:
        parse_key_ring("9:" + short)
    assert short not in str(info.value)
    for bad in ("nokey", "x:AAAA", "1:!!!notbase64", f"1:{encoded},1:{encoded}"):
        with pytest.raises(ValueError):
            parse_key_ring(bad)
    assert parse_key_ring("").empty
