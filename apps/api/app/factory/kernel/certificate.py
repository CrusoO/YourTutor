"""Certificates. LCF style: only functions in this module can build a Certificate.

The Certificate constructor demands a module-private key, so generators, SymPy, Hypothesis, Z3,
round-trip checkers and the LLM can produce data and rejections but never an acceptance. A
certificate is canonical JSON (no timestamp, so it is byte-stable) plus its sha256.

Layout (cert/1), item kind:
  schema, kind, subject{item_id, domain, spec_hash, answer_hash, witness_hash},
  kernel{version, checker_versions{domain: v}, constants_version, constants_hash},
  methods[{id, version, independence_group, technique, answer_hash}], independence_groups[],
  plugins[{id}], verdict
Template kind adds box, outcomes and error_bound (see certify.py) in place of `methods`.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from app.factory.kernel.constants import CONSTANTS_VERSION, constants_hash
from app.factory.kernel.exact import Reject, canonical_json, chash
from app.factory.kernel.verify import CHECKER_VERSIONS, KERNEL_GROUP, verify

KERNEL_VERSION = "1"
CERT_SCHEMA = "cert/1"
_KEY = object()


class CertificationRefused(Exception):  # noqa: N818
    def __init__(self, reasons: Sequence[str]) -> None:
        super().__init__("; ".join(reasons))
        self.reasons = list(reasons)


@dataclass(frozen=True)
class MethodResult:
    """One independent computation of the answer from the spec alone (never from the witness)."""

    method_id: str
    version: str
    independence_group: str
    answer: Any
    technique: str = ""


@dataclass(frozen=True)
class PluginVerdict:
    """An untrusted check (SymPy, Hypothesis, Z3, round trip). It can only add a rejection."""

    plugin_id: str
    ok: bool
    reason: str = ""


class Certificate:
    __slots__ = ("_json", "_hash")

    def __init__(self, body: dict[str, Any], *, _key: object = None) -> None:
        if _key is not _KEY:
            raise PermissionError("only the kernel can mint a certificate")
        self._json = canonical_json(body)
        self._hash = chash(body)

    @property
    def hash(self) -> str:
        return self._hash

    @property
    def body(self) -> dict[str, Any]:
        return json.loads(self._json)  # type: ignore[no-any-return]

    def to_json(self) -> str:
        return self._json


def kernel_block() -> dict[str, Any]:
    return {
        "version": KERNEL_VERSION,
        "checker_versions": dict(sorted(CHECKER_VERSIONS.items())),
        "constants_version": CONSTANTS_VERSION,
        "constants_hash": constants_hash(),
    }


def read_certificate(text: str) -> dict[str, Any] | None:
    """Parse stored certificate JSON; None unless it is well formed (hash is checked by caller
    against the stored hash with `certificate_json_hash`)."""
    try:
        body = json.loads(text)
        return body if isinstance(body, dict) and body.get("schema") == CERT_SCHEMA else None
    except ValueError:
        return None


def certificate_json_hash(text: str) -> str | None:
    body = read_certificate(text)
    return chash(body) if body is not None else None


def certificate_is_current(body: dict[str, Any]) -> bool:
    """False once the kernel, a checker or the constants table changed since minting."""
    kernel = body.get("kernel", {})
    now = kernel_block()
    return all(kernel.get(k) == now[k] for k in now) and body.get("verdict") == "accept"


def mint_item_certificate(
    item_id: str,
    spec: dict,
    answer: dict,
    witness: dict,
    *,
    methods: Sequence[MethodResult] = (),
    plugins: Sequence[PluginVerdict] = (),
    min_groups: int = 2,
) -> Certificate:
    reasons: list[str] = []
    verdict = verify(spec, answer, witness)
    if not verdict.accepted:
        raise CertificationRefused([f"kernel:{verdict.code}:{verdict.detail}"])
    claimed = chash(answer)
    groups = {KERNEL_GROUP}
    method_rows: list[dict[str, str]] = [
        {
            "id": "kernel." + verdict.domain,
            "version": verdict.checker_version,
            "independence_group": KERNEL_GROUP,
            "technique": "exact_substitution",
            "answer_hash": claimed,
        }
    ]
    for m in methods:
        try:
            got = chash(m.answer)
        except Reject as rej:
            reasons.append(f"method_answer_unreadable:{m.method_id}:{rej.code}")
            continue
        if m.independence_group.startswith("kernel.") or not m.independence_group:
            reasons.append(f"bad_independence_group:{m.method_id}")
        if got != claimed:
            reasons.append(f"method_disagreement:{m.method_id}")  # never majority-voted away
        groups.add(m.independence_group)
        method_rows.append(
            {
                "id": m.method_id,
                "version": m.version,
                "independence_group": m.independence_group,
                "technique": m.technique,
                "answer_hash": got,
            }
        )
    reasons += [f"plugin_rejected:{p.plugin_id}:{p.reason}" for p in plugins if not p.ok]
    if len(groups) < min_groups:
        reasons.append(f"not_enough_independent_groups:{len(groups)}<{min_groups}")
    if reasons:
        raise CertificationRefused(reasons)
    body = {
        "schema": CERT_SCHEMA,
        "kind": "item",
        "subject": {
            "item_id": item_id,
            "domain": verdict.domain,
            "spec_hash": chash(spec),
            "answer_hash": claimed,
            "witness_hash": chash(witness),
        },
        "kernel": kernel_block(),
        "methods": method_rows,
        "independence_groups": sorted(groups),
        "plugins": [{"id": p.plugin_id} for p in sorted(plugins, key=lambda p: p.plugin_id)],
        "verdict": "accept",
    }
    return Certificate(body, _key=_KEY)


def _mint_template_certificate(
    template_id: str,
    template_hash: str,
    *,
    box: dict[str, Any],
    outcomes: dict[str, Any],
    error_bound: dict[str, Any],
    checker_versions: dict[str, str],
    fault_injection_report_id: str | None = None,
) -> Certificate:
    """Kernel-internal: certify.certify_template calls this after it has run the whole box."""
    if outcomes.get("failures") != 0 or outcomes.get("ok", 0) < 1:
        raise CertificationRefused(["template_has_failures_or_no_accepted_tuples"])
    body = {
        "schema": CERT_SCHEMA,
        "kind": "template",
        "subject": {"template_id": template_id, "template_hash": template_hash},
        "kernel": kernel_block(),
        "checker_versions": dict(sorted(checker_versions.items())),
        "box": box,
        "outcomes": outcomes,
        "error_bound": error_bound,
        "fault_injection_report_id": fault_injection_report_id,
        "verdict": "accept",
    }
    return Certificate(body, _key=_KEY)
