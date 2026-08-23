from uuid import uuid4

from incident_agent.agent import AgentLimits, AgentRuntime
from incident_agent.assessment import assess_severity
from incident_agent.errors import ModelProviderError
from incident_agent.models import (
    AgentTrace,
    IncidentFixture,
    InvestigationRequest,
    InvestigationResponse,
    Severity,
)
from incident_agent.providers.base import ModelProvider
from incident_agent.repository import FixtureRepository
from incident_agent.tools import ToolRegistry


def _collect_evidence_refs(value: object) -> set[str]:
    if isinstance(value, dict):
        refs = {
            field_value
            for field_name, field_value in value.items()
            if field_name == "evidence_ref" and isinstance(field_value, str)
        }
        for field_value in value.values():
            refs.update(_collect_evidence_refs(field_value))
        return refs
    if isinstance(value, list):
        refs: set[str] = set()
        for item in value:
            refs.update(_collect_evidence_refs(item))
        return refs
    return set()


class InvestigationService:
    def __init__(
        self,
        repository: FixtureRepository,
        provider: ModelProvider,
        limits: AgentLimits | None = None,
    ) -> None:
        self._repository = repository
        self._provider = provider
        self._limits = limits or AgentLimits()

    async def investigate(self, request: InvestigationRequest) -> InvestigationResponse:
        context = self._repository.context_for_request(request.operator_request)
        deterministic_assessment = assess_severity(context)
        provider_chat = getattr(self._provider, "chat", None)
        if callable(provider_chat):
            fixture = IncidentFixture.model_validate(context)
            run = await AgentRuntime(self._provider, self._limits).run(
                operator_request=request.operator_request,
                device_id=fixture.device_id,
                device_model=fixture.device_model,
                tools=ToolRegistry(fixture),
            )
            diagnosis = run.diagnosis
            trace = run.trace
            available_refs = set(run.evidence_refs)
        else:
            legacy_context = dict(context)
            legacy_context["deterministic_assessment"] = deterministic_assessment
            diagnosis = await self._provider.diagnose(
                request.operator_request, legacy_context
            )
            trace = AgentTrace(turns=0, termination_reason="legacy_provider")
            available_refs = _collect_evidence_refs(context)

        if diagnosis.device_id != context["device_id"]:
            raise ModelProviderError(
                "The model returned a diagnosis for a different device."
            )
        claimed_refs = set(diagnosis.evidence_refs)
        claimed_refs.update(item.evidence_ref for item in diagnosis.observations)
        if not claimed_refs.issubset(available_refs):
            raise ModelProviderError(
                "The model returned evidence references that are not in the incident context."
            )
        confidence_cap = deterministic_assessment["confidence_cap"]
        diagnosis = diagnosis.model_copy(
            update={
                "severity": Severity(deterministic_assessment["severity"]),
                "confidence": min(diagnosis.confidence, confidence_cap),
                "inferences": [
                    inference.model_copy(
                        update={
                            "confidence": min(inference.confidence, confidence_cap)
                        }
                    )
                    for inference in diagnosis.inferences
                ],
            }
        )
        return InvestigationResponse(
            investigation_id=str(uuid4()),
            diagnosis=diagnosis,
            trace=trace,
        )
