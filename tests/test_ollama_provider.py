import json

import httpx
import pytest

from incident_agent.errors import ModelProviderError
from incident_agent.providers.base import ChatToolCall
from incident_agent.providers.ollama import OllamaModelProvider


@pytest.mark.asyncio
async def test_provider_rejects_malformed_structured_output() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"message": {"content": "not-json"}})

    provider = OllamaModelProvider(
        base_url="http://ollama.test",
        model="test-model",
        timeout_seconds=1,
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(ModelProviderError):
        await provider.diagnose(
            "Why is motor-17 overheating?",
            {"device_id": "motor-17"},
        )


@pytest.mark.asyncio
async def test_provider_requests_schema_constrained_output() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert payload["stream"] is False
        assert payload["format"]["type"] == "object"
        assert "never a percentage" in payload["messages"][0]["content"]
        assert "operating_limits" in payload["messages"][0]["content"]
        assert "deterministic_assessment" in payload["messages"][0]["content"]
        assert "confidence_cap" in payload["messages"][0]["content"]
        assert "at least one direct observation" in payload["messages"][0]["content"]
        content = json.dumps(
            {
                "device_id": "motor-17",
                "severity": "high",
                "summary": "Temperature and vibration are elevated.",
                "observations": [
                    {
                        "statement": "Temperature is elevated.",
                        "source": "telemetry",
                        "evidence_ref": "telemetry:motor-17:current",
                    }
                ],
                "confidence": 0.8,
            }
        )
        return httpx.Response(200, json={"message": {"content": content}})

    provider = OllamaModelProvider(
        base_url="http://ollama.test",
        model="test-model",
        timeout_seconds=1,
        transport=httpx.MockTransport(handler),
    )

    diagnosis = await provider.diagnose(
        "Why is motor-17 overheating?",
        {"device_id": "motor-17"},
    )

    assert diagnosis.device_id == "motor-17"
    assert diagnosis.confidence == 0.8


@pytest.mark.asyncio
async def test_provider_parses_tool_calls_and_sends_tool_schemas() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert payload["stream"] is False
        assert "format" not in payload
        assert payload["tools"][0]["function"]["name"] == "get_device_state"
        assert "current_state" not in payload["messages"][1]["content"]
        return httpx.Response(
            200,
            json={
                "message": {
                    "content": "",
                    "tool_calls": [
                        {
                            "type": "function",
                            "function": {
                                "name": "get_device_state",
                                "arguments": {"device_id": "motor-17"},
                            },
                        }
                    ],
                }
            },
        )

    provider = OllamaModelProvider(
        base_url="http://ollama.test",
        model="test-model",
        timeout_seconds=1,
        transport=httpx.MockTransport(handler),
    )

    response = await provider.chat(
        messages=[
            {"role": "system", "content": "Use tools."},
            {"role": "user", "content": '{"device_id":"motor-17"}'},
        ],
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "get_device_state",
                    "description": "Read state",
                    "parameters": {"type": "object"},
                },
            }
        ],
        output_schema={"type": "object"},
    )

    assert response.content == ""
    assert response.tool_calls == (
        ChatToolCall(
            name="get_device_state",
            arguments={"device_id": "motor-17"},
        ),
    )
