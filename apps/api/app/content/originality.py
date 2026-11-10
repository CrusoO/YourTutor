"""Originality gate v1: does a bank question share too much with a reference text?

Pure Python, no new dependency. The reference index holds HASHED word 5-grams and hashed
structure fingerprints only; the reference text itself is never stored, printed or sent anywhere.
The operator supplies local reference files and this module reads them once and writes hashes.

Checks, in order of weight:
1. containment: the share of the item's canonical 5-grams found in the index. At or above
   BLOCK_CONTAINMENT the item is blocked.
2. shared run: a run of RUN_TOKENS or more consecutive tokens found in the index, outside a small
   stock-phrase allowlist, goes to review. With hashes only, a run of L tokens shows up as
   L - 4 consecutive matching 5-grams, so no text is needed.
3. structure: the same numbers and the same unknowns as a reference unit goes to review.
4. embeddings: a documented stub (EmbeddingScorer). Not implemented now; thresholds are fixed
   here so the interface is settled.

Canonical form: lowercase, punctuation dropped, every number becomes `<n>`, every single-letter
variable becomes `<v>` (a and i stay words), so changing the numbers or the letter does not hide a
copy. A 64-bit hash is enough to compare shingles; it is not a security boundary, and short
hashed n-grams of common words can be guessed, so treat the index file as private anyway.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Protocol

SHINGLE_WORDS = 5
RUN_TOKENS = 8
BLOCK_CONTAINMENT = 0.15
MIN_STRUCTURE_NUMBERS = 2
EMBED_BLOCK_THRESHOLD = 0.92  # stub: cosine at or above this would block
EMBED_REVIEW_THRESHOLD = 0.85  # stub: cosine at or above this would go to review
INDEX_VERSION = 1
NUMBER_TOKEN = "<n>"
VARIABLE_TOKEN = "<v>"
_WORDS_KEPT = {"a", "i"}

# Phrases that carry no originality: a shared run made only of these is ignored. Canonical form.
STOCK_PHRASES: tuple[str, ...] = (
    "find the value of",
    "find the value of <v>",
    "which of the following is",
    "which of the following",
    "show that",
    "prove that",
    "solve the following",
    "solve for <v>",
    "what is the value of",
    "write the answer in the simplest form",
    "give reasons for your answer",
    "is equal to",
    "is a factor of",
    "is a multiple of",
    "the sum of",
    "the product of",
    "the difference between",
    "if and only if",
)

_TOKEN = re.compile(r"\d+(?:[.,]\d+)*|[^\W\d_]+", re.UNICODE)


class OriginalityStatus(StrEnum):
    passed = "pass"
    review = "review"
    block = "block"


def tokenize(text: str) -> list[str]:
    """Canonical tokens: numbers and single-letter variables replaced by placeholders."""
    out: list[str] = []
    for raw in _TOKEN.findall(text.lower()):
        if raw[0].isdigit():
            out.append(NUMBER_TOKEN)
        elif len(raw) == 1 and raw not in _WORDS_KEPT:
            out.append(VARIABLE_TOKEN)
        else:
            out.append(raw)
    return out


def canonicalise(text: str) -> str:
    return " ".join(tokenize(text))


def structure_of(text: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """(sorted numbers, sorted unknown letters) of a text, from the raw tokens."""
    numbers: list[str] = []
    unknowns: set[str] = set()
    for raw in _TOKEN.findall(text.lower()):
        if raw[0].isdigit():
            numbers.append(raw.replace(",", ""))
        elif len(raw) == 1 and raw not in _WORDS_KEPT:
            unknowns.add(raw)
    return tuple(sorted(numbers)), tuple(sorted(unknowns))


def hash_text(value: str) -> str:
    return hashlib.blake2b(value.encode("utf-8"), digest_size=8).hexdigest()


def shingles(tokens: Sequence[str], n: int = SHINGLE_WORDS) -> list[str]:
    """Hashed word n-grams, in order (so runs can be found)."""
    return [hash_text(" ".join(tokens[i : i + n])) for i in range(len(tokens) - n + 1)]


def structure_hash(text: str) -> str | None:
    numbers, unknowns = structure_of(text)
    if len(numbers) < MIN_STRUCTURE_NUMBERS or not unknowns:
        return None
    return hash_text("|".join(numbers) + "#" + "".join(unknowns))


@dataclass
class ReferenceIndex:
    shingle_hashes: set[str] = field(default_factory=set)
    structure_hashes: set[str] = field(default_factory=set)
    units: int = 0

    def to_json(self) -> str:
        return json.dumps(
            {
                "version": INDEX_VERSION,
                "n": SHINGLE_WORDS,
                "units": self.units,
                "shingles": sorted(self.shingle_hashes),
                "structures": sorted(self.structure_hashes),
            }
        )

    @classmethod
    def from_json(cls, blob: str) -> ReferenceIndex:
        data = json.loads(blob)
        if data.get("version") != INDEX_VERSION or data.get("n") != SHINGLE_WORDS:
            raise ValueError("originality index has a different version or shingle size")
        return cls(set(data["shingles"]), set(data["structures"]), int(data.get("units", 0)))

    def add_text(self, text: str) -> None:
        """Index one reference text: its units (blank-line blocks, else lines)."""
        blocks = [b for b in re.split(r"\n\s*\n", text) if b.strip()]
        if len(blocks) == 1:
            blocks = [line for line in text.splitlines() if line.strip()]
        for block in blocks:
            self.units += 1
            self.shingle_hashes.update(shingles(tokenize(block)))
            digest = structure_hash(block)
            if digest:
                self.structure_hashes.add(digest)


REFERENCE_SUFFIXES = (".txt", ".md", ".csv", ".tsv", ".json")


def build_index(folder: Path) -> tuple[ReferenceIndex, int]:
    """Read every text file under `folder` and keep hashes only. Returns (index, files read)."""
    index = ReferenceIndex()
    files = 0
    for path in sorted(folder.rglob("*")):
        if path.is_file() and path.suffix.lower() in REFERENCE_SUFFIXES:
            index.add_text(path.read_text(encoding="utf-8", errors="ignore"))
            files += 1
    return index, files


@dataclass(frozen=True)
class OriginalityScore:
    status: OriginalityStatus
    containment: float
    longest_run: int  # tokens, outside stock phrases
    structure_match: bool
    reasons: tuple[str, ...] = ()


def _stock_mask(tokens: Sequence[str]) -> list[bool]:
    mask = [False] * len(tokens)
    for phrase in STOCK_PHRASES:
        words = phrase.split()
        for start in range(len(tokens) - len(words) + 1):
            if list(tokens[start : start + len(words)]) == words:
                for i in range(start, start + len(words)):
                    mask[i] = True
    return mask


def longest_shared_run(tokens: Sequence[str], index: ReferenceIndex) -> int:
    """Longest stretch of consecutive tokens that also occurs in the reference, ignoring tokens
    that sit inside a stock phrase."""
    grams = shingles(tokens)
    covered = [False] * len(tokens)
    for position, gram in enumerate(grams):
        if gram in index.shingle_hashes:
            for i in range(position, position + SHINGLE_WORDS):
                covered[i] = True
    stock = _stock_mask(tokens)
    best = run = 0
    for flag, is_stock in zip(covered, stock, strict=True):
        if flag and not is_stock:
            run += 1
            best = max(best, run)
        else:
            run = 0
    return best


class EmbeddingScorer(Protocol):
    """Interface for the later embedding step (NOT implemented in v1).

    `similarity` returns the highest cosine similarity between the item and any reference unit,
    or None when no scorer is configured. At or above EMBED_BLOCK_THRESHOLD the item blocks, at or
    above EMBED_REVIEW_THRESHOLD it goes to review. A scorer must not send reference text to a
    third party without the owner's say-so.
    """

    def similarity(self, text: str) -> float | None: ...


class NoEmbeddingScorer:
    def similarity(self, text: str) -> float | None:
        return None


def score_text(
    text: str, index: ReferenceIndex, *, embedder: EmbeddingScorer | None = None
) -> OriginalityScore:
    tokens = tokenize(text)
    grams = shingles(tokens)
    hits = sum(1 for g in grams if g in index.shingle_hashes)
    containment = hits / len(grams) if grams else 0.0
    run = longest_shared_run(tokens, index) if grams else 0
    digest = structure_hash(text)
    structure_match = digest is not None and digest in index.structure_hashes
    reasons: list[str] = []
    status = OriginalityStatus.passed
    if containment >= BLOCK_CONTAINMENT:
        status = OriginalityStatus.block
        reasons.append(f"containment {containment:.2f} >= {BLOCK_CONTAINMENT}")
    if run >= RUN_TOKENS:
        if status is OriginalityStatus.passed:
            status = OriginalityStatus.review
        reasons.append(f"shared run of {run} tokens")
    if structure_match:
        if status is OriginalityStatus.passed:
            status = OriginalityStatus.review
        reasons.append("same numbers and unknowns as a reference unit")
    similarity = (embedder or NoEmbeddingScorer()).similarity(text)
    if similarity is not None:
        if similarity >= EMBED_BLOCK_THRESHOLD:
            status = OriginalityStatus.block
            reasons.append(f"embedding similarity {similarity:.2f}")
        elif similarity >= EMBED_REVIEW_THRESHOLD and status is OriginalityStatus.passed:
            status = OriginalityStatus.review
            reasons.append(f"embedding similarity {similarity:.2f}")
    return OriginalityScore(status, containment, run, structure_match, tuple(reasons))


def item_text(stem: str, options: Iterable[str] = ()) -> str:
    return "\n".join([stem, *options])
