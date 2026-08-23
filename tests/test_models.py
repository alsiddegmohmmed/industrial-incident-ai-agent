import pytest
from pydantic import ValidationError

from incident_agent.models import Diagnosis


def test_diagnosis_rejects_confidence_above_one() -> None:
    with pytest.raises(ValidationError):
        Diagnosis.model_validate(
            {
                "device_id": "motor-17",
                "severity": "high",
                "summary": "Overheating",
                "confidence": 1.2,
            }
        )


def test_diagnosis_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        Diagnosis.model_validate(
            {
                "device_id": "motor-17",
                "severity": "high",
                "summary": "Overheating",
                "confidence": 0.8,
                "unsupported_field": True,
            }
        )
