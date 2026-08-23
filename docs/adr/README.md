# Architecture Decision Records

Architecture Decision Records (ADRs) capture decisions that materially affect the system.

Do not create ADRs for trivial implementation details.

## When to write an ADR

Create one when a decision affects:

- architecture;
- model/provider strategy;
- data storage;
- retrieval;
- evaluation methodology;
- security boundaries;
- tool permissions;
- framework adoption;
- deployment model;
- significant reliability trade-offs.

## Naming

```text
0001-use-direct-model-interface-before-agent-framework.md
0002-require-zero-paid-service-runtime-path.md
0003-use-postgresql-pgvector-for-retrieval.md
```

Use sequential numbers.

## Status values

- Proposed
- Accepted
- Superseded
- Rejected

## Template

```markdown
# ADR-NNNN — Decision title

## Status

Proposed

## Context

What problem or decision are we facing?

What constraints matter?

What evidence do we have?

## Decision

What are we choosing?

## Alternatives considered

### Alternative A

Why was it considered?

Why was it not chosen?

### Alternative B

Why was it considered?

Why was it not chosen?

## Consequences

### Positive

- ...

### Negative

- ...

### Risks

- ...

## Validation

How will we know this decision was good?

Which test, evaluation, metric, or observed behavior should confirm it?
```

## First ADRs likely to be useful

Do not create them automatically, but expect decisions such as:

- direct SDK/local-model interface before an agent framework;
- zero-required-cost model execution path;
- provider abstraction;
- local embedding model;
- PostgreSQL + pgvector for retrieval;
- read-only tools in the first agent version;
- no physical device-control capability.

The purpose of ADRs is to preserve reasoning, not to create paperwork.
