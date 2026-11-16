"""Certify whole (small) boxes, refuse a buggy lane, and stamp through the real factory CLI."""

import json
from pathlib import Path

import pytest
import yaml

from app.content import validator
from app.content.ledger import Ledger, ledger_path
from app.content.originality import ReferenceIndex
from app.content.schema import Item
from app.content.signatures import item_content_hash
from app.content.verification import record_errors
from app.factory.cli import main
from app.factory.lanes.physics.content import template_path, write_content
from app.factory.lanes.physics.lane import LANE, PhysicsLane
from app.factory.runner import certify_lane_template, template_hash

from .helpers import small_template

SMALL = ["ELEC.OHM", "ELEC.SERIES", "ELEC.POWER", "LIGHT.MIRROR_FORMULA", "LIGHT.REFRACTIVE_INDEX"]


@pytest.mark.parametrize("model_id", SMALL)
def test_small_box_is_certified_exhaustively(model_id):
    tpl = small_template(model_id, per_axis=3)
    report = certify_lane_template(LANE, tpl, reference_index=ReferenceIndex())
    assert report.kind == "exhaustive" and report.failures == 0, report.failure_samples[:2]
    assert report.ok > 0 and report.certificate is not None
    assert report.certificate.body["subject"]["template_hash"] == template_hash(LANE, tpl)
    assert report.size == report.ok + report.skipped


def test_a_lane_with_a_wrong_answer_cannot_be_certified():
    class Buggy(PhysicsLane):
        def render(self, template, params):
            ctx = super().render(template, params)
            wrong = dict(ctx.options[1]["value"])  # key points at a wrong value everywhere
            ctx.answer = wrong
            ctx.options[0]["value"] = wrong
            return ctx

    tpl = small_template("ELEC.OHM", per_axis=2)
    report = certify_lane_template(Buggy(), tpl, reference_index=ReferenceIndex())
    assert report.certificate is None and report.failures > 0


def run(root: Path, *argv: str) -> int:
    return main(["--root", str(root), *argv])


@pytest.fixture(scope="module")
def stamped(tmp_path_factory):
    root = tmp_path_factory.mktemp("content")
    write_content(root)
    tpl = small_template("ELEC.OHM", per_axis=3)
    path = template_path(root, "TPL2.SMALL.OHM")
    tpl["id"] = "TPL2.SMALL.OHM"
    path.write_text(yaml.safe_dump(tpl), encoding="utf-8")
    assert run(root, "certify", str(path), "--no-reference-index") == 0
    assert run(root, "stamp", str(path), "--count", "6", "--seed", "3", "--no-reference-index") == 0
    return root


def test_stamped_items_carry_a_verified_record_and_tier_a(stamped):
    files = sorted((stamped / "items" / "factory" / "physics").glob("*.yaml"))
    assert len(files) == 6
    ledger = Ledger(ledger_path(stamped))
    assert not ledger.verify()
    hashes = {e["payload"]["record_hash"] for e in ledger.entries() if e["kind"] == "stamped"}
    for path in files:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        item = Item.model_validate(data)
        assert item.tier == "A" and item.provenance.original is True
        assert item.verification.label == "calculation-checked"
        assert not record_errors(
            data["verification"], item_hash=item_content_hash(item), stamped_hashes=hashes
        )
        assert item.type == "mcq" and len(item.options) == 4
        assert {m for m in item.verification.methods_agreeing} >= {
            "phys.closed_form",
            "phys.sympy_laws",
        }  # noqa: E501
        checks = {c["id"]: c["status"] for c in item.verification.checks}
        assert checks["stamp"] == "pass" and checks["verify.method_1"] == "pass"


def test_the_stamped_pack_passes_the_content_validator_checks(stamped):
    """Item-level validator checks. The whole-root validate also looks for a legacy template for
    every `template_id`, which factory templates are not (owner item, see the PR)."""
    bundle = validator.load_bundle(stamped)
    report = validator.ValidationReport(bundle=None)  # type: ignore[arg-type]
    for check in (
        validator._refs_and_cycles,
        validator._items,
        validator._stem_uniqueness,
        validator._hint_language,
        validator._language_quality,
        validator._bkt_params,
    ):
        check(bundle, report)
    assert not [e for e in report.errors if "distinct stems" not in e], report.errors[:3]
    assert len(bundle.items) == 6 and len(bundle.skills) == 35


def test_item_ids_are_unique_and_stems_differ(stamped):
    items = [yaml.safe_load(p.read_text(encoding="utf-8"))
             for p in (stamped / "items" / "factory" / "physics").glob("*.yaml")]  # fmt: skip
    assert len({i["id"] for i in items}) == len(items)
    assert len({i["stem"]["en"] for i in items}) == len(items)


def test_changing_the_template_makes_the_certificate_stale(stamped, capsys):
    path = template_path(stamped, "TPL2.SMALL.OHM")
    tpl = yaml.safe_load(path.read_text(encoding="utf-8"))
    tpl["syllabus"]["grade"] = 9
    other = path.with_name("changed.yaml")
    tpl["id"] = "TPL2.SMALL.OHM"
    other.write_text(yaml.safe_dump(tpl), encoding="utf-8")
    assert run(stamped, "stamp", str(other), "--no-reference-index") == 1
    assert "changed since it was certified" in capsys.readouterr().out
    cert = json.loads((stamped / "factory/certificates/TPL2.SMALL.OHM.json").read_text())
    assert cert["certificate"]["kind"] == "template"
