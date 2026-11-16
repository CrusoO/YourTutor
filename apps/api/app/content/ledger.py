"""A tamper-evident, append-only, hash-chained ledger of factory events (JSON lines).

Each entry stores `prev_hash` and `this_hash` (sha256 of prev_hash plus the canonical entry
without this_hash). Editing, deleting or reordering any earlier line breaks every later hash and
`verify()` says where. It is evidence, not a secret: someone who can rewrite the whole file and
the git history can forge it, so it lives in version control and CI runs `ledger-verify`.
Event kinds: certificate_issued, stamp_run, stamped, suspended, unsuspended, audit_sample. No
student identifiers may enter a payload.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

GENESIS = "0" * 64
LEDGER_RELATIVE = Path("factory") / "ledger.jsonl"
KINDS = frozenset(
    {"certificate_issued", "stamp_run", "stamped", "suspended", "unsuspended", "audit_sample"}
)


def ledger_path(root: Path) -> Path:
    return root / LEDGER_RELATIVE


def _canonical(entry: dict[str, Any]) -> str:
    return json.dumps(entry, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _entry_hash(prev_hash: str, entry: dict[str, Any]) -> str:
    body = {k: v for k, v in entry.items() if k != "this_hash"}
    return hashlib.sha256((prev_hash + _canonical(body)).encode("ascii")).hexdigest()


@dataclass
class Ledger:
    path: Path

    def entries(self) -> list[dict[str, Any]]:
        if not self.path.is_file():
            return []
        out = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                out.append(json.loads(line))
        return out

    def verify(self) -> list[str]:
        """Problems found, empty when the chain is intact."""
        problems: list[str] = []
        prev = GENESIS
        try:
            entries = self.entries()
        except ValueError:
            return ["ledger is not valid JSON lines"]
        for index, entry in enumerate(entries, start=1):
            if entry.get("seq") != index:
                problems.append(f"entry {index}: sequence number is {entry.get('seq')}")
            if entry.get("prev_hash") != prev:
                problems.append(f"entry {index}: prev_hash does not match the entry before it")
            if entry.get("this_hash") != _entry_hash(str(entry.get("prev_hash")), entry):
                problems.append(f"entry {index}: contents do not match this_hash (edited)")
            if entry.get("kind") not in KINDS:
                problems.append(f"entry {index}: unknown kind {entry.get('kind')!r}")
            prev = str(entry.get("this_hash"))
        return problems

    def append(
        self, kind: str, subject_id: str, subject_hash: str, payload: dict[str, Any], *, ts: str
    ) -> dict[str, Any]:
        if kind not in KINDS:
            raise ValueError(f"unknown ledger kind {kind!r}")
        problems = self.verify()
        if problems:
            raise ValueError("refusing to append to a broken ledger: " + "; ".join(problems[:3]))
        entries = self.entries()
        prev = entries[-1]["this_hash"] if entries else GENESIS
        entry: dict[str, Any] = {
            "seq": len(entries) + 1,
            "ts": ts,
            "kind": kind,
            "subject_id": subject_id,
            "subject_hash": subject_hash,
            "payload": payload,
            "prev_hash": prev,
        }
        entry["this_hash"] = _entry_hash(prev, entry)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(_canonical(entry) + "\n")
        return entry

    def stamped_record_hashes(self) -> set[str]:
        """record_hash of every stamp in an intact ledger (empty if the chain is broken)."""
        if self.verify():
            return set()
        return {
            str(e["payload"]["record_hash"]) for e in self.entries() if e.get("kind") == "stamped"
        }

    def suspended_ids(self) -> set[str]:
        """Items whose latest suspension event is `suspended`."""
        state: dict[str, bool] = {}
        for e in self.entries():
            if e.get("kind") in ("suspended", "unsuspended"):
                state[str(e["subject_id"])] = e["kind"] == "suspended"
        return {k for k, v in state.items() if v}
