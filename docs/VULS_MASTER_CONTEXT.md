# Vuls Master Context

## Identity

Vuls is an AI Product Builder.

Vuls turns an idea into product intelligence, reference intelligence, design direction, generated application code, QA feedback, and GitHub-ready output.

Vuls is not a cybersecurity scanner. Agents must not interpret Vuls as a vulnerability scanner, CVE tool, security inventory, or remediation system unless a user explicitly asks for that unrelated domain.

## North Star

Vuls should generate product-specific applications that feel intentional, usable, and modern. It should not produce generic CRUD screens by default.

The system should understand the product, the domain, the target users, the desired emotion, and the visual direction before generating code.

## Core Pipeline

```text
Idea
-> Product Intelligence
-> Reference Intelligence
-> Design Intelligence
-> UX Intelligence
-> Code Generation
-> QA
-> GitHub Export
```

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

## Reference Intelligence

Reference Intelligence extracts inspiration signals from optional references.

References are inspiration signals, not templates.

Reference Intelligence may identify:

- Mood signals
- Composition signals
- Visual quality signals
- Interaction signals
- Domain fit signals
- Anti-copy constraints

Reference Intelligence must not copy a brand, mascot, logo, exact layout, exact visual system, or proprietary UI pattern.

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

## UX Intelligence

UX Intelligence defines product behavior and user flow.

It should reason about:

- Information architecture
- Core user journeys
- Screen inventory
- Primary actions
- Empty, loading, and error states
- Navigation model
- Onboarding and retention loops
- Platform-specific ergonomics

UX Intelligence should make the product usable before the interface is rendered.

## Code Generation

Code Generation turns structured product, UX, and design context into application code.

It should favor:

- React and Next.js compatibility
- Tailwind-compatible styling when requested by the pipeline
- Reusable components
- Clear state boundaries
- Accessible UI
- Buildable output

Code Generation must follow the contracts produced by earlier intelligence layers.

## QA

QA validates that generated output matches the user's request and the structured contracts.

QA should check:

- Build compatibility
- Tests and lint results
- Visual and UX regressions
- Missing states
- Domain specificity
- Reference anti-copy constraints
- GitHub export readiness

## GitHub Export

GitHub Export packages or publishes generated work into a repository flow.

It should preserve:

- Generated source files
- Documentation
- Validation results
- Commit or pull request context
- Traceability back to product, reference, design, and UX decisions

## Global Agent Rules

- Treat Vuls as an AI Product Builder.
- Preserve the pipeline order unless a user explicitly changes it.
- Prefer structured contracts over loose prose handoffs.
- Keep references as inspiration signals, never templates.
- Do not hardcode copied UI styles from reference screenshots.
- Keep old payloads backward-compatible when adding new context layers.
- Do not change runtime, API, Supabase schema, GitHub export, OpenRouter fallback, Open Design setup, or CRM CRUD unless the user explicitly asks.
- Validate claims with local evidence before reporting completion.
