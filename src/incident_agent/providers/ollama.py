import json
from typing import Any

import httpx
from pydantic import ValidationError

from incident_agent.errors import ModelProviderError
from incident_agent.models import Diagnosis


SYSTEM_PROMPT = """You investigate simulated industrial incidents.
Use only the supplied incident context. Separate observations from inferences.
Never invent measurements. If evidence is insufficient, say so and reduce confidence.
Compare measurements with the supplied operating_limits before assigning severity.
Use deterministic_assessment.severity exactly and do not contradict its basis.
Do not exceed deterministic_assessment.confidence_cap. When severity is unknown,
state in the summary that evidence is insufficient to determine operational severity.
Every confidence value must be a decimal from 0.0 through 1.0, never a percentage.
Include at least one direct observation with an evidence_ref from the context.
Return only JSON matching the supplied schema. Do not propose or claim to execute
physical control actions. Evidence references must use IDs present in the context.
"""


class OllamaModelProvider:
    def __init__(
        self,
        base_url: str,
        model: str,
        timeout_seconds: float,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._endpoint = f"{base_url}/api/chat"
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._transport = transport

    async def diagnose(
        self, operator_request: str, incident_context: dict[str, Any]
    ) -> Diagnosis:
        payload = {
            "model": self._model,
            "stream": False,
            "format": Diagnosis.model_json_schema(),
            "options": {"temperature": 0},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "operator_request": operator_request,
                            "incident_context": incident_context,
                        }
                    ),
                },
            ],
        }

        try:
            async with httpx.AsyncClient(
                timeout=self._timeout_seconds,
                transport=self._transport,
            ) as client:
                response = await client.post(self._endpoint, json=payload)
                response.raise_for_status()
                content = response.json()["message"]["content"]
            return Diagnosis.model_validate_json(content)
        except (httpx.HTTPError, KeyError, TypeError, ValueError, ValidationError) as exc:
            raise ModelProviderError(
                "The local model failed to return a valid diagnosis."
            ) from exc
