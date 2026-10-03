from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_region_literal_script_clean() -> None:
    script = Path(__file__).resolve().parents[2] / "scripts" / "check_region_literals.py"
    completed = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
