import json

import pytest

from incident_agent.errors import DeviceNotFoundError, FixtureConfigurationError
from incident_agent.repository import FixtureRepository


def valid_fixture(device_id: str = "motor-17") -> dict[str, object]:
    return {
        "device_id": device_id,
        "device_model": "ACM-400",
        "operating_limits": {
            "temperature_c": {"warning_above": 80.0, "critical_above": 90.0},
            "vibration_mm_s": {"warning_above": 4.5, "critical_above": 7.1},
            "load_percent": {"warning_above": 90.0, "critical_above": 99.0},
        },
        "current_state": {
            "status": "running",
            "temperature_c": 70.0,
            "vibration_mm_s": 2.0,
            "rpm": 1400,
            "load_percent": 60.0,
            "evidence_ref": f"state:{device_id}:current",
        },
        "recent_telemetry": [],
        "recent_alerts": [],
    }


def test_repository_rejects_malformed_fixture(tmp_path) -> None:
    fixture = valid_fixture()
    fixture["current_state"]["load_percent"] = 140.0  # type: ignore[index]
    (tmp_path / "invalid.json").write_text(json.dumps(fixture), encoding="utf-8")

    with pytest.raises(FixtureConfigurationError, match="invalid.json"):
        FixtureRepository(tmp_path)


def test_repository_rejects_duplicate_device_ids(tmp_path) -> None:
    fixture = json.dumps(valid_fixture())
    (tmp_path / "first.json").write_text(fixture, encoding="utf-8")
    (tmp_path / "second.json").write_text(fixture, encoding="utf-8")

    with pytest.raises(FixtureConfigurationError, match="Duplicate.*motor-17"):
        FixtureRepository(tmp_path)


def test_repository_rejects_empty_fixture_directory(tmp_path) -> None:
    with pytest.raises(FixtureConfigurationError, match="No incident fixtures"):
        FixtureRepository(tmp_path)


def test_repository_requires_exactly_one_known_device(tmp_path) -> None:
    (tmp_path / "motor-17.json").write_text(
        json.dumps(valid_fixture("motor-17")), encoding="utf-8"
    )
    (tmp_path / "motor-21.json").write_text(
        json.dumps(valid_fixture("motor-21")), encoding="utf-8"
    )
    repository = FixtureRepository(tmp_path)

    with pytest.raises(DeviceNotFoundError):
        repository.context_for_request("Compare motor-17 with motor-21")
