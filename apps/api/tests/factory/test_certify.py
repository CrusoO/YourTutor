import pytest

from app.factory.kernel import OK, certify_template, clopper_pearson_upper, fail, skip
from app.factory.kernel.certify import box_size, required_sample

BOX = {"a": {"min": 1, "max": 3}, "b": {"choices": [10, 20]}}
VERSIONS = {"x": "1"}


def run(fn, **kw):
    return certify_template("T.1", "hash", BOX, fn, checker_versions=VERSIONS, **kw)


def test_sample_size_for_one_in_ten_thousand():
    assert required_sample() == 29956
    assert clopper_pearson_upper(0, 29956) <= 1e-4 < clopper_pearson_upper(0, 29900)
    assert clopper_pearson_upper(0, 100) == pytest.approx(1 - 0.05 ** (1 / 100), rel=1e-6)
    assert clopper_pearson_upper(1, 1000) == pytest.approx(0.00474, abs=1e-4)
    assert clopper_pearson_upper(5, 5) == 1.0
    with pytest.raises(ValueError):
        clopper_pearson_upper(2, 1)


def test_exhaustive_certificate_records_everything():
    seen = []

    def fn(p):
        seen.append(p)
        return skip("odd_a") if p["a"] == 2 else OK

    report = run(fn)
    assert box_size(BOX) == 6 and len(seen) == 6 and len({tuple(p.values()) for p in seen}) == 6
    assert (report.kind, report.ok, report.skipped, report.failures) == ("exhaustive", 4, 2, 0)
    body = report.certificate.body
    assert (
        body["box"]["size"] == "6"
        and body["box"]["tested"] == "6"
        and body["box"]["kind"] == "exhaustive"
    )
    assert body["outcomes"]["skip_reasons"] == {"odd_a": "2"}
    assert body["error_bound"]["kind"] == "exhaustive_zero" and body["checker_versions"] == {
        "x": "1"
    }
    assert run(fn).certificate.hash == report.certificate.hash  # byte-stable


def test_any_failure_blocks_the_certificate():
    report = run(lambda p: fail("wrong") if p == {"a": 3, "b": 20} else OK)
    assert report.certificate is None and report.failures == 1
    assert report.failure_samples == [{"params": {"a": 3, "b": 20}, "reason": "wrong"}]
    assert "failures:1" in report.refused


def test_exception_is_a_failure_not_a_pass():
    def boom(p):
        raise RuntimeError("x")

    report = run(boom)
    assert report.certificate is None and report.failures == 6
    assert report.failure_samples[0]["reason"] == "exception:RuntimeError"


def test_everything_skipped_is_not_certifiable():
    assert run(lambda p: skip("never")).certificate is None


def test_timeout_fails_closed():
    report = run(lambda p: OK, time_budget_s=-1)
    assert report.certificate is None and "timeout" in report.refused


def test_large_box_is_sampled_with_a_bound():
    box = {"x": {"min": 0, "max": 999}, "y": {"min": 0, "max": 999}}  # 1,000,000 tuples
    counted = []
    report = certify_template(
        "T.big", "h", box, lambda p: counted.append(1) or OK, checker_versions=VERSIONS, seed=7
    )
    assert report.kind == "sampled" and report.size == 1_000_000 and len(counted) == 29956
    assert report.upper_bound <= 1e-4 and report.certificate.body["box"]["seed"] == "7"
    assert report.certificate.body["error_bound"]["kind"] == "clopper_pearson_upper"
    again = certify_template("T.big", "h", box, lambda p: OK, checker_versions=VERSIONS, seed=7)
    assert again.certificate.hash == report.certificate.hash  # same seed, same sample


def test_sampled_failure_is_refused():
    box = {"x": {"min": 0, "max": 999}, "y": {"min": 0, "max": 999}}
    report = certify_template(
        "T.big", "h", box, lambda p: fail("bad") if p["x"] == 5 else OK, checker_versions=VERSIONS
    )
    assert report.certificate is None and report.failures > 0


@pytest.mark.parametrize(
    "bad", [{}, {"a": {"min": 5, "max": 1}}, {"a": {"choices": []}}, {"a": {"choices": [1, 1]}}]
)
def test_bad_boxes_raise(bad):
    with pytest.raises(Exception):  # noqa: B017,PT011
        certify_template("T", "h", bad, lambda p: OK, checker_versions=VERSIONS)
