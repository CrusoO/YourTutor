"""`python -m app.llm draft_content ...`: an authoring command, refused in production."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.config import settings
from app.llm.draft import DraftRefused, draft_items
from app.llm.provider import LiteLLMProvider, Provider


def main(argv: list[str] | None = None, provider: Provider | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.llm")
    sub = parser.add_subparsers(dest="command", required=True)
    draft = sub.add_parser("draft_content", help="draft practice items (status: draft only)")
    draft.add_argument("--skill", required=True)
    draft.add_argument(
        "--passages", type=Path, required=True, help="text file of authored passages"
    )
    draft.add_argument("--out", type=Path, required=True, help="folder for the draft item files")
    draft.add_argument("--count", type=int, default=5)
    args = parser.parse_args(argv)

    if settings.app_env.lower() == "production":
        print("draft_content is disabled when APP_ENV=production", file=sys.stderr)
        return 2
    if provider is None:
        if not settings.llm_api_key or not settings.llm_model_strong:
            print("draft_content needs LLM_API_KEY and LLM_MODEL_STRONG", file=sys.stderr)
            return 2
        provider = LiteLLMProvider()
    try:
        report = draft_items(
            skill_id=args.skill,
            passages=args.passages.read_text(encoding="utf-8"),
            count=args.count,
            provider=provider,
            out_dir=args.out,
        )
    except DraftRefused as exc:
        print(str(exc), file=sys.stderr)
        return 2
    for path in report.written:
        print(f"wrote {path}")
    for index, reason in report.rejected:
        print(f"rejected item {index}: {reason}")
    print(f"{len(report.written)} written, {len(report.rejected)} rejected (all status: draft)")
    return 0 if report.written else 1


if __name__ == "__main__":
    raise SystemExit(main())
