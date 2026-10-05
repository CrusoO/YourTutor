from __future__ import annotations

import json

from app.registries.loaders import load_locales_config
from app.registries.paths import repo_root


def main() -> None:
    default, locales = load_locales_config()
    payload = {
        "default": default,
        "locales": [
            {
                "code": spec.code,
                "name": spec.name,
                "script": spec.script,
                "status": spec.status,
                "fallback_chain": list(spec.fallback_chain),
            }
            for spec in locales.values()
        ],
    }
    out = repo_root() / "packages" / "shared" / "generated" / "locales.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
