import os

import httpx
import pytest

from incident_agent.main import create_app


pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.skipif(
        os.getenv("RUN_OLLAMA_INTEGRATION") != "1",
        reason="Set RUN_OLLAMA_INTEGRATION=1 to run live local-model tests.",
    ),
]


@pytest.mark.parametrize(
    ("device_id", "operator_request"),
    [
        ("motor-17", "Why is motor-17 overheating?"),
        ("motor-21", "Is motor-21 operating normally?"),
        ("pump-04", "Why is pump-04 telemetry unavailable?"),
    ],
    ids=["overheating", "normal-operation", "missing-telemetry"],
)
async def test_live_local_model_returns_a_valid_diagnosis(
    device_id: str,
    operator_request: str,
) -> None:
    transport = httpx.ASGITransport(app=create_app())
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
        timeout=320,
    ) as client:
        response = await client.post(
            "/v1/investigations",
            json={"operator_request": operator_request},
        )

    assert response.status_code == 200, response.text
    diagnosis = response.json()["diagnosis"]
    assert diagnosis["device_id"] == device_id
    assert diagnosis["summary"]

    if device_id == "motor-17":
        assert diagnosis["severity"] in {"high", "critical"}
        assert diagnosis["observations"]
    elif device_id == "motor-21":
        assert diagnosis["severity"] == "low"
    else:
        assert diagnosis["severity"] == "unknown"
        assert diagnosis["confidence"] <= 0.5
        summary = diagnosis["summary"].lower()
        assert "insufficient" in summary or "no measurements" in summary
