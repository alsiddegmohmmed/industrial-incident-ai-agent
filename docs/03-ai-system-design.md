# 03 — AI System Design

## 1. Objective

The AI system should investigate incidents by deciding which trusted application tools to use, gathering evidence, and returning a validated diagnosis.

The model is a probabilistic reasoning component, not a trusted authority.

## 2. Core agent loop

The first implementation should make this mechanism explicit:

```text
1. Build messages/context.
2. Send available tool schemas to the model.
3. Model chooses:
      a. request one or more tools, or
      b. produce a final answer.
4. Validate every requested tool and its arguments.
5. Execute allowed tool calls.
6. Return bounded tool results to the model.
7. Repeat until:
      a. final answer,
      b. maximum turns,
      c. timeout,
      d. unrecoverable failure.
8. Validate final structured output.
```

## 3. Why no framework first?

The first goal is to understand the mechanics:

- message history;
- tool schema design;
- tool-result injection;
- context growth;
- retries;
- termination;
- validation;
- failure handling.

A framework may be introduced later after these concepts are understood.

## 4. Model provider requirements

The design should support more than one model source.

Required capabilities:

- text generation;
- structured output or schema-constrained generation when possible;
- tool/function calling when possible;
- usage metadata when available;
- configurable timeout;
- normalized error handling.

Hard constraint:

> The project must retain a path that does not require a paid API.

## 5. Initial system behavior

The agent should receive:

- role and task definition;
- behavioral constraints;
- tool descriptions;
- relevant investigation metadata;
- previous tool results.

It should not receive:

- raw database credentials;
- unrestricted database access;
- evaluation ground truth;
- hidden incident cause;
- arbitrary shell access.

## 6. Structured output

Initial schema:

```json
{
  "device_id": "motor-17",
  "severity": "high",
  "summary": "Possible bearing degradation under sustained load",
  "observations": [
    {
      "statement": "Vibration increased before temperature crossed the alert threshold",
      "source": "telemetry"
    }
  ],
  "inferences": [
    {
      "statement": "Bearing degradation is a plausible cause",
      "confidence": 0.78
    }
  ],
  "recommended_actions": [
    {
      "action": "Inspect bearing assembly",
      "priority": "high",
      "requires_approval": false
    }
  ],
  "confidence": 0.82,
  "evidence_refs": []
}
```

The schema may evolve after evaluation shows which fields are useful.

## 7. Tool design principles

Tool descriptions are part of the model's operating environment and must be tested.

### Tool: get_device_state

Purpose:

Return the current known state of one device.

Constraints:

- one device per call;
- no wildcard;
- bounded response.

### Tool: get_telemetry_history

Purpose:

Return one or more telemetry signals for a bounded time window.

Constraints:

- maximum allowed time range;
- validated metric names;
- bounded sample count;
- no arbitrary query language.

### Tool: get_recent_alerts

Purpose:

Return recent alerts for a device.

### Tool: get_previous_incidents

Purpose:

Return prior resolved incidents without leaking current evaluation ground truth.

### Tool: search_equipment_manual

Purpose:

Retrieve relevant technical-document passages with source metadata.

## 8. Context engineering

The project should explicitly experiment with:

- what belongs in the system/developer instruction;
- what tool descriptions should contain;
- how much tool output to include;
- when to summarize earlier turns;
- when retrieved text should be excluded;
- context size versus accuracy;
- how source metadata is represented.

Context changes should be evaluated, not judged only by anecdotal examples.

## 9. Grounding strategy

The agent should prefer evidence in this order:

1. current device state;
2. recent telemetry;
3. recent alerts;
4. previous incidents;
5. relevant technical documentation;
6. model prior knowledge only when clearly identified and permitted.

The final diagnosis should clearly distinguish observed data from inferred cause.

## 10. RAG design

When introduced:

```text
Manuals
  ↓
Parsing
  ↓
Chunking
  ↓
Embedding
  ↓
Vector storage
  ↓
Retrieval
  ↓
Optional reranking
  ↓
Bounded evidence returned through tool
```

Questions to evaluate:

- chunk size;
- overlap;
- embedding model;
- metadata filters;
- top-k;
- hybrid versus vector-only search;
- reranking;
- citation quality.

## 11. Abstention

The agent should prefer:

> Insufficient evidence to identify a reliable cause.

over inventing a diagnosis.

Evaluation cases must deliberately test abstention.

## 12. Deterministic code versus model reasoning

Use deterministic code for:

- validation;
- authorization;
- schema checking;
- thresholds when explicitly defined;
- database queries;
- resource limits;
- tool permissions;
- approval requirements.

Use the model for:

- interpreting operator intent;
- deciding which evidence to gather;
- synthesizing multiple evidence sources;
- generating candidate explanations;
- explaining uncertainty.

## 13. Agent limits

Starting limits should include:

- maximum model turns;
- maximum tool calls;
- per-tool timeout;
- overall investigation timeout;
- maximum tool-result size;
- maximum retrieved chunks.

Exact values should be chosen during implementation and recorded in an ADR if they become significant.

## 14. Provider comparison

The project should eventually compare at least two model configurations using the same evaluation dataset.

Compare:

- task success;
- tool-selection accuracy;
- groundedness;
- latency;
- token usage;
- local resource requirements;
- failure behavior.

The objective is not to identify a universally best model. It is to practice model-selection trade-offs.

## 15. Future topics

Only after the single-agent baseline is measured:

- agent framework;
- MCP;
- memory;
- long-running tasks;
- model fallback;
- human approval;
- multi-agent orchestration;
- time-series ML.

Each addition requires a concrete reason and an evaluation plan.
