"""Operator helpers for the biology lane: write content, certify all, stamp all, faults, report.

    python -m app.factory.lanes.biology.tools write-content --root ../../content/cbse/10/biology
    python -m app.factory.lanes.biology.tools certify-all --root ... [--only HERED.MONO_RATIO]
    python -m app.factory.lanes.biology.tools stamp-all --root ... --count 25
    python -m app.factory.lanes.biology.tools faults
    python -m app.factory.lanes.biology.tools report --root ... [--sample 30]

Certify and stamp go through the real `python -m app.factory` commands (cli.main). No model call,
no network.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import random
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

from app.content.ledger import Ledger, ledger_path
from app.factory.cli import main as factory_main
from app.factory.lanes.biology.content import template_path, write_content
from app.factory.lanes.biology.models import ALL_MODELS
from app.factory.lanes.biology.templates import all_templates


def _run(root: Path, *argv: str) -> tuple[int, str]:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = factory_main(["--root", str(root), *argv])
    return code, buf.getvalue()


def _selected(only: list[str]) -> list[str]:
    return [m for m in ALL_MODELS if not only or m in only]


def cmd_certify_all(root: Path, only: list[str]) -> int:
    bad = 0
    templates = all_templates()
    for mid in _selected(only):
        path = template_path(root, templates[mid]["id"])
        code, out = _run(root, "certify", str(path), "--no-reference-index")
        first = next((ln for ln in out.splitlines() if ln.startswith("TPL2")), out[-120:])
        print(f"{mid}: {'CERTIFIED' if code == 0 else 'FAILED'} | {first}")
        bad += code != 0
    return bad


def cmd_stamp_all(root: Path, only: list[str], count: int, seed: int) -> int:
    bad = 0
    templates = all_templates()
    for mid in _selected(only):
        path = template_path(root, templates[mid]["id"])
        code, out = _run(
            root,
            "stamp",
            str(path),
            "--count",
            str(count),
            "--seed",
            str(seed),
            "--no-reference-index",
        )
        last = next((ln for ln in out.splitlines() if ln.startswith("stamped")), out[-80:])
        print(f"{mid}: {last}")
        bad += code != 0
    return bad


def _items(root: Path) -> list[dict[str, Any]]:
    folder = root / "items" / "factory" / "biology"
    return [yaml.safe_load(p.read_text(encoding="utf-8")) for p in sorted(folder.glob("*.yaml"))]


def cmd_report(root: Path, sample: int, seed: int) -> None:
    items = _items(root)
    ledger = Ledger(ledger_path(root))
    print(
        f"ledger entries {len(ledger.entries())}: "
        + ("intact" if not ledger.verify() else "BROKEN")
    )
    per_chapter = Counter(i["verification"]["chapter_ref"] for i in items)
    per_skill = Counter(i["skill_ids"][0] for i in items)
    print(f"stamped items: {len(items)}")
    for chapter, count in sorted(per_chapter.items()):
        print(f"  {chapter}: {count}")
    for skill, count in sorted(per_skill.items()):
        print(f"    {skill}: {count}")
    checks: dict[str, Counter[str]] = {}
    for item in items:
        for c in item["verification"]["checks"]:
            checks.setdefault(c["id"], Counter())[c["status"]] += 1
    print("checker | pass | fail | skip")
    for cid, c in checks.items():
        print(f"{cid} | {c['pass']} | {c['fail']} | {c['skip']}")
    picks = random.Random(seed).sample(sorted(i["id"] for i in items), min(sample, len(items)))
    by_id = {i["id"]: i for i in items}
    print(f"\naudit sample ({len(picks)}), NOT reviewed by a person:")
    for pid in picks:
        item = by_id[pid]
        key = next(o["en"] for o in item["options"] if o["id"] == item["answer"]["sympy"])
        print(f"- {pid} | {item['stem']['en']} | key: {key}")
    print("\ncertificates:")
    for e in ledger.entries():
        if e["kind"] == "certificate_issued":
            p = e["payload"]
            counts = f"box {p['size']} ok {p['ok']} skipped {p['skipped']}"
            print(f"- {e['subject_id']}: {p['kind']} {counts}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.factory.lanes.biology.tools")
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ("write-content", "certify-all", "stamp-all", "report"):
        p = sub.add_parser(name)
        p.add_argument("--root", type=Path, required=True)
        p.add_argument("--only", nargs="*", default=[])
        p.add_argument("--count", type=int, default=25)
        p.add_argument("--seed", type=int, default=0)
        p.add_argument("--sample", type=int, default=30)
    f = sub.add_parser("faults")
    f.add_argument("--per-model", type=int, default=3)
    args = parser.parse_args(argv)
    if args.cmd == "write-content":
        print(json.dumps(write_content(args.root)))
        return 0
    if args.cmd == "certify-all":
        return cmd_certify_all(args.root, args.only)
    if args.cmd == "stamp-all":
        return cmd_stamp_all(args.root, args.only, args.count, args.seed)
    if args.cmd == "report":
        cmd_report(args.root, args.sample, args.seed)
        return 0
    from app.factory.lanes.biology.faultset import run_all

    report, n = run_all(args.per_model)
    print(f"cases {n}\n{report.render()}\nperfect: {report.perfect}  id: {report.report_id}")
    for c in report.classes.values():
        if c.survivors:
            print("SURVIVORS", c.fault, c.survivors[:5])
    if report.baseline_failures:
        print("BASELINE FAILURES", report.baseline_failures[:5])
    return 0 if report.perfect else 1


if __name__ == "__main__":
    sys.exit(main())
