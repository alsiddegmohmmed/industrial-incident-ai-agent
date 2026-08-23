from pathlib import Path

import pytest

from incident_agent.errors import ToolCallRejected
from incident_agent.models import IncidentFixture
from incident_agent.retrieval import ManualRepository
from incident_agent.tools import ToolRegistry


def registry_for(device_id: str = "motor-17") -> ToolRegistry:
    fixture_name = "overheating" if device_id == "motor-17" else "normal"
    path = Path("data/incidents") / f"{device_id}-{fixture_name}.json"
    return ToolRegistry(IncidentFixture.model_validate_json(path.read_text()))


def manual_registry_for(device_id: str = "motor-17") -> ToolRegistry:
    fixture_name = "overheating" if device_id == "motor-17" else "normal"
    path = Path("data/incidents") / f"{device_id}-{fixture_name}.json"
    return ToolRegistry(
        IncidentFixture.model_validate_json(path.read_text()),
        ManualRepository(Path("data/manuals")),
    )


def test_tool_schemas_expose_only_the_v02_read_tools() -> None:
    registry = registry_for()

    names = [schema["function"]["name"] for schema in registry.schemas()]

    assert names == [
        "get_device_state",
        "get_telemetry_history",
        "get_recent_alerts",
        "get_previous_incidents",
    ]
    assert all(schema["type"] == "function" for schema in registry.schemas())


def test_device_state_tool_returns_bounded_state_and_limits() -> None:
    result = registry_for().execute(
        "get_device_state",
        {"device_id": "motor-17"},
    )

    assert result["device_id"] == "motor-17"
    assert result["current_state"]["evidence_ref"].startswith("state:motor-17")
    assert "recent_telemetry" not in result


def test_telemetry_tool_filters_metric_and_time_window() -> None:
    result = registry_for().execute(
        "get_telemetry_history",
        {
            "device_id": "motor-17",
            "metric": "temperature_c",
            "start_time": "2026-08-23T07:20:00Z",
            "end_time": "2026-08-23T07:40:00Z",
        },
    )

    assert result["metric"] == "temperature_c"
    assert [sample["value"] for sample in result["samples"]] == [91.2]
    assert set(result["samples"][0]) == {
        "timestamp",
        "value",
        "metric",
        "evidence_ref",
    }


@pytest.mark.parametrize(
    "arguments",
    [
        {"device_id": "motor-21"},
        {"device_id": "motor-17", "unexpected": True},
        {
            "device_id": "motor-17",
            "metric": "temperature_c",
            "start_time": "2026-08-20T00:00:00Z",
            "end_time": "2026-08-23T00:00:00Z",
        },
    ],
)
def test_tool_arguments_are_rejected_before_execution(arguments: dict[str, object]) -> None:
    tool_name = (
        "get_device_state" if "metric" not in arguments else "get_telemetry_history"
    )
    with pytest.raises(ToolCallRejected):
        registry_for().execute(tool_name, arguments)


def test_tool_rejects_unknown_tool_and_invalid_json_arguments() -> None:
    registry = registry_for()

    with pytest.raises(ToolCallRejected, match="Unknown tool"):
        registry.execute("run_shell", {})
    with pytest.raises(ToolCallRejected, match="valid JSON"):
        registry.execute("get_device_state", "not-json")


def test_alert_and_incident_history_tools_are_bounded() -> None:
    registry = registry_for()

    alerts = registry.execute(
        "get_recent_alerts", {"device_id": "motor-17", "limit": 1}
    )
    incidents = registry.execute(
        "get_previous_incidents", {"device_id": "motor-17", "limit": 1}
    )

    assert alerts["alert_count"] == 1
    assert incidents["incident_count"] == 1
    assert incidents["incidents"][0]["evidence_ref"] == "incident:motor-17:2026-07-15"


def test_manual_search_returns_ranked_citations_and_source_metadata() -> None:
    registry = manual_registry_for()

    result = registry.execute(
        "search_equipment_manual",
        {
            "device_model": "ACM-400",
            "query": "What does rising vibration and temperature indicate?",
            "limit": 2,
        },
    )

    assert result["result_count"] >= 1
    first = result["results"][0]
    assert first["evidence_ref"].startswith("manual:acm-400:")
    assert first["source_ref"].startswith("ACM-400.md#")
    assert "vibration" in first["excerpt"].lower()
    assert first["score"] > 0


def test_manual_search_is_bound_to_fixture_model() -> None:
    with pytest.raises(ToolCallRejected, match="restricted"):
        manual_registry_for().execute(
            "search_equipment_manual",
            {"device_model": "PMP-200", "query": "telemetry availability"},
        )
