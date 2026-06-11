# Vuls Agent System

## Purpose

The Vuls Agent System is a lightweight documentation-based memory foundation for future specialized agents.

The first version is intentionally simple. It defines shared memory, role files, and workflow expectations without adding runtime code.

## Agent Formula

```text
Existing LLM
+ Memory
+ Tools
+ Role
+ Workflow
= Vuls Agent
```

## Components

### Existing LLM

The existing LLM remains the reasoning engine. Vuls does not need a separate model per agent for the MVP.

### Memory

Memory is the context an agent must load before acting.

Core memory sources:

- `docs/VULS_MASTER_CONTEXT.md`
- `docs/agents/*.md`
- Product Intelligence output
- Reference Intelligence output
- Design Intelligence output
- UX Intelligence output
- Code generation context
- QA results

### Tools

Tools are capabilities available to the current workflow.

Examples:

- Repository inspection
- Code generation
- Open Design integration
- Test and lint execution
- Build validation
- GitHub export

Agents should use tools only when their role and the active workflow require them.

### Role

The role file defines the agent's responsibility, boundaries, response format, and Vuls-specific rules.

Roles prevent the system from mixing product strategy, UX, UI, engineering, and QA into one unstructured response.

### Workflow

Workflow defines the order of work and handoffs.

Default Vuls workflow:

```text
Idea
-> Product Manager
-> UX Designer
-> UI Designer
-> Frontend Engineer
-> Backend Engineer
-> QA Engineer
-> Vuls Architect review
-> GitHub Export
```

The workflow can skip roles when the task is small, but it should preserve the contract order:

```text
Product Intelligence
-> Reference Intelligence
-> Design Intelligence
-> UX Intelligence
-> Code Generation
-> QA
-> GitHub Export
```

## Handoff Model

Agents should pass structured outputs forward.

Preferred handoff artifacts:

- Product brief
- Reference analysis
- Design contract
- UX flow spec
- Component plan
- API or data contract
- QA report
- GitHub export summary

Handoffs should include decisions, constraints, risks, and unresolved questions.

## Guardrails

- Do not treat Vuls as a cybersecurity scanner.
- Do not copy reference UIs, brands, mascots, logos, or exact layouts.
- Do not bypass Product Intelligence for product-specific work.
- Do not bypass Reference or Design Intelligence when visual quality matters.
- Do not add runtime behavior from documentation-only agent work.
- Do not change public API, Supabase schema, GitHub export, OpenRouter fallback, Open Design setup, or CRM CRUD without explicit user approval.

## MVP Scope

This documentation layer is the first memory system.

It does not yet implement:

- Agent routing runtime
- Persistent agent state
- Tool permission enforcement
- Multi-agent orchestration
- Upload or storage pipelines
- New model providers

Those can be added later after the role contracts are stable.
