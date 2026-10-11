"""A per-address request limit in front of the API (config/limits.yaml).

A sliding window held in this process: enough to stop a single client hammering an endpoint, not a
replacement for a gateway in front of several API processes. The OTP, PIN and guest-start limits
stay where they are, in the database. Over the limit the answer is 429 with `Retry-After`.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass
from functools import lru_cache

import yaml

from app.registries.paths import config_dir


@dataclass(frozen=True)
class Limits:
    window: int
    default: int
    groups: tuple[tuple[str, int], ...]
    exempt: tuple[str, ...]

    def for_path(self, path: str) -> tuple[str, int] | None:
        if path in self.exempt:
            return None
        for prefix, limit in self.groups:
            if path.startswith(prefix):
                return prefix, limit
        return "*", self.default


@lru_cache(maxsize=1)
def load_limits() -> Limits:
    data = yaml.safe_load((config_dir() / "limits.yaml").read_text(encoding="utf-8"))
    return Limits(
        window=int(data["window_seconds"]),
        default=int(data["default"]),
        groups=tuple((str(g["prefix"]), int(g["limit"])) for g in data.get("groups", [])),
        exempt=tuple(str(x) for x in data.get("exempt", [])),
    )


class Limiter:
    def __init__(self, limits: Limits | None = None) -> None:
        self.limits = limits or load_limits()
        self.hits: dict[tuple[str, str], deque[float]] = defaultdict(deque)

    def check(self, client: str, path: str, now: float | None = None) -> int | None:
        """None when allowed; otherwise the seconds to wait."""
        rule = self.limits.for_path(path)
        if rule is None:
            return None
        group, limit = rule
        moment = time.monotonic() if now is None else now
        queue = self.hits[(client, group)]
        while queue and moment - queue[0] >= self.limits.window:
            queue.popleft()
        if len(queue) >= limit:
            return max(1, int(self.limits.window - (moment - queue[0])))
        queue.append(moment)
        return None

    def reset(self) -> None:
        self.hits.clear()


limiter = Limiter()
