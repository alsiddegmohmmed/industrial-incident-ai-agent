# 01 — Product Specification

## 1. Purpose

The Industrial Incident AI Agent is a software-only system that investigates simulated operational incidents in an industrial environment.

The project is not intended to simulate an entire factory or build a complete IoT platform. The industrial domain exists to provide a realistic environment for learning and demonstrating AI engineering.

## 2. Problem statement

Operational systems produce telemetry, alerts, maintenance documentation, and historical incident records. Investigating an abnormal condition often requires combining information from several sources.

The system should allow an operator to ask a natural-language question such as:

> Why is motor-17 overheating?

The AI agent should gather relevant evidence through controlled tools, reason over that evidence, and return a structured diagnosis and recommended next actions.

## 3. Primary user

**Operations engineer / maintenance operator**

The user:

- receives or observes an incident;
- wants an explanation;
- needs evidence, not just a confident answer;
- may not know which telemetry or documentation to inspect;
- must remain responsible for consequential operational actions.

## 4. Primary user story

Given a simulated overheating incident for `motor-17`, when the operator asks:

```text
Why is motor-17 overheating?
```

the system should be able to:

1. identify the referenced device;
2. inspect current device state;
3. inspect relevant telemetry history;
4. inspect recent alerts;
5. inspect similar previous incidents when available;
6. retrieve relevant technical documentation when RAG is enabled;
7. produce a structured diagnosis;
8. identify the evidence used;
9. distinguish fact from inference;
10. state uncertainty when evidence is insufficient;
11. recommend the next action;
12. avoid executing consequential control actions without explicit authorization.

## 5. Product goals

### G-1 — Demonstrate AI application engineering

The project must exercise direct model integration, structured generation, tool use, grounding, evaluation, safety, and observability.

### G-2 — Remain software-only

The entire system must run on a developer laptop.

No physical device, sensor, microcontroller, PLC, Raspberry Pi, ESP32, or industrial hardware is required.

### G-3 — Remain usable without paid AI services

The project must have a zero-required-cost execution path.

A local/open model implementation should remain supported. Optional free-tier hosted providers may be used during experimentation but must not be architectural dependencies.

### G-4 — Be evaluation-driven

Changes to prompts, models, tool descriptions, retrieval strategies, and orchestration should be measured against repeatable evaluation cases.

### G-5 — Keep the scope AI-first

The project must not become primarily an IoT, frontend, infrastructure, or backend project.

## 6. Functional requirements

### FR-1 — Investigation request

The system shall accept an incident-investigation request in natural language.

### FR-2 — Device state tool

The agent shall be able to request the current known state for an identified device.

### FR-3 — Telemetry history tool

The agent shall be able to request historical telemetry for an identified device, metric, and time range.

### FR-4 — Alert history tool

The agent shall be able to inspect recent alerts for an identified device.

### FR-5 — Incident history tool

The agent shall be able to inspect relevant previous incidents.

### FR-6 — Technical-document retrieval

When RAG is enabled, the agent shall be able to retrieve relevant sections from technical documentation.

### FR-7 — Structured diagnosis

The final result shall use a validated schema.

A starting schema:

```json
{
  "device_id": "motor-17",
  "severity": "high",
  "summary": "Possible bearing degradation under high load",
  "observations": [],
  "inferences": [],
  "recommended_actions": [],
  "confidence": 0.82,
  "evidence_refs": []
}
```

### FR-8 — Insufficient evidence

The agent shall be able to explicitly report that available evidence is insufficient for a reliable diagnosis.

### FR-9 — Evidence attribution

Diagnostic claims should be traceable to telemetry, alerts, incident records, or retrieved documentation.

### FR-10 — Controlled actions

The initial versions shall not execute physical device actions.

Later versions may model consequential actions as proposals requiring human approval.

## 7. Non-functional requirements

### NFR-1 — Deterministic validation

All tool inputs and structured model outputs must be validated by application code.

### NFR-2 — Traceability

Agent steps, model calls, tool calls, retrieval results, latency, and failures should become observable as the project matures.

### NFR-3 — Replaceable model provider

Application logic should not be tightly coupled to one vendor.

### NFR-4 — Reproducible evaluation

Evaluation cases must be machine-readable and rerunnable.

### NFR-5 — Local development

The project must be runnable with local services through a documented developer setup.

## 8. Initial simulated domain

The first domain should be deliberately small.

### Devices

- `motor-17`
- `motor-21`
- `pump-04` only if needed later

### Starting telemetry fields

For motors:

- temperature
- vibration
- rpm
- load
- status

### Initial incident classes

1. normal operation
2. sustained overload
3. overheating
4. abnormal vibration
5. suspected bearing degradation
6. sensor stuck at a constant value
7. missing telemetry
8. conflicting telemetry
9. false alarm
10. insufficient evidence

## 9. Explicit non-goals for early versions

The following are not required before the AI core is proven:

- physical hardware;
- firmware;
- real industrial protocols;
- production PLC integration;
- complex MQTT infrastructure;
- multi-tenant SaaS;
- Kubernetes;
- microservices;
- sophisticated frontend;
- mobile app;
- real-time charts;
- multi-agent orchestration;
- voice interface;
- automated equipment control;
- large custom ML models.

## 10. Success criteria

The project is successful when it can demonstrate, with repeatable evidence, that:

1. an LLM can use controlled tools to gather incident evidence;
2. the system can ground answers in internal data and documentation;
3. model behavior is evaluated against a defined dataset;
4. unsafe or unauthorized actions are blocked by deterministic controls;
5. the system can be inspected through traces and metrics;
6. model/provider choices can be changed without rewriting the entire application.

## 11. Career outcome

The project should demonstrate an AI-engineering capability that is not already proven by ordinary backend work:

> Building a reliable, evaluated, tool-using AI system whose outputs are grounded in operational data and constrained by application-level safety controls.
