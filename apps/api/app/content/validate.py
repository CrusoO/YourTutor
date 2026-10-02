from __future__ import annotations

import sys

from app.content.__main__ import main

if __name__ == "__main__":
    raise SystemExit(main(["validate", *sys.argv[1:]]))
