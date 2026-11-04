"""The worker sleeps until a job is queued instead of polling the database."""

from __future__ import annotations

import os
from pathlib import Path

from app.video_jobs import wake


class Clock:
    """A fake clock whose sleep moves time forward, so nothing really waits."""

    def __init__(self) -> None:
        self.now = 0.0
        self.slept: list[float] = []

    def clock(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.now += seconds


def test_without_a_wake_file_it_is_a_plain_sleep() -> None:
    fake = Clock()
    assert wake.wait_for_work("", 0.0, 5.0, sleep=fake.sleep, clock=fake.clock) == 0.0
    assert fake.slept == [5.0]


def test_touching_the_file_changes_its_stamp(tmp_path: Path) -> None:
    path = str(tmp_path / "deep" / "wake")
    assert wake.stamp(path) == 0.0
    wake.touch(path)
    first = wake.stamp(path)
    assert first > 0
    os.utime(path, (first + 5, first + 5))
    assert wake.stamp(path) == first + 5


def test_an_idle_worker_wakes_as_soon_as_the_file_changes(tmp_path: Path) -> None:
    path = str(tmp_path / "wake")
    wake.touch(path)
    seen = wake.stamp(path)
    fake = Clock()

    def sleep(seconds: float) -> None:
        fake.sleep(seconds)
        if fake.now >= 2.0:  # a job is queued two seconds in
            os.utime(path, (seen + 10, seen + 10))

    result = wake.wait_for_work(path, seen, 900.0, sleep=sleep, clock=fake.clock)
    assert result == seen + 10
    assert fake.now < 3.0  # woke long before the 15-minute safety poll


def test_with_no_change_it_waits_out_the_safety_poll_then_returns(tmp_path: Path) -> None:
    path = str(tmp_path / "wake")
    wake.touch(path)
    seen = wake.stamp(path)
    fake = Clock()
    result = wake.wait_for_work(path, seen, 3.0, sleep=fake.sleep, clock=fake.clock)
    assert result == seen and fake.now >= 3.0


def test_a_wake_file_that_cannot_be_written_never_raises(tmp_path: Path) -> None:
    blocker = tmp_path / "file"
    blocker.write_text("x")
    wake.touch(str(blocker / "child" / "wake"))  # the parent is a file: mkdir fails quietly
    wake.touch("")
