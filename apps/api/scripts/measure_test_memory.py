"""Peak memory per test directory (G2 memory check).

Runs `pytest <dir>` for every directory under tests/ as a subprocess and samples the process's
working set with `tasklist` (Windows, no extra packages). Prints one line per directory and a
total. Use a database no other pytest run is using:

    TEST_DATABASE_URL=postgresql+psycopg://tutor:tutor@127.0.0.1:5432/yourtutor_test2 \
        python scripts/measure_test_memory.py [dir ...]
"""

from __future__ import annotations

import csv
import io
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "tests"
INTERVAL = 0.5


def working_set_mb(pid: int) -> float:
    out = subprocess.run(
        ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
        capture_output=True,
        text=True,
        check=False,
    ).stdout
    for row in csv.reader(io.StringIO(out)):
        if len(row) >= 5:
            digits = "".join(ch for ch in row[4] if ch.isdigit())
            if digits:
                return int(digits) / 1024  # KB -> MB
    return 0.0


def measure(target: Path) -> tuple[float, float, str]:
    started = time.time()
    log_path = os.environ.get("MEASURE_LOG")  # stream pytest output so a kill leaves a trail
    sink: Any = open(log_path, "w", encoding="utf-8") if log_path else subprocess.PIPE  # noqa: SIM115
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "pytest",
            "-v" if log_path else "-q",
            "-p",
            "no:randomly",
            str(target),
        ],
        cwd=ROOT,
        stdout=sink,
        stderr=subprocess.STDOUT,
        text=True,
    )
    peak = 0.0
    while proc.poll() is None:
        peak = max(peak, working_set_mb(proc.pid))
        time.sleep(INTERVAL)
    if log_path:
        sink.close()
        output = open(log_path, encoding="utf-8", errors="ignore").read()
    else:
        output = proc.stdout.read() if proc.stdout else ""
    summary = next(
        (ln for ln in reversed(output.splitlines()) if " passed" in ln or " failed" in ln), ""
    )
    return peak, time.time() - started, summary.strip()


def main(argv: list[str]) -> int:
    targets = [TESTS / name for name in argv] or sorted(
        p for p in TESTS.iterdir() if p.is_dir() and p.name != "__pycache__"
    )
    targets += [TESTS / "test_health.py"] if not argv else []
    worst = 0.0
    for target in targets:
        peak, seconds, summary = measure(target)
        worst = max(worst, peak)
        print(f"{target.name:<14} peak {peak:7.0f} MB  {seconds:7.0f} s  {summary}", flush=True)
    print(f"worst directory: {worst:.0f} MB", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
