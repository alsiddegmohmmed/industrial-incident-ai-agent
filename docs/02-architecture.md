# 02 — Architecture

## 1. Architectural objective

The architecture should be the smallest system capable of teaching and demonstrating the target AI-engineering skills.

It should not imitate enterprise complexity for its own sake.

## 2. Initial logical architecture

```text
┌───────────────────────┐
│ Operator / API Client │
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│ FastAPI Application   │
│ Investigation API     │
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│ Agent Runtime         │
│ - context             │
│ - tool loop           │
│ - limits              │
│ - output validation   │
└──────┬─────────┬──────┘
       │         │
       │         └──────────────────┐
       ▼                            ▼
┌──────────────┐            ┌────────────────┐
│ Model        │            │ Controlled     │
│ Provider     │            │ Tool Layer     │
│ Abstraction  │            │                │
└──────────────┘            └───────┬────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              ▼                     ▼                     ▼
      ┌──────────────┐      ┌──────────────┐      ┌──────────────┐
      │ Telemetry    │      │ Incidents /  │      │ Retrieval    │
      │ Repository   │      │ Alerts       │      │ Service      │
      └──────┬───────┘      └──────┬───────┘      └──────┬───────┘
             │                     │                     │
             └──────────────┬──────┴─────────────────────┘
                            ▼
                 ┌─────────────────────┐
                 │ PostgreSQL          │
                 │ + pgvector later    │
                 └─────────────────────┘
```

## 3. Core components

### 3.1 Investigation API

Responsibilities:

- accept investigation requests;
- validate request data;
- create an investigation identifier;
- invoke the agent runtime;
- return validated results;
- expose health endpoints.

It should not contain model-specific logic.

### 3.2 Agent runtime

Responsibilities:

- build model context;
- expose allowed tools;
- run the model/tool loop;
- enforce iteration limits;
- validate tool calls;
- enforce timeouts;
- collect traces;
- produce the final structured result.

The first implementation should be simple enough to understand without an orchestration framework.

The v0.2 implementation is `incident_agent.agent.AgentRuntime`. It starts with
operator text plus device metadata, sends the four typed tool schemas to the
model, validates and executes each requested call through `ToolRegistry`, and
then validates the final `Diagnosis`. `AgentLimits` enforces the overall
timeout, maximum model turns, and maximum tool calls. `AgentTrace` records
accepted and rejected tool calls without exposing raw model internals.

### 3.3 Model provider abstraction

Responsibilities:

- provide a common interface for model calls;
- support structured output where available;
- support tool calling where available;
- normalize provider errors;
- expose token/usage metadata when available.

The application should be able to support:

- a local/open-weight model;
- an optional free-tier hosted model.

Paid access must not be required.

### 3.4 Controlled tool layer

The model never receives unrestricted database or shell access.

The v0.2 runtime exposes four read-only fixture-backed tools: state, telemetry
history, recent alerts, and previous incidents. Each registry is bound to one
device, so a model cannot use a valid-looking call to inspect another device.

Starting tool surface:

```text
get_device_state(device_id)
get_telemetry_history(device_id, metric, start_time, end_time)
get_recent_alerts(device_id, limit)
get_previous_incidents(device_id, limit)
search_equipment_manual(device_model, query)
```

Every tool must:

- use a typed schema;
- validate inputs;
- return bounded results;
- enforce authorization independently of model instructions;
- produce trace metadata.

### 3.5 Telemetry repository

Stores and retrieves synthetic telemetry.

The initial dataset may be loaded from JSON or generated programmatically.

MQTT is deliberately not required for the initial architecture.

### 3.6 Incident and alert repository

Stores:

- simulated incidents;
- ground-truth incident causes;
- operational alerts;
- incident history used by tools.

Ground truth used for evaluation must remain separate from information exposed to the agent.

### 3.7 Retrieval service

The v0.3 implementation loads Markdown manuals at application startup, splits
them into bounded sections, and stores sparse TF-IDF vectors in memory. The
manual-search tool applies a device-model filter, returns a small ranked result
set, and includes stable source metadata. This keeps the retrieval boundary
understandable before introducing PostgreSQL, pgvector, or an external embedding
service.

Responsibilities:

- ingest technical documentation;
- split documents into retrievable units;
- create local sparse vectors;
- keep the bounded index in memory;
- perform search;
- return bounded evidence with source metadata.

### 3.8 Evaluation runner

Not part of the user request path.

Responsibilities:

- load evaluation cases;
- run the system against them;
- score deterministic metrics;
- optionally invoke model-based judges;
- store results;
- compare versions.

## 4. Data boundaries

Separate:

### Agent-visible data

- telemetry;
- alerts;
- historical incidents;
- technical manuals.

### Evaluation-only ground truth

- actual simulated failure cause;
- expected tools;
- acceptable diagnoses;
- expected abstention behavior;
- prohibited actions.

The agent must never receive evaluation ground truth in normal execution.

## 5. Trust boundaries

```text
User input                     UNTRUSTED
Retrieved document content     UNTRUSTED
Model output                   UNTRUSTED
Model tool request             UNTRUSTED
Tool implementation            TRUSTED APPLICATION CODE
Database constraints           TRUSTED ENFORCEMENT
Evaluation ground truth        INTERNAL / NOT AGENT-VISIBLE
```

## 6. Initial deployment model

Early development:

```text
Developer laptop
├── API process
├── local/open model OR free-tier provider
├── PostgreSQL container
└── optional observability containers later
```

This avoids unnecessary cloud work during the learning phase.

## 7. Architecture constraints

- No direct model-to-database access.
- No arbitrary SQL tool.
- No arbitrary shell execution.
- No production hardware.
- No requirement for MQTT in the first milestones.
- No frontend requirement before AI behavior is evaluated.
- No agent framework until the hand-built loop is understood.
- No multi-agent architecture without measured need.

## 8. Failure modes to design for

The architecture should eventually handle:

- model timeout;
- provider unavailable;
- malformed structured output;
- invalid tool arguments;
- nonexistent device;
- unavailable telemetry;
- empty retrieval result;
- contradictory evidence;
- tool timeout;
- repeated tool call;
- infinite agent loop;
- context growth;
- model hallucination;
- prompt injection in retrieved documents.

## 9. Future evolution

Only when justified:

```text
JSON synthetic data
    ↓
PostgreSQL
    ↓
RAG / pgvector
    ↓
Observability
    ↓
Optional MQTT simulation
    ↓
Optional anomaly detector
```

The architecture should evolve because a learning or product requirement requires it, not because the technology is fashionable.
