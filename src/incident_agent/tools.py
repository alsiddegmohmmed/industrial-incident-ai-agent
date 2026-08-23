"""Bounded, typed tools exposed to the investigation agent."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from pydantic import BaseModel, Field, ValidationError, model_validator

from incident_agent.errors import ToolCallRejected
from incident_agent.models import (
    IncidentFixture,
    StrictModel,
    TelemetryMetric,
    ToolName,
)
from incident_agent.retrieval import ManualRepository


class DeviceToolArguments(StrictModel):
    device_id: str = Field(pattern=r"^[a-z]+-[0-9]+$")


class TelemetryHistoryArguments(StrictModel):
    device_id: str = Field(pattern=r"^[a-z]+-[0-9]+$")
    metric: TelemetryMetric
    start_time: datetime | None = None
    end_time: datetime | None = None
    limit: int = Field(default=20, ge=1, le=20)

    @model_validator(mode="after")
    def validate_time_window(self) -> "TelemetryHistoryArguments":
        if (self.start_time is None) != (self.end_time is None):
            raise ValueError("start_time and end_time must be supplied together")
        if self.start_time is not None and self.end_time is not None:
            start = _as_utc(self.start_time)
            end = _as_utc(self.end_time)
            if end <= start:
                raise ValueError("end_time must be after start_time")
            if end - start > timedelta(hours=24):
                raise ValueError("telemetry time window cannot exceed 24 hours")
        return self


class LimitedDeviceToolArguments(DeviceToolArguments):
    limit: int = Field(default=10, ge=1, le=20)


class ManualSearchArguments(StrictModel):
    device_model: str = Field(
        pattern=r"^[A-Za-z0-9-]+$", min_length=2, max_length=50
    )
    query: str = Field(min_length=3, max_length=500)
    limit: int = Field(default=3, ge=1, le=5)


@dataclass(frozen=True)
class ToolDefinition:
    name: ToolName
    description: str
    arguments_model: type[BaseModel]
    handler: Callable[[BaseModel], dict[str, Any]]

    def schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name.value,
                "description": self.description,
                "parameters": self.arguments_model.model_json_schema(),
            },
        }


class ToolRegistry:
    """Validates and executes only the tools bound to one incident device."""

    def __init__(
        self,
        fixture: IncidentFixture,
        manual_repository: ManualRepository | None = None,
    ) -> None:
        self._fixture = fixture
        self._manual_repository = manual_repository
        self._definitions = self._build_definitions()

    def schemas(self) -> list[dict[str, Any]]:
        return [definition.schema() for definition in self._definitions.values()]

    def execute(
        self,
        tool_name: str,
        raw_arguments: object,
    ) -> dict[str, Any]:
        definition = self._definitions.get(tool_name)
        if definition is None:
            raise ToolCallRejected(f"Unknown tool: {tool_name}")

        arguments = _decode_arguments(raw_arguments)
        try:
            if len(json.dumps(arguments, separators=(",", ":"))) > 4_000:
                raise ToolCallRejected("Tool arguments exceed the allowed size.")
        except TypeError as exc:
            raise ToolCallRejected("Tool arguments must contain JSON values.") from exc
        try:
            parsed = definition.arguments_model.model_validate(arguments)
        except ValidationError as exc:
            raise ToolCallRejected(
                f"Invalid arguments for {tool_name}: {exc.errors()[0]['msg']}"
            ) from exc

        device_id = getattr(parsed, "device_id", None)
        device_model = getattr(parsed, "device_model", None)
        if device_id is not None and device_id != self._fixture.device_id:
            raise ToolCallRejected(
                f"Tool {tool_name} is restricted to {self._fixture.device_id}."
            )
        if device_model is not None and (
            device_model.upper() != self._fixture.device_model.upper()
        ):
            raise ToolCallRejected(
                f"Tool {tool_name} is restricted to {self._fixture.device_model}."
            )
        if device_id is None and device_model is None:
            raise ToolCallRejected("Tool arguments must identify a device.")

        result = definition.handler(parsed)
        encoded = json.dumps(result, separators=(",", ":"))
        if len(encoded) > 16_000:
            raise ToolCallRejected(f"Tool {tool_name} returned an oversized result.")
        return result

    def _build_definitions(self) -> dict[str, ToolDefinition]:
        definitions = {
            ToolName.GET_DEVICE_STATE.value: ToolDefinition(
                name=ToolName.GET_DEVICE_STATE,
                description=(
                    "Return the current bounded state of the requested device. "
                    "Use this before interpreting an incident."
                ),
                arguments_model=DeviceToolArguments,
                handler=self._get_device_state,
            ),
            ToolName.GET_TELEMETRY_HISTORY.value: ToolDefinition(
                name=ToolName.GET_TELEMETRY_HISTORY,
                description=(
                    "Return recent samples for exactly one metric. Use a bounded "
                    "time window no longer than 24 hours when one is needed."
                ),
                arguments_model=TelemetryHistoryArguments,
                handler=self._get_telemetry_history,
            ),
            ToolName.GET_RECENT_ALERTS.value: ToolDefinition(
                name=ToolName.GET_RECENT_ALERTS,
                description="Return the most recent bounded alert records for a device.",
                arguments_model=LimitedDeviceToolArguments,
                handler=self._get_recent_alerts,
            ),
            ToolName.GET_PREVIOUS_INCIDENTS.value: ToolDefinition(
                name=ToolName.GET_PREVIOUS_INCIDENTS,
                description=(
                    "Return bounded resolved incidents for the device. The result "
                    "may be empty when no prior incidents are recorded."
                ),
                arguments_model=LimitedDeviceToolArguments,
                handler=self._get_previous_incidents,
            ),
        }
        if self._manual_repository is not None:
            definitions[ToolName.SEARCH_EQUIPMENT_MANUAL.value] = ToolDefinition(
                name=ToolName.SEARCH_EQUIPMENT_MANUAL,
                description=(
                    "Search the bounded technical manual for the requested device "
                    "model. Use this when documented limits or procedures are "
                    "needed, and cite the returned evidence_ref."
                ),
                arguments_model=ManualSearchArguments,
                handler=self._search_equipment_manual,
            )
        return definitions

    def _get_device_state(self, arguments: BaseModel) -> dict[str, Any]:
        return {
            "device_id": self._fixture.device_id,
            "device_model": self._fixture.device_model,
            "current_state": self._fixture.current_state.model_dump(mode="json"),
            "operating_limits": self._fixture.operating_limits.model_dump(mode="json"),
        }

    def _get_telemetry_history(self, arguments: BaseModel) -> dict[str, Any]:
        parsed = arguments
        if not isinstance(parsed, TelemetryHistoryArguments):
            raise ToolCallRejected("Invalid telemetry arguments.")

        samples = []
        for sample in self._fixture.recent_telemetry:
            sample_time = _as_utc(sample.timestamp)
            if parsed.start_time and sample_time < _as_utc(parsed.start_time):
                continue
            if parsed.end_time and sample_time > _as_utc(parsed.end_time):
                continue
            samples.append(
                {
                    "timestamp": sample.timestamp.isoformat(),
                    "value": getattr(sample, parsed.metric.value),
                    "metric": parsed.metric.value,
                    "evidence_ref": sample.evidence_ref,
                }
            )
            if len(samples) >= parsed.limit:
                break

        return {
            "device_id": self._fixture.device_id,
            "metric": parsed.metric.value,
            "samples": samples,
            "sample_count": len(samples),
        }

    def _get_recent_alerts(self, arguments: BaseModel) -> dict[str, Any]:
        parsed = arguments
        if not isinstance(parsed, LimitedDeviceToolArguments):
            raise ToolCallRejected("Invalid alert arguments.")
        alerts = [
            alert.model_dump(mode="json")
            for alert in self._fixture.recent_alerts[: parsed.limit]
        ]
        return {
            "device_id": self._fixture.device_id,
            "alerts": alerts,
            "alert_count": len(alerts),
        }

    def _get_previous_incidents(self, arguments: BaseModel) -> dict[str, Any]:
        parsed = arguments
        if not isinstance(parsed, LimitedDeviceToolArguments):
            raise ToolCallRejected("Invalid incident-history arguments.")
        incidents = [
            incident.model_dump(mode="json")
            for incident in self._fixture.incident_history[: parsed.limit]
        ]
        return {
            "device_id": self._fixture.device_id,
            "incidents": incidents,
            "incident_count": len(incidents),
        }

    def _search_equipment_manual(self, arguments: BaseModel) -> dict[str, Any]:
        parsed = arguments
        if not isinstance(parsed, ManualSearchArguments):
            raise ToolCallRejected("Invalid manual-search arguments.")
        if self._manual_repository is None:
            raise ToolCallRejected("The manual repository is unavailable.")
        results = self._manual_repository.search(
            parsed.device_model,
            parsed.query,
            limit=parsed.limit,
        )
        return {
            "device_id": self._fixture.device_id,
            "device_model": self._fixture.device_model,
            "query": parsed.query,
            "results": [
                {
                    "evidence_ref": result.chunk.evidence_ref,
                    "source": "manual",
                    "chunk_id": result.chunk.chunk_id,
                    "title": result.chunk.title,
                    "source_ref": result.chunk.source_ref,
                    "excerpt": result.chunk.text,
                    "score": round(result.score, 4),
                }
                for result in results
            ],
            "result_count": len(results),
        }


def _decode_arguments(raw_arguments: object) -> dict[str, Any]:
    if isinstance(raw_arguments, str):
        try:
            raw_arguments = json.loads(raw_arguments)
        except json.JSONDecodeError as exc:
            raise ToolCallRejected("Tool arguments must be valid JSON.") from exc
    if not isinstance(raw_arguments, dict):
        raise ToolCallRejected("Tool arguments must be a JSON object.")
    return raw_arguments


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
