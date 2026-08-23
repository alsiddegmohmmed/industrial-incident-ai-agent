from typing import Any

from incident_agent.models import Severity


METRICS = ("temperature_c", "vibration_mm_s", "load_percent")


def assess_severity(context: dict[str, Any]) -> dict[str, Any]:
    state = context["current_state"]
    limits = context["operating_limits"]
    available = {metric: state[metric] for metric in METRICS if state[metric] is not None}

    critical_metrics = [
        metric
        for metric, value in available.items()
        if value > limits[metric]["critical_above"]
    ]
    if critical_metrics:
        return {
            "severity": Severity.CRITICAL.value,
            "basis": f"Critical limits exceeded: {', '.join(critical_metrics)}.",
            "confidence_cap": 1.0,
        }

    warning_metrics = [
        metric
        for metric, value in available.items()
        if value > limits[metric]["warning_above"]
    ]
    if warning_metrics:
        return {
            "severity": Severity.HIGH.value,
            "basis": f"Warning limits exceeded: {', '.join(warning_metrics)}.",
            "confidence_cap": 1.0,
        }

    if len(available) != len(METRICS):
        return {
            "severity": Severity.UNKNOWN.value,
            "basis": "Operational severity cannot be determined because measurements are missing.",
            "confidence_cap": 0.5,
        }

    return {
        "severity": Severity.LOW.value,
        "basis": "All current measurements are within the supplied operating limits.",
        "confidence_cap": 1.0,
    }
