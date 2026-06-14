# Vuls Master Context

## Identity

Vuls is an AI Product Builder.

Vuls turns an idea into product intelligence, reference signals, design direction, a deterministic agent workflow, and generation context for application generation.

Vuls is not a cybersecurity scanner. Agents must not interpret Vuls as a vulnerability scanner, CVE tool, security inventory, or remediation system unless a user explicitly asks for that unrelated domain.

## North Star

Vuls should generate product-specific applications that feel intentional, usable, and modern. It should not produce generic CRUD screens by default.

The system should understand the product, the domain, the target users, the desired emotion, and the visual direction before generating code.

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

```text
Product Intelligence
-> Reference Image Intelligence
-> Reference Analysis
-> Design Intelligence
-> Agent Workflow
-> Agent Execution
-> Generation Context
```

## Implementation Wiring Notes

The runtime project and Telegram services create deterministic project context during intake. They store Product Intelligence, Reference Analysis, Design Intelligence, and Agent Workflow in the project brief payload.

Generation Context is assembled from memory plus the stored intelligence artifacts before calling the generation orchestrator.

Reference Image Intelligence is implemented and is included in Generation Context when a `reference_image_analysis` payload exists. The inspected runtime entry points do not currently ingest uploaded image files directly.

Agent Execution helpers are implemented in `src/vuls/agent_intelligence.py`. They are deterministic helpers, not LLM-backed specialized agents.

## Product Intelligence

Product Intelligence turns the user's raw idea into structured product context.

It should capture:

- Product brief
- Domain
- Target users
- Jobs to be done
- MVP scope
- Business priorities
- Feature priorities
- Constraints and assumptions

Product Intelligence is the first product memory layer. Later layers should reuse it instead of rediscovering the same product facts.

## Reference Image Intelligence

Reference Image Intelligence extracts visual signals from optional reference image metadata.

It may identify:

- Composition signals
- Color signals
- Density signals
- Platform signals
- Quality signals
- Anti-copy constraints

Reference Image Intelligence must treat images as visual quality signals, not copy targets.

## Reference Analysis

Reference Analysis synthesizes text reference signals, product context, and Reference Image Intelligence when present.

References are inspiration signals, not templates.

Reference Analysis may identify:

- Mood signals
- Composition signals
- Visual quality signals
- Interaction signals
- Domain fit signals
- Anti-copy constraints

Reference Analysis must not copy a brand, mascot, logo, exact layout, exact visual system, or proprietary UI pattern.

## Design Intelligence

Design Intelligence converts product context and reference signals into a Design Contract.

The Design Contract should describe:

- Visual archetype
- Product emotion
- Hero object strategy
- Screen composition
- Visual hierarchy
- Surface model
- Color system
- Typography direction
- Spacing and radius system
- Motion direction
- Component rules
- UX rules
- Open Design prompt

Design Intelligence is the bridge between product reasoning and UI generation.

## Agent Workflow

Agent Workflow determines the deterministic execution order and handoff boundaries for the current product generation context.

It currently plans a structured workflow using:

- Vuls Architect
- Product Manager
- UX Designer
- UI Designer

These roles are deterministic workflow contracts in the current implementation. They are not separate LLM-backed workers.

## Agent Execution

Agent Execution executes workflow steps through deterministic helpers in `src/vuls/agent_intelligence.py`.

It returns structured step results such as:

- Agent role
- Agent name
- Execution status
- Summary
- Outputs
- Handoff target

This should not be confused with future LLM-backed multi-agent execution.

## Generation Context

Generation Context assembles memory, product intelligence, reference image intelligence when present, reference analysis, design intelligence, and agent workflow prompt items before project generation.

It currently feeds the generation orchestrator with structured context such as:

- Product brief and priorities
- Product memory
- Reference image signals when present
- Reference analysis
- Design contract prompt items
- Agent workflow prompt items

## Optional GitHub Export

GitHub Export is an optional export path after generation. It is not a current agent role and is not part of the deterministic intelligence pipeline.

It should preserve:

- Generated source files
- Documentation
- Validation results
- Commit or pull request context
- Traceability back to product, reference, design, and UX decisions

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

## Global Agent Rules

- Treat Vuls as an AI Product Builder.
- Preserve the pipeline order unless a user explicitly changes it.
- Prefer structured contracts over loose prose handoffs.
- Keep references as inspiration signals, never templates.
- Do not hardcode copied UI styles from reference screenshots.
- Keep old payloads backward-compatible when adding new context layers.
- Do not change runtime, API, Supabase schema, GitHub export, OpenRouter fallback, Open Design setup, or CRM CRUD unless the user explicitly asks.
- Validate claims with local evidence before reporting completion.
