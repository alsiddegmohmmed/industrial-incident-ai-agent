import json
from pathlib import Path

import pytest

from incident_agent.assessment import assess_severity
from incident_agent.repository import FixtureRepository


@pytest.mark.parametrize(
    ("device_id", "expected_severity"),
    [
        ("motor-17", "critical"),
        ("motor-21", "low"),
        ("pump-04", "unknown"),
    ],
)
def test_fixture_severity_is_deterministic(
    device_id: str,
    expected_severity: str,
) -> None:
    repository = FixtureRepository(Path("data/incidents"))
    context = repository.context_for_request(f"Inspect {device_id}")

    assessment = assess_severity(context)

    assert assessment["severity"] == expected_severity
    if expected_severity == "unknown":
        assert assessment["confidence_cap"] == 0.5


def test_warning_threshold_maps_to_high(tmp_path) -> None:
    fixture = json.loads(Path("data/incidents/motor-21-normal.json").read_text())
    fixture["device_id"] = "motor-22"
    fixture["current_state"]["temperature_c"] = 85.0
    (tmp_path / "warning.json").write_text(json.dumps(fixture), encoding="utf-8")
    repository = FixtureRepository(tmp_path)

    assessment = assess_severity(repository.context_for_request("Inspect motor-22"))

    assert assessment["severity"] == "high"
