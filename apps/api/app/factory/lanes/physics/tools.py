"""Operator helpers for the physics lane: write content, certify all, stamp all, faults, report.

    python -m app.factory.lanes.physics.tools write-content --root ../../content/cbse/10/physics
    python -m app.factory.lanes.physics.tools certify-all --root ... [--only ELEC.OHM]
    python -m app.factory.lanes.physics.tools stamp-all --root ... --count 15
    python -m app.factory.lanes.physics.tools faults --chapter cbse.10.physics.electricity
    python -m app.factory.lanes.physics.tools report --root ... [--sample 30]

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
from app.factory.lanes.physics.content import ELEC_CH, LIGHT_CH, template_path, write_content
from app.factory.lanes.physics.models import ALL_MODELS
from app.factory.lanes.physics.templates import TEMPLATES


def _run(root: Path, *argv: str) -> tuple[int, str]:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = factory_main(["--root", str(root), *argv])
    return code, buf.getvalue()


def _selected(only: list[str]) -> list[str]:
    return [m for m in ALL_MODELS if not only or m in only]


def cmd_certify_all(root: Path, only: list[str]) -> int:
    bad = 0
    for mid in _selected(only):
        path = template_path(root, TEMPLATES[mid]["id"])
        code, out = _run(root, "certify", str(path), "--no-reference-index")
        first = next((ln for ln in out.splitlines() if ln.startswith("TPL2")), "")
        print(f"{mid}: {'CERTIFIED' if code == 0 else 'FAILED'} | {first}")
        bad += code != 0
    return bad


def cmd_stamp_all(root: Path, only: list[str], count: int, seed: int) -> int:
    bad = 0
    for mid in _selected(only):
        path = template_path(root, TEMPLATES[mid]["id"])
        code, out = _run(root, "stamp", str(path), "--count", str(count), "--seed", str(seed),
                         "--no-reference-index")  # fmt: skip
        last = next((ln for ln in out.splitlines() if ln.startswith("stamped")), out[-80:])
        print(f"{mid}: {last}")
        bad += code != 0
    return bad


def _items(root: Path) -> list[dict[str, Any]]:
    out = []
    for path in sorted((root / "items" / "factory" / "physics").glob("*.yaml")):
        out.append(yaml.safe_load(path.read_text(encoding="utf-8")))
    return out


def cmd_report(root: Path, sample: int, seed: int) -> None:
    items = _items(root)
    ledger = Ledger(ledger_path(root))
    entries = ledger.entries()
    print(f"ledger entries {len(entries)}: " + ("intact" if not ledger.verify() else "BROKEN"))
    for chapter in (ELEC_CH, LIGHT_CH):
        mine = [i for i in items if i["verification"]["chapter_ref"] == chapter]
        checks: dict[str, Counter[str]] = {}
        for item in mine:
            for c in item["verification"]["checks"]:
                checks.setdefault(c["id"], Counter())[c["status"]] += 1
        print(f"\n## {chapter}: {len(mine)} stamped items")
        print("checker | pass | fail | skip")
        for cid, c in checks.items():
            print(f"{cid} | {c['pass']} | {c['fail']} | {c['skip']}")
        picks = random.Random(seed).sample(sorted(i["id"] for i in mine), min(sample, len(mine)))
        print(f"\naudit sample ({len(picks)}), NOT reviewed by a person:")
        by_id = {i["id"]: i for i in mine}
        for pid in picks:
            item = by_id[pid]
            key = next(o["en"] for o in item["options"] if o["id"] == item["answer"]["sympy"])
            print(f"- {pid} | {item['stem']['en']} | key: {key}")
    cert_entries = [e for e in entries if e["kind"] == "certificate_issued"]
    print("\ncertificates:")
    for e in cert_entries:
        p = e["payload"]
        print(
            f"- {e['subject_id']}: {p['kind']} box {p['size']} ok {p['ok']} skipped {p['skipped']}"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.factory.lanes.physics.tools")
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ("write-content", "certify-all", "stamp-all", "report"):
        p = sub.add_parser(name)
        p.add_argument("--root", type=Path, required=True)
        p.add_argument("--only", nargs="*", default=[])
        p.add_argument("--count", type=int, default=15)
        p.add_argument("--seed", type=int, default=0)
        p.add_argument("--sample", type=int, default=30)
    f = sub.add_parser("faults")
    f.add_argument("--chapter", required=True)
    f.add_argument("--per-template", type=int, default=4)
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
    from app.factory.lanes.physics.faultset import run_chapter

    report, n = run_chapter(args.chapter, args.per_template)
    print(f"cases {n}\n{report.render()}\nperfect: {report.perfect}  id: {report.report_id}")
    for c in report.classes.values():
        if c.survivors:
            print("SURVIVORS", c.fault, c.survivors[:5])
    if report.baseline_failures:
        print("BASELINE FAILURES", report.baseline_failures[:5])
    return 0 if report.perfect else 1


if __name__ == "__main__":
    sys.exit(main())
