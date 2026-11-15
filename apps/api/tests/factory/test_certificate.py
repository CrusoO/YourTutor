import json

import pytest

from app.factory import kernel
from app.factory.kernel import certificate as cert_module
from app.factory.kernel import constants
from app.factory.kernel.certificate import (
    CertificationRefused,
    MethodResult,
    PluginVerdict,
    certificate_is_current,
    certificate_json_hash,
    mint_item_certificate,
    read_certificate,
)

SPEC = {"domain": "algebra", "kind": "polynomial", "lhs": [-6, -1, 1]}
ANSWER = {"roots": ["-2", "3"], "count": 2}
WITNESS = {"split": {"lead": 1, "roots": [[3, 1], [-2, 1]]}}
GOOD = MethodResult(
    "alg.closed", "1", "closed_form", {"roots": [-2, 3], "count": 2}, "quadratic_formula"
)

# The house constants table is pinned: editing any value changes this hash and stales every
# certificate. Update the pin only in a reviewed PR that says why.
PINNED_CONSTANTS_HASH = "c1b7f8c872cdeec17ea4188c93b26fb2093931619bc686415385297491023531"


def test_constants_table_is_pinned_and_sane():
    assert constants.constants_hash() == PINNED_CONSTANTS_HASH
    assert (
        constants.constant("g_earth").value == "9.8"
        and constants.constant("R_gas").value == "8.314"
    )
    assert constants.atomic_mass("Cl") == "35.5"
    with pytest.raises(Exception):  # noqa: B017,PT011
        constants.constant("g_moon")
    assert constants.CONSTANTS_REVIEWED is False  # honest: owner sign-off pending


def mint(**kw):
    return mint_item_certificate("ITEM.1", SPEC, ANSWER, WITNESS, **kw)


def test_only_the_kernel_can_mint():
    with pytest.raises(PermissionError):
        kernel.Certificate({"verdict": "accept"})
    with pytest.raises(PermissionError):
        kernel.Certificate({"verdict": "accept"}, _key=object())


def test_item_certificate_layout_and_hash():
    cert = mint(methods=[GOOD])
    body = cert.body
    assert body["schema"] == "cert/1" and body["kind"] == "item" and body["verdict"] == "accept"
    assert body["subject"]["domain"] == "algebra"
    assert body["independence_groups"] == ["closed_form", "kernel.exact"]
    assert body["kernel"]["constants_hash"] == PINNED_CONSTANTS_HASH
    assert set(body["kernel"]["checker_versions"]) == set(kernel.DOMAINS)
    assert [m["independence_group"] for m in body["methods"]] == ["kernel.exact", "closed_form"]
    assert certificate_json_hash(cert.to_json()) == cert.hash == mint(methods=[GOOD]).hash  # stable
    assert certificate_is_current(read_certificate(cert.to_json()))


def test_certificate_goes_stale_when_the_world_changes(monkeypatch):
    body = mint(methods=[GOOD]).body
    monkeypatch.setattr(cert_module, "CONSTANTS_VERSION", "other")
    assert not certificate_is_current(body)
    monkeypatch.undo()
    monkeypatch.setitem(cert_module.CHECKER_VERSIONS, "algebra", "2")
    assert not certificate_is_current(body)
    assert not certificate_is_current({**body, "verdict": "reject"})


def test_tampered_certificate_changes_hash():
    cert = mint(methods=[GOOD])
    forged = json.loads(cert.to_json())
    forged["subject"]["item_id"] = "OTHER"
    assert certificate_json_hash(json.dumps(forged)) != cert.hash
    assert read_certificate("not json") is None and read_certificate('{"schema":"x"}') is None


def test_kernel_rejection_means_no_certificate():
    with pytest.raises(CertificationRefused) as err:
        mint_item_certificate("I", SPEC, {"roots": [3, 5]}, WITNESS, methods=[GOOD])
    assert "kernel:" in err.value.reasons[0]


def test_disagreeing_method_is_never_outvoted():
    ok2 = MethodResult("m2", "1", "enumeration", ANSWER)
    bad = MethodResult("bad", "1", "sympy", {"roots": [-2, 4], "count": 2})
    with pytest.raises(CertificationRefused) as err:
        mint(methods=[GOOD, ok2, bad])  # two agree, one dissents: still refused
    assert err.value.reasons == ["method_disagreement:bad"]


def test_independence_is_required():
    with pytest.raises(CertificationRefused) as err:
        mint()  # kernel alone is one group
    assert "not_enough_independent_groups" in err.value.reasons[0]
    fake = MethodResult("fake", "1", "kernel.exact", ANSWER)
    with pytest.raises(CertificationRefused):
        mint(methods=[fake])  # a plugin cannot borrow the kernel's group
    assert mint(methods=[GOOD], min_groups=2)


def test_plugins_can_only_add_rejections():
    assert mint(methods=[GOOD], plugins=[PluginVerdict("hypothesis", True)])
    with pytest.raises(CertificationRefused) as err:
        mint(methods=[GOOD], plugins=[PluginVerdict("z3", False, "unknown")])
    assert err.value.reasons == ["plugin_rejected:z3:unknown"]
    # a passing plugin cannot rescue a kernel rejection
    with pytest.raises(CertificationRefused):
        mint_item_certificate(
            "I", SPEC, {"roots": [9]}, WITNESS, methods=[GOOD], plugins=[PluginVerdict("p", True)]
        )


def test_unreadable_method_answer_is_refused():
    with pytest.raises(CertificationRefused):
        mint(methods=[MethodResult("f", "1", "float", {"roots": [0.5]})])
