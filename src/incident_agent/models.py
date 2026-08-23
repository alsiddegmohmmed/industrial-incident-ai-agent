from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Severity(StrEnum):
    UNKNOWN = "unknown"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EvidenceSource(StrEnum):
    DEVICE_STATE = "device_state"
    TELEMETRY = "telemetry"
    ALERT = "alert"
    INCIDENT_HISTORY = "incident_history"
    MANUAL = "manual"


class ActionPriority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class Observation(StrictModel):
    statement: str = Field(min_length=1, max_length=500)
    source: EvidenceSource
    evidence_ref: str = Field(min_length=1, max_length=200)


class Inference(StrictModel):
    statement: str = Field(min_length=1, max_length=500)
    confidence: float = Field(ge=0.0, le=1.0)


class RecommendedAction(StrictModel):
    action: str = Field(min_length=1, max_length=500)
    priority: ActionPriority
    requires_approval: bool


class Diagnosis(StrictModel):
    device_id: str = Field(pattern=r"^[a-z]+-[0-9]+$")
    severity: Severity
    summary: str = Field(min_length=1, max_length=1000)
    observations: list[Observation] = Field(min_length=1, max_length=20)
    inferences: list[Inference] = Field(default_factory=list, max_length=10)
    recommended_actions: list[RecommendedAction] = Field(
        default_factory=list, max_length=10
    )
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_refs: list[str] = Field(default_factory=list, max_length=30)


class InvestigationRequest(StrictModel):
    operator_request: str = Field(min_length=3, max_length=2000)


class InvestigationResponse(StrictModel):
    investigation_id: str
    diagnosis: Diagnosis


class HealthResponse(StrictModel):
    status: str


class DeviceStatus(StrEnum):
    RUNNING = "running"
    STOPPED = "stopped"
    UNKNOWN = "unknown"


class DeviceState(StrictModel):
    status: DeviceStatus
    temperature_c: float | None
    vibration_mm_s: float | None = Field(ge=0)
    rpm: float | None = Field(ge=0)
    load_percent: float | None = Field(ge=0, le=100)
    evidence_ref: str = Field(min_length=1, max_length=200)


class TelemetrySample(StrictModel):
    timestamp: datetime
    temperature_c: float | None
    vibration_mm_s: float | None = Field(ge=0)
    load_percent: float | None = Field(ge=0, le=100)
    evidence_ref: str = Field(min_length=1, max_length=200)


class AlertRecord(StrictModel):
    code: str = Field(pattern=r"^[A-Z][A-Z0-9_]+$")
    timestamp: datetime
    evidence_ref: str = Field(min_length=1, max_length=200)


class MetricLimits(StrictModel):
    warning_above: float = Field(ge=0)
    critical_above: float = Field(ge=0)

    @model_validator(mode="after")
    def critical_must_exceed_warning(self) -> "MetricLimits":
        if self.critical_above <= self.warning_above:
            raise ValueError("critical_above must be greater than warning_above")
        return self


class OperatingLimits(StrictModel):
    temperature_c: MetricLimits
    vibration_mm_s: MetricLimits
    load_percent: MetricLimits


class IncidentFixture(StrictModel):
    device_id: str = Field(pattern=r"^[a-z]+-[0-9]+$")
    device_model: str = Field(min_length=1, max_length=100)
    operating_limits: OperatingLimits
    current_state: DeviceState
    recent_telemetry: list[TelemetrySample] = Field(max_length=100)
    recent_alerts: list[AlertRecord] = Field(max_length=50)
