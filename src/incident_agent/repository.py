import re
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from incident_agent.errors import DeviceNotFoundError, FixtureConfigurationError
from incident_agent.models import IncidentFixture


class FixtureRepository:
    def __init__(self, fixture_directory: Path) -> None:
        self._fixtures: dict[str, dict[str, Any]] = {}
        for path in sorted(fixture_directory.glob("*.json")):
            try:
                fixture = IncidentFixture.model_validate_json(
                    path.read_text(encoding="utf-8")
                )
            except (OSError, ValidationError) as exc:
                raise FixtureConfigurationError(
                    f"Invalid incident fixture: {path.name}"
                ) from exc

            if fixture.device_id in self._fixtures:
                raise FixtureConfigurationError(
                    f"Duplicate incident fixture for device: {fixture.device_id}"
                )
            self._fixtures[fixture.device_id] = fixture.model_dump(mode="json")

        if not self._fixtures:
            raise FixtureConfigurationError(
                f"No incident fixtures found in: {fixture_directory}"
            )

    def context_for_request(self, operator_request: str) -> dict[str, Any]:
        mentioned_ids = set(re.findall(r"\b[a-z]+-[0-9]+\b", operator_request.lower()))
        matched_ids = mentioned_ids.intersection(self._fixtures)
        if len(matched_ids) != 1:
            raise DeviceNotFoundError(
                "The request must identify exactly one known simulated device."
            )
        return self._fixtures[matched_ids.pop()]
