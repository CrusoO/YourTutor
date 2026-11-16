"""`python -m app.factory <command>`: certify, stamp, audit-sample, report, ledger-verify, suspend.

Nothing here calls a model or a paid service. Content lives under --root (default: the repo's
content folder): templates anywhere you point at, certificates in factory/certificates/, stamped
items in items/factory/<lane>/, the ledger in factory/ledger.jsonl.
"""

from __future__ import annotations

import argparse
import importlib
import json
import random
import subprocess
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from app.content.ledger import Ledger, ledger_path
from app.content.originality import ReferenceIndex
from app.factory import audit, kernel
from app.factory.checkers import stem_identity
from app.factory.kernel.certify import box_axes
from app.factory.kernel.exact import chash
from app.factory.pipeline import run
from app.factory.registry import REGISTRY, Lane
from app.factory.runner import build_item, certify_lane_template, template_hash
from app.factory.stamp import StampRefused, stamp

LANE_MODULES = ("app.factory.lanes.maths_quadratic",)  # a new lane adds its module here


def _root(arg: Path | None) -> Path:
    from app.registries.paths import content_root

    return arg or content_root()


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _git_sha() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, timeout=5
        )
        return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def _load_template(path: Path) -> tuple[dict[str, Any], Lane]:
    for module in LANE_MODULES:
        importlib.import_module(module)
    template = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(template, dict) or template.get("schema") != "factory-template/1":
        raise SystemExit(f"{path} is not a factory-template/1 file")
    lane = REGISTRY.lanes.get(str(template.get("lane")))
    if lane is None:
        raise SystemExit(f"no lane named {template.get('lane')!r} is registered")
    return template, lane


def _reference_index(args: argparse.Namespace) -> tuple[ReferenceIndex, str]:
    if args.reference_index:
        blob = args.reference_index.read_text(encoding="utf-8")
        return ReferenceIndex.from_json(blob), chash(blob)[:16]
    if not args.no_reference_index:
        raise SystemExit(
            "originality needs a reference index (--reference-index FILE from "
            "`python -m app.content originality-index`), or pass --no-reference-index to say "
            "plainly that the originality check compares against nothing"
        )
    print("WARNING: no reference index; the originality check compared against nothing.")
    return ReferenceIndex(), "none"


def _cert_path(root: Path, template_id: str) -> Path:
    return root / "factory" / "certificates" / f"{template_id}.json"


def cmd_certify(args: argparse.Namespace) -> int:
    root = _root(args.root)
    template, lane = _load_template(args.template)
    index, index_tag = _reference_index(args)
    report = certify_lane_template(
        lane, template, seed=args.seed, max_exhaustive=args.max_exhaustive, reference_index=index
    )
    print(
        f"{template['id']}: {report.kind}, box {report.size}, tested {report.tested}, "
        f"accepted {report.ok}, refused as ill-posed {report.skipped}, failures {report.failures}"
    )
    for reason, count in report.skip_reasons.items():
        print(f"  ill-posed: {reason} x{count}")
    for sample in report.failure_samples[:5]:
        print(f"  FAIL {sample['params']}: {sample['reason']}")
    if report.certificate is None:
        print("NOT CERTIFIED: " + "; ".join(report.refused))
        return 1
    cert = report.certificate
    path = _cert_path(root, str(template["id"]))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"hash": cert.hash, "certificate": cert.body}, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    Ledger(ledger_path(root)).append(
        "certificate_issued",
        str(template["id"]),
        template_hash(lane, template),
        {"certificate_hash": cert.hash, "kind": report.kind, "size": report.size,
         "ok": report.ok, "skipped": report.skipped, "originality_index": index_tag},
        ts=_now(),
    )  # fmt: skip
    print(f"CERTIFIED {cert.hash[:16]} -> {path}")
    return 0


def _existing_stems(root: Path) -> set[str]:
    stems: set[str] = set()
    for path in sorted((root / "items").rglob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("stem"), dict):
            stems.add(stem_identity(str(data["stem"].get("en", ""))))
    return stems


