"""Word handling shared by the stages: tokenising, stop words, snippets, BM25."""

from __future__ import annotations

import math
import re

# Latin and other \w letters, plus Devanagari and Bengali-script blocks (combining marks are not
# \w, so they are listed). The danda marks are left out: they are punctuation.
WORD = re.compile(r"[\wऀ-ॣ०-ॿঀ-৿]+(?:\.\d+)?")
STOP = frozenset(
    "a an the of in on at to is are was were be been it its this that these those and or but for "
    "with as by from which what who whom whose how why when where do does did not no than then so "
    "such can could will would should may might has have had their there into also each other "
    "both more most any all one two if you your we our they them he she his her i me my".split()
)


def words(text: str) -> list[str]:
    return [w.replace("_", "") for w in WORD.findall(text.casefold())]


def content_words(text: str) -> list[str]:
    return [w for w in words(text) if w not in STOP and (len(w) >= 3 or w.isdigit())]


def snippet(text: str, limit: int = 25) -> str:
    return " ".join(text.split()[:limit])


def stem(word: str) -> str:
    """A very light suffix strip so 'planets' meets 'planet'. Not a real stemmer."""
    for suffix in ("ing", "es", "s", "ed"):
        if len(word) > len(suffix) + 3 and word.endswith(suffix):
            return word[: -len(suffix)]
    return word


class BM25:
    """Okapi BM25 over a list of tokenised passages (stdlib only)."""

    def __init__(self, docs: list[list[str]], k1: float = 1.5, b: float = 0.75) -> None:
        self.k1, self.b = k1, b
        self.n = len(docs)
        self.lengths = [len(d) for d in docs]
        self.avg = (sum(self.lengths) / self.n) if self.n else 0.0
        self.postings: dict[str, list[tuple[int, int]]] = {}
        for index, doc in enumerate(docs):
            counts: dict[str, int] = {}
            for word in doc:
                counts[word] = counts.get(word, 0) + 1
            for word, tf in counts.items():
                self.postings.setdefault(word, []).append((index, tf))

    def top(self, query: list[str], k: int = 5) -> list[tuple[int, float]]:
        scores: dict[int, float] = {}
        for term in set(query):
            posting = self.postings.get(term)
            if not posting:
                continue
            idf = math.log(1 + (self.n - len(posting) + 0.5) / (len(posting) + 0.5))
            for index, tf in posting:
                norm = tf + self.k1 * (1 - self.b + self.b * self.lengths[index] / (self.avg or 1))
                scores[index] = scores.get(index, 0.0) + idf * tf * (self.k1 + 1) / norm
        return sorted(scores.items(), key=lambda pair: -pair[1])[:k]
