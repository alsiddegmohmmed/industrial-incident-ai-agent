# Industrial Incident AI Agent

A software-only, AI-first engineering project that investigates simulated industrial incidents using structured LLM outputs, controlled tool calling, retrieval over technical documentation, and evaluation-driven development.

The project is designed to demonstrate practical AI engineering rather than IoT hardware development.

## Core idea

An operator asks a question such as:

> Why is motor-17 overheating?

The system investigates the incident by using controlled tools to inspect synthetic telemetry, recent alerts, historical incidents, and technical documentation. It then returns an evidence-backed diagnosis, clearly separating observations from inference and recommending the next action.

## Hard constraints

- No physical hardware is required.
- No hardware purchase is expected at any stage.
- All devices, telemetry, alerts, incidents, and control interfaces are simulated in software.
- The project must remain runnable without a paid AI subscription or paid API.
- A local model path must remain possible.
- Free-tier hosted models may be supported, but the architecture must not depend on them.
- The project is AI-first. Backend, IoT, UI, infrastructure, and deployment work must remain subordinate to the AI-engineering learning goals.
- A complex frontend is out of scope for the initial versions.
- Multi-agent architecture is out of scope until a single-agent architecture is proven insufficient.
- An agent framework is not required for the first implementation.

## Career claim

The finished project should support this claim:

> I can design, build, evaluate, secure, observe, and operate a production-style agentic AI system that uses controlled tools and grounded data rather than treating an LLM as a simple chat API.

## Primary capabilities

The project will progressively demonstrate:

1. Direct model integration
2. Structured outputs
3. Tool/function calling
4. Agent-loop design
5. Context engineering
6. Retrieval-augmented generation
7. Evaluation-driven development
8. AI safety and tool authorization
9. LLM and tool observability
10. Provider/model abstraction
11. Production-style failure handling
12. Optional time-series anomaly detection

## Initial scenario

The initial simulated environment contains a small number of industrial devices such as motors.

Example telemetry:

```json
{
  "device_id": "motor-17",
  "timestamp": "2026-08-23T07:30:00Z",
  "temperature_c": 91.2,
  "vibration_mm_s": 7.8,
  "rpm": 1420,
  "load_percent": 94.1,
  "status": "running"
}
```

Example operator request:

```text
Why is motor-17 overheating?
```

The system may use tools such as:

```text
get_device_state()
get_telemetry_history()
get_recent_alerts()
get_previous_incidents()
search_equipment_manual()
```

The final response must be structured and evidence-backed.

## Proposed technology stack

The stack is deliberately conservative.

- Python
- FastAPI
- Pydantic
- PostgreSQL
- pgvector when retrieval is introduced
- pytest
- Docker / Docker Compose
- OpenTelemetry
- Prometheus
- Grafana
- Local/open-weight LLM support
- Optional free-tier hosted LLM provider

The first agent loop should be implemented directly against a model API or local model interface before introducing an orchestration framework.

## Repository structure

```text
industrial-incident-ai-agent/
├── README.md
├── docs/
│   ├── 01-product-spec.md
│   ├── 02-architecture.md
│   ├── 03-ai-system-design.md
│   ├── 04-evaluation-plan.md
│   ├── 05-security-model.md
│   ├── 06-roadmap.md
│   └── adr/
│       └── README.md
├── src/
├── tests/
├── evals/
│   ├── cases/
│   ├── datasets/
│   └── results/
├── data/
│   ├── manuals/
│   ├── telemetry/
│   └── incidents/
└── docker-compose.yml
```

Only the documentation exists initially. Runtime directories and implementation files should be created when their milestone requires them.

## Current implementation: v0.2

The v0.1 baseline provides:

- a FastAPI investigation endpoint;
- strict Pydantic request and diagnosis schemas;
- a replaceable model-provider boundary;
- a zero-required-cost local Ollama provider;
- three synthetic incident fixtures;
- deterministic API, validation, and failure-path tests.

The v0.2 slice adds a hand-written, bounded agent loop. The model initially
receives only the operator request and device metadata, then selects from four
read-only tools:

- `get_device_state`
- `get_telemetry_history`
- `get_recent_alerts`
- `get_previous_incidents`

Every tool call is validated against a typed schema and the requested device.
The response includes a safe tool trace with accepted/rejected calls, evidence
references, turn count, and termination reason. The loop enforces an overall
timeout, maximum model turns, and maximum tool calls.

### Local setup

Requirements:

- Python 3.11 or newer;
- either a supported native Ollama installation or Docker Desktop for real
  local-model investigations.

Create an environment and install the project:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

Start Ollama through Docker and pull the default local model:

```bash
docker compose up -d ollama
docker compose exec ollama ollama pull qwen2.5:3b
```

Alternatively, if native Ollama is supported on the machine:

```bash
ollama pull qwen2.5:3b
```

Then start the API:

```bash
uvicorn incident_agent.main:app --reload
```

Run the tests:

```bash
pytest
```

Run the opt-in live tests against the local Ollama model:

```bash
RUN_OLLAMA_INTEGRATION=1 pytest tests/integration/test_live_ollama.py -v
```

The live suite is excluded from normal test runs because CPU-only inference can
take several minutes.

Try an investigation:

```bash
curl -X POST http://127.0.0.1:8000/v1/investigations \
  -H 'Content-Type: application/json' \
  -d '{"operator_request":"Why is motor-17 overheating?"}'
```

Configuration can be changed with the environment variables documented in
`.env.example`. The API returns `503 Service Unavailable` when the local model
cannot be reached or its response fails schema validation.

The default model timeout is five minutes because first-load, CPU-only inference
can take more than one minute. Faster machines can lower `MODEL_TIMEOUT_SECONDS`.
The default `qwen2.5:3b` model is the measured CPU baseline. The 1.5B model was
faster but misclassified normal telemetry, while the 7B model exceeded the
five-minute timeout under resource contention on the development machine.

The agent controls can be tuned with `AGENT_TIMEOUT_SECONDS`, `AGENT_MAX_TURNS`,
and `AGENT_MAX_TOOL_CALLS`. These limits protect the application even when a
model repeatedly requests invalid or unnecessary tools.

## Development principle

Every feature must answer one question:

> Which AI-engineering capability does this feature teach or demonstrate?

If the answer is unclear, do not build it yet.

Examples:

- RAG evaluation: yes
- tool authorization: yes
- model fallback: yes
- polished IoT dashboard: no, not initially
- Kubernetes cluster: no, not initially
- elaborate MQTT topology: no, not initially

## Documentation

Start with:

- [Product specification](docs/01-product-spec.md)
- [Architecture](docs/02-architecture.md)
- [AI system design](docs/03-ai-system-design.md)
- [Evaluation plan](docs/04-evaluation-plan.md)
- [Security model](docs/05-security-model.md)
- [Roadmap](docs/06-roadmap.md)
- [Architecture decision records](docs/adr/README.md)
