# Vuls Agent System

## Purpose

The Vuls Agent System documents the current deterministic agent workflow contracts and the future LLM-backed agent roadmap.

Documentation must distinguish current implementation from future architecture. If documentation and code disagree, code is the source of truth.

## Current Implemented Pipeline

The following pipeline is active and deterministic in the current codebase:

1. Product Intelligence — analyzes product idea and extracts requirements
2. Reference Image Intelligence — processes reference images when provided
3. Reference Analysis — synthesizes reference information
4. Design Intelligence — creates design decisions and structure
5. Agent Workflow — determines execution order
6. Agent Execution — executes workflow agents
7. Generation Context — assembles final generation context

This is the actual current implementation.

Implementation note: the current runtime project and Telegram services persist Agent Workflow and assemble Generation Context. `src/vuls/agent_intelligence.py` also contains deterministic Agent Execution helpers. These helpers are not LLM-backed specialized agents.

## Future Roadmap — Not Yet Implemented

The following represents the target architecture and is not yet active:

- Product Manager Agent (LLM-backed)
- UX Designer Agent (LLM-backed)
- UI Designer Agent (LLM-backed)
- Frontend Engineer Agent
- Backend Engineer Agent
- QA Engineer Agent

These are documented future components.

They are not currently active in the deterministic workflow.

## Agent Roles: Current vs Future

### Vuls Architect (Current)

Status: ACTIVE

Role:

- Architecture coordination
- Workflow orchestration
- Pipeline consistency

Important:

Vuls Architect is NOT a GitHub Export agent.

### Frontend / Backend / QA Agents (Future)

Status:

DOCUMENTED

NOT ACTIVE

These agents become active only after LLM-backed execution is implemented.

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
- Reference Image Intelligence output when present
- Reference Analysis output
- Design Intelligence output
- Agent Workflow output
- Generation Context

### Tools

Tools are capabilities available to the current workflow.

Examples:

- Repository inspection
- Code generation
- Open Design integration
- Test and lint execution
- Build validation
- GitHub export

Agents should use tools only when their role and the active workflow require them. Future agent tools must not be documented as current runtime behavior until they are wired in code.

### Role

The role file defines the agent's responsibility, boundaries, response format, and Vuls-specific rules.

Roles prevent the system from mixing product strategy, UX, UI, engineering, and QA into one unstructured response.

### Workflow

Workflow defines the order of work and handoffs.

Current deterministic workflow:

```text
Product Intelligence
-> Reference Image Intelligence
-> Reference Analysis
-> Design Intelligence
-> Agent Workflow
-> Agent Execution
-> Generation Context
```

Future LLM-backed workflow target:

```text
Idea
-> Product Manager
-> UX Designer
-> UI Designer
-> Frontend Engineer
-> Backend Engineer
-> QA Engineer
-> GitHub Export
```

The future workflow is not active in the current deterministic runtime.

## Handoff Model

Agents should pass structured outputs forward.

Preferred handoff artifacts:

- Product brief
- Reference image analysis when present
- Reference analysis
- Design contract
- Agent workflow
- Agent execution result when used
- Generation context

Handoffs should include decisions, constraints, risks, and unresolved questions.

## Guardrails

- Do not treat Vuls as a cybersecurity scanner.
- Do not copy reference UIs, brands, mascots, logos, or exact layouts.
- Do not bypass Product Intelligence for product-specific work.
- Do not bypass Reference or Design Intelligence when visual quality matters.
- Do not add runtime behavior from documentation-only agent work.
- Do not change public API, Supabase schema, GitHub export, OpenRouter fallback, Open Design setup, or CRM CRUD without explicit user approval.

## MVP Scope

The current implementation includes deterministic intelligence builders, workflow contracts, and generation context assembly.

It does not yet implement:

- LLM-backed specialized agent execution
- Persistent agent state
- Tool permission enforcement
- Multi-agent orchestration
- Upload or storage pipelines
- New model providers

Those can be added later after the role contracts are stable.
