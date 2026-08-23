import asyncio
import json
from pathlib import Path
from typing import Any

import pytest

from incident_agent.agent import AgentLimits, AgentRuntime
from incident_agent.errors import AgentLoopError
from incident_agent.models import IncidentFixture
from incident_agent.providers.base import ChatResponse, ChatToolCall
from incident_agent.tools import ToolRegistry


def incident_tools() -> ToolRegistry:
    fixture = IncidentFixture.model_validate_json(
        (Path("data/incidents") / "motor-17-overheating.json").read_text()
    )
    return ToolRegistry(fixture)


def final_response() -> ChatResponse:
    return ChatResponse(
        content=json.dumps(
            {
                "device_id": "motor-17",
                "severity": "high",
                "summary": "The current state shows elevated operating measurements.",
                "observations": [
                    {
                        "statement": "The current device state was inspected.",
                        "source": "device_state",
                        "evidence_ref": "state:motor-17:2026-08-23T07:30:00Z",
                    }
                ],
                "inferences": [],
                "recommended_actions": [],
                "confidence": 0.8,
                "evidence_refs": ["state:motor-17:2026-08-23T07:30:00Z"],
            }
        )
    )


def invalid_reference_response() -> ChatResponse:
    response = json.loads(final_response().content)
    response["observations"][0]["evidence_ref"] = "invented:ref"
    response["evidence_refs"] = ["invented:ref"]
    return ChatResponse(content=json.dumps(response))


class SequencedProvider:
    def __init__(self, responses: list[ChatResponse]) -> None:
        self.responses = responses
        self.requests: list[tuple[list[dict[str, Any]], list[dict[str, Any]]]] = []

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        output_schema: dict[str, Any],
    ) -> ChatResponse:
        self.requests.append((messages, tools))
        return self.responses.pop(0)


@pytest.mark.asyncio
async def test_agent_selects_tools_without_receiving_full_fixture() -> None:
    provider = SequencedProvider(
        [
            ChatResponse(
                content="",
                tool_calls=(
                    ChatToolCall(
                        name="get_device_state",
                        arguments={"device_id": "motor-17"},
                    ),
                ),
            ),
            final_response(),
        ]
    )

    run = await AgentRuntime(provider).run(
        "Why is motor-17 overheating?",
        "motor-17",
        "ACM-400",
        incident_tools(),
    )

    initial_messages, schemas = provider.requests[0]
    assert "current_state" not in initial_messages[1]["content"]
    assert "recent_telemetry" not in initial_messages[1]["content"]
    assert {schema["function"]["name"] for schema in schemas} == {
        "get_device_state",
        "get_telemetry_history",
        "get_recent_alerts",
        "get_previous_incidents",
    }
    assert run.diagnosis.device_id == "motor-17"
    assert run.trace.turns == 2
    assert run.trace.termination_reason == "final_answer"
    assert run.trace.tool_calls[0].accepted is True
    assert "state:motor-17:2026-08-23T07:30:00Z" in run.evidence_refs
    assert any(message["role"] == "tool" for message in provider.requests[1][0])


@pytest.mark.asyncio
async def test_invalid_tool_call_is_rejected_and_traced() -> None:
    provider = SequencedProvider(
        [
            ChatResponse(
                content="",
                tool_calls=(
                    ChatToolCall(
                        name="get_device_state",
                        arguments={"device_id": "motor-21"},
                    ),
                ),
            ),
            ChatResponse(
                content="",
                tool_calls=(
                    ChatToolCall(
                        name="get_device_state",
                        arguments={"device_id": "motor-17"},
                    ),
                ),
            ),
            final_response(),
        ]
    )

    run = await AgentRuntime(provider).run(
        "Why is motor-17 overheating?",
        "motor-17",
        "ACM-400",
        incident_tools(),
    )

    assert [call.accepted for call in run.trace.tool_calls] == [False, True]
    assert "restricted" in (run.trace.tool_calls[0].error or "")
    assert any(
        message.get("content", "").find("tool_call_rejected") >= 0
        for message in provider.requests[1][0]
    )


@pytest.mark.asyncio
async def test_agent_requests_correction_for_unavailable_evidence_refs() -> None:
    provider = SequencedProvider(
        [
            ChatResponse(
                content="",
                tool_calls=(
                    ChatToolCall(
                        name="get_device_state",
                        arguments={"device_id": "motor-17"},
                    ),
                ),
            ),
            invalid_reference_response(),
            final_response(),
        ]
    )

    run = await AgentRuntime(provider).run(
        "Why is motor-17 overheating?",
        "motor-17",
        "ACM-400",
        incident_tools(),
    )

    assert run.trace.turns == 3
    assert run.diagnosis.observations[0].evidence_ref.startswith("state:motor-17")
    assert any(
        "not available" in message.get("content", "")
        for message in provider.requests[2][0]
    )


@pytest.mark.asyncio
async def test_agent_loop_stops_after_maximum_turns() -> None:
    provider = SequencedProvider(
        [
            ChatResponse(
                content="",
                tool_calls=(
                    ChatToolCall(
                        name="get_device_state",
                        arguments={"device_id": "motor-17"},
                    ),
                ),
            )
        ]
        * 3
    )

    with pytest.raises(AgentLoopError, match="model-turn limit"):
        await AgentRuntime(
            provider,
            AgentLimits(max_turns=2, max_tool_calls=4, timeout_seconds=10),
        ).run("Inspect motor-17", "motor-17", "ACM-400", incident_tools())


@pytest.mark.asyncio
async def test_agent_loop_stops_before_exceeding_tool_call_budget() -> None:
    provider = SequencedProvider(
        [
            ChatResponse(
                content="",
                tool_calls=(
                    ChatToolCall(
                        name="get_device_state",
                        arguments={"device_id": "motor-17"},
                    ),
                    ChatToolCall(
                        name="get_recent_alerts",
                        arguments={"device_id": "motor-17"},
                    ),
                ),
            )
        ]
    )

    with pytest.raises(AgentLoopError, match="tool-call limit"):
        await AgentRuntime(
            provider,
            AgentLimits(max_turns=2, max_tool_calls=1, timeout_seconds=10),
        ).run("Inspect motor-17", "motor-17", "ACM-400", incident_tools())


@pytest.mark.asyncio
async def test_agent_loop_enforces_overall_timeout() -> None:
    class SlowProvider:
        async def chat(
            self,
            messages: list[dict[str, Any]],
            tools: list[dict[str, Any]],
            output_schema: dict[str, Any],
        ) -> ChatResponse:
            await asyncio.sleep(0.05)
            return final_response()

    with pytest.raises(AgentLoopError, match="time limit"):
        await AgentRuntime(
            SlowProvider(),
            AgentLimits(max_turns=2, max_tool_calls=2, timeout_seconds=0.001),
        ).run("Inspect motor-17", "motor-17", "ACM-400", incident_tools())
