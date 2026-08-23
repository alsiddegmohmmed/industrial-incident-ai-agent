from typing import Any, Protocol

from incident_agent.models import Diagnosis


class ModelProvider(Protocol):
    async def diagnose(
        self, operator_request: str, incident_context: dict[str, Any]
    ) -> Diagnosis:
        """Return a validated diagnosis for the supplied incident context."""
        ...
