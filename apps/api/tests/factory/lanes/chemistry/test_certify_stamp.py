"""Certify small boxes, refuse a buggy lane, stamp through the real factory CLI, check faults."""

from __future__ import annotations

import copy
from pathlib import Path

import pytest
import yaml

from app.content.ledger import Ledger, ledger_path
from app.content.originality import ReferenceIndex
from app.content.schema import Item
from app.content.signatures import item_content_hash
from app.content.verification import record_errors
from app.factory.cli import main
from app.factory.faults import run_fault_injection
from app.factory.lanes.chemistry import catalog
from app.factory.lanes.chemistry.faultset import ALL_FAULTS, fault_cases
from app.factory.lanes.chemistry.lane import LANE, ChemistryLane
from app.factory.runner import certify_lane_template, template_hash

BY_ID = {t["id"]: t for t in catalog.template_records()}


def small(tid: str, per_axis: int = 3) -> dict:
    tpl = copy.deepcopy(BY_ID[tid])
    for name, spec in tpl["box"].items():
        if "choices" in spec and len(spec["choices"]) > per_axis:
            spec["choices"] = spec["choices"][:per_axis]
        elif "min" in spec and spec["max"] - spec["min"] + 1 > per_axis:
            spec["max"] = spec["min"] + per_axis - 1
    return tpl


@pytest.mark.parametrize(
    "tid",
    [
        "TPL.CHEM.BALANCE",
        "TPL.CHEM.REACTION_TYPE",
        "TPL.CHEM.PH_CONVERSION",
        "TPL.CHEM.NEUTRAL_MASS",
        "TPL.CHEM.SALT_FORMULA",
        "TPL.CHEM.REACTIVITY_ORDER",
        "TPL.CHEM.SERIES_FORMULA",
        "TPL.CHEM.NAME_ALKANE",
    ],
)
def test_small_box_is_certified_exhaustively(tid):
    tpl = small(tid, 12 if tid.endswith("NAME_ALKANE") else 3)
    report = certify_lane_template(LANE, tpl, reference_index=ReferenceIndex())
    assert report.kind == "exhaustive" and report.failures == 0, report.failure_samples[:2]
    assert report.ok > 0 and report.certificate is not None
    assert report.certificate.body["subject"]["template_hash"] == template_hash(LANE, tpl)


def test_a_lane_with_a_wrong_answer_cannot_be_certified():
    class Buggy(ChemistryLane):
        def render(self, template, params):
            ctx = super().render(template, params)
            wrong = dict(ctx.options[1]["value"])
            ctx.answer = wrong
            ctx.options[0]["value"] = wrong
            return ctx

    report = certify_lane_template(
        Buggy(), small("TPL.CHEM.PH_CONVERSION", 2), reference_index=ReferenceIndex()
    )
    assert report.certificate is None and report.failures > 0


def run(root: Path, *argv: str) -> int:
    return main(["--root", str(root), *argv])


@pytest.fixture(scope="module")
def stamped(tmp_path_factory):
    root = tmp_path_factory.mktemp("content")
    tpl = small("TPL.CHEM.ATOM_COUNT", 4)
    path = root / "templates" / "small.yaml"
    path.parent.mkdir(parents=True)
    path.write_text(yaml.safe_dump(tpl), encoding="utf-8")
    assert run(root, "certify", str(path), "--no-reference-index") == 0
    assert run(root, "stamp", str(path), "--count", "6", "--seed", "3", "--no-reference-index") == 0
    return root


def test_stamped_items_carry_a_verified_record_and_tier_a(stamped):
    files = sorted((stamped / "items" / "factory" / "chemistry").glob("*.yaml"))
    assert len(files) == 6
    ledger = Ledger(ledger_path(stamped))
    assert not ledger.verify()
    hashes = {e["payload"]["record_hash"] for e in ledger.entries() if e["kind"] == "stamped"}
    for path in files:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        item = Item.model_validate(data)
        assert item.tier == "A" and item.provenance.original is True and item.status == "draft"
        assert item.verification.label == "calculation-checked"
        assert not record_errors(
            data["verification"], item_hash=item_content_hash(item), stamped_hashes=hashes
        )
        assert item.type == "mcq" and len(item.options) == 4
        assert set(item.verification.methods_agreeing) >= {
            "chem.atoms_stack",
            "chem.atoms_expanded",
        }


@pytest.fixture(scope="module")
def report():
    return run_fault_injection(fault_cases(per_template=1, seed=3), ALL_FAULTS)


def test_baseline_items_are_all_accepted(report):
    assert report.baseline_failures == []


def test_every_fault_class_was_applied_and_every_mutant_was_killed(report):
    assert report.perfect, report.render()
    for fault in ALL_FAULTS:
        assert report.classes[fault.id].applied > 0, fault.id
