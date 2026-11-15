"""certify -> stamp -> audit -> report through the real CLI, in a temporary content folder."""

import copy
import json
from pathlib import Path

import pytest
import yaml

from app.content import validator
from app.content.ledger import Ledger, ledger_path
from app.content.schema import ContentBundle, Item
from app.content.signatures import item_content_hash
from app.content.verification import record_errors
from app.factory.cli import main
from app.factory.lanes.maths_quadratic import TEMPLATE

SMALL = copy.deepcopy(TEMPLATE)
SMALL["box"] = {"a": {"choices": [1, 2]}, "r1": {"min": -3, "max": 3}, "r2": {"min": -3, "max": 3}}


@pytest.fixture
def work(tmp_path: Path) -> tuple[Path, Path]:
    path = tmp_path / "tpl.yaml"
    path.write_text(yaml.safe_dump(SMALL), encoding="utf-8")
    return tmp_path / "content", path


def run(root: Path, *argv: str) -> int:
    return main(["--root", str(root), *argv])


def certify(root: Path, tpl: Path) -> int:
    return run(root, "certify", str(tpl), "--no-reference-index")


def test_certify_writes_certificate_and_ledger(work, capsys):
    root, tpl = work
    assert certify(root, tpl) == 0
    out = capsys.readouterr().out
    assert "CERTIFIED" in out and "failures 0" in out and "WARNING" in out
    stored = json.loads((root / "factory/certificates/TPL2.MATHS.QUAD.INT_ROOTS.json").read_text())
    assert stored["certificate"]["kind"] == "template" and len(stored["hash"]) == 64
    kinds = [e["kind"] for e in Ledger(ledger_path(root)).entries()]
    assert kinds == ["certificate_issued"]


def test_originality_index_is_required_unless_waived(work):
    root, tpl = work
    with pytest.raises(SystemExit):
        run(root, "certify", str(tpl))


def test_stamp_needs_a_current_certificate(work, capsys):
    root, tpl = work
    assert run(root, "stamp", str(tpl), "--no-reference-index") == 1  # never certified
    assert "run `certify` first" in capsys.readouterr().out
    assert certify(root, tpl) == 0
    changed = copy.deepcopy(SMALL)
    changed["syllabus"]["grade"] = 9
    tpl.write_text(yaml.safe_dump(changed), encoding="utf-8")
    assert run(root, "stamp", str(tpl), "--no-reference-index") == 1
    assert "changed since it was certified" in capsys.readouterr().out


def test_hand_edited_certificate_is_refused(work, capsys):
    root, tpl = work
    certify(root, tpl)
    cert = root / "factory/certificates/TPL2.MATHS.QUAD.INT_ROOTS.json"
    data = json.loads(cert.read_text())
    data["certificate"]["outcomes"]["ok"] = "999"
    cert.write_text(json.dumps(data))
    assert run(root, "stamp", str(tpl), "--no-reference-index") == 1
    assert "edited by hand" in capsys.readouterr().out


def test_stamped_items_are_valid_backed_and_logged(work, capsys):
    root, tpl = work
    certify(root, tpl)
    assert run(root, "stamp", str(tpl), "--count", "5", "--no-reference-index") == 0
    files = sorted((root / "items/factory/maths").glob("*.yaml"))
    assert len(files) == 5
    ledger = Ledger(ledger_path(root))
    assert ledger.verify() == [] and len(ledger.stamped_record_hashes()) == 5
    stems = set()
    for path in files:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        item = Item.model_validate(data)
        assert item.tier.value == "A" and item.status.value == "draft"
        assert item.verification.label == "calculation-checked"
        assert item.provenance.original is True and item.type.value == "mcq"
        assert (
            record_errors(
                item.verification.as_record(),
                item_hash=item_content_hash(item),
                stamped_hashes=ledger.stamped_record_hashes(),
            )
            == []
        )
        assert item.answer.sympy in {o.id for o in item.options} and item.answer.sympy != "key"
        stems.add(item.stem.en)
        assert "human" not in json.dumps(data["verification"]).lower()  # no reviewer claims
    assert len(stems) == 5  # the stamp loop never repeats a stem
    report = validator.ValidationReport(bundle=None)
    bundle = ContentBundle(
        skills=[], items=[Item.model_validate(yaml.safe_load(p.read_text())) for p in files],
        misconceptions=[], overlays=[], glossaries=[], checkpoint_forms=[],
    )  # fmt: skip
    validator._items(bundle, report)
    validator._stem_uniqueness(bundle, report)
    assert report.errors == []
    capsys.readouterr()


def test_report_audit_and_ledger_commands(work, capsys, tmp_path):
    root, tpl = work
    certify(root, tpl)
    run(root, "stamp", str(tpl), "--count", "6", "--no-reference-index")
    capsys.readouterr()
    assert run(root, "report") == 0
    out = capsys.readouterr().out
    assert "stamped items: 6" in out and "cbse.10.maths.quadratic: 6" in out
    assert "wellposed.predicates: 6 / 0 / 0" in out and "units.dimension: 0 / 0 / 6" in out
    assert "ledger: intact" in out
    assert run(root, "audit-sample", "--n", "3", "--seed", "5") == 0
    sample = json.loads(capsys.readouterr().out)
    assert sample["population"] == 6 and len(sample["random"]) == 3 and len(sample["pps"]) == 3
    exposure = tmp_path / "exposure.json"
    ids = sorted(sample["random"])
    exposure.write_text(json.dumps({ids[0]: 1000}))
    assert run(root, "audit-sample", "--n", "2", "--exposure", str(exposure)) == 0
    pps = json.loads(capsys.readouterr().out)["pps"]
    assert pps == [ids[0]]  # items nobody saw have weight zero and are never drawn
    assert run(root, "ledger-verify") == 0


def test_tampered_ledger_is_detected_and_blocks_appends(work, capsys):
    root, tpl = work
    certify(root, tpl)
    run(root, "stamp", str(tpl), "--count", "2", "--no-reference-index")
    path = ledger_path(root)
    path.write_text(path.read_text().replace("certificate_issued", "stamp_run", 1))
    capsys.readouterr()
    assert run(root, "ledger-verify") == 1
    assert "edited" in capsys.readouterr().out
    assert Ledger(path).stamped_record_hashes() == set()  # a broken chain backs nothing
    with pytest.raises(ValueError, match="broken ledger"):
        Ledger(path).append("stamped", "x", "h", {}, ts="t")
