"""Audit samples of stamped items: uniform random and PPS (probability proportional to exposure).

PPS weights are how often students actually saw each item, so the audit looks hardest where an
error would reach the most students. Sampling is seeded and reproducible, without replacement
(Efraimidis-Spirakis keys). Human audit results and seeded traps are a later step; this lists who
to check.
"""

from __future__ import annotations

import math
import random
from collections.abc import Mapping, Sequence


def random_sample(ids: Sequence[str], n: int, seed: int) -> list[str]:
    pool = sorted(ids)
    return sorted(random.Random(seed).sample(pool, min(n, len(pool))))


def pps_sample(weights: Mapping[str, float], n: int, seed: int) -> list[str]:
    """Items with weight 0 are never drawn; ties and order are fixed by the seed."""
    rng = random.Random(seed)
    keys = []
    for item_id in sorted(weights):
        w = weights[item_id]
        if w > 0:
            keys.append((math.log(rng.random() or 1e-300) / w, item_id))
    keys.sort(reverse=True)  # largest log(u)/w first == largest u**(1/w)
    return [item_id for _, item_id in keys[:n]]


def sample_size(population: int, rate: float, minimum: int = 1) -> int:
    return min(population, max(minimum, math.ceil(population * rate))) if population else 0
