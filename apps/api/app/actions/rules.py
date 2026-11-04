"""The phrase table the browser matches typed commands against.

Like the topic finder's rules, this is a GET with no user text: the browser fetches the table and
matches locally, so what a student types never reaches the API, a log or the database. The table is
built only from the closed registry and `config/actions.yaml`; the browser checks it again before
it runs anything.

Regenerate the shared fixture after changing the config:
    cd apps/api && python -m app.actions.rules \\
        > ../../packages/shared/fixtures/actions/rules_en.json
"""

from __future__ import annotations

import json
from typing import Any

from app.actions.matcher import ActionConfig, action_config, phrases_for
from app.actions.registry import REGISTRY


def build_rules(language: str, config: ActionConfig | None = None) -> dict[str, Any]:
    config = config or action_config()
    resolved = language if language in config.languages else config.default_language
    phrases = phrases_for(config, resolved)

    actions: dict[str, dict[str, Any]] = {}
    for name, spec in REGISTRY.items():
        row: dict[str, Any] = {
            "client": spec.client,
            "risk": spec.risk.value,
            "tiers": sorted(tier.value for tier in spec.tiers),
            "narration": phrases.narration[name],
        }
        if name in phrases.confirm:
            row["confirm"] = phrases.confirm[name]
        if name in phrases.denied:
            row["denied"] = phrases.denied[name]
        actions[name] = row

    table: dict[str, dict[str, Any]] = {}
    for key, (name, value) in sorted(phrases.table.items()):
        args = REGISTRY[name].args_for(value)
        if args is not None:  # a value the registry does not allow never reaches the browser
            table[key] = {"name": name, "args": args}

    return {
        "language": resolved,
        "max_chars": config.max_chars,
        "max_words": config.max_words,
        "fillers": sorted(phrases.fillers),
        "denied_default": config.messages.get(config.default_language, {}).get("denied", ""),
        "actions": actions,
        "phrases": table,
    }


if __name__ == "__main__":
    print(json.dumps(build_rules("en"), indent=2, ensure_ascii=False, sort_keys=True))
