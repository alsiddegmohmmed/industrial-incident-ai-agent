# 06 — Roadmap

## Roadmap principle

Each milestone exists to teach or demonstrate a specific AI-engineering capability.

Do not advance because the code "looks complete." Advance when the milestone's learning and verification criteria are met.

---

## v0.0 — Project contract

### Goal

Lock the scope before implementation.

### Deliverables

- README
- product specification
- architecture
- AI system design
- evaluation plan
- security model
- roadmap
- ADR process

### Exit criteria

- no-hardware constraint documented;
- no-paid-service requirement documented;
- AI-first scope documented;
- initial scenario defined;
- non-goals explicit.

---

## v0.1 — Structured LLM investigation

### AI skill

Direct model integration and structured generation.

### Build

- FastAPI project;
- one investigation endpoint;
- model-provider interface;
- one local or zero-required-cost model path;
- structured diagnosis schema;
- synthetic incident fixture loading;
- model timeout/error handling.

### Do not build

- RAG;
- agent framework;
- MQTT;
- frontend;
- multi-agent system.

### Exit criteria

- model returns schema-valid output;
- invalid output is handled safely;
- at least three simulated cases run end to end;
- unit tests cover validation and failure paths.

---

## v0.2 — Tool-using agent

### AI skill

Tool calling and agent-loop design.

### Build

- hand-written agent loop;
- device-state tool;
- telemetry-history tool;
- recent-alerts tool;
- incident-history tool;
- tool argument validation;
- maximum-turn and timeout controls.

### Exit criteria

- model can select tools rather than receiving all data upfront;
- invalid tool calls are rejected;
- infinite-loop protection exists;
- tool traces are recorded;
- evaluation cases test tool selection.

---

## v0.3 — Retrieval and grounding

### AI skill

RAG and context engineering.

### Build

- small technical-manual corpus;
- document ingestion;
- chunking;
- local embeddings;
- PostgreSQL + pgvector or equivalent local vector storage;
- manual-search tool;
- citations/source metadata.

### Exit criteria

- retrieval can be evaluated independently;
- diagnosis references retrieved evidence;
- at least one case requires documentation to answer correctly;
- irrelevant retrieval behavior is inspected.

---

## v0.4 — Evaluation-driven development

### AI skill

Disciplined eval/error-analysis loop.

### Build

- machine-readable eval cases;
- automated eval runner;
- deterministic scores;
- optional semantic judge;
- experiment configuration;
- stored results;
- regression comparison.

### Initial target

At least 10 strong cases before expanding to a larger dataset.

### Exit criteria

- prompt/model/retrieval changes can be compared;
- tool-use accuracy is measured;
- groundedness is measured;
- abstention is measured;
- failure categories are documented.

---

## v0.5 — Safety and authorization

### AI skill

Guardrails and safe tool use.

### Build

- tool permission classification;
- adversarial prompts;
- indirect prompt-injection fixture;
- authorization layer;
- action-proposal schema;
- optional simulated human approval.

### Exit criteria

- malicious document instructions do not bypass controls;
- prohibited tools cannot be invoked;
- safety tests are automated;
- model behavior is not the sole enforcement mechanism.

---

## v0.6 — AI observability

### AI skill

Operating AI systems.

### Build

- trace identifiers;
- model spans;
- tool-call spans;
- retrieval spans;
- latency measurements;
- token/usage metrics where available;
- failure metrics;
- evaluation result history.

Potential stack:

- OpenTelemetry
- Prometheus
- Grafana
- optional open-source AI observability component if justified

### Exit criteria

A failed investigation can be debugged from traces rather than by guessing.

---

## v0.7 — Provider/model comparison

### AI skill

Model selection and production trade-offs.

### Build

Compare at least two available model configurations using the same evaluation dataset.

Measure:

- accuracy;
- tool behavior;
- groundedness;
- latency;
- local resource use;
- token usage where applicable.

### Exit criteria

A written model-selection decision is supported by measured evidence.

---

## v0.8 — Production hardening

### AI skill

Reliability around probabilistic dependencies.

### Consider

- retries;
- fallback model;
- caching;
- rate limits;
- context-size control;
- concurrency;
- CI evaluation gate;
- prompt/model versioning;
- reproducible deployment.

Only implement items that solve observed failure modes.

---

## v0.9 — Optional live simulation

### Purpose

Add realism only after the AI core is already valuable.

Possible addition:

```text
Python simulator → MQTT → ingestion → database → agent tools
```

MQTT remains optional.

No physical hardware.

### Exit criteria

The new simulation layer does not dominate project effort or obscure AI behavior.

---

## v1.0 — Optional ML extension

### AI/ML skill

Classical/time-series ML working alongside an LLM agent.

Possible flow:

```text
synthetic telemetry
      ↓
anomaly detector
      ↓
anomaly event
      ↓
agent investigation
```

Possible topics:

- anomaly detection;
- train/validation/test split;
- precision/recall;
- false positives;
- model drift;
- ML inference metrics.

This milestone should happen only after the agentic-AI core is mature.

---

# Stop conditions

Do not add a feature merely because it is impressive.

Stop or postpone when work becomes dominated by:

- frontend polish;
- elaborate device simulation;
- Kubernetes;
- microservice decomposition;
- custom authentication;
- infrastructure unrelated to model behavior;
- framework experimentation without measured benefit;
- multi-agent architecture without a demonstrated single-agent limitation.

# Definition of project success

The project is strategically successful before every optional milestone is finished if it already proves:

1. controlled tool-using agent behavior;
2. grounded retrieval;
3. repeatable evaluation;
4. security boundaries;
5. observability;
6. model/provider trade-off reasoning.

Depth beats feature count.
