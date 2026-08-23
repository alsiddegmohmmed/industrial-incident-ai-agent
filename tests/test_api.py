from typing import Any

import httpx
import pytest

from incident_agent.errors import ModelProviderError
from incident_agent.main import create_app
from incident_agent.models import Diagnosis


pytestmark = pytest.mark.asyncio


class FakeProvider:
    async def diagnose(
        self, operator_request: str, incident_context: dict[str, Any]
    ) -> Diagnosis:
        device_id = incident_context["device_id"]
        is_missing = not incident_context["recent_telemetry"]
        return Diagnosis.model_validate(
            {
                "device_id": device_id,
                "severity": "medium" if is_missing else "low",
                "summary": (
                    "Insufficient telemetry for a reliable diagnosis."
                    if is_missing
                    else "Fixture evidence was reviewed."
                ),
                "observations": [
                    {
                        "statement": "The current device state was inspected.",
                        "source": "device_state",
                        "evidence_ref": incident_context["current_state"]["evidence_ref"],
                    }
                ],
                "inferences": [],
                "recommended_actions": [],
                "confidence": 0.2 if is_missing else 0.8,
                "evidence_refs": [],
            }
        )


class FailingProvider:
    async def diagnose(
        self, operator_request: str, incident_context: dict[str, Any]
    ) -> Diagnosis:
        raise ModelProviderError("The local model is unavailable.")


class WrongDeviceProvider:
    async def diagnose(
        self, operator_request: str, incident_context: dict[str, Any]
    ) -> Diagnosis:
        return Diagnosis(
            device_id="motor-21",
            severity="low",
            summary="Wrong device",
            observations=[
                {
                    "statement": "The current device state was inspected.",
                    "source": "device_state",
                    "evidence_ref": incident_context["current_state"]["evidence_ref"],
                }
            ],
            confidence=0.1,
        )


class InventedEvidenceProvider:
    async def diagnose(
        self, operator_request: str, incident_context: dict[str, Any]
    ) -> Diagnosis:
        return Diagnosis(
            device_id=incident_context["device_id"],
            severity="high",
            summary="Unsupported claim",
            observations=[
                {
                    "statement": "An unsupported measurement was observed.",
                    "source": "telemetry",
                    "evidence_ref": "telemetry:motor-17:invented",
                }
            ],
            confidence=0.9,
        )


class OverconfidentMissingEvidenceProvider:
    async def diagnose(
        self, operator_request: str, incident_context: dict[str, Any]
    ) -> Diagnosis:
        return Diagnosis(
            device_id=incident_context["device_id"],
            severity="critical",
            summary="Insufficient evidence to determine operational severity.",
            observations=[
                {
                    "statement": "Telemetry is unavailable.",
                    "source": "alert",
                    "evidence_ref": incident_context["recent_alerts"][0][
                        "evidence_ref"
                    ],
                }
            ],
            inferences=[
                {
                    "statement": "A sensor or communication fault is possible.",
                    "confidence": 1.0,
                }
            ],
            confidence=1.0,
        )


@pytest.mark.parametrize("device_id", ["motor-17", "motor-21", "pump-04"])
async def test_investigation_runs_for_each_initial_fixture(device_id: str) -> None:
    transport = httpx.ASGITransport(app=create_app(FakeProvider()))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/v1/investigations",
            json={"operator_request": f"What is happening with {device_id}?"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["diagnosis"]["device_id"] == device_id
    assert payload["investigation_id"]


async def test_unknown_device_is_rejected_before_model_call() -> None:
    transport = httpx.ASGITransport(app=create_app(FakeProvider()))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/v1/investigations",
            json={"operator_request": "Why is motor-999 overheating?"},
        )

    assert response.status_code == 422
    assert "exactly one known" in response.json()["detail"]


async def test_model_failure_returns_service_unavailable() -> None:
    transport = httpx.ASGITransport(app=create_app(FailingProvider()))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/v1/investigations",
            json={"operator_request": "Why is motor-17 overheating?"},
        )

    assert response.status_code == 503
    assert response.json()["detail"] == "The local model is unavailable."


async def test_model_cannot_return_a_different_device() -> None:
    transport = httpx.ASGITransport(app=create_app(WrongDeviceProvider()))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/v1/investigations",
            json={"operator_request": "Why is motor-17 overheating?"},
        )

    assert response.status_code == 503
    assert "different device" in response.json()["detail"]


async def test_model_cannot_invent_evidence_references() -> None:
    transport = httpx.ASGITransport(app=create_app(InventedEvidenceProvider()))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/v1/investigations",
            json={"operator_request": "Why is motor-17 overheating?"},
        )

    assert response.status_code == 503
    assert "not in the incident context" in response.json()["detail"]


async def test_missing_measurements_cap_model_confidence() -> None:
    transport = httpx.ASGITransport(
        app=create_app(OverconfidentMissingEvidenceProvider())
    )
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/v1/investigations",
            json={"operator_request": "Why is pump-04 telemetry unavailable?"},
        )

    assert response.status_code == 200
    diagnosis = response.json()["diagnosis"]
    assert diagnosis["severity"] == "unknown"
    assert diagnosis["confidence"] == 0.5
    assert diagnosis["inferences"][0]["confidence"] == 0.5


async def test_health_endpoint() -> None:
    transport = httpx.ASGITransport(app=create_app(FakeProvider()))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
