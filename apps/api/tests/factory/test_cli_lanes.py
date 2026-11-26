"""The CLI must find every shipped lane from a template file alone (no helper script)."""

from pathlib import Path

import pytest

from app.factory.cli import _load_template

CONTENT = Path(__file__).resolve().parents[4] / "content" / "cbse" / "10"
CASES = [
    (CONTENT / "maths" / "templates" / "c10_ap_difference.yaml", "maths_c10"),
    (CONTENT / "physics" / "factory" / "templates" / "TPL2.PHY.ELEC.OHM_LAW.yaml", "physics"),
    (CONTENT / "chemistry" / "templates" / "tpl_chem_ph_conversion.yaml", "chemistry"),
]


@pytest.mark.parametrize(("path", "lane_name"), CASES)
def test_cli_resolves_shipped_lane(path: Path, lane_name: str) -> None:
    template, lane = _load_template(path)
    assert lane.name == lane_name
    assert template["lane"] == lane_name
