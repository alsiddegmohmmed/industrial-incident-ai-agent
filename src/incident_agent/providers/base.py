from dataclasses import dataclass, field
from typing import Any, Protocol

from incident_agent.models import Diagnosis


class ModelProvider(Protocol):
    async def diagnose(
        self, operator_request: str, incident_context: dict[str, Any]
    ) -> Diagnosis:
        """Return a validated diagnosis for the supplied incident context."""
        ...


@dataclass(frozen=True)
class ChatToolCall:
    name: str
    arguments: object = field(default_factory=dict)


@dataclass(frozen=True)
class ChatResponse:
    content: str
    tool_calls: tuple[ChatToolCall, ...] = ()


class ChatModelProvider(Protocol):
    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        output_schema: dict[str, Any],
    ) -> ChatResponse:
        """Return one model turn, optionally containing tool calls."""
        ...