def cmd_stamp(args: argparse.Namespace) -> int:
    root = _root(args.root)
    template, lane = _load_template(args.template)
    cert_file = _cert_path(root, str(template["id"]))
    if not cert_file.is_file():
        print(f"no certificate for {template['id']}: run `certify` first")
        return 1
    stored = json.loads(cert_file.read_text(encoding="utf-8"))
    body = stored["certificate"]
    if chash(body) != stored["hash"]:
        print("certificate file was edited by hand: refusing")
        return 1
    if body["subject"]["template_hash"] != template_hash(lane, template):
        print("the template changed since it was certified: run `certify` again")
        return 1
    if not kernel.certificate_is_current(body):
        print("certificate is stale (kernel, a checker or the constants table changed): re-certify")
        return 1
    index, _ = _reference_index(args)
    axes = box_axes(lane.box(template))
    total = 1
    for _, values in axes:
        total *= len(values)
    order = list(range(total))
    random.Random(args.seed).shuffle(order)
    ledger = Ledger(ledger_path(root))
    stems = _existing_stems(root)
    hashes: set[str] = set()
    out_dir = root / "items" / "factory" / lane.name
    out_dir.mkdir(parents=True, exist_ok=True)
    stamped = 0
    rejected: Counter[str] = Counter()
    sha = _git_sha()
    for index_no in order:
        if stamped >= args.count:
            break
        params: dict[str, Any] = {}
        rest = index_no
        for name, values in reversed(axes):
            rest, pos = divmod(rest, len(values))
            params[name] = values[pos]
        if lane.well_posed(template, params):
            continue
        ctx = build_item(
            lane, template, params, reference_index=index, bank_stems=stems, bank_spec_hashes=hashes
        )
        result = run(ctx)
        if not result.stampable:
            failure = result.first_failure
            rejected[f"{failure.checker_id}:{failure.code}" if failure else "unknown"] += 1
            continue
        try:
            item = stamp(
                ctx,
                result,
                template_id=str(template["id"]),
                template_hash=body["subject"]["template_hash"],
                ledger=ledger,
                ts=_now(),
                git_sha=sha,
            )
        except StampRefused as refusal:
            rejected[f"stamp:{refusal}"] += 1
            continue
        (out_dir / f"{ctx.item_id}.yaml").write_text(
            yaml.safe_dump(item, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
            newline="\n",
        )
        stems.add(stem_identity(ctx.stem))
        hashes.add(chash(ctx.spec))
        stamped += 1
    ledger.append(
        "stamp_run",
        str(template["id"]),
        body["subject"]["template_hash"],
        {
            "requested": args.count,
            "stamped": stamped,
            "rejected_by": dict(rejected),
            "seed": args.seed,
        },
        ts=_now(),
    )
    print(f"stamped {stamped} of {args.count} requested into {out_dir}")
    for reason, count in rejected.most_common(5):
        print(f"  rejected {count}x {reason}")
    return 0 if stamped else 1


def _stamped_items(root: Path) -> list[dict[str, Any]]:
    out = []
    for path in sorted((root / "items" / "factory").rglob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and data.get("verification"):
            out.append(data)
    return out


def cmd_audit_sample(args: argparse.Namespace) -> int:
    root = _root(args.root)
    items = _stamped_items(root)
    ids = [i["id"] for i in items]
    n = args.n or audit.sample_size(len(ids), args.rate, minimum=args.minimum)
    weights: dict[str, float] = {i: 1.0 for i in ids}
    if args.exposure:
        weights = {
            k: float(v) for k, v in json.loads(args.exposure.read_text(encoding="utf-8")).items()
        }
        weights = {i: weights.get(i, 0.0) for i in ids}
    picks = {
        "random": audit.random_sample(ids, n, args.seed),
        "pps": audit.pps_sample(weights, n, args.seed),
    }
    print(json.dumps({"population": len(ids), "n": n, "seed": args.seed, **picks}, indent=1))
    Ledger(ledger_path(root)).append(
        "audit_sample",
        "factory",
        chash(ids),
        {"population": len(ids), "n": n, "seed": args.seed},
        ts=_now(),
    )
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    root = _root(args.root)
    ledger = Ledger(ledger_path(root))
    items = _stamped_items(root)
    per_chapter = Counter(i["verification"].get("chapter_ref") or "(none)" for i in items)
    checks: dict[str, Counter[str]] = {}
    for item in items:
        for check in item["verification"].get("checks", []):
            checks.setdefault(check["id"], Counter())[check["status"]] += 1
    for entry in ledger.entries():
        if entry["kind"] == "stamp_run":
            for key, count in entry["payload"].get("rejected_by", {}).items():
                checker = key.split(":")[0]
                checks.setdefault(checker, Counter())["fail"] += count
    print(f"stamped items: {len(items)}   ledger entries: {len(ledger.entries())}")
    print("per chapter:")
    for chapter, count in sorted(per_chapter.items()):
        print(f"  {chapter}: {count}")
    print("per checker (pass / fail / skip):")
    for checker, c in sorted(checks.items()):
        print(f"  {checker}: {c['pass']} / {c['fail']} / {c['skip']}")
    problems = ledger.verify()
    print("ledger: " + ("intact" if not problems else "BROKEN: " + "; ".join(problems[:3])))
    return 0 if not problems else 1


def cmd_ledger_verify(args: argparse.Namespace) -> int:
    from app.content.factory_roots import content_roots

    root = _root(args.root)
    bad = 0
    # the root's own ledger and every lane ledger under <board>/<class>/<subject>
    for base in content_roots(root):
        path = ledger_path(base)
        if base != root and not path.is_file():
            continue
        ledger = Ledger(path)
        problems = ledger.verify()
        for problem in problems:
            print(f"{path.relative_to(root).as_posix()}: {problem}")
        bad += len(problems)
        label = "" if base == root else f" ({path.relative_to(root).as_posix()})"
        print(
            f"{len(ledger.entries())} entries, " + ("intact" if not problems else "BROKEN") + label
        )
    return 0 if not bad else 1


def cmd_suspend(args: argparse.Namespace) -> int:
    from app.db.session import session_factory
    from app.factory.suspend import suspend_item, unsuspend_item

    ledger = Ledger(ledger_path(_root(args.root)))
    with session_factory(args.database_url)() as session:
        act = unsuspend_item if args.undo else suspend_item
        done = act(session, args.item, args.reason, ledger)
        session.commit()
    print(
        ("un" if args.undo else "") + ("suspended " if done else "nothing to do for ") + args.item
    )
    return 0 if done else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m app.factory")
    parser.add_argument("--root", type=Path, default=None, help="content folder")
    sub = parser.add_subparsers(dest="command", required=True)

    def with_index(p: argparse.ArgumentParser) -> None:
        p.add_argument("--reference-index", type=Path, default=None)
        p.add_argument("--no-reference-index", action="store_true")

    certify = sub.add_parser("certify", help="certify a template over its whole parameter box")
    certify.add_argument("template", type=Path)
    certify.add_argument("--seed", type=int, default=0)
    certify.add_argument("--max-exhaustive", type=int, default=kernel.certify.MAX_EXHAUSTIVE)
    with_index(certify)
    certify.set_defaults(run=cmd_certify)

    st = sub.add_parser("stamp", help="the only writer of tier A: build, verify, stamp items")
    st.add_argument("template", type=Path)
    st.add_argument("--count", type=int, default=10)
    st.add_argument("--seed", type=int, default=0)
    with_index(st)
    st.set_defaults(run=cmd_stamp)

    aud = sub.add_parser("audit-sample", help="list a random and a PPS sample of stamped items")
    aud.add_argument("--rate", type=float, default=0.02)
    aud.add_argument("--n", type=int, default=0)
    aud.add_argument("--minimum", type=int, default=1)
    aud.add_argument("--seed", type=int, default=0)
    aud.add_argument("--exposure", type=Path, default=None, help="JSON {item_id: times shown}")
    aud.set_defaults(run=cmd_audit_sample)

    sub.add_parser("report", help="counts per chapter and per checker").set_defaults(run=cmd_report)
    sub.add_parser("ledger-verify", help="check the hash chain").set_defaults(run=cmd_ledger_verify)

    susp = sub.add_parser("suspend", help="switch an item off (or back on with --undo)")
    susp.add_argument("item")
    susp.add_argument("--reason", required=True)
    susp.add_argument("--undo", action="store_true")
    susp.add_argument("--database-url", default=None)
    susp.set_defaults(run=cmd_suspend)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.run(args))


if __name__ == "__main__":
    sys.exit(main())
