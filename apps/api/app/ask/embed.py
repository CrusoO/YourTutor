"""Passage and question embeddings behind one small interface.

The default embedder hashes word unigrams and bigrams into a fixed-size unit vector. It is
deterministic, needs no model or network, and works for any script that has word boundaries; it is
a lexical embedding, so it ranks by shared wording, not by meaning. A model-backed embedder can
replace it by implementing `Embedder`; nothing else changes.
"""

from __future__ import annotations

import hashlib
import math
import re
from typing import Protocol

DIM = 256
WORD = re.compile(r"\w+", re.UNICODE)


class Embedder(Protocol):
    def embed(self, text: str) -> list[float]: ...


def tokens(text: str) -> list[str]:
    return [w.casefold() for w in WORD.findall(text)]


def _bucket(feature: str) -> tuple[int, float]:
    digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=4).digest()
    value = int.from_bytes(digest, "big")
    return value % DIM, 1.0 if (value >> 31) & 1 else -1.0


class HashingEmbedder:
    def embed(self, text: str) -> list[float]:
        words = tokens(text)
        vec = [0.0] * DIM
        for feature in [*words, *(f"{a} {b}" for a, b in zip(words, words[1:], strict=False))]:
            index, sign = _bucket(feature)
            vec[index] += sign
        norm = math.sqrt(sum(v * v for v in vec))
        return [v / norm for v in vec] if norm else vec


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=False))


def default_embedder() -> Embedder:
    return HashingEmbedder()
